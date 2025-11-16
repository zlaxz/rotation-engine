"""
Comprehensive tests for Bug 1 (Timing) and Bug 2 (Greeks Updates).

Bug 1: Same-Day Entry Timing (No Look-Ahead Bias)
- Verify signal generated at T uses only T data
- Verify trade executed at T+1 using T+1 prices
- Verify no future information leakage

Bug 2: Greeks Updates During Mark-to-Market
- Verify Greeks updated daily during MTM
- Verify Greeks history tracked over position lifetime
- Verify P&L attribution by Greek components
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.trading.trade import Trade, TradeLeg, create_straddle_trade
from src.trading.simulator import TradeSimulator, SimulationConfig


# ==============================================================================
# Bug 1: Timing Tests (No Look-Ahead Bias)
# ==============================================================================

def test_entry_signal_uses_only_current_day_data():
    """
    CRITICAL: Verify entry_logic sees ONLY Day T data, not T+1.

    Test approach:
    - Create dataset where Day T and Day T+1 have different regimes
    - Entry logic checks regime
    - Verify entry decision made using Day T regime, not T+1
    """
    # Create test data with regime change
    data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=5, freq='D'),
        'open': [400.0] * 5,
        'high': [405.0] * 5,
        'low': [395.0] * 5,
        'close': [400.0, 410.0, 420.0, 430.0, 440.0],  # Trending up
        'RV20': [0.20] * 5,
        'regime': [1, 2, 1, 2, 1]  # Regime changes daily
    })

    # Track which regime entry_logic sees
    seen_regimes = []

    def entry_logic(row, current_trade):
        """Entry logic that records regime it sees."""
        seen_regimes.append(row['regime'])
        return row['regime'] == 2  # Enter only in regime 2

    def trade_constructor(row, trade_id):
        """Simple trade constructor."""
        return create_straddle_trade(
            trade_id=trade_id,
            profile_name="Test",
            entry_date=row['date'],
            strike=row['close'],
            expiry=row['date'] + timedelta(days=30),
            dte=30,
            entry_prices={0: 5.0, 1: 5.0}
        )

    config = SimulationConfig(
        delta_hedge_enabled=False,
        allow_toy_pricing=True
    )

    sim = TradeSimulator(data, config, use_real_options_data=False)
    results = sim.simulate(entry_logic, trade_constructor, profile_name="Test")

    # Verify entry_logic was called until trade opened
    # It's called on days without open trade
    assert len(seen_regimes) >= 2, "Entry logic should be called multiple times"

    # Verify entry_logic saw regime=2 at some point (should trigger entry)
    assert 2 in seen_regimes, "Entry logic should see regime=2 and signal entry"

    # Verify trade was entered
    assert len(sim.trades) == 1
    trade = sim.trades[0]

    # Verify entry happened after seeing regime=2 signal
    # Signal at T, execute at T+1
    regime_2_index = seen_regimes.index(2)
    expected_entry_date = data.iloc[regime_2_index + 1]['date']
    assert trade.entry_date.date() == expected_entry_date.date()

    print("✅ Entry logic uses ONLY Day T data (no look-ahead bias)")


def test_trade_executed_at_t_plus_1():
    """
    CRITICAL: Verify trade executed using Day T+1 prices, not Day T.

    Test approach:
    - Create dataset with distinct prices each day
    - Signal entry on Day T
    - Verify trade entry_prices use Day T+1 close, not Day T close
    """
    data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=5, freq='D'),
        'open': [400.0] * 5,
        'high': [405.0] * 5,
        'low': [395.0] * 5,
        'close': [400.0, 410.0, 420.0, 430.0, 440.0],  # Distinct prices
        'RV20': [0.20] * 5,
        'regime': [1] * 5
    })

    # Track when entry_logic sees each day
    entry_logic_days = []

    def entry_logic(row, current_trade):
        """Signal entry on Day 1 (close=410)."""
        entry_logic_days.append((row['date'], row['close']))
        return row['date'] == pd.Timestamp('2024-01-02')

    def trade_constructor(row, trade_id):
        """Record the spot price seen at construction."""
        return create_straddle_trade(
            trade_id=trade_id,
            profile_name="Test",
            entry_date=row['date'],
            strike=row['close'],  # Use Day T+1 close
            expiry=row['date'] + timedelta(days=30),
            dte=30,
            entry_prices={0: row['close'] * 0.05, 1: row['close'] * 0.05}  # 5% of spot
        )

    config = SimulationConfig(
        delta_hedge_enabled=False,
        allow_toy_pricing=True
    )

    sim = TradeSimulator(data, config, use_real_options_data=False)
    results = sim.simulate(entry_logic, trade_constructor, profile_name="Test")

    # Verify entry_logic saw Day 1 with close=410
    assert any(close == 410.0 for date, close in entry_logic_days)

    # Verify trade entered on Day 2 with strike=420 (Day 2 close)
    assert len(sim.trades) == 1
    trade = sim.trades[0]
    assert trade.entry_date.date() == pd.Timestamp('2024-01-03').date()
    assert trade.legs[0].strike == 420.0  # Day T+1 close, not Day T (410)

    print("✅ Trade executed at T+1 using T+1 prices (correct timing)")


def test_no_same_day_execution():
    """
    CRITICAL: Verify trade NEVER executes same day as signal.

    This prevents intraday look-ahead bias where signal at EOD could
    use same-day close for execution.
    """
    data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=10, freq='D'),
        'open': [400.0] * 10,
        'high': [405.0] * 10,
        'low': [395.0] * 10,
        'close': np.linspace(400, 440, 10),
        'RV20': [0.20] * 10,
        'regime': [1] * 10
    })

    signal_dates = []
    execution_dates = []

    def entry_logic(row, current_trade):
        """Signal entry on specific dates."""
        should_enter = row['date'].day in [2, 5, 8]
        if should_enter:
            signal_dates.append(row['date'])
        return should_enter

    def trade_constructor(row, trade_id):
        """Record execution date."""
        execution_dates.append(row['date'])
        return create_straddle_trade(
            trade_id=trade_id,
            profile_name="Test",
            entry_date=row['date'],
            strike=row['close'],
            expiry=row['date'] + timedelta(days=7),
            dte=7,
            entry_prices={0: 5.0, 1: 5.0}
        )

    config = SimulationConfig(
        delta_hedge_enabled=False,
        allow_toy_pricing=True,
        roll_dte_threshold=1
    )

    sim = TradeSimulator(data, config, use_real_options_data=False)
    results = sim.simulate(entry_logic, trade_constructor, profile_name="Test")

    # Verify execution always T+1 after signal
    for signal_date, exec_date in zip(signal_dates, execution_dates):
        assert (exec_date - signal_date).days == 1, \
            f"Execution {exec_date} should be 1 day after signal {signal_date}"

    print("✅ No same-day execution (T+1 fill enforced)")


# ==============================================================================
# Bug 2: Greeks Update Tests
# ==============================================================================

def test_greeks_updated_during_mark_to_market():
    """
    CRITICAL: Verify Greeks recalculated daily during mark-to-market.

    Previous behavior: Greeks calculated once at entry, frozen
    Fixed behavior: Greeks updated every day
    """
    # Create a simple ATM straddle
    trade = create_straddle_trade(
        trade_id="TEST_001",
        profile_name="TestProfile",
        entry_date=datetime(2024, 1, 1),
        strike=400.0,
        expiry=datetime(2024, 2, 1),
        dte=30,
        entry_prices={0: 10.0, 1: 10.0}
    )

    # Calculate entry Greeks
    trade.calculate_greeks(
        underlying_price=400.0,
        current_date=datetime(2024, 1, 1),
        implied_vol=0.25,
        risk_free_rate=0.05
    )

    entry_delta = trade.net_delta
    entry_gamma = trade.net_gamma
    entry_theta = trade.net_theta
    entry_vega = trade.net_vega

    # Mark to market Day 2 (spot moved +10, vol unchanged)
    trade.mark_to_market(
        current_prices={0: 12.0, 1: 8.0},
        current_date=datetime(2024, 1, 2),
        underlying_price=410.0,  # Spot moved +10
        implied_vol=0.25,
        risk_free_rate=0.05
    )

    day2_delta = trade.net_delta
    day2_gamma = trade.net_gamma
    day2_theta = trade.net_theta

    # Verify Greeks changed (ATM straddle moved to ITM call / OTM put)
    assert day2_delta != entry_delta, "Delta should change as spot moves"
    assert day2_gamma != entry_gamma, "Gamma should change as spot moves"
    assert day2_theta != entry_theta, "Theta should change as DTE decreases"

    # ATM straddle has ~0 delta, moving spot up should increase delta (call dominates)
    assert abs(day2_delta) > abs(entry_delta), "Delta should increase as we move away from ATM"

    print("✅ Greeks updated during mark-to-market (not frozen)")


def test_greeks_history_tracked():
    """
    CRITICAL: Verify Greeks history stored over position lifetime.

    Required for P&L attribution and post-trade analysis.
    """
    trade = create_straddle_trade(
        trade_id="TEST_002",
        profile_name="TestProfile",
        entry_date=datetime(2024, 1, 1),
        strike=400.0,
        expiry=datetime(2024, 2, 1),
        dte=30,
        entry_prices={0: 10.0, 1: 10.0}
    )

    # Mark to market for 5 days
    for day in range(5):
        trade.mark_to_market(
            current_prices={0: 10.0 + day, 1: 10.0 - day},
            current_date=datetime(2024, 1, 1) + timedelta(days=day),
            underlying_price=400.0 + day * 2,  # Spot drifting up
            implied_vol=0.25 + day * 0.01,  # Vol increasing
            risk_free_rate=0.05
        )

    # Verify history length
    assert len(trade.greeks_history) == 5, "Should have 5 history entries"

    # Verify history structure
    for i, entry in enumerate(trade.greeks_history):
        assert 'date' in entry
        assert 'days_in_trade' in entry
        assert 'avg_dte' in entry
        assert 'spot' in entry
        assert 'delta' in entry
        assert 'gamma' in entry
        assert 'vega' in entry
        assert 'theta' in entry
        assert 'iv' in entry

        # Verify values make sense
        assert entry['days_in_trade'] == i
        assert entry['spot'] == 400.0 + i * 2
        assert entry['iv'] == 0.25 + i * 0.01

    print("✅ Greeks history tracked over position lifetime")


def test_pnl_attribution_calculated():
    """
    CRITICAL: Verify P&L attributed to delta, gamma, theta, vega.

    Attribution formula:
    - Delta P&L: delta × ΔS
    - Gamma P&L: 0.5 × gamma × (ΔS)²
    - Theta P&L: theta × Δt
    - Vega P&L: vega × ΔIV
    """
    trade = create_straddle_trade(
        trade_id="TEST_003",
        profile_name="TestProfile",
        entry_date=datetime(2024, 1, 1),
        strike=400.0,
        expiry=datetime(2024, 2, 1),
        dte=30,
        entry_prices={0: 10.0, 1: 10.0}
    )

    # Day 1: Calculate entry Greeks
    trade.mark_to_market(
        current_prices={0: 10.0, 1: 10.0},
        current_date=datetime(2024, 1, 1),
        underlying_price=400.0,
        implied_vol=0.25,
        risk_free_rate=0.05
    )

    # Day 2: Spot moves +10, vol unchanged
    trade.mark_to_market(
        current_prices={0: 12.0, 1: 8.0},
        current_date=datetime(2024, 1, 2),
        underlying_price=410.0,
        implied_vol=0.25,
        risk_free_rate=0.05
    )

    # Verify attribution exists
    assert trade.pnl_attribution is not None, "P&L attribution should exist"

    # Verify all components present
    assert 'delta_pnl' in trade.pnl_attribution
    assert 'gamma_pnl' in trade.pnl_attribution
    assert 'theta_pnl' in trade.pnl_attribution
    assert 'vega_pnl' in trade.pnl_attribution
    assert 'total_attributed' in trade.pnl_attribution

    # Verify delta P&L makes sense (spot moved +10)
    delta_spot = trade.pnl_attribution['delta_spot']
    assert abs(delta_spot - 10.0) < 0.01, "Delta spot should be ~10"

    # Verify gamma P&L is positive (long gamma, spot moved)
    assert trade.pnl_attribution['gamma_pnl'] > 0, "Long straddle = long gamma = positive gamma P&L"

    # Verify theta P&L is negative (long options = negative theta)
    assert trade.pnl_attribution['theta_pnl'] < 0, "Long straddle = negative theta decay"

    print("✅ P&L attribution calculated correctly")


def test_greeks_update_in_simulator_integration():
    """
    INTEGRATION: Verify simulator passes correct parameters to mark_to_market.

    End-to-end test that Greeks updates work in full backtest.
    """
    data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=10, freq='D'),
        'open': [400.0] * 10,
        'high': [405.0] * 10,
        'low': [395.0] * 10,
        'close': np.linspace(400, 420, 10),
        'RV20': np.linspace(0.20, 0.30, 10),
        'regime': [1] * 10
    })

    def entry_logic(row, current_trade):
        """Enter on Day 2."""
        return row['date'] == pd.Timestamp('2024-01-03')

    def trade_constructor(row, trade_id):
        """Create ATM straddle."""
        return create_straddle_trade(
            trade_id=trade_id,
            profile_name="Test",
            entry_date=row['date'],
            strike=row['close'],
            expiry=row['date'] + timedelta(days=7),
            dte=7,
            entry_prices={0: 5.0, 1: 5.0}
        )

    config = SimulationConfig(
        delta_hedge_enabled=False,
        allow_toy_pricing=True,
        roll_dte_threshold=1
    )

    sim = TradeSimulator(data, config, use_real_options_data=False)
    results = sim.simulate(entry_logic, trade_constructor, profile_name="Test")

    # Verify trade has Greeks history
    assert len(sim.trades) == 1
    trade = sim.trades[0]
    assert len(trade.greeks_history) > 0, "Greeks history should be populated"

    # Verify history exists for multiple days
    # Note: mark_to_market can be called multiple times per day (exit check + MTM)
    # So history length may be >= days held, not exactly equal
    entry_date = trade.entry_date.date()
    exit_date = trade.exit_date.date()
    days_held = (exit_date - entry_date).days

    # Check that we have history for at least the days held
    unique_dates = set(entry['date'] for entry in trade.greeks_history)
    assert len(unique_dates) >= days_held, \
        f"Should have Greeks history for at least {days_held} unique days, got {len(unique_dates)}"

    # Verify P&L attribution exists
    assert trade.pnl_attribution is not None, "P&L attribution should exist"

    print("✅ Greeks updates work in full simulator integration")


def test_greeks_attribution_accuracy():
    """
    VALIDATION: Check that attributed P&L roughly matches actual P&L.

    Note: Attribution is approximate (Taylor expansion, first order Greeks only).
    We don't expect perfect match, but should be close for small moves.
    """
    trade = create_straddle_trade(
        trade_id="TEST_004",
        profile_name="TestProfile",
        entry_date=datetime(2024, 1, 1),
        strike=400.0,
        expiry=datetime(2024, 2, 1),
        dte=30,
        entry_prices={0: 10.0, 1: 10.0}
    )

    # Day 1: Entry
    mtm_day1 = trade.mark_to_market(
        current_prices={0: 10.0, 1: 10.0},
        current_date=datetime(2024, 1, 1),
        underlying_price=400.0,
        implied_vol=0.25,
        risk_free_rate=0.05
    )

    # Day 2: Small move
    mtm_day2 = trade.mark_to_market(
        current_prices={0: 10.5, 1: 9.5},
        current_date=datetime(2024, 1, 2),
        underlying_price=402.0,  # Small +2 move
        implied_vol=0.25,
        risk_free_rate=0.05
    )

    # Actual P&L change
    actual_pnl_change = mtm_day2 - mtm_day1

    # Attributed P&L
    attributed_pnl = trade.pnl_attribution['total_attributed']

    # Should be reasonably close for small moves
    error = abs(actual_pnl_change - attributed_pnl)
    error_pct = error / abs(actual_pnl_change) if actual_pnl_change != 0 else 0

    # Allow up to 20% error (we're using first-order Greeks only)
    assert error_pct < 0.20, \
        f"Attribution error {error_pct:.1%} too high (actual={actual_pnl_change:.2f}, attributed={attributed_pnl:.2f})"

    print(f"✅ Attribution accuracy within tolerance (error: {error_pct:.1%})")


def test_greeks_update_on_exit():
    """
    EDGE CASE: Verify Greeks calculated at exit for final attribution.
    """
    trade = create_straddle_trade(
        trade_id="TEST_005",
        profile_name="TestProfile",
        entry_date=datetime(2024, 1, 1),
        strike=400.0,
        expiry=datetime(2024, 2, 1),
        dte=30,
        entry_prices={0: 10.0, 1: 10.0}
    )

    # Mark to market for 3 days
    for day in range(3):
        trade.mark_to_market(
            current_prices={0: 10.0, 1: 10.0},
            current_date=datetime(2024, 1, 1) + timedelta(days=day),
            underlying_price=400.0,
            implied_vol=0.25,
            risk_free_rate=0.05
        )

    # Close the trade
    trade.close(
        exit_date=datetime(2024, 1, 4),
        exit_prices={0: 9.0, 1: 9.0},
        reason="Test exit"
    )

    # Verify Greeks history includes all days held
    assert len(trade.greeks_history) == 3, "Should have 3 days of Greeks history"

    # Verify is_open = False
    assert not trade.is_open

    # Verify mark_to_market returns realized P&L after close
    final_mtm = trade.mark_to_market(
        current_prices={0: 9.0, 1: 9.0},
        current_date=datetime(2024, 1, 5),
        underlying_price=400.0,
        implied_vol=0.25
    )
    assert final_mtm == trade.realized_pnl, "After close, MTM should return realized P&L"

    print("✅ Greeks history complete at exit")


# ==============================================================================
# Run Tests
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("TESTING BUG FIXES: Timing (Bug 1) + Greeks Updates (Bug 2)")
    print("=" * 80)
    print()

    print("Bug 1: Same-Day Entry Timing Tests")
    print("-" * 80)
    test_entry_signal_uses_only_current_day_data()
    test_trade_executed_at_t_plus_1()
    test_no_same_day_execution()
    print()

    print("Bug 2: Greeks Update Tests")
    print("-" * 80)
    test_greeks_updated_during_mark_to_market()
    test_greeks_history_tracked()
    test_pnl_attribution_calculated()
    test_greeks_update_in_simulator_integration()
    test_greeks_attribution_accuracy()
    test_greeks_update_on_exit()
    print()

    print("=" * 80)
    print("ALL TESTS PASSED ✅")
    print("=" * 80)
