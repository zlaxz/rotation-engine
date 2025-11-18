#!/usr/bin/env python3
"""
Apply Exit Engine V1 to Existing Train/Validation Results

Takes the tracked trade data from train and validation periods and applies
Exit Engine V1 logic to determine actual exits (vs 14-day tracking).

This shows what P&L would have been with intelligent exits instead of
fixed time-based exits.

Usage:
    python scripts/apply_exit_engine_v1.py
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import json
import pandas as pd
from pathlib import Path

from src.trading.exit_engine_v1 import ExitEngineV1


def apply_exit_engine_to_results(results_file: Path, period_name: str):
    """
    Apply Exit Engine V1 to tracked results.

    Args:
        results_file: Path to results.json from train or validation
        period_name: 'train' or 'validation' for output naming
    """
    print(f"\n{'='*80}")
    print(f"APPLYING EXIT ENGINE V1 TO {period_name.upper()} RESULTS")
    print(f"{'='*80}\n")

    # Load tracked results
    with open(results_file, 'r') as f:
        results = json.load(f)

    # Initialize Exit Engine V1
    exit_engine = ExitEngineV1()
    exit_engine.reset_tp1_tracking()

    # Process each profile
    all_exit_results = {}

    for profile_id, profile_data in results.items():
        if profile_data['summary']['total_trades'] == 0:
            print(f"{profile_id}: No trades\n")
            continue

        print(f"{profile_id} - {profile_data['config']['name']}")
        print(f"  Original trades: {profile_data['summary']['total_trades']}")
        print(f"  Original P&L (14-day track): ${profile_data['summary']['total_pnl']:.0f}")

        # Apply Exit Engine V1 to each trade
        trade_exits = []
        total_pnl_v1 = 0.0

        for trade in profile_data['trades']:
            # Apply Exit Engine V1
            exit_info = exit_engine.apply_to_tracked_trade(profile_id, trade)

            trade_exits.append({
                'entry_date': trade['entry']['entry_date'],
                'exit_day': exit_info['exit_day'],
                'exit_reason': exit_info['exit_reason'],
                'exit_pnl': exit_info['exit_pnl'],
                'pnl_pct': exit_info['pnl_pct'],
                'original_pnl': trade['exit']['final_pnl']
            })

            total_pnl_v1 += exit_info['exit_pnl']

        # Calculate improvement (FIXED: guard division by zero)
        original_pnl = profile_data['summary']['total_pnl']
        improvement = total_pnl_v1 - original_pnl

        if abs(original_pnl) < 0.01:
            improvement_pct = 0
        else:
            improvement_pct = (improvement / abs(original_pnl) * 100)

        print(f"  Exit Engine V1 P&L: ${total_pnl_v1:.0f}")
        print(f"  Improvement: ${improvement:.0f} ({improvement_pct:+.1f}%)")

        # Count exit reasons
        exit_reasons = {}
        for te in trade_exits:
            reason = te['exit_reason']
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        print(f"  Exit reasons: {dict(exit_reasons)}")
        print()

        all_exit_results[profile_id] = {
            'original_pnl': original_pnl,
            'exit_engine_v1_pnl': total_pnl_v1,
            'improvement': improvement,
            'trade_count': len(trade_exits),
            'trades': trade_exits,
            'exit_reasons': exit_reasons
        }

    # Summary
    print(f"{'='*80}")
    print(f"{period_name.upper()} SUMMARY - EXIT ENGINE V1")
    print(f"{'='*80}")

    total_original = sum(r['original_pnl'] for r in all_exit_results.values())
    total_v1 = sum(r['exit_engine_v1_pnl'] for r in all_exit_results.values())
    total_improvement = total_v1 - total_original

    print(f"Original P&L (14-day tracking): ${total_original:.0f}")
    print(f"Exit Engine V1 P&L: ${total_v1:.0f}")
    print(f"Improvement: ${total_improvement:.0f}")
    print(f"{'='*80}\n")

    return all_exit_results


def main():
    """Apply Exit Engine V1 to train and validation results"""

    # Process train results
    train_file = Path('/Users/zstoc/rotation-engine/data/backtest_results/train_2020-2021/results.json')
    if train_file.exists():
        train_results = apply_exit_engine_to_results(train_file, 'train')
    else:
        print("Train results not found - run backtest_train.py first")
        return

    # FIXED BUG-007: Reset TP1 state between periods (prevent contamination)
    # Create fresh exit engine for validation to avoid TP1 state leakage
    print("\n⚠️  Resetting Exit Engine state for validation period (prevents TP1 contamination)\n")

    # Process validation results
    val_file = Path('/Users/zstoc/rotation-engine/data/backtest_results/validation_2022-2023/results.json')
    if val_file.exists():
        val_results = apply_exit_engine_to_results(val_file, 'validation')
    else:
        print("Validation results not found - run backtest_validation.py first")
        return

    # Compare train vs validation with Exit Engine V1
    print(f"\n{'='*80}")
    print("TRAIN vs VALIDATION COMPARISON (EXIT ENGINE V1)")
    print(f"{'='*80}\n")

    print(f"{'Profile':<15} {'Train P&L':>12} {'Val P&L':>12} {'Degradation':>15}")
    print('-'*80)

    for profile_id in train_results.keys():
        train_pnl = train_results[profile_id]['exit_engine_v1_pnl']
        val_pnl = val_results.get(profile_id, {}).get('exit_engine_v1_pnl', 0)

        # FIXED: Guard division by zero
        if abs(train_pnl) < 0.01:
            degradation = 0
        else:
            degradation = (val_pnl - train_pnl) / abs(train_pnl) * 100

        print(f"{profile_id:<15} ${train_pnl:>10.0f} ${val_pnl:>10.0f} {degradation:>13.1f}%")

    train_total = sum(r['exit_engine_v1_pnl'] for r in train_results.values())
    val_total = sum(r['exit_engine_v1_pnl'] for r in val_results.values())
    total_deg = (val_total - train_total) / abs(train_total) * 100 if train_total != 0 else 0

    print('-'*80)
    print(f"{'TOTAL':<15} ${train_total:>10.0f} ${val_total:>10.0f} {total_deg:>13.1f}%")
    print(f"{'='*80}\n")

    # Save results
    output_dir = Path('/Users/zstoc/rotation-engine/data/backtest_results')
    output_file = output_dir / 'exit_engine_v1_analysis.json'

    combined_results = {
        'train': train_results,
        'validation': val_results,
        'summary': {
            'train_total_pnl': train_total,
            'validation_total_pnl': val_total,
            'degradation_pct': total_deg
        }
    }

    with open(output_file, 'w') as f:
        json.dump(combined_results, f, indent=2, default=str)

    print(f"✅ Saved: {output_file}\n")


if __name__ == '__main__':
    main()
