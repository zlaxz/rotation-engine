# EXIT SWEEP - QUICK BUG FIX REFERENCE

**Status:** CRITICAL BUGS FOUND - ORIGINAL SCRIPT INVALID

---

## 5 BUGS FOUND (2 CRITICAL)

### CRITICAL BUG #1: Look-Ahead Bias (Lines 76, 152)

**What's Wrong:**
```python
# WRONG - Uses FUTURE data!
peak_pnl = max(day['mtm_pnl'] for day in path)
```

**Why It's Wrong:**
- `path` contains all bars from entry to END OF BACKTEST
- When testing 2-day exit, code looks at days 0-14 to find peak
- The peak often occurs DAYS AFTER the exit decision
- This biases all metrics downward and makes them invalid

**Example:**
```
Day 0: -$100
Day 1: +$50
Day 2: -$182  <-- EXIT DECISION MADE HERE
Day 3: -$267  <-- But code looks here
...
Day 14: +$5000 (FUTURE!) <-- And finds peak here
```

**The Fix (1 line each):**
```python
# CORRECT - Only look at past/current bars
peak_pnl = max(day['mtm_pnl'] for day in path[:exit_idx+1])
```

**Impact:** ALL capture_rate metrics are GARBAGE

---

### CRITICAL BUG #2: avg_peak_pct Excludes Losing Trades (Lines 90-92)

**What's Wrong:**
```python
# WRONG - Only includes winners
if peak_pnl > 0:
    pct_captured = (exit_pnl / peak_pnl) * 100
    peak_pct_captured.append(pct_captured)

avg_peak_pct = np.mean(peak_pct_captured)  # Average of winners only!
```

**Why It's Wrong:**
- Out of 349 trades: 279 have peak > 0, 70 have peak <= 0
- avg_peak_pct only averages the 279 winners
- Completely ignores 70 losing trades
- Makes mediocre rules look better than they are

**The Fix (1 line):**
```python
# CORRECT - Include all trades
if peak_pnl != 0:  # Changed from > 0 to != 0
    pct_captured = (exit_pnl / peak_pnl) * 100
    peak_pct_captured.append(pct_captured)
```

**Impact:** avg_peak_pct metric is biased and unreliable

---

### HIGH SEVERITY BUG #3: delta_win_rate Always Zero (Line 101)

**What's Wrong:**
```python
# WRONG - Calculates win_rate - win_rate = 0!
delta_win_rate = win_rate - (win_count / total_count * 100)
```

**Why It's Wrong:**
- `win_rate` was just calculated as `win_count / total_count * 100`
- Subtracting it from itself gives 0 every time
- Was supposed to be: `current_win_rate - baseline_win_rate`
- But baseline win rate not stored anywhere

**The Fix (calculate baseline first):**
```python
# Calculate baseline at start
baseline_win_count = 0
for ... trades ...:
    if baseline_exit_pnl > 0:
        baseline_win_count += 1
baseline_win_rate = baseline_win_count / baseline_trades * 100

# Then in loop:
delta_win_rate = win_rate - baseline_win_rate  # Now correct!
```

**Impact:** delta_win_rate always shows $0 improvement (misleading)

---

### MEDIUM BUG #4: Fragile Trailing Stop Init (Lines 156-157)

**What's Wrong:**
```python
running_peak = -999999  # Magic number!
```

**Why It's Not Great:**
- Works in practice but is fragile
- -999999 is unexplained
- Hard to debug if P&Ls change
- Assumes no trade will be worse than -$999,999

**The Fix (add comment):**
```python
# Initialize running_peak to extreme value to ensure first activation bar
# becomes the initial peak (all real P&Ls will exceed -999999)
running_peak = -999999
```

**Impact:** Code works but is unclear - risk if portfolio changes

---

### MEDIUM BUG #5: Path Length Edge Case (Line 79)

**What's Wrong:**
```python
exit_idx = min(exit_day, len(path) - 1)
```

**Why It's Not Great:**
- If path has 1 bar (entry day only) and exit_day=2:
  - exit_idx = min(2, 0) = 0 (exits on entry day!)
- Implicit logic, hard to understand intent
- One trade in data has path length = 1

**The Fix (explicit):**
```python
# Cap exit day to available path length
exit_idx = min(exit_day, len(path) - 1)
# Now explicitly:
peak_pnl = max(day['mtm_pnl'] for day in path[:exit_idx+1])
```

**Impact:** Minor - edge case handled correctly but unclearly

---

## DEPLOYMENT STATUS

### CANNOT USE ORIGINAL SCRIPT BECAUSE:

1. **Look-ahead bias** invalidates capture rate metrics
2. **Survivor bias** inflates avg_peak_pct
3. **Zero delta_win_rate** makes comparisons impossible
4. **All results are garbage** for decision-making

### MUST USE FIXED VERSION:
- File: `/Users/zstoc/rotation-engine/scripts/exit_sweep_pnl_based_FIXED.py`
- Contains all 5 bug fixes
- Add comment explaining each fix

---

## WHAT CHANGED IN FIXED VERSION

| Bug | Original Code | Fixed Code | Lines |
|-----|---------------|-----------|-------|
| #1 | `max(path)` | `max(path[:exit_idx+1])` | 76, 152 |
| #2 | `if peak_pnl > 0:` | `if peak_pnl != 0:` | 90-92 |
| #3 | Recalc win_rate | Calculate baseline first | 101 |
| #4 | No comment | Add explanation | 156-157 |
| #5 | Implicit | Explicit capping | 79 |

---

## TESTING BEFORE USE

```python
# Hand-verify with sample trade:
Trade:
  - Day 0: -$100
  - Day 1: +$50
  - Day 2: -$182
  - Day 3..14: ...future data...

Fixed code exit_day=2:
  peak_pnl = max(path[0:3]) = +$50 ✓ (not future data)
  exit_pnl = path[2] = -$182
  capture_rate = -182 / 50 = -364% ✓ (correct)

Original code exit_day=2:
  peak_pnl = max(path[0:15]) = +$5000 (WRONG - future!)
  exit_pnl = path[2] = -$182
  capture_rate = -182 / 5000 = -3.6% (WRONG - biased)
```

---

## FILES

- **Audit Report:** `/Users/zstoc/rotation-engine/AUDIT_EXIT_SWEEP_PNL_BASED.md`
- **Fixed Script:** `/Users/zstoc/rotation-engine/scripts/exit_sweep_pnl_based_FIXED.py`
- **Original (Broken):** `/Users/zstoc/rotation-engine/scripts/exit_sweep_pnl_based.py`

---

## RECOMMENDATION

1. **Delete** the original script (it's invalid)
2. **Use** the FIXED version for exit rule testing
3. **Add** unit tests to catch these bugs if you iterate
4. **Document** metric definitions clearly in output

**Do NOT use original script results for any strategic decision.**
