# TRAIN / VALIDATION / TEST METHODOLOGY

**Date:** 2025-11-18
**Version:** 1.0
**Purpose:** Establish proper out-of-sample validation methodology for quantitative research

---

## CRITICAL PRINCIPLE

**ZERO IN-SAMPLE CONTAMINATION.**

All parameters, bug fixes, and decisions MUST be derived from training data only. Validation and test sets are STRICTLY held out until methodology is locked.

---

## DATA SPLITS

### Train Period: 2020-01-01 to 2021-12-31 (2 years)
**Purpose:** Find bugs, derive all parameters, design strategies
**What happens here:**
- Infrastructure audit (find ALL bugs on train data)
- Calculate empirical peak timing
- Design exit strategies
- Determine risk parameters
- Optimize anything that needs optimization

**CRITICAL:** After train period completes, NO MORE CHANGES to methodology.

### Validation Period: 2022-01-01 to 2023-12-31 (2 years)
**Purpose:** Test if strategies work out-of-sample
**What happens here:**
- Apply train-period-derived parameters
- Test if exit timing works
- Validate infrastructure fixes
- Calculate out-of-sample metrics
- **If strategy fails:** Iterate on train period, re-test on validation

**Allowed:** Parameter refinement based on validation feedback, but MUST re-run full train→validation cycle

### Test Period: 2024-01-01 to 2024-12-31 (1 year)
**Purpose:** Final holdout validation (LOOK ONCE ONLY)
**What happens here:**
- Apply locked methodology from validation
- Calculate final metrics
- **NO CHANGES ALLOWED after looking at test results**
- This is what we'd present to investors

**CRITICAL:** Test period is HOLY. Once we look at it, we're done. No iterations.

---

## WORKFLOW

### Phase 1: Train Period Development

1. **Infrastructure Audit on Train Data**
   ```
   python scripts/audit_infrastructure_train.py \
     --start_date 2020-01-01 \
     --end_date 2021-12-31
   ```
   - Find ALL bugs using 2020-2021 data only
   - Fix bugs
   - Verify fixes on train data

2. **Parameter Derivation on Train Data**
   ```
   python scripts/derive_parameters_train.py \
     --start_date 2020-01-01 \
     --end_date 2021-12-31
   ```
   - Calculate median peak timing for each profile
   - Determine risk parameters
   - Design exit strategies
   - **Save all derived parameters to config file**

3. **Train Period Backtest**
   ```
   python scripts/backtest_train.py \
     --start_date 2020-01-01 \
     --end_date 2021-12-31 \
     --params_file params_train.json
   ```
   - Run full backtest with derived parameters
   - Document train period results
   - **These results are NOT validation**

### Phase 2: Validation Period Testing

1. **Load Train-Derived Parameters**
   ```
   params = load_train_parameters('params_train.json')
   ```
   - Exit days from train period
   - Risk parameters from train period
   - ZERO new parameter derivation

2. **Validation Backtest**
   ```
   python scripts/backtest_validation.py \
     --start_date 2022-01-01 \
     --end_date 2023-12-31 \
     --params_file params_train.json
   ```
   - Apply train parameters to 2022-2023 data
   - Calculate out-of-sample metrics
   - **If strategy fails here, it doesn't work**

3. **Validation Analysis**
   - Did exit timing work out-of-sample?
   - Are train metrics within 50% of validation metrics?
   - Does strategy degrade gracefully or collapse?

4. **Iteration Decision**
   - **If validation PASSES:** Proceed to test period
   - **If validation FAILS:**
     - Re-design on train period
     - Re-test on validation
     - Track iteration count

### Phase 3: Test Period (FINAL HOLDOUT)

1. **Lock Methodology**
   - Document exact parameters used
   - Freeze all code
   - Create immutable config file

2. **Test Backtest (RUN ONCE ONLY)**
   ```
   python scripts/backtest_test.py \
     --start_date 2024-01-01 \
     --end_date 2024-12-31 \
     --params_file params_final.json
   ```
   - Apply validated methodology to 2024
   - Calculate final metrics
   - **NO LOOKING UNTIL METHODOLOGY IS LOCKED**

3. **Present Results**
   - Train metrics
   - Validation metrics
   - Test metrics (FINAL)
   - Degradation analysis

---

## IMPLEMENTATION REQUIREMENTS

### Config File Format

```json
{
  "train_period": {
    "start": "2020-01-01",
    "end": "2021-12-31"
  },
  "validation_period": {
    "start": "2022-01-01",
    "end": "2023-12-31"
  },
  "test_period": {
    "start": "2024-01-01",
    "end": "2024-12-31"
  },
  "parameters_derived_from": "train",
  "exit_days": {
    "Profile_1_LDG": 7,
    "Profile_2_SDG": 5,
    "Profile_3_CHARM": 3,
    "Profile_4_VANNA": 8,
    "Profile_5_SKEW": 5,
    "Profile_6_VOV": 7
  },
  "derivation_method": "median_peak_timing",
  "train_period_trades": 400,
  "train_period_peak": 220000,
  "locked_date": "2025-11-18"
}
```

### Backtest Script Modifications

**Current:** `scripts/backtest_with_full_tracking.py` uses ALL data

**Required:** Three separate scripts:
1. `scripts/backtest_train.py` - Train period only
2. `scripts/backtest_validation.py` - Validation period only
3. `scripts/backtest_test.py` - Test period only

Each script MUST:
- Load data for specified period ONLY
- Apply parameters from config file
- Save results to period-specific directory
- Never peek at other periods

### Quality Gates

**Before proceeding to validation:**
- [ ] All bugs fixed on train data
- [ ] Parameters derived from train data only
- [ ] Train backtest runs clean
- [ ] Methodology documented
- [ ] Config file saved

**Before proceeding to test:**
- [ ] Validation results acceptable
- [ ] Methodology locked
- [ ] No further parameter changes
- [ ] Code frozen

**After test period:**
- [ ] Results documented
- [ ] Degradation analysis complete
- [ ] **NO MORE CHANGES**

---

## DEGRADATION METRICS

**Expected degradation train→validation→test:**
- Sharpe ratio: -20% to -40% typical
- Capture rate: -10% to -30% typical
- Win rate: -5% to -15% typical

**Red flags:**
- Sharpe ratio drops >50%: Severe overfitting
- Capture rate flips sign: Strategy doesn't work
- Win rate drops >20%: Entry logic overfit

---

## ANTI-PATTERNS TO AVOID

### ❌ WRONG: Parameter tuning on validation
```python
# Train period: exit_day = 7
# Validation results bad, so change to 5
# Re-run validation → looks better!
# This is OVERFITTING TO VALIDATION
```

### ✅ RIGHT: Re-derive on train, re-test on validation
```python
# Train period: exit_day = 7
# Validation results bad
# Go back to train period, re-analyze peak timing
# Find error in derivation, fix it
# Re-derive: exit_day = 5 from train data
# Re-test on validation with new parameter
```

### ❌ WRONG: Peeking at test period
```python
# Run test backtest out of curiosity
# Results look bad, change something
# Re-run test
# Test period is now contaminated
```

### ✅ RIGHT: Test once only
```python
# Lock methodology based on validation
# Run test ONCE
# Accept results, good or bad
# Present to investors: "This is true out-of-sample"
```

---

## SUCCESS CRITERIA

**Minimum bar (strategy works):**
- Validation Sharpe > 0.5
- Validation capture rate > 10%
- Test Sharpe within 30% of validation
- No sign flips across periods

**Good outcome:**
- Validation Sharpe > 1.0
- Validation capture rate > 15%
- Test metrics within 20% of validation
- Consistent behavior across periods

**Excellent outcome:**
- Validation Sharpe > 1.5
- Validation capture rate > 20%
- Test metrics match validation
- Strategy improves in test period (lucky)

---

## CURRENT STATUS

**Status:** Methodology designed, not yet implemented

**Next Steps:**
1. Archive all previous backtest results (contaminated)
2. Implement train/validation/test split scripts
3. Run Phase 1 (train period) infrastructure audit
4. Derive parameters from train data only
5. Test on validation period
6. If validation passes, run test period ONCE

---

**Approved:** 2025-11-18
**Methodology:** Non-negotiable
**Philosophy:** Real quant shop standards, not YouTube scam
