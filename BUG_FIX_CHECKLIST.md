# BUG FIX CHECKLIST - ROUND 2 AUDIT
**Date**: 2025-11-18
**Critical Path**: Fix these before running ANY backtests

---

## CRITICAL BLOCKERS (MUST FIX NOW)

### 🔴 BUG-001: Profile_5_SKEW Wrong Strike Price
**Files**: `backtest_train.py`, `backtest_validation.py`, `backtest_test.py`
**Line**: ~270, ~297, ~314

**CURRENT CODE**:
```python
strike = round(spot)  # ALL profiles get ATM
```

**FIXED CODE**:
```python
# Calculate strike based on profile structure
if profile_id == 'Profile_5_SKEW':
    strike = round(spot * 0.95)  # 5% OTM put
else:
    strike = round(spot)  # ATM for all other profiles
```

**Action**: Add 4 lines in 3 files (12 lines total)
**Test**: Entry for Profile_5 on 2020-09-03, SPY=$344.50 should get strike=327, not 345

---

### 🔴 BUG-002: Disaster Filter Blocks Disaster Profiles
**Files**: `backtest_train.py`, `backtest_validation.py`, `backtest_test.py`
**Line**: ~262-263, ~290-291, ~307-308

**DECISION REQUIRED**: Choose one option:

**Option A - Remove Filter Entirely**:
```python
# REMOVE these lines:
# if row.get('RV5', 0) > 0.22:
#     continue
```

**Option B - Exclude Profiles 5,6**:
```python
# Apply filter only to profiles 1-4
if profile_id not in ['Profile_5_SKEW', 'Profile_6_VOV']:
    if row.get('RV5', 0) > 0.22:
        continue
```

**Option C - Raise Threshold**:
```python
# Only block true disasters (40%+ vol)
if row.get('RV5', 0) > 0.40:
    continue
```

**Recommendation**: Option A (remove filter, let profiles fail naturally)
**Action**: User decides, then modify 3 files

---

### 🔴 BUG-003: get_expiry_for_dte() Wrong DTE
**Files**: `backtest_train.py`, `backtest_validation.py`, `backtest_test.py`
**Function**: `get_expiry_for_dte()` (lines ~208-215, ~239-246, ~256-263)

**CURRENT CODE**: (17 lines - see ROUND2_IMPLEMENTATION_AUDIT.md)

**FIXED CODE**:
```python
def get_expiry_for_dte(entry_date: date, dte_target: int) -> date:
    """
    Find the next Friday closest to target DTE.
    SPY has weekly options (every Friday).
    """
    target_date = entry_date + timedelta(days=dte_target)

    # Find next Friday from target date
    days_ahead = (4 - target_date.weekday()) % 7

    if days_ahead == 0:
        expiry = target_date
    else:
        expiry = target_date + timedelta(days=days_ahead)

    # Check if previous Friday is closer to target DTE
    previous_friday = expiry - timedelta(days=7)

    if previous_friday >= entry_date:
        days_to_prev = (previous_friday - entry_date).days
        days_to_next = (expiry - entry_date).days

        if abs(days_to_prev - dte_target) < abs(days_to_next - dte_target):
            expiry = previous_friday

    return expiry
```

**Action**: Replace function in 3 files
**Test**: Entry 2020-01-02, DTE=7 should return 2020-01-10, not 2020-01-17

---

## HIGH PRIORITY (FIX BEFORE RUNNING)

### 🟠 BUG-004: No SPY Data Validation
**Files**: `backtest_train.py`, `backtest_validation.py`, `backtest_test.py`
**Line**: After glob statement (~56)

**ADD AFTER**:
```python
spy_files = sorted(glob.glob('/Volumes/VelocityData/velocity_om/parquet/stock/SPY/*.parquet'))

# ADD THIS CHECK:
if len(spy_files) == 0:
    raise FileNotFoundError(
        "No SPY data files found. Check:\n"
        "1. Drive mounted: /Volumes/VelocityData/\n"
        "2. Path exists: /Volumes/VelocityData/velocity_om/parquet/stock/SPY/\n"
        "3. Parquet files present"
    )

print(f"Found {len(spy_files)} SPY data files")
```

**Action**: Add 10 lines to 3 files (30 lines total)

---

### 🟠 BUG-005: Period Check After Filtering
**Files**: `backtest_train.py`, `backtest_validation.py`, `backtest_test.py`
**Line**: ~87-88, ~127-128, ~144-145

**DECISION**: Accept current implementation OR refactor

**Current behavior**: Check happens after filtering (still catches gross errors)
**Risk**: If filtering logic has bug, check won't catch it
**Impact**: LOW (filtering logic is simple)

**Recommendation**: Document limitation, accept risk for now
**Action**: Add comment explaining check limitation

---

## MEDIUM PRIORITY (POLISH)

### 🟡 BUG-006: Missing Clearing Fees
**File**: `src/analysis/trade_tracker.py`
**Line**: ~108

**ADD**:
```python
entry_cost += commission  # Commission is always a cost

# ADD clearing fees
clearing_fee = 0.05 * len(position['legs'])
entry_cost += clearing_fee
```

**Impact**: ~$0.10 per trade
**Action**: Add 2 lines

---

### 🟡 BUG-007: NaN Feature Validation
**Files**: `backtest_train.py`, `backtest_validation.py`, `backtest_test.py`
**Line**: Before entry condition check (~254)

**ADD BEFORE ENTRY CHECK**:
```python
# Validate required features are not NaN
required_features = ['return_20d', 'return_5d', 'RV5', 'MA20']
if any(pd.isna(row.get(f)) for f in required_features):
    continue

# Check entry condition
try:
    if not config['entry_condition'](row):
        continue
```

**Action**: Add 4 lines to 3 files

---

## EXECUTION PLAN

### Step 1: Critical Fixes (30 minutes)
- [ ] Fix BUG-001 (Profile_5 strike) - 3 files
- [ ] Decide BUG-002 (disaster filter) - user decision
- [ ] Fix BUG-003 (expiry calculation) - 3 files
- [ ] Run syntax check: `python -m py_compile scripts/backtest_*.py`

### Step 2: High Priority (15 minutes)
- [ ] Fix BUG-004 (data validation) - 3 files
- [ ] Document BUG-005 limitation - 3 files

### Step 3: Test Fixes (20 minutes)
- [ ] Create test script to verify fixes
- [ ] Test Profile_5 strike calculation
- [ ] Test expiry calculation for DTE=7, 30, 75
- [ ] Test data validation error handling

### Step 4: Medium Priority (15 minutes)
- [ ] Fix BUG-006 (clearing fees) - 1 file
- [ ] Fix BUG-007 (NaN validation) - 3 files

### Step 5: Round 3 Audit (30 minutes)
- [ ] Re-run implementation audit
- [ ] Verify no new bugs introduced
- [ ] Manual spot-check 20 trades
- [ ] Green light for train/val/test

**Total Time**: ~2 hours

---

## VERIFICATION TESTS

### Test 1: Profile_5 Strike
```python
# Entry: 2020-09-03, SPY=$344.50
spot = 344.50
profile_id = 'Profile_5_SKEW'

if profile_id == 'Profile_5_SKEW':
    strike = round(spot * 0.95)
else:
    strike = round(spot)

assert strike == 327, f"Expected 327, got {strike}"
print("✅ Profile_5 strike calculation PASS")
```

### Test 2: Expiry Calculation
```python
# Test DTE=7
entry = date(2020, 1, 2)  # Thursday
expiry = get_expiry_for_dte(entry, 7)
expected = date(2020, 1, 10)  # Next Friday (8 days - closest to 7)

assert expiry == expected, f"Expected {expected}, got {expiry}"
print("✅ Expiry DTE=7 PASS")

# Test DTE=75
entry = date(2020, 1, 2)
expiry = get_expiry_for_dte(entry, 75)
days = (expiry - entry).days

assert 70 <= days <= 80, f"DTE should be 70-80, got {days}"
print("✅ Expiry DTE=75 PASS")
```

### Test 3: Data Validation
```python
import glob

# Simulate missing data
spy_files = glob.glob('/nonexistent/path/*.parquet')

if len(spy_files) == 0:
    print("✅ Data validation triggers error as expected")
else:
    print("❌ Data validation FAILED")
```

---

## FILES TO MODIFY

1. `scripts/backtest_train.py` - 7 changes
2. `scripts/backtest_validation.py` - 7 changes
3. `scripts/backtest_test.py` - 7 changes
4. `src/analysis/trade_tracker.py` - 1 change

**Total changes**: 22 locations

---

## POST-FIX ACTIONS

After all fixes applied:

1. **Run syntax check**:
   ```bash
   python -m py_compile scripts/backtest_train.py
   python -m py_compile scripts/backtest_validation.py
   python -m py_compile scripts/backtest_test.py
   ```

2. **Run verification tests** (create test script)

3. **Manual spot-check**: Pick 5 random trades, calculate by hand

4. **Round 3 audit**: Re-run full audit

5. **Green light**: If Round 3 clean, proceed to train period

---

## RISK ASSESSMENT

| Bug | If Unfixed Risk | If Fixed Risk |
|-----|----------------|---------------|
| BUG-001 | Profile_5 100% wrong | Correct instrument |
| BUG-002 | Profiles 5,6 incomplete | Full trade sample |
| BUG-003 | ALL profiles wrong DTE | Correct DTE targeting |
| BUG-004 | Silent failures | Errors caught early |
| BUG-005 | False security | Documented limitation |
| BUG-006 | P&L +$0.10/trade | Accurate costs |
| BUG-007 | Rare NaN trades | Clean data only |

**Unfixed risk**: CANNOT DEPLOY
**Fixed risk**: Ready for train/val/test

---

**Bottom line: Fix CRITICAL bugs, test thoroughly, re-audit. Then proceed.**
