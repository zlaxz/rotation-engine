#!/usr/bin/env python3
"""
DEAD SIMPLE STRATEGY TESTER

Goal: Test if Profile 1 (LDG) actually makes money, ignoring ALL complexity.

NO:
- Delta hedging
- Portfolio allocation
- Complex position tracking
- Greeks (for now)

YES:
- Real Polygon prices
- Simple entry/exit
- Clear P&L
- Easy to verify

Strategy: Long ATM straddle when Profile 1 scores high in Trend Up regime
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
import numpy as np
from datetime import date, timedelta
from src.data.polygon_options import PolygonOptionsLoader

print("=" * 80)
print("SIMPLE STRATEGY TESTER - Profile 1 (Long-Dated Gamma)")
print("=" * 80)

# Load data
print("\nLoading data...")
# Use pre-computed data from backtest
profile_1_data = pd.read_parquet('data/backtests/rotation_engine_2020_2025/profile_1.parquet')
print(f"Loaded {len(profile_1_data)} days")

# Load Polygon
polygon = PolygonOptionsLoader()

# Find all entry points (when position_open first becomes True after being False)
entries = []
prev_open = False
for idx, row in profile_1_data.iterrows():
    if row['position_open'] and not prev_open:
        entries.append(idx)
    prev_open = row['position_open']

print(f"\nFound {len(entries)} trade entries")

# Trace FIRST trade manually with real prices
if len(entries) > 0:
    entry_idx = entries[0]
    entry_row = profile_1_data.iloc[entry_idx]

    # Find exit
    exit_idx = entry_idx
    while exit_idx < len(profile_1_data) - 1:
        exit_idx += 1
        if not profile_1_data.iloc[exit_idx]['position_open']:
            break

    exit_row = profile_1_data.iloc[exit_idx - 1]  # Last day position was open

    print(f"\n" + "=" * 80)
    print(f"TRACE TRADE 1 (Using REAL Polygon prices)")
    print("=" * 80)

    # Entry
    entry_date_raw = entry_row['date']
    if isinstance(entry_date_raw, pd.Timestamp):
        entry_date = entry_date_raw.date()
    else:
        entry_date = entry_date_raw

    entry_spy = entry_row['spot']
    strike = round(entry_spy)
    expiry = entry_date + timedelta(days=75)

    print(f"\nENTRY ({entry_date}):")
    print(f"  SPY: ${entry_spy:.2f}")
    print(f"  Strike: ${strike:.0f}")
    print(f"  Expiry: {expiry} (75 DTE)")

    # Get REAL Polygon prices
    call_close = polygon.get_option_price(entry_date, strike, expiry, 'call', 'mid')
    put_close = polygon.get_option_price(entry_date, strike, expiry, 'put', 'mid')

    if call_close and put_close:
        straddle_mid = call_close + put_close
        print(f"  Call close (Polygon): ${call_close:.2f}")
        print(f"  Put close (Polygon): ${put_close:.2f}")
        print(f"  Straddle mid: ${straddle_mid:.2f}")

        # Entry execution (pay ask = mid + half spread)
        spread = 0.75  # ATM straddle spread
        entry_price = straddle_mid + (spread / 2)
        entry_cost = entry_price * 100
        commission = 2 * 0.65  # 2 contracts

        print(f"  Entry price (mid + half spread): ${entry_price:.2f}")
        print(f"  Entry cost: ${entry_cost:.2f}")
        print(f"  Commission: ${commission:.2f}")

        # Exit
        exit_date_raw = exit_row['date']
        if isinstance(exit_date_raw, pd.Timestamp):
            exit_date = exit_date_raw.date()
        else:
            exit_date = exit_date_raw

        exit_spy = exit_row['spot']
        days_held = (exit_date - entry_date).days

        print(f"\nEXIT ({exit_date}):")
        print(f"  SPY: ${exit_spy:.2f} ({((exit_spy/entry_spy)-1)*100:+.2f}%)")
        print(f"  Days held: {days_held}")

        # Get REAL exit prices
        call_close_exit = polygon.get_option_price(exit_date, strike, expiry, 'call', 'mid')
        put_close_exit = polygon.get_option_price(exit_date, strike, expiry, 'put', 'mid')

        if call_close_exit and put_close_exit:
            straddle_mid_exit = call_close_exit + put_close_exit
            print(f"  Call close (Polygon): ${call_close_exit:.2f}")
            print(f"  Put close (Polygon): ${put_close_exit:.2f}")
            print(f"  Straddle mid: ${straddle_mid_exit:.2f}")

            # Exit execution (receive bid = mid - half spread)
            exit_price = straddle_mid_exit - (spread / 2)
            exit_proceeds = exit_price * 100

            print(f"  Exit price (mid - half spread): ${exit_price:.2f}")
            print(f"  Exit proceeds: ${exit_proceeds:.2f}")

            # P&L
            gross_pnl = exit_proceeds - entry_cost
            net_pnl = gross_pnl - commission

            print(f"\nP&L:")
            print(f"  Gross: ${gross_pnl:.2f}")
            print(f"  - Commission: ${commission:.2f}")
            print(f"  = Net P&L: ${net_pnl:.2f}")

            print(f"\n  BACKTEST SHOWS: ${exit_row['total_pnl']:.2f}")
            print(f"  SIMPLE CALC: ${net_pnl:.2f}")
            print(f"  Difference: ${abs(net_pnl - exit_row['total_pnl']):.2f}")

            if abs(net_pnl - exit_row['total_pnl']) < 50:
                print(f"\n  ✓✓✓ CLOSE MATCH!")
                print(f"      The complex backtester matches simple calc (within $50)")
                print(f"      Difference is likely delta hedging costs")
            else:
                print(f"\n  ❌ BIG MISMATCH")
                print(f"     There's a bug somewhere in the complex backtester")

        else:
            print(f"  ❌ No Polygon data for exit date")
    else:
        print(f"  ❌ No Polygon data for entry date")

else:
    print("No trades found")
