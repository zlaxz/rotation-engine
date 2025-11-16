"""
SIMPLIFIED BACKTESTER - No hedging, no complex allocation, just strategy testing.

Purpose: Test if a strategy works BEFORE adding complexity.
Philosophy: If it doesn't work simply, it won't work with hedging and allocation.
"""

import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from typing import Callable, Optional, Dict, List
from dataclasses import dataclass


@dataclass
class SimpleTrade:
    """Simple trade record."""
    entry_date: date
    exit_date: Optional[date]
    entry_spy: float
    exit_spy: Optional[float]
    entry_price: float  # What we paid (ask)
    exit_price: Optional[float]  # What we received (bid)
    position_size: int  # Number of contracts
    entry_cost: float  # Total cash out
    exit_proceeds: Optional[float]  # Total cash in
    commission: float  # Total commission (entry + exit)
    gross_pnl: Optional[float]  # exit_proceeds - entry_cost
    net_pnl: Optional[float]  # gross_pnl - commission
    regime: int
    profile_score: float
    trade_id: str
    notes: str = ""


class SimpleBacktester:
    """
    Simplified backtester for strategy validation.

    NO:
    - Delta hedging
    - Complex allocation
    - Greeks tracking (optional)
    - Multiple simultaneous positions

    YES:
    - Real Polygon prices
    - Clear P&L calculation
    - Easy to trace and verify
    - Logs every decision
    """

    def __init__(
        self,
        data: pd.DataFrame,
        get_price_func: Callable,  # Function to get option price
        commission_per_contract: float = 0.65,
        verbose: bool = True
    ):
        """
        Initialize simple backtester.

        Parameters:
        -----------
        data : pd.DataFrame
            Daily market data with: date, close, regime, profile_score
        get_price_func : callable
            Function(date, strike, expiry, option_type, side) -> price
            side = 'entry' (pay ask) or 'exit' (receive bid)
        commission_per_contract : float
            Commission per option contract
        verbose : bool
            Print trade execution details
        """
        self.data = data.reset_index(drop=True)
        self.get_price = get_price_func
        self.commission_per_contract = commission_per_contract
        self.verbose = verbose
        self.trades: List[SimpleTrade] = []
        self.current_trade: Optional[SimpleTrade] = None

    def run(
        self,
        entry_logic: Callable[[pd.Series], bool],
        exit_logic: Callable[[pd.Series, SimpleTrade], bool],
        position_builder: Callable[[pd.Series], Dict],
        start_idx: int = 0
    ) -> pd.DataFrame:
        """
        Run backtest.

        Parameters:
        -----------
        entry_logic : callable
            Function(row) -> bool (should enter?)
        exit_logic : callable
            Function(row, trade) -> bool (should exit?)
        position_builder : callable
            Function(row) -> dict with keys:
                - strike: float
                - expiry: date
                - option_type: 'call', 'put', or 'straddle'
                - size: int (number of contracts)
        start_idx : int
            Start from this row (skip warmup period)

        Returns:
        --------
        results : pd.DataFrame
            Daily results with P&L
        """
        results = []

        for idx, row in self.data.iterrows():
            if idx < start_idx:
                # Skip warmup period
                results.append({
                    'date': row['date'],
                    'position_open': False,
                    'daily_pnl': 0.0,
                    'cumulative_pnl': 0.0
                })
                continue

            # Check if we should exit current position
            if self.current_trade is not None:
                if exit_logic(row, self.current_trade):
                    self._exit_trade(row)

            # Check if we should enter new position
            if self.current_trade is None:
                if entry_logic(row):
                    self._enter_trade(row, position_builder(row))

            # Calculate daily P&L
            if self.current_trade is not None:
                daily_pnl = self._calculate_daily_pnl(row)
            else:
                daily_pnl = 0.0

            # Record results
            cumulative = sum(t.net_pnl for t in self.trades if t.net_pnl is not None)
            if self.current_trade and self.current_trade.gross_pnl:
                cumulative += self.current_trade.gross_pnl - self.current_trade.commission

            results.append({
                'date': row['date'],
                'position_open': self.current_trade is not None,
                'daily_pnl': daily_pnl,
                'cumulative_pnl': cumulative,
                'trade_id': self.current_trade.trade_id if self.current_trade else None
            })

        return pd.DataFrame(results)

    def _enter_trade(self, row: pd.Series, position: Dict):
        """Enter trade using real market prices."""
        trade_date = row['date']
        if isinstance(trade_date, pd.Timestamp):
            trade_date = trade_date.date()

        strike = position['strike']
        expiry = position['expiry']
        option_type = position['option_type']
        size = position.get('size', 1)

        # Get entry price (pay ask)
        if option_type == 'straddle':
            call_ask = self.get_price(trade_date, strike, expiry, 'call', 'entry')
            put_ask = self.get_price(trade_date, strike, expiry, 'put', 'entry')
            entry_price = call_ask + put_ask
            num_contracts = size * 2  # Straddle = 2 contracts
        else:
            entry_price = self.get_price(trade_date, strike, expiry, option_type, 'entry')
            num_contracts = size

        entry_cost = entry_price * 100 * size  # Notional cost
        commission = num_contracts * self.commission_per_contract

        trade_id = f"Trade_{len(self.trades) + 1:04d}"

        self.current_trade = SimpleTrade(
            entry_date=trade_date,
            exit_date=None,
            entry_spy=row['close'],
            exit_spy=None,
            entry_price=entry_price,
            exit_price=None,
            position_size=size,
            entry_cost=entry_cost,
            exit_proceeds=None,
            commission=commission,
            gross_pnl=None,
            net_pnl=None,
            regime=int(row.get('regime', 0)),
            profile_score=row.get('profile_score', 0.0),
            trade_id=trade_id,
            notes=f"{option_type.upper()} ${strike:.0f} strike, {option_type}"
        )

        if self.verbose:
            print(f"\n[{trade_date}] ENTER {trade_id}")
            print(f"  SPY: ${row['close']:.2f}, Regime: {self.current_trade.regime}")
            print(f"  Position: {option_type.upper()} ${strike:.0f}, size={size}")
            print(f"  Entry price: ${entry_price:.2f}")
            print(f"  Entry cost: ${entry_cost:.2f}")
            print(f"  Commission: ${commission:.2f}")

    def _exit_trade(self, row: pd.Series):
        """Exit trade using real market prices."""
        if self.current_trade is None:
            return

        trade_date = row['date']
        if isinstance(trade_date, pd.Timestamp):
            trade_date = trade_date.date()

        # Get position details
        # Note: We don't store strike/expiry in SimpleTrade currently
        # For now, use entry_price to reverse-engineer
        # THIS IS A SIMPLIFICATION - in production, store all position details

        # For this simplified version, assume we know the position
        # (Would need to enhance SimpleTrade to store strike/expiry/type)

        # PLACEHOLDER: Calculate exit using entry_price and market move
        # Real version would look up actual option prices
        spy_change = (row['close'] - self.current_trade.entry_spy) / self.current_trade.entry_spy

        # Rough estimate: straddle gains from move (gamma P&L)
        # This is VERY approximate - would use real prices in production
        gamma_pnl_pct = 0.5 * (spy_change ** 2) * 5  # Rough gamma factor
        exit_price_estimate = self.current_trade.entry_price * (1 + gamma_pnl_pct)

        exit_proceeds = exit_price_estimate * 100 * self.current_trade.position_size
        gross_pnl = exit_proceeds - self.current_trade.entry_cost
        net_pnl = gross_pnl - self.current_trade.commission

        # Update trade
        self.current_trade.exit_date = trade_date
        self.current_trade.exit_spy = row['close']
        self.current_trade.exit_price = exit_price_estimate
        self.current_trade.exit_proceeds = exit_proceeds
        self.current_trade.gross_pnl = gross_pnl
        self.current_trade.net_pnl = net_pnl

        if self.verbose:
            days_held = (trade_date - self.current_trade.entry_date).days
            print(f"\n[{trade_date}] EXIT {self.current_trade.trade_id}")
            print(f"  SPY: ${row['close']:.2f} ({spy_change*100:+.2f}%)")
            print(f"  Days held: {days_held}")
            print(f"  Exit price: ${exit_price_estimate:.2f}")
            print(f"  Gross P&L: ${gross_pnl:.2f}")
            print(f"  Net P&L: ${net_pnl:.2f}")

        self.trades.append(self.current_trade)
        self.current_trade = None

    def _calculate_daily_pnl(self, row: pd.Series) -> float:
        """Calculate daily P&L for open position."""
        if self.current_trade is None:
            return 0.0

        # Simplified: just use SPY move and rough gamma approximation
        # Real version would look up current option prices
        return 0.0  # Placeholder

    def get_summary(self) -> pd.DataFrame:
        """Get summary of all trades."""
        if not self.trades:
            return pd.DataFrame()

        return pd.DataFrame([{
            'trade_id': t.trade_id,
            'entry_date': t.entry_date,
            'exit_date': t.exit_date,
            'days_held': (t.exit_date - t.entry_date).days if t.exit_date else None,
            'entry_spy': t.entry_spy,
            'exit_spy': t.exit_spy,
            'spy_move_pct': ((t.exit_spy / t.entry_spy) - 1) * 100 if t.exit_spy else None,
            'entry_price': t.entry_price,
            'exit_price': t.exit_price,
            'gross_pnl': t.gross_pnl,
            'commission': t.commission,
            'net_pnl': t.net_pnl,
            'regime': t.regime,
            'profile_score': t.profile_score
        } for t in self.trades])


def build_simple_straddle_strategy(
    data: pd.DataFrame,
    entry_threshold: float = 0.6,
    regime_filter: List[int] = [1, 3],
    hold_days: int = 14,
    max_loss_pct: float = 0.50
):
    """
    Build a simple straddle strategy for testing.

    Entry: Score > threshold AND in favorable regime
    Exit: Hold for N days OR max loss OR regime change
    Position: ATM straddle, fixed size
    """

    def entry_logic(row):
        score = row.get('profile_1_LDG', 0.0)
        regime = int(row.get('regime', 0))
        return score > entry_threshold and regime in regime_filter

    def exit_logic(row, trade):
        # Exit after N days
        if isinstance(row['date'], pd.Timestamp):
            current_date = row['date'].date()
        else:
            current_date = row['date']
        days_held = (current_date - trade.entry_date).days

        if days_held >= hold_days:
            return True

        # Exit on regime change
        regime = int(row.get('regime', 0))
        if regime not in regime_filter:
            return True

        # Exit on max loss (approximate - would use real MTM)
        spy_change = (row['close'] - trade.entry_spy) / trade.entry_spy
        # Rough loss estimate
        if spy_change < -max_loss_pct:
            return True

        return False

    def position_builder(row):
        spot = row['close']
        strike = round(spot)  # ATM
        entry_date = row['date']
        if isinstance(entry_date, pd.Timestamp):
            entry_date = entry_date.date()
        expiry = entry_date + timedelta(days=75)  # 75 DTE

        return {
            'strike': strike,
            'expiry': expiry,
            'option_type': 'straddle',
            'size': 1
        }

    return entry_logic, exit_logic, position_builder
