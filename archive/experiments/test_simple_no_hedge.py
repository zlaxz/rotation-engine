#!/usr/bin/env python3
"""
Test Profile 1 WITHOUT hedging using pre-computed backtest data.
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
from datetime import date
from src.data.polygon_options import PolygonOptionsLoader

print("=" * 80)
print("PROFILE 1 - SIMPLE P&L (No Hedging)")
print("=" * 80)

# Load pre-computed backtest data (has regimes, dates, positions)
data = pd.read_parquet('data/backtests/rotation_engine_2020_2025/profile_1.parquet')
print(f"\nLoaded {len(data)} days")

# Find all trades (entry points)
data['date_normalized'] = pd.to_datetime(data['date']).dt.date

entries = []
prev_open = False
for idx in range(len(data)):
    if data.iloc[idx]['position_open'] and not prev_open:
        entries.append(idx)
    prev_open = data.iloc[idx]['position_open']

print(f"Found {len(entries)} trades in complex backtest")

# Initialize Polygon loader
polygon = PolygonOptionsLoader()

# Trace each trade with simple P&L (no hedging)
spread_half = 0.015  # $0.03 total spread (3x penny spread, conservative)
commission_total = 2 * 0.65 * 2  # 4 contracts total

trades_simple = []
total_pnl_simple = 0.0

print(f"\nRe-calculating P&L for each trade WITHOUT delta hedging:")
print("-" * 80)

for trade_num, entry_idx in enumerate(entries[:10], 1):  # First 10 trades for now
    entry_row = data.iloc[entry_idx]
    entry_date = entry_row['date_normalized']
    entry_spy = entry_row['spot']
    strike = round(entry_spy)

    # Find exit
    exit_idx = entry_idx
    while exit_idx < len(data) - 1:
        exit_idx += 1
        if not data.iloc[exit_idx]['position_open']:
            break

    exit_row = data.iloc[exit_idx - 1]
    exit_date = exit_row['date_normalized']
    exit_spy = exit_row['spot']

    # Calculate expiry (third Friday ~75 DTE out)
    from datetime import timedelta
    target_date = entry_date + timedelta(days=75)
    year, month = target_date.year, target_date.month
    first_day = date(year, month, 1)
    first_friday_offset = (4 - first_day.weekday()) % 7
    first_friday = first_day + timedelta(days=first_friday_offset)
    third_friday = first_friday + timedelta(days=14)
    expiry = third_friday

    # Get entry prices
    call_entry = polygon.get_option_price(entry_date, strike, expiry, 'call', 'mid')
    put_entry = polygon.get_option_price(entry_date, strike, expiry, 'put', 'mid')

    # Get exit prices
    call_exit = polygon.get_option_price(exit_date, strike, expiry, 'call', 'mid')
    put_exit = polygon.get_option_price(exit_date, strike, expiry, 'put', 'mid')

    if all([call_entry, put_entry, call_exit, put_exit]):
        # Simple P&L (no hedging)
        entry_price = (call_entry + spread_half) + (put_entry + spread_half)
        exit_price = (call_exit - spread_half) + (put_exit - spread_half)

        entry_cost = entry_price * 100
        exit_proceeds = exit_price * 100
        gross = exit_proceeds - entry_cost
        net = gross - commission_total

        trades_simple.append({
            'trade': trade_num,
            'entry': entry_date,
            'exit': exit_date,
            'days': (exit_date - entry_date).days,
            'spy_move': ((exit_spy / entry_spy) - 1) * 100,
            'net_pnl': net
        })

        total_pnl_simple += net

        # Get complex backtest P&L for comparison
        complex_pnl = exit_row['total_pnl'] - entry_row['total_pnl'] if idx > 0 else exit_row['total_pnl']

        print(f"Trade {trade_num:02d}: {entry_date} → {exit_date} ({(exit_date-entry_date).days}d), "
              f"SPY {((exit_spy/entry_spy)-1)*100:+.1f}%, "
              f"Simple ${net:+.0f}, Complex ${complex_pnl:+.0f}")

    else:
        print(f"Trade {trade_num:02d}: SKIP (no Polygon data)")

print("-" * 80)
print(f"\nSIMPLE BACKTEST (10 trades, no hedging):")
print(f"Total P&L: ${total_pnl_simple:,.2f}")
print(f"Avg per trade: ${total_pnl_simple / len(trades_simple):.2f}")

# Compare to complex
print(f"\nComplex backtest (28 trades, with hedging):")
print(f"Total P&L: $-6,553.08")

print(f"\nDifference: ${total_pnl_simple - (-6553.08):,.2f}")
print(f"This is what delta hedging COST")
