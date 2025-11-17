#!/usr/bin/env python3
"""
CONSERVATIVE EXIT ASSUMPTION TEST

Exit rules (for daily bar limitations):
1. Stop loss: Position loses 10% → exit
2. Profit target: Capture 30% of move from entry to peak

This is conservative baseline - real system should beat this.
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
print("CONSERVATIVE EXIT ASSUMPTION - 42 Trades")
print("=" * 80)
print("\nExit logic:")
print("  Stop loss: Position -10%")
print("  Profit: Capture 30% of (peak - entry)")
print()

total_actual = 0
total_conservative = 0

for idx, trade in results.iterrows():
    trade_num = idx + 1
    entry_date = trade['entry']
    exit_date = trade['exit']

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

    # Find peak P&L in the window
    trade_days = spy_df[(spy_df['date'] >= entry_date) & (spy_df['date'] <= exit_date)]

    peak_pnl = -999999
    hit_stop_loss = False

    for day_num, (_, day_row) in enumerate(trade_days.iterrows(), 1):
        day_date = day_row['date']

        call_mid = polygon.get_option_price(day_date, strike, expiry, 'call', 'mid')
        put_mid = polygon.get_option_price(day_date, strike, expiry, 'put', 'mid')

        if call_mid and put_mid:
            straddle_mid = call_mid + put_mid
            pnl = (straddle_mid - 0.03) * 100 - entry_cost - 2.60

            # Check stop loss (position value, not P&L)
            position_change = (straddle_mid / entry_straddle) - 1
            if position_change < -0.10:
                hit_stop_loss = True
                # Stop loss P&L = -10% of entry cost - commission
                conservative_pnl = entry_cost * -0.10 - 2.60
                break

            if pnl > peak_pnl:
                peak_pnl = pnl

    # If didn't hit stop loss, assume we capture 30% of (peak - entry)
    if not hit_stop_loss:
        if peak_pnl > 0:
            # Profit scenario: capture 30% of the profit
            conservative_pnl = peak_pnl * 0.30
        else:
            # Loss scenario: position never went positive
            # Assume we exit quickly at -10% stop loss
            # Stop loss P&L = entry_cost * -0.10 - commission
            conservative_pnl = entry_cost * -0.10 - 2.60

    actual_pnl = trade['pnl']

    total_actual += actual_pnl
    total_conservative += conservative_pnl

    diff = conservative_pnl - actual_pnl
    sign = "✓" if diff > 50 else ("=" if abs(diff) < 50 else "✗")
    print(f"{sign} Trade {trade_num:02d}: Peak ${peak_pnl:>6.0f}, "
          f"Actual ${actual_pnl:>6.0f}, Conservative ${conservative_pnl:>6.0f}, "
          f"Diff ${diff:>5.0f}")

print("\n" + "=" * 80)
print("TOTALS")
print("=" * 80)
print(f"Actual (14-day hold):        ${total_actual:>10,.0f}")
print(f"Conservative (30% capture):  ${total_conservative:>10,.0f}")
print(f"Improvement:                 ${total_conservative - total_actual:>10,.0f}")

print("\n" + "=" * 80)
print("VERDICT")
print("=" * 80)
if total_conservative > 0:
    print(f"✅ Strategy HAS EDGE if we can capture 30% of peaks")
    print(f"   Worth building intelligent exit system")
else:
    print(f"❌ Strategy NO EDGE even at 30% capture")
    print(f"   Not worth pursuing")
