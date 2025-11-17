#!/usr/bin/env python3
"""
SIMPLE BACKTESTER - No Hedging, No Complexity

Philosophy: If it doesn't work simply, it won't work with complexity.

Tests raw strategy edge:
- Enter when conditions met
- Hold position
- Exit when conditions change
- Calculate P&L

NO delta hedging, NO allocation, NO complexity.
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
from datetime import date, timedelta
from src.data.polygon_options import PolygonOptionsLoader
from typing import List, Optional


class SimpleBacktester:
    """Dead simple backtester for strategy validation."""

    def __init__(
        self,
        spread_atm: float = 0.75,
        commission_per_contract: float = 0.65,
        verbose: bool = False
    ):
        self.spread_half = spread_atm / 2
        self.commission_per_contract = commission_per_contract
        self.verbose = verbose
        self.polygon = PolygonOptionsLoader()
        self.trades = []

    def run_straddle_strategy(
        self,
        data: pd.DataFrame,
        score_col: str,
        regime_col: str,
        score_threshold: float = 0.6,
        regime_filter: List[int] = [1, 3],
        hold_days: int = 14,
        target_dte: int = 75
    ) -> pd.DataFrame:
        """
        Run simple straddle strategy backtest.

        Entry: score > threshold AND regime in filter
        Exit: After N days OR regime change
        Position: ATM straddle, target DTE

        Returns daily results DataFrame.
        """
        results = []
        current_trade = None
        cumulative_pnl = 0.0

        for idx in range(len(data)):
            row = data.iloc[idx]
            trade_date = self._normalize_date(row['date'])
            spot = row['close']
            regime = int(row.get(regime_col, 0))
            score = row.get(score_col, 0.0)

            # Exit logic
            if current_trade is not None:
                days_held = (trade_date - current_trade['entry_date']).days
                should_exit = False
                exit_reason = None

                if days_held >= hold_days:
                    should_exit = True
                    exit_reason = f"Held {days_held}d"
                elif regime not in regime_filter:
                    should_exit = True
                    exit_reason = "Regime change"

                if should_exit:
                    # Exit trade
                    pnl = self._exit_trade(current_trade, trade_date, spot, exit_reason)
                    if pnl is not None:
                        cumulative_pnl += pnl
                        self.trades.append(current_trade)
                    current_trade = None

            # Entry logic
            if current_trade is None:
                if score > score_threshold and regime in regime_filter:
                    current_trade = self._enter_trade(trade_date, spot, regime, score, target_dte)

            # Record daily result
            results.append({
                'date': trade_date,
                'spot': spot,
                'regime': regime,
                'score': score,
                'position_open': current_trade is not None,
                'trade_id': current_trade['trade_id'] if current_trade else None,
                'cumulative_pnl': cumulative_pnl
            })

        return pd.DataFrame(results)

    def _enter_trade(self, entry_date: date, spot: float, regime: int, score: float, target_dte: int) -> dict:
        """Enter ATM straddle position."""
        strike = round(spot)
        expiry = self._get_third_friday(entry_date, target_dte)

        # Get real Polygon prices
        call_mid = self.polygon.get_option_price(entry_date, strike, expiry, 'call', 'mid')
        put_mid = self.polygon.get_option_price(entry_date, strike, expiry, 'put', 'mid')

        if call_mid is None or put_mid is None:
            if self.verbose:
                print(f"  ⚠️  No Polygon data for {entry_date}, strike ${strike}, expiry {expiry}")
            return None

        # Pay ask
        call_ask = call_mid + self.spread_half
        put_ask = put_mid + self.spread_half
        entry_straddle = call_ask + put_ask
        entry_cost = entry_straddle * 100

        trade_id = f"Trade_{len(self.trades) + 1:03d}"
        dte_actual = (expiry - entry_date).days

        trade = {
            'trade_id': trade_id,
            'entry_date': entry_date,
            'exit_date': None,
            'entry_spot': spot,
            'exit_spot': None,
            'strike': strike,
            'expiry': expiry,
            'dte_entry': dte_actual,
            'entry_call_mid': call_mid,
            'entry_put_mid': put_mid,
            'entry_straddle': entry_straddle,
            'entry_cost': entry_cost,
            'exit_call_mid': None,
            'exit_put_mid': None,
            'exit_straddle': None,
            'exit_proceeds': None,
            'gross_pnl': None,
            'commission': 4 * self.commission_per_contract,  # 2 contracts × entry/exit
            'net_pnl': None,
            'regime': regime,
            'score': score
        }

        if self.verbose:
            print(f"ENTER {trade_id} [{entry_date}] SPY ${spot:.2f}, ${strike} strike, "
                  f"{dte_actual}DTE, Entry ${entry_straddle:.2f}")

        return trade

    def _exit_trade(self, trade: dict, exit_date: date, spot: float, reason: str) -> Optional[float]:
        """Exit position and calculate P&L."""
        # Get exit prices
        call_mid = self.polygon.get_option_price(exit_date, trade['strike'], trade['expiry'], 'call', 'mid')
        put_mid = self.polygon.get_option_price(exit_date, trade['strike'], trade['expiry'], 'put', 'mid')

        if call_mid is None or put_mid is None:
            if self.verbose:
                print(f"  ⚠️  No exit price data for {exit_date}")
            return None

        # Receive bid
        call_bid = call_mid - self.spread_half
        put_bid = put_mid - self.spread_half
        exit_straddle = call_bid + put_bid
        exit_proceeds = exit_straddle * 100

        # Calculate P&L
        gross_pnl = exit_proceeds - trade['entry_cost']
        net_pnl = gross_pnl - trade['commission']

        # Update trade record
        trade['exit_date'] = exit_date
        trade['exit_spot'] = spot
        trade['exit_call_mid'] = call_mid
        trade['exit_put_mid'] = put_mid
        trade['exit_straddle'] = exit_straddle
        trade['exit_proceeds'] = exit_proceeds
        trade['gross_pnl'] = gross_pnl
        trade['net_pnl'] = net_pnl

        days_held = (exit_date - trade['entry_date']).days
        spot_move_pct = ((spot / trade['entry_spot']) - 1) * 100

        if self.verbose or True:  # Always print exits
            print(f"EXIT {trade['trade_id']} [{exit_date}] {reason}: SPY ${spot:.2f} ({spot_move_pct:+.2f}%), "
                  f"Held {days_held}d, P&L ${net_pnl:+.2f}")

        return net_pnl

    def _get_third_friday(self, entry_date: date, target_dte: int) -> date:
        """Get third Friday of month ~target_dte days out."""
        target_day = entry_date + timedelta(days=target_dte)
        year, month = target_day.year, target_day.month

        first_day = date(year, month, 1)
        first_friday_offset = (4 - first_day.weekday()) % 7
        first_friday = first_day + timedelta(days=first_friday_offset)
        third_friday = first_friday + timedelta(days=14)

        # Ensure minimum 45 DTE
        if third_friday <= entry_date + timedelta(days=45):
            # Move to next month
            if month == 12:
                year, month = year + 1, 1
            else:
                month += 1
            first_day = date(year, month, 1)
            first_friday_offset = (4 - first_day.weekday()) % 7
            first_friday = first_day + timedelta(days=first_friday_offset)
            third_friday = first_friday + timedelta(days=14)

        return third_friday

    def _normalize_date(self, d):
        """Convert any date type to date object."""
        if isinstance(d, pd.Timestamp):
            return d.date()
        elif isinstance(d, date):
            return d
        else:
            return pd.to_datetime(d).date()

    def get_summary(self) -> pd.DataFrame:
        """Get trade summary."""
        if not self.trades:
            return pd.DataFrame()

        return pd.DataFrame([{
            'trade_id': t['trade_id'],
            'entry_date': t['entry_date'],
            'exit_date': t['exit_date'],
            'days_held': (t['exit_date'] - t['entry_date']).days if t['exit_date'] else None,
            'entry_spot': t['entry_spot'],
            'exit_spot': t['exit_spot'],
            'spot_move_pct': ((t['exit_spot'] / t['entry_spot']) - 1) * 100 if t['exit_spot'] else None,
            'strike': t['strike'],
            'dte_entry': t['dte_entry'],
            'entry_straddle': t['entry_straddle'],
            'exit_straddle': t['exit_straddle'],
            'straddle_change': t['exit_straddle'] - t['entry_straddle'] if t['exit_straddle'] else None,
            'gross_pnl': t['gross_pnl'],
            'commission': t['commission'],
            'net_pnl': t['net_pnl'],
            'regime': t['regime'],
            'score': t['score']
        } for t in self.trades])


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("CONCLUSION FROM TRADE 1:")
    print("=" * 80)
    print("Simple strategy (no hedging) made $462.40")
    print("Complex backtest (with hedging) made $140.60")
    print("Delta hedging cost: $321.80 (1.79x expected cost)")
    print("\nEither:")
    print("  1. Hedging happened more than 12 times")
    print("  2. Hedging cost is wrong ($27/hedge not $15)")
    print("  3. Another bug we haven't found")
    print("\nNext: Test Profile 1 WITHOUT hedging on full 2020-2024 dataset")
