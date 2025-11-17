"""
Day 6 Validation: Complete rotation engine backtest

Success criteria:
- Rotation engine runs full 2020-2024 without crashes
- Can break down P&L by profile and regime
- Allocation weights sum to ≤1.0 (respecting constraints)
- Weights look reasonable (not all in one profile constantly)
- Portfolio metrics calculated correctly
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path
import matplotlib.pyplot as plt

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from backtest import RotationEngine
from analysis import PerformanceMetrics, PortfolioVisualizer


def validate_day6():
    """Validate Day 6: Complete rotation engine."""

    print("=" * 80)
    print("DAY 6 VALIDATION: Complete Rotation Engine")
    print("=" * 80)
    print()

    # Step 1: Initialize engine
    print("Step 1: Initializing rotation engine...")
    try:
        engine = RotationEngine(
            max_profile_weight=0.40,
            min_profile_weight=0.05,
            vix_scale_threshold=30.0,
            vix_scale_factor=0.5
        )
        print("  ✅ Engine initialized")
    except Exception as e:
        print(f"  ❌ Failed to initialize engine: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 2: Run backtest
    print("\nStep 2: Running rotation engine backtest (2020-2024)...")
    try:
        results = engine.run(start_date='2020-01-01', end_date='2024-12-31')
        print("  ✅ Backtest completed successfully")
    except Exception as e:
        print(f"  ❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 3: Validate portfolio structure
    print("\nStep 3: Validating portfolio structure...")
    portfolio = results['portfolio']

    required_cols = ['date', 'regime', 'portfolio_pnl', 'cumulative_pnl']
    missing_cols = [col for col in required_cols if col not in portfolio.columns]
    if missing_cols:
        print(f"  ❌ Missing columns: {missing_cols}")
        return False

    print(f"  ✅ Portfolio has {len(portfolio)} days")
    print(f"  ✅ Date range: {portfolio['date'].min()} to {portfolio['date'].max()}")

    # Step 4: Validate allocation weights
    print("\nStep 4: Validating allocation weights...")
    weight_cols = [col for col in portfolio.columns if col.endswith('_weight')]

    # Check weights sum to ≤1.0
    weight_sums = portfolio[weight_cols].sum(axis=1)
    max_weight_sum = weight_sums.max()
    min_weight_sum = weight_sums.min()

    print(f"  Weight sum range: {min_weight_sum:.3f} to {max_weight_sum:.3f}")

    if max_weight_sum > 1.01:  # Allow small numerical error
        print(f"  ⚠️ WARNING: Weights exceed 1.0 (max: {max_weight_sum:.3f})")
    else:
        print(f"  ✅ Weights properly normalized (max: {max_weight_sum:.3f})")

    # Check individual weight constraints
    for weight_col in weight_cols:
        max_weight = portfolio[weight_col].max()
        if max_weight > 0.41:  # Allow small numerical error above 40%
            print(f"  ⚠️ WARNING: {weight_col} exceeds 40% (max: {max_weight:.1%})")
        else:
            print(f"  ✅ {weight_col} respects max constraint (max: {max_weight:.1%})")

    # Step 5: Validate P&L structure
    print("\nStep 5: Validating P&L structure...")

    pnl_cols = [col for col in portfolio.columns if col.endswith('_pnl') and col not in ['portfolio_pnl', 'cumulative_pnl']]
    print(f"  Found {len(pnl_cols)} profile P&L columns")

    # Check for NaN
    total_nans = portfolio[pnl_cols + ['portfolio_pnl']].isna().sum().sum()
    if total_nans > 0:
        print(f"  ⚠️ WARNING: {total_nans} NaN values in P&L")
    else:
        print(f"  ✅ No NaN values in P&L")

    # Check P&L aggregation
    manual_pnl_sum = portfolio[pnl_cols].sum(axis=1)
    portfolio_pnl = portfolio['portfolio_pnl']
    pnl_diff = (manual_pnl_sum - portfolio_pnl).abs().max()

    if pnl_diff > 0.01:
        print(f"  ⚠️ WARNING: P&L aggregation mismatch (max diff: ${pnl_diff:.2f})")
    else:
        print(f"  ✅ P&L properly aggregated (max diff: ${pnl_diff:.4f})")

    # Step 6: Calculate performance metrics
    print("\nStep 6: Calculating performance metrics...")
    try:
        metrics_calc = PerformanceMetrics()
        metrics = metrics_calc.calculate_all(portfolio)

        print("\n  Portfolio Performance:")
        print(f"    Total P&L:      ${metrics['total_return']:>12,.2f}")
        print(f"    Sharpe Ratio:   {metrics['sharpe_ratio']:>12.2f}")
        print(f"    Sortino Ratio:  {metrics['sortino_ratio']:>12.2f}")
        print(f"    Calmar Ratio:   {metrics['calmar_ratio']:>12.2f}")
        print(f"    Max Drawdown:   ${metrics['max_drawdown']:>12,.2f}")
        print(f"    Max DD %:       {metrics['max_drawdown_pct']*100:>12.2f}%")
        print(f"    Win Rate:       {metrics['win_rate']*100:>12.2f}%")
        print(f"    Profit Factor:  {metrics['profit_factor']:>12.2f}")
        print(f"    Avg Daily P&L:  ${metrics['avg_daily_pnl']:>12,.2f}")

        print("\n  ✅ Metrics calculated successfully")

    except Exception as e:
        print(f"  ❌ Metrics calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 7: Validate attribution
    print("\nStep 7: Validating attribution...")

    attribution_profile = results['attribution_by_profile']
    attribution_regime = results['attribution_by_regime']

    print("\n  Attribution by Profile:")
    for _, row in attribution_profile.iterrows():
        print(f"    {row['profile']:12s}: ${row['total_pnl']:>10,.2f} ({row['pnl_contribution_pct']:>6.1f}%)")

    print("\n  Attribution by Regime:")
    for _, row in attribution_regime.iterrows():
        print(f"    Regime {int(row['regime'])}: {int(row['days']):>4d} days, ${row['total_pnl']:>10,.2f} (avg: ${row['mean_daily_pnl']:>7,.2f}/day)")

    # Step 8: Validate rotation metrics
    print("\nStep 8: Validating rotation metrics...")
    rotation_metrics = results['rotation_metrics']

    print(f"  Total rotations:         {rotation_metrics['total_rotations']}")
    print(f"  Avg days between:        {rotation_metrics['avg_days_between']:.1f}")
    print(f"  Rotation rate:           {rotation_metrics['rotation_rate_pct']:.1f}%")

    if rotation_metrics['total_rotations'] == 0:
        print("  ⚠️ WARNING: No rotations detected (static allocation)")
    else:
        print("  ✅ Rotation logic active")

    # Step 9: Check for concentration risk
    print("\nStep 9: Checking for concentration risk...")

    # Calculate average weights
    avg_weights = portfolio[weight_cols].mean()

    print(f"  Average weights:")
    for col in weight_cols:
        print(f"    {col:20s}: {avg_weights[col]:>6.1%}")

    if len(avg_weights) > 0:
        max_avg_weight = avg_weights.max()
        if max_avg_weight > 0:
            profile_with_max = avg_weights.idxmax()
            if max_avg_weight > 0.50:
                print(f"  ⚠️ WARNING: High concentration in {profile_with_max} (avg: {max_avg_weight:.1%})")
            else:
                print(f"  ✅ Reasonable diversification (max avg weight: {max_avg_weight:.1%})")
        else:
            print(f"  ⚠️ All average weights are zero")
    else:
        print(f"  ⚠️ No weight columns found")

    # Step 10: Generate visualizations
    print("\nStep 10: Generating visualizations...")
    try:
        viz = PortfolioVisualizer()
        viz.plot_all(results, save_path='.')

        print("  ✅ Visualizations generated:")
        print("    - portfolio_pnl.png")
        print("    - allocation_heatmap.png")
        print("    - attribution.png")
        print("    - regime_distribution.png")

    except Exception as e:
        print(f"  ⚠️ Visualization failed (non-critical): {e}")

    # Final validation summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    checks = {
        "Engine initialization": True,
        "Backtest completion": True,
        "Portfolio structure": len(missing_cols) == 0,
        "Weight constraints": max_weight_sum <= 1.01,
        "P&L aggregation": pnl_diff < 0.01,
        "Metrics calculation": True,
        "Rotation active": rotation_metrics['total_rotations'] > 0
    }

    all_passed = all(checks.values())

    for check, passed in checks.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10s} {check}")

    print("=" * 80)

    if all_passed:
        print("\n🎉 ALL VALIDATION CHECKS PASSED")
        print("\nRotation engine is working correctly!")
        print(f"Portfolio generated ${metrics['total_return']:,.2f} over {len(portfolio)} days")
        print(f"Sharpe: {metrics['sharpe_ratio']:.2f}, Max DD: ${metrics['max_drawdown']:,.2f}")
    else:
        print("\n⚠️ SOME VALIDATION CHECKS FAILED")
        print("Review warnings above.")

    return all_passed


if __name__ == '__main__':
    success = validate_day6()
    sys.exit(0 if success else 1)
