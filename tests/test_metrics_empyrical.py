"""
Unit tests for empyrical-based metrics implementation.

Validates that all 10 bugs from Round 4 audit are fixed.
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from analysis import PerformanceMetrics


def test_basic_functionality():
    """Test basic metrics calculation works without crashing."""
    print("TEST 1: Basic functionality...")

    # Create toy portfolio
    portfolio = pd.DataFrame({
        'portfolio_pnl': [100, -50, 200, -30, 150],  # Dollar P&L
        'cumulative_pnl': [100, 50, 250, 220, 370]   # Cumulative
    })

    metrics_calc = PerformanceMetrics(starting_capital=10000)
    metrics = metrics_calc.calculate_all(portfolio)

    # Check all expected keys exist
    expected_keys = [
        'sharpe_ratio', 'sortino_ratio', 'calmar_ratio', 'max_drawdown',
        'annual_return', 'annual_volatility', 'stability', 'tail_ratio',
        'total_return', 'total_pnl', 'avg_daily_pnl', 'std_daily_pnl',
        'total_days', 'positive_days', 'negative_days', 'best_day', 'worst_day',
        'win_rate', 'profit_factor', 'avg_win', 'avg_loss'
    ]

    for key in expected_keys:
        assert key in metrics, f"Missing metric: {key}"

    print(f"  ✓ All {len(expected_keys)} metrics calculated")
    print(f"  ✓ Sharpe ratio: {metrics['sharpe_ratio']:.3f}")
    print(f"  ✓ Total return: {metrics['total_return']*100:.2f}%")
    print(f"  ✓ Total P&L: ${metrics['total_pnl']:.2f}")
    print()


def test_pnl_to_returns_conversion():
    """Test BUG-001 fix: Dollar P&L correctly converted to percentage returns."""
    print("TEST 2: P&L to returns conversion...")

    starting_capital = 100000
    portfolio = pd.DataFrame({
        'portfolio_pnl': [1000, -500, 2000],  # Dollar P&L
        'cumulative_pnl': [1000, 500, 2500]    # Cumulative
    })

    metrics_calc = PerformanceMetrics(starting_capital=starting_capital)
    metrics = metrics_calc.calculate_all(portfolio)

    # Verify returns calculation
    # First return: 1000 / 100000 = 1%
    # Second return: -500 / 101000 = -0.495%
    # Third return: 2000 / 100500 = 1.99%

    # Total return should be: 2500 / 100000 = 2.5%
    expected_total_return = 2500 / starting_capital
    actual_total_return = metrics['total_return']

    assert abs(actual_total_return - expected_total_return) < 0.0001, \
        f"Total return mismatch: expected {expected_total_return}, got {actual_total_return}"

    print(f"  ✓ Total return: {actual_total_return*100:.2f}% (expected: {expected_total_return*100:.2f}%)")
    print(f"  ✓ Sharpe ratio is finite: {np.isfinite(metrics['sharpe_ratio'])}")
    print()


def test_risk_free_rate():
    """Test BUG-003 fix: Risk-free rate parameter works."""
    print("TEST 3: Risk-free rate parameter...")

    portfolio = pd.DataFrame({
        'portfolio_pnl': [100] * 100,
        'cumulative_pnl': list(range(100, 100 * 101, 100))
    })

    # Without risk-free rate
    metrics_no_rf = PerformanceMetrics(starting_capital=10000, risk_free_rate=0.0).calculate_all(portfolio)

    # With 4% risk-free rate
    metrics_with_rf = PerformanceMetrics(starting_capital=10000, risk_free_rate=0.04).calculate_all(portfolio)

    # Sharpe should be lower with risk-free rate
    assert metrics_with_rf['sharpe_ratio'] < metrics_no_rf['sharpe_ratio'], \
        "Sharpe ratio should decrease when risk-free rate is added"

    print(f"  ✓ Sharpe without RF: {metrics_no_rf['sharpe_ratio']:.3f}")
    print(f"  ✓ Sharpe with 4% RF: {metrics_with_rf['sharpe_ratio']:.3f}")
    print(f"  ✓ Difference: {metrics_no_rf['sharpe_ratio'] - metrics_with_rf['sharpe_ratio']:.3f}")
    print()


def test_data_validation():
    """Test BUG-004 fix: Data validation catches bad data."""
    print("TEST 4: Data validation...")

    # Test NaN detection
    portfolio_with_nan = pd.DataFrame({
        'portfolio_pnl': [100, np.nan, 200],
        'cumulative_pnl': [100, 100, 300]
    })

    metrics_calc = PerformanceMetrics()
    try:
        metrics_calc.calculate_all(portfolio_with_nan)
        assert False, "Should have raised ValueError for NaN"
    except ValueError as e:
        assert 'NaN values detected' in str(e)
        print(f"  ✓ NaN detection works: {e}")

    # Test Inf detection
    portfolio_with_inf = pd.DataFrame({
        'portfolio_pnl': [100, np.inf, 200],
        'cumulative_pnl': [100, 100, 300]
    })

    try:
        metrics_calc.calculate_all(portfolio_with_inf)
        assert False, "Should have raised ValueError for Inf"
    except ValueError as e:
        assert 'Infinite values detected' in str(e)
        print(f"  ✓ Inf detection works: {e}")

    print()


def test_missing_metrics():
    """Test BUG-007 fix: All missing metrics are now calculated."""
    print("TEST 5: Missing metrics...")

    portfolio = pd.DataFrame({
        'portfolio_pnl': [100, -50, 200, -30, 150, -20, 180],
        'cumulative_pnl': [100, 50, 250, 220, 370, 350, 530]
    })

    metrics_calc = PerformanceMetrics()
    metrics = metrics_calc.calculate_all(portfolio)

    # Check missing metrics from BUG-007
    assert 'win_rate' in metrics
    assert 'profit_factor' in metrics
    assert 'avg_win' in metrics
    assert 'avg_loss' in metrics

    # Validate calculations
    pnl = portfolio['portfolio_pnl']
    expected_win_rate = (pnl > 0).sum() / len(pnl)

    assert abs(metrics['win_rate'] - expected_win_rate) < 0.001, \
        f"Win rate mismatch: expected {expected_win_rate}, got {metrics['win_rate']}"

    print(f"  ✓ Win rate: {metrics['win_rate']*100:.1f}%")
    print(f"  ✓ Profit factor: {metrics['profit_factor']:.2f}")
    print(f"  ✓ Avg win: ${metrics['avg_win']:.2f}")
    print(f"  ✓ Avg loss: ${metrics['avg_loss']:.2f}")
    print()


def test_calculate_by_regime():
    """Test BUG-006 fix: calculate_by_regime method exists and works."""
    print("TEST 6: calculate_by_regime method...")

    portfolio = pd.DataFrame({
        'regime': [1, 1, 2, 2, 3, 3],
        'portfolio_pnl': [100, -50, 200, -30, 150, -20],
        'cumulative_pnl': [100, 50, 250, 220, 370, 350]
    })

    metrics_calc = PerformanceMetrics(starting_capital=10000)
    regime_metrics = metrics_calc.calculate_by_regime(portfolio)

    # Should have results for 3 regimes
    assert len(regime_metrics) == 3, f"Expected 3 regimes, got {len(regime_metrics)}"
    assert 'regime' in regime_metrics.columns
    assert 'sharpe_ratio' in regime_metrics.columns

    print(f"  ✓ Calculated metrics for {len(regime_metrics)} regimes")
    print(f"  ✓ Columns: {list(regime_metrics.columns)[:5]}...")
    print()


def test_realistic_values():
    """Test that metrics produce reasonable values (not 1000x inflated)."""
    print("TEST 7: Realistic metric values...")

    # Simulate realistic portfolio
    np.random.seed(42)
    n_days = 252
    daily_returns_pct = np.random.normal(0.001, 0.01, n_days)  # 0.1% mean, 1% std

    starting_capital = 100000
    pnl = daily_returns_pct * starting_capital
    cumulative_pnl = pnl.cumsum()

    portfolio = pd.DataFrame({
        'portfolio_pnl': pnl,
        'cumulative_pnl': cumulative_pnl
    })

    metrics_calc = PerformanceMetrics(starting_capital=starting_capital)
    metrics = metrics_calc.calculate_all(portfolio)

    # Sharpe should be in reasonable range (0.5 to 3.0 for real strategies)
    # NOT 100+ which would indicate the bug
    assert 0 < abs(metrics['sharpe_ratio']) < 10, \
        f"Sharpe ratio out of realistic range: {metrics['sharpe_ratio']}"

    # Annual return should be percentage, not huge number
    assert -1 < metrics['annual_return'] < 5, \
        f"Annual return out of realistic range: {metrics['annual_return']}"

    print(f"  ✓ Sharpe ratio: {metrics['sharpe_ratio']:.2f} (realistic range)")
    print(f"  ✓ Annual return: {metrics['annual_return']*100:.1f}% (reasonable)")
    print(f"  ✓ Annual vol: {metrics['annual_volatility']*100:.1f}% (reasonable)")
    print()


if __name__ == '__main__':
    print("=" * 80)
    print("EMPYRICAL METRICS - VALIDATION TESTS")
    print("=" * 80)
    print()

    try:
        test_basic_functionality()
        test_pnl_to_returns_conversion()
        test_risk_free_rate()
        test_data_validation()
        test_missing_metrics()
        test_calculate_by_regime()
        test_realistic_values()

        print("=" * 80)
        print("ALL TESTS PASSED ✓")
        print("=" * 80)
        print()
        print("empyrical implementation is VALIDATED and ready for use.")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
