# EXIT ENGINE V1 - VALIDATION CHECKLIST

**Status:** Ready for train phase execution
**Audited:** 2025-11-18
**Risk Level:** LOW-MODERATE (28/100)

---

## CRITICAL BLOCKERS (Must Fix Before Validation)

### Block #1: Exit Days Contamination

**Status:** 🔴 BLOCKER
**Issue:** Exit days derived from FULL dataset (2020-2024)
**Impact:** Parameters are contaminated by validation+test data

**Fix Instructions:**
```bash
Step 1: Run backtest on 2020-2021 ONLY
        Input: SPY options data 2020-2021
        Output: Trade results with peak timing for each profile

Step 2: Calculate median peak day per profile
        Profile_1_LDG: median(peak_days)
        Profile_2_SDG: median(peak_days)
        Profile_3_CHARM: median(peak_days)
        Profile_4_VANNA: median(peak_days)
        Profile_5_SKEW: median(peak_days)
        Profile_6_VOV: median(peak_days)

Step 3: Update exit_engine.py with NEW values
        Replace: PROFILE_EXIT_DAYS = {...}
        With fresh train period values
        LOCK THESE VALUES (no further changes)

Step 4: Run validation backtest on 2022-2023 ONLY
        Apply same exit days from Step 2
        Do NOT re-optimize on validation data

Step 5: Compare train vs validation performance
        Calculate degradation %
        Flag if >50% degradation (overfitting suspected)
```

**Acceptance Criteria:**
- Exit days are derived from train period only
- No data from validation/test period was used
- Values are locked and documented

**Estimated Time:** 2-3 hours

---

## HIGH PRIORITY (Must Complete Before Validation)

### Priority #1: CHARM Profile Deep Dive

**Status:** 🟡 YELLOW FLAG
**Issue:** Peak timing exactly at Day 0 (entry day)
**Risk:** This is unusual and suggests regime sensitivity

**Investigation Instructions:**
```bash
Step 1: Analyze CHARM profile trades in detail
        For each trade, plot P&L curve from entry to exit
        Count: How many peak on Day 0? Day 1? Day 2?

Step 2: Calculate empirical CDF of peak timing
        CDF should show when most trades reach maximum P&L
        If CDF is heavily weighted to Day 0-1, then exit at Day 3 is risky

Step 3: Check for regime patterns
        Do 2020 trades have different peak timing than 2021?
        If yes, exit day may not generalize to validation

Step 4: Make decision
        A) Peak is genuinely Day 0 → Consider earlier exit trigger
        B) Peak shows variance → Accept Day 3 as compromise
        C) Peak is regime-dependent → Monitor closely in validation
```

**Acceptance Criteria:**
- Clear understanding of why peak is at Day 0
- Can explain impact of Day 3 exit timing
- Plan documented for validation monitoring

**Estimated Time:** 2-3 hours

---

### Priority #2: Permutation Test (Validate Parameters)

**Status:** ⚠️ CAUTION
**Issue:** Need to verify exit days beat random chance
**Risk:** If parameters are data mining, permutation test will show p > 0.05

**Execution Instructions:**
```bash
Step 1: Load train period data (2020-2021)

Step 2: Run 1,000 permutation tests
        for i in range(1000):
            random_exit_days = {
                'Profile_1_LDG': random(3, 10),
                'Profile_2_SDG': random(3, 10),
                ... (all 6 profiles)
            }
            perf = backtest(data_train, random_exit_days)
            results.append(perf)

Step 3: Calculate p-value
        p_value = (count of random_perf >= actual_perf) / 1000

Step 4: Interpret
        p < 0.01:   ✅ Strong validation, parameters beat random
        p < 0.05:   ✅ Pass threshold, parameters are significant
        p > 0.05:   ❌ FAIL, parameters not better than random
```

**Acceptance Criteria:**
- p-value < 0.05 (parameters beat random chance)
- Results documented
- If p > 0.05, investigate whether parameters are spurious

**Estimated Time:** 3-5 hours (depends on backtest speed)

---

### Priority #3: Regime Robustness Test

**Status:** ⚠️ CAUTION
**Issue:** Test if exit days work across different sub-regimes
**Risk:** If performance differs >30% between 2020 vs 2021, indicates regime sensitivity

**Execution Instructions:**
```bash
Step 1: Split train period into sub-regimes
        Regime A: 2020 (COVID crash + recovery, HIGH vol)
        Regime B: 2021 (smooth rally, LOW vol)

Step 2: Run backtest on each regime separately
        perf_2020 = backtest(data['2020-01-01':'2020-12-31'])
        perf_2021 = backtest(data['2021-01-01':'2021-12-31'])

Step 3: Calculate performance difference
        diff = abs(perf_2020 - perf_2021) / max(abs(perf_2020), abs(perf_2021))

Step 4: Interpret
        diff < 15%:  ✅ Very consistent, robust parameters
        diff < 30%:  ✅ Acceptable variation, normal
        diff > 50%:  ❌ FAIL, regime sensitivity problem
```

**Acceptance Criteria:**
- Regime robustness test completed
- Performance difference < 30% or documented reason
- If major difference, understand which regime drives results

**Estimated Time:** 2 hours

---

## VALIDATION PHASE (After Blockers Fixed)

### Validation Step 1: Apply Train-Derived Exit Days to Validation Period

**Procedure:**
```bash
Step 1: Load validation data (2022-2023 ONLY)
        Do not touch test data (2024)

Step 2: Apply exit engine with train-derived exit days
        engine = ExitEngine(custom_exit_days=train_exit_days)
        results_val = backtest(data_2022_2023, engine)

Step 3: Compare train vs validation
        ├─ Train period P&L: X
        ├─ Validation P&L: Y
        └─ Degradation: (X - Y) / X

Step 4: Assess results
        Degradation < 15%:  ✅ Excellent, strategy is robust
        Degradation 15-30%: ✅ Good, normal validation loss
        Degradation 30-50%: ⚠️ High but acceptable
        Degradation > 50%:  ❌ FAIL, indicates overfitting
```

**Pass Criteria:**
- Validation degradation < 50%
- At least 3 of 6 profiles show positive capture in validation
- No profile shows >60% degradation (check for regime sensitivity)

---

### Validation Step 2: Profile-Specific Performance Check

**For Each Profile:**

```
Profile 1 (LDG):
├─ Train P&L: ?
├─ Validation P&L: ?
├─ Degradation: ? %
└─ Pass: Y/N [Expected: <40% degradation]

Profile 2 (SDG):
├─ Train P&L: ?
├─ Validation P&L: ?
├─ Degradation: ? %
└─ Pass: Y/N [Expected: <35% degradation]

Profile 3 (CHARM):
├─ Train P&L: ?
├─ Validation P&L: ?
├─ Degradation: ? %
└─ Pass: Y/N [CRITICAL: expect 40-60% degradation]

Profile 4 (VANNA):
├─ Train P&L: ?
├─ Validation P&L: ?
├─ Degradation: ? %
└─ Pass: Y/N [Expected: keep +15% capture, <20% degradation]

Profile 5 (SKEW):
├─ Train P&L: ?
├─ Validation P&L: ?
├─ Degradation: ? %
└─ Pass: Y/N [RISK: expect 40-50% degradation, worst performer]

Profile 6 (VOV):
├─ Train P&L: ?
├─ Validation P&L: ?
├─ Degradation: ? %
└─ Pass: Y/N [Expected: <35% degradation]
```

**Special Monitoring:**
- CHARM: If degradation > 60%, indicates regime sensitivity
- VANNA: Control group - if this fails, method is broken
- SKEW: Worst performer - high degradation expected but must be monitored

---

### Validation Step 3: Walk-Forward Analysis

**Procedure:**
```bash
Step 1: Sub-divide validation period into quarters
        Q1: 2022-01-01 to 2022-03-31 (rate shock begins)
        Q2: 2022-04-01 to 2022-06-30 (peak bear market)
        Q3: 2022-07-01 to 2022-09-30 (Fed continues hikes)
        Q4: 2022-10-01 to 2022-12-31 (relief rally begins)
        + 2023 data: different regime entirely

Step 2: Run backtest on each quarter
        results_q1 = backtest(data_q1, engine)
        results_q2 = backtest(data_q2, engine)
        ... etc

Step 3: Analyze per-quarter performance
        Do results degrade steadily?
        Or are there specific problem quarters?
```

**Pass Criteria:**
- Performance relatively stable across quarters
- No single quarter showing >70% degradation (except maybe Q2 2022 crisis)
- Trend shows reasonable degradation, not cliff at specific date

---

## TEST PHASE (Only if Validation Passes)

### Test Step 1: Apply to Test Period

**Procedure:**
```bash
Step 1: Load test data (2024 ONLY)
        Do not touch - this is truly out-of-sample

Step 2: Apply same exit days from train period
        engine = ExitEngine(custom_exit_days=train_exit_days)
        results_test = backtest(data_2024, engine)

Step 3: Record results
        ├─ Total P&L: ?
        ├─ Capture rate: ?
        └─ By profile: [P&L for each]

Step 4: Document
        This is the final test - accept whatever it shows
        Do NOT re-optimize based on test results
```

**Important:** Do not adjust parameters based on test results. Test results are the ground truth for what to expect in live trading.

---

## DECISION MATRIX: When to Stop

### Stop Before Validation If:
- [ ] Permutation test shows p > 0.05 (parameters are random)
- [ ] CHARM deep dive reveals regime-dependent peak timing (>50% variation)
- [ ] Regime robustness test shows >50% performance difference between 2020 and 2021

**Action:** Fix underlying issues or reconsider exit strategy

### Stop Before Test If:
- [ ] Validation degradation > 60% on any profile (except possible exception: CHARM)
- [ ] Validation P&L actually negative (strategy fails)
- [ ] More than 2 profiles show >70% degradation
- [ ] Walk-forward shows cliff at specific date (indicates regime break)

**Action:** Return to drawing board, parameters may be overfit

### Proceed to Live Trading Only If:
- [ ] Train period P&L positive
- [ ] Validation degradation 15-40% (normal range)
- [ ] At least 4 of 6 profiles profitable in validation
- [ ] VANNA profile (control) shows consistent +15% capture
- [ ] Permutation test passed (p < 0.05)
- [ ] Regime robustness test passed (<30% difference)
- [ ] Walk-forward shows smooth degradation (not cliffs)

---

## RISK TOLERANCE LEVELS

### Conservative (Recommended)
- Only deploy if validation shows <20% degradation
- Require all 6 profiles positive in validation
- Start with 25% of capital allocation
- Monitor closely for first 100 trades

### Moderate
- Deploy if validation shows <40% degradation
- Require 4+ profiles positive in validation
- Start with 50% of capital allocation
- Monitor closely for first 50 trades

### Aggressive
- Deploy if validation shows <60% degradation (rare case)
- Require 3+ profiles positive in validation
- Start with 75% of capital allocation
- Expect regime shocks to cause 50%+ peak-to-trough

---

## DOCUMENTATION REQUIREMENTS

After each phase, create/update:

### After Train Phase:
- [ ] Train backtest results (total P&L, by profile)
- [ ] Exit days derived from train period (document new values)
- [ ] Permutation test results (p-value)
- [ ] Regime robustness test (2020 vs 2021 comparison)
- [ ] CHARM deep dive (understanding of Day 0 peak)

### After Validation Phase:
- [ ] Validation backtest results (total P&L, by profile)
- [ ] Degradation analysis (train vs validation, by profile)
- [ ] Walk-forward quarterly breakdown
- [ ] Any regime-specific anomalies
- [ ] Decision: Proceed to test or revise?

### After Test Phase:
- [ ] Test backtest results (total P&L, by profile)
- [ ] Final degradation summary (train → validation → test)
- [ ] Ready for live trading checklist
- [ ] Live trading risk limits and monitoring plan

---

## SUCCESS CRITERIA (HARD TARGETS)

**Train Period (2020-2021):**
- Exit days successfully derived
- Permutation test p < 0.05 (validates parameters)
- Regime robustness: <30% difference between 2020 and 2021

**Validation Period (2022-2023):**
- Overall P&L: Positive (proves concept works)
- Capture rate: > 5% (prove exits capture meaningful portion of peak)
- Degradation: 20-40% (normal validation loss)
- Profitable profiles: ≥ 3 of 6 (majority of strategies work)
- No cliff degradation at specific date (indicates robustness)

**Test Period (2024):**
- Total P&L: Accept whatever it is (no re-optimization)
- Use results to calibrate live trading risk limits

---

## SCHEDULE

**Estimated Timeline:**
- Train phase deep dives: 2-3 days (permutation test, regime analysis, CHARM deep dive)
- Train backtest execution: 2-4 hours
- Validation backtest: 2-4 hours
- Analysis and reporting: 2-3 hours
- **Total: 3-5 days** (depending on backtest speed and findings)

---

## Sign-Off

When all criteria met:

```
Exit Engine V1 Status: [ ] READY FOR VALIDATION
Auditor: [Name]
Date: [Date]
Confidence Level: [%]
```

Once signed off, exit days are locked and parameter tuning ends. Any further changes require new validation cycle.

---

**Last Updated:** 2025-11-18
**Next Review:** After train phase completion
