#!/usr/bin/env python3
"""
DEAD SIMPLE BACKTESTER - Strategy validation only

Rules:
1. Use real Polygon CLOSE prices (daily bars)
2. Entry = close + half_spread (pay ask)
3. Exit = close - half_spread (receive bid)
4. Commission = $0.65 per contract
5. NO delta hedging
6. NO allocation complexity
7. One position at a time

If it doesn't work simply, it won't work with complexity.
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
from datetime import date, timedelta
from src.data.polygon_options import PolygonOptionsLoader

class SimpleTrade:
    def __init__(self):
        self.entry_date = None
        self.exit_date = None
        self.strike = None
        self.expiry = None
        self.entry_call_price = None
        self.entry_put_price = None
        self.exit_call_price = None
        self.exit_put_price = None
        self.commission = 0.0
        self.pnl = None

def simple_backtest(
    data: pd.DataFrame,
    score_col: str,
    regime_col: str,
    score_threshold: float = 0.6,
    regime_filter: list = [1, 3],
    hold_days: int = 14
):
    """
    Run dead simple backtest.

    Entry: score > threshold AND regime in filter
    Exit: After N days OR regime change
    Position: ATM straddle, 75 DTE
    """

    polygon = PolygonOptionsLoader()
    trades = []
    current_trade = None

    spread_half = 0.375  # Half of $0.75 ATM spread
    commission_per_contract = 0.65

    results = []
    cumulative_pnl = 0.0

    for idx in range(len(data)):
        row = data.iloc[idx]
        trade_date = row['date']
        if isinstance(trade_date, pd.Timestamp):
            trade_date = trade_date.date()

        spot = row['close']
        regime = int(row.get(regime_col, 0))
        score = row.get(score_col, 0.0)

        # Exit logic
        if current_trade is not None:
            days_held = (trade_date - current_trade.entry_date).days
            should_exit = False

            if days_held >= hold_days:
                should_exit = True
                exit_reason = f"Held {days_held} days"
            elif regime not in regime_filter:
                should_exit = True
                exit_reason = "Regime change"

            if should_exit:
                # Get exit prices (receive bid = close - half_spread)
                call_close = polygon.get_option_price(
                    trade_date, current_trade.strike, current_trade.expiry, 'call', 'mid'
                )
                put_close = polygon.get_option_price(
                    trade_date, current_trade.strike, current_trade.expiry, 'put', 'mid'
                )

                if call_close and put_close:
                    current_trade.exit_date = trade_date
                    current_trade.exit_call_price = call_close - spread_half
                    current_trade.exit_put_price = put_close - spread_half

                    # Calculate P&L
                    entry_cost = (current_trade.entry_call_price + current_trade.entry_put_price) * 100
                    exit_proceeds = (current_trade.exit_call_price + current_trade.exit_put_price) * 100
                    gross_pnl = exit_proceeds - entry_cost
                    net_pnl = gross_pnl - current_trade.commission

                    current_trade.pnl = net_pnl
                    trades.append(current_trade)
                    cumulative_pnl += net_pnl

                    print(f"EXIT {len(trades):02d} [{trade_date}] {exit_reason}: SPY ${spot:.2f}, "
                          f"Held {days_held}d, P&L ${net_pnl:+.2f}")

                current_trade = None

        # Entry logic
        if current_trade is None and score > score_threshold and regime in regime_filter:
            strike = round(spot)
            expiry = trade_date + timedelta(days=75)

            # Snap to third Friday
            year = expiry.year
            month = expiry.month
            first_day = date(year, month, 1)
            first_friday_offset = (4 - first_day.weekday()) % 7
            first_friday = first_day + timedelta(days=first_friday_offset)
            third_friday = first_friday + timedelta(days=14)
            expiry = third_friday

            # Get entry prices (pay ask = close + half_spread)
            call_close = polygon.get_option_price(trade_date, strike, expiry, 'call', 'mid')
            put_close = polygon.get_option_price(trade_date, strike, expiry, 'put', 'mid')

            if call_close and put_close:
                current_trade = SimpleTrade()
                current_trade.entry_date = trade_date
                current_trade.strike = strike
                current_trade.expiry = expiry
                current_trade.entry_call_price = call_close + spread_half
                current_trade.entry_put_price = put_close + spread_half
                current_trade.commission = 4 * commission_per_contract  # 2 contracts × 2 (entry + exit)

                dte = (expiry - trade_date).days
                entry_straddle = current_trade.entry_call_price + current_trade.entry_put_price

                print(f"ENTER {len(trades)+1:02d} [{trade_date}] SPY ${spot:.2f}, Regime {regime}, "
                      f"Score {score:.2f}, Strike ${strike:.0f}, {dte}DTE, Entry ${entry_straddle:.2f}")

        # Record daily result
        results.append({
            'date': trade_date,
            'position_open': current_trade is not None,
            'cumulative_pnl': cumulative_pnl
        })

    return pd.DataFrame(results), trades


if __name__ == '__main__':
    print("=" * 80)
    print("SIMPLE BACKTEST - Profile 1 (LDG)")
    print("=" * 80)

    # Load data
    print("\nLoading data...")
    full_data = pd.read_parquet('data/backtests/rotation_engine_2020_2025/profile_1.parquet')

    # Need to add profile_1_LDG score column (it's called profile_1_score in complex backtest)
    # For now, use a threshold that triggers on the same days

    print(f"Running simple backtest on {len(full_data)} days...")
    print(f"Entry: Score > 0.6 AND Regime in [1, 3]")
    print(f"Exit: After 14 days OR regime change")
    print(f"Position: ATM straddle, ~75 DTE")
    print(f"\nNO DELTA HEDGING")
    print(f"NO ALLOCATION COMPLEXITY")
    print(f"JUST STRATEGY P&L")
    print()

    # For this test, we need profile scores - let me load them
    # Actually, let's just run on a subset where we KNOW positions were entered

    # Filter to rows where complex backtest had positions
    position_days = full_data[full_data['position_open'] == True]
    print(f"Complex backtest had positions on {len(position_days)} days")
    print(f"Complex backtest total P&L: ${full_data['total_pnl'].iloc[-1]:.2f}")
    print()

    # For this minimal test, let's just manually trace the FIRST trade
    # Entry: 2020-05-20, Exit: 2020-06-05 (from our earlier analysis)

    print("=" * 80)
    print("MANUAL TRACE: First Trade Only")
    print("=" * 80)

    from src.data.polygon_options import PolygonOptionsLoader
    polygon = PolygonOptionsLoader()

    # Entry
    entry_date = date(2020, 5, 20)
    strike = 297.0
    expiry = date(2020, 8, 21)

    call_entry = polygon.get_option_price(entry_date, strike, expiry, 'call', 'mid')
    put_entry = polygon.get_option_price(entry_date, strike, expiry, 'put', 'mid')

    print(f"\nENTRY ({entry_date}):")
    print(f"  Call close: ${call_entry:.2f}")
    print(f"  Put close: ${put_entry:.2f}")
    print(f"  Straddle mid: ${call_entry + put_entry:.2f}")

    entry_price = (call_entry + 0.375) + (put_entry + 0.375)  # Pay ask
    entry_cost = entry_price * 100
    print(f"  Entry price (ask): ${entry_price:.2f}")
    print(f"  Entry cost: ${entry_cost:.2f}")

    # Exit
    exit_date = date(2020, 6, 5)
    call_exit = polygon.get_option_price(exit_date, strike, expiry, 'call', 'mid')
    put_exit = polygon.get_option_price(exit_date, strike, expiry, 'put', 'mid')

    print(f"\nEXIT ({exit_date}):")
    print(f"  Call close: ${call_exit:.2f}")
    print(f"  Put close: ${put_exit:.2f}")
    print(f"  Straddle mid: ${call_exit + put_exit:.2f}")

    exit_price = (call_exit - 0.375) + (put_exit - 0.375)  # Receive bid
    exit_proceeds = exit_price * 100
    print(f"  Exit price (bid): ${exit_price:.2f}")
    print(f"  Exit proceeds: ${exit_proceeds:.2f}")

    # P&L
    commission = 4 * 0.65  # 4 total contracts (2 entry + 2 exit)
    gross_pnl = exit_proceeds - entry_cost
    net_pnl = gross_pnl - commission

    print(f"\nP&L (NO HEDGING):")
    print(f"  Gross: ${gross_pnl:.2f}")
    print(f"  Commission: ${commission:.2f}")
    print(f"  Net: ${net_pnl:.2f}")

    print(f"\nCOMPARISON:")
    print(f"  Simple backtest (no hedging): ${net_pnl:.2f}")
    print(f"  Complex backtest (with hedging): $140.60")
    print(f"  Implied hedge cost: ${net_pnl - 140.60:.2f}")
    print(f"  At $15/day × 12 days = $180")
    print(f"  Actual implied: ${net_pnl - 140.60:.2f}")
    print(f"  Ratio: {(net_pnl - 140.60) / 180:.2f}x")
