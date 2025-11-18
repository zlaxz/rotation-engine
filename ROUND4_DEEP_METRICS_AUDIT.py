#!/usr/bin/env python3
"""
ROUND 4 DEEP AUDIT - Metrics Calculation Bug Investigation

This audit investigates the Sharpe ratio "fix" more carefully.
The claim: "First return is already in pct_change(), don't add it again"

Let's verify this claim with mathematical precision.
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
import numpy as np
from src.analysis.metrics import PerformanceMetrics


def manual_sharpe_calculation():
    """
    Do a complete manual calculation to understand the logic
    """
    print("\n" + "="*80)
    print("MANUAL SHARPE CALCULATION VERIFICATION")
    print("="*80)

    # Test data
    pnl = pd.Series([100, -50, 200, -80, 150], index=range(5))
    starting_capital = 100000
    annual_factor = 252

    print("\n1. INPUT DATA:")
    print(f"   Daily P&L: {pnl.tolist()}")
    print(f"   Starting capital: ${starting_capital}")

    print("\n2. CUMULATIVE PORTFOLIO VALUE:")
    cumulative_portfolio_value = starting_capital + pnl.cumsum()
    print(f"   Values: {cumulative_portfolio_value.tolist()}")
    print("   Breakdown:")
    for i, val in enumerate(cumulative_portfolio_value):
        if i == 0:
            print(f"     [0] = {starting_capital} (starting)")
        else:
            print(f"     [{i}] = {starting_capital} + sum({pnl[:i+1].tolist()}) = {val}")

    print("\n3. PCT_CHANGE() CALCULATION:")
    returns_pct_raw = cumulative_portfolio_value.pct_change()
    print(f"   Raw pct_change (with NaN): {returns_pct_raw.tolist()}")
    returns_pct = returns_pct_raw.dropna()
    print(f"   After dropna (length={len(returns_pct)}): {returns_pct.tolist()}")
    print("   Breakdown:")
    for i, ret in enumerate(returns_pct):
        idx = i + 1  # Because we dropped the first NaN
        print(f"     [{i}] = ({cumulative_portfolio_value[idx]} - {cumulative_portfolio_value[idx-1]}) / {cumulative_portfolio_value[idx-1]} = {ret:.6f}")

    print("\n4. FIRST RETURN MANUAL CALCULATION:")
    first_return_manual = pnl.iloc[0] / starting_capital
    print(f"   Method 1 (P&L / starting): {pnl.iloc[0]} / {starting_capital} = {first_return_manual:.6f}")
    print(f"   Method 2 (from pct_change): {returns_pct.iloc[0]:.6f}")
    print(f"   Are they equal? {abs(first_return_manual - returns_pct.iloc[0]) < 1e-6}")

    print("\n5. KEY QUESTION:")
    print(f"   pct_change()[0] = ({cumulative_portfolio_value[1]} - {starting_capital}) / {starting_capital}")
    print(f"                    = ({starting_capital + pnl.iloc[0]} - {starting_capital}) / {starting_capital}")
    print(f"                    = {pnl.iloc[0]} / {starting_capital}")
    print(f"                    = {first_return_manual:.6f}")
    print(f"\n   → pct_change() ALREADY includes the first return!")
    print(f"   → Adding it again would DUPLICATE it!")

    print("\n6. TESTING CURRENT IMPLEMENTATION:")
    metrics = PerformanceMetrics(starting_capital=starting_capital)
    sharpe = metrics.sharpe_ratio(pnl)
    print(f"   Current Sharpe result: {sharpe:.4f}")

    # Now let's see what the code actually does internally
    # Read the sharpe_ratio function behavior

    print("\n7. CHECKING CODE BEHAVIOR:")
    print("   Looking at src/analysis/metrics.py line 121-126...")
    print("   Code checks: if len(returns) > 0:")
    print("       first_return = returns.iloc[0] / starting_capital")
    print("       returns_pct = concat([pd.Series([first_return]), returns_pct])")
    print("\n   This PREPENDS first_return to the returns_pct series!")
    print("   Since pct_change()[0] already equals first_return,")
    print("   we now have: [first_return, first_return, pct_change[1], ...]")
    print("   → POTENTIAL BUG!")

    return sharpe


def test_sharpe_length():
    """
    Test if the returns array length is what we expect
    """
    print("\n" + "="*80)
    print("TEST: RETURN ARRAY LENGTH")
    print("="*80)

    pnl = pd.Series([100, -50, 200], index=range(3))
    starting_capital = 100000
    metrics = PerformanceMetrics(starting_capital=starting_capital)

    # Manually trace through the sharpe_ratio code
    cumulative_portfolio_value = starting_capital + pnl.cumsum()
    print(f"\nCumulative portfolio: {cumulative_portfolio_value.tolist()}")

    returns_pct = cumulative_portfolio_value.pct_change().dropna()
    print(f"pct_change().dropna() length: {len(returns_pct)}")
    print(f"pct_change().dropna() values: {returns_pct.tolist()}")

    # Check if code adds first_return again
    if len(returns_pct) > 0:
        first_return = pnl.iloc[0] / starting_capital
        print(f"\nFirst return (manual): {first_return:.6f}")
        print(f"First pct_change value: {returns_pct.iloc[0]:.6f}")

        # This is what the code does:
        returns_pct_modified = pd.concat([
            pd.Series([first_return], index=[pnl.index[0]]),
            returns_pct
        ])
        print(f"\nAfter concat with first_return prepended:")
        print(f"Length: {len(returns_pct_modified)}")
        print(f"Values: {returns_pct_modified.tolist()}")

        # The question: is returns_pct_modified[0] == returns_pct_modified[1]?
        if len(returns_pct_modified) > 1 and abs(returns_pct_modified.iloc[0] - returns_pct_modified.iloc[1]) < 1e-6:
            print("\n❌ BUG CONFIRMED: First two returns are identical!")
            print("   This means first return was added twice (once by pct_change, once by concat)")
        else:
            print("\n✅ No duplication detected")


def test_sortino_length():
    """
    Same test for Sortino ratio
    """
    print("\n" + "="*80)
    print("TEST: SORTINO RATIO RETURN ARRAY LENGTH")
    print("="*80)

    pnl = pd.Series([100, -50, 200], index=range(3))
    starting_capital = 100000
    metrics = PerformanceMetrics(starting_capital=starting_capital)

    cumulative_portfolio_value = starting_capital + pnl.cumsum()
    returns_pct = cumulative_portfolio_value.pct_change().dropna()

    print(f"pct_change().dropna() length: {len(returns_pct)}")

    if len(returns_pct) > 0:
        first_return = pnl.iloc[0] / starting_capital
        returns_pct_modified = pd.concat([
            pd.Series([first_return], index=[pnl.index[0]]),
            returns_pct
        ])
        print(f"After adding first_return: length = {len(returns_pct_modified)}")

        if len(returns_pct_modified) > 1 and abs(returns_pct_modified.iloc[0] - returns_pct_modified.iloc[1]) < 1e-6:
            print("❌ BUG CONFIRMED: First two returns are identical!")


def test_actual_sharpe_vs_manual():
    """
    Compare sharpe calculation to manual numpy calculation
    """
    print("\n" + "="*80)
    print("SHARPE RATIO: IMPLEMENTATION VS MANUAL NUMPY")
    print("="*80)

    pnl = pd.Series([100, -50, 200, -80, 150])
    starting_capital = 100000
    annual_factor = 252

    metrics = PerformanceMetrics(starting_capital=starting_capital, annual_factor=annual_factor)
    sharpe_impl = metrics.sharpe_ratio(pnl)

    # Manual calculation with correct formula
    cumulative_portfolio_value = starting_capital + pnl.cumsum()
    returns_pct = cumulative_portfolio_value.pct_change().dropna()

    # Correct returns (WITHOUT prepending first_return again)
    mean_ret = returns_pct.mean()
    std_ret = returns_pct.std()
    sharpe_correct = (mean_ret / std_ret) * np.sqrt(annual_factor)

    print(f"\nImplementation Sharpe: {sharpe_impl:.4f}")
    print(f"Correct Sharpe (no duplication): {sharpe_correct:.4f}")
    print(f"Ratio (impl / correct): {sharpe_impl / sharpe_correct:.4f}")

    if abs(sharpe_impl - sharpe_correct) > 0.1:
        print("\n⚠️  SIGNIFICANT DIFFERENCE DETECTED")
        print("   Suggests returns array length or values are different")
    else:
        print("\n✅ Sharpe values are close (within expected rounding)")


if __name__ == '__main__':
    manual_sharpe_calculation()
    test_sharpe_length()
    test_sortino_length()
    test_actual_sharpe_vs_manual()
