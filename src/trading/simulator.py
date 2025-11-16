"""
Generic trade execution simulator for options backtesting.

Handles:
- Trade entry/exit
- Mark-to-market P&L calculation
- Delta hedging (daily or intraday)
- Roll logic (time-based or regime-based)
- Transaction costs via ExecutionModel
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Callable
from dataclasses import dataclass

from .trade import Trade, TradeLeg
from .execution import ExecutionModel, calculate_moneyness, get_vix_proxy
from .utils import normalize_date
from src.data.polygon_options import PolygonOptionsLoader


@dataclass
class SimulationConfig:
    """Configuration for trade simulator."""

    # Delta hedging
    delta_hedge_enabled: bool = True
    delta_hedge_frequency: str = 'daily'  # 'daily', 'threshold', 'none'
    delta_hedge_threshold: float = 0.10  # Rehedge if delta > this

    # Roll rules
    roll_dte_threshold: int = 5  # Roll when DTE < this
    roll_on_regime_change: bool = True

    # Risk limits
    max_loss_pct: float = 0.50  # Close if loss > 50% of entry cost
    max_days_in_trade: int = 120  # Force close after this many days

    # Execution
    execution_model: Optional[ExecutionModel] = None
    capital_per_trade: float = 100_000.0  # Used for return normalization
    allow_toy_pricing: bool = False  # Diagnostics-only fallback pricing

    def __post_init__(self):
        """Set default execution model if not provided."""
        if self.execution_model is None:
            self.execution_model = ExecutionModel()


class TradeSimulator:
    """Generic trade execution simulator for backtesting."""

    def __init__(
        self,
        data: pd.DataFrame,  # Full dataset with OHLCV, features, regimes
        config: Optional[SimulationConfig] = None,
        use_real_options_data: bool = True,
        polygon_data_root: Optional[str] = None
    ):
        """
        Initialize trade simulator.

        Parameters:
        -----------
        data : pd.DataFrame
            Full market data with columns: date, open, high, low, close, RV20, regime, etc.
        config : SimulationConfig
            Simulation configuration
        use_real_options_data : bool
            If True, use real Polygon options data. If False, use toy pricing model.
        polygon_data_root : str, optional
            Path to Polygon data root. If None, uses default.
        """
        self.data = data.copy()
        self.config = config or SimulationConfig()
        self.trades: List[Trade] = []
        self.trade_counter = 0

        # P&L tracking
        self.daily_pnl = []
        self.equity_curve = []

        # Polygon options loader
        self.use_real_options_data = use_real_options_data
        if use_real_options_data:
            self.polygon_loader = PolygonOptionsLoader(
                data_root=polygon_data_root or "/Volumes/VelocityData/polygon_downloads/us_options_opra/day_aggs_v1"
            )
        else:
            self.polygon_loader = None

        if not self.config.allow_toy_pricing and not self.use_real_options_data:
            raise ValueError(
                "Real Polygon data is required for production backtests. "
                "Set allow_toy_pricing=True explicitly to run diagnostic toy simulations."
            )

        # Statistics for data usage
        self.stats = {
            'real_prices_used': 0,
            'fallback_prices_used': 0,
            'missing_contracts': []
        }

        # Ensure data is sorted by date
        self.data = self.data.sort_values('date').reset_index(drop=True)

    def simulate(
        self,
        entry_logic: Callable[[pd.Series, Optional[Trade]], bool],
        trade_constructor: Callable[[pd.Series, str], Trade],
        exit_logic: Optional[Callable[[pd.Series, Trade], bool]] = None,
        profile_name: str = "Generic"
    ) -> pd.DataFrame:
        """
        Run backtest simulation using provided entry/exit logic.

        Parameters:
        -----------
        entry_logic : callable
            Function(row, current_trade) -> bool
            Returns True if should enter trade on this date
        trade_constructor : callable
            Function(row, trade_id) -> Trade
            Constructs trade object given market conditions
        exit_logic : callable, optional
            Function(row, trade) -> bool
            Returns True if should exit trade on this date
            If None, uses default exit logic (DTE threshold, max loss)
        profile_name : str
            Name of profile for logging

        Returns:
        --------
        results : pd.DataFrame
            Daily P&L, equity curve, position tracking
        """
        current_trade: Optional[Trade] = None
        realized_equity = 0.0
        prev_total_equity = 0.0
        pending_entry_signal = False

        results = []
        total_rows = len(self.data)

        for idx, row in self.data.iterrows():
            current_date = row['date']
            spot = row['close']
            vix_proxy = get_vix_proxy(row.get('RV20', 0.20))

            pnl_today = 0.0

            # Execute any pending entry signaled from previous day (T+1 fill)
            # ==================================================================
            # TIMING VERIFICATION:
            # - pending_entry_signal was set at Day T using row_T data
            # - We are now at Day T+1 with row_T+1 data
            # - trade_constructor(row_T+1) uses ONLY Day T+1 prices
            # - No look-ahead bias: Signal (T) → Fill (T+1)
            # ==================================================================
            if pending_entry_signal and current_trade is None:
                pending_entry_signal = False
                self.trade_counter += 1
                # Use date + profile + counter for unique trade IDs
                date_str = current_date.strftime('%Y%m%d') if hasattr(current_date, 'strftime') else str(current_date).replace('-', '')
                trade_id = f"{profile_name}_{date_str}_{self.trade_counter:04d}"

                current_trade = trade_constructor(row, trade_id)
                current_trade.profile_name = profile_name
                current_trade.underlying_price_entry = spot

                entry_prices = self._get_entry_prices(current_trade, row)
                current_trade.entry_prices = entry_prices
                current_trade.__post_init__()

                total_contracts = sum(abs(leg.quantity) for leg in current_trade.legs)
                has_short = any(leg.quantity < 0 for leg in current_trade.legs)
                current_trade.entry_commission = self.config.execution_model.get_commission_cost(
                    total_contracts, is_short=has_short
                )

                current_trade.calculate_greeks(
                    underlying_price=spot,
                    current_date=current_date,
                    implied_vol=vix_proxy,
                    risk_free_rate=0.05
                )

            # Check if we should exit current trade
            if current_trade is not None and current_trade.is_open:
                should_exit = False
                exit_reason = None

                # Custom exit logic
                if exit_logic is not None and exit_logic(row, current_trade):
                    should_exit = True
                    exit_reason = "Custom exit logic"

                # Default exit: DTE threshold
                # Normalize dates for comparison
                current_date_normalized = normalize_date(current_date)
                entry_date_normalized = normalize_date(current_trade.entry_date)

                days_in_trade = (current_date_normalized - entry_date_normalized).days

                # Calculate DTE for nearest expiry (most conservative)
                min_dte = float('inf')
                for leg in current_trade.legs:
                    expiry = normalize_date(leg.expiry)
                    dte = (expiry - current_date_normalized).days
                    min_dte = min(min_dte, dte)

                if min_dte <= self.config.roll_dte_threshold:
                    should_exit = True
                    exit_reason = f"DTE threshold ({min_dte} DTE)"

                # Default exit: Max loss
                current_prices = self._get_current_prices(current_trade, row)
                # Calculate estimated exit commission for realistic P&L
                total_contracts = sum(abs(leg.quantity) for leg in current_trade.legs)
                has_short = any(leg.quantity < 0 for leg in current_trade.legs)
                estimated_exit_commission = self.config.execution_model.get_commission_cost(
                    total_contracts, is_short=has_short
                )
                current_pnl = current_trade.mark_to_market(
                    current_prices,
                    estimated_exit_commission=estimated_exit_commission
                )

                if current_pnl < -abs(current_trade.entry_cost) * self.config.max_loss_pct:
                    should_exit = True
                    exit_reason = f"Max loss ({current_pnl:.2f})"

                # Default exit: Max days
                if days_in_trade >= self.config.max_days_in_trade:
                    should_exit = True
                    exit_reason = f"Max days ({days_in_trade} days)"

                # Execute exit
                if should_exit:
                    exit_prices = self._get_exit_prices(current_trade, row)

                    # Calculate exit commission
                    total_contracts = sum(abs(leg.quantity) for leg in current_trade.legs)
                    has_short = any(leg.quantity < 0 for leg in current_trade.legs)
                    current_trade.exit_commission = self.config.execution_model.get_commission_cost(
                        total_contracts, is_short=has_short
                    )

                    current_trade.close(current_date, exit_prices, exit_reason or "Unknown")
                    realized_equity += current_trade.realized_pnl
                    self.trades.append(current_trade)
                    current_trade = None

                # Daily delta hedge (if trade still open)
                elif self.config.delta_hedge_enabled:
                    hedge_cost = self._perform_delta_hedge(current_trade, row)
                    current_trade.add_hedge_cost(hedge_cost)

                # Mark-to-market (if trade still open) with Greeks updates
                if current_trade is not None:
                    current_prices = self._get_current_prices(current_trade, row)
                    # Calculate estimated exit commission for realistic P&L
                    total_contracts = sum(abs(leg.quantity) for leg in current_trade.legs)
                    has_short = any(leg.quantity < 0 for leg in current_trade.legs)
                    estimated_exit_commission = self.config.execution_model.get_commission_cost(
                        total_contracts, is_short=has_short
                    )
                    pnl_today = current_trade.mark_to_market(
                        current_prices=current_prices,
                        current_date=current_date,
                        underlying_price=spot,
                        implied_vol=vix_proxy,
                        risk_free_rate=0.05,
                        estimated_exit_commission=estimated_exit_commission
                    )

            # TIMING DIAGRAM: Entry Signal vs. Execution (No Look-Ahead Bias)
            # ==================================================================
            # Day T (Current Row):
            #   - entry_logic(row_T) evaluates using ONLY Day T EOD data
            #   - SPY close_T, VIX_T, RV20_T, regime_T, profile_scores_T
            #   - If True: Sets pending_entry_signal = True
            #   - NO trade execution on Day T
            #
            # Day T+1 (Next Row):
            #   - pending_entry_signal triggers trade_constructor(row_T+1)
            #   - Trade executed using Day T+1 prices (close_T+1, options_T+1)
            #   - This is T+1 fill - realistic execution timing
            #
            # Result: Signal generated at T EOD, trade filled at T+1 EOD
            # No future information used - walk-forward compliant
            # ==================================================================

            # Check if we should enter new trade (schedule for next session)
            is_last_row = idx == total_rows - 1
            if (
                current_trade is None
                and not pending_entry_signal
                and not is_last_row
                and entry_logic(row, current_trade)
            ):
                pending_entry_signal = True

            # Track equity using realized + unrealized outstanding position value
            unrealized_pnl = 0.0
            if current_trade is not None:
                current_prices = self._get_current_prices(current_trade, row)
                # Calculate estimated exit commission for realistic P&L
                total_contracts = sum(abs(leg.quantity) for leg in current_trade.legs)
                has_short = any(leg.quantity < 0 for leg in current_trade.legs)
                estimated_exit_commission = self.config.execution_model.get_commission_cost(
                    total_contracts, is_short=has_short
                )
                unrealized_pnl = current_trade.mark_to_market(
                    current_prices=current_prices,
                    current_date=current_date,
                    underlying_price=spot,
                    implied_vol=vix_proxy,
                    risk_free_rate=0.05,
                    estimated_exit_commission=estimated_exit_commission
                )

            total_equity = realized_equity + unrealized_pnl
            daily_pnl = total_equity - prev_total_equity

            # Use previous day's total equity as denominator for returns
            if prev_total_equity > 0:
                daily_return = daily_pnl / prev_total_equity
            else:
                # First day or zero equity - use initial capital
                daily_return = daily_pnl / max(self.config.capital_per_trade, 1.0)

            prev_total_equity = total_equity

            results.append({
                'date': current_date,
                'spot': spot,
                'regime': row.get('regime', 0),
                'position_open': current_trade is not None,
                'daily_pnl': daily_pnl,
                'daily_return': daily_return,
                'realized_pnl_total': realized_equity,
                'unrealized_pnl': unrealized_pnl,
                'total_pnl': total_equity,
                'trade_id': current_trade.trade_id if current_trade else None
            })

        # Close any remaining open trade at end
        if current_trade is not None and current_trade.is_open:
            final_row = self.data.iloc[-1]
            exit_prices = self._get_exit_prices(current_trade, final_row)

            # Calculate exit commission
            total_contracts = sum(abs(leg.quantity) for leg in current_trade.legs)
            has_short = any(leg.quantity < 0 for leg in current_trade.legs)
            current_trade.exit_commission = self.config.execution_model.get_commission_cost(
                total_contracts, is_short=has_short
            )

            current_trade.close(final_row['date'], exit_prices, "End of backtest")
            realized_equity += current_trade.realized_pnl
            self.trades.append(current_trade)

            if results:
                capital_base = max(self.config.capital_per_trade, 1.0)
                last_row = results[-1]
                previous_total = last_row['total_pnl']
                last_row['realized_pnl_total'] = realized_equity
                last_row['unrealized_pnl'] = 0.0
                last_row['total_pnl'] = realized_equity
                adjustment = realized_equity - previous_total
                last_row['daily_pnl'] += adjustment
                last_row['daily_return'] = last_row['daily_pnl'] / capital_base

        return pd.DataFrame(results)

    def _get_entry_prices(self, trade: Trade, row: pd.Series) -> Dict[int, float]:
        """Get execution prices for trade entry (pay ask for longs, receive bid for shorts)."""
        spot = row['close']
        vix_proxy = get_vix_proxy(row.get('RV20', 0.20))

        # Normalize trade date
        trade_date = normalize_date(row['date'])

        entry_prices = {}

        for i, leg in enumerate(trade.legs):
            # Try to get real bid/ask from Polygon
            real_bid = None
            real_ask = None

            if self.use_real_options_data and self.polygon_loader is not None:
                try:
                    expiry = normalize_date(leg.expiry)

                    real_bid = self.polygon_loader.get_option_price(
                        trade_date=trade_date,
                        strike=leg.strike,
                        expiry=expiry,
                        option_type=leg.option_type,
                        price_type='bid'
                    )

                    real_ask = self.polygon_loader.get_option_price(
                        trade_date=trade_date,
                        strike=leg.strike,
                        expiry=expiry,
                        option_type=leg.option_type,
                        price_type='ask'
                    )
                except:
                    pass

            if (real_bid is None or real_ask is None) and self.use_real_options_data:
                suggestion = self._snap_contract_to_available(trade_date, leg)
                if suggestion:
                    real_bid = suggestion['bid']
                    real_ask = suggestion['ask']

            # If we have real bid/ask, use them directly
            if real_bid is not None and real_ask is not None:
                self.stats['real_prices_used'] += 1
                if leg.quantity > 0:
                    exec_price = real_ask  # Buy at ask
                else:
                    exec_price = real_bid  # Sell at bid
            else:
                # Fallback: estimate mid and apply spread model
                mid_price = self._estimate_option_price(leg, spot, row)
                moneyness = calculate_moneyness(leg.strike, spot)
                exec_price = self.config.execution_model.apply_spread_to_price(
                    mid_price,
                    leg.quantity,
                    moneyness,
                    leg.dte,
                    vix_proxy
                )

            entry_prices[i] = exec_price

        return entry_prices

    def _get_exit_prices(self, trade: Trade, row: pd.Series) -> Dict[int, float]:
        """Get execution prices for trade exit (reverse of entry: receive bid for longs, pay ask for shorts)."""
        spot = row['close']
        vix_proxy = get_vix_proxy(row.get('RV20', 0.20))

        # Normalize trade date
        trade_date = normalize_date(row['date'])

        exit_prices = {}

        for i, leg in enumerate(trade.legs):
            # Normalize dates for DTE calculation
            current_date_exit = normalize_date(row['date'])
            entry_date_exit = normalize_date(trade.entry_date)

            days_in_trade = (current_date_exit - entry_date_exit).days
            current_dte = leg.dte - days_in_trade

            # Try to get real bid/ask from Polygon
            real_bid = None
            real_ask = None

            if self.use_real_options_data and self.polygon_loader is not None:
                try:
                    expiry = normalize_date(leg.expiry)

                    real_bid = self.polygon_loader.get_option_price(
                        trade_date=trade_date,
                        strike=leg.strike,
                        expiry=expiry,
                        option_type=leg.option_type,
                        price_type='bid'
                    )

                    real_ask = self.polygon_loader.get_option_price(
                        trade_date=trade_date,
                        strike=leg.strike,
                        expiry=expiry,
                        option_type=leg.option_type,
                        price_type='ask'
                    )
                except:
                    pass

            if (real_bid is None or real_ask is None) and self.use_real_options_data:
                suggestion = self._snap_contract_to_available(trade_date, leg)
                if suggestion:
                    real_bid = suggestion['bid']
                    real_ask = suggestion['ask']

            # If we have real bid/ask, use them (reverse of entry)
            if real_bid is not None and real_ask is not None:
                self.stats['real_prices_used'] += 1
                if leg.quantity > 0:
                    exec_price = real_bid  # Longs close at bid
                else:
                    exec_price = real_ask  # Shorts close at ask
            else:
                # Fallback: estimate mid and apply spread model
                mid_price = self._estimate_option_price(leg, spot, row, current_dte)
                moneyness = calculate_moneyness(leg.strike, spot)
                # Flip quantity for exit
                flipped_quantity = -leg.quantity
                exec_price = self.config.execution_model.apply_spread_to_price(
                    mid_price,
                    flipped_quantity,
                    moneyness,
                    current_dte,
                    vix_proxy
                )

            exit_prices[i] = exec_price

        return exit_prices

    def _get_current_prices(self, trade: Trade, row: pd.Series) -> Dict[int, float]:
        """Get current mark-to-market prices (mid price)."""
        spot = row['close']

        current_prices = {}

        # Normalize dates for comparison
        current_date = normalize_date(row['date'])
        entry_date = normalize_date(trade.entry_date)

        for i, leg in enumerate(trade.legs):
            days_in_trade = (current_date - entry_date).days
            current_dte = leg.dte - days_in_trade

            # Use mid price for mark-to-market
            mid_price = self._estimate_option_price(leg, spot, row, current_dte)
            current_prices[i] = mid_price

        return current_prices

    def _estimate_option_price(
        self,
        leg: TradeLeg,
        spot: float,
        row: pd.Series,
        dte: Optional[int] = None
    ) -> float:
        """
        Get option price using real Polygon data, with fallback to toy model.

        Parameters:
        -----------
        leg : TradeLeg
            Option leg
        spot : float
            Current spot price
        row : pd.Series
            Market data row
        dte : int, optional
            Current DTE (defaults to leg.dte)

        Returns:
        --------
        price : float
            Option price
        """
        dte = dte if dte is not None else leg.dte

        # Normalize trade date
        trade_date = normalize_date(row['date'])

        # Calculate expiry date from entry + DTE
        if hasattr(leg, 'expiry') and leg.expiry is not None:
            expiry = normalize_date(leg.expiry)
        else:
            # Fallback: estimate expiry from current date + DTE
            expiry = trade_date + timedelta(days=dte)

        # Try to get real Polygon data first
        if self.use_real_options_data and self.polygon_loader is not None:
            price = self.polygon_loader.get_option_price(
                trade_date=trade_date,
                strike=leg.strike,
                expiry=expiry,
                option_type=leg.option_type,
                price_type='mid'  # Use mid for fair value
            )

            if price is not None and price > 0:
                self.stats['real_prices_used'] += 1
                return price
            else:
                suggestion = self._snap_contract_to_available(trade_date, leg)
                if suggestion:
                    self.stats['real_prices_used'] += 1
                    return suggestion['mid']
                # No data found, record and enforce policy
                suggestion = self._handle_missing_contract(trade_date, leg, expiry)
                if suggestion:
                    self.stats['real_prices_used'] += 1
                    return suggestion['mid']
        else:
            # Running without real data (diagnostics only)
            suggestion = self._handle_missing_contract(trade_date, leg, expiry)
            if suggestion:
                return suggestion['mid']

        # Fallback to toy model (diagnostics only)
        return self._toy_option_price(leg, spot, row, dte)

    def _handle_missing_contract(self, trade_date, leg: TradeLeg, expiry):
        """Record missing contracts and optionally raise when toy pricing disabled."""
        normalized_trade_date = trade_date
        if isinstance(normalized_trade_date, pd.Timestamp):
            normalized_trade_date = normalized_trade_date.date()
        if isinstance(expiry, pd.Timestamp):
            expiry = expiry.date()
        contract_key = (normalized_trade_date, leg.strike, expiry, leg.option_type)
        if contract_key not in self.stats['missing_contracts']:
            self.stats['missing_contracts'].append(contract_key)
        self.stats['fallback_prices_used'] += 1

        suggestion = self._snap_contract_to_available(normalized_trade_date, leg)
        if suggestion:
            return suggestion

        if not self.config.allow_toy_pricing:
            raise RuntimeError(
                f"Polygon options data missing for {leg.option_type.upper()} "
                f"{leg.strike} exp {expiry} on {normalized_trade_date}. "
                "Mount the real Polygon dataset or set allow_toy_pricing=True "
                "explicitly for diagnostic toy simulations."
            )

        return None

    def _snap_contract_to_available(self, trade_date: date, leg: TradeLeg) -> Optional[Dict]:
        """Adjust leg to closest available contract and return its prices."""
        if not self.use_real_options_data or self.polygon_loader is None:
            return None

        expiry_date = normalize_date(leg.expiry)

        suggestion = self.polygon_loader.find_closest_contract(
            trade_date=trade_date,
            strike=leg.strike,
            expiry=expiry_date,
            option_type=leg.option_type
        )

        if suggestion is None:
            return None

        suggested_expiry = normalize_date(suggestion['expiry'])

        leg.strike = suggestion['strike']
        leg.expiry = datetime.combine(suggested_expiry, datetime.min.time())
        leg.dte = max(
            (leg.expiry - datetime.combine(trade_date, datetime.min.time())).days,
            1
        )

        return suggestion

    def _toy_option_price(
        self,
        leg: TradeLeg,
        spot: float,
        row: pd.Series,
        dte: int
    ) -> float:
        """
        Toy option pricing model (fallback when real data not available).

        Uses intrinsic + time value proxy.
        """
        # Intrinsic value
        if leg.option_type == 'call':
            intrinsic = max(0, spot - leg.strike)
        else:  # put
            intrinsic = max(0, leg.strike - spot)

        # Time value (simplified: proportional to sqrt(DTE) and volatility)
        effective_dte = max(dte, 1)

        iv_proxy = row.get('RV20', 0.20) * 1.2  # IV ≈ RV × 1.2
        time_value = spot * iv_proxy * np.sqrt(effective_dte / 365.0)

        # Adjust time value for moneyness (ATM has highest time value)
        moneyness = abs(spot - leg.strike) / spot
        time_value_factor = np.exp(-10 * moneyness)  # Decays for OTM
        time_value *= time_value_factor

        return intrinsic + time_value

    def _perform_delta_hedge(self, trade: Trade, row: pd.Series) -> float:
        """
        Perform delta hedge and return cost.

        Calculates current net delta and hedges using ES futures.
        Each ES contract represents ~50 delta (since SPX is ~50x ES).

        Returns:
        --------
        hedge_cost : float
            Cost of hedging (commission + slippage)
        """
        if self.config.delta_hedge_frequency != 'daily':
            return 0.0

        # Update Greeks with current prices
        spot = row['close']
        current_date = row['date']
        vix_proxy = get_vix_proxy(row.get('RV20', 0.20))

        trade.calculate_greeks(
            underlying_price=spot,
            current_date=current_date,
            implied_vol=vix_proxy,
            risk_free_rate=0.05
        )

        # Determine hedge quantity needed
        # ES futures: each contract ~= 50 SPX delta (since SPX is ~50x ES price)
        # Example: SPX at 5000, ES at 5000, notional = 5000 * 50 = $250k per contract
        # If net_delta = 100 (1 ATM call contract), need 100/50 = 2 ES contracts
        es_delta_per_contract = 50

        # Only hedge if delta exceeds threshold
        delta_threshold = 20  # Hedge if abs(delta) > 20
        if abs(trade.net_delta) < delta_threshold:
            return 0.0

        # Calculate ES contracts needed to neutralize delta
        hedge_contracts = abs(trade.net_delta) / es_delta_per_contract

        # Get hedging cost
        return self.config.execution_model.get_delta_hedge_cost(hedge_contracts)

    def get_trade_summary(self) -> pd.DataFrame:
        """Get summary of all closed trades."""
        if not self.trades:
            return pd.DataFrame()

        summary = []
        for trade in self.trades:
            if not trade.is_open:
                summary.append({
                    'trade_id': trade.trade_id,
                    'profile': trade.profile_name,
                    'entry_date': trade.entry_date,
                    'exit_date': trade.exit_date,
                    'days_held': (trade.exit_date - trade.entry_date).days,
                    'entry_cost': trade.entry_cost,
                    'exit_proceeds': trade.exit_proceeds,
                    'hedge_cost': trade.cumulative_hedge_cost,
                    'realized_pnl': trade.realized_pnl,
                    'return_pct': trade.realized_pnl / abs(trade.entry_cost) * 100 if trade.entry_cost != 0 else 0,
                    'exit_reason': trade.exit_reason,
                    'legs': len(trade.legs)
                })

        return pd.DataFrame(summary)
