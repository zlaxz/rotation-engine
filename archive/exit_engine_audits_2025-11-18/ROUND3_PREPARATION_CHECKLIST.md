# ROUND 3 PREPARATION CHECKLIST

**Next Session: Fix and Verify the 4 Remaining Critical Bugs**

---

## BEFORE YOU START

Read these documents IN ORDER:

- [ ] Read `EXIT_ENGINE_V1_ROUND2_AUDIT.md` (understand the full picture)
- [ ] Read `ROUND2_CRITICAL_BUGS_TO_FIX.md` (know what to change)
- [ ] Read `ROUND2_CODE_LOCATIONS.md` (see code with context)
- [ ] Review test evidence in `/tmp/test_exit_engine_bugs.py`

**Time:** 20-30 minutes to understand all issues

---

## THE 4 BUGS TO FIX

### Bug #2: TP1 Tracking Collision

**File:** `src/trading/exit_engine_v1.py`
**Line:** 327
**Current:**
```python
trade_id = trade_data['entry']['entry_date']
```
**Change to:**
```python
trade_id = f"{trade_data['entry']['entry_date']}_{trade_data['entry']['strike']}_{trade_data['entry']['expiry']}"
```
**Verification:** Two same-day trades now track separately

---

### Bug #3: Empty Path Crash

**File:** `src/trading/exit_engine_v1.py`
**Line:** 361 (INSERT BEFORE)
**Insert this code:**
```python
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
**Then keep the rest:**
```python
last_day = daily_path[-1]
```
**Verification:** No crash on empty path

---

### Bug #4: Credit Position P&L Sign Error

**File:** `src/trading/exit_engine_v1.py`
**Lines:** 338 and 367

**Line 338 - Change from:**
```python
pnl_pct = mtm_pnl / entry_cost
```
**To:**
```python
pnl_pct = mtm_pnl / abs(entry_cost)
```

**Line 367 - Change from:**
```python
final_pnl_pct = last_day['mtm_pnl'] / entry_cost
```
**To:**
```python
final_pnl_pct = last_day['mtm_pnl'] / abs(entry_cost)
```

**Verification:** Loss positions show negative pnl_pct

---

### Bug #5: Fractional Exit P&L Not Scaled

**File:** `src/trading/exit_engine_v1.py`
**Line:** 354

**Current:**
```python
if should_exit:
    return {
        'exit_day': day_idx,
        'exit_reason': reason,
        'exit_pnl': mtm_pnl,
        'exit_fraction': fraction,
        'entry_cost': entry_cost,
        'pnl_pct': pnl_pct
    }
```

**Change to:**
```python
if should_exit:
    # Scale exit_pnl by fraction for partial exits
    exit_pnl = mtm_pnl * fraction if fraction < 1.0 else mtm_pnl
    return {
        'exit_day': day_idx,
        'exit_reason': reason,
        'exit_pnl': exit_pnl,
        'exit_fraction': fraction,
        'entry_cost': entry_cost,
        'pnl_pct': pnl_pct
    }
```

**Verification:** Partial exits report half P&L

---

## STEP-BY-STEP FIX PROCEDURE

### Step 1: Backup Current Code
```bash
cp src/trading/exit_engine_v1.py src/trading/exit_engine_v1.py.backup
```

### Step 2: Apply Bug #2 Fix
- [ ] Open `src/trading/exit_engine_v1.py`
- [ ] Go to line 327
- [ ] Replace trade_id line with new version
- [ ] Save file

### Step 3: Apply Bug #3 Fix
- [ ] Go to line 361
- [ ] Insert empty path guard BEFORE `last_day = daily_path[-1]`
- [ ] Save file

### Step 4: Apply Bug #4 Fix - Location 1
- [ ] Go to line 338
- [ ] Change `/ entry_cost` to `/ abs(entry_cost)`
- [ ] Save file

### Step 5: Apply Bug #4 Fix - Location 2
- [ ] Go to line 367
- [ ] Change `/ entry_cost` to `/ abs(entry_cost)`
- [ ] Save file

### Step 6: Apply Bug #5 Fix
- [ ] Go to line 354
- [ ] Add code to scale exit_pnl by fraction
- [ ] Save file

---

## VERIFICATION PROCEDURE

### Step 1: Run Test Suite
```bash
python3 /tmp/test_exit_engine_bugs.py
```

**Expected output:**
```
TEST 1: Credit Position P&L Calculation
  STATUS: PASS

TEST 2: TP1 Tracking Collision
  STATUS: PASS

TEST 3: Empty Path Crash
  STATUS: PASS

TEST 4: Fractional Exit P&L Scaling
  STATUS: PASS

============================================================
SUMMARY
============================================================
Credit Position P&L: PASS
TP1 Tracking Collision: PASS
Empty Path Crash: PASS
Fractional Exit P&L: PASS
```

### Step 2: If Any Test Fails
- Review the specific failure
- Check your code change against the spec in `ROUND2_CODE_LOCATIONS.md`
- Look for typos or incomplete edits
- Verify line numbers match your file (they may have shifted)

### Step 3: Run Backtest
```bash
python3 scripts/apply_exit_engine_v1.py
```

Verify:
- [ ] No crashes
- [ ] Results show reasonable P&L
- [ ] No error messages
- [ ] Output files created

### Step 4: Sanity Check Results
- [ ] Check that no profile has extreme returns (>1000%)
- [ ] Check that P&L is reasonable relative to entry sizes
- [ ] Verify partial exits (TP1) reduce position sizes
- [ ] Credit positions show reasonable P&L

---

## DEBUGGING CHECKLIST

If tests fail, check:

### For BUG #2 Failure:
- [ ] Did you add both strike AND expiry to trade_id?
- [ ] Is there an underscore between date, strike, and expiry?
- [ ] Did you access the correct fields from trade_data['entry']?

### For BUG #3 Failure:
- [ ] Is the empty check BEFORE the [-1] access?
- [ ] Is the guard `if not daily_path:` exactly spelled?
- [ ] Does the return statement have all required fields?

### For BUG #4 Failure:
- [ ] Did you change BOTH line 338 AND 367?
- [ ] Is it `abs(entry_cost)` not `abs(entry_cost`?
- [ ] Did you keep the rest of the if statement intact?

### For BUG #5 Failure:
- [ ] Did you add the line `exit_pnl = mtm_pnl * fraction if fraction < 1.0 else mtm_pnl`?
- [ ] Did you change the return to use `exit_pnl` not `mtm_pnl`?
- [ ] Is the logic correct (multiply if < 1.0, otherwise use full)?

---

## WHEN ALL TESTS PASS

1. [ ] Commit changes with clear message:
```bash
git add src/trading/exit_engine_v1.py
git commit -m "fix: Apply Round 2 critical bug fixes (4 bugs)"
```

2. [ ] Create new backtest results:
```bash
python3 scripts/apply_exit_engine_v1.py
```

3. [ ] Archive old results:
```bash
mv data/backtest_results/exit_engine_v1_analysis.json \
   data/backtest_results/exit_engine_v1_analysis_before_round2_fix.json
```

4. [ ] Document the fixes:
   - Create `ROUND2_FIXES_APPLIED.md` with what was changed
   - Include test results showing all 4 tests pass

5. [ ] Next step: Run full validation phase

---

## QUALITY GATES - AFTER FIXES

After applying all fixes and passing tests, verify:

### Gate 1: Logic Audit
- [ ] All 4 bugs fixed with evidence in tests
- [ ] Code matches specification in ROUND2_CODE_LOCATIONS.md
- [ ] No new bugs introduced

### Gate 2: Edge Case Testing
- [ ] Empty path handled gracefully
- [ ] Same-day trades tracked separately
- [ ] Credit positions calculated correctly
- [ ] Partial exits report correct P&L

### Gate 3: P&L Accuracy
- [ ] No negative P&L flips sign
- [ ] Partial exits sum to correct total
- [ ] Credit positions show losses as negative
- [ ] Results match expectations

### Gate 4: Integration
- [ ] apply_exit_engine_v1.py runs without crash
- [ ] Results saved correctly
- [ ] No validation errors

---

## ESTIMATED TIME

- **Reading/Understanding:** 30 minutes
- **Applying Fixes:** 15 minutes
- **Running Tests:** 5 minutes
- **Verification:** 10 minutes
- **Commit/Document:** 5 minutes

**Total: 1 hour**

---

## DO NOT SKIP

- ❌ Don't skip reading the audit documents
- ❌ Don't skip running the test suite
- ❌ Don't skip verification
- ❌ Don't deploy without all 4 tests passing

---

## CONTINGENCY

If something goes wrong:

1. Restore backup:
```bash
cp src/trading/exit_engine_v1.py.backup src/trading/exit_engine_v1.py
```

2. Re-read the spec in ROUND2_CODE_LOCATIONS.md

3. Try again, line by line

4. If still stuck, review ROUND2_CRITICAL_BUGS_TO_FIX.md for exact code

---

## SUCCESS CRITERIA

After Round 3:
- [ ] All 4 bugs fixed
- [ ] All 4 tests pass
- [ ] Backtest runs without crash
- [ ] Results are reasonable
- [ ] Quality gates passed
- [ ] Changes committed

Then: Proceed to validation phase

---

**Status:** READY FOR NEXT SESSION
**Duration:** 1-2 hours
**Complexity:** LOW (straightforward replacements)
**Risk:** LOW (well-documented, verified)

Good luck. Fix these 4 bugs and we can move to validation.
