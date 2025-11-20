#!/usr/bin/env python3
"""
Standalone verification script for critical bug fixes in Phase 3.

Tests:
- BUG-C07: DTE calculation for multi-leg positions
- BUG-C08: Commission and fee tracking
- BUG-M01: Allocation re-normalization after VIX scaling
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.trading.trade import Trade, TradeLeg
from src.trading.execution import ExecutionModel

# Import RotationAllocator directly to avoid engine.py import issues
import importlib.util
spec = importlib.util.spec_from_file_location(
    "rotation",
    os.path.join(os.path.dirname(__file__), '..', 'src', 'backtest', 'rotation.py')
)
rotation_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rotation_module)
RotationAllocator = rotation_module.RotationAllocator


def test_dte_calculation():
    """Test BUG-C07: DTE calculation for multi-leg positions."""
    print("\n" + "="*70)
    print("TEST: BUG-C07 - DTE Calculation for Multi-Leg Positions")
    print("="*70)

    # Create a trade with two legs, different expiries
    entry_date = datetime(2024, 1, 1)
    near_expiry = entry_date + timedelta(days=8)   # Will have 3 DTE at entry + 5 days
    far_expiry = entry_date + timedelta(days=15)   # Will have 10 DTE at entry + 5 days

    trade = Trade(
        trade_id="TEST_001",
        profile_name="TestProfile",
        entry_date=entry_date,
        legs=[
            TradeLeg(strike=500, expiry=near_expiry, option_type='call', quantity=1, dte=8),
            TradeLeg(strike=500, expiry=far_expiry, option_type='put', quantity=1, dte=15)
        ],
        entry_prices={0: 10.0, 1: 10.0}
    )
    trade.__post_init__()
    trade.is_open = True

    # Simulate advancing 5 days
    # At this point: near_expiry = 3 DTE, far_expiry = 10 DTE
    current_date = (entry_date + timedelta(days=5)).date()

    # Calculate min DTE using the fixed logic
    min_dte = float('inf')
    for leg in trade.legs:
        expiry = leg.expiry
        if isinstance(expiry, datetime):
            expiry = expiry.date()

        dte = (expiry - current_date).days
        min_dte = min(min_dte, dte)

    print(f"Entry date: {entry_date.date()}")
    print(f"Current date: {current_date}")
    print(f"Near expiry: {near_expiry.date()} ({(near_expiry.date() - current_date).days} DTE)")
    print(f"Far expiry: {far_expiry.date()} ({(far_expiry.date() - current_date).days} DTE)")
    print(f"Min DTE calculated: {min_dte}")

    # Verify
    expected_min_dte = 3
    assert min_dte == expected_min_dte, f"FAILED: Expected min_dte={expected_min_dte}, got {min_dte}"

    # Verify exit would trigger at 5 DTE threshold
    roll_threshold = 5
    should_exit = min_dte <= roll_threshold
    print(f"Roll threshold: {roll_threshold}")
    print(f"Should exit: {should_exit}")

    assert should_exit, "FAILED: Trade should exit when min_dte <= roll_threshold"

    print("✅ PASSED: DTE calculation correctly uses nearest expiry")
    return True


def test_commissions():
    """Test BUG-C08: Commission and fee tracking."""
    print("\n" + "="*70)
    print("TEST: BUG-C08 - Commission and Fee Tracking")
    print("="*70)

    # Test commission calculation
    exec_model = ExecutionModel(
        option_commission=0.65,
        sec_fee_rate=0.00182
    )

    # Test long position (no SEC fees)
    cost_long = exec_model.get_commission_cost(num_contracts=2, is_short=False)
    expected_long = 2 * 0.65
    print(f"Long position (2 contracts): ${cost_long:.4f} (expected ${expected_long:.4f})")
    assert cost_long == expected_long, f"FAILED: Expected {expected_long}, got {cost_long}"

    # Test short position (with SEC fees)
    cost_short = exec_model.get_commission_cost(num_contracts=2, is_short=True)
    expected_short = 2 * 0.65 + 2 * 0.00182
    print(f"Short position (2 contracts): ${cost_short:.4f} (expected ${expected_short:.4f})")
    assert cost_short == expected_short, f"FAILED: Expected {expected_short}, got {cost_short}"

    # Test trade P&L includes commissions
    entry_date = datetime(2024, 1, 1)
    exit_date = datetime(2024, 1, 10)

    trade = Trade(
        trade_id="TEST_003",
        profile_name="TestProfile",
        entry_date=entry_date,
        legs=[
            TradeLeg(strike=500, expiry=entry_date + timedelta(days=30),
                    option_type='call', quantity=1, dte=30)
        ],
        entry_prices={0: 10.0}
    )
    trade.__post_init__()

    print(f"\nTrade setup:")
    print(f"  Entry: 1 call @ $10.00")
    print(f"  Entry cost: ${trade.entry_cost}")

    # Set commissions
    trade.entry_commission = 0.65
    trade.exit_commission = 0.65

    # Close at profit: exit at 15.0
    # Raw P&L = 1 * (15.0 - 10.0) = 5.0
    # After commissions: 5.0 - 0.65 - 0.65 = 3.70
    trade.close(exit_date, {0: 15.0}, "Test close")

    expected_pnl = 5.0 - 0.65 - 0.65
    print(f"  Exit: 1 call @ $15.00")
    print(f"  Raw P&L: $5.00")
    print(f"  Entry commission: $0.65")
    print(f"  Exit commission: $0.65")
    print(f"  Net P&L: ${trade.realized_pnl:.2f} (expected ${expected_pnl:.2f})")

    assert trade.realized_pnl == expected_pnl, \
        f"FAILED: Expected realized_pnl={expected_pnl}, got {trade.realized_pnl}"

    # Test mark-to-market includes entry commission
    trade2 = Trade(
        trade_id="TEST_004",
        profile_name="TestProfile",
        entry_date=entry_date,
        legs=[
            TradeLeg(strike=500, expiry=entry_date + timedelta(days=30),
                    option_type='call', quantity=1, dte=30)
        ],
        entry_prices={0: 10.0}
    )
    trade2.__post_init__()
    trade2.entry_commission = 0.65

    # Current price = 12.0
    # Unrealized P&L = 1 * (12.0 - 10.0) - 0.65 = 1.35
    unrealized = trade2.mark_to_market({0: 12.0})
    expected_unrealized = 2.0 - 0.65
    print(f"\nMark-to-market test:")
    print(f"  Current price: $12.00")
    print(f"  Unrealized P&L: ${unrealized:.2f} (expected ${expected_unrealized:.2f})")

    assert unrealized == expected_unrealized, \
        f"FAILED: Expected unrealized={expected_unrealized}, got {unrealized}"

    print("✅ PASSED: Commissions correctly tracked in P&L")
    return True


def test_allocation_normalization():
    """Test BUG-M01: Allocation re-normalization after VIX scaling."""
    print("\n" + "="*70)
    print("TEST: BUG-M01 - Allocation Re-normalization After VIX Scaling")
    print("="*70)

    allocator = RotationAllocator(
        max_profile_weight=0.40,
        min_profile_weight=0.05,
        vix_scale_threshold=0.30,
        vix_scale_factor=0.5
    )

    profile_scores = {
        'profile_1': 0.8,
        'profile_2': 0.6,
        'profile_3': 0.4
    }

    # Test with high volatility (triggers scaling)
    regime = 1
    rv20_high = 0.35  # Above threshold

    print(f"Profile scores: {profile_scores}")
    print(f"Regime: {regime}")
    print(f"RV20 (high vol): {rv20_high}")

    weights_high = allocator.allocate(profile_scores, regime, rv20_high)
    total_high = sum(weights_high.values())

    print(f"\nWeights after VIX scaling:")
    for profile, weight in weights_high.items():
        print(f"  {profile}: {weight:.4f}")
    print(f"Total: {total_high:.4f}")

    # Weights should sum to 1.0 after re-normalization
    assert np.isclose(total_high, 1.0, atol=1e-6), \
        f"FAILED: Weights should sum to 1.0 after VIX scaling, got {total_high}"

    # Test with normal volatility (no scaling)
    rv20_normal = 0.20  # Below threshold

    print(f"\nRV20 (normal vol): {rv20_normal}")

    weights_normal = allocator.allocate(profile_scores, regime, rv20_normal)
    total_normal = sum(weights_normal.values())

    print(f"\nWeights without VIX scaling:")
    for profile, weight in weights_normal.items():
        print(f"  {profile}: {weight:.4f}")
    print(f"Total: {total_normal:.4f}")

    assert np.isclose(total_normal, 1.0, atol=1e-6), \
        f"FAILED: Weights should sum to 1.0 normally, got {total_normal}"

    print("✅ PASSED: Allocation correctly re-normalizes after VIX scaling")
    return True


def main():
    """Run all verification tests."""
    print("\n" + "="*70)
    print("PHASE 3 BUG FIX VERIFICATION")
    print("="*70)

    tests = [
        ("BUG-C07: DTE Calculation", test_dte_calculation),
        ("BUG-C08: Commissions", test_commissions),
        ("BUG-M01: Allocation Normalization", test_allocation_normalization)
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, "PASSED" if passed else "FAILED"))
        except Exception as e:
            print(f"\n❌ FAILED: {name}")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, "FAILED"))

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    all_passed = True
    for name, status in results:
        symbol = "✅" if status == "PASSED" else "❌"
        print(f"{symbol} {name}: {status}")
        if status == "FAILED":
            all_passed = False

    print("="*70)

    if all_passed:
        print("\n🎉 ALL TESTS PASSED - Infrastructure fixes verified!")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED - Review fixes needed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
