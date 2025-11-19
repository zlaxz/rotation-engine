# PRE-TRAIN PHASE CHECKLIST
**Status:** MUST COMPLETE BEFORE RUNNING backtest_train.py

---

## SECTION 1: ANSWER CRITICAL QUESTIONS

### Question 1: Exit Timing Derivation Method
**Current Status:** Unknown

**You must specify:**
```python
# How will backtest_train.py derive exit timing?

METHOD = "median_peak_timing"  # or specify your approach
# Explain in detail:
# 1. Run backtest with neutral 7-day exits
# 2. For each completed trade, calculate days_to_peak
# 3. Calculate median across all trades per profile
# 4. Use this median as exit day for next phases

AVOID_OPTIMIZATION = True  # Do NOT pick the Sharpe-maximizing exit day!
# Reason: That would be optimizing on train data
```

**Action:** Write this down. Add as comment to backtest_train.py.

---

### Question 2: Sensitivity Analysis Plan
**Current Status:** Not planned

**You must plan:**
```python
SENSITIVITY_ANALYSIS = {
    'test_exit_days': [5, 6, 7, 8, 9],  # Range around neutral default
    'test_regime_thresholds': False,  # Or True if desired
    'record_all_sharpes': True,  # Save Sharpe for each exit day
    'purpose': 'Detect if peak coincides with neutral default'
}

OUTPUT_FORMAT = {
    'Profile_1_LDG': {
        'sensitivity': {
            '5_days': {'sharpe': 1.05, 'return': 0.12},
            '6_days': {'sharpe': 1.15, 'return': 0.14},
            '7_days': {'sharpe': 1.20, 'return': 0.15},  # Flag if peak here
            '8_days': {'sharpe': 1.18, 'return': 0.14},
            '9_days': {'sharpe': 1.10, 'return': 0.12}
        },
        'chosen_exit': 6,  # Or 7 if peak is at 7
        'overfitting_risk': 'LOW'
    }
}
```

**Action:** Add sensitivity analysis code to backtest_train.py before running.

---

### Question 3: Degradation Acceptance Criteria
**Current Status:** Not defined

**You must define:**
```python
VALIDATION_DEGRADATION_THRESHOLDS = {
    'healthy_range': (0.20, 0.40),  # 20-40% is healthy
    'underfitting_threshold': 0.10,  # <10% is suspicious
    'overfitting_threshold': 0.50,   # >50% is severe overfitting
    'minimum_sharpe': 0.50,           # Reject if validation Sharpe < 0.50
}

DECISION_LOGIC = """
if validation_sharpe > 0.50 and degradation in (0.20, 0.40):
    PROCEED = True  # Healthy
elif validation_sharpe > 0.50 and degradation in (0.10, 0.20):
    PROCEED = True  # Maybe underfitting, but still acceptable
elif degradation > 0.50:
    PROCEED = False  # Severe overfitting - stop
elif validation_sharpe < 0.40:
    PROCEED = False  # Too weak to trade
"""
```

**Action:** Write this to a file. Use to make validation decision.

---

### Question 4: Regime Distribution Monitoring
**Current Status:** Not planned

**You must plan:**
```python
REGIME_DISTRIBUTION_ANALYSIS = {
    'compare_train_vs_validation': True,
    'threshold_for_alert': 0.10,  # >10% shift is significant
    'acknowledge_2022_anomaly': True,
    'adjust_expectations': "If 2022 has extreme vol, accept larger degradation"
}

SAMPLE_OUTPUT = """
Train Regime Distribution (2020-2021):
  Regime 1 (Trend Up): 25%
  Regime 2 (Trend Down): 20%
  Regime 3 (Compression): 20%
  Regime 4 (Breaking Vol): 15%
  Regime 5 (Choppy): 15%
  Regime 6 (Event): 5%

Validation Regime Distribution (2022-2023):
  Regime 1 (Trend Up): 10%  ⚠️ -15% from train
  Regime 2 (Trend Down): 25% ⚠️ +5% from train
  Regime 3 (Compression): 15% ⚠️ -5% from train
  Regime 4 (Breaking Vol): 25% ⚠️ +10% from train (2022 volatility)
  Regime 5 (Choppy): 20% ✅
  Regime 6 (Event): 5% ✅

Commentary: 2022 had elevated vol and breaking vol regimes.
Adjustment: Expect larger degradation if strategy underweights Regime 4.
"""
```

**Action:** Add regime distribution analysis to validation phase.

---

### Question 5: Parameter Lock Procedure
**Current Status:** Not defined

**You must define:**
```python
PARAMETER_LOCK_PROCEDURE = {
    'timing': 'Immediately after train phase completes',
    'location': '/Users/zstoc/rotation-engine/config/train_derived_params.json',
    'contents': {
        'train_period': {'start': '2020-01-01', 'end': '2021-12-31'},
        'derivation_date': '2025-11-18',  # Today
        'derivation_method': 'median_peak_timing',
        'exit_days': {
            'Profile_1_LDG': 6,
            'Profile_2_SDG': 7,
            # ... etc for all 6 profiles
        },
        'regime_thresholds': {
            'trend_threshold': 0.02,
            # ... etc for all thresholds
        }
    },
    'immutability': 'NEVER EDIT after lock - if wrong, discard and re-derive',
    'git_commit': 'git commit -m "Train phase complete: Locked parameters from 2020-2021"'
}
```

**Action:** Create config/train_derived_params.json structure before running train.

---

## SECTION 2: CODE VERIFICATION

### Verify #1: All Shifts are Positive
```bash
grep -n "shift(-" /Users/zstoc/rotation-engine/scripts/backtest_train.py
# Expected: ZERO matches
# If found: ❌ STOP - Fix before proceeding

grep -n "\.iloc\[.*\+" /Users/zstoc/rotation-engine/scripts/backtest_train.py
# Expected: ZERO matches (no forward indexing)
```

**Action:** Run both commands. Get zero matches.

---

### Verify #2: Period Boundaries are Hardcoded
```bash
grep "TRAIN_START\|TRAIN_END\|VALIDATION_START\|VALIDATION_END\|TEST_START\|TEST_END" \
  /Users/zstoc/rotation-engine/scripts/backtest_*.py
```

**Expected output:**
```
TRAIN_START = date(2020, 1, 1)      ✅
TRAIN_END = date(2021, 12, 31)      ✅
VALIDATION_START = date(2022, 1, 1) ✅
VALIDATION_END = date(2023, 12, 31) ✅
TEST_START = date(2024, 1, 1)       ✅
TEST_END = date(2024, 12, 31)       ✅
```

**Action:** Verify all 6 boundaries are present and correct.

---

### Verify #3: Warmup Period Logic
```bash
grep -A 10 "warmup_start\|WARMUP" /Users/zstoc/rotation-engine/scripts/backtest_train.py
```

**Expected:**
- Warmup is loaded (90 calendar days = ~60 trading days)
- Features are calculated on warmup + train
- Then filtered to train period only
- NO data leakage from outside warmup+train

**Action:** Read and confirm warmup logic is correct.

---

### Verify #4: Execution Model Spread Fix
```bash
grep -A 5 "base_spread\|min_spread" /Users/zstoc/rotation-engine/src/trading/execution.py | head -20
```

**Expected:**
```
ATM base_spread: 0.20  # Not 0.03
OTM base_spread: 0.30  # Not 0.05
vol_factor: scales from 1.0 to 2.5  # NOT blocked by min_spread
moneyness_factor: scales 1.0 to 2.0  # NOT blocked
dte_factor: scales 1.0 to 1.3  # NOT blocked
```

**Action:** Verify spread scales work correctly.

---

## SECTION 3: DATA & INFRASTRUCTURE

### Check #1: Data Drive Mounted
```bash
ls -lh /Volumes/VelocityData/ | head -5
# Expected: Output showing directory listing
# If ERROR: Mount drive first
```

**Action:** Verify drive is accessible.

---

### Check #2: Config Directory Exists
```bash
ls -la /Users/zstoc/rotation-engine/config/ 2>/dev/null || echo "CREATE IT"
```

**Action:** Create if doesn't exist: `mkdir -p /Users/zstoc/rotation-engine/config/`

---

### Check #3: SPY Data Available
```bash
ls -la /Volumes/VelocityData/velocity_om/parquet/stock/SPY/ | head -5
# Expected: Parquet files for 2020-2024
```

**Action:** Verify data is present for all periods.

---

## SECTION 4: COMMIT STRATEGY

### Before Train Phase
```bash
git status
# Should show clean working directory
git add .
git commit -m "Pre-train checkpoint: Sensitivity analysis and degradation thresholds defined"
```

**Action:** Commit your checklist completion as a checkpoint.

---

### After Train Phase
```bash
git add config/train_derived_params.json
git add data/backtest_results/train_2020-2021/
git commit -m "Train phase complete: Exit timing derived from 2020-2021 period"
```

**Action:** Commit locked parameters immediately.

---

### Before Validation Phase
```bash
git log --oneline -5
# Verify you can see train phase commit
git checkout config/train_derived_params.json
# Load locked parameters
python scripts/backtest_validation.py
```

**Action:** Use git to enforce parameter immutability.

---

## SECTION 5: EXECUTION ORDER

### Step 1: Complete This Checklist
- [ ] Answer all 5 questions (write answers to a document)
- [ ] Run all 4 code verifications (get zero failures)
- [ ] Check data/infrastructure (3/3 checks pass)
- [ ] Plan commits (understand git flow)

### Step 2: Create Sensitivity Analysis Code
- [ ] Write function to test exit days 5-9
- [ ] Record Sharpe for each exit day per profile
- [ ] Save results to JSON
- [ ] Add comments explaining why NOT picking best exit day

### Step 3: Run Train Phase
```bash
cd /Users/zstoc/rotation-engine
python scripts/backtest_train.py
```
**Duration:** ~10-30 minutes depending on data size

### Step 4: Analyze Train Results
- [ ] Review sensitivity analysis
- [ ] Check regime distributions
- [ ] Flag if any profile peaks at 7-day default
- [ ] Derive exit timing parameters
- [ ] Review peak timing reasonableness

### Step 5: Lock Parameters
- [ ] Write config/train_derived_params.json
- [ ] Add derivation_date, derivation_method, source metadata
- [ ] Commit to git with immutable message
- [ ] Verify you cannot accidentally edit later

### Step 6: Run Validation Phase
```bash
python scripts/backtest_validation.py
```
**Duration:** ~10-30 minutes

### Step 7: Assess Validation Results
- [ ] Compare validation Sharpe to train
- [ ] Calculate degradation percentage
- [ ] Check against thresholds (20-40% healthy)
- [ ] Review regime distribution shifts
- [ ] Make PROCEED / STOP decision

### Step 8: Run Test Phase (if validation passes)
```bash
python scripts/backtest_test.py
```
**Duration:** ~10-30 minutes

**WARNING:** Run ONCE ONLY. No iterations.

---

## SIGN-OFF

**Completion checklist:**
```
[ ] All 5 questions answered (write to document)
[ ] All code verifications passed (4/4)
[ ] All data/infrastructure checks passed (3/3)
[ ] Sensitivity analysis code written
[ ] Degradation thresholds defined
[ ] Parameter lock procedure documented
[ ] Regime distribution analysis planned
[ ] Git commit strategy understood
```

**Once ALL checkboxes are checked, you are ready for train phase.**

**Before you start:**
1. Save this checklist as a completed file with your answers
2. Commit to git as "Pre-train checklist: Complete"
3. Run train phase
4. Monitor for the 5 critical risks identified in ROUND8_METHODOLOGY_RISK_AUDIT.md

---

## RISK MONITORING DURING EXECUTION

### Train Phase Red Flags
- ❌ Sharpe <0.3: Debug the strategy
- ❌ Sharpe >3.0: Likely look-ahead bias somewhere
- ❌ Exit timing range >20 days: Data quality issue
- ❌ Peak timing coincides with 7 days AND >0.5 sharpe drop: Overfitting risk
- ✅ Sharpe 0.5-2.0: Healthy range
- ✅ Exit timing 5-9 days: Reasonable range

### Validation Phase Red Flags
- ❌ Degradation >50%: Stop, strategy overfit
- ❌ Validation Sharpe <0.4: Stop, not tradeable
- ❌ Validation negative: Stop, broken strategy
- ⚠️ Degradation <10%: Be suspicious, check for underfitting
- ✅ Degradation 20-40%: Healthy
- ✅ Validation Sharpe >0.5: Acceptable

### Test Phase Red Flags
- ⚠️ Test Sharpe <0.3: Risky but proceed with caution
- ✅ Test Sharpe positive: Accept
- ⚠️ Test Sharpe <0 but close: Risky
- ❌ Test Sharpe << Validation by >50%: Reject

---

**You're now ready. Complete this checklist, then run train phase with confidence.**
