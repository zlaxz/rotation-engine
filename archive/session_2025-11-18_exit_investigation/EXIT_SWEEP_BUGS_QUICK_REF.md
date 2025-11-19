# EXIT SWEEP BUGS - QUICK REFERENCE

**File:** `/Users/zstoc/rotation-engine/scripts/exit_sweep_pnl_based.py`
**Status:** ✗ CRITICAL BUG - DO NOT TRUST RESULTS
**Date:** 2025-11-18

---

## BUGS FOUND

### ✗ CRITICAL #1: Peak Calculation Look-Ahead Bias
**Lines:** 76, 152
**Impact:** ALL capture rate calculations are WRONG

**Problem:**
```python
peak_pnl = max(day['mtm_pnl'] for day in path)  # Uses ENTIRE path
```

Early exits compare to peaks that happen AFTER the exit.

**Fix:**
```python
# Calculate peak AFTER determining exit_idx
peak_pnl = max(day['mtm_pnl'] for day in path[:exit_idx+1])  # Only up to exit
```

---

### ✗ HIGH #2: Average Days Off-By-One
**Lines:** 85, 96, 179, 190
**Impact:** All holding periods understated by 1 day

**Problem:**
```python
total_days_held += path[exit_idx]['day']  # Days are 0-indexed
```

Day 0 = 1 day held, but code reports 0 days.

**Fix:**
```python
total_days_held += path[exit_idx]['day'] + 1  # +1 to convert index to count
```

---

### ⚠️ MEDIUM #1: Unused Code
**Line:** 101

**Problem:**
```python
delta_win_rate = win_rate - (win_count / total_count * 100)  # Always = 0
```

**Fix:** Remove this line.

---

## IMPACT ANALYSIS

**Example of CRITICAL #1 bug:**

```
Trade path:
  Day 0: $100
  Day 1: $300 (peak)
  Day 2: $200
  Day 3: $150

Exit day 0:
  Current code:
    exit_pnl = $100
    peak_pnl = $300 (WRONG - looks at day 1 which we never reached)
    capture_rate = 33%

  Correct:
    exit_pnl = $100
    peak_pnl = $100 (only day 0 available)
    capture_rate = 100%
```

**This makes early exits look TERRIBLE compared to reality.**

---

## DEPLOYMENT DECISION

**DO NOT DEPLOY. FIX CRITICAL #1 FIRST.**

Current results are biased toward longer holding periods because early exits are penalized for not capturing peaks that occur after they exit.

---

## NEXT STEPS

1. Fix CRITICAL #1 (peak calculation)
2. Fix HIGH #2 (avg days +1)
3. Remove MEDIUM #1 (unused code)
4. Re-run sweep
5. Compare new results to old (expect MAJOR changes for early exits)

---

**Full audit:** `/Users/zstoc/rotation-engine/EXIT_SWEEP_RED_TEAM_AUDIT.md`
