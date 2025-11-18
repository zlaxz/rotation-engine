# ROUND 6 CRITICAL BUG FIX REQUIRED

## Executive Summary

**Bug Found:** Portfolio attribution double-counting
**Location:** `/Users/zstoc/rotation-engine/src/backtest/portfolio.py`, line 157
**Severity:** CRITICAL - Reporting is wrong
**Time to Fix:** 5 minutes
**Blocks:** Live trading (attribution metrics used for rebalancing decisions)

---

## The Bug

### Current Code (WRONG)
```python
# Line 157 in _attribution_by_profile()
pnl_cols = [col for col in portfolio.columns
            if col.endswith('_pnl')
            and col != 'portfolio_pnl'
            and col != 'cumulative_pnl']
```

### Problem
This filter matches:
- `profile_1_daily_pnl` (unweighted daily P&L from profile backtest)
- `profile_1_pnl` (weighted daily P&L after allocation)

Both columns exist in portfolio DataFrame and both end with `_pnl`, so BOTH get summed in attribution.

### Example
```
Day 1 attribution for profile_1:
  - profile_1_daily_pnl: $1,000 (unweighted)
  - profile_1_pnl: $600 (weighted at 60% allocation)
  - Sum: $1,600 (WRONG!)
  - Should be: $600
```

---

## The Fix

### Option 1: Exclude Daily Columns (Recommended)
```python
# Line 157 in _attribution_by_profile()
pnl_cols = [col for col in portfolio.columns
            if col.endswith('_pnl')
            and '_daily_' not in col              # ADD THIS LINE
            and col != 'portfolio_pnl'
            and col != 'cumulative_pnl']
```

### Option 2: Explicit Pattern Matching
```python
# Line 157 in _attribution_by_profile()
pnl_cols = [col for col in portfolio.columns
            if col.startswith('profile_')
            and col.endswith('_pnl')
            and '_daily_' not in col]
```

### Option 3: Simpler Approach
```python
# Line 157 in _attribution_by_profile()
# Only include columns that match pattern: profile_X_pnl (no daily)
pnl_cols = [col for col in portfolio.columns
            if col.startswith('profile_')
            and col.endswith('_pnl')
            and col.count('_') == 2]  # profile_1_pnl has exactly 2 underscores
```

---

## Verification After Fix

### Step 1: Run aggregation with test data
```python
portfolio = aggregator.aggregate_pnl(allocations, profile_results)
attribution = portfolio.groupby('profile')['profile_X_pnl'].sum()
```

### Step 2: Verify attribution adds up
```python
sum(attribution) == portfolio['portfolio_pnl'].sum()
```

This must be TRUE after fix.

### Step 3: Check no double-counting
```python
# Before fix - sum would be wrong
# After fix - sum should equal portfolio total

total_attribution = sum(aggregator._attribution_by_profile(portfolio)['total_pnl'])
total_portfolio = portfolio['portfolio_pnl'].sum()

assert abs(total_attribution - total_portfolio) < 1.0  # $1 rounding tolerance
```

---

## Impact Assessment

### What's WRONG (needs fixing):
- Attribution metrics in `_attribution_by_profile()` output
- Any reports that show "Profile X contributed Y% to returns"
- Executive summaries of profile P&L breakdown

### What's CORRECT (no impact):
- Total portfolio P&L (uses `portfolio_pnl` which is excluded)
- Portfolio returns and Sharpe ratio
- Individual profile backtest results
- Attribution by regime (uses portfolio_pnl)
- All performance metrics (use correct portfolio P&L)

### Real-World Impact:
- Reports show Profile 1 contributed $1600 when really $600
- Management might make wrong rebalancing decisions based on inflated attribution
- Strategy decisions would be based on incorrect performance attribution

---

## Files to Modify

**File:** `/Users/zstoc/rotation-engine/src/backtest/portfolio.py`
**Method:** `_attribution_by_profile()`
**Line:** 157
**Change:** Add filter to exclude `_daily_pnl` columns

---

## Testing After Fix

### Command to test:
```python
import pandas as pd
from src.backtest.portfolio import PortfolioAggregator

# Run backtest...
portfolio = aggregator.aggregate_pnl(allocations, profile_results)

# Check attribution
attribution = aggregator._attribution_by_profile(portfolio)
total_attr = attribution['total_pnl'].sum()
total_pnl = portfolio['portfolio_pnl'].sum()

print(f"Attribution total: ${total_attr:,.2f}")
print(f"Portfolio total:   ${total_pnl:,.2f}")
print(f"Match? {abs(total_attr - total_pnl) < 1.0}")  # Should print True
```

---

## Deployment Checklist

- [ ] Fix line 157 in portfolio.py
- [ ] Run local test to verify attribution matches portfolio total
- [ ] Re-run historical backtest
- [ ] Verify profile attribution numbers are now 40-60% smaller (correct)
- [ ] Check that total still matches (no loss of money)
- [ ] Update any dashboards showing attribution
- [ ] Note: This ONLY affects attribution reporting, not actual P&L
- [ ] Commit fix with message: "fix: Remove double-counting in portfolio attribution (line 157)"

---

## Reference

**Full audit:** `/Users/zstoc/rotation-engine/ROUND6_INDEPENDENT_VERIFICATION_AUDIT.md`
**Session state:** `/Users/zstoc/rotation-engine/SESSION_STATE.md`
