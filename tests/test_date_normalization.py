"""
Test date normalization utility.

Verifies that the centralized normalize_date function handles all
common date types correctly.
"""

import pytest
import pandas as pd
from datetime import date, datetime
import sys
import os

# Add src to path for imports (avoid circular dependency with __init__.py)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import directly from the module file to avoid circular import
import importlib.util
spec = importlib.util.spec_from_file_location(
    "utils",
    os.path.join(os.path.dirname(__file__), '..', 'src', 'trading', 'utils.py')
)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)
normalize_date = utils.normalize_date


class TestDateNormalization:
    """Test suite for normalize_date utility function."""

    def test_normalize_date_from_date(self):
        """Test normalizing from datetime.date."""
        input_date = date(2023, 6, 15)
        result = normalize_date(input_date)

        assert result == date(2023, 6, 15)
        assert isinstance(result, date)
        assert not isinstance(result, datetime)

    def test_normalize_date_from_datetime(self):
        """Test normalizing from datetime.datetime."""
        input_dt = datetime(2023, 6, 15, 14, 30, 45)
        result = normalize_date(input_dt)

        assert result == date(2023, 6, 15)
        assert isinstance(result, date)
        assert not isinstance(result, datetime)

    def test_normalize_date_from_pd_timestamp(self):
        """Test normalizing from pd.Timestamp."""
        input_ts = pd.Timestamp('2023-06-15 14:30:45')
        result = normalize_date(input_ts)

        assert result == date(2023, 6, 15)
        assert isinstance(result, date)
        assert not isinstance(result, datetime)

    def test_normalize_date_from_string(self):
        """Test normalizing from string."""
        input_str = '2023-06-15'
        result = normalize_date(input_str)

        assert result == date(2023, 6, 15)
        assert isinstance(result, date)

    def test_normalize_date_from_string_with_time(self):
        """Test normalizing from string with time component."""
        input_str = '2023-06-15 14:30:45'
        result = normalize_date(input_str)

        assert result == date(2023, 6, 15)
        assert isinstance(result, date)

    def test_normalize_date_idempotent(self):
        """Test that normalizing an already-normalized date returns same value."""
        input_date = date(2023, 6, 15)
        result1 = normalize_date(input_date)
        result2 = normalize_date(result1)

        assert result1 == result2
        assert result1 is input_date  # Should be same object

    def test_normalize_date_invalid_type(self):
        """Test that invalid types raise TypeError."""
        with pytest.raises(TypeError, match="Cannot convert"):
            normalize_date(12345)

        with pytest.raises(TypeError, match="Cannot convert"):
            normalize_date([2023, 6, 15])

        with pytest.raises(TypeError, match="Cannot convert"):
            normalize_date(None)

    def test_normalize_date_consistency(self):
        """Test that different representations of same date normalize to same value."""
        same_date = date(2023, 6, 15)

        results = [
            normalize_date(date(2023, 6, 15)),
            normalize_date(datetime(2023, 6, 15)),
            normalize_date(datetime(2023, 6, 15, 10, 30)),
            normalize_date(pd.Timestamp('2023-06-15')),
            normalize_date(pd.Timestamp('2023-06-15 10:30:00')),
            normalize_date('2023-06-15'),
            normalize_date('2023-06-15 10:30:00'),
        ]

        # All should be equal
        for result in results:
            assert result == same_date
            assert isinstance(result, date)
            assert not isinstance(result, datetime)


class TestDateNormalizationInSimulator:
    """Test that date normalization integrates correctly with simulator."""

    def test_mixed_date_types_in_comparison(self):
        """Test that date comparisons work regardless of input type."""
        # Simulate what happens in simulator code
        current_date_ts = pd.Timestamp('2023-06-20')
        entry_date_dt = datetime(2023, 6, 15, 10, 30)

        # Before fix: Would need explicit conversions
        # After fix: Just normalize
        current = normalize_date(current_date_ts)
        entry = normalize_date(entry_date_dt)

        days_diff = (current - entry).days
        assert days_diff == 5

    def test_expiry_dte_calculation(self):
        """Test DTE calculation using normalized dates."""
        current_date = pd.Timestamp('2023-06-15')
        expiry = datetime(2023, 7, 21)  # Different type

        current_normalized = normalize_date(current_date)
        expiry_normalized = normalize_date(expiry)

        dte = (expiry_normalized - current_normalized).days
        assert dte == 36  # June 15 to July 21

    def test_date_normalization_preserves_ordering(self):
        """Test that date ordering is preserved after normalization."""
        dates = [
            pd.Timestamp('2023-06-10'),
            datetime(2023, 6, 15),
            date(2023, 6, 20),
            '2023-06-25',
        ]

        normalized = [normalize_date(d) for d in dates]

        # Check ordering preserved
        assert normalized[0] < normalized[1] < normalized[2] < normalized[3]

        # Check all are date type
        for norm_date in normalized:
            assert isinstance(norm_date, date)
            assert not isinstance(norm_date, datetime)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
