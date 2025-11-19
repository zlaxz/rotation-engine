# RED TEAM AUDIT: exit_sweep_pnl_based.py

**Auditor:** Claude (Strategy Logic Auditor mode)
**Date:** 2025-11-18
**File:** `/Users/zstoc/rotation-engine/scripts/exit_sweep_pnl_based.py`
**Mission:** Find bugs that corrupt results or crash execution

---

## EXECUTIVE SUMMARY

**STATUS: ✗ CRITICAL BUG FOUND - RESULTS INVALID**

Found **3 bugs** (1 CRITICAL, 1 HIGH, 1 MEDIUM) that corrupt results.

**CRITICAL bugs that invalidate results:**
1. ✗ Peak calculation uses look-ahead bias (lines 76, 152)
   - Compares exit PnL to peak from ENTIRE path (including future days)
   - Makes early exits look terrible (comparing to unreachable peaks)
   - Biases analysis toward longer holding periods
   - **ALL capture rate calculations are WRONG**

**HIGH bugs that mislead:**
2. ✗ Average days calculation off-by-one (lines 85, 96, 179, 190)
   - Days are 0-indexed, but code doesn't add +1 to convert to actual days held
   - All holding periods understated by 1 day

**MEDIUM code quality:**
3. ⚠️ Unused variable delta_win_rate (line 101)

**Recommendation:** DO NOT TRUST CURRENT RESULTS. Fix CRITICAL #1, re-run analysis.

---

## BUG REPORT

### CRITICAL #1: Peak Calculation Includes Future Data (Look-Ahead Bias)

**Location:** Lines 76, 152

**Code:**
```python
# Line 76 (Fixed Days)
peak_pnl = max(day['mtm_pnl'] for day in path)

# Line 152 (Trailing Stops)
peak_pnl = max(day['mtm_pnl'] for day in path)
```

**Bug:** Peak calculation uses ENTIRE path including days after exit.

**Example:**
```
Day 0: $100
Day 1: $200
Day 2: $500  ← Peak (but we exit day 2, can't know this yet!)
Day 3: $300
Day 4: $100

If exit_day=2:
  exit_pnl = $500
  peak_pnl = $500  ← CORRECT by accident

If exit_day=1:
  exit_pnl = $200
  peak_pnl = $500  ← WRONG! We didn't hold until day 2, can't use its peak
  Capture rate = 200/500 = 40% ← INFLATED (real peak was $200)
```

**Impact:**
- Capture rates are UNDERSTATED (comparing to unrealistic peak)
- Makes early exits look worse than they are
- Inflates "peak potential" metric

**Fix:**
```python
# For fixed days
exit_idx = min(exit_day, len(path) - 1)
exit_pnl = path[exit_idx]['mtm_pnl']
peak_pnl = max(day['mtm_pnl'] for day in path[:exit_idx+1])  # Only up to exit

# For trailing stops
exit_pnl = path[exit_idx]['mtm_pnl']
peak_pnl = max(day['mtm_pnl'] for day in path[:exit_idx+1])  # Only up to exit
```

**Severity:** CRITICAL - Invalidates all capture rate calculations

---

### CRITICAL #2: Trailing Stop Activation Logic Bug

**Location:** Lines 156, 163-167

**Code:**
```python
activated = False
running_peak = -999999  # ← BUG: Wrong initial value

for idx, day in enumerate(path):
    pnl = day['mtm_pnl']

    if pnl >= activation_k:
        activated = True

    if activated:
        running_peak = max(running_peak, pnl)  # ← BUG HERE
```

**Bug:** `running_peak` starts at -999999, so first `max()` call will set it to current PnL even if current PnL is negative.

**Example:**
```
Activation K = $300
Trail D = $100

Day 0: PnL = -$50
Day 1: PnL = $350  ← Activates
Day 2: PnL = $200  ← Should NOT exit (350 - 200 = 150 > trail_d)

What actually happens:
Day 1: activated=True, running_peak = max(-999999, 350) = 350 ✓
Day 2: pnl=200, running_peak=350, 200 <= 350-100? YES, EXIT ✓

What if activation happens at negative PnL? (Edge case):
Day 0: PnL = -$50
Day 1: PnL = $350  ← Activates
Day 2: PnL = $320

Before activation:
  running_peak = -999999

At Day 1 (activation):
  running_peak = max(-999999, 350) = 350 ✓

This actually works CORRECTLY because max() fixes the -999999.
```

**Wait - is this actually a bug?**

Let me trace through more carefully:

```python
# Scenario: Never activates
activation_k = 500
path = [100, 200, 150]

activated = False
running_peak = -999999

Day 0: pnl=100
  pnl >= 500? NO
  activated? NO
  Skip tracking

Day 1: pnl=200
  pnl >= 500? NO
  activated? NO
  Skip tracking

Day 2: pnl=150
  pnl >= 500? NO
  activated? NO
  exit_idx = 2 (last day) ✓
```

This works fine - if never activated, we hold to end.

**Scenario: Activates then trails:**
```python
activation_k = 150
trail_d = 100
path = [{mtm_pnl: 100}, {mtm_pnl: 200}, {mtm_pnl: 50}]

Day 0: pnl=100
  100 >= 150? NO
  activated = False

Day 1: pnl=200
  200 >= 150? YES
  activated = True
  running_peak = max(-999999, 200) = 200
  200 <= 200 - 100? NO (200 <= 100? NO)

Day 2: pnl=50
  50 >= 150? YES (already activated, doesn't matter)
  activated = True
  running_peak = max(200, 50) = 200
  50 <= 200 - 100? YES (50 <= 100? YES)
  EXIT at idx=2 ✓
```

**Actually this works correctly.** The -999999 is fine because `max()` will immediately replace it.

**RETRACTING CRITICAL #2 - Not a bug.**

---

### CRITICAL #2 (REVISED): Division by Zero Risk

**Location:** Lines 91, 185

**Code:**
```python
# Line 91
if peak_pnl > 0:
    pct_captured = (exit_pnl / peak_pnl) * 100
    peak_pct_captured.append(pct_captured)
```

**Bug:** If `peak_pnl == 0` exactly, we skip it. But what if `peak_pnl < 0`?

**Edge Case:**
```
Trade loses money entire path:
Day 0: -$100
Day 1: -$200
Day 2: -$150

peak_pnl = max(-100, -200, -150) = -100
exit_pnl = -150 (exit day 2)

Line 90: if peak_pnl > 0?  NO (-100 > 0 = False)
We skip calculation ✓

This is handled correctly!
```

**RETRACTING - Not a bug, handled by if statement.**

---

### CRITICAL #2 (ACTUAL): Trailing Stop Exit on Same Day as Activation

**Location:** Lines 163-172

**Code:**
```python
if pnl >= activation_k:
    activated = True

if activated:
    running_peak = max(running_peak, pnl)

    # Trail stop triggered?
    if pnl <= running_peak - trail_d:
        exit_idx = idx
        break
```

**Bug:** Can trigger exit on SAME day as activation if activation PnL is low and we immediately drop.

**Example:**
```
activation_k = 150
trail_d = 100

Day 0: pnl = 100
Day 1: pnl = 150  ← Activates
  activated = True
  running_peak = max(-999999, 150) = 150
  150 <= 150 - 100? (150 <= 50?) NO ✓

Day 2: pnl = 40
  running_peak = max(150, 40) = 150
  40 <= 150 - 100? (40 <= 50?) YES
  EXIT ✓
```

This seems correct - we activate at $150, then if we drop $100 from that peak, we exit.

**Edge case - activate and immediately drop:**
```
activation_k = 150
trail_d = 200

Day 0: pnl = 100
Day 1: pnl = 150  ← Activates
  activated = True
  running_peak = max(-999999, 150) = 150
  150 <= 150 - 200? (150 <= -50?) NO ✓
  Continue

Day 2: pnl = -60
  running_peak = max(150, -60) = 150
  -60 <= 150 - 200? (-60 <= -50?) YES!
  EXIT at day 2 ✓
```

This is correct behavior - once activated, if we drop trail_d from the peak, we exit.

**What if activation happens exactly at peak, then drops trail_d SAME day?**

This can't happen because we check `pnl <= running_peak - trail_d` AFTER updating running_peak with current pnl.

Same-day activation + exit:
```
activation_k = 150
trail_d = 0  # Zero trail distance

Day 0: pnl = 100
Day 1: pnl = 150
  activated = True
  running_peak = max(-999999, 150) = 150
  150 <= 150 - 0? (150 <= 150?) YES
  EXIT at day 1 (same day as activation)
```

**Is this a bug?** With trail_d=0, it means "exit immediately on activation". This is technically correct but probably not intended behavior. If trail_d=0 is in the sweep parameters, every trade would exit on activation day.

**Checking sweep parameters:** Lines 135-136
```python
for activation_k in [150, 300, 500]:
    for trail_d in [100, 200, 300]:
```

Minimum trail_d is 100, so this edge case won't happen. **Not a bug.**

---

### HIGH #1: Incorrect Index Logic in Fixed Days

**Location:** Line 79

**Code:**
```python
exit_idx = min(exit_day, len(path) - 1)
```

**Bug:** `exit_day` is 0-indexed or 1-indexed? Code treats it as index, but parameter names suggest days.

**Analysis:**
```python
for exit_day in [2, 3, 5, 7, 10]:  # Line 60
```

These are DAYS (1-indexed: day 2 = second day).

```python
exit_idx = min(exit_day, len(path) - 1)  # Line 79
```

If `exit_day=2`, `exit_idx=2`, we access `path[2]` = 3rd element (0-indexed) = day 2 (if path[0]=day 0).

**Checking path structure from backtest code:**

Need to verify what `day` field contains. Looking at line 85:
```python
total_days_held += path[exit_idx]['day']
```

So `path[idx]['day']` tells us which day number it is.

**Scenario:**
```
path = [
  {'day': 0, 'mtm_pnl': 100},
  {'day': 1, 'mtm_pnl': 200},
  {'day': 2, 'mtm_pnl': 300}
]

exit_day = 2  (meaning "exit on day 2")
exit_idx = min(2, 3-1) = min(2, 2) = 2
path[2] = {'day': 2, 'mtm_pnl': 300} ✓ CORRECT
```

**But what if path uses 1-indexed days?**
```
path = [
  {'day': 1, 'mtm_pnl': 100},  ← First day
  {'day': 2, 'mtm_pnl': 200},
  {'day': 3, 'mtm_pnl': 300}
]

exit_day = 2  (meaning "exit on day 2")
exit_idx = 2
path[2] = {'day': 3, 'mtm_pnl': 300} ✗ WRONG (wanted day 2, got day 3)
```

**Need to check backtest code to see if days start at 0 or 1.**

**Assumption for now:** Days start at 0, so path[0]['day'] = 0.

If days start at 1, then this is a HIGH severity off-by-one error.

**Recommendation:** Verify `path[idx]['day']` numbering scheme. If it starts at 1, need:
```python
exit_idx = min(exit_day - 1, len(path) - 1)  # Convert day to index
```

**Severity:** HIGH - Off-by-one errors in backtesting are deadly

---

### HIGH #2: Average Days Calculation Off-By-One (CONFIRMED)

**Location:** Lines 85, 96, 179, 190

**Code:**
```python
# Line 85 (Fixed days)
total_days_held += path[exit_idx]['day']

# Line 179 (Trailing stops)
total_days_held += path[exit_idx]['day']

# Line 96, 190 (Both)
avg_days = total_days_held / total_count if total_count > 0 else 0
```

**Bug:** Days are 0-indexed, so `path[exit_idx]['day']` understates actual holding period.

**VERIFIED:** Days are 0-indexed (path[0]['day'] = 0).

**Examples:**
- Trade held for 1 day (exit at day 0) → day=0, avg_days=0 ✗ (should be 1)
- Trade held for 2 days (exit at day 1) → day=1, avg_days=1 ✗ (should be 2)
- Trade held for 3 days (exit at day 2) → day=2, avg_days=2 ✗ (should be 3)

**All holding periods are understated by 1 day.**

**Fix:**
```python
# Lines 85, 179
total_days_held += path[exit_idx]['day'] + 1  # +1 to convert index to count
```

**Impact:**
- Avg days display is wrong by -1 day for all rules
- Affects comparison to baseline (baseline shows 14.0, but should be 15.0 if using same bug)
- Misleading when comparing exit rules

**Severity:** HIGH - Misrepresents holding period, affects rule comparison

---

### MEDIUM #1: Unused Calculation

**Location:** Line 101

**Code:**
```python
delta_win_rate = win_rate - (win_count / total_count * 100)  # TODO: Calculate baseline win rate
```

**Bug:** This calculates `delta_win_rate = win_rate - win_rate = 0` always.

**Impact:** Variable is never used, so doesn't affect output. But indicates incomplete code.

**Fix:** Either calculate baseline win rate or remove this line.

**Severity:** MEDIUM - Code smell, doesn't affect results

---

### MEDIUM #2: Missing Validation - Empty Path Handling

**Location:** Lines 71-73, 147-149

**Code:**
```python
path = trade.get('path', [])
if not path:
    continue
```

**Analysis:** This correctly handles empty paths by skipping them. ✓

**But what about single-day paths?**

```python
path = [{'day': 0, 'mtm_pnl': 100}]

# Fixed days with exit_day=2
exit_idx = min(2, 1-1) = min(2, 0) = 0 ✓
```

This works correctly - we exit on day 0 (only day available).

**What about peak calculation with 1 element?**
```python
peak_pnl = max(day['mtm_pnl'] for day in path)
# With 1 element: max([100]) = 100 ✓
```

Works correctly.

**Not a bug - properly handled.**

---

### MEDIUM #3: Trailing Stop Never Activates Case

**Location:** Lines 154-173

**Code:**
```python
exit_idx = len(path) - 1  # Default: last day

for idx, day in enumerate(path):
    # ... activation logic ...
    if activated:
        # ... trailing stop logic ...
        if pnl <= running_peak - trail_d:
            exit_idx = idx
            break

exit_pnl = path[exit_idx]['mtm_pnl']
```

**Scenario:** Trailing stop never activates (PnL never reaches activation_k).

**Result:** `exit_idx = len(path) - 1` (last day) ✓

This is correct - if stop never activates, we hold to end.

**Not a bug - properly handled.**

---

## VERIFICATION COMPLETED

### 1. Day Numbering Scheme (VERIFIED)

**VERIFIED:** Days are **0-indexed**. `path[0]['day'] = 0`

**Evidence from results.json:**
```python
path[0]: {'day': 0, 'date': '2020-04-30', ...}
path[1]: {'day': 1, 'date': '2020-05-01', ...}
path[2]: {'day': 2, 'date': '2020-05-04', ...}
```

**Impact on bugs:**
- HIGH #1 (exit day indexing): ✓ NOT A BUG (correctly using day as index)
- HIGH #2 (avg days calculation): ✗ IS A BUG (need to add +1 for actual days held)

**Updated bug analysis:**

---

## CRITICAL BUG VERIFICATION

### Testing CRITICAL #1 (Peak Calculation Look-Ahead)

**Manual verification:**

```python
# Simulate trade path
path = [
    {'day': 0, 'mtm_pnl': 100},
    {'day': 1, 'mtm_pnl': 300},  # Peak here
    {'day': 2, 'mtm_pnl': 200},
    {'day': 3, 'mtm_pnl': 150}
]

# Exit day 1 (second day)
exit_day = 1
exit_idx = min(1, 4-1) = 1
exit_pnl = path[1]['mtm_pnl'] = 300

# CURRENT CODE:
peak_pnl = max(day['mtm_pnl'] for day in path)
         = max(100, 300, 200, 150) = 300
capture_rate = 300/300 = 100%  ✓ Correct by accident

# Exit day 0 (first day)
exit_day = 0
exit_idx = 0
exit_pnl = path[0]['mtm_pnl'] = 100

# CURRENT CODE:
peak_pnl = 300  (looks at future days!)
capture_rate = 100/300 = 33%  ✗ WRONG

# CORRECT CODE:
peak_pnl = max(day['mtm_pnl'] for day in path[:1])  # Only day 0
         = 100
capture_rate = 100/100 = 100%  ✓ RIGHT
```

**CONFIRMED: CRITICAL #1 is a real bug that corrupts capture rate calculations.**

---

## FINAL BUG COUNT (VERIFIED)

**CRITICAL: 1**
1. ✗ Peak calculation uses look-ahead bias (lines 76, 152) - **INVALIDATES RESULTS**

**HIGH: 1**
1. ✗ Average days calculation off-by-one (lines 85, 96, 179, 190) - Misrepresents holding periods

**MEDIUM: 1**
1. ⚠️ Unused delta_win_rate calculation (line 101) - Code smell, no impact

**Total bugs that corrupt results: 2 (1 CRITICAL + 1 HIGH)**
**Total code quality issues: 1 MEDIUM**

**Day numbering verified:** 0-indexed (path[0]['day'] = 0) ✓

---

## DEPLOYMENT DECISION

**STATUS: ⚠️ DO NOT DEPLOY - CRITICAL BUG FOUND**

**Current results are INVALID due to CRITICAL look-ahead bias.**

**Must fix before running:**
1. ✗ CRITICAL #1: Peak calculation look-ahead bias (lines 76, 152)
2. ✗ HIGH #2: Average days off-by-one (lines 85, 96, 179, 190)
3. ⚠️ MEDIUM #1: Remove unused delta_win_rate (line 101)

**Recommended fix order:**
1. Fix CRITICAL #1 (peak calculation) - HIGHEST PRIORITY
2. Fix HIGH #2 (avg days +1)
3. Remove MEDIUM #1 (unused code)
4. Re-run sweep with corrected code
5. Compare results (expect MAJOR changes for early exit capture rates)

---

## ESTIMATED IMPACT

**CRITICAL #1 impact on results:**

For early exits (day 0, 1, 2):
- Current code: Compares exit PnL to max PnL over entire 14-day path
- This UNDERSTATES capture rate for early exits
- Makes early exits look worse than they actually are
- Could bias results toward longer hold times

**Example:**
```
Trade that peaks at day 1 ($300) then decays:
Day 0: $100
Day 1: $300 (peak)
Day 2: $200
Day 3: $150
...
Day 14: $50

Exit day 1:
  Current: 300/300 = 100% ✓ (correct by accident)

Exit day 0:
  Current: 100/300 = 33% ✗ (wrong - comparing to unreachable peak)
  Correct: 100/100 = 100% ✓

Exit day 2:
  Current: 200/300 = 67% ✗ (wrong - day 2 exit can't capture day 1 peak)
  Correct: 200/200 = 100% ✓ (day 2 was the peak up to exit)
```

**This bug makes early exits look terrible because we're comparing them to peaks they never had a chance to capture.**

**CRITICAL: Results are INVALID. Fix before drawing conclusions.**

---

## RECOMMENDED FIXES

### Fix for CRITICAL #1: Peak Calculation Look-Ahead Bias

**File:** `/Users/zstoc/rotation-engine/scripts/exit_sweep_pnl_based.py`

**Fix 1A - Lines 75-80 (Fixed Days):**
```python
# BEFORE
# Find peak
peak_pnl = max(day['mtm_pnl'] for day in path)

# Exit at specified day or last day
exit_idx = min(exit_day, len(path) - 1)
exit_pnl = path[exit_idx]['mtm_pnl']

# AFTER
# Exit at specified day or last day
exit_idx = min(exit_day, len(path) - 1)
exit_pnl = path[exit_idx]['mtm_pnl']

# Find peak UP TO EXIT (no look-ahead)
peak_pnl = max(day['mtm_pnl'] for day in path[:exit_idx+1])
```

**Fix 1B - Lines 150-176 (Trailing Stops):**
```python
# BEFORE (line 152)
# Find peak
peak_pnl = max(day['mtm_pnl'] for day in path)

# Trailing stop logic
activated = False
running_peak = -999999
exit_idx = len(path) - 1  # Default: last day
...
exit_pnl = path[exit_idx]['mtm_pnl']

# AFTER
# REMOVE line 152 (peak_pnl = max(...))
# ADD peak calculation AFTER exit_idx is determined:

# Trailing stop logic
activated = False
running_peak = -999999
exit_idx = len(path) - 1  # Default: last day

for idx, day in enumerate(path):
    pnl = day['mtm_pnl']
    if pnl >= activation_k:
        activated = True
    if activated:
        running_peak = max(running_peak, pnl)
        if pnl <= running_peak - trail_d:
            exit_idx = idx
            break

exit_pnl = path[exit_idx]['mtm_pnl']
# Find peak UP TO EXIT (no look-ahead)
peak_pnl = max(day['mtm_pnl'] for day in path[:exit_idx+1])
```

### Fix for HIGH #2: Average Days Off-By-One

**Fix 2 - Lines 85, 179:**
```python
# BEFORE (line 85)
total_days_held += path[exit_idx]['day']

# AFTER
total_days_held += path[exit_idx]['day'] + 1  # +1 to convert index to days

# BEFORE (line 179)
total_days_held += path[exit_idx]['day']

# AFTER
total_days_held += path[exit_idx]['day'] + 1  # +1 to convert index to days
```

### Fix for MEDIUM #1: Remove Unused Code

**Fix 3 - Line 101:**
```python
# REMOVE this line (unused variable)
delta_win_rate = win_rate - (win_count / total_count * 100)  # TODO: Calculate baseline win rate
```

---

## TEST CASES TO VERIFY FIX

After fixing CRITICAL #1, run these test cases:

### Test Case 1: Early Exit Peak
```python
path = [
    {'day': 0, 'mtm_pnl': 500},  # Peak here
    {'day': 1, 'mtm_pnl': 300},
    {'day': 2, 'mtm_pnl': 100}
]

exit_day = 0
Expected:
  exit_pnl = 500
  peak_pnl = 500 (not 500 from looking ahead)
  capture_rate = 100%
```

### Test Case 2: Late Peak Unreachable
```python
path = [
    {'day': 0, 'mtm_pnl': 100},
    {'day': 1, 'mtm_pnl': 200},
    {'day': 2, 'mtm_pnl': 150},
    {'day': 3, 'mtm_pnl': 800}  # Peak way later
]

exit_day = 1
Expected:
  exit_pnl = 200
  peak_pnl = 200 (not 800!)
  capture_rate = 100% (we captured all available peak)
```

### Test Case 3: Declining Trade
```python
path = [
    {'day': 0, 'mtm_pnl': 300},
    {'day': 1, 'mtm_pnl': 200},
    {'day': 2, 'mtm_pnl': 100}
]

exit_day = 2
Expected:
  exit_pnl = 100
  peak_pnl = 300 (peak was day 0)
  capture_rate = 33%
```

---

## CONCLUSION

**This script has a CRITICAL bug that invalidates all results.**

The peak calculation look-ahead bias makes early exits look worse than they are by comparing them to peaks that occur AFTER the exit. This biases the entire analysis toward longer holding periods.

**DO NOT TRUST CURRENT RESULTS.**

Fix CRITICAL #1, verify day numbering scheme, then re-run analysis.

**Next steps:**
1. Verify day numbering in backtest code
2. Apply fixes for CRITICAL #1
3. Fix HIGH #1 or HIGH #2 based on verification
4. Re-run sweep
5. Compare results to current (expect major changes for early exits)

---

**Audit complete. Red team out.**
