#!/usr/bin/env python3
"""
Test smart exits on the EXACT SAME 42 trades.
No re-entries. Just: would we have done better with smart exits?
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
from datetime import date, timedelta
from src.data.polygon_options import PolygonOptionsLoader
import glob

# Load SPY
spy_files = sorted(glob.glob('/Volumes/VelocityData/velocity_om/parquet/stock/SPY/*.parquet'))
spy_daily = []
for f in spy_files:
    df = pd.read_parquet(f)
    if len(df) > 0:
        spy_daily.append({
            'date': pd.to_datetime(df['ts'].iloc[0]).date(),
            'close': df['close'].iloc[-1]
        })

spy_df = pd.DataFrame(spy_daily)

# Load the 42 original trades
results = pd.read_csv('clean_results.csv')
results['entry'] = pd.to_datetime(results['entry']).dt.date
results['exit'] = pd.to_datetime(results['exit']).dt.date

polygon = PolygonOptionsLoader()

print("=" * 80)
print("SMART EXITS - SAME 42 TRADES")
print("=" * 80)
print("\nTesting on exact same entry/exit windows")
print("Exit: 50% trail stop OR 10% position stop loss")
print()

total_dumb = 0
total_smart = 0

for idx, trade in results.iterrows():
    trade_num = idx + 1
    entry_date = trade['entry']
    exit_date = trade['exit']

    # Get entry SPY
    entry_spy_row = spy_df[spy_df['date'] == entry_date]
    if len(entry_spy_row) == 0:
        continue

    entry_spy = entry_spy_row.iloc[0]['close']
    strike = round(entry_spy)

    # Expiry
    target = entry_date + timedelta(days=75)
    fd = date(target.year, target.month, 1)
    ff = fd + timedelta(days=(4 - fd.weekday()) % 7)
    from datetime import date
    expiry = ff + timedelta(days=14)

    # Entry prices
    call_entry = polygon.get_option_price(entry_date, strike, expiry, 'call', 'mid')
    put_entry = polygon.get_option_price(entry_date, strike, expiry, 'put', 'mid')

    if not call_entry or not put_entry:
        continue

    entry_straddle = call_entry + put_entry
    entry_cost = (entry_straddle + 0.03) * 100

    # Trace within the SAME window
    trade_days = spy_df[(spy_df['date'] >= entry_date) & (spy_df['date'] <= exit_date)]

    peak_pnl = -999999
    smart_exit_pnl = None

    for day_num, (_, day_row) in enumerate(trade_days.iterrows(), 1):
        day_date = day_row['date']

        call_mid = polygon.get_option_price(day_date, strike, expiry, 'call', 'mid')
        put_mid = polygon.get_option_price(day_date, strike, expiry, 'put', 'mid')

        if not call_mid or not put_mid:
            continue

        straddle_mid = call_mid + put_mid
        exit_price = straddle_mid - 0.03
        pnl = exit_price * 100 - entry_cost - 2.60

        # Update peak
        if pnl > peak_pnl:
            peak_pnl = pnl

        # Exit triggers

        # 1. Trail stop (50% of max profit)
        if peak_pnl > 0:
            trail_level = peak_pnl * 0.50
            if pnl < trail_level:
                smart_exit_pnl = pnl
                break

        # 2. Stop loss (position -10%)
        position_change = (straddle_mid / entry_straddle) - 1
        if position_change < -0.10:
            smart_exit_pnl = pnl
            break

    # If no exit triggered, use end of window
    if smart_exit_pnl is None:
        smart_exit_pnl = trade['pnl']

    dumb_pnl = trade['pnl']
    improvement = smart_exit_pnl - dumb_pnl

    total_dumb += dumb_pnl
    total_smart += smart_exit_pnl

    if abs(improvement) > 50:
        sign = "✓" if improvement > 0 else "✗"
        print(f"{sign} Trade {trade_num:02d}: Dumb ${dumb_pnl:>7.0f}, Smart ${smart_exit_pnl:>7.0f}, "
              f"Peak ${peak_pnl:>7.0f}, Diff ${improvement:>6.0f}")

print("\n" + "=" * 80)
print("FINAL COMPARISON - SAME 42 TRADES")
print("=" * 80)
print(f"Dumb exits:  ${total_dumb:>10,.0f}")
print(f"Smart exits: ${total_smart:>10,.0f}")
print(f"Improvement: ${total_smart - total_dumb:>10,.0f}")
