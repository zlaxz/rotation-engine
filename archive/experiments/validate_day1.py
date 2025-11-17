#!/usr/bin/env python3
"""
Data spine validation script.

Test: Can we query SPY + options for 2022-06-15?
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from datetime import datetime, timedelta
from data import DataSpine

def main():
    print("="*60)
    print("DATA SPINE VALIDATION")
    print("="*60)

    spine = DataSpine()

    # Coverage check
    print("\n1. Checking data coverage...")
    coverage = spine.loader.get_data_coverage()
    print(f"   Data available: {coverage['start']} to {coverage['end']}")
    print(f"   Total files: {coverage['count']}")

    stock_cov = spine.loader.get_spy_stock_coverage()
    print(f"   SPY stock coverage: {stock_cov['start']} to {stock_cov['end']} "
          f"({stock_cov['count']} trading days)")

    # Test date (ensure within stock coverage window and far enough from start for features)
    requested = datetime(2022, 6, 15)
    stock_start_dt = datetime.combine(stock_cov['start'], datetime.min.time())
    stock_end_dt = datetime.combine(stock_cov['end'], datetime.min.time())
    warmup_buffer = timedelta(days=90)
    fallback = stock_start_dt + warmup_buffer
    test_date = max(requested, fallback)
    test_date = min(test_date, stock_end_dt - timedelta(days=5))

    print(f"\n2. Loading data for {test_date.date()}...")

    data = spine.get_day_data(test_date, include_options=True)

    spy = data['spy']
    options = data['options']

    if spy is None:
        print("   ❌ Failed to load SPY data")
        return False

    print(f"   ✅ SPY loaded: Close=${spy['close']:.2f}")

    # Check features
    print(f"\n3. Validating derived features...")
    features = ['RV5', 'RV10', 'RV20', 'ATR5', 'ATR10', 'MA20', 'MA50', 'slope_MA20']
    missing = [f for f in features if f not in spy or pd.isna(spy[f])]

    if missing:
        print(f"   ❌ Missing/NaN features: {missing}")
        return False

    print(f"   ✅ All features present:")
    print(f"      RV20={spy['RV20']:.2%}, ATR10={spy['ATR10']:.2f}, MA20=${spy['MA20']:.2f}")

    # Check options
    print(f"\n4. Validating options chain...")
    if options is None or options.empty:
        print(f"   ❌ No options data")
        return False

    print(f"   ✅ Options loaded: {len(options)} contracts")
    print(f"      Calls: {(options['option_type']=='call').sum()}")
    print(f"      Puts: {(options['option_type']=='put').sum()}")
    print(f"      DTE range: {options['dte'].min()}-{options['dte'].max()} days")

    # Data quality
    print(f"\n5. Data quality checks...")
    checks = {
        'No negative prices': (options['close'] > 0).all(),
        'No zero volume': (options['volume'] > 0).all(),
        'Valid strikes': (options['strike'] > 0).all(),
        'Bid <= Ask': (options['bid'] <= options['ask']).all(),
    }

    all_good = True
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")
        all_good = all_good and passed

    if all_good:
        print("\n" + "="*60)
        print("✅ DATA SPINE VALIDATION PASSED")
        print("="*60)
        print("\nData spine is ready:")
        print("- SPY OHLCV: ✅")
        print("- Options chain: ✅")
        print("- Derived features: ✅")
        print("- Data quality: ✅")
        print("\nReady for Day 2: Regime Labeler")
        return True
    else:
        print("\n❌ VALIDATION FAILED")
        return False


if __name__ == '__main__':
    import pandas as pd
    success = main()
    sys.exit(0 if success else 1)
