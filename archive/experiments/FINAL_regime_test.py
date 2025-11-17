#!/usr/bin/env python3
"""FINAL REGIME TEST - Built clean, verified, no shortcuts"""
import sys
sys.path.append('/Users/zstoc/rotation-engine')
import pandas as pd
from datetime import date, timedelta
from src.data.polygon_options import PolygonOptionsLoader
from src.regimes.classifier import RegimeClassifier
from src.profiles.detectors import ProfileDetectors
import glob

# Load SPY from Polygon
spy_files = sorted(glob.glob('/Volumes/VelocityData/velocity_om/parquet/stock/SPY/*.parquet'))
spy_data = []
for f in spy_files:
    df = pd.read_parquet(f)
    if len(df) > 0:
        spy_data.append({'date': pd.to_datetime(df['ts'].iloc[0]).date(),
                        'open': df['open'].iloc[0], 'high': df['high'].max(),
                        'low': df['low'].min(), 'close': df['close'].iloc[-1]})
spy = pd.DataFrame(spy_data)

# Compute features (all required by regime classifier)
spy['ret'] = spy['close'].pct_change()
spy['RV5'] = spy['ret'].rolling(5).std() * (252**0.5)
spy['RV10'] = spy['ret'].rolling(10).std() * (252**0.5)
spy['RV20'] = spy['ret'].rolling(20).std() * (252**0.5)
spy['ATR5'] = (spy['high'] - spy['low']).rolling(5).mean()
spy['ATR10'] = (spy['high'] - spy['low']).rolling(10).mean()
spy['MA20'] = spy['close'].rolling(20).mean()
spy['MA50'] = spy['close'].rolling(50).mean()
spy['slope_MA20'] = (spy['MA20'] - spy['MA20'].shift(5)) / spy['MA20'].shift(5)
spy['slope_MA50'] = (spy['MA50'] - spy['MA50'].shift(10)) / spy['MA50'].shift(10)
spy['return_5d'] = spy['close'].pct_change(5)
spy['return_10d'] = spy['close'].pct_change(10)
spy['return_20d'] = spy['close'].pct_change(20)
spy['range_10d'] = (spy['high'].rolling(10).max() - spy['low'].rolling(10).min()) / spy['close']
spy['price_to_MA20'] = spy['close'] / spy['MA20']
spy['price_to_MA50'] = spy['close'] / spy['MA50']

# Classify regimes with REAL classifier
classifier = RegimeClassifier()
spy_with_regimes = classifier.classify_period(spy)

# Compute REAL Profile 1 scores
detector = ProfileDetectors()
full_data = detector.compute_all_profiles(spy_with_regimes)

print(f"Data: {len(full_data)} days")
print(f"\nRegime distribution:")
for r in range(1, 7):
    count = (full_data['regime_label'] == r).sum()
    print(f"  Regime {r}: {count} days ({count/len(full_data)*100:.1f}%)")

polygon = PolygonOptionsLoader()

def run(use_filter):
    trades, pos = [], None
    regime_filter = [1, 3] if use_filter else list(range(1, 7))

    for idx in range(90, len(full_data)):
        row = full_data.iloc[idx]
        d, spot = row['date'], row['close']
        regime = int(row.get('regime_label', 0))
        score = row.get('profile_1_LDG', 0.0)

        if pos:
            days = (d - pos['entry']).days if hasattr(d, '__sub__') else 0
            if days >= 7:
                cm = polygon.get_option_price(d, pos['strike'], pos['expiry'], 'call', 'mid')
                pm = polygon.get_option_price(d, pos['strike'], pos['expiry'], 'put', 'mid')
                if cm and pm:
                    pnl = (cm + pm - 0.03) * 100 - pos['cost'] - 2.60
                    trades.append({'pnl': pnl})
                pos = None

        if not pos and score > 0.6 and regime in regime_filter:
            strike = round(spot)
            d_obj = d if isinstance(d, date) else (d.date() if hasattr(d, 'date') else pd.to_datetime(d).date())
            target = d_obj + timedelta(days=75)
            fd = date(target.year, target.month, 1)
            ff = fd + timedelta(days=(4 - fd.weekday()) % 7)
            expiry = ff + timedelta(days=14)

            cm = polygon.get_option_price(d_obj, strike, expiry, 'call', 'mid')
            pm = polygon.get_option_price(d_obj, strike, expiry, 'put', 'mid')
            if cm and pm:
                pos = {'entry': d_obj, 'strike': strike, 'expiry': expiry, 'cost': (cm + pm + 0.03) * 100}

    return pd.DataFrame(trades) if trades else pd.DataFrame()

print("\nTEST A: Regimes 1 & 3 only")
df_filtered = run(True)
print(f"  Trades: {len(df_filtered)}, P&L: ${df_filtered['pnl'].sum() if len(df_filtered) > 0 else 0:.0f}")

print("\nTEST B: ALL regimes")
df_all = run(False)
print(f"  Trades: {len(df_all)}, P&L: ${df_all['pnl'].sum() if len(df_all) > 0 else 0:.0f}")

if len(df_filtered) > 0 and len(df_all) > 0:
    print(f"\nFiltered better by: ${(df_filtered['pnl'].sum() - df_all['pnl'].sum()):.0f}")
