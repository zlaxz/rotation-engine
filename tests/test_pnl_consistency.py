"""
P&L consistency tests - validates single source of truth.

These tests are CRITICAL for ensuring backtest results are reliable.
Any failure here indicates a fundamental accounting error that could
lead to incorrect strategy evaluation.

Tests:
1. Position-based P&L matches equity changes
2. Cash flow conservation (no money created/destroyed)
3. Entry/exit price accounting
4. Commission and cost accounting
5. Multi-position P&L aggregation
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from src.backtest.portfolio_new import Portfolio
from src.backtest.position import Position
from src.trading.trade import Trade, TradeLeg


class TestCashFlowConservation:
    """Test that cash is conserved (no money created/destroyed)."""

    def test_cash_flow_matches_position_values(self):
        """Cash out + position values = initial capital + P&L."""
        portfolio = Portfolio(initial_capital=1_000_000.0)

        # Create trade
        entry_date = date(2024, 1, 2)
        expiry = datetime(2024, 3, 15)

        legs = [
            TradeLeg('call', 500.0, expiry, 1, 45),
            TradeLeg('put', 500.0, expiry, 1, 45)
        ]

        trade = Trade(
            trade_id="TEST_001",
            profile_name="test_profile",
            entry_date=entry_date,
            legs=legs,
            entry_prices={0: 15.0, 1: 14.0}
        )
        trade.__post_init__()

        initial_cash = portfolio.cash

        # Open position (20% allocation)
        portfolio.open_position(
            profile_id=1,
            trade=trade,
            allocation_pct=0.20,
            entry_date=entry_date
        )

        # Cash should decrease by entry cost
        expected_cash = initial_cash - abs(trade.entry_cost)
        assert abs(portfolio.cash - expected_cash) < 0.01

        # Total value should equal initial capital (no P&L yet)
        total_value = portfolio.cash + portfolio.positions[1].current_value
        assert abs(total_value - portfolio.initial_capital) < 0.01

    def test_cash_flow_after_close(self):
        """Cash flow is conserved after closing position."""
        portfolio = Portfolio(initial_capital=1_000_000.0)

        entry_date = date(2024, 1, 2)
        exit_date = date(2024, 1, 10)
        expiry = datetime(2024, 3, 15)

        legs = [
            TradeLeg('call', 500.0, expiry, 1, 45),
            TradeLeg('put', 500.0, expiry, 1, 45)
        ]

        trade = Trade(
            trade_id="TEST_001",
            profile_name="test_profile",
            entry_date=entry_date,
            legs=legs,
            entry_prices={0: 15.0, 1: 14.0}
        )
        trade.__post_init__()

        # Open position
        portfolio.open_position(
            profile_id=1,
            trade=trade,
            allocation_pct=0.20,
            entry_date=entry_date
        )

        cash_after_open = portfolio.cash

        # Close position with profit
        exit_prices = {0: 18.0, 1: 17.0}
        realized_pnl = portfolio.close_position(
            profile_id=1,
            exit_prices=exit_prices,
            exit_date=exit_date,
            exit_reason="Test"
        )

        # Cash should increase by exit proceeds
        expected_cash = cash_after_open + trade.exit_proceeds
        assert abs(portfolio.cash - expected_cash) < 0.01

        # Final equity should equal initial capital + realized P&L
        final_equity = portfolio.get_equity()
        expected_equity = portfolio.initial_capital + realized_pnl
        assert abs(final_equity - expected_equity) < 0.01


class TestPositionPnLAccuracy:
    """Test that position P&L calculations are accurate."""

    def test_position_pnl_from_price_changes(self):
        """Position P&L accurately reflects option price changes."""
        portfolio = Portfolio(initial_capital=1_000_000.0)

        entry_date = date(2024, 1, 2)
        expiry = datetime(2024, 3, 15)

        legs = [
            TradeLeg('call', 500.0, expiry, 1, 45),
            TradeLeg('put', 500.0, expiry, 1, 45)
        ]

        trade = Trade(
            trade_id="TEST_001",
            profile_name="test_profile",
            entry_date=entry_date,
            legs=legs,
            entry_prices={0: 15.0, 1: 14.0}
        )
        trade.__post_init__()

        # Entry cost = -(call_price + put_price) * 100
        expected_entry_cost = -(15.0 + 14.0) * 100
        assert abs(trade.entry_cost - expected_entry_cost) < 0.01

        # Open position
        portfolio.open_position(
            profile_id=1,
            trade=trade,
            allocation_pct=0.20,
            entry_date=entry_date
        )

        # Mark to market with new prices
        new_prices = {0: 18.0, 1: 17.0}  # Both increased by 3.0
        portfolio.mark_to_market(
            current_date=date(2024, 1, 3),
            option_prices_by_profile={1: new_prices}
        )

        # Expected P&L = (new_call - old_call + new_put - old_put) * 100
        expected_pnl = ((18.0 - 15.0) + (17.0 - 14.0)) * 100
        actual_pnl = portfolio.positions[1].unrealized_pnl

        assert abs(actual_pnl - expected_pnl) < 0.01

    def test_losing_position_pnl(self):
        """Losing position P&L is correctly negative."""
        portfolio = Portfolio(initial_capital=1_000_000.0)

        entry_date = date(2024, 1, 2)
        expiry = datetime(2024, 3, 15)

        legs = [
            TradeLeg('call', 500.0, expiry, 1, 45),
            TradeLeg('put', 500.0, expiry, 1, 45)
        ]

        trade = Trade(
            trade_id="TEST_001",
            profile_name="test_profile",
            entry_date=entry_date,
            legs=legs,
            entry_prices={0: 15.0, 1: 14.0}
        )
        trade.__post_init__()

        portfolio.open_position(
            profile_id=1,
            trade=trade,
            allocation_pct=0.20,
            entry_date=entry_date
        )

        # Mark to market with lower prices (loss)
        new_prices = {0: 12.0, 1: 11.0}
        portfolio.mark_to_market(
            current_date=date(2024, 1, 3),
            option_prices_by_profile={1: new_prices}
        )

        # Expected loss
        expected_pnl = ((12.0 - 15.0) + (11.0 - 14.0)) * 100
        actual_pnl = portfolio.positions[1].unrealized_pnl

        assert actual_pnl < 0  # Should be negative
        assert abs(actual_pnl - expected_pnl) < 0.01


class TestMultiPositionPnLAggregation:
    """Test P&L aggregation across multiple positions."""

    def test_total_pnl_sum_of_positions(self):
        """Total portfolio P&L = sum of individual position P&Ls."""
        portfolio = Portfolio(initial_capital=1_000_000.0)

        entry_date = date(2024, 1, 2)
        expiry = datetime(2024, 3, 15)

        # Open 3 positions
        for profile_id in [1, 2, 3]:
            legs = [
                TradeLeg('call', 500.0, expiry, 1, 45),
                TradeLeg('put', 500.0, expiry, 1, 45)
            ]

            trade = Trade(
                trade_id=f"TEST_{profile_id}",
                profile_name=f"test_profile_{profile_id}",
                entry_date=entry_date,
                legs=legs,
                entry_prices={0: 15.0, 1: 14.0}
            )
            trade.__post_init__()

            portfolio.open_position(
                profile_id=profile_id,
                trade=trade,
                allocation_pct=0.15,
                entry_date=entry_date
            )

        # Mark to market with different prices for each position
        prices = {
            1: {0: 18.0, 1: 17.0},  # Profit
            2: {0: 14.0, 1: 13.0},  # Loss
            3: {0: 16.0, 1: 15.0}   # Small profit
        }

        portfolio.mark_to_market(
            current_date=date(2024, 1, 3),
            option_prices_by_profile=prices
        )

        # Calculate expected total P&L
        expected_total = 0.0
        for profile_id in [1, 2, 3]:
            expected_total += portfolio.positions[profile_id].unrealized_pnl

        actual_total = portfolio.get_unrealized_pnl()

        assert abs(actual_total - expected_total) < 0.01

    def test_mixed_realized_unrealized_pnl(self):
        """Total P&L correctly combines realized and unrealized."""
        portfolio = Portfolio(initial_capital=1_000_000.0)

        entry_date = date(2024, 1, 2)
        exit_date = date(2024, 1, 10)
        expiry = datetime(2024, 3, 15)

        # Open 2 positions
        for profile_id in [1, 2]:
            legs = [
                TradeLeg('call', 500.0, expiry, 1, 45),
                TradeLeg('put', 500.0, expiry, 1, 45)
            ]

            trade = Trade(
                trade_id=f"TEST_{profile_id}",
                profile_name=f"test_profile_{profile_id}",
                entry_date=entry_date,
                legs=legs,
                entry_prices={0: 15.0, 1: 14.0}
            )
            trade.__post_init__()

            portfolio.open_position(
                profile_id=profile_id,
                trade=trade,
                allocation_pct=0.20,
                entry_date=entry_date
            )

        # Close first position (realized P&L)
        exit_prices = {0: 18.0, 1: 17.0}
        realized_pnl = portfolio.close_position(
            profile_id=1,
            exit_prices=exit_prices,
            exit_date=exit_date,
            exit_reason="Test"
        )

        # Mark second position (unrealized P&L)
        current_prices = {2: {0: 16.0, 1: 15.0}}
        portfolio.mark_to_market(
            current_date=exit_date,
            option_prices_by_profile=current_prices
        )

        # Total P&L should equal sum
        expected_total = realized_pnl + portfolio.positions[2].unrealized_pnl
        actual_total = portfolio.get_total_pnl()

        assert abs(actual_total - expected_total) < 0.01


class TestEquityConsistency:
    """Test equity calculation consistency."""

    def test_equity_matches_pnl(self):
        """Equity change matches cumulative P&L."""
        portfolio = Portfolio(initial_capital=1_000_000.0)

        entry_date = date(2024, 1, 2)
        expiry = datetime(2024, 3, 15)

        legs = [
            TradeLeg('call', 500.0, expiry, 1, 45),
            TradeLeg('put', 500.0, expiry, 1, 45)
        ]

        trade = Trade(
            trade_id="TEST_001",
            profile_name="test_profile",
            entry_date=entry_date,
            legs=legs,
            entry_prices={0: 15.0, 1: 14.0}
        )
        trade.__post_init__()

        # Open position
        portfolio.open_position(
            profile_id=1,
            trade=trade,
            allocation_pct=0.20,
            entry_date=entry_date
        )

        # Mark to market for 5 days
        for day in range(1, 6):
            prices = {1: {0: 15.0 + day * 0.5, 1: 14.0 + day * 0.5}}
            portfolio.mark_to_market(
                current_date=date(2024, 1, 2 + day),
                option_prices_by_profile=prices
            )

        # Final equity should equal initial capital + total P&L
        final_equity = portfolio.get_equity()
        total_pnl = portfolio.get_total_pnl()
        expected_equity = portfolio.initial_capital + total_pnl

        assert abs(final_equity - expected_equity) < 0.01

    def test_equity_curve_consistency(self):
        """Equity curve shows consistent values."""
        portfolio = Portfolio(initial_capital=1_000_000.0)

        entry_date = date(2024, 1, 2)
        expiry = datetime(2024, 3, 15)

        legs = [
            TradeLeg('call', 500.0, expiry, 1, 45),
            TradeLeg('put', 500.0, expiry, 1, 45)
        ]

        trade = Trade(
            trade_id="TEST_001",
            profile_name="test_profile",
            entry_date=entry_date,
            legs=legs,
            entry_prices={0: 15.0, 1: 14.0}
        )
        trade.__post_init__()

        portfolio.open_position(
            profile_id=1,
            trade=trade,
            allocation_pct=0.20,
            entry_date=entry_date
        )

        # Mark to market multiple days
        for day in range(1, 6):
            prices = {1: {0: 15.0 + day, 1: 14.0 + day}}
            portfolio.mark_to_market(
                current_date=date(2024, 1, 2 + day),
                option_prices_by_profile=prices
            )

        equity_curve = portfolio.get_equity_curve()

        # Each row should satisfy: total_equity = cash + position_value
        for _, row in equity_curve.iterrows():
            expected = row['cash'] + row['position_value']
            actual = row['total_equity']
            assert abs(actual - expected) < 0.01


class TestCommissionAccounting:
    """Test that commissions are accounted for correctly."""

    def test_entry_commission_reduces_pnl(self):
        """Entry commissions reduce position P&L."""
        portfolio = Portfolio(initial_capital=1_000_000.0)

        entry_date = date(2024, 1, 2)
        exit_date = date(2024, 1, 10)
        expiry = datetime(2024, 3, 15)

        legs = [
            TradeLeg('call', 500.0, expiry, 1, 45),
            TradeLeg('put', 500.0, expiry, 1, 45)
        ]

        trade = Trade("TEST_001", legs, entry_date)
        trade.entry_prices = {0: 15.0, 1: 14.0}
        trade.entry_commission = 5.0  # $5 commission
        trade.__post_init__()

        portfolio.open_position(
            profile_id=1,
            trade=trade,
            allocation_pct=0.20,
            entry_date=entry_date
        )

        # Close at same prices (should lose commission)
        exit_prices = {0: 15.0, 1: 14.0}
        trade.exit_commission = 5.0

        realized_pnl = portfolio.close_position(
            profile_id=1,
            exit_prices=exit_prices,
            exit_date=exit_date,
            exit_reason="Test"
        )

        # With no price change, P&L should be -(entry_commission + exit_commission)
        expected_pnl = -(5.0 + 5.0)
        assert abs(realized_pnl - expected_pnl) < 0.01


class TestEdgeCases:
    """Test edge cases in P&L calculation."""

    def test_zero_allocation_position(self):
        """Position with zero allocation handles correctly."""
        portfolio = Portfolio(initial_capital=1_000_000.0)

        # This should not occur in practice but test boundary
        entry_date = date(2024, 1, 2)
        expiry = datetime(2024, 3, 15)

        legs = [
            TradeLeg('call', 500.0, expiry, 1, 45),
            TradeLeg('put', 500.0, expiry, 1, 45)
        ]

        trade = Trade(
            trade_id="TEST_001",
            profile_name="test_profile",
            entry_date=entry_date,
            legs=legs,
            entry_prices={0: 15.0, 1: 14.0}
        )
        trade.__post_init__()

        # Very small allocation
        portfolio.open_position(
            profile_id=1,
            trade=trade,
            allocation_pct=0.0001,  # 0.01%
            entry_date=entry_date
        )

        equity = portfolio.get_equity()
        assert equity > 0
        assert np.isfinite(equity)

    def test_large_loss_does_not_create_negative_equity(self):
        """Large losses are accounted but don't create impossible equity."""
        portfolio = Portfolio(initial_capital=1_000_000.0)

        entry_date = date(2024, 1, 2)
        expiry = datetime(2024, 3, 15)

        legs = [
            TradeLeg('call', 500.0, expiry, 1, 45),
            TradeLeg('put', 500.0, expiry, 1, 45)
        ]

        trade = Trade(
            trade_id="TEST_001",
            profile_name="test_profile",
            entry_date=entry_date,
            legs=legs,
            entry_prices={0: 15.0, 1: 14.0}
        )
        trade.__post_init__()

        portfolio.open_position(
            profile_id=1,
            trade=trade,
            allocation_pct=0.20,
            entry_date=entry_date
        )

        # Mark with extreme loss
        extreme_prices = {1: {0: 1.0, 1: 1.0}}
        portfolio.mark_to_market(
            current_date=date(2024, 1, 3),
            option_prices_by_profile=extreme_prices
        )

        equity = portfolio.get_equity()

        # Equity should still be positive (can't lose more than allocated)
        assert equity > 0

    def test_multiple_rebalances_preserve_pnl(self):
        """P&L is preserved through multiple rebalancing cycles."""
        portfolio = Portfolio(initial_capital=1_000_000.0)

        entry_date = date(2024, 1, 2)
        expiry = datetime(2024, 3, 15)

        # Track total P&L through rebalancing
        cumulative_realized = 0.0

        for cycle in range(3):
            legs = [
                TradeLeg('call', 500.0, expiry, 1, 45),
                TradeLeg('put', 500.0, expiry, 1, 45)
            ]

            trade = Trade(
                trade_id=f"TEST_{cycle}",
                profile_name="test_profile",
                entry_date=date(2024, 1, 2 + cycle * 10),
                legs=legs,
                entry_prices={0: 15.0, 1: 14.0}
            )
            trade.__post_init__()

            portfolio.open_position(
                profile_id=1,
                trade=trade,
                allocation_pct=0.20,
                entry_date=date(2024, 1, 2 + cycle * 10)
            )

            # Mark to market
            prices = {1: {0: 16.0 + cycle, 1: 15.0 + cycle}}
            portfolio.mark_to_market(
                current_date=date(2024, 1, 5 + cycle * 10),
                option_prices_by_profile=prices
            )

            # Close position
            exit_prices = {0: 16.0 + cycle, 1: 15.0 + cycle}
            realized = portfolio.close_position(
                profile_id=1,
                exit_prices=exit_prices,
                exit_date=date(2024, 1, 8 + cycle * 10),
                exit_reason="Rebalance"
            )

            cumulative_realized += realized

        # Final equity should match cumulative realized
        final_equity = portfolio.get_equity()
        expected_equity = portfolio.initial_capital + cumulative_realized

        assert abs(final_equity - expected_equity) < 0.01
