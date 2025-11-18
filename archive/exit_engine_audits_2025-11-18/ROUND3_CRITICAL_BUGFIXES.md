# ROUND 3 CRITICAL BUG FIXES
**Date:** 2025-11-18
**Priority:** CRITICAL - Must fix before running backtests
**Found By:** Round 3 Implementation Audit

---

## BUG #5: Sharpe Ratio - First Return Double-Counted

### Location
**File:** `/Users/zstoc/rotation-engine/src/analysis/metrics.py`
**Function:** `sharpe_ratio()`
**Lines:** 118-122

### Issue
```python
# CURRENT CODE (BUGGY):
cumulative_portfolio_value = self.starting_capital + returns.cumsum()
returns_pct = cumulative_portfolio_value.pct_change().dropna()
if len(returns_pct) > 0:
    # BUG: First return already in returns_pct, this duplicates it
    first_return = returns.iloc[0] / self.starting_capital
    returns_pct = pd.concat([pd.Series([first_return], index=[returns.index[0]]), returns_pct])
```

### Why This Is Wrong

**Step-by-step breakdown:**
```python
# Input: Daily P&L = [100, -50, 200]
# starting_capital = 100000

# Step 1: Calculate cumulative portfolio value
cumulative_portfolio_value = [100000, 100100, 100050, 100250]
#                             [start,  +100,   -50,    +200]

# Step 2: pct_change() - THIS ALREADY INCLUDES FIRST RETURN
pct = cumulative_portfolio_value.pct_change()
# pct = [NaN, 0.001, -0.0005, 0.002]
#       [N/A, 100/100000, -50/100100, 200/100050]

# Step 3: dropna()
returns_pct = pct.dropna()
# returns_pct = [0.001, -0.0005, 0.002]  ← FIRST RETURN IS ALREADY HERE

# Step 4: Code then ADDS first return AGAIN (BUG!)
first_return = 100 / 100000 = 0.001
returns_pct = concat([0.001], [0.001, -0.0005, 0.002])
# returns_pct = [0.001, 0.001, -0.0005, 0.002]  ← DUPLICATE!
```

### Impact
- If first day is big winner (+$500): Sharpe inflated by ~10-20%
- If first day is big loser (-$500): Sharpe deflated by ~10-20%
- Systematic bias in ALL Sharpe calculations using dollar P&L
- **All existing Sharpe results are INVALID**

### Fix
```python
# CORRECT CODE:
cumulative_portfolio_value = self.starting_capital + returns.cumsum()
returns_pct = cumulative_portfolio_value.pct_change().dropna()
# DON'T add first_return - it's already in returns_pct!
```

### Lines to DELETE
Delete lines 119-122:
```python
if len(returns_pct) > 0:
    # Insert first return manually to avoid NaN
    first_return = returns.iloc[0] / self.starting_capital
    returns_pct = pd.concat([pd.Series([first_return], index=[returns.index[0]]), returns_pct])
```

---

## BUG #6: Sortino Ratio - Same First Return Issue

### Location
**File:** `/Users/zstoc/rotation-engine/src/analysis/metrics.py`
**Function:** `sortino_ratio()`
**Lines:** 165-168

### Issue
Identical bug as Sharpe ratio - first return duplicated

### Fix
Delete lines 165-168:
```python
if len(returns_pct) > 0:
    first_return = returns.iloc[0] / self.starting_capital
    returns_pct = pd.concat([pd.Series([first_return], index=[returns.index[0]]), returns_pct])
```

---

## BUG #7: Drawdown Analysis - Undefined Variable

### Location
**File:** `/Users/zstoc/rotation-engine/src/analysis/metrics.py`
**Function:** `drawdown_analysis()`
**Line:** 358

### Issue
```python
# Line 330: Variable defined as max_dd_position
max_dd_position = drawdown.argmin()

# Line 358: But code uses max_dd_idx (NameError!)
'max_dd_date': cumulative_pnl.index[max_dd_idx] if hasattr(...) else max_dd_idx,
```

### Impact
- Function crashes with `NameError: name 'max_dd_idx' is not defined`
- Any call to `drawdown_analysis()` will fail immediately
- Metrics calculation fails

### Fix
Change line 358 to use correct variable name:
```python
# BEFORE (WRONG):
'max_dd_date': cumulative_pnl.index[max_dd_idx] if hasattr(cumulative_pnl.index[max_dd_idx], 'date') else max_dd_idx,

# AFTER (CORRECT):
'max_dd_date': cumulative_pnl.index[max_dd_position] if hasattr(cumulative_pnl.index[max_dd_position], 'date') else max_dd_position,
```

---

## VERIFICATION AFTER FIX

### Test Case for Sharpe/Sortino Fix

```python
import pandas as pd
import numpy as np
from src.analysis.metrics import PerformanceMetrics

# Test data
pnl = pd.Series([100, -50, 200, -80, 150])
metrics = PerformanceMetrics(starting_capital=100000)

# Calculate Sharpe
sharpe = metrics.sharpe_ratio(pnl)

# Manual verification:
# cumulative = [100000, 100100, 100050, 100250, 100170, 100320]
# returns = [NaN, 0.1%, -0.05%, 0.2%, -0.08%, 0.15%]
# After dropna: [0.1%, -0.05%, 0.2%, -0.08%, 0.15%]
# Mean = 0.064%, Std = 0.126%
# Sharpe = (0.00064 / 0.00126) * sqrt(252) = 0.508 * 15.87 = 8.06

print(f"Sharpe: {sharpe:.2f}")
# Expected: ~8.0 (verify no duplication)

# Check length
cumulative_portfolio_value = 100000 + pnl.cumsum()
returns_pct = cumulative_portfolio_value.pct_change().dropna()
print(f"Returns length: {len(returns_pct)}")  # Should be 5 (same as pnl length)
print(f"First return: {returns_pct.iloc[0]:.4f}")  # Should be 0.1%
print(f"Second return: {returns_pct.iloc[1]:.4f}")  # Should be -0.05%, NOT 0.1% again
```

### Test Case for Drawdown Fix

```python
# Test drawdown_analysis doesn't crash
cumulative_pnl = pd.Series([0, 100, 50, 150, 100, 200])
dd_metrics = metrics.drawdown_analysis(cumulative_pnl)

print(f"Max DD: {dd_metrics['max_dd_value']:.0f}")  # Should be -50
print(f"Max DD date: {dd_metrics['max_dd_date']}")  # Should be index 2
# Should NOT crash with NameError
```

---

## APPLY FIXES

### Fix Command
```bash
# Edit src/analysis/metrics.py

# 1. Delete lines 119-122 (Sharpe fix)
# 2. Delete lines 165-168 (Sortino fix)
# 3. Change line 358: max_dd_idx → max_dd_position (Drawdown fix)
```

### Verification Command
```bash
# Run test after fixes
python -c "
from src.analysis.metrics import PerformanceMetrics
import pandas as pd

pnl = pd.Series([100, -50, 200])
m = PerformanceMetrics(starting_capital=100000)

# This should NOT crash and should have correct length
cumulative_portfolio_value = 100000 + pnl.cumsum()
returns_pct = cumulative_portfolio_value.pct_change().dropna()
print(f'Returns length: {len(returns_pct)} (should be 3)')
print(f'Returns: {returns_pct.tolist()}')

# Should be [0.001, -0.00049950..., 0.0019980...]
# NOT [0.001, 0.001, -0.00049950..., 0.0019980...] (4 values)

# Test drawdown doesn't crash
cum_pnl = pd.Series([0, 100, 50, 200])
dd = m.drawdown_analysis(cum_pnl)
print(f'Drawdown analysis worked: {dd[\"max_dd_value\"]:.0f}')
"
```

---

## IMPACT ASSESSMENT

### What Results Are Invalid

**Before fixes:**
- ❌ All Sharpe ratios calculated from dollar P&L
- ❌ All Sortino ratios calculated from dollar P&L
- ❌ Any metrics using drawdown_analysis() (crashes)
- ✅ Calmar ratios (don't use the buggy return conversion)
- ✅ Win rates, profit factors (don't use buggy code)
- ✅ Total P&L, max drawdown dollars (not affected)

### What Needs Re-Running

After applying fixes:
1. Re-run train period backtest
2. Re-run validation period backtest
3. Re-run test period backtest (if already run)
4. Recalculate all performance metrics
5. Regenerate all reports

**Do NOT trust any Sharpe/Sortino numbers from before this fix**

---

## REGRESSION PREVENTION

### Add Unit Tests

```python
# tests/test_metrics_bugfixes.py

def test_sharpe_no_duplicate_first_return():
    """Verify first return isn't duplicated in Sharpe calculation"""
    pnl = pd.Series([100, -50, 200], index=[0, 1, 2])
    metrics = PerformanceMetrics(starting_capital=100000)

    # Internal check: converted returns should have same length as pnl
    cumulative_portfolio_value = 100000 + pnl.cumsum()
    returns_pct = cumulative_portfolio_value.pct_change().dropna()

    assert len(returns_pct) == len(pnl), "Returns length should match P&L length"

    # First two returns should NOT be identical
    assert returns_pct.iloc[0] != returns_pct.iloc[1], "First return duplicated!"

def test_drawdown_analysis_no_crash():
    """Verify drawdown_analysis uses correct variable name"""
    cumulative_pnl = pd.Series([0, 100, 50, 150, 100, 200])
    metrics = PerformanceMetrics()

    # Should not raise NameError
    try:
        dd_metrics = metrics.drawdown_analysis(cumulative_pnl)
        assert dd_metrics['max_dd_value'] == -50
    except NameError as e:
        pytest.fail(f"drawdown_analysis crashed with NameError: {e}")
```

---

## FINAL CHECKLIST

- [ ] Apply Fix #5: Delete lines 119-122 in sharpe_ratio()
- [ ] Apply Fix #6: Delete lines 165-168 in sortino_ratio()
- [ ] Apply Fix #7: Change max_dd_idx → max_dd_position on line 358
- [ ] Run verification test (should NOT crash, returns length = pnl length)
- [ ] Add unit tests to prevent regression
- [ ] Re-run ALL backtests (train/validation/test)
- [ ] Verify Sharpe ratios are reasonable (not suspiciously high/low)
- [ ] Update all existing reports with corrected metrics

**Status:** Ready to apply fixes
**Priority:** CRITICAL - Cannot trust current results until fixed
**Estimated Time:** 10 minutes to fix + 2-3 hours to re-run backtests
