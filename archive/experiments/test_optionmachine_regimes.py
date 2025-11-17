#!/usr/bin/env python3
"""
Test using option-machine's 4-regime system (CARRY, TREND, NEUTRAL, SHOCK)
Simpler, volatility-focused regime detection
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
import numpy as np
from datetime import date, timedelta
from src.data.polygon_options import PolygonOptionsLoader
import glob

# Load SPY
spy_files = sorted(glob.glob('/Volumes/VelocityData/velocity_om/parquet/stock/SPY/*.parquet'))
spy_data = []
for f in spy_files:
    df = pd.read_parquet(f)
    if len(df) > 0:
        spy_data.append({
            'date': pd.to_datetime(df['ts'].iloc[0]).date(),
            'close': df['close'].iloc[-1],
            'high': df['high'].max(),
            'low': df['low'].min()
        })

spy = pd.DataFrame(spy_data)

# Compute features (option-machine style)
spy['ret'] = spy['close'].pct_change()
spy['RV20'] = spy['ret'].rolling(20).std() * np.sqrt(252)
spy['RV60'] = spy['ret'].rolling(60).std() * np.sqrt(252)
spy['vol_ratio'] = spy['RV20'] / (spy['RV60'] + 0.001)
spy['MA50'] = spy['close'].rolling(50).mean()
spy['MA200'] = spy['close'].rolling(200).mean()
spy['above_ma50'] = (spy['close'] > spy['MA50']).astype(int)
spy['breadth'] = spy['above_ma50'].rolling(20).sum() / 20 * 100

# Classify regimes (option-machine logic)
spy['regime'] = 'NEUTRAL'

# SHOCK: High vol OR term structure issues
spy.loc[spy['RV20'] > 0.22, 'regime'] = 'SHOCK'

# CARRY: Low vol, bullish
spy.loc[
    (spy['RV20'] < 0.12) &
    (spy['close'] > spy['MA200']) &
    (spy['breadth'] > 60),
    'regime'
] = 'CARRY'

# TREND: Not shock, not carry, directional
spy.loc[
    (spy['regime'] == 'NEUTRAL') &
    ((spy['close'] > spy['MA50']*1.05) | (spy['close'] < spy['MA50']*0.95)),
    'regime'
] = 'TREND'

print(f"SPY data: {len(spy)} days")
print("\nRegime distribution (option-machine style):")
for regime in ['CARRY', 'TREND', 'NEUTRAL', 'SHOCK']:
    count = (spy['regime'] == regime).sum()
    print(f"  {regime:8s}: {count:4d} days ({count/len(spy)*100:5.1f}%)")

# Profile-regime pairing (based on strategy type)
REGIME_FILTERS = {
    'p1_LDG': ['TREND', 'SHOCK'],      # Long gamma needs moves
    'p2_SDG': ['SHOCK'],                # Short-dated needs big vol
    'p3_CHARM': ['CARRY', 'NEUTRAL'],   # Theta harvesting needs calm
    'p4_VANNA': ['CARRY', 'TREND'],     # Vol crush + trend
    'p5_SKEW': ['TREND', 'SHOCK'],      # Downside protection
    'p6_VOV': ['SHOCK']                 # Vol-of-vol needs uncertainty
}

polygon = PolygonOptionsLoader()

profiles = {
    'p1_LDG': {'dte': 75},
    'p2_SDG': {'dte': 7},
    'p3_CHARM': {'dte': 30},
    'p4_VANNA': {'dte': 60},
    'p5_SKEW': {'dte': 45},
    'p6_VOV': {'dte': 30}
}

results = {}

print("\n" + "=" * 80)
print("TESTING WITH OPTION-MACHINE REGIMES")
print("=" * 80)

for pid, config in profiles.items():
    favorable = REGIME_FILTERS[pid]
    trades, pos = [], None

    for idx in range(90, len(spy)):
        row = spy.iloc[idx]
        d, spot, regime = row['date'], row['close'], row['regime']

        # Exit
        if pos and (d - pos['entry']).days >= 7:
            cm = polygon.get_option_price(d, pos['strike'], pos['expiry'], 'call', 'mid')
            pm = polygon.get_option_price(d, pos['strike'], pos['expiry'], 'put', 'mid')
            if cm and pm:
                pnl = (cm + pm - 0.03) * 100 - pos['cost'] - 2.60
                trades.append({'pnl': pnl, 'peak': pos.get('peak', pnl)})
            pos = None

        # Entry (regime filtered)
        if not pos and regime in favorable:
            strike = round(spot)
            target = d + timedelta(days=config['dte'])
            fd = date(target.year, target.month, 1)
            ff = fd + timedelta(days=(4-fd.weekday())%7)
            expiry = ff + timedelta(days=14)

            cm = polygon.get_option_price(d, strike, expiry, 'call', 'mid')
            pm = polygon.get_option_price(d, strike, expiry, 'put', 'mid')
            if cm and pm:
                cost = (cm + pm + 0.03) * 100

                # Calculate peak
                peak = -999999
                for i in range(idx, min(idx+8, len(spy))):
                    r = spy.iloc[i]
                    c = polygon.get_option_price(r['date'], strike, expiry, 'call', 'mid')
                    p = polygon.get_option_price(r['date'], strike, expiry, 'put', 'mid')
                    if c and p:
                        ppnl = (c + p - 0.03) * 100 - cost - 2.60
                        if ppnl > peak:
                            peak = ppnl

                pos = {'entry': d, 'strike': strike, 'expiry': expiry, 'cost': cost, 'peak': peak}

    if trades:
        df = pd.DataFrame(trades)
        pk = df['peak'].apply(lambda x: max(x,0)).sum()
        c30 = df['peak'].apply(lambda x: x*0.3 if x>0 else x*0.1).sum()
        results[pid] = (len(df), pk, c30)
        print(f"{pid:12s} {len(df):3d} trades, ${pk:>8.0f} peak, ${c30:>8.0f} (30%)")
    else:
        results[pid] = (0, 0, 0)
        print(f"{pid:12s} No trades")

total_pk = sum(r[1] for r in results.values())
total_30 = sum(r[2] for r in results.values())

print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)
print(f"\nOption-machine regimes: ${total_30:,.0f} (30%)")
print(f"Original 6-regime filter: $45,725 (30%)")
print(f"No filter baseline:       $83,041 (30%)")

if total_30 > 83041:
    print(f"\n✅ BEATS BASELINE (+${total_30 - 83041:,.0f})")
elif total_30 > 45725:
    print(f"\n✅ BETTER than 6-regime (+${total_30 - 45725:,.0f})")
else:
    print(f"\n⚠️ WORSE than baseline (${total_30 - 83041:,.0f})")
