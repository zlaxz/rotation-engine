#!/usr/bin/env python3
"""Quick verification that BUG-C04/C05 fix is working correctly."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from regimes.signals import RegimeSignals
import pandas as pd
import numpy as np

print("="*70)
print("BUG-C04/C05 FIX VERIFICATION")
print("="*70)

# Create sample data
np.random.seed(42)
dates = pd.date_range('2022-01-01', periods=100, freq='D')
spy_data = pd.DataFrame({
    'date': dates,
    'close': np.linspace(400, 450, 100),
    'RV5': np.random.rand(100) * 0.02 + 0.01,
    'RV10': np.random.rand(100) * 0.02 + 0.01,
    'RV20': np.random.rand(100) * 0.02 + 0.01,
    'ATR5': np.random.rand(100) * 5 + 2,
    'ATR10': np.random.rand(100) * 5 + 2,
    'MA20': np.linspace(400, 450, 100),
    'MA50': np.linspace(395, 445, 100),
    'slope_MA20': np.random.randn(100) * 0.001,
    'slope_MA50': np.random.randn(100) * 0.001,
    'return_5d': np.random.randn(100) * 0.02,
    'return_10d': np.random.randn(100) * 0.03,
    'return_20d': np.random.randn(100) * 0.04,
    'range_10d': np.random.rand(100) * 0.05,
    'price_to_MA20': np.random.randn(100) * 0.02,
    'price_to_MA50': np.random.randn(100) * 0.03,
})

print("\n1. Computing regime signals...")
calculator = RegimeSignals(lookback_percentile=60)
result = calculator.compute_all_signals(spy_data)

print("✓ Signals computed successfully")

print("\n2. Checking for duplicate columns...")
percentile_cols = [col for col in result.columns if 'RV20' in col and ('percentile' in col or 'rank' in col)]
print(f"   RV20 percentile-related columns found: {percentile_cols}")

if len(percentile_cols) == 1 and percentile_cols[0] == 'RV20_percentile':
    print("✓ PASS: Only one percentile column exists (RV20_percentile)")
else:
    print(f"✗ FAIL: Expected ['RV20_percentile'], got {percentile_cols}")
    sys.exit(1)

print("\n3. Checking percentile values...")
pct = result['RV20_percentile'].dropna()

if pct.min() >= 0.0 and pct.max() <= 1.0:
    print(f"✓ PASS: All percentiles in valid range [0, 1]")
    print(f"   Min: {pct.min():.4f}, Max: {pct.max():.4f}, Mean: {pct.mean():.4f}")
else:
    print(f"✗ FAIL: Percentiles out of range")
    print(f"   Min: {pct.min():.4f}, Max: {pct.max():.4f}")
    sys.exit(1)

print("\n4. Walk-forward compliance check...")
# Manually verify one point
i = 75
lookback = spy_data['RV20'].iloc[15:75]  # past 60 values
current = spy_data['RV20'].iloc[75]
expected = (lookback < current).sum() / len(lookback)
actual = result['RV20_percentile'].iloc[75]

if abs(expected - actual) < 0.001:
    print(f"✓ PASS: Walk-forward compliance verified at index {i}")
    print(f"   Expected: {expected:.4f}, Actual: {actual:.4f}")
else:
    print(f"✗ FAIL: Walk-forward compliance failed")
    print(f"   Expected: {expected:.4f}, Actual: {actual:.4f}, Diff: {abs(expected-actual):.4f}")
    sys.exit(1)

print("\n" + "="*70)
print("ALL CHECKS PASSED ✓")
print("="*70)
print("\nBUG-C04: Duplicate implementations - FIXED")
print("BUG-C05: Off-by-one shift error - FIXED")
print("\nPercentile calculations are now:")
print("  - Walk-forward compliant (no look-ahead)")
print("  - Consistent (single implementation)")
print("  - Accurate (values in [0,1] range)")
print("  - Timely (no shift errors)")
print("\nRegime signals are ready for backtesting.")
