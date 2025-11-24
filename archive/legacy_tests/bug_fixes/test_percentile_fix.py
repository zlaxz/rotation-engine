"""Validation tests for BUG-C04/C05 percentile fix.

Tests verify:
1. Percentile uses only past data (walk-forward compliance)
2. Consistent results (no duplicates, one implementation)
3. Reasonable values (0-100 range)
4. No off-by-one shift errors
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from regimes.signals import RegimeSignals


class TestPercentileFix:
    """Test suite for percentile calculation fix."""

    @pytest.fixture
    def sample_data(self):
        """Create sample time series for testing."""
        np.random.seed(42)
        dates = pd.date_range('2022-01-01', periods=100, freq='D')

        # Create known pattern: increasing trend with some noise
        values = np.linspace(10, 20, 100) + np.random.randn(100) * 0.5

        df = pd.DataFrame({
            'date': dates,
            'RV20': values
        })
        return df

    def test_walk_forward_compliance(self, sample_data):
        """CRITICAL: Verify percentile at time t uses ONLY data from 0 to t-1."""
        calculator = RegimeSignals(lookback_percentile=20)

        # Compute percentiles
        percentiles = calculator._compute_walk_forward_percentile(
            sample_data['RV20'],
            window=20
        )

        # Manual verification for specific points
        for i in [25, 50, 75]:
            # Get lookback window (PAST data only, excluding current point)
            lookback = sample_data['RV20'].iloc[max(0, i-20):i]
            current_val = sample_data['RV20'].iloc[i]

            # Calculate expected percentile
            expected_pct = (lookback < current_val).sum() / len(lookback)
            actual_pct = percentiles.iloc[i]

            # Should match
            assert abs(expected_pct - actual_pct) < 0.001, (
                f"At index {i}: expected {expected_pct:.4f}, got {actual_pct:.4f}. "
                f"This indicates look-ahead bias or incorrect window calculation."
            )

    def test_no_look_ahead_bias(self, sample_data):
        """Verify current point is NOT included in percentile calculation."""
        calculator = RegimeSignals(lookback_percentile=20)

        # Create series where last value is extreme
        test_series = sample_data['RV20'].copy()
        test_series.iloc[50] = 999  # Extreme outlier

        percentiles = calculator._compute_walk_forward_percentile(test_series, window=20)

        # At index 50, percentile should be calculated using indices 30-49
        # The extreme value at 50 should NOT be included
        # So percentile should be based on comparison with past values

        # Get lookback (indices 30-49, NOT including 50)
        lookback = test_series.iloc[30:50]
        current_val = test_series.iloc[50]

        # Since current_val (999) is way higher than all lookback values,
        # percentile should be 100% (or 1.0)
        expected_pct = (lookback < current_val).sum() / len(lookback)
        actual_pct = percentiles.iloc[50]

        assert abs(expected_pct - actual_pct) < 0.001
        assert actual_pct == 1.0, "Extreme high value should have 100th percentile"

    def test_percentile_range(self, sample_data):
        """Verify all percentile values are in valid range [0, 1]."""
        calculator = RegimeSignals(lookback_percentile=20)

        percentiles = calculator._compute_walk_forward_percentile(
            sample_data['RV20'],
            window=20
        )

        # All values should be in [0, 1]
        assert (percentiles >= 0).all(), "Percentiles cannot be negative"
        assert (percentiles <= 1).all(), "Percentiles cannot exceed 1.0"

        # Should have variation (not all the same)
        assert percentiles.std() > 0.01, "Percentiles should vary"

    def test_no_duplicate_columns(self):
        """Verify only ONE percentile column exists after fix."""
        calculator = RegimeSignals(lookback_percentile=60)

        # Create dummy SPY data
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

        # Compute signals
        result = calculator.compute_all_signals(spy_data)

        # Should have RV20_percentile but NOT RV20_rank
        assert 'RV20_percentile' in result.columns, "Missing RV20_percentile column"
        assert 'RV20_rank' not in result.columns, "RV20_rank column should not exist (removed duplicate)"

        # Only one RV20 percentile-related column
        percentile_cols = [col for col in result.columns if 'RV20' in col and ('percentile' in col or 'rank' in col)]
        assert len(percentile_cols) == 1, f"Should have exactly 1 percentile column, found {len(percentile_cols)}: {percentile_cols}"

    def test_off_by_one_fix(self, sample_data):
        """Verify no off-by-one shift error in percentile calculation."""
        calculator = RegimeSignals(lookback_percentile=10)

        # Create series with known pattern
        test_series = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])

        percentiles = calculator._compute_walk_forward_percentile(test_series, window=10)

        # At index 12 (value=13):
        # Lookback should be indices 2-11 (values 3-12)
        # Current value 13 > all of [3,4,5,6,7,8,9,10,11,12]
        # So percentile should be 10/10 = 1.0

        lookback = test_series.iloc[2:12]  # indices 2-11
        current = test_series.iloc[12]  # value 13
        expected = (lookback < current).sum() / len(lookback)

        assert abs(percentiles.iloc[12] - expected) < 0.001
        assert percentiles.iloc[12] == 1.0, "Value 13 should be 100th percentile of [3-12]"

        # At index 11 (value=12):
        # Lookback should be indices 1-10 (values 2-11)
        # Current value 12 > all of [2,3,4,5,6,7,8,9,10,11]
        # So percentile should be 10/10 = 1.0

        lookback = test_series.iloc[1:11]
        current = test_series.iloc[11]
        expected = (lookback < current).sum() / len(lookback)

        assert abs(percentiles.iloc[11] - expected) < 0.001
        assert percentiles.iloc[11] == 1.0, "Value 12 should be 100th percentile of [2-11]"

    def test_consistent_with_manual_calculation(self, sample_data):
        """Verify automated calculation matches manual percentile computation."""
        calculator = RegimeSignals(lookback_percentile=20)

        # Compute using the method
        auto_percentiles = calculator._compute_walk_forward_percentile(
            sample_data['RV20'],
            window=20
        )

        # Manual calculation for index 50
        i = 50
        lookback = sample_data['RV20'].iloc[30:50]  # indices 30-49
        current = sample_data['RV20'].iloc[50]
        manual_pct = (lookback < current).sum() / len(lookback)

        assert abs(auto_percentiles.iloc[50] - manual_pct) < 0.001, (
            f"Automated ({auto_percentiles.iloc[50]:.4f}) != Manual ({manual_pct:.4f})"
        )


class TestRegimeImpact:
    """Test impact of percentile fix on regime classification."""

    def test_percentile_values_reasonable(self):
        """Verify percentile values are in reasonable range after fix."""
        calculator = RegimeSignals(lookback_percentile=60)

        # Load actual SPY data if available
        spy_data_path = Path(__file__).parent.parent / 'data' / 'spy_features_2022.parquet'

        if spy_data_path.exists():
            spy_data = pd.read_parquet(spy_data_path)
            result = calculator.compute_all_signals(spy_data)

            # Check percentile distribution
            pct = result['RV20_percentile']

            # Should be well-distributed across [0, 1]
            assert pct.min() >= 0.0
            assert pct.max() <= 1.0
            assert pct.mean() > 0.2 and pct.mean() < 0.8, "Mean should be near 0.5"

            # Should have reasonable spread
            assert pct.std() > 0.1, "Should have variation"

            print(f"\nRV20_percentile stats after fix:")
            print(f"  Mean: {pct.mean():.3f}")
            print(f"  Std:  {pct.std():.3f}")
            print(f"  Min:  {pct.min():.3f}")
            print(f"  Max:  {pct.max():.3f}")
        else:
            pytest.skip("SPY data not available for integration test")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
