"""Test suite for walk-forward compliance in rolling calculations.

CRITICAL: Ensures no look-ahead bias in percentile calculations.

Tests:
1. ProfileFeatures._rolling_percentile() - verify excludes current point
2. RegimeSignals._compute_walk_forward_percentile() - verify excludes current point
3. Compare against naive implementation that includes current point (should differ)
4. Verify warmup period handling
"""

import pytest
import pandas as pd
import numpy as np
from src.profiles.features import ProfileFeatures
from src.regimes.signals import RegimeSignals


class TestWalkForwardCompliance:
    """Test all rolling percentile calculations are walk-forward compliant."""

    def test_profile_features_rolling_percentile_excludes_current(self):
        """ProfileFeatures._rolling_percentile() must exclude current point from window."""
        pf = ProfileFeatures(lookback_percentile=60)

        # Create test series with known pattern
        # [10, 20, 30, 40, 50] with window=3
        # At index 2 (value=30): percentile vs [10, 20] = 100% (2/2)
        # At index 3 (value=40): percentile vs [20, 30] = 100% (2/2)
        # At index 4 (value=50): percentile vs [30, 40] = 100% (2/2)

        test_series = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
        result = pf._rolling_percentile(test_series, window=3)

        # At index 2, current=30, past=[10, 20]
        # (10 < 30) + (20 < 30) = 2, percentile = 2/2 = 1.0
        assert result.iloc[2] == 1.0, f"Expected 1.0, got {result.iloc[2]}"

        # At index 3, current=40, past=[20, 30]
        assert result.iloc[3] == 1.0, f"Expected 1.0, got {result.iloc[3]}"

        # At index 4, current=50, past=[30, 40]
        assert result.iloc[4] == 1.0, f"Expected 1.0, got {result.iloc[4]}"

        print("✅ ProfileFeatures._rolling_percentile() excludes current point")

    def test_profile_features_vs_naive_implementation(self):
        """Verify correct implementation differs from naive (look-ahead) version."""
        pf = ProfileFeatures(lookback_percentile=60)

        # Test series
        test_series = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0, 25.0, 35.0])

        # Correct (walk-forward)
        correct = pf._rolling_percentile(test_series, window=3)

        # Naive (WRONG - includes current point)
        def naive_percentile(series, window):
            def percentile_rank_naive(x):
                if len(x) < 2:
                    return 0.5
                # WRONG: includes current in window
                current = x[-1]
                return (x < current).sum() / len(x)  # Includes current in comparison

            return series.rolling(window=window, min_periods=1).apply(
                percentile_rank_naive, raw=True
            )

        naive = naive_percentile(test_series, window=3)

        # They should differ (naive will be systematically higher)
        # At index 2: correct uses [10, 20] vs 30 = 1.0
        #             naive uses [10, 20, 30] vs 30 = 2/3 = 0.67
        assert correct.iloc[2] != naive.iloc[2], "Correct and naive should differ"
        assert correct.iloc[2] > naive.iloc[2], "Correct should be higher (excludes current)"

        print("✅ Correct implementation differs from naive look-ahead version")

    def test_regime_signals_walk_forward_percentile(self):
        """RegimeSignals._compute_walk_forward_percentile() must exclude current point."""
        rs = RegimeSignals(lookback_percentile=60)

        # Test series
        test_series = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
        result = rs._compute_walk_forward_percentile(test_series, window=3)

        # At index 2, current=30, lookback=series.iloc[:2]=[10, 20]
        # (10 < 30) + (20 < 30) = 2, percentile = 2/2 = 1.0
        assert result.iloc[2] == 1.0, f"Expected 1.0, got {result.iloc[2]}"

        # At index 3, current=40, lookback=series.iloc[0:3]=[10, 20, 30]
        # All 3 values < 40, percentile = 3/3 = 1.0
        assert result.iloc[3] == 1.0, f"Expected 1.0, got {result.iloc[3]}"

        print("✅ RegimeSignals._compute_walk_forward_percentile() excludes current point")

    def test_percentile_at_minimum_value(self):
        """When current value is minimum, percentile should be 0."""
        pf = ProfileFeatures(lookback_percentile=60)

        # Series where last value is minimum
        test_series = pd.Series([50.0, 40.0, 30.0, 20.0, 10.0])
        result = pf._rolling_percentile(test_series, window=3)

        # At index 4, current=10, past=[20, 30]
        # (20 < 10) + (30 < 10) = 0, percentile = 0/2 = 0.0
        assert result.iloc[4] == 0.0, f"Expected 0.0, got {result.iloc[4]}"

        print("✅ Minimum value correctly gives 0.0 percentile")

    def test_percentile_at_median(self):
        """When current value is median, percentile should be ~0.5."""
        pf = ProfileFeatures(lookback_percentile=60)

        # Series where current value is median
        test_series = pd.Series([10.0, 30.0, 20.0])
        result = pf._rolling_percentile(test_series, window=3)

        # At index 2, current=20, past=[10, 30]
        # (10 < 20) = 1, percentile = 1/2 = 0.5
        assert result.iloc[2] == 0.5, f"Expected 0.5, got {result.iloc[2]}"

        print("✅ Median value correctly gives 0.5 percentile")

    def test_warmup_period_handling(self):
        """Verify behavior during warmup period (insufficient history)."""
        pf = ProfileFeatures(lookback_percentile=60)
        rs = RegimeSignals(lookback_percentile=60)

        # Very short series (less than window)
        test_series = pd.Series([10.0, 20.0, 30.0])

        # ProfileFeatures with window=5 (longer than series)
        result_pf = pf._rolling_percentile(test_series, window=5)

        # Should handle gracefully (no crashes)
        assert len(result_pf) == len(test_series)
        assert not result_pf.isna().all(), "Should have some valid values"

        # RegimeSignals
        result_rs = rs._compute_walk_forward_percentile(test_series, window=5)

        # At index 0, no history → default to 0.5
        assert result_rs.iloc[0] == 0.5, f"Expected 0.5 for first point, got {result_rs.iloc[0]}"

        # At index 1, lookback=[10], current=20
        # (10 < 20) = 1, percentile = 1/1 = 1.0
        assert result_rs.iloc[1] == 1.0, f"Expected 1.0, got {result_rs.iloc[1]}"

        print("✅ Warmup period handled correctly")

    def test_real_data_integration(self):
        """Test with realistic data to ensure no crashes and reasonable output."""
        pf = ProfileFeatures(lookback_percentile=60)
        rs = RegimeSignals(lookback_percentile=60)

        # Simulate 200 days of RV data (realistic values)
        np.random.seed(42)
        rv_data = pd.Series(0.15 + 0.10 * np.random.randn(200))  # Mean 15% vol, 10% stdev
        rv_data = rv_data.clip(lower=0.05)  # Keep positive

        # ProfileFeatures
        result_pf = pf._rolling_percentile(rv_data, window=60)

        # Check outputs are in valid range [0, 1]
        assert result_pf.min() >= 0.0, f"Min percentile {result_pf.min()} < 0"
        assert result_pf.max() <= 1.0, f"Max percentile {result_pf.max()} > 1"

        # Check distribution is reasonable (not all same value)
        assert result_pf.std() > 0.1, f"Percentiles too uniform: std={result_pf.std()}"

        # RegimeSignals
        result_rs = rs._compute_walk_forward_percentile(rv_data, window=60)

        assert result_rs.min() >= 0.0
        assert result_rs.max() <= 1.0
        assert result_rs.std() > 0.1

        print("✅ Real data integration test passed")

    def test_no_future_leakage_explicit(self):
        """Explicit test: changing future values should NOT affect past percentiles."""
        pf = ProfileFeatures(lookback_percentile=60)

        # Original series
        original = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
        result_original = pf._rolling_percentile(original, window=3)

        # Modified series (change last value only)
        modified = pd.Series([10.0, 20.0, 30.0, 40.0, 999.0])
        result_modified = pf._rolling_percentile(modified, window=3)

        # Percentiles at index 0-3 should be IDENTICAL
        # (because index 4 value doesn't affect them in walk-forward)
        for i in range(4):
            assert result_original.iloc[i] == result_modified.iloc[i], \
                f"Changing future value affected past percentile at index {i}"

        # Only index 4 should differ
        assert result_original.iloc[4] != result_modified.iloc[4], \
            "Current index should be affected by its own value"

        print("✅ Explicit future leakage test PASSED - no contamination")


class TestLookAheadBiasScenarios:
    """Specific scenarios that would expose look-ahead bias if present."""

    def test_spike_detection_scenario(self):
        """Scenario: Market spike should NOT inflate pre-spike percentiles."""
        pf = ProfileFeatures(lookback_percentile=60)

        # Calm market, then sudden spike
        test_series = pd.Series([0.15, 0.16, 0.14, 0.15, 0.50])  # Spike to 50%
        result = pf._rolling_percentile(test_series, window=4)

        # At index 3 (before spike), percentile should be computed vs [0.15, 0.16, 0.14]
        # Value 0.15 vs [0.15, 0.16, 0.14] → (0.14 < 0.15) + (0.15 < 0.15) + (0.16 < 0.15)
        #                                     = 1 + 0 + 0 = 1, percentile = 1/3 = 0.33
        pct_before_spike = result.iloc[3]

        # If look-ahead bias present, this would be inflated by the 0.50 spike
        # Without bias, should be normal (~0.33)
        assert pct_before_spike < 0.6, \
            f"Pre-spike percentile {pct_before_spike} suspiciously high (look-ahead?)"

        print("✅ Spike scenario: pre-spike percentiles not contaminated")

    def test_regime_change_scenario(self):
        """Scenario: Regime change should NOT affect pre-change percentiles."""
        rs = RegimeSignals(lookback_percentile=60)

        # Low vol regime → High vol regime
        low_vol = [0.10] * 20
        high_vol = [0.30] * 20
        test_series = pd.Series(low_vol + high_vol)

        result = rs._compute_walk_forward_percentile(test_series, window=10)

        # At index 15 (still in low vol), percentile should be based on low vol history
        # NOT contaminated by upcoming high vol
        pct_at_idx15 = result.iloc[15]

        # Should be moderate (comparing 0.10 to other 0.10s)
        # NOT high (which would indicate future high vol contamination)
        assert 0.3 < pct_at_idx15 < 0.7, \
            f"Percentile at index 15: {pct_at_idx15} - may be contaminated by future regime"

        print("✅ Regime change scenario: no future contamination")


def run_all_tests():
    """Run all walk-forward compliance tests."""
    print("\n" + "="*70)
    print("WALK-FORWARD COMPLIANCE TEST SUITE")
    print("="*70 + "\n")

    # Test class 1
    print("Test Suite 1: Core Walk-Forward Compliance")
    print("-" * 70)
    test1 = TestWalkForwardCompliance()
    test1.test_profile_features_rolling_percentile_excludes_current()
    test1.test_profile_features_vs_naive_implementation()
    test1.test_regime_signals_walk_forward_percentile()
    test1.test_percentile_at_minimum_value()
    test1.test_percentile_at_median()
    test1.test_warmup_period_handling()
    test1.test_real_data_integration()
    test1.test_no_future_leakage_explicit()

    # Test class 2
    print("\n" + "-" * 70)
    print("Test Suite 2: Look-Ahead Bias Scenarios")
    print("-" * 70)
    test2 = TestLookAheadBiasScenarios()
    test2.test_spike_detection_scenario()
    test2.test_regime_change_scenario()

    print("\n" + "="*70)
    print("ALL TESTS PASSED ✅")
    print("="*70)
    print("\nConclusion: Rolling percentile calculations are walk-forward compliant.")
    print("No look-ahead bias detected.")


if __name__ == "__main__":
    run_all_tests()
