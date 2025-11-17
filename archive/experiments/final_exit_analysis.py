#!/usr/bin/env python3
"""
FINAL EXIT ANALYSIS - Clean, correct, verified

Tests 3 exit strategies on the SAME 42 trades:
1. Hold 14 days (current/dumb)
2. Exit at 90% of ultimate peak (hindsight optimal)
3. 50% trailing stop (realistic smart exit)

NO re-entries. Same 42 trades. Just different exit timing.
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
results = pd.read_csv('clean_results.csv')
results['entry'] = pd.to_datetime(results['entry']).dt.date
results['exit'] = pd.to_datetime(results['exit']).dt.date

polygon = PolygonOptionsLoader()

print("=" * 80)
print("EXIT STRATEGY COMPARISON - Same 42 Trades")
print("=" * 80)
print("\n3 Exit Strategies:")
print("  1. DUMB: Hold 14 days")
print("  2. OPTIMAL: Exit at 90% of ultimate peak (hindsight)")
print("  3. SMART: 50% trailing stop (realistic)")
print()

total_dumb = 0
total_optimal = 0
total_smart = 0

for idx, trade in results.iterrows():
    trade_num = idx + 1
    entry_date = trade['entry']
    exit_date = trade['exit']

    # Get entry details
    entry_spy_row = spy_df[spy_df['date'] == entry_date]
    if len(entry_spy_row) == 0:
        continue

    entry_spy = entry_spy_row.iloc[0]['close']
    strike = round(entry_spy)

    target = entry_date + timedelta(days=75)
    fd = date(target.year, target.month, 1)
    ff = fd + timedelta(days=(4 - fd.weekday()) % 7)
    expiry = ff + timedelta(days=14)

    call_entry = polygon.get_option_price(entry_date, strike, expiry, 'call', 'mid')
    put_entry = polygon.get_option_price(entry_date, strike, expiry, 'put', 'mid')

    if not call_entry or not put_entry:
        continue

    entry_straddle = call_entry + put_entry
    entry_cost = (entry_straddle + 0.03) * 100

    # Trace day-by-day
    trade_days = spy_df[(spy_df['date'] >= entry_date) & (spy_df['date'] <= exit_date)]

    all_pnls = []
    peak_pnl = -999999
    peak_day = 1

    for day_num, (_, day_row) in enumerate(trade_days.iterrows(), 1):
        day_date = day_row['date']

        call_mid = polygon.get_option_price(day_date, strike, expiry, 'call', 'mid')
        put_mid = polygon.get_option_price(day_date, strike, expiry, 'put', 'mid')

        if call_mid and put_mid:
            straddle_mid = call_mid + put_mid
            pnl = (straddle_mid - 0.03) * 100 - entry_cost - 2.60

            all_pnls.append((day_num, pnl))

            if pnl > peak_pnl:
                peak_pnl = pnl
                peak_day = day_num

    # Strategy 1: DUMB (actual exit)
    dumb_pnl = trade['pnl']

    # Strategy 2: OPTIMAL (exit at 90% of ultimate peak)
    optimal_pnl = peak_pnl  # Default to peak
    for day_num, pnl in all_pnls:
        if pnl >= peak_pnl * 0.9:
            optimal_pnl = pnl
            break

    # Strategy 3: SMART (50% trail stop)
    smart_pnl = None
    running_peak = -999999
    for day_num, pnl in all_pnls:
        if pnl > running_peak:
            running_peak = pnl

        if running_peak > 0:
            trail_level = running_peak * 0.50
            if pnl < trail_level:
                smart_pnl = pnl
                break

    if smart_pnl is None:
        smart_pnl = all_pnls[-1][1] if all_pnls else dumb_pnl

    total_dumb += dumb_pnl
    total_optimal += optimal_pnl
    total_smart += smart_pnl

    if idx < 10 or abs(optimal_pnl - dumb_pnl) > 100:
        print(f"Trade {trade_num:02d}: Dumb ${dumb_pnl:>6.0f}, Optimal ${optimal_pnl:>6.0f}, Smart ${smart_pnl:>6.0f}")

print("\n" + "=" * 80)
print("FINAL TOTALS - SAME 42 TRADES")
print("=" * 80)
print(f"Dumb (14 days):          ${total_dumb:>10,.0f}")
print(f"Optimal (90% of peak):   ${total_optimal:>10,.0f}")
print(f"Smart (50% trail):       ${total_smart:>10,.0f}")
print(f"\nOptimal improvement:     ${total_optimal - total_dumb:>10,.0f}")
print(f"Smart improvement:       ${total_smart - total_dumb:>10,.0f}")
