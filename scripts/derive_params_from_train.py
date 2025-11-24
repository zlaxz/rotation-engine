#!/usr/bin/env python3
"""
Derive Exit Parameters from TRAIN Period Distribution

METHODOLOGY:
- Use TRAIN period (2020-2021) ONLY
- Analyze peak P&L distribution for each profile
- Derive TP2 from 75th PERCENTILE (not optimization)
- Derive max_loss from worst 10% of trades
- Skip TP1 (can't scale with 1 contract)

This is STATISTICAL FITTING, not optimization.
Percentiles should generalize to validation period.
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import json
import numpy as np
from datetime import datetime
from pathlib import Path

# Configuration
TRAIN_START = datetime(2020, 1, 1).date()
TRAIN_END = datetime(2021, 12, 31).date()

# Load tracked trades from full backtest
results_file = 'data/backtest_results/full_2020-2024/results.json'
if not Path(results_file).exists():
    print(f"ERROR: {results_file} not found")
    sys.exit(1)

with open(results_file) as f:
    all_results = json.load(f)

print("=" * 80)
print("PARAMETER DERIVATION FROM TRAIN PERIOD DISTRIBUTION")
print("=" * 80)
print(f"Train Period: {TRAIN_START} to {TRAIN_END}")
print(f"Data Source: {results_file}")
print()

# Analyze each profile
derived_params = {}

for profile_id, profile_data in all_results.items():
    print(f"\n{profile_id}")
    print("-" * 60)

    # Extract trades list
    trades = profile_data.get('trades', [])
    print(f"  Total trades in dataset: {len(trades)}")

    # Filter to train period only
    train_trades = []
    for trade_data in trades:
        entry_info = trade_data.get('entry', {})
        entry_date_str = entry_info.get('entry_date')
        if not entry_date_str:
            continue

        # Parse date
        entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()

        # Filter to train period
        if TRAIN_START <= entry_date <= TRAIN_END:
            train_trades.append(trade_data)

    print(f"  Trades in TRAIN period: {len(train_trades)}")

    if len(train_trades) < 3:
        print(f"  ⚠️  WARNING: Only {len(train_trades)} trades in train period")
        print(f"     Using industry defaults")
        derived_params[profile_id] = {
            'max_loss_pct': -0.50,
            'tp1_pct': None,
            'tp2_pct': 1.00,
            'max_hold_days': 14,
            'source': 'industry_default (insufficient train data)'
        }
        continue

    # Analyze peak distribution
    peak_pcts = []
    worst_pcts = []
    peak_days = []

    for trade_data in train_trades:
        daily_path = trade_data.get('path', [])
        entry_cost = trade_data['entry'].get('entry_cost')

        if not daily_path or not entry_cost or abs(entry_cost) < 0.01:
            continue

        # Find peak P&L and day
        peak_pnl = -999999
        peak_day_idx = 0
        worst_pnl = 999999

        for day in daily_path:
            pnl = day['mtm_pnl']
            if pnl > peak_pnl:
                peak_pnl = pnl
                peak_day_idx = day['day']
            if pnl < worst_pnl:
                worst_pnl = pnl

        # Calculate percentages
        peak_pct = peak_pnl / abs(entry_cost)
        worst_pct = worst_pnl / abs(entry_cost)

        peak_pcts.append(peak_pct)
        worst_pcts.append(worst_pct)
        peak_days.append(peak_day_idx)

    # Calculate percentiles
    if len(peak_pcts) > 0:
        p25_peak = np.percentile(peak_pcts, 25)
        p50_peak = np.percentile(peak_pcts, 50)  # Median
        p75_peak = np.percentile(peak_pcts, 75)
        p90_peak = np.percentile(peak_pcts, 90)

        worst_10pct = np.percentile(worst_pcts, 10)
        median_peak_day = int(np.median(peak_days))

        print(f"\n  Peak P&L Distribution (Train Period):")
        print(f"    25th percentile: {p25_peak:>7.1%}")
        print(f"    50th percentile: {p50_peak:>7.1%} (median)")
        print(f"    75th percentile: {p75_peak:>7.1%}")
        print(f"    90th percentile: {p90_peak:>7.1%}")
        print(f"  Median peak day: {median_peak_day}")
        print(f"  Worst 10% drawdown: {worst_10pct:>7.1%}")

        # DERIVE PARAMETERS (Statistical, not optimized)

        # TP2: Use 75th percentile
        # Rationale: Should capture top 25% of trades
        # This is CONSERVATIVE - not using 90th (would overfit)
        tp2 = round(p75_peak, 2)

        # Alternative: Could use 50th percentile (even more conservative)
        # tp2 = round(p50_peak, 2)

        # Max loss: Use worst 10% + safety buffer
        # Don't go below -50% (too risky for options)
        max_loss = round(worst_10pct * 1.1, 2)  # 10% buffer
        max_loss = max(max_loss, -0.50)  # Cap at -50%

        # Max hold: Use median peak day + buffer
        max_hold = max(median_peak_day + 3, 14)  # At least 14 days

        print(f"\n  DERIVED PARAMETERS:")
        print(f"    TP1: None (single contract)")
        print(f"    TP2 (75th %ile): {tp2:>7.1%}")
        print(f"    Max Loss (10th %ile): {max_loss:>7.1%}")
        print(f"    Max Hold Days: {max_hold}")

        derived_params[profile_id] = {
            'max_loss_pct': max_loss,
            'tp1_pct': None,  # Skip TP1 for 1 contract
            'tp2_pct': tp2,   # Exit all at TP2 (75th percentile)
            'max_hold_days': max_hold,
            'source': 'train_distribution',
            'stats': {
                'train_trades': len(train_trades),
                'median_peak_pct': round(p50_peak, 3),
                'p75_peak_pct': round(p75_peak, 3),
                'median_peak_day': median_peak_day,
                'worst_10pct': round(worst_10pct, 3)
            }
        }
    else:
        print(f"  ERROR: No valid trades to derive from")
        derived_params[profile_id] = {
            'max_loss_pct': -0.50,
            'tp1_pct': None,
            'tp2_pct': 1.00,
            'max_hold_days': 14,
            'source': 'default (no valid train data)'
        }

# Save derived parameters
output_file = 'config/train_derived_params.json'
Path('config').mkdir(exist_ok=True)

with open(output_file, 'w') as f:
    json.dump(derived_params, f, indent=2)

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"\nDerived parameters saved to: {output_file}")
print()
print("Methodology:")
print("  - TP1: DISABLED (can't scale with 1 contract)")
print("  - TP2: 75th percentile of peak P&L in TRAIN period (2020-2021)")
print("  - Max Loss: Worst 10% of trades + 10% safety buffer")
print("  - Max Hold: Median peak day + 3 day buffer (min 14)")
print()
print("This is STATISTICAL derivation, NOT optimization:")
print("  - Uses percentiles (stable statistics)")
print("  - Conservative (75th, not 90th percentile)")
print("  - Derived ONLY on train period")
print("  - Should generalize to validation period")
print()
print("Next Steps:")
print("  1. Review derived parameters")
print("  2. Update Exit Engine V1 with these parameters")
print("  3. Test on TRAIN period (confirm profitable)")
print("  4. Test on VALIDATION period (expect 20-40% degradation)")
print("  5. If validation passes → Test on TEST period (2024)")
