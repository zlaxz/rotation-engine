"""
Rotation logic: desirability scoring, normalization, and capital allocation.

This module implements the core rotation algorithm:
1. Calculate profile edge scores (from detectors)
2. Apply regime compatibility weights
3. Compute desirability = edge × compatibility
4. Normalize to sum to 1.0
5. Apply risk constraints (max 40%, min 5%, VIX scaling)
6. Generate allocation weights
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional


# Regime compatibility weights (from FRAMEWORK.md)
REGIME_COMPATIBILITY = {
    1: {  # Trend Up
        'profile_1': 1.0,  # Long-dated gamma - strong
        'profile_2': 0.0,  # Short-dated gamma - avoid
        'profile_3': 0.3,  # Charm - weak
        'profile_4': 1.0,  # Vanna - strong
        'profile_5': 0.0,  # Skew - avoid
        'profile_6': 0.2   # Vol-of-vol - weak
    },
    2: {  # Trend Down
        'profile_1': 0.0,  # Long-dated gamma - avoid
        'profile_2': 1.0,  # Short-dated gamma - strong
        'profile_3': 0.2,  # Charm - weak
        'profile_4': 0.0,  # Vanna - avoid
        'profile_5': 1.0,  # Skew - strong
        'profile_6': 0.6   # Vol-of-vol - moderate
    },
    3: {  # Compression
        'profile_1': 0.4,  # Long-dated gamma - moderate
        'profile_2': 0.0,  # Short-dated gamma - avoid
        'profile_3': 1.0,  # Charm - strong (pinned market)
        'profile_4': 1.0,  # Vanna - strong
        'profile_5': 0.0,  # Skew - avoid
        'profile_6': 0.1   # Vol-of-vol - weak
    },
    4: {  # Breaking Vol
        'profile_1': 0.0,  # Long-dated gamma - avoid
        'profile_2': 0.4,  # Short-dated gamma - moderate
        'profile_3': 0.0,  # Charm - avoid (will blow up)
        'profile_4': 0.0,  # Vanna - avoid
        'profile_5': 1.0,  # Skew - strong (tail risk)
        'profile_6': 1.0   # Vol-of-vol - strong
    },
    5: {  # Choppy
        'profile_1': 0.2,  # Long-dated gamma - weak
        'profile_2': 1.0,  # Short-dated gamma - strong (scalp chop)
        'profile_3': 0.6,  # Charm - conditional
        'profile_4': 0.3,  # Vanna - weak
        'profile_5': 0.4,  # Skew - moderate
        'profile_6': 0.1   # Vol-of-vol - weak
    },
    6: {  # Event / Catalyst
        'profile_1': 0.4,
        'profile_2': 0.6,
        'profile_3': 0.2,
        'profile_4': 0.2,
        'profile_5': 0.8,
        'profile_6': 1.0
    }
}


class RotationAllocator:
    """
    Manages dynamic capital allocation across profiles based on regime and desirability.

    Process:
    1. Receive daily profile scores [0,1] for each profile
    2. Receive current regime label
    3. Calculate desirability = score × regime_compatibility
    4. Normalize weights to sum to 1.0
    5. Apply constraints (max/min, VIX scaling)
    6. Return allocation weights
    """

    def __init__(
        self,
        max_profile_weight: float = 0.40,  # Max 40% per profile
        min_profile_weight: float = 0.05,  # Min 5% threshold
        vix_scale_threshold: float = 0.30,  # Scale down if RV20 > 30%
        vix_scale_factor: float = 0.5      # Scale to 50% if above threshold
    ):
        """
        Initialize rotation allocator.

        Parameters:
        -----------
        max_profile_weight : float
            Maximum allocation to any single profile (default 40%)
        min_profile_weight : float
            Minimum allocation threshold - ignore below this (default 5%)
        vix_scale_threshold : float
            RV20 threshold above which to scale down exposure (default 30%)
        vix_scale_factor : float
            Factor to scale exposure when above threshold (default 0.5 = 50%)
        """
        self.max_profile_weight = max_profile_weight
        self.min_profile_weight = min_profile_weight
        self.vix_scale_threshold = vix_scale_threshold
        self.vix_scale_factor = vix_scale_factor

    def calculate_desirability(
        self,
        profile_scores: Dict[str, float],
        regime: int
    ) -> Dict[str, float]:
        """
        Calculate desirability scores = profile_score × regime_compatibility.

        Parameters:
        -----------
        profile_scores : dict
            Dictionary mapping profile names to scores [0,1]
            e.g., {'profile_1': 0.75, 'profile_2': 0.3, ...}
        regime : int
            Current regime label (1-5)

        Returns:
        --------
        desirability : dict
            Dictionary mapping profile names to desirability scores
        """
        compatibility = REGIME_COMPATIBILITY.get(regime)
        if compatibility is None:
            raise ValueError(f"Unknown regime {regime}. Valid regimes: {list(REGIME_COMPATIBILITY.keys())}")

        desirability = {}
        for profile_name, score in profile_scores.items():
            if profile_name in compatibility:
                desirability[profile_name] = score * compatibility[profile_name]
            else:
                # Profile not in compatibility matrix - assign 0
                desirability[profile_name] = 0.0

        return desirability

    def normalize_weights(
        self,
        desirability: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Normalize desirability scores to sum to 1.0.

        Parameters:
        -----------
        desirability : dict
            Raw desirability scores

        Returns:
        --------
        weights : dict
            Normalized weights summing to 1.0
        """
        total = sum(desirability.values())

        if total == 0:
            # No desirable profiles - return zeros
            return {k: 0.0 for k in desirability.keys()}

        return {k: v / total for k, v in desirability.items()}

    def apply_constraints(
        self,
        weights: Dict[str, float],
        rv20: float,
        regime: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Apply allocation constraints with correct precedence:
        1. Apply hard cap (max_profile_weight) with redistribution
        2. Zero out weights below minimum threshold (accepts sum < 1.0)
        3. Apply VIX scaling (scales down, does NOT renormalize - holds cash)

        Returns weights that satisfy:
        - No weight > max_profile_weight (HARD CONSTRAINT - never violated)
        - All weights >= 0
        - Sum(weights) <= 1.0 (may hold cash after min threshold or VIX scaling)
        - VIX scaling reduces exposure without renormalization (risk management)

        Parameters:
        -----------
        weights : dict
            Normalized weights
        rv20 : float
            20-day realized volatility (annualized, e.g., 0.25 = 25%)
        regime : int, optional
            Current regime (unused, kept for API compatibility)

        Returns:
        --------
        constrained_weights : dict
            Weights after applying all constraints
        """
        # Convert to array for easier manipulation
        profile_names = list(weights.keys())
        weight_array = np.array([weights[p] for p in profile_names])

        # Step 1: Apply hard cap with redistribution FIRST
        # This ensures no weight exceeds max_cap
        weight_array = self._iterative_cap_and_redistribute(
            weight_array,
            self.max_profile_weight
        )

        # Step 2: Apply minimum threshold (zero out noise)
        # This happens AFTER capping, and we accept sum < 1.0 (cash position)
        weight_array[weight_array < self.min_profile_weight] = 0.0

        # Step 3: Apply VIX scaling (reduce exposure in high vol)
        # Scale down ALL weights proportionally, accept sum < 1.0 (hold cash)
        # DO NOT renormalize after scaling - that would violate cap constraint
        if rv20 > self.vix_scale_threshold:
            weight_array = weight_array * self.vix_scale_factor
            # NOTE: No renormalization - we hold cash in high vol environments

        # Convert back to dict
        constrained = {name: weight for name, weight in zip(profile_names, weight_array)}

        return constrained

    def _iterative_cap_and_redistribute(
        self,
        weights: np.ndarray,
        max_cap: float,
        max_iterations: int = 100
    ) -> np.ndarray:
        """
        Redistribute weight from capped profiles to uncapped profiles.

        Algorithm:
        1. Cap any weight > max_cap
        2. Take excess weight, redistribute to uncapped profiles proportionally
        3. Repeat until converged or all profiles capped

        If all profiles capped, final sum may be < 1.0 (cash position).

        Parameters:
        -----------
        weights : np.ndarray
            Array of weights to constrain
        max_cap : float
            Maximum weight for any single profile
        max_iterations : int
            Maximum number of redistribution iterations

        Returns:
        --------
        constrained_weights : np.ndarray
            Weights after capping and redistribution
        """
        weights = weights.copy()
        # Track which profiles have been capped (can't receive redistribution)
        capped = np.zeros(len(weights), dtype=bool)

        for iteration in range(max_iterations):
            # Identify violations
            violations = weights > max_cap

            if not violations.any():
                # Converged - all weights within cap
                break

            # Cap violations and calculate excess
            excess = (weights[violations] - max_cap).sum()
            weights[violations] = max_cap
            capped[violations] = True  # Mark as capped

            # Find uncapped profiles with non-zero weight
            # Must NOT have been capped in this or previous iterations
            uncapped = ~capped & (weights > 0)

            if not uncapped.any():
                # All profiles capped, can't redistribute
                # Accept sum < 1.0 (holding cash)
                break

            # Redistribute excess proportionally to uncapped profiles
            uncapped_sum = weights[uncapped].sum()
            if uncapped_sum > 0:
                redistribution = excess * (weights[uncapped] / uncapped_sum)
                weights[uncapped] += redistribution
            else:
                # Edge case: uncapped profiles have zero weight
                break

        # Ensure sum <= 1.0 (should already be true, but safety check)
        total = weights.sum()
        if total > 1.0 + 1e-9:  # Allow tiny floating point error
            weights = weights / total

        return weights

    def allocate(
        self,
        profile_scores: Dict[str, float],
        regime: int,
        rv20: float
    ) -> Dict[str, float]:
        """
        Full allocation pipeline: scores → desirability → weights → constraints.

        Parameters:
        -----------
        profile_scores : dict
            Profile edge scores [0,1] from detectors
        regime : int
            Current regime label (1-5)
        rv20 : float
            20-day realized volatility (for VIX scaling)

        Returns:
        --------
        allocation_weights : dict
            Final allocation weights for each profile
        """
        # Step 1: Calculate desirability
        desirability = self.calculate_desirability(profile_scores, regime)

        # Step 2: Normalize to sum to 1.0
        weights = self.normalize_weights(desirability)

        # Step 3: Apply constraints
        final_weights = self.apply_constraints(weights, rv20)

        return final_weights

    def allocate_daily(
        self,
        data: pd.DataFrame,
        profile_score_cols: Optional[list] = None
    ) -> pd.DataFrame:
        """
        Calculate allocation weights for entire dataset (day by day).

        Parameters:
        -----------
        data : pd.DataFrame
            Must contain:
            - 'regime' column (regime labels)
            - 'RV20' column (20-day realized vol)
            - profile score columns (e.g., 'profile_1_score', ...)
        profile_score_cols : list, optional
            List of profile score column names
            If None, auto-detect columns starting with 'profile_' and ending with '_score'

        Returns:
        --------
        allocations : pd.DataFrame
            DataFrame with columns:
            - 'date'
            - 'regime'
            - 'profile_1_weight', 'profile_2_weight', ...
        """
        # Auto-detect profile score columns if not provided
        if profile_score_cols is None:
            profile_score_cols = [
                col for col in data.columns
                if col.startswith('profile_') and col.endswith('_score')
            ]

        # Validate required columns
        required_cols = ['date', 'regime', 'RV20'] + profile_score_cols
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # Calculate daily allocations
        allocations = []

        for idx, row in data.iterrows():
            date = row['date']
            regime = int(row['regime'])
            rv20 = row['RV20']

            # Extract profile scores
            profile_scores = {}
            for col in profile_score_cols:
                # Convert 'profile_1_score' → 'profile_1'
                profile_name = col.replace('_score', '')
                score_value = row[col]
                # Handle NaN/None - RAISE ERROR instead of silent 0
                if pd.isna(score_value):
                    # Check if we're in warmup period
                    row_index = idx
                    if row_index < 90:  # Warmup period
                        # NaN in warmup is expected - skip allocation
                        raise ValueError(
                            f"Cannot allocate capital during warmup period (row {row_index}). "
                            f"Profile score {col} is NaN. "
                            f"Call allocate_weights() with data starting after warmup."
                        )
                    else:
                        # NaN post-warmup is CRITICAL ERROR
                        raise ValueError(
                            f"CRITICAL: Profile score {col} is NaN at date {date} (row {row_index}). "
                            f"This indicates missing/corrupt data. NaN must not reach allocation logic. "
                            f"Check data quality and feature engineering."
                        )
                else:
                    profile_scores[profile_name] = score_value

            # Calculate allocation weights
            weights = self.allocate(profile_scores, regime, rv20)

            # Build result row
            result = {'date': date, 'regime': regime}
            for profile_name, weight in weights.items():
                result[f'{profile_name}_weight'] = weight

            allocations.append(result)

        return pd.DataFrame(allocations)
