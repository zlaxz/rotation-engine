#!/usr/bin/env python3
"""
CLEAN BACKTEST - Built properly from scratch
Using Polygon data (minute bars aggregated to daily)
Profile 1: Long-Dated Gamma
Real costs: $0.03 spread, $0.65 commission
NO hedging, NO slippage
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
import numpy as np
from datetime import date, timedelta
from src.data.polygon_options import PolygonOptionsLoader
import glob

print("=" * 80)
print("CLEAN BACKTEST - PROFILE 1 (BUILT FROM SCRATCH)")
print("=" * 80)

# Load SPY minute bars and aggregate to daily
print("\n[1/5] Loading SPY data (aggregating minute bars to daily)...")
spy_files = sorted(glob.glob('/Volumes/VelocityData/velocity_om/parquet/stock/SPY/*.parquet'))

spy_daily = []
for filepath in spy_files:
    try:
        df = pd.read_parquet(filepath)
        if len(df) > 0:
            daily = {
                'date': pd.to_datetime(df['ts'].iloc[0]).date(),
                'open': df['open'].iloc[0],
                'high': df['high'].max(),
                'low': df['low'].min(),
                'close': df['close'].iloc[-1],
                'volume': df['volume'].sum()
            }
            spy_daily.append(daily)
    except:
        continue

data = pd.DataFrame(spy_daily)
print(f"  Loaded {len(data)} days: {data['date'].min()} to {data['date'].max()}")

# Compute features
print("\n[2/5] Computing features...")
data['ret'] = data['close'].pct_change()
data['RV10'] = data['ret'].rolling(10).std() * np.sqrt(252)
data['MA20'] = data['close'].rolling(20).mean()
data['slope'] = data['close'].pct_change(20)  # 20-day return as trend
print("  Features computed")

# Classify regime (SIMPLE: uptrend or not)
print("\n[3/5] Classifying regime...")
data['regime'] = 0
data.loc[data['slope'] > 0.02, 'regime'] = 1  # Uptrend (>2% over 20 days)
regime_1_days = (data['regime'] == 1).sum()
print(f"  Regime 1 (Uptrend): {regime_1_days} days ({regime_1_days/len(data)*100:.1f}%)")

# Profile score (SIMPLE: enter when in strong uptrend)
print("\n[4/5] Computing profile scores...")
data['score'] = data['slope'].clip(lower=0)  # Use 20-day return as score
high_score = (data['score'] > 0.05).sum()  # >5% return over 20 days
print(f"  Days with score > 0.05: {high_score} ({high_score/len(data)*100:.1f}%)")

# Backtest
print(f"\n[5/5] Running backtest...")
print(f"  Entry: Score > 0.05 AND Regime = 1")
print(f"  Exit: After 14 days OR regime change")
print(f"  Position: ATM straddle, 75 DTE")
print(f"  Costs: $0.03 spread, $2.60 commission")
print()

polygon = PolygonOptionsLoader()
trades = []
position = None

for idx in range(50, len(data)):
    row = data.iloc[idx]
    d = row['date']
    spot = row['close']
    regime = row['regime']
    score = row['score']

    # Exit
    if position:
        days = (d - position['entry_date']).days
        if days >= 14 or regime != 1:
            cm = polygon.get_option_price(d, position['strike'], position['expiry'], 'call', 'mid')
            pm = polygon.get_option_price(d, position['strike'], position['expiry'], 'put', 'mid')
            if cm and pm:
                ex_p = (cm - 0.015) + (pm - 0.015)
                gross = ex_p * 100 - position['entry_cost']
                net = gross - 2.60
                trades.append({'entry': position['entry_date'], 'exit': d, 'days': days,
                               'spy_move': ((spot/position['entry_spot'])-1)*100, 'pnl': net})
                print(f"  Exit {len(trades):02d}: {d}, {days}d, SPY {((spot/position['entry_spot'])-1)*100:+.1f}%, P&L ${net:+.0f}")
            position = None

    # Entry
    if not position and score > 0.05 and regime == 1:
        strike = round(spot)
        target = d + timedelta(days=75)
        fd = date(target.year, target.month, 1)
        ff = fd + timedelta(days=(4 - fd.weekday()) % 7)
        expiry = ff + timedelta(days=14)

        cm = polygon.get_option_price(d, strike, expiry, 'call', 'mid')
        pm = polygon.get_option_price(d, strike, expiry, 'put', 'mid')
        if cm and pm:
            position = {'entry_date': d, 'entry_spot': spot, 'strike': strike, 'expiry': expiry,
                       'entry_cost': ((cm + 0.015) + (pm + 0.015)) * 100}
            print(f"  Enter {len(trades)+1:02d}: {d}, SPY ${spot:.0f}")

# Results
print(f"\n{'='*80}")
if trades:
    df = pd.DataFrame(trades)
    print(f"Trades: {len(trades)}, Winners: {(df['pnl']>0).sum()}, Total: ${df['pnl'].sum():,.0f}")
    df.to_csv('clean_results.csv', index=False)
else:
    print("NO TRADES EXECUTED")
