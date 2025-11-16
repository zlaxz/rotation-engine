"""
Example usage of the Rotation Engine.

This script demonstrates how to:
1. Initialize the rotation engine
2. Run a backtest
3. Access results
4. Generate visualizations
"""

import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from backtest import RotationEngine
from analysis import PerformanceMetrics, PortfolioVisualizer


def main():
    """Run example rotation engine backtest."""

    print("=" * 80)
    print("ROTATION ENGINE - EXAMPLE USAGE")
    print("=" * 80)
    print()

    # Step 1: Initialize engine with custom parameters
    print("Step 1: Initializing rotation engine...")
    engine = RotationEngine(
        max_profile_weight=0.40,   # Max 40% per profile
        min_profile_weight=0.05,   # Ignore <5% allocations
        vix_scale_threshold=30.0,  # Scale down when RV20 > 30%
        vix_scale_factor=0.5       # Scale to 50% exposure
    )
    print("  Engine initialized with custom parameters")

    # Step 2: Run backtest
    print("\nStep 2: Running backtest (2020-2024)...")
    results = engine.run(
        start_date='2020-01-01',
        end_date='2024-12-31'
    )
    print("  Backtest complete!")

    # Step 3: Access results
    print("\nStep 3: Accessing results...")

    # Portfolio P&L
    portfolio = results['portfolio']
    print(f"\n  Portfolio Summary:")
    print(f"    Total days: {len(portfolio)}")
    print(f"    Final P&L: ${portfolio['cumulative_pnl'].iloc[-1]:,.2f}")
    print(f"    Date range: {portfolio['date'].min()} to {portfolio['date'].max()}")

    # Allocations
    allocations = results['allocations']
    print(f"\n  Allocations:")
    print(f"    Total allocation days: {len(allocations)}")
    weight_cols = [col for col in allocations.columns if col.endswith('_weight')]
    print(f"    Weight columns: {len(weight_cols)}")

    # Attribution
    attribution_profile = results['attribution_by_profile']
    print(f"\n  Top 3 Profiles by P&L:")
    top3 = attribution_profile.nlargest(3, 'total_pnl')
    for _, row in top3.iterrows():
        print(f"    {row['profile']}: ${row['total_pnl']:,.2f}")

    attribution_regime = results['attribution_by_regime']
    print(f"\n  Best Regime by P&L:")
    best_regime = attribution_regime.nlargest(1, 'total_pnl').iloc[0]
    print(f"    Regime {int(best_regime['regime'])}: ${best_regime['total_pnl']:,.2f} ({int(best_regime['days'])} days)")

    # Rotation metrics
    rotation_metrics = results['rotation_metrics']
    print(f"\n  Rotation Activity:")
    print(f"    Total rotations: {rotation_metrics['total_rotations']}")
    print(f"    Avg days between: {rotation_metrics['avg_days_between']:.1f}")
    print(f"    Rotation rate: {rotation_metrics['rotation_rate_pct']:.1f}%")

    # Step 4: Calculate performance metrics
    print("\nStep 4: Calculating performance metrics...")
    metrics_calc = PerformanceMetrics()
    metrics = metrics_calc.calculate_all(portfolio)

    print(f"\n  Performance Metrics:")
    print(f"    Sharpe Ratio:    {metrics['sharpe_ratio']:>8.2f}")
    print(f"    Sortino Ratio:   {metrics['sortino_ratio']:>8.2f}")
    print(f"    Calmar Ratio:    {metrics['calmar_ratio']:>8.2f}")
    print(f"    Max Drawdown:    ${metrics['max_drawdown']:>8,.2f}")
    print(f"    Win Rate:        {metrics['win_rate']*100:>8.2f}%")
    print(f"    Profit Factor:   {metrics['profit_factor']:>8.2f}")

    # Step 5: Generate visualizations
    print("\nStep 5: Generating visualizations...")
    viz = PortfolioVisualizer()
    viz.plot_all(results, save_path='.')
    print("  Visualizations saved to current directory")

    # Step 6: Export results to CSV (optional)
    print("\nStep 6: Exporting results to CSV...")
    portfolio.to_csv('portfolio_results.csv', index=False)
    allocations.to_csv('allocations.csv', index=False)
    attribution_profile.to_csv('attribution_by_profile.csv', index=False)
    attribution_regime.to_csv('attribution_by_regime.csv', index=False)
    print("  Results exported to CSV files")

    print("\n" + "=" * 80)
    print("EXAMPLE COMPLETE")
    print("=" * 80)
    print()
    print("Generated files:")
    print("  - portfolio_results.csv")
    print("  - allocations.csv")
    print("  - attribution_by_profile.csv")
    print("  - attribution_by_regime.csv")
    print("  - portfolio_pnl.png")
    print("  - allocation_heatmap.png")
    print("  - attribution.png")
    print("  - regime_distribution.png")


if __name__ == '__main__':
    main()
