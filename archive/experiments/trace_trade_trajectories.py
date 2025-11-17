#!/usr/bin/env python3
"""
Trace individual trades day-by-day to see if we're exiting like idiots.

Question: Are we giving back profits by holding too long?
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
import numpy as np
from datetime import date, timedelta
from src.data.polygon_options import PolygonOptionsLoader
import glob

# Load SPY daily data
print("Loading SPY data...")
spy_files = sorted(glob.glob('/Volumes/VelocityData/velocity_om/parquet/stock/SPY/*.parquet'))
spy_daily = []
for f in spy_files:
    df = pd.read_parquet(f)
    if len(df) > 0:
        spy_daily.append({
            'date': pd.to_datetime(df['ts'].iloc[0]).date(),
            'open': df['open'].iloc[0],
            'high': df['high'].max(),
            'low': df['low'].min(),
            'close': df['close'].iloc[-1]
        })

spy_df = pd.DataFrame(spy_daily)
print(f"Loaded {len(spy_df)} days\n")

# Load the clean backtest results
results = pd.read_csv('clean_results.csv')
results['entry'] = pd.to_datetime(results['entry']).dt.date
results['exit'] = pd.to_datetime(results['exit']).dt.date

polygon = PolygonOptionsLoader()

# Pick trades to trace:
# 1. Trade 4: Winner (+$113)
# 2. Trade 9: Winner (+$597)
# 3. Trade 2: Loser (-$550)
# 4. Trade 8: Loser (-$203)

for trade_num in [4, 9, 2, 8]:
    trade = results.iloc[trade_num - 1]

    entry_date = trade['entry']
    exit_date = trade['exit']

    # Look up SPY prices
    entry_spy_row = spy_df[spy_df['date'] == entry_date]
    exit_spy_row = spy_df[spy_df['date'] == exit_date]

    if len(entry_spy_row) == 0 or len(exit_spy_row) == 0:
        print(f"⚠️  Trade {trade_num}: Missing SPY data, skipping\n")
        continue

    entry_spy = entry_spy_row.iloc[0]['close']
    exit_spy = exit_spy_row.iloc[0]['close']
    strike = round(entry_spy)

    # Calculate expiry (75 DTE)
    target = entry_date + timedelta(days=75)
    fd = date(target.year, target.month, 1)
    ff = fd + timedelta(days=(4 - fd.weekday()) % 7)
    expiry = ff + timedelta(days=14)

    print("=" * 80)
    print(f"TRADE {trade_num} TRAJECTORY")
    print("=" * 80)
    print(f"Entry: {entry_date}, SPY ${entry_spy:.2f}")
    print(f"Exit: {exit_date}, SPY ${exit_spy:.2f}")
    print(f"Strike: ${strike}, Expiry: {expiry}")
    print(f"Held: {trade['days']} days")
    print(f"SPY move: {trade['spy_move']:+.2f}%")
    print(f"Final P&L: ${trade['pnl']:+.2f}")
    print()

    # Get entry prices to calculate entry cost
    call_entry = polygon.get_option_price(entry_date, strike, expiry, 'call', 'mid')
    put_entry = polygon.get_option_price(entry_date, strike, expiry, 'put', 'mid')

    if not call_entry or not put_entry:
        print(f"⚠️  No entry price data, skipping\n")
        continue

    entry_price = (call_entry + 0.015) + (put_entry + 0.015)  # Pay ask
    entry_cost = entry_price * 100

    # Get SPY prices for each day in trade
    trade_days = spy_df[(spy_df['date'] >= entry_date) & (spy_df['date'] <= exit_date)]

    print(f"{'Day':>3} {'Date':>12} {'SPY':>8} {'Change':>8} {'Call':>8} {'Put':>8} {'Straddle':>10} {'P&L':>10} {'Exit?':>15}")
    print("-" * 100)
    best_pnl = -999999
    best_day = None

    for day_num, (idx, day_row) in enumerate(trade_days.iterrows(), 1):
        day_date = day_row['date']
        day_spy = day_row['close']
        spy_change = ((day_spy / entry_spy) - 1) * 100

        # Get option prices
        call_mid = polygon.get_option_price(day_date, strike, expiry, 'call', 'mid')
        put_mid = polygon.get_option_price(day_date, strike, expiry, 'put', 'mid')

        if call_mid and put_mid:
            straddle_mid = call_mid + put_mid
            # Exit price (receive bid)
            exit_price = (call_mid - 0.015) + (put_mid - 0.015)
            current_proceeds = exit_price * 100
            current_pnl = current_proceeds - entry_cost - 2.60

            # Track best P&L
            if current_pnl > best_pnl:
                best_pnl = current_pnl
                best_day = day_num

            # Exit signal
            exit_signal = ""
            if day_num >= 14:
                exit_signal = "Hold period"
            elif day_date == exit_date:
                exit_signal = "Actual exit"

            # Suggest better exits
            if current_pnl > 200 and day_num < 7:
                exit_signal += " [TAKE PROFIT?]"

            print(f"{day_num:>3} {str(day_date):>12} ${day_spy:>7.2f} {spy_change:>7.2f}% "
                  f"${call_mid:>7.2f} ${put_mid:>7.2f} ${straddle_mid:>9.2f} ${current_pnl:>9.2f} {exit_signal:>15}")

    print("-" * 100)
    print(f"Best P&L: ${best_pnl:.2f} on Day {best_day}")
    print(f"Actual exit: ${trade['pnl']:.2f} on Day {trade['days']}")
    print(f"Left on table: ${best_pnl - trade['pnl']:.2f}")

    if best_pnl - trade['pnl'] > 100:
        print(f"⚠️  Gave back ${best_pnl - trade['pnl']:.2f} by holding too long!")

    print()
