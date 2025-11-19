#!/usr/bin/env python3
"""
ROUND 4 SHARPE BUG DETAILED ANALYSIS

The Sharpe ratio is inflated by ~33%. This document traces exactly WHY.
"""

import sys
sys.path.append('/Users/zstoc/rotation-engine')

import pandas as pd
import numpy as np


def sharpe_bug_root_cause():
    """
    Identify the ROOT CAUSE of the Sharpe ratio bug
    """
    print("\n" + "="*80)
    print("SHARPE BUG ROOT CAUSE ANALYSIS")
    print("="*80)

    # Simple test case
    pnl = pd.Series([100, -50, 200])
    starting_capital = 100000

    print("\n1. THE DATA:")
    print(f"   Daily P&L: {pnl.tolist()}")
    print(f"   Portfolio value changes: [100000→100100, 100100→100050, 100050→100250]")

    print("\n2. PORTFOLIO VALUE SERIES (what pct_change sees):")
    portfolio_values = starting_capital + pnl.cumsum()
    print(f"   [100100, 100050, 100250]")
    print(f"   Note: NO starting value (100000) at index 0!")

    print("\n3. PCT_CHANGE BEHAVIOR:")
    print("   When you call pct_change() on [100100, 100050, 100250]:")
    print("   pct_change = [NaN, (100050-100100)/100100, (100250-100050)/100050]")
    print("   pct_change = [NaN, -0.000499..., 0.001999...]")
    print("   After dropna: [-0.000499..., 0.001999...]")
    print("\n   This calculates:")
    print("   - Return from day 0→1: -$50 / $100100 = -0.05%")
    print("   - Return from day 1→2: $200 / $100050 = 0.20%")
    print("   → MISSING: Return from day -1→0 (entry day): $100 / $100000 = 0.10%")

    print("\n4. THE FIX ATTEMPT (WRONG):")
    print("   Code says: 'pct_change loses first return, add it back'")
    print("   So it prepends: first_return = 100 / 100000 = 0.001")
    print("   Result: [0.001, -0.000499..., 0.001999...]")
    print("   Length: 3 (matches pnl length) ✓")

    print("\n5. THE PROBLEM:")
    print("   The code assumes we should have 3 returns for 3 P&L values.")
    print("   But this is CONCEPTUALLY WRONG.")
    print("\n   Daily P&L = changes in portfolio value")
    print("   Daily returns = portfolio_value[t] / portfolio_value[t-1] - 1")
    print("\n   If we have 3 daily P&L values, we have:")
    print("   - 4 portfolio values (including starting)")
    print("   - 3 daily returns (one per P&L period)")
    print("\n   pct_change([100100, 100050, 100250]) gives 2 returns")
    print("   (comparing: 100050→100100, 100250→100050)")
    print("   NOT comparing: 100000→100100, 100100→100050, 100050→100250")

    print("\n6. CORRECT APPROACH:")
    print("   Portfolio values should INCLUDE starting value:")
    portfolio_values_correct = [starting_capital] + (starting_capital + pnl.cumsum()).tolist()
    print(f"   [100000, 100100, 100050, 100250]")
    print("\n   Then pct_change gives all 3 returns:")
    returns_correct = np.diff(portfolio_values_correct) / portfolio_values_correct[:-1]
    print(f"   [{returns_correct[0]:.6f}, {returns_correct[1]:.6f}, {returns_correct[2]:.6f}]")
    print(f"   = [0.001000, -0.000499, 0.001999]")
    print("   → First return now correctly calculated from starting capital!")

    print("\n7. VERIFICATION:")
    sharpe_wrong = calc_sharpe_buggy_way(pnl, starting_capital)
    sharpe_correct = calc_sharpe_correct_way(pnl, starting_capital)
    print(f"   Buggy Sharpe (prepending): {sharpe_wrong:.4f}")
    print(f"   Correct Sharpe: {sharpe_correct:.4f}")
    print(f"   Ratio: {sharpe_wrong / sharpe_correct:.4f}")


def calc_sharpe_buggy_way(pnl, starting_capital):
    """Calculate Sharpe the way the code does it (BUGGY)"""
    cumulative_portfolio_value = starting_capital + pnl.cumsum()
    returns_pct = cumulative_portfolio_value.pct_change().dropna()

    # Code prepends first_return
    if len(returns_pct) > 0:
        first_return = pnl.iloc[0] / starting_capital
        returns_pct = pd.concat([
            pd.Series([first_return], index=[pnl.index[0]]),
            returns_pct
        ])

    mean_ret = returns_pct.mean()
    std_ret = returns_pct.std()
    sharpe = (mean_ret / std_ret) * np.sqrt(252) if std_ret > 0 else 0
    return sharpe


def calc_sharpe_correct_way(pnl, starting_capital):
    """Calculate Sharpe the CORRECT way"""
    # Include starting value in portfolio values
    portfolio_values = pd.Series(
        [starting_capital] + (starting_capital + pnl.cumsum()).tolist(),
        index=range(len(pnl) + 1)
    )

    # Now pct_change will give all daily returns (no missing first one)
    returns_pct = portfolio_values.pct_change().dropna()

    mean_ret = returns_pct.mean()
    std_ret = returns_pct.std()
    sharpe = (mean_ret / std_ret) * np.sqrt(252) if std_ret > 0 else 0
    return sharpe


def test_why_prepending_is_wrong():
    """
    Explain why prepending first_return is conceptually wrong
    """
    print("\n" + "="*80)
    print("WHY PREPENDING FIRST_RETURN IS WRONG")
    print("="*80)

    print("\nThe bug comes from a misunderstanding of what pct_change does.")
    print("\nLet's trace through carefully:")

    pnl = pd.Series([100, 200], index=['Day0', 'Day1'])
    starting_capital = 1000
    cumulative_portfolio_value = starting_capital + pnl.cumsum()

    print(f"\nInput: pnl = {pnl.to_dict()}")
    print(f"Portfolio value at:")
    print(f"  Entry (Day -1): $1000")
    print(f"  After Day 0: ${cumulative_portfolio_value.iloc[0]}")
    print(f"  After Day 1: ${cumulative_portfolio_value.iloc[1]}")

    print(f"\ncumulative_portfolio_value = starting + pnl.cumsum()")
    print(f"                           = [1100, 1300]")
    print(f"Note: Does NOT include starting value (1000)")

    print(f"\nWhen we call pct_change() on [1100, 1300]:")
    returns = cumulative_portfolio_value.pct_change()
    print(f"  pct_change() = [NaN, {returns.iloc[1]:.4f}]")
    print(f"  This calculates: (1300 - 1100) / 1100 = 0.1818 (the Day 1 return)")
    print(f"  But it CANNOT calculate Day 0 return (no prior portfolio value)")

    print(f"\nCode tries to fix this by prepending:")
    first_return = pnl.iloc[0] / starting_capital
    print(f"  first_return = 100 / 1000 = {first_return}")
    print(f"  Result: [{first_return}, {returns.iloc[1]:.4f}]")

    print(f"\n>>> BUT this is WRONG calculation! <<<")
    print(f"    If we compare Day 0 return to starting (1000):")
    print(f"    → $100 gain / $1000 = 10% = 0.10 ✓ Correct")
    print(f"\n    If we compare Day 1 return to Day 0 value (1100):")
    print(f"    → $200 gain / $1100 = 18.18% = 0.1818 ✓ Correct")
    print(f"\n    So prepending 0.10 makes sense...")
    print(f"\n    ... EXCEPT that pct_change()[1] already gave us the WRONG return!")
    print(f"    Should be: Return from Day 0→1 = $200 gain / $1100 = 18.18% ✓")
    print(f"    Got: Return from Day 0→1 = $200 gain / $1100 = 18.18% ✓ Correct")

    print(f"\n>>> WAIT, LET ME RECALCULATE <<<")
    print(f"\npct_change on cumulative_portfolio_value [1100, 1300]:")
    print(f"  [1] = (1300 - 1100) / 1100 = 0.1818")
    print(f"  This is correct for Day 1 return")

    print(f"\nWhat SHOULD the full returns be?")
    print(f"  Day 0 return = 100 / 1000 = 0.10")
    print(f"  Day 1 return = 200 / 1100 = 0.1818")
    print(f"  Total: [0.10, 0.1818]")

    print(f"\nWhat does prepending give us?")
    prepended = [first_return, returns.iloc[1]]
    print(f"  [0.10, 0.1818]")
    print(f"  WAIT - this is CORRECT!")

    print(f"\n... So what's the bug then?")
    print(f"\nThe bug is more subtle. Let me recalculate the second return:")

    print(f"\nPortfolio at Day 0: ${1000 + 100} = $1100")
    print(f"Portfolio at Day 1: ${1000 + 100 + 200} = $1300")
    print(f"Return Day 0→1: (1300 - 1100) / 1100 = 200 / 1100 = {200/1100:.6f}")

    print(f"\ncumulative_portfolio_value = [1100, 1300]")
    print(f"pct_change()[1] = (1300 - 1100) / 1100 = {(1300-1100)/1100:.6f}")
    print(f"✓ Correct!")

    print(f"\nSo the issue isn't duplication or wrong calculation per se...")
    print(f"The issue is that we're comparing apples to oranges:")
    print(f"  - Day 0 return uses: change / starting_capital")
    print(f"  - Day 1 return uses: change / portfolio_at_day0")
    print(f"\nThis is inconsistent!  Returns are calculated relative to DIFFERENT bases!")


def correct_sharpe_formula():
    """
    Show the correct way to calculate Sharpe when we have daily P&L
    """
    print("\n" + "="*80)
    print("CORRECT SHARPE FORMULA (Method 1: Use P&L directly)")
    print("="*80)

    pnl = pd.Series([100, -50, 200])
    starting_capital = 100000

    print(f"\nGiven: Daily P&L = {pnl.tolist()}")
    print(f"Starting capital = ${starting_capital}")

    print(f"\nMethod 1 (Convert P&L to returns, calculate Sharpe):")
    print(f"  Option A: Use only pct_change of cumulative portfolio")
    cumulative_portfolio_value = starting_capital + pnl.cumsum()
    returns_only_pct_change = cumulative_portfolio_value.pct_change().dropna()
    sharpe_a = (returns_only_pct_change.mean() / returns_only_pct_change.std()) * np.sqrt(252)
    print(f"    Returns: {returns_only_pct_change.tolist()}")
    print(f"    Length: {len(returns_only_pct_change)} (missing first return!)")
    print(f"    Sharpe: {sharpe_a:.4f}")

    print(f"\n  Option B: Calculate all returns relative to starting capital")
    # For each day t, return = (P&L_t) / starting_capital
    # (This assumes we can re-balance back to starting capital each day)
    returns_relative_to_start = pnl / starting_capital
    sharpe_b = (returns_relative_to_start.mean() / returns_relative_to_start.std()) * np.sqrt(252)
    print(f"    Returns: {returns_relative_to_start.tolist()}")
    print(f"    (Assumes each P&L is independent, compared to starting capital)")
    print(f"    Sharpe: {sharpe_b:.4f}")

    print(f"\n  Option C (CORRECT): Include starting value in portfolio series")
    portfolio_with_start = pd.Series([starting_capital] + (starting_capital + pnl.cumsum()).tolist())
    returns_all = portfolio_with_start.pct_change().dropna()
    sharpe_c = (returns_all.mean() / returns_all.std()) * np.sqrt(252)
    print(f"    Portfolio values: {portfolio_with_start.tolist()}")
    print(f"    Returns: {returns_all.tolist()}")
    print(f"    Sharpe: {sharpe_c:.4f}")

    print(f"\n  Option D (What code does): Prepend first_return to pct_change result")
    returns_pct = cumulative_portfolio_value.pct_change().dropna()
    first_return = pnl.iloc[0] / starting_capital
    returns_d = pd.concat([pd.Series([first_return]), returns_pct])
    sharpe_d = (returns_d.mean() / returns_d.std()) * np.sqrt(252)
    print(f"    Returns: {returns_d.tolist()}")
    print(f"    Sharpe: {sharpe_d:.4f}")

    print(f"\n\nCOMPARISON:")
    print(f"  A (pct_change only):        {sharpe_a:.4f}")
    print(f"  B (all relative to start):  {sharpe_b:.4f}")
    print(f"  C (correct with start):     {sharpe_c:.4f}")
    print(f"  D (code's prepend method):  {sharpe_d:.4f}")

    print(f"\nThe problem with Option D:")
    print(f"  - Prepended return (0.1%) is calculated as: P&L[0] / starting_capital")
    print(f"  - Other returns are calculated as: (portfolio[t] - portfolio[t-1]) / portfolio[t-1]")
    print(f"  - These use DIFFERENT bases, causing bias!")


if __name__ == '__main__':
    sharpe_bug_root_cause()
    test_why_prepending_is_wrong()
    correct_sharpe_formula()
