#!/usr/bin/env python3
"""
CLEAN BACKTEST - Using Polygon data (stock + options)
Profile 1 (Long-Dated Gamma) - Real costs, no hedging
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
from src.data.polygon_options import PolygonOptionsLoader
import glob
import gzip

print("=" * 80)
print("CLEAN BACKTEST - PROFILE 1 (Using Polygon Data)")
print("=" * 80)

# Load SPY stock data from Polygon minute bars (aggregate to daily)
print("\nLoading SPY data from Polygon minute bars...")
spy_files = sorted(glob.glob('/Volumes/VelocityData/velocity_om/parquet/stock/SPY/*.parquet'))
print(f"Found {len(spy_files)} files")

spy_data = []
for f in spy_files[:500]:  # Load 2020-2021 for now (500 trading days ~2 years)
    df = pd.read_parquet(f)
    # Get daily OHLC from minute bars
    daily = {
        'date': pd.to_datetime(df['ts'].iloc[0]).date(),
        'open': df['open'].iloc[0],
        'high': df['high'].max(),
        'low': df['low'].min(),
        'close': df['close'].iloc[-1],
        'volume': df['volume'].sum()
    }
    spy_data.append(daily)

spy_df = pd.DataFrame(spy_data)
print(f"Loaded {len(spy_df)} days: {spy_df['date'].min()} to {spy_df['date'].max()}")

# Simple features
spy_df['ret'] = spy_df['close'].pct_change()
spy_df['RV10'] = spy_df['ret'].rolling(10).std() * np.sqrt(252)
spy_df['MA20'] = spy_df['close'].rolling(20).mean()
spy_df['slope_MA20'] = (spy_df['MA20'] - spy_df['MA20'].shift(5)) / spy_df['MA20'].shift(5)

# Simple regime: Trend Up (positive slope)
spy_df['regime'] = 0
spy_df.loc[spy_df['slope_MA20'] > 0, 'regime'] = 1

# Simple profile score: High when in uptrend
spy_df['profile_1_score'] = spy_df['slope_MA20'].clip(lower=0) * 10  # Scale up
spy_df['profile_1_score'] = spy_df['profile_1_score'].clip(upper=1)  # Cap at 1

print(f"\nRegime 1 days: {(spy_df['regime']==1).sum()} ({(spy_df['regime']==1).sum()/len(spy_df)*100:.1f}%)")
print(f"High score days (>0.5): {(spy_df['profile_1_score']>0.5).sum()}")

# Run backtest
print(f"\n{'='*80}")
print("RUNNING BACKTEST")
print(f"{'='*80}\n")

polygon = PolygonOptionsLoader()
trades = []
position = None

for idx in range(50, len(spy_df)):  # Skip warmup
    row = spy_df.iloc[idx]
    trade_date = row['date']
    spot = row['close']
    regime = row['regime']
    score = row['profile_1_score']

    # Exit
    if position:
        days_held = (trade_date - position['entry_date']).days

        if days_held >= 14 or regime != 1:
            # Exit prices
            call_mid = polygon.get_option_price(trade_date, position['strike'], position['expiry'], 'call', 'mid')
            put_mid = polygon.get_option_price(trade_date, position['strike'], position['expiry'], 'put', 'mid')

            if call_mid and put_mid:
                exit_price = (call_mid - 0.015) + (put_mid - 0.015)  # Bid
                exit_proceeds = exit_price * 100
                gross = exit_proceeds - position['entry_cost']
                net = gross - 2.60

                position['exit_date'] = trade_date
                position['net_pnl'] = net
                position['days_held'] = days_held
                trades.append(position)

                print(f"Trade {len(trades):02d}: {position['entry_date']} → {trade_date} ({days_held}d), "
                      f"SPY {((spot/position['entry_spot'])-1)*100:+.1f}%, P&L ${net:+.0f}")

            position = None

    # Entry
    if not position and score > 0.5 and regime == 1:
        strike = round(spot)
        target = trade_date + timedelta(days=75)
        first_day = date(target.year, target.month, 1)
        first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
        expiry = first_friday + timedelta(days=14)

        call_mid = polygon.get_option_price(trade_date, strike, expiry, 'call', 'mid')
        put_mid = polygon.get_option_price(trade_date, strike, expiry, 'put', 'mid')

        if call_mid and put_mid:
            entry_price = (call_mid + 0.015) + (put_mid + 0.015)  # Ask
            entry_cost = entry_price * 100

            position = {
                'entry_date': trade_date,
                'entry_spot': spot,
                'strike': strike,
                'expiry': expiry,
                'entry_cost': entry_cost
            }

            print(f"ENTER {len(trades)+1:02d}: {trade_date}, SPY ${spot:.0f}, Score {score:.2f}")

# Results
print(f"\n{'='*80}")
print("RESULTS")
print(f"{'='*80}\n")

if trades:
    df = pd.DataFrame(trades)
    total = df['net_pnl'].sum()
    print(f"Trades: {len(trades)}")
    print(f"Winners: {(df['net_pnl']>0).sum()}")
    print(f"Total P&L: ${total:,.2f}")
    print(f"Average: ${total/len(trades):.2f}/trade")
    df.to_csv('clean_polygon_backtest.csv', index=False)
else:
    print("NO TRADES")
