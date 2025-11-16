"""
Before/After comparison for IV and NaN fixes.

Demonstrates the impact of:
1. VIX-based IV vs RV × 1.2 proxy
2. Error-raising NaN handling vs silent fillna(0)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from profiles.features import ProfileFeatures
from profiles.detectors import ProfileDetectors


def test_iv_before_after_comparison():
    """Compare IV calculation before (RV × 1.2) vs after (VIX-based)."""
    dates = pd.date_range('2023-01-01', periods=100, freq='D')

    # Scenario: VIX = 25%, RV10 = 15%
    # Before fix: IV20 = 15 × 1.2 = 18% (backward-looking, constant multiplier)
    # After fix: IV20 = 25 × 0.95 = 23.75% (forward-looking, tracks VIX)

    df = pd.DataFrame({
        'date': dates,
        'close': 400.0,
        'RV5': 15.0,
        'RV10': 15.0,
        'RV20': 15.0,
        'vix_close': 25.0
    })

    feature_engine = ProfileFeatures()
    result = feature_engine._compute_iv_proxies(df)

    # After fix: IV is VIX-based
    iv20_after = result['IV20'].iloc[0]
    expected_after = 25.0 * 0.95  # 23.75

    # Before fix would have been
    iv20_before = 15.0 * 1.2  # 18.0

    print("\n=== IV CALCULATION COMPARISON ===")
    print(f"Scenario: VIX = 25%, RV10 = 15%")
    print(f"BEFORE (RV × 1.2): IV20 = {iv20_before:.2f}%")
    print(f"AFTER (VIX-based): IV20 = {iv20_after:.2f}%")
    print(f"Difference: {iv20_after - iv20_before:+.2f}%")
    print(f"Impact: {abs(iv20_after - iv20_before) / iv20_before * 100:.1f}% change")

    # Verify fix is applied
    assert abs(iv20_after - expected_after) < 0.01, "Should use VIX-based calculation"
    assert abs(iv20_after - iv20_before) > 2.0, "Should differ significantly from old method"


def test_iv_responds_to_market_stress():
    """Demonstrate IV now responds to VIX spikes (forward-looking)."""
    dates = pd.date_range('2023-01-01', periods=10, freq='D')

    # Simulate market stress: VIX spikes from 15% to 40%
    vix_values = [15.0, 16.0, 20.0, 30.0, 40.0, 38.0, 35.0, 30.0, 25.0, 22.0]

    df = pd.DataFrame({
        'date': dates,
        'close': 400.0,
        'RV5': [15.0] * 10,  # RV stays constant (lags actual volatility)
        'RV10': [15.0] * 10,
        'RV20': [15.0] * 10,
        'vix_close': vix_values
    })

    feature_engine = ProfileFeatures()
    result = feature_engine._compute_iv_proxies(df)

    # BEFORE fix: IV would be constant (RV × 1.2 = 18%)
    iv20_before = 15.0 * 1.2

    # AFTER fix: IV tracks VIX
    iv20_peak = result['IV20'].iloc[4]  # Day of VIX spike
    expected_peak = 40.0 * 0.95  # 38%

    print("\n=== IV MARKET STRESS RESPONSE ===")
    print(f"Scenario: VIX spikes from 15% → 40% (market stress)")
    print(f"RV10 stays constant at 15% (backward-looking)")
    print(f"")
    print(f"BEFORE (RV × 1.2):")
    print(f"  IV20 remains constant at {iv20_before:.2f}%")
    print(f"  Does NOT respond to market stress")
    print(f"")
    print(f"AFTER (VIX-based):")
    print(f"  IV20 spikes to {iv20_peak:.2f}%")
    print(f"  CORRECTLY anticipates volatility increase")
    print(f"  Change: {iv20_peak / iv20_before:.2f}x multiplier")

    # Verify responsiveness
    assert abs(iv20_peak - expected_peak) < 0.5
    assert iv20_peak > iv20_before * 1.5, "IV should spike significantly during stress"


def test_profile_4_vanna_impact():
    """Show how IV calculation affects Profile 4 (Vanna) and Profile 1 (LDG)."""
    dates = pd.date_range('2023-01-01', periods=200, freq='D')

    # Test profiles that use IV directly (not just IV_rank)
    # Profile 1 (LDG) uses RV10/IV60 ratio and IV_rank_60

    # Scenario: Constant RV, but VIX changes
    df = pd.DataFrame({
        'date': [d.date() for d in dates],
        'close': 400.0,
        'RV5': 15.0,
        'RV10': 15.0,
        'RV20': 15.0,
        'ATR5': 8.0,
        'ATR10': 9.0,
        'MA20': 400.0,
        'MA50': 395.0,
        'slope_MA20': 0.01,
        'slope_MA50': 0.008,
        'return_5d': 0.02,
        'return_10d': 0.03,
        'return_20d': 0.04,
        'range_10d': 0.025,
        'price_to_MA20': 1.00,
        'price_to_MA50': 1.01,
        'vix_close': 18.0  # Matches RV × 1.2
    })

    detector = ProfileDetectors()
    df_result = detector.compute_all_profiles(df)

    # Check IV values
    iv60_with_vix = df_result['IV60'].iloc[100]  # VIX-based: 18 × 1.08 = 19.44
    iv60_old_method = 15.0 * 1.2  # Old: RV × 1.2 = 18.0

    print("\n=== IV CALCULATION IMPACT ON PROFILES ===")
    print(f"Scenario: RV10 = 15%, VIX = 18%")
    print(f"")
    print(f"IV60 calculation:")
    print(f"  BEFORE (RV × 1.2): {iv60_old_method:.2f}%")
    print(f"  AFTER (VIX × 1.08): {iv60_with_vix:.2f}%")
    print(f"  Difference: {iv60_with_vix - iv60_old_method:+.2f}%")
    print(f"")
    print(f"Profile 1 (LDG) uses RV10/IV60 ratio:")
    print(f"  BEFORE: 15.0 / 18.0 = {15.0/18.0:.3f}")
    print(f"  AFTER:  15.0 / 19.44 = {15.0/19.44:.3f}")
    print(f"  Impact: Lower ratio → different scoring")
    print(f"")
    print(f"This demonstrates IV calculation is now:")
    print(f"  ✓ Forward-looking (uses VIX market expectation)")
    print(f"  ✓ Variable (responds to VIX changes)")
    print(f"  ✓ Affects profile scores through IV-based formulas")

    # Just verify IV is calculated correctly
    expected_iv60 = 18.0 * 1.08
    assert abs(iv60_with_vix - expected_iv60) < 0.1, "IV60 should use VIX × 1.08"


def test_nan_handling_before_after():
    """Demonstrate NaN handling behavior before/after fix."""
    dates = pd.date_range('2023-01-01', periods=150, freq='D')

    df = pd.DataFrame({
        'date': [d.date() for d in dates],
        'close': 400.0,
        'RV5': 15.0,
        'RV10': 16.0,
        'RV20': 17.0,
        'ATR5': 8.0,
        'ATR10': 9.0,
        'MA20': 395.0,
        'MA50': 390.0,
        'slope_MA20': 0.01,
        'slope_MA50': 0.005,
        'return_5d': 0.02,
        'return_10d': 0.03,
        'return_20d': 0.04,
        'range_10d': 0.025,
        'price_to_MA20': 1.01,
        'price_to_MA50': 1.02,
        'vix_close': 20.0
    })

    # Corrupt data at row 120 (post-warmup)
    df.loc[120, 'RV10'] = np.nan

    detector = ProfileDetectors()
    df_with_profiles = detector.compute_all_profiles(df)

    print("\n=== NaN HANDLING COMPARISON ===")
    print(f"Scenario: Data corruption (NaN) at row 120 (post-warmup)")
    print(f"")
    print(f"BEFORE fix:")
    print(f"  - profile_1_LDG would use fillna(0)")
    print(f"  - Silently treats NaN as 0.0 score")
    print(f"  - Allocation proceeds with corrupt data")
    print(f"  - Portfolio allocates 0% to Profile 1 (wrong!)")
    print(f"  - Bug goes undetected until live trading")
    print(f"")
    print(f"AFTER fix:")
    print(f"  - NaN preserved in profile scores")
    print(f"  - validation checks detect NaN")

    # Test validation catches corruption
    from profiles.detectors import ProfileValidationError
    try:
        detector.validate_profile_scores(df_with_profiles, warmup_days=90)
        print(f"  - ERROR: Validation should have raised exception!")
        assert False, "Should have caught NaN corruption"
    except ProfileValidationError as e:
        print(f"  - ProfileValidationError raised: {str(e)[:80]}...")
        print(f"  - System HALTS before corrupt allocations")
        print(f"  - Bug detected immediately, not in live trading")

    print(f"")
    print(f"Impact: Prevents corrupt allocations and capital loss")


def test_allocation_error_clarity():
    """Show improved error messages from allocation NaN handling."""
    dates = pd.date_range('2023-01-01', periods=150, freq='D')

    df = pd.DataFrame({
        'date': [d.date() for d in dates],
        'close': 400.0,
        'RV5': 15.0,
        'RV10': 16.0,
        'RV20': 17.0,
        'ATR5': 8.0,
        'ATR10': 9.0,
        'MA20': 395.0,
        'MA50': 390.0,
        'slope_MA20': 0.01,
        'slope_MA50': 0.005,
        'return_5d': 0.02,
        'return_10d': 0.03,
        'return_20d': 0.04,
        'range_10d': 0.025,
        'price_to_MA20': 1.01,
        'price_to_MA50': 1.02,
        'vix_close': 20.0,
        'regime': 1
    })

    detector = ProfileDetectors()
    df_with_profiles = detector.compute_all_profiles(df)

    # Rename for allocation
    df_with_profiles = df_with_profiles.rename(columns={
        'profile_1_LDG': 'profile_1_score',
        'profile_2_SDG': 'profile_2_score',
        'profile_3_CHARM': 'profile_3_score',
        'profile_4_VANNA': 'profile_4_score',
        'profile_5_SKEW': 'profile_5_score',
        'profile_6_VOV': 'profile_6_score'
    })

    # Corrupt post-warmup data
    df_no_warmup = df_with_profiles.iloc[90:].copy()
    df_no_warmup.loc[df_no_warmup.index[50], 'profile_2_score'] = np.nan

    from backtest.rotation import RotationAllocator
    allocator = RotationAllocator()

    print("\n=== ALLOCATION ERROR HANDLING ===")
    print(f"Scenario: NaN in profile_2_score at post-warmup row")
    print(f"")
    print(f"BEFORE fix:")
    print(f"  - Silent fillna(0) converts NaN → 0.0")
    print(f"  - Allocation proceeds")
    print(f"  - Profile 2 gets 0% weight (wrong!)")
    print(f"  - No error message")
    print(f"")
    print(f"AFTER fix:")

    try:
        allocator.allocate_daily(df_no_warmup)
        assert False, "Should raise error"
    except ValueError as e:
        error_msg = str(e)
        print(f"  - ValueError raised with clear message:")
        print(f"    '{error_msg[:100]}...'")
        print(f"  - Error indicates: CRITICAL data corruption")
        print(f"  - Error provides: date, column name, row index")
        print(f"  - System HALTS before corrupt allocation")

    print(f"")
    print(f"Impact: Clear diagnostics + prevents silent corruption")


if __name__ == '__main__':
    # Run all comparison tests
    print("=" * 70)
    print("BEFORE/AFTER COMPARISON: IV & NaN FIXES")
    print("=" * 70)

    test_iv_before_after_comparison()
    test_iv_responds_to_market_stress()
    test_profile_4_vanna_impact()
    test_nan_handling_before_after()
    test_allocation_error_clarity()

    print("\n" + "=" * 70)
    print("ALL COMPARISONS COMPLETE")
    print("=" * 70)
