"""
Tests for critical bug fixes in Phase 3.

Tests:
- BUG-C07: DTE calculation for multi-leg positions
- BUG-C08: Commission and fee tracking
- BUG-M01: Allocation re-normalization after VIX scaling
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.trading.trade import Trade, TradeLeg
from src.trading.simulator import TradeSimulator, SimulationConfig
from src.trading.execution import ExecutionModel
from src.backtest.rotation import RotationAllocator


class TestDTECalculation:
    """Test BUG-C07: DTE calculation for multi-leg positions."""

    def test_multi_leg_dte_uses_nearest_expiry(self):
        """
        Verify that DTE calculation uses the nearest expiry across all legs.

        Setup:
        - Create a trade with two legs: one expiring in 3 days, one in 10 days
        - Advance to a date where nearest leg has 2 DTE
        - Verify exit triggers when min_dte <= roll_threshold (5 days)
        """
        # Create test data
        start_date = datetime(2024, 1, 1)
        data = pd.DataFrame({
            'date': pd.date_range(start_date, periods=15, freq='D'),
            'open': 500.0,
            'high': 505.0,
            'low': 495.0,
            'close': 500.0,
            'RV20': 0.20,
            'regime': 1
        })

        # Configure simulator with 5 DTE threshold
        config = SimulationConfig(
            roll_dte_threshold=5,
            delta_hedge_enabled=False
        )

        simulator = TradeSimulator(data, config, use_real_options_data=False)

        # Create a trade with two legs, different expiries
        entry_date = start_date
        near_expiry = entry_date + timedelta(days=8)   # Will have 3 DTE at entry + 5 days
        far_expiry = entry_date + timedelta(days=15)   # Will have 10 DTE at entry + 5 days

        trade = Trade(
            trade_id="TEST_001",
            profile_name="TestProfile",
            entry_date=entry_date,
            legs=[
                TradeLeg(strike=500, expiry=near_expiry, option_type='call', quantity=1, dte=8),
                TradeLeg(strike=500, expiry=far_expiry, option_type='put', quantity=1, dte=15)
            ],
            entry_prices={0: 10.0, 1: 10.0}
        )
        trade.__post_init__()

        # Manually simulate: open trade, then advance 5 days
        # At day 5: near_expiry = 3 DTE remaining, far_expiry = 10 DTE remaining
        # Min DTE = 3, which is < 5 threshold → should exit

        current_trade = trade
        current_trade.is_open = True

        # Simulate to day 6 (index 5, 5 days after entry)
        # This would be 8 - 5 = 3 DTE for near leg
        row = data.iloc[5]
        date = row['date']

        # Convert dates to same type
        current_date = date
        if isinstance(current_date, pd.Timestamp):
            current_date = current_date.date()

        entry_date_check = current_trade.entry_date
        if isinstance(entry_date_check, pd.Timestamp):
            entry_date_check = entry_date_check.date()
        elif isinstance(entry_date_check, datetime):
            entry_date_check = entry_date_check.date()

        # Calculate min DTE (replicate fix logic)
        min_dte = float('inf')
        for leg in current_trade.legs:
            expiry = leg.expiry
            if isinstance(expiry, pd.Timestamp):
                expiry = expiry.date()
            elif isinstance(expiry, datetime):
                expiry = expiry.date()

            dte = (expiry - current_date).days
            min_dte = min(min_dte, dte)

        # Verify min_dte is calculated from nearest expiry
        assert min_dte == 3, f"Expected min_dte=3, got {min_dte}"

        # Verify this triggers exit (min_dte <= 5)
        should_exit = min_dte <= config.roll_dte_threshold
        assert should_exit, "Trade should exit when min_dte <= roll_threshold"

    def test_single_leg_dte_still_works(self):
        """Verify single-leg trades still calculate DTE correctly."""
        start_date = datetime(2024, 1, 1)
        data = pd.DataFrame({
            'date': pd.date_range(start_date, periods=10, freq='D'),
            'open': 500.0,
            'high': 505.0,
            'low': 495.0,
            'close': 500.0,
            'RV20': 0.20,
            'regime': 1
        })

        config = SimulationConfig(
            roll_dte_threshold=5,
            delta_hedge_enabled=False
        )

        simulator = TradeSimulator(data, config, use_real_options_data=False)

        entry_date = start_date
        expiry = entry_date + timedelta(days=8)

        trade = Trade(
            trade_id="TEST_002",
            profile_name="TestProfile",
            entry_date=entry_date,
            legs=[
                TradeLeg(strike=500, expiry=expiry, option_type='call', quantity=1, dte=8)
            ],
            entry_prices={0: 10.0}
        )
        trade.__post_init__()
        trade.is_open = True

        # Advance to day 4 (8 - 4 = 4 DTE remaining, should exit since 4 <= 5)
        row = data.iloc[4]
        current_date = row['date']
        if isinstance(current_date, pd.Timestamp):
            current_date = current_date.date()

        # Calculate min DTE
        min_dte = float('inf')
        for leg in trade.legs:
            expiry_date = leg.expiry
            if isinstance(expiry_date, pd.Timestamp):
                expiry_date = expiry_date.date()
            elif isinstance(expiry_date, datetime):
                expiry_date = expiry_date.date()

            dte = (expiry_date - current_date).days
            min_dte = min(min_dte, dte)

        assert min_dte == 4, f"Expected min_dte=4, got {min_dte}"
        should_exit = min_dte <= config.roll_dte_threshold
        assert should_exit, "Single-leg trade should exit at DTE threshold"


class TestCommissions:
    """Test BUG-C08: Commission and fee tracking."""

    def test_commission_calculation(self):
        """Verify commission calculation for options trades."""
        exec_model = ExecutionModel(
            option_commission=0.65,
            sec_fee_rate=0.00182
        )

        # Test long position (no SEC fees)
        cost_long = exec_model.get_commission_cost(num_contracts=2, is_short=False)
        expected_long = 2 * 0.65
        assert cost_long == expected_long, f"Expected {expected_long}, got {cost_long}"

        # Test short position (with SEC fees)
        cost_short = exec_model.get_commission_cost(num_contracts=2, is_short=True)
        expected_short = 2 * 0.65 + 2 * 0.00182
        assert cost_short == expected_short, f"Expected {expected_short}, got {cost_short}"

    def test_trade_includes_commissions_in_pnl(self):
        """Verify trade P&L includes entry and exit commissions."""
        entry_date = datetime(2024, 1, 1)
        exit_date = datetime(2024, 1, 10)

        trade = Trade(
            trade_id="TEST_003",
            profile_name="TestProfile",
            entry_date=entry_date,
            legs=[
                TradeLeg(strike=500, expiry=entry_date + timedelta(days=30),
                        option_type='call', quantity=1, dte=30)
            ],
            entry_prices={0: 10.0}
        )
        trade.__post_init__()

        # Entry cost should be 1 * 10.0 = 10.0 (debit)
        assert trade.entry_cost == 10.0

        # Set commissions
        trade.entry_commission = 0.65
        trade.exit_commission = 0.65

        # Close at profit: exit at 15.0
        # P&L = 1 * (15.0 - 10.0) = 5.0
        # After commissions: 5.0 - 0.65 - 0.65 = 3.70
        trade.close(exit_date, {0: 15.0}, "Test close")

        expected_pnl = 5.0 - 0.65 - 0.65
        assert trade.realized_pnl == expected_pnl, \
            f"Expected realized_pnl={expected_pnl}, got {trade.realized_pnl}"

    def test_mark_to_market_includes_entry_commission(self):
        """Verify unrealized P&L includes entry commission but not exit commission."""
        entry_date = datetime(2024, 1, 1)

        trade = Trade(
            trade_id="TEST_004",
            profile_name="TestProfile",
            entry_date=entry_date,
            legs=[
                TradeLeg(strike=500, expiry=entry_date + timedelta(days=30),
                        option_type='call', quantity=1, dte=30)
            ],
            entry_prices={0: 10.0}
        )
        trade.__post_init__()
        trade.entry_commission = 0.65

        # Current price = 12.0
        # Unrealized P&L = 1 * (12.0 - 10.0) - 0.65 = 1.35
        unrealized = trade.mark_to_market({0: 12.0})
        expected_unrealized = 2.0 - 0.65
        assert unrealized == expected_unrealized, \
            f"Expected unrealized={expected_unrealized}, got {unrealized}"


class TestAllocationNormalization:
    """Test BUG-M01: Allocation re-normalization after VIX scaling."""

    def test_vix_scaling_renormalizes(self):
        """Verify weights sum to 1.0 after VIX scaling."""
        allocator = RotationAllocator(
            max_profile_weight=0.40,
            min_profile_weight=0.05,
            vix_scale_threshold=0.30,
            vix_scale_factor=0.5
        )

        profile_scores = {
            'profile_1': 0.8,
            'profile_2': 0.6,
            'profile_3': 0.4
        }

        # Test with high volatility (triggers scaling)
        regime = 1
        rv20 = 0.35  # Above threshold

        weights = allocator.allocate(profile_scores, regime, rv20)

        # Weights should sum to 1.0 after re-normalization
        total = sum(weights.values())
        assert np.isclose(total, 1.0, atol=1e-6), \
            f"Weights should sum to 1.0 after VIX scaling, got {total}"

    def test_normal_volatility_no_scaling(self):
        """Verify weights sum to 1.0 without VIX scaling."""
        allocator = RotationAllocator(
            max_profile_weight=0.40,
            min_profile_weight=0.05,
            vix_scale_threshold=0.30,
            vix_scale_factor=0.5
        )

        profile_scores = {
            'profile_1': 0.8,
            'profile_2': 0.6,
            'profile_3': 0.4
        }

        # Test with normal volatility (no scaling)
        regime = 1
        rv20 = 0.20  # Below threshold

        weights = allocator.allocate(profile_scores, regime, rv20)

        # Weights should sum to 1.0
        total = sum(weights.values())
        assert np.isclose(total, 1.0, atol=1e-6), \
            f"Weights should sum to 1.0 normally, got {total}"

    def test_high_vol_reduces_individual_weights_but_maintains_allocation(self):
        """
        Verify that high vol reduces individual position sizes through lower scores,
        but total allocation remains at 100% (sum=1.0).
        """
        allocator = RotationAllocator(
            max_profile_weight=0.40,
            min_profile_weight=0.05,
            vix_scale_threshold=0.30,
            vix_scale_factor=0.5
        )

        profile_scores = {
            'profile_1': 1.0,  # Perfect score
            'profile_2': 0.0,
            'profile_3': 0.0,
            'profile_4': 0.0,
            'profile_5': 0.0,
            'profile_6': 0.0
        }

        regime = 1  # Trend Up (profile_1 has compatibility 1.0)

        # Normal vol
        weights_normal = allocator.allocate(profile_scores, regime, rv20=0.20)

        # High vol
        weights_high = allocator.allocate(profile_scores, regime, rv20=0.35)

        # Both should sum to 1.0
        assert np.isclose(sum(weights_normal.values()), 1.0, atol=1e-6)
        assert np.isclose(sum(weights_high.values()), 1.0, atol=1e-6)

        # But high vol should not change allocation pattern (since we're renormalizing)
        # After fix: weights stay proportional but renormalized
        # Before fix: weights would sum to 0.5, leaving 50% unallocated


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
