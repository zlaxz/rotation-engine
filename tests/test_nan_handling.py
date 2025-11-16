"""
Test suite for NaN handling fix.

Validates:
1. Profile scores preserve NaN during warmup (expected)
2. ProfileValidationError raised if NaN after warmup
3. Allocation logic raises error on NaN (not silent 0)
4. Portfolio merge fillna documented and acceptable
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from profiles.detectors import ProfileDetectors, ProfileValidationError
from backtest.rotation import RotationAllocator


def create_test_data_with_nan(warmup_days=60, total_days=200, nan_after_warmup=False):
    """Create test data with controllable NaN patterns."""
    dates = pd.date_range('2023-01-01', periods=total_days, freq='D')

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
        'price_to_MA50': 1.02
    })

    # Add VIX for real IV calculation
    df['vix_close'] = 20.0

    # Simulate warmup period NaN (first warmup_days rows)
    for col in ['RV10', 'RV20', 'ATR10', 'MA50', 'slope_MA50']:
        df.loc[df.index < warmup_days, col] = np.nan

    # Optionally add NaN after warmup (to trigger errors)
    if nan_after_warmup:
        # Corrupt data at row 150
        df.loc[150, 'RV10'] = np.nan

    return df


def test_profile_scores_preserve_nan_in_warmup():
    """Test that profile scores contain NaN during warmup (expected behavior)."""
    df = create_test_data_with_nan(warmup_days=60, total_days=200)

    detector = ProfileDetectors()
    df_with_profiles = detector.compute_all_profiles(df)

    # Check that profile scores have NaN in warmup period
    warmup_profiles = df_with_profiles.iloc[:60]

    # At least some profiles should have NaN in warmup
    assert warmup_profiles['profile_1_LDG'].isna().any(), "Profile scores should have NaN during warmup"
    assert warmup_profiles['profile_4_VANNA'].isna().any()


def test_profile_scores_valid_after_warmup():
    """Test that profile scores are valid (no NaN) after warmup period."""
    df = create_test_data_with_nan(warmup_days=60, total_days=200, nan_after_warmup=False)

    detector = ProfileDetectors()
    df_with_profiles = detector.compute_all_profiles(df)

    # Check that profile scores have no NaN after warmup
    post_warmup = df_with_profiles.iloc[90:]  # After 90-day warmup

    profile_cols = [
        'profile_1_LDG', 'profile_2_SDG', 'profile_3_CHARM',
        'profile_4_VANNA', 'profile_5_SKEW', 'profile_6_VOV'
    ]

    for col in profile_cols:
        nan_count = post_warmup[col].isna().sum()
        assert nan_count == 0, f"{col} should have no NaN after warmup, found {nan_count}"


def test_validation_passes_with_clean_data():
    """Test that validation passes when no NaN after warmup."""
    df = create_test_data_with_nan(warmup_days=60, total_days=200, nan_after_warmup=False)

    detector = ProfileDetectors()
    df_with_profiles = detector.compute_all_profiles(df)

    # Validation should pass (no exception)
    try:
        detector.validate_profile_scores(df_with_profiles, warmup_days=90)
    except ProfileValidationError as e:
        pytest.fail(f"Validation should pass with clean data, but raised: {e}")


def test_validation_raises_error_on_nan_after_warmup():
    """Test that validation raises ProfileValidationError if NaN detected after warmup."""
    df = create_test_data_with_nan(warmup_days=60, total_days=200, nan_after_warmup=True)

    detector = ProfileDetectors()
    df_with_profiles = detector.compute_all_profiles(df)

    # Validation should raise ProfileValidationError
    with pytest.raises(ProfileValidationError) as exc_info:
        detector.validate_profile_scores(df_with_profiles, warmup_days=90)

    # Error message should be informative
    error_msg = str(exc_info.value)
    assert "NaN values after warmup" in error_msg
    assert "missing/corrupt data" in error_msg


def test_allocation_raises_error_on_nan_in_warmup():
    """Test that allocation raises error if called with warmup period data."""
    df = create_test_data_with_nan(warmup_days=60, total_days=100, nan_after_warmup=False)

    detector = ProfileDetectors()
    df_with_profiles = detector.compute_all_profiles(df)

    # Add regime column (required for allocation)
    df_with_profiles['regime'] = 1  # Trend Up

    # Rename profile columns to match allocation expectation
    df_with_profiles = df_with_profiles.rename(columns={
        'profile_1_LDG': 'profile_1_score',
        'profile_2_SDG': 'profile_2_score',
        'profile_3_CHARM': 'profile_3_score',
        'profile_4_VANNA': 'profile_4_score',
        'profile_5_SKEW': 'profile_5_score',
        'profile_6_VOV': 'profile_6_score'
    })

    allocator = RotationAllocator()

    # Try to allocate on data that includes warmup period (rows with NaN)
    # Should raise ValueError about warmup period
    with pytest.raises(ValueError) as exc_info:
        allocator.allocate_daily(df_with_profiles)

    error_msg = str(exc_info.value)
    assert "warmup period" in error_msg.lower() or "NaN" in error_msg


def test_allocation_raises_error_on_nan_post_warmup():
    """Test that allocation raises CRITICAL error if NaN detected post-warmup."""
    df = create_test_data_with_nan(warmup_days=60, total_days=200, nan_after_warmup=False)

    detector = ProfileDetectors()
    df_with_profiles = detector.compute_all_profiles(df)

    # Add regime
    df_with_profiles['regime'] = 1

    # Rename columns
    df_with_profiles = df_with_profiles.rename(columns={
        'profile_1_LDG': 'profile_1_score',
        'profile_2_SDG': 'profile_2_score',
        'profile_3_CHARM': 'profile_3_score',
        'profile_4_VANNA': 'profile_4_score',
        'profile_5_SKEW': 'profile_5_score',
        'profile_6_VOV': 'profile_6_score'
    })

    # Skip warmup period (first 90 days)
    df_no_warmup = df_with_profiles.iloc[90:].copy()

    # Corrupt one profile score post-warmup
    df_no_warmup.loc[df_no_warmup.index[50], 'profile_2_score'] = np.nan

    allocator = RotationAllocator()

    # Should raise CRITICAL error about corrupt data
    with pytest.raises(ValueError) as exc_info:
        allocator.allocate_daily(df_no_warmup)

    error_msg = str(exc_info.value)
    assert "CRITICAL" in error_msg or "corrupt" in error_msg.lower()


def test_allocation_works_without_nan():
    """Test that allocation works normally when no NaN present."""
    df = create_test_data_with_nan(warmup_days=60, total_days=150, nan_after_warmup=False)

    detector = ProfileDetectors()
    df_with_profiles = detector.compute_all_profiles(df)

    # Add regime
    df_with_profiles['regime'] = 1

    # Rename columns
    df_with_profiles = df_with_profiles.rename(columns={
        'profile_1_LDG': 'profile_1_score',
        'profile_2_SDG': 'profile_2_score',
        'profile_3_CHARM': 'profile_3_score',
        'profile_4_VANNA': 'profile_4_score',
        'profile_5_SKEW': 'profile_5_score',
        'profile_6_VOV': 'profile_6_score'
    })

    # Skip warmup
    df_no_warmup = df_with_profiles.iloc[90:].copy()

    allocator = RotationAllocator()

    # Should work without errors
    try:
        allocation = allocator.allocate_daily(df_no_warmup)
        assert len(allocation) > 0, "Should return allocation weights"
    except ValueError as e:
        pytest.fail(f"Allocation should work with clean data, but raised: {e}")


def test_profile_detectors_no_fillna_zero():
    """Test that profile detector functions don't use fillna(0)."""
    # Read the detectors.py source code
    detector_file = os.path.join(
        os.path.dirname(__file__), '..', 'src', 'profiles', 'detectors.py'
    )

    with open(detector_file, 'r') as f:
        source = f.read()

    # Check that profile scoring functions don't use fillna(0)
    # (Portfolio merge fillna is acceptable, but not in profile scoring)
    lines = source.split('\n')

    problematic_fillna = []
    for i, line in enumerate(lines):
        if 'fillna(0)' in line and '_compute_' in source[max(0, i-20):i+5]:
            # Found fillna(0) in a profile compute function
            problematic_fillna.append((i+1, line.strip()))

    assert len(problematic_fillna) == 0, (
        f"Found fillna(0) in profile scoring functions (should preserve NaN): "
        f"{problematic_fillna}"
    )


def test_nan_documentation_in_detectors():
    """Test that detectors.py has NaN handling policy documented."""
    detector_file = os.path.join(
        os.path.dirname(__file__), '..', 'src', 'profiles', 'detectors.py'
    )

    with open(detector_file, 'r') as f:
        source = f.read()

    # Check for NaN policy documentation
    assert "NaN HANDLING POLICY" in source or "NaN handling" in source, (
        "detectors.py should document NaN handling policy"
    )
    assert "ProfileValidationError" in source, (
        "detectors.py should define ProfileValidationError exception"
    )


def test_warmup_period_nan_acceptable():
    """Test that NaN in warmup period is expected and documented."""
    df = create_test_data_with_nan(warmup_days=60, total_days=100)

    detector = ProfileDetectors()
    df_with_profiles = detector.compute_all_profiles(df)

    # Warmup period should have NaN (this is EXPECTED)
    warmup = df_with_profiles.iloc[:60]

    # At least one profile should have NaN in warmup
    has_nan = any(warmup[col].isna().any() for col in [
        'profile_1_LDG', 'profile_2_SDG', 'profile_3_CHARM',
        'profile_4_VANNA', 'profile_5_SKEW', 'profile_6_VOV'
    ])

    assert has_nan, "Warmup period should contain NaN (expected for rolling window features)"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
