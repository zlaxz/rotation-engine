#!/usr/bin/env python3
"""
Analyze ALL trades with intelligent exit strategy.

Exit rules:
1. Trailing stop: Exit when P&L drops 10% below peak
2. Stop loss: Exit when position loses 10% (excluding costs)
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
import numpy as np
from datetime import date, timedelta
from src.data.polygon_options import PolygonOptionsLoader
import glob

# Load data
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
results = pd.read_csv('clean_results.csv')
results['entry'] = pd.to_datetime(results['entry']).dt.date
results['exit'] = pd.to_datetime(results['exit']).dt.date

polygon = PolygonOptionsLoader()

print("=" * 80)
print("SMART EXIT ANALYSIS - All 42 Trades")
print("=" * 80)
print("\nExit Strategy:")
print("  1. Trailing stop: Exit when P&L drops 10% below peak")
print("  2. Stop loss: Exit when straddle value drops 10%")
print()

comparison = []
total_dumb_exit = 0
total_smart_exit = 0

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

    # Calculate expiry
    target = entry_date + timedelta(days=75)
    fd = date(target.year, target.month, 1)
    ff = fd + timedelta(days=(4 - fd.weekday()) % 7)
    expiry = ff + timedelta(days=14)

    # Get entry prices
    call_entry = polygon.get_option_price(entry_date, strike, expiry, 'call', 'mid')
    put_entry = polygon.get_option_price(entry_date, strike, expiry, 'put', 'mid')

    if not call_entry or not put_entry:
        continue

    entry_straddle = call_entry + put_entry
    entry_price = entry_straddle + 0.03  # Pay ask
    entry_cost = entry_price * 100

    # Trace day-by-day
    trade_days = spy_df[(spy_df['date'] >= entry_date) & (spy_df['date'] <= exit_date)]

    peak_pnl = -999999
    peak_day = 1
    smart_exit_day = None
    smart_exit_pnl = None

    for day_num, (day_idx, day_row) in enumerate(trade_days.iterrows(), 1):
        day_date = day_row['date']
        day_spy = day_row['close']

        # Get option prices
        call_mid = polygon.get_option_price(day_date, strike, expiry, 'call', 'mid')
        put_mid = polygon.get_option_price(day_date, strike, expiry, 'put', 'mid')

        if not call_mid or not put_mid:
            continue

        straddle_mid = call_mid + put_mid
        exit_price = straddle_mid - 0.03  # Receive bid
        proceeds = exit_price * 100
        pnl = proceeds - entry_cost - 2.60

        # Check stop loss (straddle value down 10%)
        straddle_change = ((straddle_mid / entry_straddle) - 1)
        if straddle_change < -0.10:
            smart_exit_day = day_num
            smart_exit_pnl = pnl
            break

        # Update peak
        if pnl > peak_pnl:
            peak_pnl = pnl
            peak_day = day_num

        # Check trailing stop (P&L dropped 10% from peak)
        drawdown_from_peak = (pnl - peak_pnl) / abs(peak_pnl) if peak_pnl != 0 else 0
        if peak_pnl > 0 and drawdown_from_peak < -0.10:
            smart_exit_day = day_num
            smart_exit_pnl = pnl
            break

    # If no exit triggered, use actual exit
    if smart_exit_day is None:
        smart_exit_day = trade['days']
        smart_exit_pnl = trade['pnl']

    dumb_exit_pnl = trade['pnl']
    improvement = smart_exit_pnl - dumb_exit_pnl

    total_dumb_exit += dumb_exit_pnl
    total_smart_exit += smart_exit_pnl

    comparison.append({
        'trade': trade_num,
        'entry': entry_date,
        'dumb_days': trade['days'],
        'smart_days': smart_exit_day,
        'peak_pnl': peak_pnl,
        'peak_day': peak_day,
        'dumb_pnl': dumb_exit_pnl,
        'smart_pnl': smart_exit_pnl,
        'improvement': improvement
    })

    status = "✓" if smart_exit_pnl > dumb_exit_pnl else "="
    print(f"{status} Trade {trade_num:02d}: Peak ${peak_pnl:>7.0f} (Day {peak_day}), "
          f"Dumb ${dumb_exit_pnl:>7.0f} (Day {trade['days']}), "
          f"Smart ${smart_exit_pnl:>7.0f} (Day {smart_exit_day}), "
          f"Gain ${improvement:>6.0f}")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"\nDumb exits (hold 14 days):      ${total_dumb_exit:>10,.2f}")
print(f"Smart exits (trailing stop):    ${total_smart_exit:>10,.2f}")
print(f"Improvement:                    ${total_smart_exit - total_dumb_exit:>10,.2f}")

df = pd.DataFrame(comparison)
big_improvements = df[df['improvement'] > 100].sort_values('improvement', ascending=False)

if len(big_improvements) > 0:
    print(f"\nTop 10 trades improved by smart exits:")
    for _, row in big_improvements.head(10).iterrows():
        print(f"  Trade {int(row['trade']):02d}: ${row['improvement']:>6.0f} gain "
              f"(exited Day {int(row['smart_days'])} vs Day {int(row['dumb_days'])})")

df.to_csv('smart_exit_analysis.csv', index=False)
print(f"\nSaved: smart_exit_analysis.csv")
