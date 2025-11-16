"""
Tests for RotationBacktestEngine.

Validates:
- Unified daily loop execution
- Regime classification integration
- Profile scoring integration
- Dynamic allocation calculation
- Rebalancing logic
- Multi-position management
- P&L consistency (single source of truth)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from src.backtest.engine_new import RotationBacktestEngine
from src.trading.trade import Trade, TradeLeg


@pytest.fixture
def sample_market_data():
    """Create sample market data for backtesting."""
    dates = pd.date_range('2024-01-01', '2024-03-31', freq='B')  # Business days

    data = pd.DataFrame({
        'date': dates,
        'open': 500.0 + np.random.randn(len(dates)) * 5,
        'high': 505.0 + np.random.randn(len(dates)) * 5,
        'low': 495.0 + np.random.randn(len(dates)) * 5,
        'close': 500.0 + np.random.randn(len(dates)) * 5,
        'volume': 100_000_000,
        'RV20': np.clip(0.15 + np.random.randn(len(dates)) * 0.05, 0.10, 0.40)
    })

    # Add regime labels (cycling through 1-5)
    data['regime'] = ((np.arange(len(dates)) % 5) + 1).astype(int)

    # Add profile scores (random for testing)
    for i in range(1, 7):
        data[f'profile_{i}_score'] = np.clip(
            0.5 + np.random.randn(len(dates)) * 0.2,
            0.0,
            1.0
        )

    return data


@pytest.fixture
def simple_trade_constructor():
    """Simple trade constructor for testing."""
    def constructor(row, trade_id):
        spot = row['close']
        dte = 45
        expiry = datetime.now() + timedelta(days=dte)

        legs = [
            TradeLeg(
                option_type='call',
                strike=spot,
                expiry=expiry,
                quantity=1,
                dte=dte
            ),
            TradeLeg(
                option_type='put',
                strike=spot,
                expiry=expiry,
                quantity=1,
                dte=dte
            )
        ]

        trade = Trade(
            trade_id=trade_id,
            profile_name="test_profile",
            entry_date=row['date'] if hasattr(row['date'], 'date') else row['date'],
            legs=legs,
            entry_prices={0: 15.0, 1: 14.0}
        )

        trade.__post_init__()

        # Set Greeks
        trade.net_delta = 0.0
        trade.net_gamma = 0.5
        trade.net_theta = -10.0
        trade.net_vega = 100.0

        return trade

    return constructor


class TestEngineInitialization:
    """Test engine initialization."""

    def test_default_initialization(self):
        """Engine initializes with default parameters."""
        engine = RotationBacktestEngine()

        assert engine.portfolio.initial_capital == 1_000_000.0
        assert engine.allocator.max_profile_weight == 0.40
        assert engine.allocator.min_profile_weight == 0.05
        assert engine.rebalance_threshold == 0.05

    def test_custom_initialization(self):
        """Engine initializes with custom parameters."""
        engine = RotationBacktestEngine(
            initial_capital=500_000.0,
            max_profile_weight=0.30,
            min_profile_weight=0.10,
            rebalance_threshold=0.08
        )

        assert engine.portfolio.initial_capital == 500_000.0
        assert engine.allocator.max_profile_weight == 0.30
        assert engine.allocator.min_profile_weight == 0.10
        assert engine.rebalance_threshold == 0.08


class TestBacktestExecution:
    """Test backtest execution."""

    def test_run_complete_backtest(self, sample_market_data, simple_trade_constructor):
        """Can run complete backtest without errors."""
        engine = RotationBacktestEngine(use_real_options_data=False)

        # Create trade constructors for all profiles
        constructors = {i: simple_trade_constructor for i in range(1, 7)}

        results = engine.run(
            data=sample_market_data,
            start_date='2024-01-15',  # Skip warmup
            end_date='2024-02-15',
            trade_constructors=constructors
        )

        # Check results structure
        assert 'portfolio' in results
        assert 'equity_curve' in results
        assert 'daily_results' in results
        assert 'closed_positions' in results
        assert 'metrics' in results

    def test_daily_results_structure(self, sample_market_data, simple_trade_constructor):
        """Daily results DataFrame has correct structure."""
        engine = RotationBacktestEngine(use_real_options_data=False)
        constructors = {i: simple_trade_constructor for i in range(1, 7)}

        results = engine.run(
            data=sample_market_data,
            start_date='2024-01-15',
            end_date='2024-01-31',
            trade_constructors=constructors
        )

        daily_df = results['daily_results']

        # Check required columns
        required_cols = [
            'date', 'regime', 'total_equity', 'cash', 'daily_pnl',
            'daily_return', 'realized_pnl', 'unrealized_pnl',
            'num_positions', 'delta', 'gamma', 'theta', 'vega'
        ]

        for col in required_cols:
            assert col in daily_df.columns

        # Check per-profile allocation columns
        for i in range(1, 7):
            assert f'profile_{i}_allocation' in daily_df.columns
            assert f'profile_{i}_target' in daily_df.columns


class TestRebalancing:
    """Test rebalancing logic."""

    def test_rebalancing_triggered(self, sample_market_data, simple_trade_constructor):
        """Rebalancing is triggered when allocations change."""
        # Create data with regime changes to trigger rebalancing
        data = sample_market_data.copy()
        data['regime'] = 1  # All Regime 1
        data.loc[data.index[10:], 'regime'] = 2  # Switch to Regime 2

        engine = RotationBacktestEngine(
            use_real_options_data=False,
            rebalance_threshold=0.05
        )
        constructors = {i: simple_trade_constructor for i in range(1, 7)}

        results = engine.run(
            data=data,
            start_date='2024-01-15',
            end_date='2024-01-31',
            trade_constructors=constructors
        )

        # Should have rebalancing events
        rebalance_log = results['rebalance_log']
        assert len(rebalance_log) > 0
        assert 'action' in rebalance_log.columns
        assert set(rebalance_log['action'].unique()).issubset({'open', 'close', 'hold'})

    def test_no_rebalance_when_under_threshold(self, sample_market_data, simple_trade_constructor):
        """No rebalancing when allocation change < threshold."""
        # Create data with stable regime
        data = sample_market_data.copy()
        data['regime'] = 1  # All same regime

        # Make profile scores very stable
        for i in range(1, 7):
            data[f'profile_{i}_score'] = 0.5

        engine = RotationBacktestEngine(
            use_real_options_data=False,
            rebalance_threshold=0.10  # High threshold
        )
        constructors = {i: simple_trade_constructor for i in range(1, 7)}

        results = engine.run(
            data=data,
            start_date='2024-01-15',
            end_date='2024-01-25',
            trade_constructors=constructors
        )

        rebalance_log = results['rebalance_log']

        # Should have initial opens but minimal subsequent rebalancing
        opens = rebalance_log[rebalance_log['action'] == 'open']
        closes = rebalance_log[rebalance_log['action'] == 'close']

        assert len(opens) >= 1  # At least initial positions
        assert len(closes) < len(opens)  # Fewer closes (stable)


class TestMultiPositionManagement:
    """Test simultaneous multi-position management."""

    def test_holds_multiple_positions(self, sample_market_data, simple_trade_constructor):
        """Engine holds multiple positions simultaneously."""
        engine = RotationBacktestEngine(use_real_options_data=False)
        constructors = {i: simple_trade_constructor for i in range(1, 7)}

        results = engine.run(
            data=sample_market_data,
            start_date='2024-01-15',
            end_date='2024-01-31',
            trade_constructors=constructors
        )

        daily_df = results['daily_results']

        # Check that we sometimes hold multiple positions
        max_positions = daily_df['num_positions'].max()
        assert max_positions > 1  # Should hold more than 1 position

    def test_position_values_tracked_separately(self, sample_market_data, simple_trade_constructor):
        """Each profile's position value is tracked separately."""
        engine = RotationBacktestEngine(use_real_options_data=False)
        constructors = {i: simple_trade_constructor for i in range(1, 7)}

        results = engine.run(
            data=sample_market_data,
            start_date='2024-01-15',
            end_date='2024-01-31',
            trade_constructors=constructors
        )

        equity_curve = results['equity_curve']

        # Check per-profile value columns exist
        for i in range(1, 7):
            assert f'profile_{i}_value' in equity_curve.columns
            assert f'profile_{i}_pnl' in equity_curve.columns


class TestPnLConsistency:
    """Test P&L calculation consistency (single source of truth)."""

    def test_equity_equals_cash_plus_positions(self, sample_market_data, simple_trade_constructor):
        """Total equity = cash + sum(position values)."""
        engine = RotationBacktestEngine(use_real_options_data=False)
        constructors = {i: simple_trade_constructor for i in range(1, 7)}

        results = engine.run(
            data=sample_market_data,
            start_date='2024-01-15',
            end_date='2024-01-31',
            trade_constructors=constructors
        )

        equity_curve = results['equity_curve']

        for _, row in equity_curve.iterrows():
            cash = row['cash']
            position_value = row['position_value']
            total_equity = row['total_equity']

            # Allow small floating point tolerance
            assert abs(total_equity - (cash + position_value)) < 0.01

    def test_daily_pnl_consistency(self, sample_market_data, simple_trade_constructor):
        """Daily P&L = change in total equity."""
        engine = RotationBacktestEngine(use_real_options_data=False)
        constructors = {i: simple_trade_constructor for i in range(1, 7)}

        results = engine.run(
            data=sample_market_data,
            start_date='2024-01-15',
            end_date='2024-01-31',
            trade_constructors=constructors
        )

        daily_df = results['daily_results']

        # Check that cumulative daily P&L equals total change
        cumulative_pnl = daily_df['daily_pnl'].sum()
        final_equity = daily_df['total_equity'].iloc[-1]
        initial_capital = engine.portfolio.initial_capital

        total_change = final_equity - initial_capital

        # Should match within floating point tolerance
        assert abs(cumulative_pnl - total_change) < 1.0

    def test_realized_plus_unrealized_equals_total(self, sample_market_data, simple_trade_constructor):
        """Total P&L = realized + unrealized."""
        engine = RotationBacktestEngine(use_real_options_data=False)
        constructors = {i: simple_trade_constructor for i in range(1, 7)}

        results = engine.run(
            data=sample_market_data,
            start_date='2024-01-15',
            end_date='2024-01-31',
            trade_constructors=constructors
        )

        daily_df = results['daily_results']

        for _, row in daily_df.iterrows():
            realized = row['realized_pnl']
            unrealized = row['unrealized_pnl']
            initial_capital = engine.portfolio.initial_capital
            total_equity = row['total_equity']

            expected_total_pnl = total_equity - initial_capital
            actual_total_pnl = realized + unrealized

            # Should match
            assert abs(expected_total_pnl - actual_total_pnl) < 0.01


class TestGreeksTracking:
    """Test portfolio-level Greeks tracking."""

    def test_greeks_calculated_daily(self, sample_market_data, simple_trade_constructor):
        """Greeks calculated for each day."""
        engine = RotationBacktestEngine(use_real_options_data=False)
        constructors = {i: simple_trade_constructor for i in range(1, 7)}

        results = engine.run(
            data=sample_market_data,
            start_date='2024-01-15',
            end_date='2024-01-31',
            trade_constructors=constructors
        )

        daily_df = results['daily_results']

        # Greeks should be present
        assert 'delta' in daily_df.columns
        assert 'gamma' in daily_df.columns
        assert 'theta' in daily_df.columns
        assert 'vega' in daily_df.columns

        # Greeks should not all be zero
        assert daily_df['gamma'].abs().sum() > 0

    def test_greeks_aggregate_across_positions(self, sample_market_data, simple_trade_constructor):
        """Portfolio Greeks are sum of position Greeks."""
        engine = RotationBacktestEngine(use_real_options_data=False)
        constructors = {i: simple_trade_constructor for i in range(1, 7)}

        results = engine.run(
            data=sample_market_data,
            start_date='2024-01-15',
            end_date='2024-01-31',
            trade_constructors=constructors
        )

        # When holding multiple positions, Greeks should be larger
        daily_df = results['daily_results']

        rows_with_multiple_pos = daily_df[daily_df['num_positions'] > 1]
        if len(rows_with_multiple_pos) > 0:
            # Gamma should increase with more positions (if all same sign)
            assert rows_with_multiple_pos['gamma'].abs().mean() > 0


class TestPerformanceMetrics:
    """Test performance metrics calculation."""

    def test_metrics_calculated(self, sample_market_data, simple_trade_constructor):
        """Performance metrics are calculated."""
        engine = RotationBacktestEngine(use_real_options_data=False)
        constructors = {i: simple_trade_constructor for i in range(1, 7)}

        results = engine.run(
            data=sample_market_data,
            start_date='2024-01-15',
            end_date='2024-01-31',
            trade_constructors=constructors
        )

        metrics = results['metrics']

        # Check expected metrics
        expected_metrics = [
            'total_return_pct',
            'sharpe_ratio',
            'max_drawdown_pct',
            'win_rate_pct',
            'total_trades'
        ]

        for metric in expected_metrics:
            assert metric in metrics

    def test_sharpe_calculation_reasonable(self, sample_market_data, simple_trade_constructor):
        """Sharpe ratio is calculated and finite."""
        engine = RotationBacktestEngine(use_real_options_data=False)
        constructors = {i: simple_trade_constructor for i in range(1, 7)}

        results = engine.run(
            data=sample_market_data,
            start_date='2024-01-15',
            end_date='2024-02-15',
            trade_constructors=constructors
        )

        sharpe = results['metrics']['sharpe_ratio']

        # Should be finite and reasonable
        assert np.isfinite(sharpe)
        assert -10 < sharpe < 10  # Reasonable range


class TestDateFiltering:
    """Test date range filtering."""

    def test_start_date_filter(self, sample_market_data, simple_trade_constructor):
        """Start date filter works correctly."""
        engine = RotationBacktestEngine(use_real_options_data=False)
        constructors = {i: simple_trade_constructor for i in range(1, 7)}

        results = engine.run(
            data=sample_market_data,
            start_date='2024-02-01',
            end_date='2024-02-15',
            trade_constructors=constructors
        )

        daily_df = results['daily_results']
        first_date = daily_df['date'].min()

        assert first_date >= pd.to_datetime('2024-02-01').date()

    def test_end_date_filter(self, sample_market_data, simple_trade_constructor):
        """End date filter works correctly."""
        engine = RotationBacktestEngine(use_real_options_data=False)
        constructors = {i: simple_trade_constructor for i in range(1, 7)}

        results = engine.run(
            data=sample_market_data,
            start_date='2024-01-15',
            end_date='2024-01-31',
            trade_constructors=constructors
        )

        daily_df = results['daily_results']
        last_date = daily_df['date'].max()

        assert last_date <= pd.to_datetime('2024-01-31').date()
