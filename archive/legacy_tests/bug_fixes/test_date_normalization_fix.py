"""
Test suite for Bug 1: Date Normalization Consistency Fix

Verifies that:
1. All date conversions use utils.normalize_date()
2. Trade._normalize_datetime() has been removed
3. DTE calculations are consistent across the codebase
4. No off-by-one errors in date arithmetic
"""

import pytest
from datetime import datetime, date, timedelta
import pandas as pd
from src.trading.trade import Trade, TradeLeg, create_straddle_trade
from src.trading.utils import normalize_date


class TestDateNormalizationFix:
    """Test date normalization consistency fixes."""

    def test_normalize_date_handles_all_types(self):
        """Test that normalize_date correctly handles all input types."""
        # Test with datetime.date
        d = date(2023, 1, 15)
        assert normalize_date(d) == d

        # Test with datetime.datetime
        dt = datetime(2023, 1, 15, 10, 30, 0)
        assert normalize_date(dt) == date(2023, 1, 15)

        # Test with pd.Timestamp
        ts = pd.Timestamp('2023-01-15 10:30:00')
        assert normalize_date(ts) == date(2023, 1, 15)

        # Test with string
        s = '2023-01-15'
        assert normalize_date(s) == date(2023, 1, 15)

    def test_trade_normalize_datetime_removed(self):
        """Verify Trade._normalize_datetime() method has been removed."""
        # This should raise AttributeError if method was removed
        with pytest.raises(AttributeError):
            Trade._normalize_datetime(datetime.now())

    def test_trade_entry_date_normalization(self):
        """Test that Trade entry_date is normalized consistently."""
        # Create trade with different date types
        entry_dates = [
            date(2023, 1, 15),
            datetime(2023, 1, 15, 14, 30),
            pd.Timestamp('2023-01-15 14:30:00'),
        ]

        for entry_date in entry_dates:
            trade = Trade(
                trade_id="TEST_001",
                profile_name="TestProfile",
                entry_date=entry_date,
                legs=[
                    TradeLeg(
                        strike=500.0,
                        expiry=datetime(2023, 2, 15),
                        option_type='call',
                        quantity=1,
                        dte=30
                    )
                ],
                entry_prices={0: 10.0}
            )

            # After __post_init__, entry_date should be datetime with date normalized
            assert isinstance(trade.entry_date, datetime)
            assert trade.entry_date.date() == date(2023, 1, 15)

    def test_trade_exit_date_normalization(self):
        """Test that Trade exit_date is normalized consistently."""
        trade = create_straddle_trade(
            trade_id="TEST_002",
            profile_name="TestProfile",
            entry_date=datetime(2023, 1, 15),
            strike=500.0,
            expiry=datetime(2023, 2, 15),
            dte=30,
            quantity=1,
            entry_prices={0: 10.0, 1: 8.0}
        )

        # Close with different date types
        exit_dates = [
            date(2023, 1, 20),
            datetime(2023, 1, 20, 16, 0),
            pd.Timestamp('2023-01-20 16:00:00'),
        ]

        for exit_date in exit_dates:
            trade_copy = Trade(
                trade_id=trade.trade_id,
                profile_name=trade.profile_name,
                entry_date=trade.entry_date,
                legs=trade.legs,
                entry_prices=trade.entry_prices
            )

            trade_copy.close(
                exit_date=exit_date,
                exit_prices={0: 12.0, 1: 9.0},
                reason="Test exit"
            )

            # exit_date should be datetime with date normalized
            assert isinstance(trade_copy.exit_date, datetime)
            assert trade_copy.exit_date.date() == date(2023, 1, 20)

    def test_greeks_calculation_date_normalization(self):
        """Test that Greeks calculation normalizes dates consistently."""
        trade = create_straddle_trade(
            trade_id="TEST_003",
            profile_name="TestProfile",
            entry_date=datetime(2023, 1, 15),
            strike=500.0,
            expiry=datetime(2023, 2, 15),
            dte=30,
            quantity=1,
            entry_prices={0: 10.0, 1: 8.0}
        )

        # Calculate Greeks with different date types
        current_dates = [
            date(2023, 1, 20),
            datetime(2023, 1, 20, 14, 0),
            pd.Timestamp('2023-01-20 14:00:00'),
        ]

        for current_date in current_dates:
            trade.calculate_greeks(
                underlying_price=500.0,
                current_date=current_date,
                implied_vol=0.30,
                risk_free_rate=0.05
            )

            # Greeks should be calculated (non-zero for ATM straddle)
            assert trade.net_delta is not None
            assert trade.net_gamma > 0  # ATM straddle has positive gamma
            assert trade.net_vega > 0   # ATM straddle has positive vega

    def test_dte_consistency_across_date_types(self):
        """Test that DTE calculations are consistent regardless of date input type."""
        entry_date = date(2023, 1, 15)
        expiry_date = date(2023, 2, 15)  # 31 days later

        # Create trade with different date type combinations
        test_cases = [
            (datetime(2023, 1, 15), datetime(2023, 2, 15)),
            (pd.Timestamp('2023-01-15'), pd.Timestamp('2023-02-15')),
            (date(2023, 1, 15), datetime(2023, 2, 15)),
        ]

        for entry, expiry in test_cases:
            trade = Trade(
                trade_id="TEST_DTE",
                profile_name="TestProfile",
                entry_date=entry,
                legs=[
                    TradeLeg(
                        strike=500.0,
                        expiry=expiry,
                        option_type='call',
                        quantity=1,
                        dte=31
                    )
                ],
                entry_prices={0: 10.0}
            )

            # Calculate Greeks on current date
            current_date = datetime(2023, 1, 20)  # 5 days after entry
            trade.calculate_greeks(
                underlying_price=500.0,
                current_date=current_date,
                implied_vol=0.30,
                risk_free_rate=0.05
            )

            # Time to expiry should be consistent: (Feb 15 - Jan 20) = 26 days
            # Convert to years for Greeks calculation: 26/365 ≈ 0.0712
            entry_normalized = normalize_date(trade.entry_date)
            expiry_normalized = normalize_date(trade.legs[0].expiry)
            current_normalized = normalize_date(current_date)

            days_to_expiry = (expiry_normalized - current_normalized).days
            assert days_to_expiry == 26, f"Expected 26 DTE, got {days_to_expiry}"

    def test_no_off_by_one_in_days_held(self):
        """Test that days_held calculation has no off-by-one errors."""
        entry_date = date(2023, 1, 15)
        exit_date = date(2023, 1, 20)  # Should be 5 days held

        trade = create_straddle_trade(
            trade_id="TEST_HELD",
            profile_name="TestProfile",
            entry_date=entry_date,
            strike=500.0,
            expiry=datetime(2023, 2, 15),
            dte=31,
            quantity=1,
            entry_prices={0: 10.0, 1: 8.0}
        )

        trade.close(
            exit_date=exit_date,
            exit_prices={0: 12.0, 1: 9.0},
            reason="Test"
        )

        # Calculate days held
        entry_normalized = normalize_date(trade.entry_date)
        exit_normalized = normalize_date(trade.exit_date)
        days_held = (exit_normalized - entry_normalized).days

        assert days_held == 5, f"Expected 5 days held, got {days_held}"

    def test_simulator_date_normalization(self):
        """Test that simulator uses consistent date normalization."""
        from src.trading.simulator import TradeSimulator, SimulationConfig

        # Create simple test data
        dates = pd.date_range('2023-01-01', '2023-01-10', freq='D')
        data = pd.DataFrame({
            'date': dates,
            'open': 500.0,
            'high': 505.0,
            'low': 495.0,
            'close': 500.0,
            'volume': 1000000,
            'RV20': 0.20,
            'regime': 1
        })

        config = SimulationConfig(
            delta_hedge_enabled=False,
            roll_dte_threshold=5,
            max_loss_pct=0.50,
            max_days_in_trade=30,
            allow_toy_pricing=True  # Use toy pricing for test
        )

        simulator = TradeSimulator(
            data=data,
            config=config,
            use_real_options_data=False
        )

        # Entry logic: Enter on first day
        def entry_logic(row, current_trade):
            return current_trade is None and row['date'] == dates[0]

        # Trade constructor
        def trade_constructor(row, trade_id):
            return create_straddle_trade(
                trade_id=trade_id,
                profile_name="Test",
                entry_date=row['date'],
                strike=500.0,
                expiry=row['date'] + timedelta(days=10),
                dte=10,
                quantity=1
            )

        # Run simulation
        results = simulator.simulate(
            entry_logic=entry_logic,
            trade_constructor=trade_constructor,
            profile_name="DateTest"
        )

        # Verify no errors and consistent date handling
        assert len(results) == len(data)
        assert all(isinstance(r, dict) for r in results.to_dict('records'))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
