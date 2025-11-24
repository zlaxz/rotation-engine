"""
Portfolio P&L aggregation across multiple profiles.

This module combines individual profile P&L series into a single portfolio,
weighted by dynamic allocation weights.
"""

import pandas as pd
from typing import Dict, List


class PortfolioAggregator:
    """
    Aggregates profile P&L into portfolio-level metrics.

    Takes daily allocation weights and profile P&L series, combines them into
    weighted portfolio P&L, and tracks attribution.
    """

    def __init__(self, starting_capital: float = 1_000_000.0):
        """Initialize portfolio aggregator."""
        self.starting_capital = starting_capital

    def aggregate_pnl(
        self,
        allocations: pd.DataFrame,
        profile_results: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Aggregate individual profile P&L into weighted portfolio P&L.

        Parameters:
        -----------
        allocations : pd.DataFrame
            Daily allocation weights with columns:
            - 'date'
            - 'regime'
            - 'profile_1_weight', 'profile_2_weight', ...
        profile_results : dict
            Dictionary mapping profile names to their backtest results
            Each DataFrame must have 'date' and 'daily_pnl' columns

        Returns:
        --------
        portfolio : pd.DataFrame
            Aggregated portfolio with columns:
            - 'date'
            - 'regime'
            - 'profile_1_pnl', 'profile_2_pnl', ... (weighted P&L by profile)
            - 'portfolio_pnl' (total weighted P&L)
            - 'cumulative_pnl'
            - 'profile_1_weight', 'profile_2_weight', ... (weights)
        """
        # Start with allocations
        portfolio = allocations.copy()
        portfolio['portfolio_return'] = 0.0

        return_contrib_cols = {}

        for profile_name, results in profile_results.items():
            weight_col = f'{profile_name}_weight'
            pnl_col = f'{profile_name}_pnl'
            return_col = f'{profile_name}_return'

            # Merge profile results (require daily_return for normalization)
            if 'daily_return' not in results.columns:
                raise ValueError(f"{profile_name} results missing 'daily_return' column.")

            profile_daily = results[['date', 'daily_return', 'daily_pnl']].copy()
            profile_daily = profile_daily.rename(columns={
                'daily_return': f'{profile_name}_daily_return',
                'daily_pnl': f'{profile_name}_daily_pnl'
            })

            portfolio = portfolio.merge(profile_daily, on='date', how='left')

            # fillna(0) here is ACCEPTABLE - it's for left join alignment
            # Days where profile was not active (weight=0) will have NaN returns
            # Filling with 0 is correct: no position = no return
            portfolio[f'{profile_name}_daily_return'] = portfolio[f'{profile_name}_daily_return'].fillna(0.0)
            portfolio[f'{profile_name}_daily_pnl'] = portfolio[f'{profile_name}_daily_pnl'].fillna(0.0)

            weight_series = portfolio[weight_col] if weight_col in portfolio.columns else 0.0
            if isinstance(weight_series, pd.Series):
                # fillna(0) acceptable here - missing weight means no allocation
                weight_series = weight_series.fillna(0.0)

            portfolio[return_col] = weight_series * portfolio[f'{profile_name}_daily_return']
            return_contrib_cols[profile_name] = return_col

        # Aggregate portfolio returns
        if return_contrib_cols:
            portfolio['portfolio_return'] = portfolio[list(return_contrib_cols.values())].sum(axis=1)

        # Compute capital trajectory iteratively to avoid divide-by-zero on -100% days
        prev_values = []
        curr_values = []
        daily_pnls = []
        prev_value = self.starting_capital

        for ret in portfolio['portfolio_return']:
            prev_values.append(prev_value)
            pnl = prev_value * ret
            daily_pnls.append(pnl)
            prev_value = prev_value + pnl
            curr_values.append(prev_value)

        portfolio['portfolio_prev_value'] = prev_values
        portfolio['portfolio_pnl'] = daily_pnls
        portfolio['portfolio_value'] = curr_values
        portfolio['cumulative_pnl'] = portfolio['portfolio_pnl'].cumsum()

        # Convert per-profile return contributions into dollar P&L
        for profile_name, return_col in return_contrib_cols.items():
            pnl_col = f'{profile_name}_pnl'
            portfolio[pnl_col] = portfolio['portfolio_prev_value'] * portfolio[return_col]

        return portfolio

    def calculate_attribution(
        self,
        portfolio: pd.DataFrame,
        by: str = 'profile'
    ) -> pd.DataFrame:
        """
        Calculate P&L attribution breakdown.

        Parameters:
        -----------
        portfolio : pd.DataFrame
            Portfolio DataFrame from aggregate_pnl()
        by : str
            Attribution dimension: 'profile' or 'regime'

        Returns:
        --------
        attribution : pd.DataFrame
            Attribution summary
        """
        if by == 'profile':
            return self._attribution_by_profile(portfolio)
        elif by == 'regime':
            return self._attribution_by_regime(portfolio)
        else:
            raise ValueError(f"Unknown attribution type: {by}")

    def _attribution_by_profile(self, portfolio: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate P&L attribution by profile.

        Returns:
        --------
        attribution : pd.DataFrame
            Columns: profile, total_pnl, mean_daily_pnl, pnl_contribution
        """
        # Identify profile P&L columns (exclude intermediate daily columns)
        # FIXED Round 6: Exclude '_daily_pnl' columns to avoid double-counting
        pnl_cols = [col for col in portfolio.columns
                    if col.endswith('_pnl')
                    and '_daily_' not in col
                    and col != 'portfolio_pnl'
                    and col != 'cumulative_pnl']

        attribution = []
        total_portfolio_pnl = portfolio['portfolio_pnl'].sum()

        for pnl_col in pnl_cols:
            profile_name = pnl_col.replace('_pnl', '')
            total_pnl = portfolio[pnl_col].sum()
            mean_daily = portfolio[pnl_col].mean()

            # Contribution to total P&L
            contribution = (total_pnl / total_portfolio_pnl * 100) if total_portfolio_pnl != 0 else 0

            attribution.append({
                'profile': profile_name,
                'total_pnl': total_pnl,
                'mean_daily_pnl': mean_daily,
                'pnl_contribution_pct': contribution
            })

        return pd.DataFrame(attribution)

    def _attribution_by_regime(self, portfolio: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate P&L attribution by regime.

        Returns:
        --------
        attribution : pd.DataFrame
            Columns: regime, days, total_pnl, mean_daily_pnl
        """
        attribution = portfolio.groupby('regime').agg({
            'portfolio_pnl': ['count', 'sum', 'mean', 'std']
        }).reset_index()

        attribution.columns = ['regime', 'days', 'total_pnl', 'mean_daily_pnl', 'std_daily_pnl']

        return attribution

    def calculate_exposure_over_time(
        self,
        portfolio: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate profile exposure (weights) over time.

        Parameters:
        -----------
        portfolio : pd.DataFrame
            Portfolio DataFrame from aggregate_pnl()

        Returns:
        --------
        exposure : pd.DataFrame
            Columns: date, profile_1_weight, profile_2_weight, ...
        """
        weight_cols = [col for col in portfolio.columns if col.endswith('_weight')]
        return portfolio[['date'] + weight_cols].copy()

    def calculate_regime_distribution(
        self,
        portfolio: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate distribution of time spent in each regime.

        Returns:
        --------
        distribution : pd.DataFrame
            Columns: regime, days, percentage
        """
        regime_counts = portfolio['regime'].value_counts().reset_index()
        regime_counts.columns = ['regime', 'days']
        regime_counts['percentage'] = regime_counts['days'] / len(portfolio) * 100
        regime_counts = regime_counts.sort_values('regime')

        return regime_counts

    def calculate_rotation_frequency(
        self,
        portfolio: pd.DataFrame,
        threshold: float = 0.05
    ) -> Dict[str, float]:
        """
        Calculate how often allocations change (rotation frequency).

        Parameters:
        -----------
        portfolio : pd.DataFrame
            Portfolio DataFrame
        threshold : float
            Minimum weight change to count as rotation

        Returns:
        --------
        metrics : dict
            - 'total_rotations': Number of rotation events
            - 'avg_days_between': Average days between rotations
            - 'rotation_rate_pct': Percentage of days with rotation
        """
        weight_cols = [col for col in portfolio.columns if col.endswith('_weight')]

        # Calculate weight changes
        weight_changes = portfolio[weight_cols].diff().abs()

        # Count days with material rotation
        rotation_days = (weight_changes > threshold).any(axis=1).sum()

        total_days = len(portfolio)
        avg_days_between = total_days / rotation_days if rotation_days > 0 else total_days

        return {
            'total_rotations': rotation_days,
            'avg_days_between': avg_days_between,
            'rotation_rate_pct': rotation_days / total_days * 100
        }
