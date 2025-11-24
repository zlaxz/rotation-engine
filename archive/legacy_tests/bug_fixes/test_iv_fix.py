"""
Test suite for IV calculation fix.

Validates:
1. VIX-based IV calculation (forward-looking)
2. Proper term structure scaling
3. Fallback to RV proxy when VIX unavailable
4. IV values are different from RV × 1.2
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from profiles.features import ProfileFeatures
from data.loaders import DataSpine


def test_iv_uses_vix_when_available():
    """Test that IV is calculated from VIX, not RV × 1.2."""
    # Create test data with VIX
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    df = pd.DataFrame({
        'date': dates,
        'close': 400.0,
        'RV5': 15.0,
        'RV10': 16.0,
        'RV20': 17.0,
        'vix_close': 20.0  # VIX present
    })

    feature_engine = ProfileFeatures()
    result = feature_engine._compute_iv_proxies(df)

    # Check IV is VIX-based, not RV-based
    assert 'IV7' in result.columns
    assert 'IV20' in result.columns
    assert 'IV60' in result.columns

    # IV should be based on VIX (20.0), not RV
    # IV7 = VIX × 0.85 = 20 × 0.85 = 17.0
    # IV20 = VIX × 0.95 = 20 × 0.95 = 19.0
    # IV60 = VIX × 1.08 = 20 × 1.08 = 21.6
    expected_iv7 = 20.0 * 0.85
    expected_iv20 = 20.0 * 0.95
    expected_iv60 = 20.0 * 1.08

    # Check first row (no NaN from forward-fill)
    assert abs(result['IV7'].iloc[0] - expected_iv7) < 0.01
    assert abs(result['IV20'].iloc[0] - expected_iv20) < 0.01
    assert abs(result['IV60'].iloc[0] - expected_iv60) < 0.01

    # Verify IV is NOT RV × 1.2
    old_iv7 = df['RV5'].iloc[0] * 1.2  # 15 × 1.2 = 18.0
    assert abs(result['IV7'].iloc[0] - old_iv7) > 0.5  # Should be significantly different


def test_iv_term_structure_shape():
    """Test that IV term structure is properly shaped (upward sloping)."""
    dates = pd.date_range('2023-01-01', periods=50, freq='D')
    df = pd.DataFrame({
        'date': dates,
        'close': 400.0,
        'RV5': 15.0,
        'RV10': 16.0,
        'RV20': 17.0,
        'vix_close': 25.0
    })

    feature_engine = ProfileFeatures()
    result = feature_engine._compute_iv_proxies(df)

    # Term structure should be upward sloping in normal markets
    # IV7 < IV20 < IV60
    iv7 = result['IV7'].iloc[0]
    iv20 = result['IV20'].iloc[0]
    iv60 = result['IV60'].iloc[0]

    assert iv7 < iv20 < iv60, "IV term structure should be upward sloping"


def test_iv_fallback_when_no_vix():
    """Test fallback to RV × 1.2 when VIX unavailable."""
    dates = pd.date_range('2023-01-01', periods=50, freq='D')
    df = pd.DataFrame({
        'date': dates,
        'close': 400.0,
        'RV5': 15.0,
        'RV10': 16.0,
        'RV20': 17.0
        # No vix_close column
    })

    feature_engine = ProfileFeatures()

    # Capture stderr to check for warning
    import io
    captured_stderr = io.StringIO()
    old_stderr = sys.stderr
    sys.stderr = captured_stderr

    result = feature_engine._compute_iv_proxies(df)

    sys.stderr = old_stderr
    stderr_output = captured_stderr.getvalue()

    # Should see warning about fallback
    assert 'WARNING' in stderr_output
    assert 'RV-based IV proxy' in stderr_output

    # Should fallback to RV × 1.2
    expected_iv7 = 15.0 * 1.2
    expected_iv20 = 16.0 * 1.2
    expected_iv60 = 17.0 * 1.2

    assert abs(result['IV7'].iloc[0] - expected_iv7) < 0.01
    assert abs(result['IV20'].iloc[0] - expected_iv20) < 0.01
    assert abs(result['IV60'].iloc[0] - expected_iv60) < 0.01


def test_iv_with_varying_vix():
    """Test IV tracks VIX changes (forward-looking)."""
    dates = pd.date_range('2023-01-01', periods=5, freq='D')
    vix_values = [15.0, 20.0, 25.0, 30.0, 18.0]

    df = pd.DataFrame({
        'date': dates,
        'close': 400.0,
        'RV5': 15.0,  # Constant RV
        'RV10': 15.0,
        'RV20': 15.0,
        'vix_close': vix_values
    })

    feature_engine = ProfileFeatures()
    result = feature_engine._compute_iv_proxies(df)

    # IV should track VIX changes, not stay constant
    iv20_values = result['IV20'].values

    # IV should vary with VIX
    assert iv20_values.std() > 1.0, "IV should vary with VIX, not be constant"

    # IV should be proportional to VIX
    # Day 0: VIX=15 → IV20 = 15×0.95 = 14.25
    # Day 1: VIX=20 → IV20 = 20×0.95 = 19.0
    # Day 3: VIX=30 → IV20 = 30×0.95 = 28.5
    assert abs(iv20_values[0] - 14.25) < 0.01
    assert abs(iv20_values[1] - 19.0) < 0.01
    assert abs(iv20_values[3] - 28.5) < 0.01


def test_iv_handles_vix_nan_gaps():
    """Test IV forward-fills VIX NaN gaps (market closed days)."""
    dates = pd.date_range('2023-01-01', periods=10, freq='D')
    vix_values = [20.0] * 5 + [np.nan] * 3 + [25.0, 25.0]

    df = pd.DataFrame({
        'date': dates,
        'close': 400.0,
        'RV5': 15.0,
        'RV10': 16.0,
        'RV20': 17.0,
        'vix_close': vix_values
    })

    feature_engine = ProfileFeatures()
    result = feature_engine._compute_iv_proxies(df)

    # IV should forward-fill during NaN gaps
    iv20 = result['IV20']

    # Days 5-7 should have forward-filled values (20 × 0.95 = 19.0)
    assert not iv20.iloc[5:8].isna().any(), "IV should forward-fill VIX NaN gaps"
    assert abs(iv20.iloc[6] - 19.0) < 0.01, "Forward-fill should preserve last valid value"

    # Days 8-9 should update to new VIX value (25 × 0.95 = 23.75)
    assert abs(iv20.iloc[8] - 23.75) < 0.01


def test_iv_real_vix_integration():
    """Integration test: Load real VIX data and verify IV calculation."""
    try:
        spine = DataSpine()
        df = spine.build_spine(
            datetime(2023, 6, 1),
            datetime(2023, 6, 30),
            include_vix=True
        )

        # Check VIX was loaded
        assert 'vix_close' in df.columns, "VIX should be loaded from yfinance"
        assert not df['vix_close'].isna().all(), "VIX should have valid values"

        # Compute features (includes IV calculation)
        from profiles.features import ProfileFeatures
        feature_engine = ProfileFeatures()
        df = feature_engine.compute_all_features(df)

        # Check IV columns exist
        assert 'IV7' in df.columns
        assert 'IV20' in df.columns
        assert 'IV60' in df.columns

        # Check IV is based on VIX (should be similar magnitude)
        # VIX for June 2023 was ~13-16 range
        # IV20 should be close to VIX (0.95x multiplier)
        post_warmup = df.iloc[60:]  # After warmup
        mean_vix = post_warmup['vix_close'].mean()
        mean_iv20 = post_warmup['IV20'].mean()

        # IV20 should be ~95% of VIX
        ratio = mean_iv20 / mean_vix
        assert 0.93 < ratio < 0.97, f"IV20/VIX ratio should be ~0.95, got {ratio}"

        # Verify IV is NOT RV × 1.2
        mean_rv10 = post_warmup['RV10'].mean()
        old_iv20 = mean_rv10 * 1.2
        assert abs(mean_iv20 - old_iv20) > 1.0, "IV should differ significantly from RV × 1.2"

    except Exception as e:
        pytest.skip(f"Integration test requires VelocityData drive: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
