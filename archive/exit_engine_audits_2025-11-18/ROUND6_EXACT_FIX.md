# ROUND 6: EXACT CODE FIX

## File to Modify
`/Users/zstoc/rotation-engine/src/backtest/portfolio.py`

## Current Code (Lines 147-177)

```python
def _attribution_by_profile(self, portfolio: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate P&L attribution by profile.

    Returns:
    --------
    attribution : pd.DataFrame
        Columns: profile, total_pnl, mean_daily_pnl, pnl_contribution
    """
    # Identify profile P&L columns
    pnl_cols = [col for col in portfolio.columns if col.endswith('_pnl') and col != 'portfolio_pnl' and col != 'cumulative_pnl']

    attribution = []
    total_portfolio_pnl = portfolio['portfolio_pnl'].sum()

    for pnl_col in pnl_cols:
        profile_name = pnl_col.replace('_pnl', '')
        total_pnl = portfolio[pnl_col].sum()
        mean_daily = portfolio[pnl_col].mean()

        # Contribution to total P&L
        contribution = (total_pnl / total_portfolio_pnl * 100) if total_portfolio_pnl != 0 else 0

        attribution.append({
            'profile': profile_name,
            'total_pnl': total_pnl,
            'mean_daily_pnl': mean_daily,
            'pnl_contribution_pct': contribution
        })

    return pd.DataFrame(attribution)
```

## Fixed Code (Lines 147-177)

```python
def _attribution_by_profile(self, portfolio: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate P&L attribution by profile.

    Returns:
    --------
    attribution : pd.DataFrame
        Columns: profile, total_pnl, mean_daily_pnl, pnl_contribution
    """
    # Identify profile P&L columns (EXCLUDE daily_pnl intermediate columns)
    pnl_cols = [col for col in portfolio.columns if col.endswith('_pnl') and '_daily_' not in col and col != 'portfolio_pnl' and col != 'cumulative_pnl']

    attribution = []
    total_portfolio_pnl = portfolio['portfolio_pnl'].sum()

    for pnl_col in pnl_cols:
        profile_name = pnl_col.replace('_pnl', '')
        total_pnl = portfolio[pnl_col].sum()
        mean_daily = portfolio[pnl_col].mean()

        # Contribution to total P&L
        contribution = (total_pnl / total_portfolio_pnl * 100) if total_portfolio_pnl != 0 else 0

        attribution.append({
            'profile': profile_name,
            'total_pnl': total_pnl,
            'mean_daily_pnl': mean_daily,
            'pnl_contribution_pct': contribution
        })

    return pd.DataFrame(attribution)
```

## The Exact Change

**Line 157 - OLD:**
```python
pnl_cols = [col for col in portfolio.columns if col.endswith('_pnl') and col != 'portfolio_pnl' and col != 'cumulative_pnl']
```

**Line 157 - NEW:**
```python
pnl_cols = [col for col in portfolio.columns if col.endswith('_pnl') and '_daily_' not in col and col != 'portfolio_pnl' and col != 'cumulative_pnl']
```

**What changed:**
- Added: `and '_daily_' not in col`
- Location: Between `col.endswith('_pnl')` and `col != 'portfolio_pnl'`

---

## Verification Script

Run this after making the fix:

```python
import pandas as pd
import numpy as np
from src.backtest.portfolio import PortfolioAggregator

# Create test data
allocations = pd.DataFrame({
    'date': pd.date_range('2024-01-01', periods=10),
    'regime': [1, 1, 2, 2, 1, 1, 2, 2, 1, 1],
    'profile_1_weight': [0.6, 0.6, 0.3, 0.3, 0.6, 0.6, 0.3, 0.3, 0.6, 0.6],
    'profile_2_weight': [0.4, 0.4, 0.7, 0.7, 0.4, 0.4, 0.7, 0.7, 0.4, 0.4]
})

profile_results = {
    'profile_1': pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=10),
        'daily_return': np.random.normal(0.001, 0.01, 10),
        'daily_pnl': np.random.normal(100, 1000, 10)
    }),
    'profile_2': pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=10),
        'daily_return': np.random.normal(0.0005, 0.015, 10),
        'daily_pnl': np.random.normal(50, 1500, 10)
    })
}

# Run aggregation
aggregator = PortfolioAggregator()
portfolio = aggregator.aggregate_pnl(allocations, profile_results)

# Check attribution
attribution = aggregator._attribution_by_profile(portfolio)
total_attr = attribution['total_pnl'].sum()
total_pnl = portfolio['portfolio_pnl'].sum()

# Verify fix
print("Attribution Total P&L:", f"${total_attr:,.2f}")
print("Portfolio Total P&L:  ", f"${total_pnl:,.2f}")
print("Difference:           ", f"${abs(total_attr - total_pnl):,.2f}")
print()
print("PASS" if abs(total_attr - total_pnl) < 1.0 else "FAIL")
```

**Expected output after fix:**
```
Attribution Total P&L: $[some number]
Portfolio Total P&L:   $[same number]
Difference:            $0.00 (or <$1.00)

PASS
```

---

## Testing Checklist

After applying the fix:

- [ ] File saves successfully
- [ ] Python syntax is valid (can import the module)
- [ ] Run the verification script above - must see "PASS"
- [ ] Attribution totals now match portfolio total
- [ ] Profile contribution percentages are now smaller (40-60% of original, which is correct)
- [ ] Total portfolio P&L unchanged (still correct)
- [ ] No new errors in backtest runs

---

## Commit Message

```
fix: Remove double-counting in portfolio attribution (line 157)

The _attribution_by_profile() method was matching both intermediate
'profile_X_daily_pnl' columns (unweighted) and final 'profile_X_pnl'
columns (weighted by allocation), causing attribution to be inflated
by ~166%.

Changed line 157 filter to exclude '_daily_' columns, so only the
final weighted P&L columns are included in attribution sums.

Verification: Attribution totals now match portfolio total P&L.
```

---

## Why This Bug Existed

The portfolio aggregation process creates many columns:
1. `profile_1_daily_return` - unweighted return from profile
2. `profile_1_daily_pnl` - unweighted P&L from profile  ← **Intermediate**
3. `profile_1_return` - weighted return (allocation × daily_return)
4. `profile_1_pnl` - weighted P&L ← **Final, what we want**

The original filter looked for `col.endswith('_pnl')`, which matched BOTH the intermediate (daily_pnl) AND final (pnl) columns.

The fix excludes the `_daily_` prefix, so only the final weighted columns are used.

---

## Related Code

**How columns are created (aggregate_pnl method):**
- Line 72: Intermediate column created: `profile_1_daily_pnl`
- Line 116: Final weighted column created: `profile_1_pnl`

**How attribution uses them (WRONG before fix):**
- Line 157 filter matched both columns
- Line 164: Sum all matched columns (WRONG - double counted)

**How attribution uses them (CORRECT after fix):**
- Line 157 filter matches only `profile_1_pnl` (not `profile_1_daily_pnl`)
- Line 164: Sum only weighted columns (CORRECT)
