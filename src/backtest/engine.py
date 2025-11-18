"""
Main rotation engine orchestrator.

This is the top-level interface that:
1. Loads data
2. Computes profile scores
3. Runs individual profile backtests
4. Calculates dynamic allocations
5. Aggregates portfolio P&L
6. Generates performance metrics
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Tuple
import sys
from pathlib import Path

# Import data and profile modules
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.data.loaders import load_spy_data
from src.profiles.detectors import ProfileDetectors

# Import profile backtests
from src.trading.profiles.profile_1 import run_profile_1_backtest
from src.trading.profiles.profile_2 import run_profile_2_backtest
from src.trading.profiles.profile_3 import run_profile_3_backtest
from src.trading.profiles.profile_4 import run_profile_4_backtest
from src.trading.profiles.profile_5 import run_profile_5_backtest
from src.trading.profiles.profile_6 import run_profile_6_backtest

# Import rotation logic
from .rotation import RotationAllocator
from .portfolio import PortfolioAggregator


class RotationEngine:
    """
    Main rotation engine orchestrator.

    Combines all components:
    - Data loading
    - Profile scoring
    - Individual profile backtests
    - Dynamic allocation
    - Portfolio aggregation
    - Performance metrics
    """

    def __init__(
        self,
        max_profile_weight: float = 0.40,
        min_profile_weight: float = 0.05,
        vix_scale_threshold: float = 0.30,
        vix_scale_factor: float = 0.5
    ):
        """
        Initialize rotation engine.

        Parameters:
        -----------
        max_profile_weight : float
            Maximum allocation to any single profile (default 40%)
        min_profile_weight : float
            Minimum allocation threshold (default 5%)
        vix_scale_threshold : float
            RV20 threshold for scaling down (default 30%)
        vix_scale_factor : float
            Scale factor when above threshold (default 0.5)
        """
        self.allocator = RotationAllocator(
            max_profile_weight=max_profile_weight,
            min_profile_weight=min_profile_weight,
            vix_scale_threshold=vix_scale_threshold,
            vix_scale_factor=vix_scale_factor
        )
        self.aggregator = PortfolioAggregator()

        # Profile configurations
        self.profile_configs = {
            'profile_1': {'threshold': 0.6, 'regimes': [1, 3]},  # LDG
            'profile_2': {'threshold': 0.5, 'regimes': [2, 5]},  # SDG
            'profile_3': {'threshold': 0.5, 'regimes': [3]},     # Charm
            'profile_4': {'threshold': 0.5, 'regimes': [1]},     # Vanna
            'profile_5': {'threshold': 0.4, 'regimes': [2]},     # Skew
            'profile_6': {'threshold': 0.6, 'regimes': [4]}      # VoV
        }

    def run(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        data: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Run complete rotation engine backtest.

        Parameters:
        -----------
        start_date : str, optional
            Start date (YYYY-MM-DD)
        end_date : str, optional
            End date (YYYY-MM-DD)
        data : pd.DataFrame, optional
            Pre-loaded data (if None, will load from file)

        Returns:
        --------
        results : dict
            Complete results package:
            - 'portfolio': Portfolio P&L DataFrame
            - 'allocations': Allocation weights over time
            - 'profile_results': Individual profile results
            - 'attribution': P&L attribution
            - 'metrics': Performance metrics
        """
        print("=" * 80)
        print("ROTATION ENGINE BACKTEST")
        print("=" * 80)
        print()

        # BUG FIX (2025-11-18): Agent #4/#10 found - components maintain state between runs
        # Reset all component state for fresh run
        self.allocator = RotationAllocator(
            max_profile_weight=self.allocator.max_profile_weight,
            min_profile_weight=self.allocator.min_profile_weight,
            vix_scale_threshold=self.allocator.vix_scale_threshold,
            vix_scale_factor=self.allocator.vix_scale_factor
        )
        self.aggregator = PortfolioAggregator()

        # Step 1: Load data
        print("Step 1: Loading data...")
        if data is None:
            data = load_spy_data()

        # Filter date range
        if start_date:
            start_ts = pd.to_datetime(start_date)
            # Handle both datetime.date and pd.Timestamp
            if hasattr(data['date'].iloc[0], 'date'):
                data = data[data['date'] >= start_ts]
            else:
                data = data[data['date'] >= start_ts.date()]
        if end_date:
            end_ts = pd.to_datetime(end_date)
            if hasattr(data['date'].iloc[0], 'date'):
                data = data[data['date'] <= end_ts]
            else:
                data = data[data['date'] <= end_ts.date()]

        # BUG FIX Round 8: Reset indices after filtering
        # Without reset_index(), the filtered DataFrame keeps original row numbers
        # Example: filtering to 2024-01-02 onwards gives rows 250-698 with indices 250-698
        # This causes warmup logic to fail (thinks row 250 is post-warmup when it's row 0 of filtered data)
        data = data.reset_index(drop=True)

        print(f"  Loaded {len(data)} days of data")
        print(f"  Date range: {data['date'].min()} to {data['date'].max()}")

        # Step 2: Compute profile scores
        print("\nStep 2: Computing profile scores...")
        detector = ProfileDetectors()
        data_with_scores = detector.compute_all_profiles(data)

        # Prepare profile scores DataFrame
        profile_scores = self._prepare_profile_scores(data_with_scores)
        print(f"  Computed scores for {len(profile_scores.columns) - 1} profiles")

        # Step 3: Run individual profile backtests
        print("\nStep 3: Running individual profile backtests...")
        # BUG FIX (2025-11-18): Pass data_with_scores instead of data to ensure regime data available
        # Agent #1/#10 found: profile backtests use data but allocations use data_with_scores
        profile_results = self._run_profile_backtests(data_with_scores, profile_scores)

        # Step 4: Calculate dynamic allocations
        print("\nStep 4: Calculating dynamic allocations...")
        # Rename profile columns to _score format BEFORE passing to allocator
        data_for_allocation = data_with_scores.copy()
        rename_map = {
            'profile_1_LDG': 'profile_1_score',
            'profile_2_SDG': 'profile_2_score',
            'profile_3_CHARM': 'profile_3_score',
            'profile_4_VANNA': 'profile_4_score',
            'profile_5_SKEW': 'profile_5_score',
            'profile_6_VOV': 'profile_6_score'
        }
        data_for_allocation = data_for_allocation.rename(columns=rename_map)

        allocations = self.allocator.allocate_daily(data_for_allocation)
        print(f"  Calculated allocations for {len(allocations)} days")

        # Step 5: Aggregate portfolio P&L
        print("\nStep 5: Aggregating portfolio P&L...")
        portfolio = self.aggregator.aggregate_pnl(allocations, profile_results)
        print(f"  Total portfolio P&L: ${portfolio['portfolio_pnl'].sum():,.2f}")
        print(f"  Final cumulative P&L: ${portfolio['cumulative_pnl'].iloc[-1]:,.2f}")

        # Step 6: Calculate attribution
        print("\nStep 6: Calculating attribution...")
        attribution_by_profile = self.aggregator.calculate_attribution(portfolio, by='profile')
        attribution_by_regime = self.aggregator.calculate_attribution(portfolio, by='regime')

        print("\n  Attribution by profile:")
        for _, row in attribution_by_profile.iterrows():
            print(f"    {row['profile']}: ${row['total_pnl']:,.2f} ({row['pnl_contribution_pct']:.1f}%)")

        # Step 7: Calculate rotation metrics
        print("\nStep 7: Calculating rotation metrics...")
        rotation_metrics = self.aggregator.calculate_rotation_frequency(portfolio)
        print(f"  Total rotations: {rotation_metrics['total_rotations']}")
        print(f"  Avg days between rotations: {rotation_metrics['avg_days_between']:.1f}")

        # Package results
        results = {
            'portfolio': portfolio,
            'allocations': allocations,
            'profile_results': profile_results,
            'attribution_by_profile': attribution_by_profile,
            'attribution_by_regime': attribution_by_regime,
            'rotation_metrics': rotation_metrics,
            'exposure_over_time': self.aggregator.calculate_exposure_over_time(portfolio),
            'regime_distribution': self.aggregator.calculate_regime_distribution(portfolio)
        }

        print("\n" + "=" * 80)
        print("ROTATION ENGINE BACKTEST COMPLETE")
        print("=" * 80)

        return results

    def _prepare_profile_scores(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Extract and rename profile score columns.

        Parameters:
        -----------
        data : pd.DataFrame
            Data with profile scores

        Returns:
        --------
        profile_scores : pd.DataFrame
            Clean DataFrame with date and profile scores
        """
        # Extract profile score columns
        profile_cols = [col for col in data.columns if col.startswith('profile_')]

        # Rename to standard format
        rename_map = {
            'profile_1_LDG': 'profile_1_score',
            'profile_2_SDG': 'profile_2_score',
            'profile_3_CHARM': 'profile_3_score',
            'profile_4_VANNA': 'profile_4_score',
            'profile_5_SKEW': 'profile_5_score',
            'profile_6_VOV': 'profile_6_score'
        }

        profile_scores = data[['date'] + profile_cols].copy()
        profile_scores = profile_scores.rename(columns=rename_map)

        return profile_scores

    def _run_profile_backtests(
        self,
        data: pd.DataFrame,
        profile_scores: pd.DataFrame
    ) -> Dict[str, pd.DataFrame]:
        """
        Run all 6 profile backtests.

        Parameters:
        -----------
        data : pd.DataFrame
            Market data
        profile_scores : pd.DataFrame
            Profile scores

        Returns:
        --------
        results : dict
            Mapping of profile names to backtest results
        """
        runners = {
            'profile_1': run_profile_1_backtest,
            'profile_2': run_profile_2_backtest,
            'profile_3': run_profile_3_backtest,
            'profile_4': run_profile_4_backtest,
            'profile_5': run_profile_5_backtest,
            'profile_6': run_profile_6_backtest
        }

        results = {}

        for profile_name, runner in runners.items():
            config = self.profile_configs[profile_name]

            print(f"  Running {profile_name}...")
            try:
                profile_results, trades = runner(
                    data=data,
                    profile_scores=profile_scores,
                    score_threshold=config['threshold'],
                    regime_filter=config['regimes']
                )

                results[profile_name] = profile_results
                print(f"    {len(trades)} trades executed")

            except Exception as e:
                import traceback
                print(f"    ❌ CRITICAL: {profile_name} failed: {e}")
                print("    " + "\n    ".join(traceback.format_exc().split('\n')))
                # BUG FIX (2025-11-18): Agent #2/#10 found - don't mask failures silently
                # RAISE error instead of creating dummy results - silent failures hide critical bugs
                raise RuntimeError(f"Profile {profile_name} backtest failed - fix before continuing") from e

        return results
