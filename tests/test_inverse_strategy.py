"""
Inverse Strategy Test

Hypothesis: The allocation strategy is backwards.

Test: What if we INVERT the allocation weights?
- Profiles with low scores → HIGH weight
- Profiles with high scores → LOW weight

If the inverse strategy performs BETTER, this proves the scoring/allocation logic is inverted.
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from backtest import RotationEngine
from analysis import PerformanceMetrics


def run_inverse_strategy_test():
    """Test inverse allocation strategy."""

    print("=" * 80)
    print("INVERSE STRATEGY TEST")
    print("=" * 80)
    print()

    # Run normal strategy
    print("Running NORMAL strategy...")
    engine_normal = RotationEngine(
        max_profile_weight=0.40,
        min_profile_weight=0.05,
        vix_scale_threshold=30.0,
        vix_scale_factor=0.5
    )

    results_normal = engine_normal.run(start_date='2020-01-01', end_date='2024-12-31')
    portfolio_normal = results_normal['portfolio']

    metrics_calc = PerformanceMetrics()
    metrics_normal = metrics_calc.calculate_all(portfolio_normal)

    print(f"\nNormal Strategy Results:")
    print(f"  Total P&L:    ${metrics_normal['total_return']:>10,.2f}")
    print(f"  Sharpe Ratio: {metrics_normal['sharpe_ratio']:>10.2f}")
    print(f"  Max Drawdown: ${metrics_normal['max_drawdown']:>10,.2f}")

    # Extract allocations
    allocations_normal = results_normal['allocations']

    # Invert the weights
    print("\n" + "=" * 80)
    print("Creating INVERSE allocations...")
    print("=" * 80)

    weight_cols = [col for col in allocations_normal.columns if col.endswith('_weight')]

    # Create inverted allocations
    allocations_inverse = allocations_normal.copy()

    # Method 1: Invert each weight (max - weight)
    # This flips high weights to low and vice versa
    for weight_col in weight_cols:
        max_weight = allocations_normal[weight_col].max()
        allocations_inverse[weight_col] = max_weight - allocations_normal[weight_col]

    # Renormalize to sum to 1.0
    weight_sum = allocations_inverse[weight_cols].sum(axis=1)
    for weight_col in weight_cols:
        allocations_inverse[weight_col] = allocations_inverse[weight_col] / weight_sum

    # Handle any NaN (if weight_sum was 0)
    allocations_inverse[weight_cols] = allocations_inverse[weight_cols].fillna(0)

    print("\nComparison of allocations:")
    print("\nNormal Strategy (average weights):")
    for col in weight_cols:
        print(f"  {col:20s}: {allocations_normal[col].mean():>6.1%}")

    print("\nInverse Strategy (average weights):")
    for col in weight_cols:
        print(f"  {col:20s}: {allocations_inverse[col].mean():>6.1%}")

    # Now compute inverse portfolio P&L
    print("\n" + "=" * 80)
    print("Computing INVERSE portfolio P&L...")
    print("=" * 80)

    # Get profile results (individual profile P&L)
    profile_results = results_normal['profile_results']

    # Rebuild portfolio using inverse weights
    portfolio_inverse = allocations_inverse[['date', 'regime']].copy()

    # For each profile, multiply inverse weight by profile P&L
    for profile_name in ['profile_1', 'profile_2', 'profile_3', 'profile_4', 'profile_5', 'profile_6']:
        weight_col = f"{profile_name}_weight"
        pnl_col = f"{profile_name}_pnl"

        if profile_name not in profile_results:
            continue

        # Merge profile P&L
        profile_pnl = profile_results[profile_name][['date', 'daily_pnl']].rename(columns={'daily_pnl': pnl_col})
        portfolio_inverse = portfolio_inverse.merge(profile_pnl, on='date', how='left')

        # Weighted P&L
        portfolio_inverse[pnl_col] = portfolio_inverse[pnl_col].fillna(0) * allocations_inverse[weight_col]

    # Calculate total portfolio P&L
    pnl_cols = [col for col in portfolio_inverse.columns if col.endswith('_pnl')]
    portfolio_inverse['portfolio_pnl'] = portfolio_inverse[pnl_cols].sum(axis=1)
    portfolio_inverse['cumulative_pnl'] = portfolio_inverse['portfolio_pnl'].cumsum()

    # Add weights to inverse portfolio
    for weight_col in weight_cols:
        portfolio_inverse[weight_col] = allocations_inverse[weight_col]

    # Calculate inverse metrics
    metrics_inverse = metrics_calc.calculate_all(portfolio_inverse)

    print(f"\nInverse Strategy Results:")
    print(f"  Total P&L:    ${metrics_inverse['total_return']:>10,.2f}")
    print(f"  Sharpe Ratio: {metrics_inverse['sharpe_ratio']:>10.2f}")
    print(f"  Max Drawdown: ${metrics_inverse['max_drawdown']:>10,.2f}")

    # Comparison
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)

    print(f"\n{'Metric':<20s} {'Normal':>15s} {'Inverse':>15s} {'Difference':>15s}")
    print("-" * 70)
    print(f"{'Total P&L':<20s} ${metrics_normal['total_return']:>14,.2f} ${metrics_inverse['total_return']:>14,.2f} ${metrics_inverse['total_return'] - metrics_normal['total_return']:>14,.2f}")
    print(f"{'Sharpe Ratio':<20s} {metrics_normal['sharpe_ratio']:>15.2f} {metrics_inverse['sharpe_ratio']:>15.2f} {metrics_inverse['sharpe_ratio'] - metrics_normal['sharpe_ratio']:>15.2f}")
    print(f"{'Sortino Ratio':<20s} {metrics_normal['sortino_ratio']:>15.2f} {metrics_inverse['sortino_ratio']:>15.2f} {metrics_inverse['sortino_ratio'] - metrics_normal['sortino_ratio']:>15.2f}")
    print(f"{'Max Drawdown':<20s} ${metrics_normal['max_drawdown']:>14,.2f} ${metrics_inverse['max_drawdown']:>14,.2f} ${metrics_inverse['max_drawdown'] - metrics_normal['max_drawdown']:>14,.2f}")
    print(f"{'Win Rate':<20s} {metrics_normal['win_rate']*100:>14.1f}% {metrics_inverse['win_rate']*100:>14.1f}% {(metrics_inverse['win_rate'] - metrics_normal['win_rate'])*100:>14.1f}%")
    print(f"{'Profit Factor':<20s} {metrics_normal['profit_factor']:>15.2f} {metrics_inverse['profit_factor']:>15.2f} {metrics_inverse['profit_factor'] - metrics_normal['profit_factor']:>15.2f}")

    # Verdict
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    pnl_improvement = metrics_inverse['total_return'] - metrics_normal['total_return']
    sharpe_improvement = metrics_inverse['sharpe_ratio'] - metrics_normal['sharpe_ratio']

    if pnl_improvement > 0 and sharpe_improvement > 0:
        print("\n✅ INVERSE STRATEGY PERFORMS BETTER")
        print("\nThis proves the allocation logic is BACKWARDS.")
        print("Fix: Invert the scoring or allocation logic.")
        print(f"\nImprovement: ${pnl_improvement:,.2f} P&L, {sharpe_improvement:+.2f} Sharpe")
    elif abs(pnl_improvement) < 100 and abs(sharpe_improvement) < 0.5:
        print("\n⚠️ INVERSE STRATEGY PERFORMS SIMILARLY")
        print("\nNeither normal nor inverse has strong edge.")
        print("Issue: Allocation strategy doesn't matter - profiles themselves may be random.")
    else:
        print("\n❌ NORMAL STRATEGY PERFORMS BETTER")
        print("\nAllocation logic is correct direction.")
        print("Issue: Individual profiles have negative edge (not allocation).")

    # Save results
    print("\nSaving inverse portfolio results...")
    portfolio_inverse.to_csv('inverse_portfolio.csv', index=False)
    print("  Saved: inverse_portfolio.csv")

    return {
        'normal': metrics_normal,
        'inverse': metrics_inverse,
        'portfolio_normal': portfolio_normal,
        'portfolio_inverse': portfolio_inverse
    }


if __name__ == '__main__':
    results = run_inverse_strategy_test()
