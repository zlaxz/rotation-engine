"""
True rotation backtest engine with multi-position portfolio.

This replaces the old architecture of 6 independent backtests + post-hoc weighting
with a unified daily loop that:
1. Classifies regime
2. Scores all 6 profiles
3. Allocates capital across profiles
4. Manages 6 simultaneous positions
5. Rebalances on regime change or allocation shift
6. Calculates portfolio-level P&L and Greeks

SINGLE SOURCE OF TRUTH: Position-based P&L accounting
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Callable, List
from datetime import datetime, date, timedelta
from pathlib import Path

from .portfolio_new import Portfolio
from .rotation import RotationAllocator
from src.regimes.classifier import RegimeClassifier
from src.profiles.detectors import ProfileDetectors
from src.trading.trade import Trade, TradeLeg
from src.trading.execution import ExecutionModel, get_vix_proxy
from src.data.polygon_options import PolygonOptionsLoader


class RotationBacktestEngine:
    """
    True rotation backtest engine.

    Manages unified daily loop with multi-position portfolio, realistic
    execution modeling, and single source of truth P&L accounting.
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000.0,
        max_profile_weight: float = 0.40,
        min_profile_weight: float = 0.05,
        rebalance_threshold: float = 0.05,
        vix_scale_threshold: float = 0.30,
        vix_scale_factor: float = 0.5,
        polygon_data_root: Optional[str] = None,
        use_real_options_data: bool = True
    ):
        """
        Initialize rotation backtest engine.

        Parameters:
        -----------
        initial_capital : float
            Starting portfolio capital
        max_profile_weight : float
            Maximum allocation to single profile (40%)
        min_profile_weight : float
            Minimum allocation threshold (5%)
        rebalance_threshold : float
            Minimum allocation change to trigger rebalance (5%)
        vix_scale_threshold : float
            RV20 threshold for scaling down exposure (30%)
        vix_scale_factor : float
            Scale factor when above threshold (0.5 = 50%)
        polygon_data_root : str, optional
            Path to Polygon options data
        use_real_options_data : bool
            Use real Polygon data (required for production)
        """
        # Core components
        self.portfolio = Portfolio(initial_capital=initial_capital)
        self.allocator = RotationAllocator(
            max_profile_weight=max_profile_weight,
            min_profile_weight=min_profile_weight,
            vix_scale_threshold=vix_scale_threshold,
            vix_scale_factor=vix_scale_factor
        )
        self.regime_classifier = RegimeClassifier()
        self.profile_detectors = ProfileDetectors()

        # Execution
        self.execution_model = ExecutionModel()
        self.rebalance_threshold = rebalance_threshold

        # Options data
        self.use_real_options_data = use_real_options_data
        if use_real_options_data:
            self.polygon_loader = PolygonOptionsLoader(
                data_root=polygon_data_root or "/Volumes/VelocityData/polygon_downloads/us_options_opra/day_aggs_v1"
            )
        else:
            self.polygon_loader = None

        # Results tracking
        self.daily_results = []
        self.rebalance_log = []

    def run(
        self,
        data: pd.DataFrame,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        trade_constructors: Optional[Dict[int, Callable]] = None
    ) -> Dict:
        """
        Run complete rotation backtest.

        Parameters:
        -----------
        data : pd.DataFrame
            Market data with OHLCV, regime, profile scores
        start_date : str, optional
            Start date (YYYY-MM-DD)
        end_date : str, optional
            End date (YYYY-MM-DD)
        trade_constructors : dict, optional
            {profile_id: constructor_fn} for building trades
            If None, uses default constructors

        Returns:
        --------
        results : dict
            Complete results package:
            - 'portfolio': Portfolio object
            - 'equity_curve': Daily equity curve
            - 'daily_results': Daily P&L, allocations, Greeks
            - 'closed_positions': Closed position summary
            - 'rebalance_log': Rebalancing actions log
            - 'metrics': Performance metrics
        """
        print("=" * 80)
        print("ROTATION BACKTEST ENGINE (True Multi-Position)")
        print("=" * 80)
        print()

        # Filter date range
        df = self._filter_dates(data, start_date, end_date)
        print(f"Backtest period: {df['date'].min()} to {df['date'].max()}")
        print(f"Days: {len(df)}")
        print(f"Initial capital: ${self.portfolio.initial_capital:,.0f}")
        print()

        # Classify regimes if not present
        if 'regime' not in df.columns:
            print("Classifying regimes...")
            df = self.regime_classifier.classify_period(df)

        # Compute profile scores if not present
        profile_cols = [f'profile_{i}_score' for i in range(1, 7)]
        if not all(col in df.columns for col in profile_cols):
            print("Computing profile scores...")
            df = self._compute_profile_scores(df)

        # Set default trade constructors if not provided
        if trade_constructors is None:
            trade_constructors = self._get_default_trade_constructors()

        print("Running daily simulation loop...")
        print()

        # Daily simulation loop
        for idx, row in df.iterrows():
            self._simulate_day(row, trade_constructors)

            # Progress reporting
            if idx % 100 == 0:
                progress_pct = (idx / len(df)) * 100
                equity = self.portfolio.get_equity()
                num_pos = len(self.portfolio.positions)
                print(f"  {progress_pct:5.1f}% | {row['date']} | "
                      f"Equity: ${equity:,.0f} | Positions: {num_pos}")

        # Close any remaining positions at end
        self._close_all_positions(df.iloc[-1])

        print()
        print("Backtest complete!")
        print(f"Final equity: ${self.portfolio.get_equity():,.0f}")
        print(f"Total P&L: ${self.portfolio.get_total_pnl():,.0f}")
        print(f"Total trades: {len(self.portfolio.closed_positions)}")
        print(f"Rebalance events: {len(self.rebalance_log)}")
        print()

        # Package results
        results = {
            'portfolio': self.portfolio,
            'equity_curve': self.portfolio.get_equity_curve(),
            'daily_results': pd.DataFrame(self.daily_results),
            'closed_positions': self.portfolio.get_closed_positions_summary(),
            'rebalance_log': pd.DataFrame(self.rebalance_log),
            'metrics': self._calculate_metrics()
        }

        print("=" * 80)

        return results

    def _simulate_day(
        self,
        row: pd.Series,
        trade_constructors: Dict[int, Callable]
    ):
        """
        Simulate single day of trading.

        1. Extract current market conditions
        2. Get current regime and profile scores
        3. Calculate target allocations
        4. Rebalance portfolio if needed
        5. Mark to market all positions
        6. Record daily results
        """
        current_date = row['date']
        if isinstance(current_date, pd.Timestamp):
            current_date = current_date.date()

        spot = row['close']
        regime = int(row['regime'])
        rv20 = row.get('RV20', 0.20)

        # Extract profile scores
        profile_scores = {}
        for i in range(1, 7):
            # Handle both naming conventions
            score_col = f'profile_{i}_score'
            alt_names = [
                f'profile_{i}_LDG', f'profile_{i}_SDG', f'profile_{i}_CHARM',
                f'profile_{i}_VANNA', f'profile_{i}_SKEW', f'profile_{i}_VOV'
            ]

            score = None
            if score_col in row.index:
                score = row[score_col]
            else:
                for alt_name in alt_names:
                    if alt_name in row.index:
                        score = row[alt_name]
                        break

            if score is None or pd.isna(score):
                # Warmup period - skip allocation
                if len(self.daily_results) < 90:
                    return
                else:
                    raise ValueError(
                        f"Profile {i} score is NaN at {current_date}. "
                        "Data corruption detected."
                    )

            profile_scores[f'profile_{i}'] = score

        # Calculate target allocations
        target_allocations = {}
        for i in range(1, 7):
            target_allocations[i] = self.allocator.allocate(
                profile_scores=profile_scores,
                regime=regime,
                rv20=rv20
            ).get(f'profile_{i}', 0.0)

        # Check if rebalancing needed
        current_allocations = self.portfolio.get_allocations()
        needs_rebalance = self._check_rebalance_needed(
            current_allocations,
            target_allocations
        )

        # Rebalance if needed
        if needs_rebalance:
            self._rebalance_portfolio(
                target_allocations=target_allocations,
                current_date=current_date,
                row=row,
                trade_constructors=trade_constructors
            )

        # Mark to market all positions
        option_prices_by_profile = self._get_current_option_prices(row)
        total_equity = self.portfolio.mark_to_market(
            current_date=current_date,
            option_prices_by_profile=option_prices_by_profile
        )

        # Calculate daily P&L
        if len(self.daily_results) > 0:
            prev_equity = self.daily_results[-1]['total_equity']
            daily_pnl = total_equity - prev_equity
            daily_return = daily_pnl / prev_equity if prev_equity > 0 else 0.0
        else:
            daily_pnl = total_equity - self.portfolio.initial_capital
            daily_return = daily_pnl / self.portfolio.initial_capital

        # Get portfolio Greeks
        greeks = self.portfolio.get_portfolio_greeks()

        # Record daily results
        daily_record = {
            'date': current_date,
            'regime': regime,
            'spot': spot,
            'rv20': rv20,
            'total_equity': total_equity,
            'cash': self.portfolio.cash,
            'daily_pnl': daily_pnl,
            'daily_return': daily_return,
            'realized_pnl': self.portfolio.get_realized_pnl(),
            'unrealized_pnl': self.portfolio.get_unrealized_pnl(),
            'num_positions': len(self.portfolio.positions),
            'delta': greeks['delta'],
            'gamma': greeks['gamma'],
            'theta': greeks['theta'],
            'vega': greeks['vega']
        }

        # Add per-profile allocations
        for i in range(1, 7):
            daily_record[f'profile_{i}_allocation'] = current_allocations.get(i, 0.0)
            daily_record[f'profile_{i}_target'] = target_allocations.get(i, 0.0)

        self.daily_results.append(daily_record)

    def _check_rebalance_needed(
        self,
        current: Dict[int, float],
        target: Dict[int, float]
    ) -> bool:
        """Check if any allocation change exceeds rebalance threshold."""
        for profile_id in range(1, 7):
            curr_pct = current.get(profile_id, 0.0)
            tgt_pct = target.get(profile_id, 0.0)

            if abs(tgt_pct - curr_pct) > self.rebalance_threshold:
                return True

        return False

    def _rebalance_portfolio(
        self,
        target_allocations: Dict[int, float],
        current_date: date,
        row: pd.Series,
        trade_constructors: Dict[int, Callable]
    ):
        """
        Rebalance portfolio to match target allocations.

        Closes old positions and opens new positions.
        """
        current_allocations = self.portfolio.get_allocations()

        for profile_id in range(1, 7):
            curr_pct = current_allocations.get(profile_id, 0.0)
            tgt_pct = target_allocations.get(profile_id, 0.0)

            allocation_change = abs(tgt_pct - curr_pct)

            if allocation_change < self.rebalance_threshold:
                continue

            # Close existing position if present
            if profile_id in self.portfolio.positions:
                position = self.portfolio.positions[profile_id]
                exit_prices = self._get_exit_prices(position, row)

                realized_pnl = self.portfolio.close_position(
                    profile_id=profile_id,
                    exit_prices=exit_prices,
                    exit_date=current_date,
                    exit_reason="Rebalance"
                )

                self.rebalance_log.append({
                    'date': current_date,
                    'action': 'close',
                    'profile_id': profile_id,
                    'old_allocation': curr_pct,
                    'new_allocation': tgt_pct,
                    'realized_pnl': realized_pnl
                })

            # Open new position if target >= minimum
            if tgt_pct >= self.min_profile_weight:
                # Construct trade
                constructor = trade_constructors.get(profile_id)
                if constructor is None:
                    continue

                trade = constructor(row, f"R{row['regime']}_P{profile_id}")

                # Get entry prices
                entry_prices = self._get_entry_prices(trade, row)
                trade.entry_prices = entry_prices
                trade.__post_init__()

                # Calculate Greeks
                vix_proxy = get_vix_proxy(row.get('RV20', 0.20))
                trade.calculate_greeks(
                    underlying_price=row['close'],
                    current_date=current_date,
                    implied_vol=vix_proxy,
                    risk_free_rate=0.05
                )

                # Open position
                self.portfolio.open_position(
                    profile_id=profile_id,
                    trade=trade,
                    allocation_pct=tgt_pct,
                    entry_date=current_date
                )

                self.rebalance_log.append({
                    'date': current_date,
                    'action': 'open',
                    'profile_id': profile_id,
                    'old_allocation': curr_pct,
                    'new_allocation': tgt_pct,
                    'entry_cost': trade.entry_cost
                })

    def _close_all_positions(self, final_row: pd.Series):
        """Close all remaining positions at end of backtest."""
        final_date = final_row['date']
        if isinstance(final_date, pd.Timestamp):
            final_date = final_date.date()

        profile_ids = list(self.portfolio.positions.keys())

        for profile_id in profile_ids:
            position = self.portfolio.positions[profile_id]
            exit_prices = self._get_exit_prices(position, final_row)

            self.portfolio.close_position(
                profile_id=profile_id,
                exit_prices=exit_prices,
                exit_date=final_date,
                exit_reason="End of backtest"
            )

    def _get_entry_prices(self, trade: Trade, row: pd.Series) -> Dict[int, float]:
        """Get entry execution prices (pay ask for longs, receive bid for shorts)."""
        # Placeholder - needs Polygon integration
        # For now, return placeholder prices
        entry_prices = {}
        for i, leg in enumerate(trade.legs):
            # TODO: Get real bid/ask from Polygon
            mid_price = self._estimate_option_price(leg, row['close'], row)
            if leg.quantity > 0:
                entry_prices[i] = mid_price * 1.01  # Longs pay ask (1% spread)
            else:
                entry_prices[i] = mid_price * 0.99  # Shorts receive bid

        return entry_prices

    def _get_exit_prices(self, position, row: pd.Series) -> Dict[int, float]:
        """Get exit execution prices (receive bid for longs, pay ask for shorts)."""
        exit_prices = {}
        for i, leg in enumerate(position.trade.legs):
            mid_price = self._estimate_option_price(leg, row['close'], row)
            if leg.quantity > 0:
                exit_prices[i] = mid_price * 0.99  # Longs exit at bid
            else:
                exit_prices[i] = mid_price * 1.01  # Shorts exit at ask

        return exit_prices

    def _get_current_option_prices(self, row: pd.Series) -> Dict[int, Dict[int, float]]:
        """Get current mid prices for all active positions."""
        option_prices_by_profile = {}

        for profile_id, position in self.portfolio.positions.items():
            leg_prices = {}
            for i, leg in enumerate(position.trade.legs):
                mid_price = self._estimate_option_price(leg, row['close'], row)
                leg_prices[i] = mid_price

            option_prices_by_profile[profile_id] = leg_prices

        return option_prices_by_profile

    def _estimate_option_price(self, leg: TradeLeg, spot: float, row: pd.Series) -> float:
        """
        Estimate option price (placeholder - needs Polygon integration).

        TODO: Integrate with PolygonOptionsLoader for real bid/ask/mid prices.
        """
        # Simplified pricing
        iv = row.get('RV20', 0.20) * 1.2
        dte = max(leg.dte, 1)

        # Intrinsic
        if leg.option_type == 'call':
            intrinsic = max(0, spot - leg.strike)
        else:
            intrinsic = max(0, leg.strike - spot)

        # Time value
        time_value = spot * iv * np.sqrt(dte / 365.0)
        moneyness = abs(spot - leg.strike) / spot
        time_value *= np.exp(-10 * moneyness)

        return intrinsic + time_value

    def _compute_profile_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute profile scores if not present."""
        df_with_scores = self.profile_detectors.compute_all_profiles(df)

        # Rename to _score format
        rename_map = {
            'profile_1_LDG': 'profile_1_score',
            'profile_2_SDG': 'profile_2_score',
            'profile_3_CHARM': 'profile_3_score',
            'profile_4_VANNA': 'profile_4_score',
            'profile_5_SKEW': 'profile_5_score',
            'profile_6_VOV': 'profile_6_score'
        }
        df_with_scores = df_with_scores.rename(columns=rename_map)

        return df_with_scores

    def _filter_dates(
        self,
        df: pd.DataFrame,
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> pd.DataFrame:
        """Filter dataframe by date range."""
        df = df.copy()

        if start_date:
            start_ts = pd.to_datetime(start_date)
            if hasattr(df['date'].iloc[0], 'date'):
                df = df[df['date'] >= start_ts]
            else:
                df = df[df['date'] >= start_ts.date()]

        if end_date:
            end_ts = pd.to_datetime(end_date)
            if hasattr(df['date'].iloc[0], 'date'):
                df = df[df['date'] <= end_ts]
            else:
                df = df[df['date'] <= end_ts.date()]

        return df.reset_index(drop=True)

    def _get_default_trade_constructors(self) -> Dict[int, Callable]:
        """
        Get default trade constructors for each profile.

        TODO: Implement proper trade construction logic for each profile.
        """
        # Placeholder - needs real implementation
        def placeholder_constructor(row, trade_id):
            # Placeholder ATM straddle
            spot = row['close']
            dte = 45

            expiry = datetime.now() + timedelta(days=dte)

            legs = [
                TradeLeg(
                    option_type='call',
                    strike=spot,
                    expiry=expiry,
                    quantity=1,
                    dte=dte
                ),
                TradeLeg(
                    option_type='put',
                    strike=spot,
                    expiry=expiry,
                    quantity=1,
                    dte=dte
                )
            ]

            return Trade(
                trade_id=trade_id,
                legs=legs,
                entry_date=row['date']
            )

        return {i: placeholder_constructor for i in range(1, 7)}

    def _calculate_metrics(self) -> Dict:
        """Calculate performance metrics."""
        if not self.daily_results:
            return {}

        df = pd.DataFrame(self.daily_results)

        # Returns
        total_return = (df['total_equity'].iloc[-1] / self.portfolio.initial_capital - 1) * 100

        # Sharpe ratio (annualized)
        daily_returns = df['daily_return']
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0

        # Max drawdown
        cumulative = (1 + daily_returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min() * 100

        # Win rate
        closed = self.portfolio.closed_positions
        if closed:
            wins = sum(1 for cp in closed if cp.realized_pnl > 0)
            win_rate = wins / len(closed) * 100
        else:
            win_rate = 0

        return {
            'total_return_pct': total_return,
            'sharpe_ratio': sharpe,
            'max_drawdown_pct': max_drawdown,
            'win_rate_pct': win_rate,
            'total_trades': len(closed),
            'avg_daily_return': daily_returns.mean() * 100,
            'return_std': daily_returns.std() * 100
        }
