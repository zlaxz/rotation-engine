"""
Test Day 1: Data Spine

Validates:
- SPY OHLCV loading
- Options chain loading
- Feature calculation
- Data quality
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from datetime import datetime
import pandas as pd
import numpy as np

from data import DataSpine, validate_features


def test_spy_ohlcv():
    """Test SPY OHLCV loading."""
    print("\n=== Testing SPY OHLCV Loading ===")

    spine = DataSpine()

    # Load 2022 data
    start = datetime(2022, 1, 1)
    end = datetime(2022, 12, 31)

    df = spine.build_spine(start, end)

    print(f"Loaded {len(df)} rows")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Columns: {list(df.columns)}")

    # Validate
    assert len(df) > 200, "Should have ~252 trading days"
    assert 'close' in df.columns
    assert 'RV20' in df.columns
    assert 'MA20' in df.columns

    # Check for NaN (expect some in early rows)
    nan_counts = df.isna().sum()
    print("\nNaN counts by column:")
    print(nan_counts[nan_counts > 0])

    # Verify no NaN after warmup period (50 days for MA50)
    warmup_df = df.iloc[60:]
    critical_cols = ['close', 'RV20', 'ATR10', 'MA20', 'MA50']
    for col in critical_cols:
        nan_count = warmup_df[col].isna().sum()
        assert nan_count == 0, f"{col} has {nan_count} NaN values after warmup"

    print("\n✅ SPY OHLCV test PASSED")
    return df


def test_options_chain():
    """Test options chain loading."""
    print("\n=== Testing Options Chain Loading ===")

    spine = DataSpine()

    # Test date: 2022-06-15 (random trading day)
    test_date = datetime(2022, 6, 15)

    data = spine.get_day_data(test_date, include_options=True)

    spy = data['spy']
    options = data['options']

    print(f"\nSPY data for {test_date.date()}:")
    print(f"  Close: ${spy['close']:.2f}")
    print(f"  RV20: {spy['RV20']:.2%}")
    print(f"  MA20: ${spy['MA20']:.2f}")

    print(f"\nOptions chain:")
    print(f"  Total contracts: {len(options)}")

    if not options.empty:
        print(f"  Strikes: {options['strike'].min():.0f} to {options['strike'].max():.0f}")
        print(f"  Expiries: {options['expiry'].min()} to {options['expiry'].max()}")
        print(f"  Calls: {(options['option_type'] == 'call').sum()}")
        print(f"  Puts: {(options['option_type'] == 'put').sum()}")

        # Check DTE distribution
        print(f"\nDTE distribution:")
        print(options['dte'].value_counts().sort_index().head(10))

        # Validate columns
        expected_cols = ['date', 'expiry', 'strike', 'option_type', 'dte', 'close', 'volume']
        for col in expected_cols:
            assert col in options.columns, f"Missing column: {col}"

        # Validate data quality
        assert (options['close'] > 0).all(), "Found negative option prices"
        assert (options['volume'] > 0).all(), "Found zero volume (should be filtered)"
        assert options['strike'].min() > 0, "Invalid strikes"

    print("\n✅ Options chain test PASSED")
    return data


def test_features_calculation():
    """Test derived features."""
    print("\n=== Testing Feature Calculations ===")

    spine = DataSpine()

    # Load data
    start = datetime(2022, 1, 1)
    end = datetime(2022, 3, 31)

    df = spine.build_spine(start, end)

    # Validate features
    results = validate_features(df)

    print(f"\nValidation results:")
    print(f"  Rows: {results['row_count']}")
    print(f"  Date range: {results['date_range']}")

    print("\nMissing values:")
    for col, count in results['missing_values'].items():
        if count > 0:
            pct = 100 * count / results['row_count']
            print(f"  {col}: {count} ({pct:.1f}%)")

    print("\nFeature statistics (sample):")
    for col in ['RV20', 'ATR10', 'slope_MA20']:
        if col in results['feature_stats']:
            stats = results['feature_stats'][col]
            print(f"  {col}:")
            print(f"    Mean: {stats['mean']:.4f}")
            print(f"    Std:  {stats['std']:.4f}")
            print(f"    Range: [{stats['min']:.4f}, {stats['max']:.4f}]")

    # Sanity checks
    assert results['feature_stats']['RV20']['mean'] > 0, "RV should be positive"
    assert results['feature_stats']['RV20']['mean'] < 2.0, "RV should be reasonable (<200%)"

    print("\n✅ Features test PASSED")
    return results


def test_day_1_definition_of_done():
    """
    Day 1 Definition of Done Test:

    Test query: "Give me SPY + full options chain for 2022-06-15 with RV/IV/MA features"

    Success criteria:
    - ✅ No NaN explosions
    - ✅ No weird gaps
    - ✅ Data structure clean and queryable
    """
    print("\n" + "="*60)
    print("DAY 1 DEFINITION OF DONE TEST")
    print("="*60)

    spine = DataSpine()

    # The test query
    test_date = datetime(2022, 6, 15)
    print(f"\nQuery: Get SPY + options chain for {test_date.date()}")

    data = spine.get_day_data(test_date, include_options=True)

    spy = data['spy']
    options = data['options']

    print("\n--- SPY Data ---")
    print(f"Date: {spy['date']}")
    print(f"OHLCV: O={spy['open']:.2f} H={spy['high']:.2f} L={spy['low']:.2f} C={spy['close']:.2f} V={spy['volume']:,.0f}")
    print(f"\nDerived Features:")
    print(f"  RV5:  {spy['RV5']:.2%}")
    print(f"  RV10: {spy['RV10']:.2%}")
    print(f"  RV20: {spy['RV20']:.2%}")
    print(f"  ATR5: {spy['ATR5']:.2f}")
    print(f"  ATR10: {spy['ATR10']:.2f}")
    print(f"  MA20: {spy['MA20']:.2f}")
    print(f"  MA50: {spy['MA50']:.2f}")
    print(f"  slope_MA20: {spy['slope_MA20']:.4f}")
    print(f"  return_20d: {spy['return_20d']:.2%}")

    print("\n--- Options Chain ---")
    print(f"Total contracts: {len(options)}")

    # Check for NaN explosions
    spy_nans = pd.Series(spy).isna().sum()
    options_nans = options.isna().sum().sum()

    print(f"\n✓ NaN check:")
    print(f"  SPY NaNs: {spy_nans}")
    print(f"  Options NaNs: {options_nans}")

    # Check for gaps
    print(f"\n✓ Data quality:")
    print(f"  SPY close > 0: {spy['close'] > 0}")
    print(f"  All features computed: {pd.Series(spy)[['RV20', 'ATR10', 'MA20', 'MA50']].notna().all()}")
    print(f"  Options count reasonable: {len(options) > 100}")

    # Sample options
    print(f"\n--- Sample Options (ATM calls, 30 DTE) ---")
    atm_strike = spy['close']
    sample = options[
        (options['option_type'] == 'call') &
        (options['strike'].between(atm_strike - 5, atm_strike + 5)) &
        (options['dte'].between(25, 35))
    ].head()

    if not sample.empty:
        print(sample[['strike', 'expiry', 'dte', 'close', 'volume', 'bid', 'ask']])
    else:
        print("(No ATM calls found in 30 DTE range)")

    # Success criteria
    print("\n" + "="*60)
    print("SUCCESS CRITERIA:")
    print("="*60)

    criteria = {
        "No NaN explosions": spy_nans == 0 and options_nans == 0,
        "No weird gaps": len(options) > 100,
        "Data structure clean": 'RV20' in spy and 'close' in options.columns,
    }

    all_passed = True
    for criterion, passed in criteria.items():
        status = "✅" if passed else "❌"
        print(f"{status} {criterion}")
        all_passed = all_passed and passed

    if all_passed:
        print("\n" + "🎉"*20)
        print("DAY 1 COMPLETE - DATA SPINE READY!")
        print("🎉"*20)
    else:
        print("\n❌ Some criteria failed - needs fixes")

    return all_passed


if __name__ == '__main__':
    # Run all tests
    print("="*60)
    print("RUNNING DAY 1 DATA SPINE TESTS")
    print("="*60)

    try:
        # Test 1: SPY OHLCV
        spy_df = test_spy_ohlcv()

        # Test 2: Options chain
        day_data = test_options_chain()

        # Test 3: Features
        feature_results = test_features_calculation()

        # Test 4: Definition of Done
        success = test_day_1_definition_of_done()

        if success:
            print("\n" + "="*60)
            print("ALL TESTS PASSED ✅")
            print("="*60)
            sys.exit(0)
        else:
            print("\n" + "="*60)
            print("SOME TESTS FAILED ❌")
            print("="*60)
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
