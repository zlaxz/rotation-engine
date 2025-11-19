#!/usr/bin/env python3
"""
Quick Test: Do Bug Fixes Solve the Capture Rate Problem?

Tests Exit Engine V1 with bug fixes on existing tracked trades.
If capture rate improves significantly → bug fixes worked
If still terrible → need to re-derive parameters

Expected:
- Before fixes: 0.3% capture rate
- After fixes: Should be 5-15% capture rate minimum
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import json
import glob
from pathlib import Path
from src.trading.exit_engine_v1 import ExitEngineV1

# Load tracked trades
tracked_trades_pattern = '/Users/zstoc/rotation-engine/data/backtest_results/tracked_trades_*.json'
tracked_files = sorted(glob.glob(tracked_trades_pattern))

if not tracked_files:
    print("ERROR: No tracked trades found")
    print(f"Looking for: {tracked_trades_pattern}")
    sys.exit(1)

print(f"Found {len(tracked_files)} tracked trade files")
print()

# Initialize exit engine with bug fixes
exit_engine = ExitEngineV1()
exit_engine.reset_tp1_tracking()

# Process all tracked trades
results_by_profile = {}
total_max_potential = 0
total_captured = 0

for file_path in tracked_files:
    with open(file_path) as f:
        tracked_data = json.load(f)

    profile_id = tracked_data['profile_id']

    if profile_id not in results_by_profile:
        results_by_profile[profile_id] = {
            'trades': 0,
            'max_potential': 0,
            'captured': 0,
            'capture_rate': 0
        }

    # Get max potential (peak P&L in 14-day window)
    daily_path = tracked_data['path']
    if not daily_path:
        continue

    max_pnl = max(day['mtm_pnl'] for day in daily_path)

    # Apply Exit Engine V1 (with bug fixes!)
    exit_result = exit_engine.apply_to_tracked_trade(profile_id, tracked_data)
    captured_pnl = exit_result['exit_pnl']
    exit_day = exit_result['exit_day']
    exit_reason = exit_result['exit_reason']

    # Track results
    results_by_profile[profile_id]['trades'] += 1
    results_by_profile[profile_id]['max_potential'] += max_pnl
    results_by_profile[profile_id]['captured'] += captured_pnl

    total_max_potential += max_pnl
    total_captured += captured_pnl

# Calculate capture rates
for profile_id, stats in results_by_profile.items():
    if stats['max_potential'] > 0:
        stats['capture_rate'] = (stats['captured'] / stats['max_potential']) * 100

overall_capture_rate = (total_captured / total_max_potential) * 100 if total_max_potential > 0 else 0

# Display results
print("=" * 80)
print("EXIT ENGINE V1 - WITH BUG FIXES")
print("=" * 80)
print()
print("Results by Profile:")
print("-" * 80)
print(f"{'Profile':<20} {'Trades':>8} {'Max Potential':>15} {'Captured':>15} {'Rate':>10}")
print("-" * 80)

for profile_id in sorted(results_by_profile.keys()):
    stats = results_by_profile[profile_id]
    print(f"{profile_id:<20} {stats['trades']:>8} "
          f"${stats['max_potential']:>14,.0f} "
          f"${stats['captured']:>14,.0f} "
          f"{stats['capture_rate']:>9.1f}%")

print("-" * 80)
print(f"{'TOTAL':<20} {sum(s['trades'] for s in results_by_profile.values()):>8} "
      f"${total_max_potential:>14,.0f} "
      f"${total_captured:>14,.0f} "
      f"{overall_capture_rate:>9.1f}%")
print("=" * 80)
print()

# Verdict
print("VERDICT:")
print()
if overall_capture_rate < 2:
    print(f"❌ FAILURE: {overall_capture_rate:.1f}% capture rate")
    print("   Bug fixes didn't solve the problem")
    print("   → Need to RE-DERIVE parameters on clean train period")
elif overall_capture_rate < 10:
    print(f"⚠️  MARGINAL: {overall_capture_rate:.1f}% capture rate")
    print("   Bug fixes helped but not enough")
    print("   → Consider re-deriving parameters")
elif overall_capture_rate < 20:
    print(f"✓ ACCEPTABLE: {overall_capture_rate:.1f}% capture rate")
    print("   Bug fixes significantly improved performance")
    print("   → Proceed to train/val/test with clean methodology")
else:
    print(f"✓✓ EXCELLENT: {overall_capture_rate:.1f}% capture rate")
    print("   Bug fixes solved the problem!")
    print("   → Proceed to validation testing")

print()
print("Next Steps:")
if overall_capture_rate >= 10:
    print("1. Run on TRAIN period (2020-2021) to establish baseline")
    print("2. Run on VALIDATION period (2022-2023) expecting 20-40% degradation")
    print("3. If validation passes → Run on TEST period (2024)")
else:
    print("1. Re-derive ALL parameters on clean train period (2020-2021)")
    print("2. Use statistical distribution, not optimization")
    print("3. Test on validation (2022-2023)")
