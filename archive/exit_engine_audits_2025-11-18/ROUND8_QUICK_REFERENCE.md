# ROUND 8 - QUICK REFERENCE GUIDE

## ONE-PAGE RISK SUMMARY

**Overall Risk Score: 22/100 (LOW RISK)**

| Category | Score | Status | Key Action |
|----------|-------|--------|-----------|
| Look-ahead bias | 5/25 | ✅ | Monitor shift operations |
| Data contamination | 0/25 | ✅ | Period boundaries enforced |
| Exit timing overfitting | 8/25 | ⚠️ | Sensitivity analysis required |
| Parameter count | 4/25 | ✅ | 33:1 ratio is healthy |
| Execution costs | 5/25 | ✅ | Round 7 fix verified |
| Statistical power | 0/25 | ✅ | Data size adequate |

---

## 5 CRITICAL RISKS TO MONITOR

### Risk #1: Exit Timing Coincides with 7-Day Default
**When to worry:** Peak timing in train phase is 6-8 days
**What to do:** Flag for overfitting investigation
**Mitigation:** Conduct sensitivity analysis (5-9 day range)

### Risk #2: Validation Degradation Outside Expected Range
**When to worry:** Degradation <10% or >50%
**What to do:** Stop and investigate before proceeding
**Healthy range:** 20-40% degradation

### Risk #3: Regime Distribution Shift (2022 Crisis)
**When to worry:** Train has Regime 1=25%, Validation has Regime 1=10%
**What to do:** Acknowledge shift, adjust expectations
**2022 anomaly:** Breaking Vol (Regime 4) elevated 15%→25%

### Risk #4: Exit Timing Parameter Optimization (NOT ALLOWED)
**When to worry:** You pick the exit day that has highest train Sharpe
**What to do:** Use median peak timing instead (data-driven, not optimized)
**Rule:** No picking best-performing parameter on train data

### Risk #5: Parameter Lock Discipline
**When to worry:** After seeing train results, tempted to "adjust" parameters
**What to do:** Lock immediately in config/train_derived_params.json
**Immutable:** Never edit after lock; if wrong, discard and re-derive

---

## EXECUTION CHECKLIST

### Before Train Phase
```
✓ All shifts are positive (no negative shift operations)
✓ Period boundaries hardcoded and non-overlapping
✓ Warmup period logic verified
✓ Execution model spread fix in place
✓ Config directory exists
✓ Data drive is mounted
✓ Sensitivity analysis code written
✓ Degradation thresholds defined
✓ Git commit strategy understood
```

### During Train Phase
```
Monitor:
  ⚠️ Sharpe < 0.3 → Debug
  ⚠️ Sharpe > 3.0 → Check for bias
  ⚠️ Exit timing range > 20 days → Data quality issue
  ⚠️ Peak at 7 days + high Sharpe → Overfitting risk

After train completes:
  ✓ Review sensitivity analysis
  ✓ Verify regime distributions
  ✓ Check exit timing reasonableness
  ✓ Lock parameters to config/
  ✓ Commit to git
```

### Before Validation Phase
```
✓ Load parameters from config/ (LOCKED, not modified)
✓ Verify you did NOT re-run train with optimized parameters
✓ Double-check period boundaries (2022-2023 only)
```

### During Validation Phase
```
Monitor:
  ⚠️ Degradation < 10% → Suspicious (underfitting?)
  ⚠️ Degradation > 50% → STOP (severe overfitting)
  ⚠️ Validation Sharpe < 0.4 → Not tradeable

Decision gate:
  ✅ Pass: Degradation 20-40% AND Sharpe > 0.5 → Proceed to test
  ⚠️ Caution: Degradation 10-20% → Proceed with skepticism
  ❌ Fail: Degradation > 50% OR Sharpe < 0.4 → STOP
```

### Before Test Phase (Final Holdout)
```
✓ Confirm this is the FINAL test (run only once)
✓ Load locked parameters
✓ NO iterations after seeing results
```

### During Test Phase
```
Run ONCE ONLY - no re-running:
  python scripts/backtest_test.py

Accept results:
  ✅ Test Sharpe > 0.4 → Approve for deployment
  ⚠️ 0.3 < Test Sharpe < 0.4 → Risky but consider
  ❌ Test Sharpe < 0.3 → Reject
```

---

## EXPECTED OUTCOMES

### Train Phase (2020-2021)
- Profile Sharpe ratios: 0.8-1.5 (healthy range)
- Total portfolio Sharpe: 1.0-1.8
- Exit timing median: 5-9 days per profile
- Regime 4 frequency: ~15%

### Validation Phase (2022-2023)
- Expected degradation: 20-40%
- Minimum acceptable Sharpe: 0.5
- If Sharpe = 1.2 on train → Expect 0.72-0.96 on validation
- 2022 regime shift: Regime 4 elevated to ~25%

### Test Phase (2024)
- Expected Sharpe: ±20% from validation
- No surprises if consistent with validation pattern
- Accept whatever it is (good or bad)

---

## DECISION TREE

```
TRAIN PHASE RESULT:
├─ Sharpe < 0.3 → ❌ STOP (strategy doesn't work)
├─ Sharpe 0.3-0.5 → ⚠️ Marginal (proceed with caution)
├─ Sharpe 0.5-2.0 → ✅ PROCEED (healthy)
└─ Sharpe > 3.0 → ❌ SUSPECT (likely bias)

VALIDATION PHASE RESULT:
├─ Degradation > 50% → ❌ STOP (severe overfitting)
├─ Degradation 40-50% → ⚠️ CAUTION (likely overfitting)
├─ Degradation 20-40% → ✅ PROCEED (healthy)
├─ Degradation 10-20% → ⚠️ CAUTION (underfitting?)
└─ Degradation < 10% → ⚠️ SUSPECT (overfitting?)

TEST PHASE RESULT:
├─ Sharpe > 0.4 → ✅ DEPLOY (acceptable)
├─ 0.3 < Sharpe < 0.4 → ⚠️ RISKY (could deploy with caution)
└─ Sharpe < 0.3 → ❌ REJECT (too weak)
```

---

## RED TEAM ATTACK SURFACE

### Things I'll Check Next:
1. **Parameter derivation methodology** - Ensure not optimizing on train data
2. **Regime distribution analysis** - Verify 2022 shifts acknowledged
3. **Exit timing sensitivity** - Check if peak is truly at 7 days or elsewhere
4. **Validation degradation pattern** - Confirm 20-40% range achieved
5. **Test vs validation consistency** - Ensure test doesn't diverge dramatically

### Questions You Should Answer:
- "Why did exit timing choose 6 days instead of 7?" (if peak is at 6)
- "Why is validation degradation only 8%?" (if it happens - investigate)
- "Does regime distribution shift in 2022 explain validation underperformance?" (acknowledge it)
- "Are we in the healthy 20-40% degradation range?" (yes/no, explain)
- "Can we confidently deploy test results?" (only if all gates pass)

---

## GIT WORKFLOW

```bash
# Before train
git add PRE_TRAIN_PHASE_CHECKLIST.md
git add ROUND8_METHODOLOGY_RISK_AUDIT.md
git commit -m "Pre-train: Checklist and risk audit complete"

# After train
git add config/train_derived_params.json
git add data/backtest_results/train_2020-2021/
git commit -m "Train phase complete: Exit timing derived from 2020-2021"

# After validation
git add data/backtest_results/validation_2022-2023/
git commit -m "Validation phase complete: [Degradation]% observed"

# After test
git add data/backtest_results/test_2024/
git commit -m "Test phase complete: Final holdout validation"
```

---

## COMMON FAILURE MODES

### Failure Mode 1: Exit Timing "Optimization"
**Symptom:** "I tested exit days 5-9, and day 5 had best Sharpe, so I'm using that"
**Problem:** That's optimizing on train data
**Solution:** Use median peak timing instead

### Failure Mode 2: Validation Adjustment
**Symptom:** "Validation is weak, so let me adjust regime thresholds"
**Problem:** You're now optimizing on validation data
**Solution:** Lock parameters, proceed to test, accept results

### Failure Mode 3: Parameter Reuse
**Symptom:** "Let me re-run train with different thresholds"
**Problem:** You're contaminating train phase by iterating
**Solution:** Train is done; don't re-run

### Failure Mode 4: Degradation Misinterpretation
**Symptom:** "Validation is only 10% worse, that means the strategy is robust!"
**Problem:** <10% degradation is suspicious (possible overfitting)
**Solution:** 20-40% is healthy; be skeptical of <10%

### Failure Mode 5: Test Contamination
**Symptom:** "Test results are weak, let me re-run to see if I can improve"
**Problem:** You've now peeked at test data twice (contamination)
**Solution:** Test run ONCE ONLY, accept results

---

## KEY METRICS TO TRACK

### Per Profile
- Exit days derived (5-9 day range expected)
- Train Sharpe vs validation Sharpe
- Degradation percentage
- Trade count (need 30+ for robustness)

### Overall Portfolio
- Train Sharpe: ______ (target: 1.0-1.8)
- Validation Sharpe: ______ (target: 0.6-1.2)
- Degradation: ______ % (target: 20-40%)
- Test Sharpe: ______ (target: >0.4)

### Regime Distribution
- Regime 4 frequency train: ______ %
- Regime 4 frequency validation: ______ % (expect 15% → 25%)
- Impact on profiles: ______ (acknowledge shift)

---

## APPROVAL GATES

### Gate 1: Train Phase Complete
```
✓ Sharpe > 0.5
✓ Exit timing 5-9 days per profile
✓ Regime distributions calculated
✓ No look-ahead bias detected
✓ Parameters locked in config/
```

### Gate 2: Validation Phase Complete
```
✓ Degradation 20-40%
✓ Validation Sharpe > 0.5
✓ Regime shift (2022) acknowledged
✓ No parameter re-optimization
```

### Gate 3: Test Phase Complete
```
✓ Test Sharpe > 0.4
✓ Consistent with validation pattern
✓ No degradation > 30% from validation
✓ Acceptable for deployment
```

---

## FINAL REALITY CHECK

Before you go live:

1. **Is this the same strategy that failed in previous rounds?**
   - If yes: Why should this round be different?
   - Answer: Proper train/val/test splits + no contamination

2. **Can I explain every parameter?**
   - Exit timing: Median peak from train data ✓
   - Regime thresholds: From literature and defaults ✓
   - Why 7-day default: Neutral baseline to avoid contamination ✓

3. **Would I bet my own money on this?**
   - If yes: Deployment ready
   - If no: Keep refining

4. **Did I run the train phase responsibly?**
   - No parameter optimization ✓
   - No looking at validation during train ✓
   - Locked parameters immediately ✓
   - Ran test phase ONCE ONLY ✓

---

**You're ready. Execute with discipline. Monitor the 5 critical risks.**
