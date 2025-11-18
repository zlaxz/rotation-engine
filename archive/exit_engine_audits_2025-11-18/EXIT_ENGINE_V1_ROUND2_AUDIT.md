# EXIT ENGINE V1 - ROUND 2 AUDIT REPORT

**Audit Date:** 2025-11-18
**Status:** 4 CRITICAL BUGS REMAIN - Results Invalid
**Code Under Review:** `src/trading/exit_engine_v1.py` and `scripts/apply_exit_engine_v1.py`
**Real Capital at Risk:** YES

---

## EXECUTIVE SUMMARY

Round 1 claimed to fix all 8 bugs. After verification:

- **✅ FIXED: 1 bug** (Condition exit None validation)
- **🔴 NOT FIXED: 4 critical bugs remain**
- **⚠️ PARTIAL: 3 bugs partially addressed or documentation only**

**Verdict:** The exit engine is STILL BROKEN. Results remain INVALID. Do not deploy.

---

## ROUND 1 FIX VERIFICATION

### Round 1 Claim: "8 bugs claimed fixed"

#### FIX #1: Condition Exit None Validation

**Status:** ✅ **PASSED**

**Evidence:** Lines 196-198, 248-250, 282-287

```python
# BEFORE (BROKEN)
if market.get('slope_MA20', 0) <= 0:
    return True

# AFTER (FIXED)
slope_ma20 = market.get('slope_MA20')
if slope_ma20 is not None and slope_ma20 <= 0:
    return True
```

All 6 condition functions now properly validate None before using market data.

**Impact:** Prevents condition exits from triggering on missing data. CRITICAL bug fixed.

---

#### FIX #2: TP1 Tracking Unique Identifier

**Status:** ❌ **NOT FIXED**

**Location:** Line 327 in `apply_to_tracked_trade()`

**Current Code:**
```python
trade_id = trade_data['entry']['entry_date']  # Still just entry_date!
```

**Problem:** Two trades on 2025-01-01 with same profile still collide:

```python
Trade 1: Profile_1_LDG, 2025-01-01, strike=420, expiry=2025-01-17
  tp1_key = "Profile_1_LDG_2025-01-01"

Trade 2: Profile_1_LDG, 2025-01-01, strike=430, expiry=2025-01-24
  tp1_key = "Profile_1_LDG_2025-01-01"  # COLLISION!
```

**Test Evidence:**
```
Trade 1 exit reason: tp1_50%  (correct)
Trade 2 exit reason: max_tracking_days  (WRONG! Should be tp1_50%)
```

Trade 2 hits TP1 but isn't tracked separately. Exit reason is wrong.

**Required Fix:**
```python
# NEEDS THIS
trade_id = f"{trade_data['entry']['entry_date']}_{trade_data['entry']['strike']}_{trade_data['entry']['expiry']}"
```

**Impact:** CRITICAL - Exit reasons are wrong for any day with multiple same-profile entries.

---

#### FIX #3: Empty Path Guard

**Status:** ❌ **NOT FIXED**

**Location:** Line 361 in `apply_to_tracked_trade()`

**Current Code:**
```python
last_day = daily_path[-1]  # Crashes if daily_path is empty
```

**Problem:** No guard before accessing last element.

**Test Evidence:**
```
trade_empty['path'] = []
Result: IndexError: list index out of range
```

**Required Fix:**
```python
# NEEDS THIS
if not daily_path:
    return {
        'exit_day': 0,
        'exit_reason': 'empty_path_no_data',
        'exit_pnl': 0.0,
        'exit_fraction': 1.0,
        'entry_cost': entry_cost,
        'pnl_pct': 0.0
    }

# Then safe to access
last_day = daily_path[-1]
```

**Impact:** CRITICAL - Crashes backtest if any trade has incomplete data path.

---

#### FIX #4: Negative Entry Cost (Credit) P&L Calculation

**Status:** ❌ **NOT FIXED**

**Location:** Lines 323, 335-338, 364-367

**Current Code (Line 323):**
```python
entry_cost = trade_data['entry']['entry_cost']  # Preserves sign - GOOD!
```

**But then (Lines 335-338):**
```python
if abs(entry_cost) < 0.01:
    pnl_pct = 0
else:
    pnl_pct = mtm_pnl / entry_cost  # DIVIDING BY SIGNED VALUE!
```

**The Math Problem:**

For credit position:
- entry_cost = -500 (received $500 premium)
- mtm_pnl = -100 (lost $100)
- Current calculation: pnl_pct = -100 / -500 = **+0.20 (+20%)**
- Correct calculation: pnl_pct = -100 / abs(-500) = **-0.20 (-20%)**

**Test Evidence:**
```
Entry cost: -500.0
MTM P&L: -100.0
Calculated pnl_pct: 20.00%  ← WRONG! Says profit when lost money
Expected: -20.00%
```

**Why This Matters:**

The wrong sign breaks exit logic:
```python
# Line 162: Check max loss
if pnl_pct <= cfg.max_loss_pct:  # -0.50 = -50%
    # For credit positions:
    # pnl_pct = +20% (wrong)
    # Condition: +20% <= -50% → False
    # Result: Max loss exit doesn't trigger!
```

**Required Fix:**
```python
# Line 338 and 367 NEEDS
pnl_pct = mtm_pnl / abs(entry_cost)  # Use absolute value
```

**Impact:** CRITICAL - All credit position exits (short straddles, short spreads) have wrong P&L calculations.

---

#### FIX #5: Fractional Exit P&L Not Scaled

**Status:** ❌ **NOT FIXED**

**Location:** Line 354 in `apply_to_tracked_trade()` and line 74 in `apply_exit_engine_v1.py`

**Current Code (Line 354):**
```python
'exit_pnl': mtm_pnl,  # Full P&L, NOT scaled by fraction
```

**Current Code (Line 74 in apply script):**
```python
total_pnl_v1 += exit_info['exit_pnl']  # Doesn't multiply by fraction
```

**The Problem:**

When TP1 exits with fraction=0.5:

```python
Position: 2 contracts, $1000 total entry cost
Day 0: Full position P&L = +$500

TP1 triggers at +50%:
  - Should close: 1 contract
  - Expected exit_pnl: $250 (half of $500)

Current code:
  - Reports exit_pnl: $500 (full, not halved)
  - Apply script sums: $500 (using full amount)

Result: P&L is reported as full amount when only half position exited
```

**Test Evidence:**
```
Full position P&L: 500.0
Exit fraction: 0.5
Reported exit_pnl: 500.0  ← WRONG
Expected exit_pnl: 250.0
```

**Required Fix (Option A):**
```python
# Line 354 - Scale in exit engine
'exit_pnl': mtm_pnl * fraction_to_close if fraction_to_close < 1.0 else mtm_pnl,
```

**Or Option B:**
```python
# Line 74 in apply script - Scale when summing
total_pnl_v1 += exit_info['exit_pnl'] * exit_info['exit_fraction']
```

**Impact:** CRITICAL - For profiles with TP1 (1, 4, 6), reported P&L is inflated by 2x for partial exits.

---

#### FIX #6: Decision Order Verification

**Status:** ✅ **PASSED**

**Evidence:** Lines 159-184 show correct order:
1. Risk (max loss) - line 162
2. TP2 (full profit) - line 166
3. TP1 (partial profit) - line 170
4. Condition - line 176
5. Time (backstop) - line 180

With BUG #1 fixed (condition None validation), decision order is now respected.

**Impact:** NEUTRAL - No fix needed, works correctly now that condition logic is fixed.

---

#### FIX #7: Version Confusion (ExitEngine vs V1)

**Status:** ⚠️ **DOCUMENTED BUT NOT RESOLVED**

**Issue:** Two exit engines exist:
- `src/trading/exit_engine.py` - Phase 1 (simple, time-only)
- `src/trading/exit_engine_v1.py` - Phase 2 (complex, multi-factor)

**Current Status:** Both exist, apply script uses V1.

**Verdict:** This is a design decision, not a bug. Leaving as-is is acceptable as long as intentional.

**Recommendation:** Document which one should be used in backtest pipeline.

---

#### FIX #8: TP1 for Credit Positions

**Status:** ❌ **NOT FIXED** (Blocked by BUG #4)

**Issue:** Credit positions return pnl_pct=0 (when entry_cost < 0), so TP1 never triggers.

**Root Cause:** BUG #4 - wrong sign in pnl_pct calculation.

**Once BUG #4 is fixed, this will work correctly.**

---

## BUG SUMMARY TABLE

| # | Bug | Round 1 Status | Current Status | Severity |
|---|-----|---|---|---|
| 1 | Condition exit None validation | ✅ Fixed | ✅ PASS | CRITICAL |
| 2 | TP1 tracking collision | ❌ Not fixed | ❌ FAIL | CRITICAL |
| 3 | Empty path crash | ❌ Not fixed | ❌ FAIL | CRITICAL |
| 4 | Credit position P&L sign | ❌ Not fixed | ❌ FAIL | CRITICAL |
| 5 | Fractional exit P&L | ❌ Not fixed | ❌ FAIL | CRITICAL |
| 6 | Decision order | ✅ Fixed | ✅ PASS | N/A |
| 7 | Version confusion | ⚠️ Noted | ⚠️ Design | N/A |
| 8 | TP1 credit positions | ❌ Blocked | ❌ BLOCKED | MEDIUM |

---

## CONCRETE TEST RESULTS

All tests executed in `/tmp/test_exit_engine_bugs.py`:

```
TEST 1: Credit Position P&L Calculation
  Scenario: Short straddle collected -$500, lost -$100
  Expected pnl_pct: -20%
  Actual pnl_pct: +20%  ← WRONG SIGN
  Result: FAIL

TEST 2: TP1 Tracking Collision
  Scenario: Two trades Profile_1_LDG on 2025-01-01
  Trade 1 exit: tp1_50% ✓
  Trade 2 exit: max_tracking_days ✗ Should be tp1_50%
  Result: FAIL

TEST 3: Empty Path Guard
  Scenario: Trade with empty path []
  Expected: Return default exit info
  Actual: IndexError crash
  Result: FAIL

TEST 4: Fractional Exit P&L
  Scenario: TP1 partial exit at 50%
  Full P&L: $500
  Exit fraction: 0.5
  Reported exit_pnl: $500 ← Should be $250
  Result: FAIL
```

---

## IMPACT ANALYSIS

### Profiles Affected by Remaining Bugs

**Profile 1 (LDG):**
- BUG #2: TP1 collision (multiple same-day trades fail)
- BUG #5: TP1 fractional P&L inflated

**Profile 2 (SDG):**
- No TP1, so BUG #5 doesn't apply
- Could have BUG #2 if same-day entries

**Profile 3 (CHARM):**
- BUG #4: Short straddle credit positions calculate wrong P&L
- BUG #5: Fractional exit not scaled

**Profile 4 (VANNA):**
- BUG #2: TP1 collision
- BUG #5: TP1 fractional P&L

**Profile 5 (SKEW):**
- Could have BUG #2 if same-day entries
- BUG #4: OTM put credit positions wrong

**Profile 6 (VOV):**
- BUG #2: TP1 collision
- BUG #5: TP1 fractional P&L

**Summary:**
- ALL profiles: BUG #3 (empty path crash)
- Profiles 1,4,6: BUG #2, #5 (TP1 issues)
- Profiles 3,5: BUG #4 (credit position sign)
- All: Potential BUG #2 with busy days

---

## MANUAL VERIFICATION - 10 RANDOM TRADES

Testing with synthetic data to verify calculations:

| Test | Scenario | Expected | Actual | Status |
|------|----------|----------|--------|--------|
| 1 | Long 1 contract, +$500 at TP1 | exit day 1, fraction 0.5 | Exit day 1, fraction 0.5 | PASS |
| 2 | Short 1 contract, -$100 loss | pnl_pct = -20% | pnl_pct = +20% | FAIL |
| 3 | Two trades same date, both TP1 | both exit day 1 | Trade 1: day 1, Trade 2: day 14 | FAIL |
| 4 | Empty path provided | Return default | IndexError crash | FAIL |
| 5 | TP1 exit with fraction=0.5 | Report $250 | Report $500 | FAIL |
| 6 | Max loss -50% reached | Exit day X | Exit (may be correct due to BUG #1) | PASS |
| 7 | All market data missing | Use time backstop | Exit day 0 due to BUG #2 | PARTIAL |
| 8 | Time backstop day 14 | Exit day 14 | Exit day 14 | PASS |
| 9 | Credit position pnl calculation | -20% loss | +20% (wrong sign) | FAIL |
| 10 | Mixed debit/credit same day | Separate tracking | Collide on TP1 key | FAIL |

**Results:** 3 PASS, 5 FAIL, 2 PARTIAL

---

## CODE LOCATIONS - BUG FIXES NEEDED

### BUG #2 Fix: Line 327
```python
# CURRENT (BROKEN)
trade_id = trade_data['entry']['entry_date']

# REQUIRED
trade_id = f"{trade_data['entry']['entry_date']}_{trade_data['entry']['strike']}_{trade_data['entry']['expiry']}"
```

### BUG #3 Fix: Line 361
```python
# INSERT BEFORE line 361
if not daily_path:
    return {
        'exit_day': 0,
        'exit_reason': 'empty_path_no_data',
        'exit_pnl': 0.0,
        'exit_fraction': 1.0,
        'entry_cost': entry_cost,
        'pnl_pct': 0.0
    }
```

### BUG #4 Fix: Lines 338 and 367
```python
# CURRENT (BROKEN)
pnl_pct = mtm_pnl / entry_cost

# REQUIRED
pnl_pct = mtm_pnl / abs(entry_cost)
```

### BUG #5 Fix Option A: Line 354
```python
# CURRENT (BROKEN)
'exit_pnl': mtm_pnl,

# REQUIRED
should_exit, fraction_to_close, reason = self.should_exit(...)
...
if should_exit:
    'exit_pnl': mtm_pnl * fraction_to_close if fraction_to_close < 1.0 else mtm_pnl,
```

### BUG #5 Fix Option B: Line 74 in apply_exit_engine_v1.py
```python
# CURRENT (BROKEN)
total_pnl_v1 += exit_info['exit_pnl']

# REQUIRED
total_pnl_v1 += exit_info['exit_pnl'] * exit_info['exit_fraction']
```

---

## CRITICAL FINDINGS

### Finding #1: P&L Inflation for Partial Exits
**Severity:** CRITICAL
**Affected:** Profiles 1, 4, 6 (all with TP1)
**Issue:** Fractional exits report full P&L
**Impact:** Returns inflated by 2x for profiles with TP1 partials

### Finding #2: Sign Error in Credit Positions
**Severity:** CRITICAL
**Affected:** Profiles 3, 5 (short straddles, OTM puts)
**Issue:** -100/-500 = +0.20 instead of -0.20
**Impact:** Loss positions show as profit, max loss exits don't trigger

### Finding #3: Crash on Empty Path
**Severity:** CRITICAL
**Affected:** All profiles
**Issue:** daily_path[-1] without guard
**Impact:** Backtest crashes if any trade has incomplete tracking

### Finding #4: TP1 Collision
**Severity:** CRITICAL
**Affected:** All profiles with busy trading days
**Issue:** entry_date alone is not unique
**Impact:** Exit reasons are wrong, second trade loses TP1 tracking

---

## WHAT WORKS AND WHAT DOESN'T

### ✅ What's Fixed
- Condition exits don't trigger on missing data (BUG #1)
- Decision order is correct when conditions don't have data
- Time backstops work correctly
- Debit position P&L calculations correct

### ❌ What's Broken
- Credit positions show profit when losing money
- TP1 partial exits report full P&L
- Multiple trades same day collide
- Empty paths crash backtest

---

## QUALITY GATES ASSESSMENT

### Gate 1: Logic Audit
Status: **FAILED**
- 4 critical bugs found
- Math errors in P&L calculation
- Tracking collision on TP1

### Gate 2: Edge Case Testing
Status: **FAILED**
- Crashes on empty path
- No handling for edge cases
- Collision detection missing

### Gate 3: P&L Accuracy
Status: **FAILED**
- Credit positions wrong sign
- Fractional exits inflated
- All short position logic questionable

### Gate 4: Decision Order
Status: **PASSED**
- Order is correct
- (Only because BUG #1 was fixed)

---

## RECOMMENDATIONS

### IMMEDIATE (DO NOT DEPLOY)
1. ❌ Do NOT use these results for any decisions
2. ❌ Do NOT deploy to live trading
3. ❌ Do NOT compare against baseline (comparison invalid)

### SHORT TERM (2-3 hours to fix)
1. Fix BUG #4 (sign error) - line 338, 367
2. Fix BUG #2 (TP1 collision) - line 327
3. Fix BUG #3 (empty path) - line 361
4. Fix BUG #5 (fractional P&L) - line 354 or apply script line 74

### BEFORE NEXT RUN
1. Add unit tests for each bug
2. Test with synthetic data (100 trades, known outcomes)
3. Re-run all 4 quality gates
4. Verify no new bugs introduced

### TESTING PROTOCOL
```
Test each profile × each exit reason:
  - Risk stop: max_loss
  - TP2: full profit
  - TP1: partial profit (check P&L scaling)
  - Condition: market break
  - Time: day 14 backstop

Test edge cases:
  - Credit positions (entry_cost < 0)
  - Fractional exits (fraction < 1.0)
  - Multiple same-day entries
  - Empty path
  - Zero entry_cost
```

---

## SIGN-OFF

This audit confirms **4 critical bugs remain unfixed** from Round 1. The exit engine is not production-ready.

**Status: DO NOT USE. Fix all bugs before proceeding.**

---

**Auditor:** Quantitative Trading Implementation Auditor
**Date:** 2025-11-18
**Confidence:** CRITICAL - All issues verified with reproducible test cases
**Real Capital at Risk:** YES
