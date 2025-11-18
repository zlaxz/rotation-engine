# ROUND 5: EXECUTION CHECKLIST

## Before Running Train Period

### Data Preparation
- [ ] Verify data drive mounted: `ls -lh /Volumes/VelocityData/`
- [ ] Verify SPY data path: `ls /Volumes/VelocityData/velocity_om/parquet/stock/SPY/`
- [ ] Check date range includes 2020-2021 (with 90-day warmup period)
- [ ] Create output directories:
  ```bash
  mkdir -p config
  mkdir -p data/backtest_results/train_2020-2021
  mkdir -p data/backtest_results/validation_2022-2023
  mkdir -p data/backtest_results/test_2024
  ```

### Code Readiness
- [ ] No uncommitted changes to core backtest code
- [ ] All 22 bug fixes from previous session still in place
- [ ] Exit engine configured for Phase 1
- [ ] Feature calculation looks correct (all shifts in place)

---

## Running Train Period

### Execution
```bash
cd /Users/zstoc/rotation-engine
python scripts/backtest_train.py
```

**Expected duration:** 5-15 minutes (depends on data loading)

### Output Verification

**Console Output - MUST See:**
```
✅ TRAIN PERIOD ENFORCED
   Expected: 2020-01-01 to 2021-12-31
   Actual:   2020-01-01 to 2021-12-31  ← Must match exactly
   Warmup days used: ~60 ← Should be 60±5
   First MA50 value: [number] ← Must NOT be NaN
```

**If you see:**
```
❌ DATA LEAK DETECTED: Data outside train period!
```
**STOP.** Data loading error. Debug before proceeding.

### File Verification

**After train period completes:**

```bash
# Check parameter file exists and is valid JSON
cat config/train_derived_params.json

# Should show:
# {
#   "train_period": {
#     "start": "2020-01-01",
#     "end": "2021-12-31"
#   },
#   "exit_days": {
#     "Profile_1_LDG": 7,
#     "Profile_2_SDG": 5,
#     "Profile_3_CHARM": 3,
#     "Profile_4_VANNA": 8,
#     "Profile_5_SKEW": 5,
#     "Profile_6_VOV": 7
#   },
#   "derivation_method": "median_peak_timing",
#   "derived_date": "2025-11-18"
# }

# Check results exist
ls -lh data/backtest_results/train_2020-2021/results.json
```

---

## Analyzing Train Results

### Extract Key Metrics

**From the train results JSON, document:**

```python
# Run this analysis script
import json

with open('config/train_derived_params.json', 'r') as f:
    params = json.load(f)

with open('data/backtest_results/train_2020-2021/results.json', 'r') as f:
    results = json.load(f)

# Print for documentation
print("TRAIN PERIOD RESULTS")
print("=" * 60)

for profile_id, result in results.items():
    print(f"\n{profile_id}:")
    print(f"  Trades: {result['summary']['total_trades']}")
    print(f"  Peak potential: ${result['summary']['peak_potential']:.0f}")
    print(f"  Final P&L: ${result['summary']['total_pnl']:.0f}")
    print(f"  Avg days to peak: {result['summary']['avg_days_to_peak']:.1f}")
    print(f"  Median % captured: {result['summary']['median_pct_captured']:.1%}")
    print(f"  → Exit day: {params['exit_days'][profile_id]} days")

print("\n" + "=" * 60)
print("TOTAL TRADES: [sum of all profiles]")
print("TOTAL PEAK POTENTIAL: [sum of all peak potentials]")
print("Sharpe ratio: [calculate from results if available]")
```

### Document Results

**Create a record - paste this into SESSION_STATE.md:**

```markdown
## TRAIN PERIOD RESULTS (2020-2021)

**Date completed:** [date]
**Data period:** 2020-01-01 to 2021-12-31
**Parameters derived:** Yes

### Metrics
- Total trades: [number]
- Total peak potential: $[number]
- Sharpe ratio: [value or "not calculated"]
- Peak days - Min: [days], Median: [days], Max: [days]

### Exit Days Derived
- Profile 1 LDG: Day [X]
- Profile 2 SDG: Day [X]
- Profile 3 CHARM: Day [X]
- Profile 4 VANNA: Day [X]
- Profile 5 SKEW: Day [X]
- Profile 6 VOV: Day [X]

### Assessment
[Does this look reasonable? Any surprises?]

### Confidence in Parameters
[Will any profile have too few trades for reliable median?]
```

---

## Critical Decision Point

### Before Running Validation

**Do NOT proceed to validation unless:**

- [ ] Train period completed successfully
- [ ] Parameter file `config/train_derived_params.json` exists and is valid
- [ ] Results file exists and contains trade data
- [ ] You've examined results and they make sense
- [ ] You've documented train period results in SESSION_STATE.md
- [ ] You understand what each derived parameter represents

**If anything is missing or wrong: STOP and debug before validation.**

### Set Acceptance Criteria

**Before seeing validation results, decide:**

Write this down and commit to it:

```markdown
## VALIDATION ACCEPTANCE CRITERIA (Set BEFORE running validation)

### Sharpe Ratio Degradation
- Train Sharpe: [expected range, e.g., 0.8-1.2]
- Acceptable validation Sharpe: [e.g., 0.6-1.0]
- Red flag: Sharpe <0.3 or <-50% degradation

### Capture Rate
- Expected: [e.g., 20-30% of peak potential]
- Acceptable: [e.g., 15-25%]
- Red flag: Negative capture rate

### Overall Profile Performance
- How many profiles should be profitable in validation?
- Which profiles are most critical?
- Is any single profile failure acceptable?

### Go/No-Go Decision
- If validation passes criteria → Proceed to test period
- If validation borderline → Re-iterate on train
- If validation fails → Abandon strategy
```

---

## Running Validation Period

### Prerequisites
- [ ] Train period completed
- [ ] `config/train_derived_params.json` exists
- [ ] You've set and documented acceptance criteria

### Execution
```bash
cd /Users/zstoc/rotation-engine
python scripts/backtest_validation.py
```

**Expected duration:** 5-15 minutes

### Output Verification

**Should load train parameters:**
```
================================================================================
LOADED TRAIN-DERIVED PARAMETERS
================================================================================
Derived from: 2020-01-01 to 2021-12-31
Derivation date: 2025-11-18
Method: median_peak_timing

Exit days (from train period median peak timing):
  Profile_1_LDG: Day 7
  [etc...]
================================================================================
```

**Should validate against 2022-2023 data:**
```
VALIDATION PERIOD: 2022-01-01 to 2023-12-31
```

### Analysis

```python
# Compare train vs validation
import json

with open('data/backtest_results/train_2020-2021/results.json', 'r') as f:
    train = json.load(f)

with open('data/backtest_results/validation_2022-2023/results.json', 'r') as f:
    val = json.load(f)

print("TRAIN vs VALIDATION COMPARISON")
print("=" * 70)

for profile_id in train.keys():
    train_peak = train[profile_id]['summary']['peak_potential']
    val_peak = val[profile_id]['summary']['peak_potential']

    if train_peak > 0:
        degradation = (val_peak - train_peak) / train_peak * 100
        print(f"{profile_id}")
        print(f"  Train peak: ${train_peak:,.0f}")
        print(f"  Valid peak: ${val_peak:,.0f}")
        print(f"  Degradation: {degradation:+.1f}%")
```

---

## Making the Go/No-Go Decision

### Red Flags (STOP - Abandon Strategy)

- ❌ Validation Sharpe < 0.3
- ❌ Validation Sharpe drops >50% from train
- ❌ Most profiles completely negative in validation
- ❌ Capture rate flips sign (positive train → negative validation)
- ❌ Strategy behavior completely changes

### Yellow Flags (RE-EVALUATE - Consider Re-iteration)

- ⚠️ 40-50% Sharpe degradation
- ⚠️ Some profiles profitable, others not
- ⚠️ Specific profile failing consistently
- ⚠️ Results borderline on acceptance criteria

**Decision:** Acceptable degradation in bear market (2022) or not?

### Green Lights (PROCEED to Test)

- ✅ Sharpe degrades 20-40% as expected
- ✅ All or most profiles profitable
- ✅ Results within acceptance criteria
- ✅ Degradation pattern makes economic sense

---

## Running Test Period (Final)

### Prerequisites
- [ ] Validation completed and acceptable
- [ ] Decision made to proceed: "This strategy works in train and validation"
- [ ] Ready to accept results, good or bad

### CRITICAL: This runs ONCE ONLY

**Do NOT:**
- Re-run if results are bad
- Modify code and re-run
- "Peek" multiple times

### Execution
```bash
cd /Users/zstoc/rotation-engine
python scripts/backtest_test.py
```

### Output Handling

**Whatever results you see: Accept them.**

- ✅ Good results → Strategy works, proceed to deployment considerations
- ❌ Bad results → Strategy doesn't work, that's valuable information
- Both outcomes are acceptable. The test answered the question.

---

## After Test Period: Next Steps

### If Test Passes (Consistent with validation)

1. Document results side-by-side with train and validation
2. Calculate bootstrap confidence intervals (run `statistical-validator` skill)
3. Assess if returns are sufficient for capital allocation
4. Plan position sizing for live trading
5. Create deployment checklist

### If Test Fails (Doesn't match validation)

1. Document failure explicitly
2. Check for data quality issues
3. Verify 2024 period wasn't unique (external events?)
4. Return to research with lessons learned
5. This is valuable information, not wasted time

---

## Git Commit Discipline

### After Train Period
```bash
git add config/train_derived_params.json
git add data/backtest_results/train_2020-2021/
git commit -m "feat: Train period execution (2020-2021) - 6 parameters derived"
```

### After Validation Period
```bash
git add data/backtest_results/validation_2022-2023/
git commit -m "feat: Validation period execution (2022-2023) - [acceptable/failed]"
```

### After Test Period
```bash
git add data/backtest_results/test_2024/
git commit -m "feat: Test period execution (2024) - [results summary]"
```

**DO NOT commit intermediate attempts or parameter tweaks.**

---

## Common Mistakes to Avoid

### ❌ Mistake 1: Modifying Parameters Between Periods
**Wrong:** "Validation didn't work, let me adjust exit days and re-run validation"
**Right:** If validation fails, go back to train period, re-analyze, re-derive parameters, then re-validate

### ❌ Mistake 2: Peeking at Test Results Multiple Times
**Wrong:** Run test, see results, change code, run test again
**Right:** Run test ONCE, accept results

### ❌ Mistake 3: Using Validation Data for Train Decisions
**Wrong:** "Validation worked well, let me optimize train parameters around that"
**Right:** Train period is locked once parameters derived. Validation tests those locked parameters.

### ❌ Mistake 4: Not Following Date Boundaries
**Wrong:** "I'll just load 2020-2024 data for the train period"
**Right:** Load EXACTLY 2020-2021 (warmup before, nothing after)

### ❌ Mistake 5: Treating Acceptable Degradation as Failure
**Wrong:** Train Sharpe = 1.2, Validation Sharpe = 0.9 (25% drop) "This failed!"
**Right:** 25% degradation is completely expected, this passed

---

## Success Criteria Summary

**You've completed this phase successfully when:**

- [ ] Train period executed with hard date boundaries enforced
- [ ] Parameters derived from median peak timing
- [ ] Validation period executed with locked parameters
- [ ] Validation degradation analyzed and documented
- [ ] Go/no-go decision made explicitly
- [ ] If proceeding: Test period executed once
- [ ] All results committed to git with clear messages
- [ ] SESSION_STATE.md updated with final status

---

**Print this page and keep it visible while executing.**

**Following this checklist exactly = Rigorous research methodology.**

**Deviating from this checklist = Overfitting risk.**
