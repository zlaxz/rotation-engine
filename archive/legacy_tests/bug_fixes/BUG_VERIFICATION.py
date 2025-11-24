"""
BUG VERIFICATION SCRIPT
======================

This script demonstrates the 3 critical bugs found in the quantitative audit.
Run this to see the bugs in action.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("=" * 80)
print("BUG VERIFICATION: ROTATION ENGINE AUDIT")
print("=" * 80)

# ============================================================================
# BUG-001: DTE CALCULATION BROKEN FOR MULTI-LEG POSITIONS
# ============================================================================

print("\n" + "=" * 80)
print("BUG-001: DTE Calculation with Multi-Leg Positions")
print("=" * 80)

# Setup
entry_date = datetime(2024, 11, 1)
current_date = datetime(2024, 11, 13)
long_expiry = entry_date + timedelta(days=60)    # Nov 30
short_expiry = entry_date + timedelta(days=7)    # Nov 8

days_in_trade = (current_date - entry_date).days

# Current (BROKEN) code
stored_dte_long = 60
stored_dte_short = 7
avg_dte_broken = int(np.mean([stored_dte_long, stored_dte_short])) - days_in_trade

# Correct calculation
correct_dte_long = (long_expiry - current_date).days
correct_dte_short = (short_expiry - current_date).days

print(f"\nScenario: Diagonal spread (long 60 DTE call, short 7 DTE call)")
print(f"Entry date: {entry_date.date()}")
print(f"Current date: {current_date.date()}")
print(f"Days in trade: {days_in_trade} calendar days")

print(f"\nLong leg expiry: {long_expiry.date()} -> {correct_dte_long} DTE (CORRECT)")
print(f"Short leg expiry: {short_expiry.date()} -> {correct_dte_short} DTE (CORRECT)")

print(f"\nCurrent (broken) code:")
print(f"  avg_dte = mean([{stored_dte_long}, {stored_dte_short}]) - {days_in_trade}")
print(f"          = {(stored_dte_long + stored_dte_short) / 2:.1f} - {days_in_trade}")
print(f"          = {avg_dte_broken:.1f} DTE")

print(f"\nPROBLEM: Short leg already expired 5 days ago! ({correct_dte_short} DTE)")
print(f"But code shows {avg_dte_broken:.1f} DTE because average hides it.")
print(f"Rolling logic would NOT trigger (threshold is typically 3 DTE)")
print(f"Position continues holding an EXPIRED leg.")

# ============================================================================
# BUG-002: MULTI-LEG POSITIONS LACK PER-LEG STATE TRACKING
# ============================================================================

print("\n" + "=" * 80)
print("BUG-002: Multi-Leg Position State Tracking")
print("=" * 80)

print(f"\nDiagonal spread with 2 legs:")
print(f"  Leg 1: Long call, 60 DTE")
print(f"  Leg 2: Short call, 7 DTE (expires Nov 8)")

print(f"\nCurrent date: {current_date.date()}")
print(f"Short leg EXPIRED on Nov 8")

print(f"\nTrade object state:")
print(f"  is_open = True  (single flag for ENTIRE position)")
print(f"  No per-leg state tracking")

print(f"\nWhat SHOULD happen:")
print(f"  - Short leg 2 expires at 3 DTE")
print(f"  - Replace leg 2 with new 7 DTE short call")
print(f"  - Keep leg 1 open")

print(f"\nWhat ACTUALLY happens:")
print(f"  - Code checks avg DTE (21.5 currently)")
print(f"  - avg DTE is still > 3, so NO rolling")
print(f"  - No per-leg tracking = no way to roll just leg 2")
print(f"  - Position would stay open with expired leg")

print(f"\nResult: Rolling doesn't work for complex strategies")

# ============================================================================
# BUG-003: ALLOCATION WEIGHTS DON'T SUM TO 1.0 AFTER VIX SCALING
# ============================================================================

print("\n" + "=" * 80)
print("BUG-003: Allocation Weight Normalization After VIX Scaling")
print("=" * 80)

# Setup weights after all constraints
weights_before_vix = {
    'profile_1': 0.40,
    'profile_2': 0.40,
    'profile_3': 0.20
}

rv20 = 0.35  # 35% volatility
vix_scale_threshold = 0.30
vix_scale_factor = 0.5

print(f"\nAfter min/max constraints and normalization:")
for name, w in weights_before_vix.items():
    print(f"  {name}: {w:.2f}")
print(f"  Sum: {sum(weights_before_vix.values()):.2f} ✓")

print(f"\nVIX scaling decision:")
print(f"  RV20 = {rv20:.1%}")
print(f"  Threshold = {vix_scale_threshold:.1%}")
print(f"  Scale factor = {vix_scale_factor}")

if rv20 > vix_scale_threshold:
    weights_after_vix = {k: v * vix_scale_factor for k, v in weights_before_vix.items()}

    print(f"\n  RV20 > threshold, apply scaling")
    print(f"  Multiply all weights by {vix_scale_factor}")

    print(f"\nAfter VIX scaling (BROKEN):")
    for name, w in weights_after_vix.items():
        print(f"  {name}: {w:.2f}")
    print(f"  Sum: {sum(weights_after_vix.values()):.2f} ✗ (NOT 1.0!)")

    print(f"\nResult: Allocation is only {sum(weights_after_vix.values()):.0%} of portfolio")
    print(f"        {(1 - sum(weights_after_vix.values())):.0%} is MISSING / UNALLOCATED")

    print(f"\nWhat SHOULD happen:")
    print(f"  After scaling:")
    for name, w in weights_after_vix.items():
        print(f"    {name}: {w:.2f}")

    # Correct: re-normalize
    total = sum(weights_after_vix.values())
    weights_correct = {k: v / total for k, v in weights_after_vix.items()}
    print(f"\n  Then re-normalize:")
    for name, w in weights_correct.items():
        print(f"    {name}: {w:.2f}")
    print(f"  Sum: {sum(weights_correct.values()):.2f} ✓")

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("IMPACT SUMMARY")
print("=" * 80)

print(f"""
BUG-001: DTE Calculation
  Impact: Rolling doesn't work correctly for multi-leg strategies
  Affected: All strategies using rolling (Profiles 1, 4)

BUG-002: Per-Leg State Tracking
  Impact: Can't roll individual legs, must close entire position
  Affected: All multi-leg strategies (Profiles 1, 4, 5, 6)

BUG-003: Weight Normalization
  Impact: Allocation only 50% of intended when RV20 > 30%
  Affected: All backtests in high volatility periods (frequent!)

DEPLOYMENT DECISION: DO NOT DEPLOY
These bugs invalidate backtest results. Must fix before trading.

Expected fix time: 6-8 hours total
Expected retest time: 4-6 hours
""")

print("=" * 80)
print("END VERIFICATION")
print("=" * 80)
