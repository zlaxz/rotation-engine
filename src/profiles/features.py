"""Feature engineering for profile detection.

Computes:
- IV proxies (using RV until real IV available)
- IV rank (percentile)
- VVIX proxy (volatility of volatility)
- VVIX slope
- Skew proxy
- Sigmoid transformation function

All calculations are walk-forward compliant.
"""

import pandas as pd
import numpy as np
from typing import Optional


def sigmoid(x: pd.Series, k: float = 1.0) -> pd.Series:
    """Smooth 0-1 mapping with steepness k.

    Maps any input to [0, 1] range with smooth transition.

    Args:
        x: Input series
        k: Steepness parameter (higher = sharper transition, default=1.0)

    Returns:
        Series in [0, 1] range

    Examples:
        sigmoid(0) = 0.5
        sigmoid(large positive) → 1.0
        sigmoid(large negative) → 0.0
    """
    return 1 / (1 + np.exp(-k * x))


class ProfileFeatures:
    """Compute features needed for profile detection."""

    def __init__(self, lookback_percentile: int = 60):
        """Initialize feature calculator.

        Args:
            lookback_percentile: Window for percentile calculations (days)
        """
        self.lookback_percentile = lookback_percentile

    def compute_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all features needed for profile detection.

        Args:
            df: DataFrame with data-spine features (RV5, RV10, RV20, ATR, etc.)

        Returns:
            DataFrame with additional profile-specific features
        """
        df = df.copy()

        # 1. IV Proxies (use RV × 1.2 as typical IV/RV relationship)
        df = self._compute_iv_proxies(df)

        # 2. IV Rank (percentiles)
        df = self._compute_iv_ranks(df)

        # 3. VVIX proxy (vol-of-vol)
        df = self._compute_vvix(df)

        # 4. VVIX slope
        df = self._compute_vvix_slope(df)

        # 5. Skew proxy (until we have real IV surface)
        df = self._compute_skew_proxy(df)

        # 6. Additional helper features
        df = self._compute_helper_features(df)

        return df

    def _compute_iv_proxies(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute IV from VIX term structure.

        VIX represents 30-day ATM implied volatility.
        We compute IV for different horizons by interpolating the term structure:
        - IV7: Short-term (0.5x VIX scaling typical for 7-day vol vs 30-day)
        - IV20: Near VIX (0.95x VIX for 20-day)
        - IV60: Long-term (1.1x VIX for 60-day, term structure typically upward sloping)

        If VIX is unavailable, falls back to RV-based proxy with warning.
        """
        df = df.copy()

        if 'vix_close' in df.columns and not df['vix_close'].isna().all():
            # VIX-based calculation (REAL forward-looking IV)
            # VIX is quoted as %, already annualized
            vix = df['vix_close']

            # Term structure scaling based on typical VIX term structure shape
            # Short-term vol tends to be lower, long-term higher
            df['IV7'] = vix * 0.85   # 7-day typically 15% below 30-day
            df['IV20'] = vix * 0.95  # 20-day close to 30-day
            df['IV60'] = vix * 1.08  # 60-day typically 8% above 30-day (contango)

            # Handle any NaN in VIX (market closed, data gaps)
            # Forward-fill last valid VIX value (reasonable for day-to-day gaps)
            df['IV7'] = df['IV7'].ffill()
            df['IV20'] = df['IV20'].ffill()
            df['IV60'] = df['IV60'].ffill()

        else:
            # Fallback: RV-based proxy (BACKWARD-LOOKING)
            # Typical relationship: IV ≈ RV × 1.2 (IV trades at premium to RV)
            import sys
            print("WARNING: VIX data unavailable, using RV-based IV proxy (backward-looking, less accurate)", file=sys.stderr)

            df['IV7'] = df['RV5'] * 1.2
            df['IV20'] = df['RV10'] * 1.2
            df['IV60'] = df['RV20'] * 1.2

        return df

    def _compute_iv_ranks(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute IV rank (percentile over rolling window).

        Walk-forward: At time t, compute percentile relative to PAST data only.
        """
        df = df.copy()

        # IV_rank_20 (based on IV20)
        df['IV_rank_20'] = self._rolling_percentile(df['IV20'], window=60)

        # IV_rank_60 (based on IV60)
        df['IV_rank_60'] = self._rolling_percentile(df['IV60'], window=90)

        return df

    def _compute_vvix(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute VVIX proxy (volatility of volatility).

        VVIX = rolling stdev of RV10 (measures volatility of volatility)
        """
        df = df.copy()

        # VVIX: 20-day stdev of RV10
        df['VVIX'] = df['RV10'].rolling(window=20, min_periods=10).std()

        # VVIX percentile (for scaling)
        df['VVIX_80pct'] = df['VVIX'].rolling(window=60, min_periods=20).quantile(0.8)

        return df

    def _compute_vvix_slope(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute rate of change in VVIX.

        Positive slope = vol-of-vol rising (unstable volatility)
        Negative slope = vol-of-vol falling (stable volatility)
        """
        df = df.copy()

        # VVIX slope (5-day linear regression slope)
        df['VVIX_slope'] = (
            df['VVIX']
            .rolling(window=5, min_periods=3)
            .apply(
                lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) >= 2 else 0,
                raw=False
            )
        )

        return df

    def _compute_skew_proxy(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute skew proxy until we have real IV surface.

        Real skew: IV_25D_put - IV_ATM
        Proxy: Use RV/ATR dynamics as crude measure of put/call imbalance

        This is a placeholder - will be replaced with real skew from options chain.
        """
        df = df.copy()

        # Use ATR5 if ATR10 not available
        atr_col = 'ATR10' if 'ATR10' in df.columns else 'ATR5'

        # Crude skew proxy: normalized ATR / RV ratio
        # Higher = more downside concern (wider range relative to volatility)
        skew_proxy = (df[atr_col] / df['close']) / (df['RV10'] + 1e-6)

        # Z-score vs recent history
        mean = skew_proxy.rolling(window=60, min_periods=20).mean()
        std = skew_proxy.rolling(window=60, min_periods=20).std()

        df['skew_z'] = (skew_proxy - mean) / (std + 1e-6)

        return df

    def _compute_helper_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute additional helper features."""
        df = df.copy()

        # 1-day absolute return (for short gamma detection)
        df['ret_1d'] = df['close'].pct_change().abs()

        return df

    def _rolling_percentile(self, series: pd.Series, window: int) -> pd.Series:
        """Compute rolling percentile rank (walk-forward).

        At time t, compute percentile of current value relative to
        PAST window data (excluding current point).

        Args:
            series: Input series
            window: Lookback window

        Returns:
            Percentile rank in [0, 1]
        """
        def percentile_rank(x):
            """Rank current value vs past values."""
            if len(x) < 2:
                return 0.5
            # Current value vs past values (x is numpy array)
            past = x[:-1]
            current = x[-1]
            return (past < current).sum() / len(past)

        return series.rolling(window=window, min_periods=10).apply(
            percentile_rank, raw=True  # raw=True passes numpy array
        )


def validate_profile_features(df: pd.DataFrame) -> dict:
    """Validate profile feature calculations.

    Args:
        df: DataFrame with profile features

    Returns:
        Dictionary with validation results
    """
    results = {
        'row_count': len(df),
        'date_range': (df['date'].min(), df['date'].max()) if 'date' in df.columns else ('N/A', 'N/A'),
        'missing_values': {},
        'feature_stats': {}
    }

    # Expected features
    feature_cols = [
        'IV7', 'IV20', 'IV60',
        'IV_rank_20', 'IV_rank_60',
        'VVIX', 'VVIX_80pct', 'VVIX_slope',
        'skew_z', 'ret_1d'
    ]

    for col in feature_cols:
        if col in df.columns:
            nan_count = df[col].isna().sum()
            results['missing_values'][col] = nan_count

            # Basic stats
            if nan_count < len(df):
                results['feature_stats'][col] = {
                    'mean': float(df[col].mean()),
                    'std': float(df[col].std()),
                    'min': float(df[col].min()),
                    'max': float(df[col].max())
                }

    return results
