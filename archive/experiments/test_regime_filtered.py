#!/usr/bin/env python3
"""
Test all 6 profiles WITH regime filtering (using REGIME_COMPATIBILITY matrix)
Compare to unfiltered $83K baseline
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
from datetime import date, timedelta
from src.data.polygon_options import PolygonOptionsLoader
from src.regimes.classifier import RegimeClassifier
import glob

# REGIME_COMPATIBILITY from original code
REGIME_COMPAT = {
    1: {'p1': 1.0, 'p2': 0.0, 'p3': 0.3, 'p4': 1.0, 'p5': 0.0, 'p6': 0.2},
    2: {'p1': 0.0, 'p2': 1.0, 'p3': 0.2, 'p4': 0.0, 'p5': 1.0, 'p6': 0.6},
    3: {'p1': 0.4, 'p2': 0.0, 'p3': 1.0, 'p4': 1.0, 'p5': 0.0, 'p6': 0.1},
    4: {'p1': 0.0, 'p2': 0.4, 'p3': 0.0, 'p4': 0.0, 'p5': 1.0, 'p6': 1.0},
    5: {'p1': 0.2, 'p2': 1.0, 'p3': 0.6, 'p4': 0.3, 'p5': 0.4, 'p6': 0.1},
    6: {'p1': 0.4, 'p2': 0.6, 'p3': 0.2, 'p4': 0.2, 'p5': 0.8, 'p6': 1.0}
}

# Load SPY + compute simple regimes
spy_files = sorted(glob.glob('/Volumes/VelocityData/velocity_om/parquet/stock/SPY/*.parquet'))
spy_data = []
for f in spy_files:
    df = pd.read_parquet(f)
    if len(df) > 0:
        spy_data.append({'date': pd.to_datetime(df['ts'].iloc[0]).date(), 'close': df['close'].iloc[-1]})

spy = pd.DataFrame(spy_data)
spy['slope'] = spy['close'].pct_change(20)

# Simple regime classification (for testing)
spy['regime'] = 5  # Default: Choppy
spy.loc[spy['slope'] > 0.05, 'regime'] = 1  # Strong uptrend
spy.loc[(spy['slope'] > 0) & (spy['slope'] <= 0.05), 'regime'] = 3  # Compression/grind
spy.loc[(spy['slope'] < 0) & (spy['slope'] > -0.05), 'regime'] = 5  # Choppy down
spy.loc[spy['slope'] < -0.05, 'regime'] = 2  # Downtrend

print(f"SPY data: {len(spy)} days")
print("Regime distribution:")
for r in range(1, 7):
    count = (spy['regime'] == r).sum()
    print(f"  Regime {r}: {count} days ({count/len(spy)*100:.1f}%)")

polygon = PolygonOptionsLoader()

profiles = {
    'p1': {'name': 'LDG', 'score_thresh': 0.02, 'dte': 75},
    'p2': {'name': 'SDG', 'score_thresh': 0.03, 'dte': 7},
    'p3': {'name': 'CHARM', 'score_thresh': -0.01, 'dte': 30},
    'p4': {'name': 'VANNA', 'score_thresh': 0.02, 'dte': 60},
    'p5': {'name': 'SKEW', 'score_thresh': -0.02, 'dte': 45},
    'p6': {'name': 'VOV', 'score_thresh': 0.00, 'dte': 30}
}

print("\n" + "=" * 80)
print("TESTING WITH REGIME FILTERING")
print("=" * 80)

results = {}

for pid, config in profiles.items():
    print(f"\nTesting {pid} ({config['name']})...")

    trades, pos = [], None

    for idx in range(50, len(spy)):
        row = spy.iloc[idx]
        d, spot = row['date'], row['close']
        score, regime = row['slope'], int(row['regime'])

        # Exit
        if pos:
            days = (d - pos['entry']).days
            if days >= 7:
                cm = polygon.get_option_price(d, pos['strike'], pos['expiry'], 'call', 'mid')
                pm = polygon.get_option_price(d, pos['strike'], pos['expiry'], 'put', 'mid')
                if cm and pm:
                    pnl = (cm + pm - 0.03) * 100 - pos['cost'] - 2.60
                    trades.append({'pnl': pnl, 'peak': pos['peak']})
                pos = None

        # Entry with regime filter
        if not pos and score > config['score_thresh']:
            # Check regime compatibility
            compat = REGIME_COMPAT.get(regime, {}).get(pid, 0.0)
            if compat < 0.5:  # Only trade in favorable regimes (compat >= 0.5)
                continue

            strike = round(spot)
            target = d + timedelta(days=config['dte'])
            fd = date(target.year, target.month, 1)
            ff = fd + timedelta(days=(4 - fd.weekday()) % 7)
            expiry = ff + timedelta(days=14)

            cm = polygon.get_option_price(d, strike, expiry, 'call', 'mid')
            pm = polygon.get_option_price(d, strike, expiry, 'put', 'mid')
            if cm and pm:
                cost = (cm + pm + 0.03) * 100

                # Calculate peak
                peak = -999999
                for fidx in range(idx, min(idx+8, len(spy))):
                    fr = spy.iloc[fidx]
                    fcm = polygon.get_option_price(fr['date'], strike, expiry, 'call', 'mid')
                    fpm = polygon.get_option_price(fr['date'], strike, expiry, 'put', 'mid')
                    if fcm and fpm:
                        fpnl = (fcm + fpm - 0.03) * 100 - cost - 2.60
                        if fpnl > peak:
                            peak = fpnl

                pos = {'entry': d, 'strike': strike, 'expiry': expiry, 'cost': cost, 'peak': peak}

    if trades:
        df = pd.DataFrame(trades)
        peak_total = df['peak'].apply(lambda x: x if x > 0 else 0).sum()
        capture_30 = df['peak'].apply(lambda x: x * 0.3 if x > 0 else x * 0.1).sum()
        results[pid] = {
            'trades': len(df),
            'peak': peak_total,
            'capture_30': capture_30
        }
        print(f"  {len(df)} trades, Peak ${peak_total:.0f}, 30% ${capture_30:.0f}")
    else:
        results[pid] = {'trades': 0, 'peak': 0, 'capture_30': 0}
        print(f"  No trades")

# Summary
print("\n" + "=" * 80)
print("WITH REGIME FILTERING")
print("=" * 80)

total_peak_filtered = sum(r['peak'] for r in results.values())
total_30_filtered = sum(r['capture_30'] for r in results.values())

print(f"\nTotal peak (filtered):    ${total_peak_filtered:,.0f}")
print(f"Total 30% (filtered):     ${total_30_filtered:,.0f}")
print(f"\nBaseline (unfiltered):    $83,041")
print(f"Improvement:              ${total_30_filtered - 83041:,.0f}")

if total_30_filtered > 83041:
    print(f"\n✅ REGIME FILTERING HELPS (+${total_30_filtered - 83041:,.0f})")
else:
    print(f"\n⚠️ REGIME FILTERING NEUTRAL (${total_30_filtered - 83041:,.0f})")
