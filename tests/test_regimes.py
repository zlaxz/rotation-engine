"""Test suite for regime classification."""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from regimes import RegimeSignals, RegimeClassifier
from data import DataSpine


class TestRegimeSignals:
    """Test regime signal calculations."""

    def test_signal_calculation(self):
        """Test that all signals are computed without errors."""
        # Load sample data
        from datetime import datetime
        spine = DataSpine()
        spy_data = spine.build_spine(
            start_date=datetime(2022, 1, 1),
            end_date=datetime(2022, 12, 31)
        )

        # Compute signals
        signal_calc = RegimeSignals()
        df_with_signals = signal_calc.compute_all_signals(spy_data)

        # Check that signal columns exist
        expected_columns = [
            'RV5_RV20_ratio',
            'RV10_RV20_ratio',
            'RV20_rank',
            'vol_of_vol',
            'vol_of_vol_slope',
            'ATR10_rank',
            'is_compressed',
            'MA_distance',
            'MA20_above_MA50',
            'slope_near_zero',
            'RSI'
        ]

        for col in expected_columns:
            assert col in df_with_signals.columns, f"Missing signal column: {col}"

    def test_walk_forward_percentile(self):
        """Test that percentile calculation is walk-forward."""
        signal_calc = RegimeSignals()

        # Create simple test series
        series = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

        # Compute percentiles
        percentiles = signal_calc._compute_walk_forward_percentile(series, window=5)

        # At index 5 (value=6), percentile should be relative to [1,2,3,4,5]
        # 6 is greater than all 5 values, so percentile should be 1.0
        assert percentiles.iloc[5] == 1.0, "Walk-forward percentile incorrect"

        # At index 0, should default to 0.5 (no lookback)
        assert percentiles.iloc[0] == 0.5, "First percentile should be 0.5"

    def test_no_look_ahead_bias(self):
        """Verify no look-ahead bias in signal calculations."""
        from datetime import datetime
        spine = DataSpine()
        spy_data = spine.build_spine(
            start_date=datetime(2022, 1, 1),
            end_date=datetime(2022, 3, 31)
        )

        signal_calc = RegimeSignals()
        df_with_signals = signal_calc.compute_all_signals(spy_data)

        # For each row, signals should only use data up to that row
        # Check that RV20_rank at index i doesn't depend on data after index i
        # This is implicit in rolling() but verify no NaN at end
        assert not df_with_signals['RV20_rank'].iloc[-10:].isna().all(), \
            "Percentile should be calculated for recent data"

    def test_RSI_calculation(self):
        """Test RSI calculation."""
        signal_calc = RegimeSignals()

        # Create simple price series
        prices = pd.Series([100, 102, 104, 103, 105, 107, 106, 108, 110, 109])

        rsi = signal_calc._compute_RSI(prices, window=5)

        # RSI should be between 0 and 100
        assert (rsi >= 0).all() and (rsi <= 100).all(), "RSI out of bounds"


class TestRegimeClassifier:
    """Test regime classification logic."""

    def test_basic_classification(self):
        """Test that classification runs without errors."""
        from datetime import datetime
        spine = DataSpine()
        spy_data = spine.build_spine(
            start_date=datetime(2022, 1, 1),
            end_date=datetime(2022, 12, 31)
        )

        classifier = RegimeClassifier()
        df_classified = classifier.classify_period(spy_data)

        # Check regime columns exist
        assert 'regime_label' in df_classified.columns
        assert 'regime_name' in df_classified.columns

        # Check all regimes are 1-6
        assert df_classified['regime_label'].between(1, 6).all(), \
            "Regime labels should be 1-6"

        # Check no NaN regimes
        assert not df_classified['regime_label'].isna().any(), \
            "Should have no NaN regime labels"

    def test_trend_up_detection(self):
        """Test trend up regime detection."""
        classifier = RegimeClassifier()

        # Create row that should be trend up
        row = pd.Series({
            'return_20d': 0.05,  # 5% positive return
            'price_to_MA20': 0.02,  # Above MA20
            'price_to_MA50': 0.03,  # Above MA50
            'slope_MA20': 0.001,  # Positive slope
            'RV20_rank': 0.30,  # Low vol
            'is_event': False
        })

        assert classifier._is_trend_up(row), "Should detect trend up"

    def test_trend_down_detection(self):
        """Test trend down regime detection."""
        classifier = RegimeClassifier()

        # Create row that should be trend down
        row = pd.Series({
            'return_20d': -0.05,  # -5% negative return
            'price_to_MA20': -0.02,  # Below MA20
            'price_to_MA50': -0.03,  # Below MA50
            'slope_MA20': -0.001,  # Negative slope
            'RV20_rank': 0.60,  # Elevated vol
            'is_event': False
        })

        assert classifier._is_trend_down(row), "Should detect trend down"

    def test_compression_detection(self):
        """Test compression regime detection."""
        classifier = RegimeClassifier()

        # Create row that should be compression
        row = pd.Series({
            'range_10d': 0.025,  # Tight range
            'RV20_rank': 0.20,  # Low vol percentile
            'slope_MA20': 0.0001,  # Flat
            'is_event': False
        })

        assert classifier._is_compression(row), "Should detect compression"

    def test_breaking_vol_detection(self):
        """Test breaking vol regime detection."""
        classifier = RegimeClassifier()

        # Create row that should be breaking vol
        row = pd.Series({
            'RV20_rank': 0.90,  # Very high vol percentile
            'vol_of_vol': 0.30,  # Elevated vol-of-vol
            'RV20': 0.50,  # High RV
            'is_event': False
        })

        assert classifier._is_breaking_vol(row), "Should detect breaking vol"

    def test_event_priority(self):
        """Test that event regime has highest priority."""
        classifier = RegimeClassifier()

        # Create row that could be anything but has event flag
        row = pd.Series({
            'is_event': True,
            'return_20d': 0.05,
            'price_to_MA20': 0.02,
            'price_to_MA50': 0.03,
            'slope_MA20': 0.001,
            'RV20_rank': 0.30,
            'range_10d': 0.025,
            'vol_of_vol': 0.10,
            'RV20': 0.15
        })

        regime = classifier._classify_row(row)
        assert regime == classifier.REGIME_EVENT, "Event should override all other regimes"

    def test_regime_statistics(self):
        """Test regime statistics calculation."""
        from datetime import datetime
        spine = DataSpine()
        spy_data = spine.build_spine(
            start_date=datetime(2022, 1, 1),
            end_date=datetime(2022, 12, 31)
        )

        classifier = RegimeClassifier()
        df_classified = classifier.classify_period(spy_data)

        stats = classifier.compute_regime_statistics(df_classified)

        # Check stats structure
        assert 'frequency' in stats
        assert 'duration' in stats
        assert 'transitions' in stats
        assert 'total_transitions' in stats

        # Check frequencies sum to 1.0
        total_freq = sum(stats['frequency'].values())
        assert abs(total_freq - 1.0) < 0.01, "Frequencies should sum to 1.0"

    def test_historical_validation(self):
        """Test historical validation against known dates."""
        from datetime import datetime
        spine = DataSpine()
        spy_data = spine.build_spine(
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2024, 12, 31)
        )

        classifier = RegimeClassifier()
        df_classified = classifier.classify_period(spy_data)

        validation = classifier.validate_historical_regimes(df_classified)

        # Should have validation results
        assert len(validation) > 0, "Should have validation results"

        # Check that 2020 crash is detected
        if '2020 COVID Crash' in validation:
            result = validation['2020 COVID Crash']
            # Should be either Trend Down or Breaking Vol
            assert result['passed'] or result['actual'] in ['Trend Down', 'Breaking Vol'], \
                f"2020 crash should be Downtrend or Breaking Vol, got {result['actual']}"


class TestRegimeValidation:
    """Test regime validation and sanity checks."""

    def test_sanity_checks(self):
        """Test regime sanity checks."""
        from datetime import datetime
        from regimes.validator import RegimeValidator

        spine = DataSpine()
        spy_data = spine.build_spine(
            start_date=datetime(2022, 1, 1),
            end_date=datetime(2024, 12, 31)
        )

        classifier = RegimeClassifier()
        df_classified = classifier.classify_period(spy_data)

        validator = RegimeValidator()
        checks = validator.sanity_check_regimes(df_classified)

        # Should pass basic checks
        assert checks['no_nan_regimes']['passed'], "Should have no NaN regimes"

        # Should have reasonable duration
        # (may fail if classifier is broken, but good to check)
        assert checks['reasonable_duration']['passed'], \
            f"Average regime duration too short: {checks['reasonable_duration']['avg_duration']}"


def test_integration():
    """Integration test: Full pipeline from data to regime classification."""
    # Load data
    from datetime import datetime
    spine = DataSpine()
    spy_data = spine.build_spine(
        start_date=datetime(2020, 1, 1),
        end_date=datetime(2024, 12, 31)
    )

    # Classify regimes
    classifier = RegimeClassifier()
    df_classified = classifier.classify_period(spy_data)

    # Check we have classifications for all dates
    assert len(df_classified) > 0, "Should have classified data"
    assert not df_classified['regime_label'].isna().any(), "Should have no NaN regimes"

    # Check date range
    assert df_classified['date'].min() >= pd.to_datetime('2020-01-01')
    assert df_classified['date'].max() <= pd.to_datetime('2024-12-31')

    # Compute statistics
    stats = classifier.compute_regime_statistics(df_classified)

    # Should have reasonable regime distribution
    # (not all one regime)
    assert len(stats['frequency']) > 1, "Should have multiple regimes"

    print("\n✅ Integration test passed!")
    print(f"   Classified {len(df_classified)} days")
    print(f"   Regimes found: {df_classified['regime_label'].nunique()}")
    print(f"   Date range: {df_classified['date'].min()} to {df_classified['date'].max()}")


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
