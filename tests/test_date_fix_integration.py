"""
Integration test for BUG-TIER3-001: Date Type Inconsistency fix.

Verifies that date normalization works correctly in simulator context,
eliminating the need for scattered date type conversions.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta

# Direct imports to avoid circular dependency
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from trading.simulator import TradeSimulator, SimulationConfig
from trading.trade import Trade, TradeLeg
from trading.execution import ExecutionModel


def create_test_data(start_date, days=10):
    """Create minimal test data with various date types."""
    dates = pd.date_range(start=start_date, periods=days, freq='D')

    return pd.DataFrame({
        'date': dates,  # pd.Timestamp type
        'open': 420.0,
        'high': 425.0,
        'low': 415.0,
        'close': np.linspace(420, 440, days),  # Small upward trend
        'volume': 1000000,
        'RV20': 0.15,
        'regime': 0
    })


class TestDateNormalizationIntegration:
    """Test date normalization in simulator."""

    def test_mixed_date_types_in_simulator(self):
        """
        Test that simulator handles mixed date types correctly.

        Before fix: Would have scattered if/elif conversions and potential failures
        After fix: normalize_date() handles all conversions at entry points
        """
        # Create data with pd.Timestamp dates
        start_date = datetime(2024, 1, 1)
        data = create_test_data(start_date, days=10)

        # Verify data has pd.Timestamp type
        assert isinstance(data['date'].iloc[0], pd.Timestamp)

        # Create simulator with toy pricing enabled
        config = SimulationConfig(
            delta_hedge_enabled=False,
            roll_dte_threshold=1,
            max_days_in_trade=30,
            allow_toy_pricing=True  # Enable fallback pricing
        )

        simulator = TradeSimulator(
            data=data,
            config=config,
            use_real_options_data=False
        )

        # Entry logic: Enter once
        entry_executed = [False]
        def entry_logic(row, current_trade):
            if not entry_executed[0] and current_trade is None:
                entry_executed[0] = True
                return True
            return False

        # Trade constructor with datetime.date for expiry (different type)
        def trade_constructor(row, trade_id):
            spot = row['close']
            strike = 420.0

            # Use datetime for entry_date (different from pd.Timestamp in data)
            entry_date = datetime(2024, 1, 1)

            # Use date for expiry (yet another type)
            expiry = date(2024, 1, 31)

            legs = [
                TradeLeg(strike=strike, expiry=expiry, option_type='call', quantity=1, dte=30)
            ]

            return Trade(
                trade_id=trade_id,
                profile_name="Test",
                entry_date=entry_date,
                legs=legs,
                entry_prices={}
            )

        # Should not raise errors due to date type mismatches
        results = simulator.simulate(
            entry_logic=entry_logic,
            trade_constructor=trade_constructor,
            profile_name="DateTest"
        )

        # Verify results exist
        assert len(results) == 10
        assert 'date' in results.columns
        assert 'total_pnl' in results.columns

    def test_dte_calculation_with_mixed_types(self):
        """
        Test DTE calculation works with mixed date types.

        This was a common source of scattered conversions.
        """
        start_date = datetime(2024, 1, 1)
        data = create_test_data(start_date, days=10)

        config = SimulationConfig(
            delta_hedge_enabled=False,
            roll_dte_threshold=2,  # Roll at 2 DTE
            max_days_in_trade=30,
            allow_toy_pricing=True
        )

        simulator = TradeSimulator(
            data=data,
            config=config,
            use_real_options_data=False
        )

        entry_executed = [False]
        def entry_logic(row, current_trade):
            if not entry_executed[0] and current_trade is None:
                entry_executed[0] = True
                return True
            return False

        def trade_constructor(row, trade_id):
            # Create short-dated trade that will hit roll threshold
            spot = row['close']
            entry_date = row['date']
            expiry = entry_date + timedelta(days=5)

            legs = [
                TradeLeg(strike=420.0, expiry=expiry, option_type='call', quantity=1, dte=5)
            ]

            return Trade(
                trade_id=trade_id,
                profile_name="Test",
                entry_date=entry_date,
                legs=legs,
                entry_prices={}
            )

        # Should handle DTE calculation correctly and exit at threshold
        results = simulator.simulate(
            entry_logic=entry_logic,
            trade_constructor=trade_constructor,
            profile_name="DTETest"
        )

        # Should have exited before end of backtest (due to DTE threshold)
        assert len(results) == 10

        # Check that trade was closed
        trades = simulator.get_trade_summary()
        assert len(trades) == 1
        assert trades.iloc[0]['exit_reason'] in ["DTE threshold (1 DTE)", "DTE threshold (2 DTE)"]

    def test_days_in_trade_calculation(self):
        """
        Test that days_in_trade calculation works with mixed date types.

        This appeared in multiple places in the old code.
        """
        start_date = datetime(2024, 1, 1)
        data = create_test_data(start_date, days=10)

        config = SimulationConfig(
            delta_hedge_enabled=False,
            max_days_in_trade=5,  # Force exit after 5 days
            allow_toy_pricing=True
        )

        simulator = TradeSimulator(
            data=data,
            config=config,
            use_real_options_data=False
        )

        entry_executed = [False]
        def entry_logic(row, current_trade):
            if not entry_executed[0] and current_trade is None:
                entry_executed[0] = True
                return True
            return False

        def trade_constructor(row, trade_id):
            spot = row['close']
            entry_date = row['date']
            expiry = entry_date + timedelta(days=30)

            legs = [
                TradeLeg(strike=420.0, expiry=expiry, option_type='call', quantity=1, dte=30)
            ]

            return Trade(
                trade_id=trade_id,
                profile_name="Test",
                entry_date=entry_date,
                legs=legs,
                entry_prices={}
            )

        results = simulator.simulate(
            entry_logic=entry_logic,
            trade_constructor=trade_constructor,
            profile_name="MaxDaysTest"
        )

        # Verify trade exited after max days
        trades = simulator.get_trade_summary()
        assert len(trades) == 1

        # Should exit at or before max_days_in_trade
        days_held = trades.iloc[0]['days_held']
        assert days_held <= 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
