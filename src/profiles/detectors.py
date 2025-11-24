"""Convexity profile detectors.

Each detector outputs a continuous score in [0, 1] indicating how strongly
that convexity profile is expressed in current market conditions.

The 6 Profiles:
1. Long-Dated Gamma Efficiency (LDG)
2. Short-Dated Gamma Spike (SDG)
3. Charm/Decay Dominance (CHARM)
4. Vanna Convexity (VANNA)
5. Skew Convexity (SKEW)
6. Vol-of-Vol Convexity (VOV)

All scoring uses sigmoid functions for smooth 0-1 transitions.

NaN HANDLING POLICY:
- NaN during warmup period (first 60-90 days): EXPECTED and acceptable
- NaN after warmup: CRITICAL ERROR - indicates missing data corruption
- Profile scores with NaN will NOT be silently filled with 0
- Allocation logic MUST check for NaN before allocating capital
"""

import pandas as pd
import numpy as np
from .features import ProfileFeatures, sigmoid


class ProfileValidationError(Exception):
    """Raised when profile scores contain invalid NaN values after warmup."""
    pass


class ProfileDetectors:
    """Compute convexity profile scores (0-1) for each market regime."""

    def __init__(self, lookback_percentile: int = 60):
        """Initialize profile detectors.

        Args:
            lookback_percentile: Window for percentile calculations
        """
        self.feature_engine = ProfileFeatures(lookback_percentile)

    def compute_all_profiles(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all 6 profile scores.

        Args:
            df: DataFrame with data-spine features (RV, ATR, MA, etc.)

        Returns:
            DataFrame with 6 profile score columns (0-1 range)
        """
        df = df.copy()

        # 1. Compute profile-specific features
        df = self.feature_engine.compute_all_features(df)

        # 2. Compute each profile score (raw)
        df['profile_1_LDG'] = self._compute_long_gamma_score(df)
        df['profile_2_SDG_raw'] = self._compute_short_gamma_score(df)
        df['profile_3_CHARM'] = self._compute_charm_score(df)
        df['profile_4_VANNA'] = self._compute_vanna_score(df)
        df['profile_5_SKEW_raw'] = self._compute_skew_score(df)
        df['profile_6_VOV'] = self._compute_vov_score(df)

        # 3. Apply EMA smoothing to noisy profiles (SDG, SKEW)
        # BUG FIX (2025-11-18): Agent #3 found span=3 too short, causes noise
        # Increased to span=7 for better noise reduction
        df['profile_2_SDG'] = df['profile_2_SDG_raw'].ewm(span=7, adjust=False).mean()
        df['profile_5_SKEW'] = df['profile_5_SKEW_raw'].ewm(span=7, adjust=False).mean()

        # Drop raw columns
        df = df.drop(columns=['profile_2_SDG_raw', 'profile_5_SKEW_raw'])

        return df

    def validate_profile_scores(self, df: pd.DataFrame, warmup_days: int = 90) -> None:
        """
        Validate profile scores for NaN values after warmup period.

        Raises ProfileValidationError if NaN detected after warmup.

        Args:
            df: DataFrame with profile scores
            warmup_days: Number of days for warmup period (default 90)
        """
        profile_cols = [
            'profile_1_LDG', 'profile_2_SDG', 'profile_3_CHARM',
            'profile_4_VANNA', 'profile_5_SKEW', 'profile_6_VOV'
        ]

        # Check only rows after warmup
        if len(df) <= warmup_days:
            # Entire dataset is warmup - no validation needed
            return

        post_warmup = df.iloc[warmup_days:]

        for col in profile_cols:
            if col not in post_warmup.columns:
                continue

            nan_count = post_warmup[col].isna().sum()
            if nan_count > 0:
                nan_dates = post_warmup[post_warmup[col].isna()]['date'].tolist()
                raise ProfileValidationError(
                    f"{col} has {nan_count} NaN values after warmup period "
                    f"(after row {warmup_days}). This indicates missing/corrupt data. "
                    f"NaN dates: {nan_dates[:10]}..."
                )

    def _compute_long_gamma_score(self, df: pd.DataFrame) -> pd.Series:
        """Profile 1: Long-Dated Gamma Efficiency.

        Attractive when:
        - Long-dated vol is cheap (RV/IV ratio high)
        - IV rank is low (cheap vol in absolute terms)
        - Upward drift (positive MA slope)

        Formula:
            LDG_score = sigmoid((RV10/IV60) - 0.9) ×
                       sigmoid((IV_rank_60 - 0.4) × -1) ×
                       sigmoid(slope_MA20)

        Returns:
            Score in [0, 1]
        """
        # Factor 1: RV catching up to IV (cheap long vol)
        # When RV10/IV60 > 0.9, vol is relatively cheap
        rv_iv_ratio = df['RV10'] / (df['IV60'] + 1e-6)
        factor1 = sigmoid((rv_iv_ratio - 0.9) * 5)  # k=5 for moderate steepness

        # Factor 2: IV rank low (vol cheap in absolute terms)
        # When IV_rank < 0.4, we're in low vol regime
        factor2 = sigmoid((0.4 - df['IV_rank_60']) * 5)

        # Factor 3: Upward trend (positive slope)
        factor3 = sigmoid(df['slope_MA20'] * 100)  # Scale slope for sigmoid

        # Geometric mean (all factors must be present)
        score = (factor1 * factor2 * factor3) ** (1/3)

        # Do NOT fillna(0) - let NaN propagate to catch data quality issues
        # Warmup period NaN is expected and handled downstream
        return score

    def _compute_short_gamma_score(self, df: pd.DataFrame) -> pd.Series:
        """Profile 2: Short-Dated Gamma Spike.

        Attractive when:
        - Short-term RV spiking faster than IV reprices
        - Large daily moves relative to ATR
        - Vol-of-vol rising (volatility unstable)

        Formula:
            SDG_score = sigmoid((RV5/IV7) - 0.8) ×
                       sigmoid(abs(ret_1d)/ATR5) ×
                       sigmoid(VVIX_slope)

        Returns:
            Score in [0, 1]
        """
        # Factor 1: RV spiking vs short IV
        rv_iv_ratio = df['RV5'] / (df['IV7'] + 1e-6)
        factor1 = sigmoid((rv_iv_ratio - 0.8) * 5)

        # Factor 2: Large daily moves (relative to recent range)
        # BUG FIX (2025-11-18): Agent #3 found - missing abs() for move_size
        move_size = abs(df['ret_1d']) / (df['ATR5'] / df['close'] + 1e-6)
        factor2 = sigmoid((move_size - 1.0) * 3)

        # Factor 3: VVIX rising (vol-of-vol increasing)
        factor3 = sigmoid(df['VVIX_slope'] * 1000)  # Scale slope

        # Geometric mean
        score = (factor1 * factor2 * factor3) ** (1/3)

        # Do NOT fillna(0) - let NaN propagate
        return score

    def _compute_charm_score(self, df: pd.DataFrame) -> pd.Series:
        """Profile 3: Charm/Decay Dominance.

        Attractive when:
        - IV elevated relative to RV (vol overpriced)
        - Market pinned (tight range)
        - Vol-of-vol declining (stable conditions)

        Formula:
            CHARM_score = sigmoid((IV20/RV10) - 1.4) ×
                         sigmoid(range_10d < 0.03) ×
                         sigmoid(-VVIX_slope)

        Returns:
            Score in [0, 1]
        """
        # Factor 1: IV rich vs RV (vol overpriced)
        iv_rv_ratio = df['IV20'] / (df['RV10'] + 1e-6)
        factor1 = sigmoid((iv_rv_ratio - 1.4) * 5)

        # Factor 2: Market pinned (tight range)
        # range_10d < 0.03 means <3% range
        factor2 = sigmoid((0.035 - df['range_10d']) * 100)

        # Factor 3: VVIX declining (stable vol)
        factor3 = sigmoid(-df['VVIX_slope'] * 1000)

        # Geometric mean
        score = (factor1 * factor2 * factor3) ** (1/3)

        # Do NOT fillna(0) - let NaN propagate
        return score

    def _compute_vanna_score(self, df: pd.DataFrame) -> pd.Series:
        """Profile 4: Vanna Convexity.

        Attractive when:
        - Low IV rank (vol cheap)
        - Upward trend (positive drift)
        - Vol-of-vol stable/declining

        Vanna benefits from correlation between spot moves and vol changes.
        Best in low vol, trending up environments.

        Formula:
            VANNA_score = sigmoid(-IV_rank_20) ×
                         sigmoid(slope_MA20) ×
                         sigmoid(-VVIX_slope)

        Returns:
            Score in [0, 1]
        """
        # Factor 1: Low IV rank (cheap vol)
        # BUG FIX (2025-11-18): Agent #3 found wrong sign - correcting formula
        # Want high score when IV_rank < 0.3 (cheap vol)
        factor1 = sigmoid((0.3 - df['IV_rank_20']) * 5)  # High when rank < 0.3

        # Factor 2: Upward trend
        factor2 = sigmoid(df['slope_MA20'] * 100)

        # Factor 3: VVIX stable/declining
        factor3 = sigmoid(-df['VVIX_slope'] * 1000)

        # Geometric mean
        score = (factor1 * factor2 * factor3) ** (1/3)

        # Do NOT fillna(0) - let NaN propagate
        return score

    def _compute_skew_score(self, df: pd.DataFrame) -> pd.Series:
        """Profile 5: Skew Convexity.

        Attractive when:
        - Skew steepening (put premium rising)
        - Vol-of-vol rising (fear building)
        - RV > IV (realized overtaking implied)

        Formula:
            SKEW_score = sigmoid(skew_z - 1.0) ×
                        sigmoid(VVIX_slope) ×
                        sigmoid((RV5/IV20) - 1)

        Returns:
            Score in [0, 1]
        """
        # Factor 1: Skew steepening (z-score > 1)
        factor1 = sigmoid((df['skew_z'] - 1.0) * 2)

        # Factor 2: VVIX rising
        factor2 = sigmoid(df['VVIX_slope'] * 1000)

        # Factor 3: RV catching up to IV
        rv_iv_ratio = df['RV5'] / (df['IV20'] + 1e-6)
        factor3 = sigmoid((rv_iv_ratio - 1.0) * 5)

        # Geometric mean
        score = (factor1 * factor2 * factor3) ** (1/3)

        # Do NOT fillna(0) - let NaN propagate
        return score

    def _compute_vov_score(self, df: pd.DataFrame) -> pd.Series:
        """Profile 6: Vol-of-Vol Convexity.

        Attractive when:
        - VVIX elevated (high percentile)
        - VVIX rising (vol becoming more volatile)
        - IV rank high (vol already elevated)

        Formula:
            VOV_score = sigmoid((VVIX/VVIX_80pct) - 1) ×
                       sigmoid(VVIX_slope) ×
                       sigmoid(IV_rank_20)

        Returns:
            Score in [0, 1]
        """
        # Factor 1: VVIX elevated vs recent 80th percentile
        vvix_ratio = df['VVIX'] / (df['VVIX_80pct'] + 1e-6)
        factor1 = sigmoid((vvix_ratio - 1.0) * 5)

        # Factor 2: VVIX rising
        factor2 = sigmoid(df['VVIX_slope'] * 1000)

        # Factor 3: IV rank LOW (want to buy straddles when vol is CHEAP)
        # FIXED: Inverted sign - was buying expensive vol, now buying cheap vol
        factor3 = sigmoid((0.5 - df['IV_rank_20']) * 5)

        # Factor 4: RV/IV compression (vol about to expand)
        # FIXED: Added compression detection - score high when RV < IV (compressed)
        rv_iv_ratio = df['RV10'] / (df['IV20'] + 1e-6)
        factor4 = sigmoid((1.0 - rv_iv_ratio) * 5)

        # Geometric mean (4 factors now)
        score = (factor1 * factor2 * factor3 * factor4) ** (1/4)

        # Do NOT fillna(0) - let NaN propagate
        return score


def get_profile_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Convenience function to get all profile scores.

    Args:
        df: DataFrame with data-spine features

    Returns:
        DataFrame with 6 profile score columns
    """
    detector = ProfileDetectors()
    return detector.compute_all_profiles(df)


def get_profile_names() -> list:
    """Get list of profile names in order."""
    return [
        'profile_1_LDG',
        'profile_2_SDG',
        'profile_3_CHARM',
        'profile_4_VANNA',
        'profile_5_SKEW',
        'profile_6_VOV'
    ]


def validate_profile_scores(df: pd.DataFrame) -> dict:
    """Validate profile score calculations.

    Args:
        df: DataFrame with profile scores

    Returns:
        Dictionary with validation results
    """
    results = {
        'row_count': len(df),
        'date_range': (df['date'].min(), df['date'].max()) if 'date' in df.columns else ('N/A', 'N/A'),
        'score_stats': {},
        'out_of_range': {}
    }

    profile_cols = get_profile_names()

    for col in profile_cols:
        if col in df.columns:
            scores = df[col].dropna()

            # Check range [0, 1]
            out_of_range = ((scores < 0) | (scores > 1)).sum()
            results['out_of_range'][col] = int(out_of_range)

            # Stats
            results['score_stats'][col] = {
                'mean': float(scores.mean()),
                'std': float(scores.std()),
                'min': float(scores.min()),
                'max': float(scores.max()),
                'median': float(scores.median())
            }

    return results
