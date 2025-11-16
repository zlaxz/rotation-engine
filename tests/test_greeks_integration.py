"""
Integration test for Greeks calculation in Trade and Simulator.

Tests:
1. Greeks calculated at trade entry
2. Greeks update during position lifecycle
3. Delta hedging uses actual Greeks
4. Multi-leg structures aggregate Greeks correctly
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from src.trading.trade import Trade, TradeLeg, create_straddle_trade
from src.trading.simulator import TradeSimulator, SimulationConfig, ExecutionModel


class TestTradeGreeksCalculation:
    """Test Greeks calculation in Trade class."""

    def test_single_call_greeks(self):
        """Test Greeks for single long call."""
        trade = Trade(
            trade_id="test_001",
            profile_name="test",
            entry_date=datetime(2024, 1, 1),
            legs=[
                TradeLeg(
                    strike=100.0,
                    expiry=datetime(2024, 2, 1),  # 31 days
                    option_type='call',
                    quantity=1,
                    dte=31
                )
            ],
            entry_prices={0: 5.0}
        )

        # Calculate Greeks
        trade.calculate_greeks(
            underlying_price=100.0,
            current_date=datetime(2024, 1, 1),
            implied_vol=0.30,
            risk_free_rate=0.05
        )

        # ATM call: delta should be ~50-60 per contract (0.5-0.6 * 100)
        assert 40 <= trade.net_delta <= 70, f"ATM call delta {trade.net_delta} not in expected range"

        # Gamma should be positive
        assert trade.net_gamma > 0, f"Long call gamma {trade.net_gamma} should be positive"

        # Vega should be positive (long vol)
        assert trade.net_vega > 0, f"Long call vega {trade.net_vega} should be positive"

        # Theta should be negative (time decay)
        assert trade.net_theta < 0, f"Long call theta {trade.net_theta} should be negative"

    def test_straddle_greeks(self):
        """Test Greeks for ATM straddle (delta-neutral)."""
        trade = create_straddle_trade(
            trade_id="test_002",
            profile_name="test",
            entry_date=datetime(2024, 1, 1),
            strike=100.0,
            expiry=datetime(2024, 2, 1),
            dte=31,
            quantity=1,
            entry_prices={0: 5.0, 1: 5.0}
        )

        # Calculate Greeks
        trade.calculate_greeks(
            underlying_price=100.0,
            current_date=datetime(2024, 1, 1),
            implied_vol=0.30,
            risk_free_rate=0.05
        )

        # ATM straddle should be approximately delta-neutral
        assert abs(trade.net_delta) < 20, (
            f"ATM straddle delta {trade.net_delta} should be near 0 (delta-neutral)"
        )

        # Straddle has positive gamma (long both call and put)
        assert trade.net_gamma > 5, (
            f"Long straddle gamma {trade.net_gamma} should be significantly positive"
        )

        # Straddle has positive vega (long vol)
        assert trade.net_vega > 500, (
            f"Long straddle vega {trade.net_vega} should be significantly positive"
        )

        # Straddle has negative theta (time decay)
        assert trade.net_theta < -500, (
            f"Long straddle theta {trade.net_theta} should be negative"
        )

    def test_short_option_greeks(self):
        """Test Greeks for short option (negative quantity)."""
        trade = Trade(
            trade_id="test_003",
            profile_name="test",
            entry_date=datetime(2024, 1, 1),
            legs=[
                TradeLeg(
                    strike=100.0,
                    expiry=datetime(2024, 2, 1),
                    option_type='put',
                    quantity=-1,  # Short put
                    dte=31
                )
            ],
            entry_prices={0: 5.0}
        )

        # Calculate Greeks
        trade.calculate_greeks(
            underlying_price=100.0,
            current_date=datetime(2024, 1, 1),
            implied_vol=0.30,
            risk_free_rate=0.05
        )

        # Short ATM put: delta should be positive (opposite of long put)
        assert trade.net_delta > 20, f"Short ATM put delta {trade.net_delta} should be positive"

        # Short option has negative gamma
        assert trade.net_gamma < 0, f"Short put gamma {trade.net_gamma} should be negative"

        # Short option has negative vega (short vol)
        assert trade.net_vega < 0, f"Short put vega {trade.net_vega} should be negative"

        # Short option has positive theta (collect time decay)
        assert trade.net_theta > 0, f"Short put theta {trade.net_theta} should be positive"

    def test_greeks_update_over_time(self):
        """Test that Greeks update as trade ages."""
        trade = create_straddle_trade(
            trade_id="test_004",
            profile_name="test",
            entry_date=datetime(2024, 1, 1),
            strike=100.0,
            expiry=datetime(2024, 2, 1),
            dte=31,
            quantity=1,
            entry_prices={0: 5.0, 1: 5.0}
        )

        # Calculate Greeks at entry
        trade.calculate_greeks(
            underlying_price=100.0,
            current_date=datetime(2024, 1, 1),
            implied_vol=0.30,
            risk_free_rate=0.05
        )
        initial_gamma = trade.net_gamma
        initial_theta = trade.net_theta

        # Calculate Greeks 15 days later
        trade.calculate_greeks(
            underlying_price=100.0,
            current_date=datetime(2024, 1, 16),  # 15 days later
            implied_vol=0.30,
            risk_free_rate=0.05
        )
        later_gamma = trade.net_gamma
        later_theta = trade.net_theta

        # As expiration approaches, gamma should increase
        assert later_gamma > initial_gamma, (
            f"Gamma should increase near expiration: {initial_gamma:.2f} -> {later_gamma:.2f}"
        )

        # Theta magnitude should increase (more negative)
        assert later_theta < initial_theta, (
            f"Theta should be more negative near expiration: {initial_theta:.2f} -> {later_theta:.2f}"
        )

    def test_greeks_at_expiration(self):
        """Test Greeks at/after expiration."""
        trade = Trade(
            trade_id="test_005",
            profile_name="test",
            entry_date=datetime(2024, 1, 1),
            legs=[
                TradeLeg(
                    strike=100.0,
                    expiry=datetime(2024, 1, 1),  # Already expired
                    option_type='call',
                    quantity=1,
                    dte=0
                )
            ],
            entry_prices={0: 5.0}
        )

        # Calculate Greeks at expiration
        trade.calculate_greeks(
            underlying_price=100.0,
            current_date=datetime(2024, 1, 1),
            implied_vol=0.30,
            risk_free_rate=0.05
        )

        # At expiration, all Greeks should be 0
        assert trade.net_delta == 0.0, f"Delta at expiration should be 0, got {trade.net_delta}"
        assert trade.net_gamma == 0.0, f"Gamma at expiration should be 0, got {trade.net_gamma}"
        assert trade.net_vega == 0.0, f"Vega at expiration should be 0, got {trade.net_vega}"
        assert trade.net_theta == 0.0, f"Theta at expiration should be 0, got {trade.net_theta}"


class TestSimulatorGreeksIntegration:
    """Test Greeks integration in simulator."""

    def test_greeks_calculated_at_entry(self):
        """Test that simulator calculates Greeks when entering trade."""
        # Create simple backtest data
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        data = pd.DataFrame({
            'date': dates,
            'close': [100.0] * 5,
            'RV20': [0.20] * 5
        })

        config = SimulationConfig(
            delta_hedge_enabled=False  # Disable hedging for this test
        )
        sim = TradeSimulator(data, config)

        # Simple entry: enter on day 1
        def entry_logic(row, current_trade):
            return current_trade is None and row['date'] == dates[0]

        def trade_constructor(row, trade_id):
            return create_straddle_trade(
                trade_id=trade_id,
                profile_name="test",
                entry_date=row['date'],
                strike=row['close'],
                expiry=row['date'] + timedelta(days=30),
                dte=30
            )

        # Run simulation
        sim.simulate(
            profile_name="test_greeks",
            entry_logic=entry_logic,
            trade_constructor=trade_constructor
        )

        # Check that trade has Greeks calculated
        assert len(sim.trades) > 0, "Should have entered at least one trade"
        trade = sim.trades[0]

        # Greeks should be non-zero
        assert trade.net_delta != 0.0 or trade.net_gamma != 0.0, (
            "Greeks should be calculated at entry"
        )

    def test_delta_hedging_uses_greeks(self):
        """Test that delta hedging uses actual Greeks, not placeholder."""
        # Create backtest data with position held for multiple days
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        data = pd.DataFrame({
            'date': dates,
            'close': [100.0] * 10,
            'RV20': [0.20] * 10
        })

        config = SimulationConfig(
            delta_hedge_enabled=True,
            delta_hedge_frequency='daily'
        )
        sim = TradeSimulator(data, config)

        # Entry logic: enter on day 1 only
        def entry_logic(row, current_trade):
            return current_trade is None and row['date'] == dates[0]

        def trade_constructor(row, trade_id):
            # Long call (positive delta) - should trigger hedging
            return Trade(
                trade_id=trade_id,
                profile_name="test",
                entry_date=row['date'],
                legs=[
                    TradeLeg(
                        strike=100.0,
                        expiry=row['date'] + timedelta(days=30),
                        option_type='call',
                        quantity=5,  # 5 contracts = ~250 delta
                        dte=30
                    )
                ],
                entry_prices={0: 5.0}
            )

        # Run simulation
        sim.simulate(
            profile_name="test_hedge",
            entry_logic=entry_logic,
            trade_constructor=trade_constructor
        )

        # Check that hedging occurred
        assert len(sim.trades) > 0, "Should have entered at least one trade"
        trade = sim.trades[0]

        # With 5 long calls, should have accumulated hedge costs
        # Hedging should cost more than placeholder $15/day * days
        # because actual delta is ~250 (5 contracts * 50 delta)
        days_held = (trade.exit_date - trade.entry_date).days
        placeholder_cost = 15.0 * max(1, days_held)

        # Real hedge cost should be higher (hedging ~250 delta = ~5 ES contracts)
        assert trade.cumulative_hedge_cost > placeholder_cost, (
            f"Hedge cost ${trade.cumulative_hedge_cost:.2f} should exceed "
            f"placeholder ${placeholder_cost:.2f} for {days_held} days"
        )

    def test_delta_neutral_no_hedge(self):
        """Test that delta-neutral positions don't incur hedging costs."""
        # Create backtest data
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        data = pd.DataFrame({
            'date': dates,
            'close': [100.0] * 10,
            'RV20': [0.20] * 10
        })

        config = SimulationConfig(
            delta_hedge_enabled=True,
            delta_hedge_frequency='daily'
        )
        sim = TradeSimulator(data, config)

        # Entry logic: enter on day 1 only
        def entry_logic(row, current_trade):
            return current_trade is None and row['date'] == dates[0]

        def trade_constructor(row, trade_id):
            # ATM straddle (delta-neutral) - should not trigger hedging
            return create_straddle_trade(
                trade_id=trade_id,
                profile_name="test",
                entry_date=row['date'],
                strike=100.0,
                expiry=row['date'] + timedelta(days=30),
                dte=30
            )

        # Run simulation
        sim.simulate(
            profile_name="test_neutral",
            entry_logic=entry_logic,
            trade_constructor=trade_constructor
        )

        # Check that minimal/no hedging occurred
        assert len(sim.trades) > 0, "Should have entered at least one trade"
        trade = sim.trades[0]

        # ATM straddle has delta ~0-10, should incur minimal hedging
        # With delta threshold = 20, straddle delta ~8 shouldn't hedge
        # But if IV or price changes, delta might occasionally cross threshold
        # Allow up to 2 ES contracts worth of hedging ($30)
        assert trade.cumulative_hedge_cost <= 30.0, (
            f"Delta-neutral straddle should have minimal hedge costs, "
            f"got ${trade.cumulative_hedge_cost:.2f}"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
