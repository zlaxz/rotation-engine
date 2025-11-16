"""
Tests for multi-position Portfolio class.

Validates:
- Simultaneous multi-position tracking
- Cash management
- Position opening/closing
- Mark-to-market calculation
- Portfolio-level P&L
- Greeks aggregation
"""

import pytest
import pandas as pd
from datetime import datetime, date, timedelta
from src.backtest.portfolio_new import Portfolio, ClosedPosition
from src.backtest.position import Position
from src.trading.trade import Trade, TradeLeg


@pytest.fixture
def empty_portfolio():
    """Create empty portfolio with $1M capital."""
    return Portfolio(initial_capital=1_000_000.0)


@pytest.fixture
def sample_trade():
    """Create sample ATM straddle trade."""
    entry_date = date(2024, 1, 2)
    expiry = datetime(2024, 3, 15)

    legs = [
        TradeLeg(
            option_type='call',
            strike=500.0,
            expiry=expiry,
            quantity=1,
            dte=45
        ),
        TradeLeg(
            option_type='put',
            strike=500.0,
            expiry=expiry,
            quantity=1,
            dte=45
        )
    ]

    trade = Trade(
        trade_id="TEST_001",
        profile_name="test_profile",
        entry_date=entry_date,
        legs=legs,
        entry_prices={0: 15.0, 1: 14.0}
    )

    trade.__post_init__()

    return trade


class TestPortfolioInitialization:
    """Test portfolio initialization."""

    def test_initial_state(self, empty_portfolio):
        """Portfolio starts with correct initial state."""
        assert empty_portfolio.initial_capital == 1_000_000.0
        assert empty_portfolio.cash == 1_000_000.0
        assert len(empty_portfolio.positions) == 0
        assert len(empty_portfolio.closed_positions) == 0
        assert len(empty_portfolio.equity_history) == 0

    def test_get_equity_empty(self, empty_portfolio):
        """Empty portfolio equity equals cash."""
        assert empty_portfolio.get_equity() == 1_000_000.0

    def test_get_allocations_empty(self, empty_portfolio):
        """Empty portfolio has no allocations."""
        allocations = empty_portfolio.get_allocations()
        assert allocations == {}


class TestPositionOpening:
    """Test opening positions."""

    def test_open_single_position(self, empty_portfolio, sample_trade):
        """Can open single position."""
        position = empty_portfolio.open_position(
            profile_id=1,
            trade=sample_trade,
            allocation_pct=0.20,
            entry_date=date(2024, 1, 2)
        )

        assert position.profile_id == 1
        assert position.allocation_pct == 0.20
        assert position.entry_value == 200_000.0  # 20% of $1M

        # Check portfolio state
        assert len(empty_portfolio.positions) == 1
        assert empty_portfolio.has_position(1)
        assert empty_portfolio.cash < 1_000_000.0  # Cash reduced by entry cost

    def test_open_multiple_positions(self, empty_portfolio, sample_trade):
        """Can open multiple simultaneous positions."""
        # Open 3 positions for different profiles
        for profile_id in [1, 2, 3]:
            trade = Trade(
                trade_id=f"TEST_{profile_id}",
                profile_name=f"test_profile_{profile_id}",
                entry_date=date(2024, 1, 2),
                legs=sample_trade.legs.copy(),
                entry_prices=sample_trade.entry_prices.copy()
            )
            trade.__post_init__()

            empty_portfolio.open_position(
                profile_id=profile_id,
                trade=trade,
                allocation_pct=0.15,
                entry_date=date(2024, 1, 2)
            )

        assert len(empty_portfolio.positions) == 3
        assert empty_portfolio.has_position(1)
        assert empty_portfolio.has_position(2)
        assert empty_portfolio.has_position(3)
        assert not empty_portfolio.has_position(4)

    def test_open_all_six_positions(self, empty_portfolio, sample_trade):
        """Can open all 6 profile positions simultaneously."""
        for profile_id in range(1, 7):
            trade = Trade(
                trade_id=f"TEST_{profile_id}",
                profile_name=f"test_profile_{profile_id}",
                entry_date=date(2024, 1, 2),
                legs=sample_trade.legs.copy(),
                entry_prices=sample_trade.entry_prices.copy()
            )
            trade.__post_init__()

            empty_portfolio.open_position(
                profile_id=profile_id,
                trade=trade,
                allocation_pct=0.10,  # 10% each
                entry_date=date(2024, 1, 2)
            )

        assert len(empty_portfolio.positions) == 6
        allocations = empty_portfolio.get_allocations()
        assert len(allocations) == 6
        assert all(alloc == 0.10 for alloc in allocations.values())

    def test_insufficient_cash_error(self, empty_portfolio, sample_trade):
        """Opening position with insufficient cash raises error."""
        # Try to allocate 150% of capital
        with pytest.raises(ValueError, match="Insufficient cash"):
            empty_portfolio.open_position(
                profile_id=1,
                trade=sample_trade,
                allocation_pct=1.50,
                entry_date=date(2024, 1, 2)
            )


class TestPositionClosing:
    """Test closing positions."""

    def test_close_single_position(self, empty_portfolio, sample_trade):
        """Can close open position."""
        # Open position
        empty_portfolio.open_position(
            profile_id=1,
            trade=sample_trade,
            allocation_pct=0.20,
            entry_date=date(2024, 1, 2)
        )

        assert len(empty_portfolio.positions) == 1

        # Close position
        exit_prices = {0: 18.0, 1: 16.0}  # Profitable exit
        realized_pnl = empty_portfolio.close_position(
            profile_id=1,
            exit_prices=exit_prices,
            exit_date=date(2024, 1, 10),
            exit_reason="Test close"
        )

        assert len(empty_portfolio.positions) == 0
        assert not empty_portfolio.has_position(1)
        assert len(empty_portfolio.closed_positions) == 1
        assert realized_pnl > 0  # Profitable trade

    def test_close_nonexistent_position_error(self, empty_portfolio):
        """Closing nonexistent position raises error."""
        with pytest.raises(ValueError, match="No active position"):
            empty_portfolio.close_position(
                profile_id=1,
                exit_prices={},
                exit_date=date(2024, 1, 10),
                exit_reason="Test"
            )

    def test_closed_position_record(self, empty_portfolio, sample_trade):
        """Closed position is recorded correctly."""
        entry_date = date(2024, 1, 2)
        exit_date = date(2024, 1, 10)

        # Open and close
        empty_portfolio.open_position(
            profile_id=1,
            trade=sample_trade,
            allocation_pct=0.20,
            entry_date=entry_date
        )

        exit_prices = {0: 18.0, 1: 16.0}
        empty_portfolio.close_position(
            profile_id=1,
            exit_prices=exit_prices,
            exit_date=exit_date,
            exit_reason="Test close"
        )

        closed = empty_portfolio.closed_positions[0]
        assert closed.profile_id == 1
        assert closed.entry_date == entry_date
        assert closed.exit_date == exit_date
        assert closed.days_held == 8
        assert closed.exit_reason == "Test close"


class TestMarkToMarket:
    """Test mark-to-market calculations."""

    def test_mark_to_market_single_position(self, empty_portfolio, sample_trade):
        """Mark to market updates position values."""
        # Open position
        empty_portfolio.open_position(
            profile_id=1,
            trade=sample_trade,
            allocation_pct=0.20,
            entry_date=date(2024, 1, 2)
        )

        # Mark to market with new prices
        current_prices = {
            1: {0: 16.0, 1: 15.0}  # Profile 1 prices
        }

        total_equity = empty_portfolio.mark_to_market(
            current_date=date(2024, 1, 3),
            option_prices_by_profile=current_prices
        )

        assert total_equity > empty_portfolio.initial_capital  # Profitable
        assert len(empty_portfolio.equity_history) == 1

        # Check equity record
        record = empty_portfolio.equity_history[0]
        assert record['date'] == date(2024, 1, 3)
        assert record['total_equity'] == total_equity
        assert record['num_positions'] == 1

    def test_mark_to_market_multiple_positions(self, empty_portfolio, sample_trade):
        """Mark to market with multiple positions."""
        # Open 3 positions
        for profile_id in [1, 2, 3]:
            trade = Trade(
                trade_id=f"TEST_{profile_id}",
                profile_name=f"test_profile_{profile_id}",
                entry_date=date(2024, 1, 2),
                legs=sample_trade.legs.copy(),
                entry_prices=sample_trade.entry_prices.copy()
            )
            trade.__post_init__()

            empty_portfolio.open_position(
                profile_id=profile_id,
                trade=trade,
                allocation_pct=0.15,
                entry_date=date(2024, 1, 2)
            )

        # Mark to market all positions
        current_prices = {
            1: {0: 16.0, 1: 15.0},
            2: {0: 14.0, 1: 13.0},  # Losing position
            3: {0: 17.0, 1: 16.0}   # Winning position
        }

        total_equity = empty_portfolio.mark_to_market(
            current_date=date(2024, 1, 3),
            option_prices_by_profile=current_prices
        )

        # Should have mix of P&L
        assert len(empty_portfolio.equity_history) == 1
        record = empty_portfolio.equity_history[0]
        assert record['num_positions'] == 3


class TestPnLCalculations:
    """Test P&L calculation methods."""

    def test_unrealized_pnl(self, empty_portfolio, sample_trade):
        """Unrealized P&L calculated correctly."""
        # Open position
        empty_portfolio.open_position(
            profile_id=1,
            trade=sample_trade,
            allocation_pct=0.20,
            entry_date=date(2024, 1, 2)
        )

        # Mark to market
        current_prices = {1: {0: 18.0, 1: 17.0}}  # Profitable
        empty_portfolio.mark_to_market(
            current_date=date(2024, 1, 3),
            option_prices_by_profile=current_prices
        )

        unrealized = empty_portfolio.get_unrealized_pnl()
        assert unrealized > 0  # Profit

    def test_realized_pnl(self, empty_portfolio, sample_trade):
        """Realized P&L calculated correctly."""
        # Open and close position
        empty_portfolio.open_position(
            profile_id=1,
            trade=sample_trade,
            allocation_pct=0.20,
            entry_date=date(2024, 1, 2)
        )

        exit_prices = {0: 18.0, 1: 17.0}
        empty_portfolio.close_position(
            profile_id=1,
            exit_prices=exit_prices,
            exit_date=date(2024, 1, 10),
            exit_reason="Test"
        )

        realized = empty_portfolio.get_realized_pnl()
        assert realized > 0

    def test_total_pnl(self, empty_portfolio, sample_trade):
        """Total P&L = realized + unrealized."""
        # Open 2 positions
        for profile_id in [1, 2]:
            trade = Trade(
                trade_id=f"TEST_{profile_id}",
                profile_name=f"test_profile_{profile_id}",
                entry_date=date(2024, 1, 2),
                legs=sample_trade.legs.copy(),
                entry_prices=sample_trade.entry_prices.copy()
            )
            trade.__post_init__()

            empty_portfolio.open_position(
                profile_id=profile_id,
                trade=trade,
                allocation_pct=0.20,
                entry_date=date(2024, 1, 2)
            )

        # Close first position (realized)
        exit_prices = {0: 18.0, 1: 17.0}
        empty_portfolio.close_position(
            profile_id=1,
            exit_prices=exit_prices,
            exit_date=date(2024, 1, 5),
            exit_reason="Test"
        )

        # Mark second position (unrealized)
        current_prices = {2: {0: 16.0, 1: 15.0}}
        empty_portfolio.mark_to_market(
            current_date=date(2024, 1, 6),
            option_prices_by_profile=current_prices
        )

        # Total = realized + unrealized
        total = empty_portfolio.get_total_pnl()
        realized = empty_portfolio.get_realized_pnl()
        unrealized = empty_portfolio.get_unrealized_pnl()

        assert abs(total - (realized + unrealized)) < 0.01  # Floating point tolerance


class TestGreeksAggregation:
    """Test portfolio-level Greeks calculation."""

    def test_portfolio_greeks_single_position(self, empty_portfolio, sample_trade):
        """Portfolio Greeks for single position."""
        # Open position and set Greeks
        position = empty_portfolio.open_position(
            profile_id=1,
            trade=sample_trade,
            allocation_pct=0.20,
            entry_date=date(2024, 1, 2)
        )

        # Set Greeks on trade
        sample_trade.net_delta = 50.0
        sample_trade.net_gamma = 0.5
        sample_trade.net_theta = -10.0
        sample_trade.net_vega = 100.0

        greeks = empty_portfolio.get_portfolio_greeks()

        assert greeks['delta'] == 50.0
        assert greeks['gamma'] == 0.5
        assert greeks['theta'] == -10.0
        assert greeks['vega'] == 100.0

    def test_portfolio_greeks_multiple_positions(self, empty_portfolio, sample_trade):
        """Portfolio Greeks aggregate across positions."""
        # Open 3 positions with different Greeks
        for profile_id in [1, 2, 3]:
            trade = Trade(
                trade_id=f"TEST_{profile_id}",
                profile_name=f"test_profile_{profile_id}",
                entry_date=date(2024, 1, 2),
                legs=sample_trade.legs.copy(),
                entry_prices=sample_trade.entry_prices.copy()
            )
            trade.__post_init__()

            # Set Greeks
            trade.net_delta = 25.0 * profile_id
            trade.net_gamma = 0.2 * profile_id
            trade.net_theta = -5.0 * profile_id
            trade.net_vega = 50.0 * profile_id

            empty_portfolio.open_position(
                profile_id=profile_id,
                trade=trade,
                allocation_pct=0.15,
                entry_date=date(2024, 1, 2)
            )

        greeks = empty_portfolio.get_portfolio_greeks()

        # Should sum across all 3 positions
        expected_delta = 25.0 * 1 + 25.0 * 2 + 25.0 * 3
        assert abs(greeks['delta'] - expected_delta) < 0.01


class TestEquityCurve:
    """Test equity curve generation."""

    def test_equity_curve_generation(self, empty_portfolio, sample_trade):
        """Equity curve DataFrame generated correctly."""
        # Open position
        empty_portfolio.open_position(
            profile_id=1,
            trade=sample_trade,
            allocation_pct=0.20,
            entry_date=date(2024, 1, 2)
        )

        # Mark to market 3 days
        for day in range(1, 4):
            current_prices = {1: {0: 15.0 + day, 1: 14.0 + day}}
            empty_portfolio.mark_to_market(
                current_date=date(2024, 1, 2 + day),
                option_prices_by_profile=current_prices
            )

        equity_curve = empty_portfolio.get_equity_curve()

        assert len(equity_curve) == 3
        assert 'date' in equity_curve.columns
        assert 'total_equity' in equity_curve.columns
        assert 'cash' in equity_curve.columns
        assert 'num_positions' in equity_curve.columns

    def test_closed_positions_summary(self, empty_portfolio, sample_trade):
        """Closed positions summary DataFrame."""
        # Open and close 2 positions
        for profile_id in [1, 2]:
            trade = Trade(
                trade_id=f"TEST_{profile_id}",
                profile_name=f"test_profile_{profile_id}",
                entry_date=date(2024, 1, 2),
                legs=sample_trade.legs.copy(),
                entry_prices=sample_trade.entry_prices.copy()
            )
            trade.__post_init__()

            empty_portfolio.open_position(
                profile_id=profile_id,
                trade=trade,
                allocation_pct=0.20,
                entry_date=date(2024, 1, 2)
            )

            exit_prices = {0: 18.0, 1: 17.0}
            empty_portfolio.close_position(
                profile_id=profile_id,
                exit_prices=exit_prices,
                exit_date=date(2024, 1, 10),
                exit_reason="Test"
            )

        summary = empty_portfolio.get_closed_positions_summary()

        assert len(summary) == 2
        assert 'profile_id' in summary.columns
        assert 'realized_pnl' in summary.columns
        assert 'return_pct' in summary.columns
        assert 'exit_reason' in summary.columns
