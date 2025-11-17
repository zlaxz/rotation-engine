#!/usr/bin/env python3
"""
Profile 1 WITHOUT regime filtering.

Entry: Score > 0.05 (ANY market condition)
Exit: After 7 days
Position: ATM straddle, 75 DTE
Costs: $0.03 spread, $2.60 commission, NO hedging
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
from datetime import date, timedelta
from src.data.polygon_options import PolygonOptionsLoader
import glob

# Load SPY
print("Loading SPY data...")
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

# Compute score (simple momentum)
spy_df['slope'] = spy_df['close'].pct_change(20)
spy_df['score'] = spy_df['slope'].clip(lower=0)

print(f"Loaded {len(spy_df)} days")
print(f"Days with score > 0.05: {(spy_df['score'] > 0.05).sum()} ({(spy_df['score'] > 0.05).sum()/len(spy_df)*100:.1f}%)")

print("\n" + "=" * 80)
print("BACKTEST - NO REGIME FILTER")
print("=" * 80)
print("\nEntry: Score > 0.05 (ALL market conditions)")
print("Exit: After 7 days")
print("Position: ATM straddle, 75 DTE")
print("Costs: $0.03 spread, $2.60 commission")
print()

polygon = PolygonOptionsLoader()
trades = []
position = None

for idx in range(50, len(spy_df)):
    row = spy_df.iloc[idx]
    d = row['date']
    spot = row['close']
    score = row['score']

    # Exit after 7 days
    if position:
        days = (d - position['entry_date']).days
        if days >= 7:
            cm = polygon.get_option_price(d, position['strike'], position['expiry'], 'call', 'mid')
            pm = polygon.get_option_price(d, position['strike'], position['expiry'], 'put', 'mid')
            if cm and pm:
                pnl = (cm + pm - 0.03) * 100 - position['entry_cost'] - 2.60
                spy_move = ((spot / position['entry_spot']) - 1) * 100
                trades.append({
                    'entry': position['entry_date'],
                    'exit': d,
                    'days': days,
                    'spy_move': spy_move,
                    'pnl': pnl
                })
                if len(trades) <= 20:
                    print(f"Exit {len(trades):02d}: {d}, {days}d, SPY {spy_move:+.1f}%, P&L ${pnl:+.0f}")
            position = None

    # Entry: NO regime filter
    if not position and score > 0.05:
        strike = round(spot)
        target = d + timedelta(days=75)
        fd = date(target.year, target.month, 1)
        ff = fd + timedelta(days=(4 - fd.weekday()) % 7)
        expiry = ff + timedelta(days=14)

        cm = polygon.get_option_price(d, strike, expiry, 'call', 'mid')
        pm = polygon.get_option_price(d, strike, expiry, 'put', 'mid')
        if cm and pm:
            position = {
                'entry_date': d,
                'entry_spot': spot,
                'strike': strike,
                'expiry': expiry,
                'entry_cost': (cm + pm + 0.03) * 100
            }
            if len(trades) < 20:
                print(f"Enter {len(trades)+1:02d}: {d}, SPY ${spot:.0f}, Score {score:.2f}")

# Results
print(f"\n{'...' if len(trades) > 20 else ''}")
print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)

if trades:
    df = pd.DataFrame(trades)
    total = df['pnl'].sum()
    winners = (df['pnl'] > 0).sum()

    print(f"\nTrades: {len(trades)}")
    print(f"Winners: {winners} ({winners/len(trades)*100:.1f}%)")
    print(f"Losers: {len(trades) - winners}")
    print(f"\nTotal P&L: ${total:,.0f}")
    print(f"Average: ${total/len(trades):.0f}/trade")

    print(f"\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)
    print(f"WITH regime filter (Regime 1 only):")
    print(f"  42 trades, 7-year window")
    print(f"  P&L: -$1,535")
    print()
    print(f"WITHOUT regime filter (All regimes):")
    print(f"  {len(trades)} trades, 7-year window")
    print(f"  P&L: ${total:,.0f}")
    print()
    print(f"Difference: ${total - (-1535):,.0f}")

    if total > -1535:
        print(f"\n✅ NO FILTER is BETTER")
        print(f"   Regime filtering is HURTING performance")
    else:
        print(f"\n❌ REGIME FILTER is BETTER")
        print(f"   Regime detection adds value")

    df.to_csv('no_regime_results.csv', index=False)

else:
    print("\nNO TRADES")
