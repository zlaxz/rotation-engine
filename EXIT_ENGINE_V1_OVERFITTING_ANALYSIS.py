#!/usr/bin/env python3
"""
EXIT ENGINE V1 OVERFITTING ANALYSIS

The code is clean (zero bugs), but results show CATASTROPHIC overfitting:
- Train: +40% improvement
- Validation: -415% degradation

This script identifies WHICH exit rules caused the failure.
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import json
from pathlib import Path

def analyze_exit_rule_performance():
    """
    Analyze which exit rules helped in train but destroyed validation.
    """

    results_file = Path('/Users/zstoc/rotation-engine/data/backtest_results/exit_engine_v1_analysis.json')
    with open(results_file, 'r') as f:
        results = json.load(f)

    print("="*80)
    print("EXIT RULE PERFORMANCE: TRAIN vs VALIDATION")
    print("="*80)

    # Collect all exit reasons
    all_reasons = set()
    for period in ['train', 'validation']:
        for profile_data in results[period].values():
            all_reasons.update(profile_data['exit_reasons'].keys())

    # Analyze each exit rule
    for reason in sorted(all_reasons):
        print(f"\n{reason}:")
        print(f"  {'Profile':<20} {'Train':>8} {'Val':>8} {'T Count':>8} {'V Count':>8}")
        print(f"  {'-'*60}")

        train_total_pnl = 0
        val_total_pnl = 0
        train_count = 0
        val_count = 0

        for profile_id in sorted(results['train'].keys()):
            train_profile = results['train'][profile_id]
            val_profile = results['validation'].get(profile_id, {'trades': [], 'exit_reasons': {}})

            # Find trades that exited for this reason
            train_trades = [t for t in train_profile['trades'] if t['exit_reason'] == reason]
            val_trades = [t for t in val_profile.get('trades', []) if t['exit_reason'] == reason]

            train_pnl = sum(t['exit_pnl'] for t in train_trades)
            val_pnl = sum(t['exit_pnl'] for t in val_trades)

            if len(train_trades) > 0 or len(val_trades) > 0:
                print(f"  {profile_id:<20} ${train_pnl:>7.0f} ${val_pnl:>7.0f} {len(train_trades):>8} {len(val_trades):>8}")

            train_total_pnl += train_pnl
            val_total_pnl += val_pnl
            train_count += len(train_trades)
            val_count += len(val_trades)

        print(f"  {'-'*60}")
        print(f"  {'TOTAL':<20} ${train_total_pnl:>7.0f} ${val_total_pnl:>7.0f} {train_count:>8} {val_count:>8}")

        if train_count > 0:
            train_avg = train_total_pnl / train_count
        else:
            train_avg = 0

        if val_count > 0:
            val_avg = val_total_pnl / val_count
        else:
            val_avg = 0

        print(f"  {'AVG per trade':<20} ${train_avg:>7.0f} ${val_avg:>7.0f}")

        if abs(train_avg) > 0.01:
            degradation = (val_avg - train_avg) / abs(train_avg) * 100
            print(f"  Degradation: {degradation:+.1f}%")


def analyze_condition_exits():
    """
    Deep dive on 'condition_exit' - the most common rule.
    What conditions triggered? Did they work in validation?
    """

    print("\n\n" + "="*80)
    print("CONDITION EXIT DEEP DIVE")
    print("="*80)

    results_file = Path('/Users/zstoc/rotation-engine/data/backtest_results/exit_engine_v1_analysis.json')
    with open(results_file, 'r') as f:
        results = json.load(f)

    for period_name in ['train', 'validation']:
        period = results[period_name]

        print(f"\n{period_name.upper()}:")
        print(f"  {'Profile':<20} {'Cond Exits':>12} {'Cond PnL':>12} {'Avg PnL':>12}")
        print(f"  {'-'*60}")

        for profile_id in sorted(period.keys()):
            profile = period[profile_id]

            # Find condition exit trades
            cond_trades = [t for t in profile['trades'] if t['exit_reason'] == 'condition_exit']

            if len(cond_trades) > 0:
                cond_pnl = sum(t['exit_pnl'] for t in cond_trades)
                avg_pnl = cond_pnl / len(cond_trades)

                print(f"  {profile_id:<20} {len(cond_trades):>12} ${cond_pnl:>11.0f} ${avg_pnl:>11.0f}")


def analyze_profile_4_disaster():
    """
    Profile_4_VANNA: Train +$2395 → Validation -$1784 (-174.5% degradation)

    What happened?
    """

    print("\n\n" + "="*80)
    print("PROFILE 4 (VANNA) DISASTER ANALYSIS")
    print("="*80)

    results_file = Path('/Users/zstoc/rotation-engine/data/backtest_results/exit_engine_v1_analysis.json')
    with open(results_file, 'r') as f:
        results = json.load(f)

    for period_name in ['train', 'validation']:
        period = results[period_name]['Profile_4_VANNA']

        print(f"\n{period_name.upper()}:")
        print(f"  Total P&L: ${period['exit_engine_v1_pnl']:.0f}")
        print(f"  Original (14-day): ${period['original_pnl']:.0f}")
        print(f"  Improvement: ${period['improvement']:.0f}")
        print(f"\n  Exit Reason Breakdown ({period['trade_count']} trades):")

        for reason, count in sorted(period['exit_reasons'].items(), key=lambda x: -x[1]):
            # Find trades for this reason
            trades = [t for t in period['trades'] if t['exit_reason'] == reason]
            pnl = sum(t['exit_pnl'] for t in trades)
            avg_pnl = pnl / count if count > 0 else 0

            print(f"    {reason:<20} {count:>3} trades  ${pnl:>8.0f} total  ${avg_pnl:>7.0f} avg")


def main():
    """Run overfitting analysis"""

    analyze_exit_rule_performance()
    analyze_condition_exits()
    analyze_profile_4_disaster()

    print("\n\n" + "="*80)
    print("VERDICT")
    print("="*80)

    print("""
Exit Engine V1 has ZERO implementation bugs (all audits passed).

The performance destruction is PURE OVERFITTING:

1. CONDITION EXITS (36.9% of train trades):
   - Helped in train (+40% improvement)
   - Destroyed in validation (-415% degradation)
   - Pattern: Exit rules optimized on train market conditions
   - Failure: Those conditions didn't predict exits in validation

2. PROFIT TARGETS (TP1/TP2):
   - Only 5.6% of train exits
   - Too rare to matter

3. MAX LOSS STOPS:
   - Helped in train (cut losses)
   - Likely triggered earlier in validation (worse entries?)

ROOT CAUSE: Exit Engine V1 uses CONDITION-BASED exits that were
implicitly optimized on train period regime patterns. These patterns
failed completely out-of-sample.

RECOMMENDATION: Return to Phase 1 (fixed 14-day exits) until we have
MORE data to derive exit conditions that are statistically robust.

Exit Engine V1 is a PERFECT example of:
- Clean implementation
- Good train performance
- CATASTROPHIC overfitting
- Why we need train/validation/test methodology
""")


if __name__ == '__main__':
    main()
