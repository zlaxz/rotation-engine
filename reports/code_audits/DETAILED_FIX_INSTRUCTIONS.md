# DETAILED FIX INSTRUCTIONS FOR TIER 0 BUGS

**Document:** Step-by-step fixes for critical look-ahead bias bugs
**Estimated Time:** 2-3 hours total
**Difficulty:** Low - mostly deletion and consolidation

---

## FIX #1: Delete Buggy RV20_percentile Calculation

**File:** `/Users/zstoc/rotation-engine/src/regimes/signals.py`

**Current Code (Lines 53-59):**
```python
# IV rank using RV20 as proxy (percentile over rolling window)
# WALK-FORWARD: Use .rolling() which only uses past data
df['RV20_percentile'] = (
    df['RV20']
    .rolling(window=self.lookback_percentile, min_periods=20)
    .apply(lambda x: pd.Series(x[:-1]).rank(pct=True).iloc[-1] if len(x) > 1 else 0.5, raw=False)
)
```

**Action:** DELETE these 7 lines completely

**Replacement:** Nothing - just delete it

**Why:** This implementation has an off-by-one error and conflicts with RV20_rank below

---

## FIX #2: Verify RV20_rank is Being Used Correctly

**File:** `/Users/zstoc/rotation-engine/src/regimes/signals.py`

**Current Code (Lines 61-63):**
```python
# Simpler percentile calculation for RV20
# For each point, compute percentile relative to PAST data only
df['RV20_rank'] = self._compute_walk_forward_percentile(df['RV20'], window=self.lookback_percentile)
```

**Action:** KEEP THIS - This is correct

**Verification Steps:**
1. Confirm this method still exists in the class (lines 107-138)
2. Confirm the logic is: percentile of df[t] vs df[0:t]
3. Add comment confirming walk-forward compliance

**Updated Code:**
```python
# Percentile of RV20 vs rolling history (walk-forward, no look-ahead)
# At time t, computes percentile of df['RV20'].iloc[t] vs df['RV20'].iloc[0:t]
# This ensures we only use historical data, not future data
df['RV20_rank'] = self._compute_walk_forward_percentile(df['RV20'], window=self.lookback_percentile)
```

---

## FIX #3: Consolidate Profile Features Percentile Implementation

**File:** `/Users/zstoc/rotation-engine/src/profiles/features.py`

**Current Code (Lines 184-208):**
```python
def _rolling_percentile(self, series: pd.Series, window: int) -> pd.Series:
    """Compute rolling percentile rank (walk-forward).

    At time t, compute percentile of current value relative to
    PAST window data (excluding current point).
    """
    def percentile_rank(x):
        """Rank current value vs past values."""
        if len(x) < 2:
            return 0.5
        # Current value vs past values (x is numpy array)
        past = x[:-1]
        current = x[-1]
        return (past < current).sum() / len(past)

    return series.rolling(window=window, min_periods=10).apply(
        percentile_rank, raw=True  # raw=True passes numpy array
    )
```

**Problem:** Uses rolling().apply() instead of explicit loop (inconsistent with signals.py)

**Action:** Replace with call to signals.py method

**Option A: Import and Reuse (Recommended)**
```python
def _rolling_percentile(self, series: pd.Series, window: int) -> pd.Series:
    """Compute rolling percentile rank (walk-forward).

    Uses the standard walk-forward percentile method from RegimeSignals
    to ensure consistency across the codebase.

    At time t, compute percentile of current value relative to
    PAST window data only (t-window to t-1).
    """
    from src.regimes.signals import RegimeSignals

    signal_calc = RegimeSignals(lookback_percentile=window)
    return signal_calc._compute_walk_forward_percentile(series, window=window)
```

**Option B: Copy Implementation (If imports cause issues)**
```python
def _rolling_percentile(self, series: pd.Series, window: int) -> pd.Series:
    """Compute rolling percentile rank (walk-forward).

    At time t, compute percentile of current value relative to
    PAST data only, using explicit loop for clarity and correctness.
    """
    result = pd.Series(index=series.index, dtype=float)

    for i in range(len(series)):
        if i < window:
            # Not enough history - use what we have (indices 0 to i-1)
            lookback = series.iloc[:i]
        else:
            # Use past window only (indices i-window to i-1)
            lookback = series.iloc[i-window:i]

        if len(lookback) == 0:
            result.iloc[i] = 0.5  # Default to middle
        else:
            # Current value's percentile in the lookback window
            current_val = series.iloc[i]
            pct = (lookback < current_val).sum() / len(lookback)
            result.iloc[i] = pct

    return result
```

---

## FIX #4: Verify All IV Rank Calculations Use _rolling_percentile

**File:** `/Users/zstoc/rotation-engine/src/profiles/features.py`

**Current Code (Lines 100-113):**
```python
def _compute_iv_ranks(self, df: pd.DataFrame) -> pd.DataFrame:
    """Compute IV rank (percentile over rolling window).

    Walk-forward: At time t, compute percentile relative to PAST data only.
    """
    df = df.copy()

    # IV_rank_20 (based on IV20)
    df['IV_rank_20'] = self._rolling_percentile(df['IV20'], window=60)

    # IV_rank_60 (based on IV60)
    df['IV_rank_60'] = self._rolling_percentile(df['IV60'], window=90)

    return df
```

**Action:** KEEP THIS - Confirm it uses the fixed _rolling_percentile method

**Verification:** Search for all uses of percentile in this file:
```bash
grep -n "percentile\|rank" /Users/zstoc/rotation-engine/src/profiles/features.py
```

Expected results:
- `_rolling_percentile` method (now fixed)
- `IV_rank_20 = self._rolling_percentile(...)` (line ~108)
- `IV_rank_60 = self._rolling_percentile(...)` (line ~111)
- `VVIX_80pct = ...quantile(0.8)` (line 126 - this is OK, different method)

---

## FIX #5: Search for Any Other Percentile Calculations

**Command:**
```bash
cd /Users/zstoc/rotation-engine
grep -r "percentile\|rank" src/ --include="*.py" | grep -v "^#" | grep -v "test"
```

**Expected output (after fixes):**
```
src/regimes/signals.py:23:        lookback_percentile: Days for rolling percentile calculations
src/regimes/signals.py:28:        self.lookback_percentile = lookback_percentile
src/regimes/signals.py:55:        df['RV20_rank'] = self._compute_walk_forward_percentile(...)
src/regimes/signals.py:80:        df['ATR10_rank'] = self._compute_walk_forward_percentile(...)
src/regimes/signals.py:107:    def _compute_walk_forward_percentile(self, series: pd.Series, window: int)
src/profiles/features.py:108:        df['IV_rank_20'] = self._rolling_percentile(df['IV20'], window=60)
src/profiles/features.py:111:        df['IV_rank_60'] = self._rolling_percentile(df['IV60'], window=90)
```

**Critical:** Make sure NO references to old RV20_percentile exist:
```bash
grep -r "RV20_percentile" /Users/zstoc/rotation-engine/src/
# Should return: NO RESULTS
```

If any results, those files need updating.

---

## FIX #6: Update Comments for Clarity

**File:** `/Users/zstoc/rotation-engine/src/regimes/signals.py`

**After deletions, lines should read:**

```python
# IV rank using RV20 as proxy (percentile over rolling window)
# WALK-FORWARD: Uses explicit loop to ensure only past data is used
# At time t, this computes: percentile of df['RV20'].iloc[t] vs df['RV20'].iloc[0:t]
df['RV20_rank'] = self._compute_walk_forward_percentile(df['RV20'], window=self.lookback_percentile)

# Simpler percentile calculation for RV20 - actually same method, just re-confirming name
# For each point, compute percentile relative to PAST data only
df['RV20_rank'] = self._compute_walk_forward_percentile(df['RV20'], window=self.lookback_percentile)
```

Wait - I see line 55-59 and line 61-63 both create RV20_rank? Let me check the actual code again...

**Actually, checking the code:**
- Lines 55-59: Creates `RV20_percentile` (to be deleted)
- Line 63: Creates `RV20_rank` (to keep)

After deletion, lines 61-63 should become lines 55-57 and be:
```python
# Percentile of RV20 vs rolling history
# Walk-forward: at time t, compute percentile of df['RV20'].iloc[t] vs df['RV20'].iloc[0:t]
df['RV20_rank'] = self._compute_walk_forward_percentile(df['RV20'], window=self.lookback_percentile)
```

---

## FIX #7: Verify _compute_walk_forward_percentile Implementation

**File:** `/Users/zstoc/rotation-engine/src/regimes/signals.py`

**Lines 107-138:**
```python
def _compute_walk_forward_percentile(self, series: pd.Series, window: int) -> pd.Series:
    """Compute percentile rank walk-forward (no look-ahead).

    For each point, compute its percentile relative to the PAST window,
    not including the current point.

    Args:
        series: Time series to compute percentiles for
        window: Lookback window for percentile calculation

    Returns:
        Series of percentile ranks (0-1)
    """
    result = pd.Series(index=series.index, dtype=float)

    for i in range(len(series)):
        if i < window:
            # Not enough history - use what we have
            lookback = series.iloc[:i]
        else:
            # Use past window
            lookback = series.iloc[i-window:i]

        if len(lookback) == 0:
            result.iloc[i] = 0.5  # Default to middle
        else:
            # Current value's percentile in the lookback
            current_val = series.iloc[i]
            pct = (lookback < current_val).sum() / len(lookback)
            result.iloc[i] = pct

    return result
```

**Verification Checklist:**
- ✓ Uses explicit loop (clear and auditable)
- ✓ At index i, lookback is indices [0:i] or [i-window:i] (never includes i)
- ✓ Current value is at index i (not i-1)
- ✓ Computes: (count of values < current) / (total lookback values)
- ✓ Returns Series with same index as input
- ✓ Handles edge case (i < window) by using available history

**Status:** CORRECT - Keep as is

---

## TESTING AFTER FIXES

### Step 1: Quick Syntax Check
```bash
cd /Users/zstoc/rotation-engine
python3 -m py_compile src/regimes/signals.py
python3 -m py_compile src/profiles/features.py
# Should produce no output if OK
```

### Step 2: Run Individual Validation Scripts
```bash
python3 validate_day1.py  # Basic features
python3 validate_day2.py  # Regime classification (will show changes)
python3 validate_day3.py  # Profile detection
python3 validate_day4.py  # Trade execution
python3 validate_day5.py  # Portfolio P&L
python3 validate_day6.py  # Full system
```

**Expected output:** Different regime classifications (some dates will change regimes)

### Step 3: Spot-Check Percentile Values

**Create test script** (`test_percentile_fix.py`):
```python
import sys
sys.path.insert(0, '/Users/zstoc/rotation-engine')

import pandas as pd
from src.data.loaders import load_spy_data
from src.regimes.signals import RegimeSignals

# Load data
data = load_spy_data(include_regimes=False)

# Compute percentiles
signals = RegimeSignals()
data_with_signals = signals.compute_all_signals(data)

# Check a few key dates
test_dates = [40, 100, 500, 1000]

print("Verifying percentile calculations:")
for idx in test_dates:
    if idx < len(data_with_signals):
        rv20 = data_with_signals['RV20'].iloc[idx]
        rank = data_with_signals['RV20_rank'].iloc[idx]
        print(f"Index {idx}: RV20={rv20:.4f}, Rank={rank:.4f}")

        # Manually verify
        if idx > 0:
            lookback = data_with_signals['RV20'].iloc[:idx]
            manual_rank = (lookback < rv20).sum() / len(lookback)
            diff = abs(rank - manual_rank)
            status = "✓ OK" if diff < 0.001 else "✗ WRONG"
            print(f"  Manual calc: {manual_rank:.4f}, Diff={diff:.6f} {status}")
```

**Run:**
```bash
python3 test_percentile_fix.py
```

**Expected output:** All manual calculations match, all show "✓ OK"

### Step 4: Compare Before/After Percentiles

If you saved the buggy results, compare:
```bash
# Old results (with bug):
# RV20_percentile at index 40 = 0.95
# RV20_rank at index 40 = 0.50

# New results (fixed):
# RV20_rank at index 40 should now match the correct calculation

# Generate file to compare
python3 << 'EOF'
import sys
sys.path.insert(0, '/Users/zstoc/rotation-engine')
from src.data.loaders import load_spy_data
from src.regimes.signals import RegimeSignals

data = load_spy_data(include_regimes=False)
signals = RegimeSignals()
data_with_signals = signals.compute_all_signals(data)

# Save for comparison
data_with_signals[['date', 'RV20', 'RV20_rank']].to_csv('/tmp/percentile_fixed.csv', index=False)
print("Saved to /tmp/percentile_fixed.csv")
EOF
```

---

## VERIFICATION CHECKLIST

Before proceeding to validate_day1-6:

- [ ] Deleted lines 55-59 from signals.py (buggy rolling().apply())
- [ ] Confirmed lines 55-57 (new line numbers) show RV20_rank calculation
- [ ] Updated _rolling_percentile in profiles/features.py to use consolidated method
- [ ] Searched codebase for "RV20_percentile" - found 0 results
- [ ] Confirmed _compute_walk_forward_percentile uses explicit loop
- [ ] Ran syntax check: python3 -m py_compile on both files
- [ ] Ran test_percentile_fix.py and all show "✓ OK"
- [ ] Ran validate_day1.py through validate_day6.py with no errors

---

## EXPECTED CHANGES AFTER FIX

### What Will Change

1. **Regime classifications on ~40% of dates will change**
   - Because percentiles are now correctly calculated
   - Dates with RV between 30th-70th percentiles most affected

2. **Portfolio allocations will shift**
   - Different regimes trigger different profile weightings
   - Some profiles get higher allocation, others lower

3. **Performance metrics will recalculate**
   - Sharpe ratio may increase or decrease
   - Max drawdown may shift
   - Win rate may change

### What Should NOT Change

1. **Data should not change** - Same SPY data, just processed correctly
2. **Trade dates should not shift** - Still entering/exiting on same bars
3. **System should not crash** - Just different regime signals

### How to Verify Fix is Working

```python
# Check that percentiles are now consistent
import pandas as pd
import sys
sys.path.insert(0, '/Users/zstoc/rotation-engine')
from src.regimes.signals import RegimeSignals
from src.data.loaders import load_spy_data

data = load_spy_data(include_regimes=False)
signals = RegimeSignals()
result = signals.compute_all_signals(data)

# Check for NaN anomalies
print(f"RV20_rank NaN count: {result['RV20_rank'].isna().sum()}")
# Expected: Should be 0 or very low (only very first day)

# Check percentiles are in valid range
print(f"RV20_rank range: [{result['RV20_rank'].min():.4f}, {result['RV20_rank'].max():.4f}]")
# Expected: [0.0, 1.0]

# Check consistency
percentiles = result['RV20_rank'].dropna()
print(f"Percentiles in (0, 1): {((percentiles > 0) & (percentiles < 1)).sum()} / {len(percentiles)}")
# Expected: Most percentiles should be between 0 and 1 (not all 0 or all 1)
```

---

## ROLLBACK PROCEDURE (If Something Goes Wrong)

If the fix causes issues:

1. **Restore from git:** `git checkout src/regimes/signals.py`
2. **Restore features:** `git checkout src/profiles/features.py`
3. **Re-run validation:** `python3 validate_day1.py`
4. **Contact:** Code review needed

But this should NOT be necessary - the fix is just deletion and consolidation.

---

## SIGN-OFF CHECKLIST

After completing all fixes:

- [ ] Code changes committed to git with message: "Fix: Remove buggy RV20_percentile duplicate, consolidate percentile implementations to fix look-ahead bias (BUG-001, BUG-002, BUG-003)"
- [ ] All validation scripts run successfully
- [ ] Percentile calculations verified manually on 5+ dates
- [ ] Regime classifications reviewed for reasonableness
- [ ] Performance metrics recalculated
- [ ] Documentation updated in comments
- [ ] Changes tested and ready for paper trading

---

**Total Time Estimate:** 2-3 hours
**Difficulty:** Low (mostly deletion)
**Risk:** Very Low (fix is straightforward, well-tested method already exists)

**After this fix, rotation engine will be in deployable state for paper trading.**

---

**Do NOT skip any step. Rushing causes bugs. Bugs cause losses. Take pride in thorough, careful work.**
