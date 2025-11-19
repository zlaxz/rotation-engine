# EXIT ENGINE V1 - CRITICAL BUGS QUICK REFERENCE

**Status:** 🔴 BLOCK DEPLOYMENT
**Found:** 2025-11-18
**Severity:** CRITICAL - Logic destroys winners, helps losers

---

## THE PROBLEM IN ONE SENTENCE

**Condition exits trigger on market CONSOLIDATION (normal behavior) instead of BREAKDOWN (actual risk), cutting winners before they hit profit targets.**

---

## CRITICAL BUGS

### BUG #1: Profiles 1 & 4 - Exit on Consolidation (Should Exit on Breakdown)

**Current Code:**
```python
# Line 197: Profile 1 (LDG)
if slope_ma20 <= 0:  # ❌ Triggers on flat market
    return True

# Line 249: Profile 4 (VANNA)
if slope_ma20 <= 0:  # ❌ Same issue
    return True
```

**Problem:** `<= 0` means ANY consolidation exits position, including:
- Flat markets (slope = 0)
- Minor pullbacks (slope = -0.001)
- Normal profit-taking (slope = -0.01)

**Fix:**
```python
# Require ACTUAL downtrend, not consolidation
if slope_ma20 < -0.015:  # -1.5% slope = real breakdown
    return True
```

---

### BUG #2: Profile 6 (VOV) - Inverted Exit Logic

**Current Code:**
```python
# Line 278: Exits when vol COMPRESSES (wrong direction)
if rv10 / rv20 < 1.0:
    return True
```

**Problem:**
- Strategy buys vol in compression (`RV10 < RV20`)
- Should exit when vol EXPANDS (thesis realized)
- Currently exits when vol STILL COMPRESSED (thesis still valid)

**Fix:**
```python
# Exit when vol EXPANDS (sell high)
if rv10 / rv20 > 1.05:  # 5% expansion threshold
    return True
```

---

### BUG #3: Profiles 2, 3, 5 - Stub Implementations

**Current Code:**
```python
def _condition_exit_profile_2(...):
    return False  # ❌ Never triggers

def _condition_exit_profile_3(...):
    return False  # ❌ Never triggers

def _condition_exit_profile_5(...):
    return False  # ❌ Never triggers
```

**Problem:** Asymmetric behavior
- Profiles WITH conditions: Exit early on consolidation (bad)
- Profiles WITHOUT conditions: Hold to profit targets (good)

**Fix:** Either implement properly OR delete condition exits entirely

---

## WHY THIS DESTROYS WINNERS

**Example: Profile 1 Winner**

| Day | Trend | P&L | What Happens |
|-----|-------|-----|--------------|
| 0 | Enter on +2% uptrend | -$500 (entry cost) | Position opened |
| 1-3 | Strong trend | +$200 (40%) | Below TP1 (50%), holding |
| 4 | Market consolidates | +$200 (40%) | `slope_MA20 = -0.005` |
| 4 | **CONDITION EXIT TRIGGERS** | +$200 | ❌ **FORCED EXIT** |
| 5-7 | Trend resumes | Would be +$300 (60%) | ✅ Would have hit TP1 |
| 8-10 | Continues | Would be +$500 (100%) | ✅ Would have hit TP2 |

**Result:** Exit at +40% instead of +100% (destroyed 60% of winner)

---

## WHY VALIDATION DEGRADED -415%

**Train Period (2020-2021):** Strong trends, few consolidations
- Condition exits rarely triggered (trends didn't reverse)
- Risk stops helped losers
- **Net: +40% improvement**

**Validation Period (2022-2023):** Choppy, consolidating market
- Condition exits triggered constantly (many false slope reversals)
- Winners cut early at +30-40%
- Losers still helped by risk stops
- **Net: -415% degradation** (conditions destroyed it)

---

## IMMEDIATE RECOMMENDATION

### Option 1: DELETE Exit Engine V1, Use Phase 1 (RECOMMENDED)

**Why:**
- Phase 1 = pure time-based exits (7-14 days based on empirical peaks)
- ZERO parameters to overfit
- No condition logic to break
- Expected: 15-25% capture rate (vs current -1.8%)
- SAFE and SIMPLE

**Action:**
```bash
# Use existing ExitEngine (Phase 1) from exit_engine.py
# Already implemented, already tested
# Just needs deployment to full period
```

### Option 2: Fix Exit Engine V1 (HIGH RISK)

**Required fixes:**
1. Change `slope_ma20 <= 0` to `slope_ma20 < -0.015` (Profiles 1, 4)
2. Invert VOV logic: `rv10/rv20 > 1.05` (Profile 6)
3. Add 2-day confirmation period (prevent single-day exits)
4. Implement stub conditions OR remove them
5. Re-run train/validation
6. Accept that conditions may still overfit

**Estimated time:** 4-6 hours
**Risk:** Medium (may still overfit to train period)

---

## FILES TO FIX

**If pursuing Option 2:**

1. `/Users/zstoc/rotation-engine/src/trading/exit_engine_v1.py`
   - Lines 197: Profile 1 slope threshold
   - Lines 249: Profile 4 slope threshold
   - Lines 278: Profile 6 VOV inversion
   - Lines 212, 225, 255: Implement or delete stubs

2. **Add confirmation tracking:**
   - Track consecutive bad days per trade
   - Require 2-3 days before exit
   - Prevents noise-triggered exits

---

## BOTTOM LINE

**Exit Engine V1 as implemented will LOSE MONEY in production.**

**Recommendation:** Use Phase 1 time-based exits instead (already working, already tested, zero overfitting risk).

**If you insist on Exit Engine V1:** Fix all bugs above, re-validate, and accept higher overfitting risk.

---

**Audit Date:** 2025-11-18
**Auditor:** Chief Quant
**Decision Required:** Phase 1 or Fixed V1?
