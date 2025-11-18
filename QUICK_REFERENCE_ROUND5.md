# ROUND 5: QUICK REFERENCE GUIDE

**Print this. Keep it visible during execution.**

---

## THE VERDICT IN ONE SENTENCE

Your train/validation/test methodology is sound and reduces overfitting risk substantially. The strategy may or may not work, but you'll get an honest answer.

---

## RISK SCORE INTERPRETATION

**10/100 = LOW RISK**

This means:
- ✅ Methodology has no obvious flaws
- ✅ Data isolation is strong
- ✅ Parameters are empirically derived
- ✅ Sample size is abundant
- ⚠️ Real test is whether strategy works out-of-sample (unknown)

---

## WHAT TO READ WHEN

| When | What | Time |
|------|------|------|
| Right now | ROUND5_EXECUTIVE_SUMMARY.md | 5 min |
| Before train | ROUND5_EXECUTION_CHECKLIST.md | 10 min |
| During validation | ROUND5_VALIDATION_TESTS.md | Reference |
| Questions | ROUND5_METHODOLOGY_AUDIT.md | Deep dive |

---

## EXECUTION CHECKLIST (Abbreviated)

### Before Train Period
- [ ] Data drive mounted: `ls /Volumes/VelocityData/`
- [ ] Output dirs created: `mkdir -p config data/backtest_results/{train_2020-2021,validation_2022-2023,test_2024}`
- [ ] No uncommitted changes: `git status`

### During Train Period
```bash
cd /Users/zstoc/rotation-engine
python scripts/backtest_train.py
```

Expected output:
```
✅ TRAIN PERIOD ENFORCED
   Expected: 2020-01-01 to 2021-12-31
   Actual:   2020-01-01 to 2021-12-31
```

### After Train Period
- [ ] `config/train_derived_params.json` exists
- [ ] `data/backtest_results/train_2020-2021/results.json` exists
- [ ] Document results in SESSION_STATE.md
- [ ] Set validation acceptance criteria in writing

### Before Validation
- [ ] Train period complete
- [ ] Acceptance criteria written down
- [ ] Committed to not modifying parameters

### During Validation
```bash
python scripts/backtest_validation.py
```

### After Validation
Run 8 tests from ROUND5_VALIDATION_TESTS.md:
1. Sharpe degradation
2. Per-profile degradation
3. Win rate stability
4. Capture rate stability
5. Trade frequency
6. Sign consistency
7. Statistical significance
8. Degradation pattern

### Test Period (If Validation Passes)
```bash
python scripts/backtest_test.py
```
Run ONCE ONLY. Accept results.

---

## CRITICAL RED FLAGS

### ❌ DO NOT PROCEED IF:

- Train period shows >50% Sharpe degradation (indicates massive overfitting)
- Validation shows sign flips (profitable train → unprofitable validation)
- You're tempted to "fix" parameters after seeing validation results
- More than 3 validation tests fail

### ✅ SAFE TO PROCEED IF:

- Sharpe degrades 20-40% train→validation (normal)
- All profiles degrade consistently
- Win rate stable (degradation <15%)
- Capture rate stable (degradation <30%)
- No sign flips
- 6+ of 8 validation tests pass

---

## EXPECTED METRICS

| Metric | Train Range | Validation Expected | Pass Criteria |
|--------|------------|----------------------|---------------|
| Sharpe | 0.8-1.5 | 0.6-1.2 | Degrade 20-40% |
| Capture | 20-40% | 15-30% | Degrade 10-30% |
| Win rate | 45-60% | 40-55% | Degrade 5-15% |
| Trades | ~300-600 | ~300-600 | Within ±30% |

---

## THE 3 COMMANDS YOU NEED

```bash
# Execute train period (2020-2021)
python /Users/zstoc/rotation-engine/scripts/backtest_train.py

# Execute validation period (2022-2023)
python /Users/zstoc/rotation-engine/scripts/backtest_validation.py

# Execute test period (2024) - RUN ONCE ONLY
python /Users/zstoc/rotation-engine/scripts/backtest_test.py
```

---

## WHAT NOT TO DO

### ❌ FORBIDDEN ACTIONS

- Don't modify parameters after seeing validation results
- Don't run validation multiple times
- Don't run test period, see results, run again
- Don't use validation data to inform train decisions
- Don't change code between train and validation
- Don't "peek" at test results multiple times
- Don't move the goalposts ("I thought Sharpe >1.0 was success")

### ✅ CORRECT APPROACH

If validation fails:
1. Accept result: "Strategy is overfit"
2. Go back to train period
3. Re-analyze and re-derive parameters
4. Re-run validation with new parameters
5. This is iteration, not fitting

---

## GIT DISCIPLINE

After each phase:
```bash
git add [results files]
git commit -m "feat: Phase X (train/validation/test) complete"
```

Never force push. Never skip commits. Clean git history = professional methodology.

---

## DECISION TREE

```
Train Period Complete?
  No  → Fix data/code issues
  Yes → Set validation criteria in writing
        ↓
        Validation Period Complete?
          No  → Fix issues, re-run
          Yes → Run 8 validation tests
                ↓
                Validation Tests Pass (6+/8)?
                  No  → Strategy is overfit, ABANDON
                  Yes → Decision Point
                        ↓
                        Degradation Acceptable?
                          No  → Re-iterate (go back to train)
                          Yes → Proceed to Test Period
                                ↓
                                Test Period (RUN ONCE)
                                ↓
                                Test Passes?
                                  Yes → Ready for deployment
                                  No  → Valuable learning, try next hypothesis
```

---

## ACCEPTABLE OUTCOMES

### ✅ Success: Strategy Works
- Train Sharpe: 1.0
- Validation Sharpe: 0.8 (20% degradation)
- Test Sharpe: 0.75 (25% degradation)
- **Decision:** Strategy is robust, proceed to deployment

### ✅ Success: Strategy is Overfit (Valuable Failure)
- Train Sharpe: 1.5
- Validation Sharpe: 0.5 (67% degradation)
- **Decision:** Strategy doesn't work, abandon, try next hypothesis
- **Why valuable:** Better to know in backtest than deploy to live trading

### ✅ Success: Strategy is Mediocre (Still Valid)
- Train Sharpe: 0.6
- Validation Sharpe: 0.5 (17% degradation)
- Test Sharpe: 0.48 (20% degradation)
- **Decision:** Strategy works, returns may be insufficient for capital allocation, but it's honest

---

## METRICS BY PROFILE (For Documentation)

After train period, document:
```
Profile_1_LDG:   [X] trades, exit day [Y], median peak [Z] days
Profile_2_SDG:   [X] trades, exit day [Y], median peak [Z] days
Profile_3_CHARM: [X] trades, exit day [Y], median peak [Z] days
Profile_4_VANNA: [X] trades, exit day [Y], median peak [Z] days
Profile_5_SKEW:  [X] trades, exit day [Y], median peak [Z] days
Profile_6_VOV:   [X] trades, exit day [Y], median peak [Z] days
```

---

## ESTIMATION ERROR TO EXPECT

**Median peak timing estimation error:**

With ~50 trades per profile:
- Estimated median: ±1-2 days
- Validation test will reveal true median
- Don't worry about precision, validation will validate

---

## WORST CASE SCENARIO RESPONSE

**If validation shows >50% Sharpe degradation:**

1. ❌ Don't panic
2. ✅ Don't blame methodology (it's sound)
3. ✅ Don't try to "fix" it
4. ✅ Accept result: "Strategy is overfit"
5. ✅ Document why: Entry conditions? Exit timing? Both?
6. ✅ Try next hypothesis
7. ✅ This is valuable data

Better to fail in backtest than deploy to live trading.

---

## BEST CASE SCENARIO RESPONSE

**If validation passes acceptably:**

1. ✅ Document results
2. ✅ Proceed to test period
3. ✅ Run test once
4. ✅ Accept results
5. ✅ Consider deployment (if returns sufficient)
6. ✅ Professional methodology led to professional results

---

## SESSION_STATE.md UPDATES

After each phase, update SESSION_STATE.md:

```markdown
## ROUND 5 EXECUTION STATUS

### Train Period (2020-2021)
- **Completed:** [date]
- **Exit days derived:** [list]
- **Total trades:** [count]
- **Sharpe:** [value]
- **Status:** Complete / In Progress / Failed

### Validation Period (2022-2023)
- **Completed:** [date]
- **Sharpe:** [value]
- **Degradation:** [%]
- **Tests passed:** X/8
- **Status:** Complete / In Progress / Failed

### Test Period (2024)
- **Completed:** [date]
- **Sharpe:** [value]
- **Status:** Not yet run / Complete / Failed
```

---

## TIME ESTIMATES

| Phase | Duration |
|-------|----------|
| Train period execution | 10 min |
| Train result analysis | 30 min |
| Validation execution | 10 min |
| Validation test analysis | 1 hour |
| Test period execution | 10 min |
| **Total** | **~2 hours** |

You can complete entire validation cycle in one focused session.

---

## FINAL THOUGHT

The methodology is your guarantee of honest results. Follow it precisely and you'll know if the strategy works. Cut corners and you'll trick yourself with false positives.

You've chosen to build a quant shop. That choice matters.

Execute professionally. Accept results honestly.

---

**Keep this page bookmarked. Refer to it constantly during execution.**

**Questions not answered here? Check ROUND5_EXECUTIVE_SUMMARY.md or ROUND5_METHODOLOGY_AUDIT.md**

**Ready to start? Go to ROUND5_EXECUTION_CHECKLIST.md**
