#!/usr/bin/env python3
"""
Exit at Peak Analysis

Question: If we had exited within 10% of the PEAK P&L for each trade,
what would total P&L be?

This is hindsight analysis to see how much we're leaving on the table
with our dumb exit strategy.
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
print("EXIT AT PEAK ANALYSIS - All 42 Trades")
print("=" * 80)
print("\nStrategy: Exit within 10% of PEAK P&L for that trade")
print("(This is hindsight - shows how much we left on table)\n")

comparison = []
total_actual = 0
total_at_peak = 0

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
    expiry = ff + timedelta(days=14)

    # Entry prices
    call_entry = polygon.get_option_price(entry_date, strike, expiry, 'call', 'mid')
    put_entry = polygon.get_option_price(entry_date, strike, expiry, 'put', 'mid')

    if not call_entry or not put_entry:
        continue

    entry_straddle = call_entry + put_entry
    entry_cost = (entry_straddle + 0.03) * 100

    # Trace ENTIRE trade window to find PEAK
    trade_days = spy_df[(spy_df['date'] >= entry_date) & (spy_df['date'] <= exit_date)]

    peak_pnl = -999999
    peak_day = 1
    peak_date = entry_date
    all_pnls = []

    for day_num, (_, day_row) in enumerate(trade_days.iterrows(), 1):
        day_date = day_row['date']

        call_mid = polygon.get_option_price(day_date, strike, expiry, 'call', 'mid')
        put_mid = polygon.get_option_price(day_date, strike, expiry, 'put', 'mid')

        if call_mid and put_mid:
            exit_price = (call_mid + put_mid - 0.03)  # Receive bid
            pnl = exit_price * 100 - entry_cost - 2.60

            all_pnls.append((day_num, day_date, pnl))

            if pnl > peak_pnl:
                peak_pnl = pnl
                peak_day = day_num
                peak_date = day_date

    # Now find first day where P&L >= 90% of peak
    exit_at_peak_day = peak_day
    exit_at_peak_pnl = peak_pnl

    for day_num, day_date, pnl in all_pnls:
        if pnl >= peak_pnl * 0.9:  # Within 10% of peak
            exit_at_peak_day = day_num
            exit_at_peak_pnl = pnl
            break

    actual_pnl = trade['pnl']
    improvement = exit_at_peak_pnl - actual_pnl

    total_actual += actual_pnl
    total_at_peak += exit_at_peak_pnl

    comparison.append({
        'trade': trade_num,
        'actual_days': trade['days'],
        'actual_pnl': actual_pnl,
        'peak_pnl': peak_pnl,
        'peak_day': peak_day,
        'exit_at_peak_day': exit_at_peak_day,
        'exit_at_peak_pnl': exit_at_peak_pnl,
        'improvement': improvement
    })

    status = "✓✓" if improvement > 100 else ("✓" if improvement > 0 else "=")
    print(f"{status} Trade {trade_num:02d}: Peak ${peak_pnl:>7.0f} (Day {peak_day:>2}), "
          f"90% Peak ${exit_at_peak_pnl:>7.0f} (Day {exit_at_peak_day:>2}), "
          f"Actual ${actual_pnl:>7.0f} (Day {trade['days']:>2}), "
          f"Gain ${improvement:>6.0f}")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"\nActual exits (14 days):           ${total_actual:>10,.2f}")
print(f"Exit at 90% of peak:              ${total_at_peak:>10,.2f}")
print(f"Left on table:                    ${total_at_peak - total_actual:>10,.2f}")

df = pd.DataFrame(comparison)
big_improvements = df[df['improvement'] > 100].sort_values('improvement', ascending=False)

if len(big_improvements) > 0:
    print(f"\nTop 10 trades where we left money on table:")
    for _, row in big_improvements.head(10).iterrows():
        print(f"  Trade {int(row['trade']):02d}: ${row['improvement']:>6.0f} left "
              f"(should exit Day {int(row['exit_at_peak_day'])} vs Day {int(row['actual_days'])})")

df.to_csv('exit_at_peak_analysis.csv', index=False)
print(f"\nSaved: exit_at_peak_analysis.csv")
