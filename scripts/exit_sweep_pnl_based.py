#!/usr/bin/env python3
"""
EXIT SWEEP - PNL-BASED RULE TESTING

Test simple exit rules on existing trades:
- Family A: Fixed hold times (2, 3, 5, 7, 10 days)
- Family B: Trailing stops (activation + trail size)

Compare to BASELINE (current 14-day exits)

NOT optimization - just see which simple patterns improve capture rate.
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import json
import numpy as np
import pandas as pd
from pathlib import Path

# Load current results (baseline)
results_file = 'data/backtest_results/full_2020-2024/results.json'
with open(results_file) as f:
    all_results = json.load(f)

print("=" * 80)
print("EXIT SWEEP - TESTING SIMPLE EXIT RULES")
print("=" * 80)
print()
print("Baseline: Current exits (14-day time stop)")
print("Testing: Fixed hold times + Trailing stops")
print()

# BASELINE METRICS
baseline_total_pnl = 0
baseline_total_peak = 0
baseline_trades = 0

for profile_id, data in all_results.items():
    baseline_total_pnl += data['summary']['total_pnl']
    baseline_total_peak += data['summary']['peak_potential']
    baseline_trades += data['summary']['total_trades']

print("BASELINE (Current Exits):")
print(f"  Total P&L: ${baseline_total_pnl:,.0f}")
print(f"  Peak Potential: ${baseline_total_peak:,.0f}")
print(f"  Capture Rate: {baseline_total_pnl/baseline_total_peak*100:.1f}%")
print(f"  Total Trades: {baseline_trades}")
print()

# FAMILY A: FIXED HOLD TIMES
print("=" * 80)
print("FAMILY A: FIXED HOLD TIMES")
print("=" * 80)
print()

fixed_day_results = []

for exit_day in [2, 3, 5, 7, 10]:
    total_pnl = 0
    total_peak = 0
    win_count = 0
    total_count = 0
    total_days_held = 0
    peak_pct_captured = []

    # Apply to all trades
    for profile_id, data in all_results.items():
        for trade in data['trades']:
            path = trade.get('path', [])
            if not path:
                continue

            # Find peak
            peak_pnl = max(day['mtm_pnl'] for day in path)

            # Exit at specified day or last day
            exit_idx = min(exit_day, len(path) - 1)
            exit_pnl = path[exit_idx]['mtm_pnl']

            total_pnl += exit_pnl
            total_peak += peak_pnl
            total_count += 1
            total_days_held += path[exit_idx]['day']

            if exit_pnl > 0:
                win_count += 1

            if peak_pnl > 0:
                pct_captured = (exit_pnl / peak_pnl) * 100
                peak_pct_captured.append(pct_captured)

    avg_pnl = total_pnl / total_count if total_count > 0 else 0
    win_rate = win_count / total_count * 100 if total_count > 0 else 0
    avg_days = total_days_held / total_count if total_count > 0 else 0
    capture_rate = total_pnl / total_peak * 100 if total_peak > 0 else 0
    avg_peak_pct = np.mean(peak_pct_captured) if peak_pct_captured else 0

    delta_pnl = total_pnl - baseline_total_pnl
    delta_win_rate = win_rate - (win_count / total_count * 100)  # TODO: Calculate baseline win rate

    fixed_day_results.append({
        'rule': f'Exit Day {exit_day}',
        'total_pnl': total_pnl,
        'avg_pnl': avg_pnl,
        'win_rate': win_rate,
        'avg_days': avg_days,
        'capture_rate': capture_rate,
        'avg_peak_pct': avg_peak_pct,
        'delta_pnl': delta_pnl
    })

# Display Family A results
print(f"{'Rule':<15} {'Total P&L':>12} {'Avg P&L':>10} {'Win Rate':>10} {'Avg Days':>10} {'Capture %':>10} {'Δ from Base':>12}")
print("-" * 95)

for result in fixed_day_results:
    print(f"{result['rule']:<15} ${result['total_pnl']:>11,.0f} ${result['avg_pnl']:>9,.0f} "
          f"{result['win_rate']:>9.1f}% {result['avg_days']:>9.1f} {result['capture_rate']:>9.1f}% "
          f"${result['delta_pnl']:>11,.0f}")

print(f"{'Baseline':<15} ${baseline_total_pnl:>11,.0f} {'':>10} {'':>10} {'14.0':>10} "
      f"{baseline_total_pnl/baseline_total_peak*100:>9.1f}% {'$0':>12}")

# FAMILY B: TRAILING STOPS
print()
print("=" * 80)
print("FAMILY B: TRAILING STOPS")
print("=" * 80)
print()

trailing_results = []

for activation_k in [150, 300, 500]:
    for trail_d in [100, 200, 300]:

        total_pnl = 0
        total_peak = 0
        total_count = 0
        win_count = 0
        total_days_held = 0
        peak_pct_captured = []

        for profile_id, data in all_results.items():
            for trade in data['trades']:
                path = trade.get('path', [])
                if not path:
                    continue

                # Find peak
                peak_pnl = max(day['mtm_pnl'] for day in path)

                # Trailing stop logic
                activated = False
                running_peak = -999999
                exit_idx = len(path) - 1  # Default: last day

                for idx, day in enumerate(path):
                    pnl = day['mtm_pnl']

                    # Activation
                    if pnl >= activation_k:
                        activated = True

                    if activated:
                        running_peak = max(running_peak, pnl)

                        # Trail stop triggered?
                        if pnl <= running_peak - trail_d:
                            exit_idx = idx
                            break

                exit_pnl = path[exit_idx]['mtm_pnl']

                total_pnl += exit_pnl
                total_peak += peak_pnl
                total_count += 1
                total_days_held += path[exit_idx]['day']

                if exit_pnl > 0:
                    win_count += 1

                if peak_pnl > 0:
                    pct_captured = (exit_pnl / peak_pnl) * 100
                    peak_pct_captured.append(pct_captured)

        avg_pnl = total_pnl / total_count if total_count > 0 else 0
        win_rate = win_count / total_count * 100 if total_count > 0 else 0
        avg_days = total_days_held / total_count if total_count > 0 else 0
        capture_rate = total_pnl / total_peak * 100 if total_peak > 0 else 0

        delta_pnl = total_pnl - baseline_total_pnl

        trailing_results.append({
            'rule': f'K={activation_k} D={trail_d}',
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'win_rate': win_rate,
            'avg_days': avg_days,
            'capture_rate': capture_rate,
            'delta_pnl': delta_pnl
        })

# Display Family B results
print(f"{'Rule':<15} {'Total P&L':>12} {'Avg P&L':>10} {'Win Rate':>10} {'Avg Days':>10} {'Capture %':>10} {'Δ from Base':>12}")
print("-" * 95)

for result in trailing_results:
    print(f"{result['rule']:<15} ${result['total_pnl']:>11,.0f} ${result['avg_pnl']:>9,.0f} "
          f"{result['win_rate']:>9.1f}% {result['avg_days']:>9.1f} {result['capture_rate']:>9.1f}% "
          f"${result['delta_pnl']:>11,.0f}")

print(f"{'Baseline':<15} ${baseline_total_pnl:>11,.0f} {'':>10} {'':>10} {'14.0':>10} "
      f"{baseline_total_pnl/baseline_total_peak*100:>9.1f}% {'$0':>12}")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()

# Find best rule
all_rules = fixed_day_results + trailing_results
best_rule = max(all_rules, key=lambda r: r['total_pnl'])

print(f"Best performing rule: {best_rule['rule']}")
print(f"  Total P&L: ${best_rule['total_pnl']:,.0f} (vs ${baseline_total_pnl:,.0f} baseline)")
print(f"  Improvement: ${best_rule['delta_pnl']:,.0f}")
print(f"  Capture rate: {best_rule['capture_rate']:.1f}%")
print()

if best_rule['delta_pnl'] > 10000:
    print("✓ Significant improvement found - implement this exit rule")
elif best_rule['delta_pnl'] > 5000:
    print("✓ Moderate improvement - consider implementing")
else:
    print("⚠️  Marginal improvement - current exits may be near-optimal")

print()
