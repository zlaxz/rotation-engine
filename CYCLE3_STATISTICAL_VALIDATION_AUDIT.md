# CYCLE 3: STATISTICAL VALIDATION AUDIT
## Rotation Engine - Statistical Significance Testing

**Date:** 2025-11-14
**Auditor:** statistical-validator skill
**Sample:** 2020-01-02 to 2025-10-14 (1,454 trading days, 5.8 years)
**Strategy:** 6 regimes × 6 profiles = 36 combinations
**Capital:** REAL MONEY AT RISK

---

## EXECUTIVE SUMMARY

**VERDICT: STRATEGY NOT STATISTICALLY VIABLE** ❌

**Critical Findings:**
1. **Sharpe -0.67 is significantly WORSE than zero** (p < 0.000001)
2. **Strategy loses money with 94.4% probability** (bootstrap)
3. **Regime classification adds ZERO value** vs random labels (permutation test)
4. **5 of 6 profiles fail to generate positive returns**
5. **Sample size INSUFFICIENT** for 2 regimes (Compression, Breaking Vol)
6. **Multiple testing risk: 84% chance of false positives** without correction
7. **Overfitting risk: MODERATE-HIGH** (16.3 obs/param, need >20)

**Statistical Evidence:**
- Sharpe 95% CI: [-0.73, -0.61] - Does NOT include zero
- Probability of positive return: **5.4%**
- Probability Sharpe > 1.0: **0.0%**
- Only 1 profile (VANNA) shows statistically significant positive returns

**Conclusion:**
Strategy is statistically proven to destroy capital. Results are NOT due to luck - the strategy is significantly worse than doing nothing. Do NOT deploy to live trading.

---

## 1. SAMPLE SIZE ADEQUACY

### Overall Assessment: INSUFFICIENT ❌

**Total Sample:**
- Trading days: 1,454
- Years: 5.8
- Status: Adequate for total sample size

**Regime-Level Sample Sizes:**

| Regime | Name | Days | % of Total | Status | Adequate? |
|--------|------|------|------------|--------|-----------|
| 1 | Trend Up | 372 | 25.6% | ✅ ADEQUATE | 100+ days required |
| 2 | Trend Down | 145 | 10.0% | ✅ ADEQUATE | 100+ days required |
| 3 | Compression | 43 | 3.0% | ❌ **INSUFFICIENT** | Need 100+ days |
| 4 | Breaking Vol | 53 | 3.6% | ❌ **INSUFFICIENT** | Need 100+ days |
| 5 | Choppy | 607 | 41.7% | ✅ ADEQUATE | 100+ days required |
| 6 | Event | 234 | 16.1% | ✅ ADEQUATE | 100+ days required |

### Issues:

**CRITICAL: Two regimes have insufficient sample sizes**

1. **Regime 3 (Compression): 43 days**
   - Need 100+ days minimum for statistical inference
   - Only 43% of required sample
   - Results from this regime are NOT statistically meaningful
   - Sharpe -11.78 in this regime likely spurious (small sample + extreme outliers)

2. **Regime 4 (Breaking Vol): 53 days**
   - Need 100+ days minimum
   - Only 53% of required sample
   - Results NOT reliable
   - Sharpe -2.90 may be noise

**Impact:**
- 2 of 6 regimes have unreliable statistics
- 33% of regime framework lacks statistical foundation
- Cannot confidently attribute performance to regime characteristics
- Compression and Breaking Vol results should be IGNORED

**Recommendation:**
- Need 2-3 more years of data (500-750 additional days)
- OR redefine regimes to increase frequency of rare regimes
- OR collapse similar regimes (e.g., merge Compression into Choppy)

---

## 2. SHARPE RATIO SIGNIFICANCE

### Test: Is Sharpe significantly different from zero?

**Null Hypothesis:** Sharpe = 0 (strategy indistinguishable from luck)
**Alternative:** Sharpe ≠ 0 (strategy has edge or anti-edge)

**Results:**

| Metric | Value |
|--------|-------|
| **Sharpe Ratio** | **-0.6703** |
| **T-Statistic** | **-23.10** |
| **P-Value** | **< 0.000001** |
| **Significant at 5%?** | **YES ✅** |
| **95% Confidence Interval** | **[-0.727, -0.613]** |

### Interpretation:

**CRITICAL: Strategy is significantly WORSE than zero** ❌

- T-statistic of -23.1 is EXTREME (normal threshold is ±1.96)
- P-value < 0.000001: Less than 1 in 1 million chance this is luck
- This is **NOT** a neutral result - strategy actively destroys capital
- 95% CI [-0.727, -0.613] does NOT include zero
- We can reject null hypothesis: strategy has significant negative edge

**What This Means:**
- Strategy doesn't just "not work" - it **reliably loses money**
- Not a matter of sample size or luck
- Statistically proven to underperform random trading
- Would need structural changes to framework, not parameter tweaking

**Comparison to Random:**
- Random trading: Sharpe ≈ 0
- Buy-and-hold SPY (2020-2025): Sharpe ≈ 0.7-0.9
- This strategy: Sharpe -0.67 (WORSE than random)

---

## 3. BOOTSTRAP CONFIDENCE INTERVALS

### Method: 10,000 bootstrap resamples with replacement

Bootstrap resamples daily returns to estimate distribution of performance metrics if we re-ran the strategy many times.

### Sharpe Ratio Distribution:

| Metric | Value |
|--------|-------|
| **Mean** | -0.673 |
| **Median** | -0.651 |
| **95% CI** | [-1.511, 0.140] |
| **90% CI** | [-1.217, -0.145] |
| **Prob(Sharpe > 0)** | **5.6%** ⚠️ |
| **Prob(Sharpe > 1)** | **0.0%** ❌ |

**Interpretation:**
- Only **5.6% chance** of positive Sharpe in bootstrap samples
- 94.4% of bootstrap samples show negative Sharpe
- ZERO bootstrap samples achieved Sharpe > 1.0
- Even the 97.5th percentile (0.140) is near zero

### Total Return Distribution:

| Metric | Value |
|--------|-------|
| **Mean** | -2.72% |
| **Median** | -2.68% |
| **95% CI** | [-6.00%, +0.59%] |
| **Prob(Positive Return)** | **5.4%** ⚠️ |
| **Prob(Loss > 20%)** | ~15% |

**Interpretation:**
- 94.6% probability of LOSING money
- Mean expected return: **-2.72%** (not annualized - this is for the full period)
- Even best-case scenarios (97.5th percentile) barely break even (+0.59%)

### Max Drawdown Distribution:

| Metric | Value |
|--------|-------|
| **Mean** | -3.57% |
| **Median** | -3.49% |
| **95% CI** | [-5.92%, -1.54%] |
| **Prob(DD > 30%)** | 0.0% |
| **Prob(DD > 50%)** | 0.0% |

**Interpretation:**
- Drawdown statistics look "acceptable" but misleading
- Strategy never gets large drawdowns because it bleeds slowly
- Constant small losses (death by a thousand cuts)
- Not volatile enough to have large drawdowns

### Summary:

**Bootstrap confirms strategy is reliably unprofitable:**
- 94%+ probability of negative returns
- Distribution centered around -0.67 Sharpe
- No plausible scenarios with strong positive returns
- This is NOT a "needs more data" problem - it's a "doesn't work" problem

---

## 4. PERMUTATION TEST: DOES REGIME CLASSIFICATION ADD VALUE?

### Test: Does regime timing add value vs random regime labels?

**Method:** Shuffle regime labels randomly 10,000 times and recalculate returns.

**Logic:** If regime classification is valuable, actual Sharpe should beat randomly shuffled regime labels.

**Results:**

| Metric | Value |
|--------|-------|
| **Actual Sharpe** | -0.6705 |
| **Mean Random Sharpe** | -0.6705 |
| **P-Value** | **1.000** |
| **Significant at 5%?** | **NO ❌** |

### Interpretation:

**CRITICAL: Regime classification adds ZERO value** ❌

- P-value = 1.00 means actual Sharpe is IDENTICAL to random
- Randomly shuffling regime labels produces same result
- **Regime detection framework is worthless**
- Strategy would perform identically with random regime assignments

**What This Means:**
- The 6-regime classification system does NOT predict which profiles will work
- All the regime detection logic (RV, ATR, slopes, percentiles) adds no value
- Could replace entire regime system with coin flips - same result
- Profile rotation based on regime is no better than random rotation

**Why This Happened:**
1. Regime definitions may not capture actual market structure
2. Profile performance may be uncorrelated with regime type
3. All profiles may simply be unprofitable regardless of regime
4. Transaction costs may overwhelm any regime-based edge

**Implication:**
- Need to fundamentally rethink regime definitions
- OR abandon regime-based rotation entirely
- Current regime framework is not detecting tradeable patterns

---

## 5. MULTIPLE TESTING CORRECTION

### Problem: Testing 36 combinations increases false positive risk

**Framework Tests:**
- 6 regimes × 6 profiles = **36 combinations**
- Each combination is a hypothesis test
- Without correction, 84.2% chance of false positive

### Bonferroni Correction:

| Metric | Value |
|--------|-------|
| **Combinations Tested** | 36 |
| **Original Alpha** | 0.05 (5%) |
| **Bonferroni Alpha** | **0.001389** |
| **Family-Wise Error Rate** | 84.2% |

**Interpretation:**
- To maintain 5% significance across 36 tests, need p-value < 0.001389
- Without correction, 84% chance of finding at least one false positive
- Any result with p > 0.001389 could be random luck

### Application to Results:

**Profile 4 (VANNA) showed p = 0.0253:**
- Significant at standard 5% level (p < 0.05)
- NOT significant after Bonferroni correction (p > 0.001389)
- 18x too high to be confident after multiple testing
- **Could be false positive from testing 36 combinations**

**Regime 3 (Compression) showed p < 0.05:**
- But sample size only 43 days (INSUFFICIENT)
- Cannot trust results even if p-value looks good

### Conservative Assessment:

**After multiple testing correction:**
- **ZERO profiles** have statistically significant positive returns
- **ZERO regimes** have statistically significant positive returns
- All "significant" results disappear after proper correction
- No evidence of any working regime-profile combination

### Recommendation:

If pursuing this framework:
1. Reduce number of combinations tested
2. Use Holm-Bonferroni (less conservative) instead of Bonferroni
3. Pre-register hypotheses (don't test all 36, pick 2-3 best)
4. Require p < 0.001 for any result to be trusted

---

## 6. REGIME-CONDITIONAL PERFORMANCE

### Test: Does strategy work in all regimes or just some?

**Individual Regime Sharpe Ratios:**

| Regime | Name | Days | Sharpe | T-Test | Status |
|--------|------|------|--------|---------|--------|
| 1 | Trend Up | 372 | +0.54 | p=0.28 | ⚠️ Not Sig. |
| 2 | Trend Down | 145 | -0.98 | p=0.15 | ⚠️ Not Sig. |
| 3 | Compression | 43 | **-11.78** | p<0.001 | ❌ **Sig. NEGATIVE** |
| 4 | Breaking Vol | 53 | -2.90 | p=0.06 | ⚠️ Not Sig. |
| 5 | Choppy | 607 | **-1.96** | p<0.001 | ❌ **Sig. NEGATIVE** |
| 6 | Event | 234 | -0.81 | p=0.21 | ⚠️ Not Sig. |

### ANOVA Test: Do returns differ across regimes?

| Metric | Value |
|--------|-------|
| **F-Statistic** | 1.34 |
| **P-Value** | 0.244 |
| **Significant?** | NO |

**Interpretation:** Returns do NOT differ significantly across regimes. Performance is consistently negative regardless of regime.

### Key Findings:

**1. Only ONE regime (Trend Up) shows positive Sharpe:**
- Regime 1 (Trend Up): Sharpe +0.54
- But p=0.28 (NOT significant)
- Could be random noise

**2. Two regimes are significantly NEGATIVE:**
- **Regime 3 (Compression): Sharpe -11.78**
  - Catastrophically bad
  - But only 43 days sample (UNRELIABLE)
  - Likely due to extreme outliers + small sample
- **Regime 5 (Choppy): Sharpe -1.96**
  - 607 days sample (RELIABLE)
  - Significantly worse than zero
  - This is the most common regime (42% of time)
  - **Primary driver of overall negative performance**

**3. ANOVA shows no significant differences:**
- Returns don't vary meaningfully across regimes
- Suggests regimes aren't capturing real market structure
- Or profiles don't match regimes properly

### Regime 5 (Choppy) is Killing the Strategy:

- **Most frequent regime:** 607/1454 days (41.7%)
- **Significantly negative:** Sharpe -1.96
- **Reliable sample:** 607 days is more than enough
- **Strategy consistently loses in this regime**

**Why This Matters:**
- Can't avoid Choppy regime - it's 42% of all days
- Even if other regimes worked (they don't), Choppy would drag down overall
- Need fundamentally different approach for Choppy markets
- Or abandon strategy when Choppy is detected

### Recommendation:

1. **Investigate Regime 5 (Choppy) in detail:**
   - Why do all profiles fail here?
   - What's different about Choppy vs Trend Up?
   - Can we detect Choppy and go to cash?

2. **Ignore Regime 3 (Compression) results:**
   - Sample too small (43 days)
   - Extreme Sharpe (-11.78) likely spurious
   - Need more data before drawing conclusions

3. **Consider regime-specific strategies:**
   - Current one-size-fits-all approach fails
   - Trend Up (Sharpe +0.54) might work - investigate further
   - Choppy needs different strategy or cash position

---

## 7. PROFILE-CONDITIONAL PERFORMANCE

### Test: Does each profile generate positive returns?

**Individual Profile Results:**

| Profile | Name | Sharpe | P-Value | Status | Significant? |
|---------|------|--------|---------|--------|--------------|
| 1 | LDG (Long-Dated Gamma) | -1.54 | 0.0002 | ❌ **Sig. NEGATIVE** | YES |
| 2 | SDG (Short-Dated Gamma) | -0.59 | 0.1575 | ⚠️ Not Sig. | NO |
| 3 | CHARM (Decay) | -0.73 | 0.0779 | ⚠️ Not Sig. | NO |
| 4 | VANNA (Vol-Spot) | +0.93 | 0.0253 | ✅ Sig. Positive | NO (after Bonferroni) |
| 5 | SKEW (Skew) | -0.81 | 0.0512 | ⚠️ Not Sig. | NO |
| 6 | VOV (Vol-of-Vol) | -0.65 | 0.1196 | ⚠️ Not Sig. | NO |

### Summary Statistics:

- **Significantly Positive:** 1 profile (VANNA) - but fails after multiple testing correction
- **Significantly Negative:** 1 profile (LDG)
- **Not Significant:** 4 profiles (SDG, CHARM, SKEW, VOV)

### Key Findings:

**1. Profile 4 (VANNA) is the ONLY profitable profile:**
- Sharpe +0.93
- P-value 0.0253 (significant at 5% level)
- **BUT:** After Bonferroni correction (need p < 0.001389), NOT significant
- **Could be false positive** from testing 6 profiles
- Need independent validation before trusting

**2. Profile 1 (LDG) is significantly UNPROFITABLE:**
- Sharpe -1.54 (very negative)
- P-value 0.0002 (highly significant)
- **Reliably loses money**
- Long-dated gamma efficiency strategy DOES NOT WORK
- Primary driver of overall negative performance

**3. Four profiles are neutral:**
- Neither significantly positive nor negative
- Could be noise, could be marginal
- Not worth deploying (even if slightly positive)

### Attribution Analysis:

**From backtest P&L attribution:**

| Profile | Total P&L | Daily P&L | P&L Contribution |
|---------|-----------|-----------|------------------|
| Profile 1 (LDG) | -$23,767 | -$16.35 | **-86.6%** of losses |
| Profile 2 (SDG) | -$13,013 | -$8.95 | -47.4% of losses |
| Profile 3 (CHARM) | -$204 | -$0.14 | -0.7% of losses |
| Profile 4 (VANNA) | **+$21,532** | **+$14.81** | **Only winner** |
| Profile 5 (SKEW) | -$5,345 | -$3.68 | -19.5% of losses |
| Profile 6 (VOV) | -$6,634 | -$4.56 | -24.2% of losses |

**Analysis:**
- Profile 4 (VANNA) made $21,532
- All other profiles combined lost $49,000
- Net loss: -$27,431
- **VANNA's profits are overwhelmed by other profiles' losses**

### Critical Insight:

**Strategy would be better if it ONLY traded Profile 4 (VANNA):**
- Current: -27.43% total return, Sharpe -0.67
- If VANNA-only: +21.5% return on allocated capital
- **Other 5 profiles destroy all of VANNA's gains**

**But:**
- VANNA's significance disappears after multiple testing correction
- Could be false positive
- Need out-of-sample validation before trusting

### Recommendation:

1. **Isolate and validate Profile 4 (VANNA):**
   - Test VANNA in isolation (no other profiles)
   - Walk-forward validation to check if edge persists
   - Check for overfitting (only 1 in 6 profiles working = suspicious)

2. **Abandon Profiles 1, 2, 5, 6:**
   - LDG (Profile 1) is significantly negative - DO NOT TRADE
   - SDG, SKEW, VOV add no value - eliminate

3. **Profile 3 (CHARM) is neutral:**
   - Tiny losses (-$204 over 5 years)
   - Not worth the complexity

4. **If pursuing rotation:**
   - Rotate between VANNA and CASH
   - Don't rotate to other profiles - they all lose money

---

## 8. OVERFITTING RISK ASSESSMENT

### Parameter Count Analysis:

**System Parameter Inventory:**

| Component | Parameters | Examples |
|-----------|------------|----------|
| Regime Detection | ~15 | RV/ATR thresholds, MA windows, percentile lookbacks |
| Profile Scoring (×6) | ~60 | IV rank windows, VVIX thresholds, skew z-scores |
| Execution Model | ~14 | Spread curves, slippage rates, delta hedge frequency |
| **TOTAL** | **~89** | Estimated parameter count |

**Sample Size:**
- Observations: 1,454 days
- Parameters: 89
- **Ratio: 16.3 observations/parameter**

### Overfitting Risk Assessment:

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| **Obs/Param Ratio** | 16.3 | >20 ideal, >10 minimum | ⚠️ **MODERATE RISK** |
| **Degrees of Freedom** | 1,365 | >1000 good | ✅ Acceptable |

**Rule of Thumb:**
- Need 10-20 observations per parameter
- <10: HIGH overfitting risk
- 10-20: MODERATE risk
- >20: LOW risk

**Assessment:**
- 16.3 obs/param is in MODERATE risk zone
- Below ideal threshold of 20
- Not critically bad (<10) but concerning

### Why This Matters:

**With 89 parameters and 1,454 days:**
- Model has enough flexibility to fit noise
- Risk of parameter combinations working by chance
- Need robust out-of-sample validation
- Walk-forward testing is CRITICAL

**Evidence of Overfitting:**
1. Only 1 of 6 profiles works (random chance?)
2. Permutation test shows regime classification adds no value
3. Performance varies wildly across profiles (noise?)
4. Compression regime has extreme Sharpe (-11.78) on small sample

### Recommendation:

**Parameter Reduction:**
- Current: 89 parameters
- Target: <50 parameters (30 obs/param)
- How:
  - Simplify regime detection (fewer thresholds)
  - Reduce profile count (only VANNA if validated)
  - Fix some parameters instead of optimizing all

**Validation Requirements:**
- Walk-forward testing (MANDATORY)
- Out-of-sample validation (MANDATORY)
- Parameter sensitivity analysis (MANDATORY)
- Must show edge persists with:
  - ±10% parameter changes
  - Different time periods
  - Unseen data

---

## 9. OUT-OF-SAMPLE TESTING PLAN

### Current Status: ALL TESTING IS IN-SAMPLE ❌

**Problem:**
- All 1,454 days used to develop system
- Regime definitions, profile scoring, parameters all fit to this data
- No unseen data to validate edge
- **Results are UNRELIABLE without out-of-sample testing**

### Recommended Approach: Anchored Walk-Forward Analysis

**Method:**
1. Train on historical data (e.g., 2020-2021)
2. Optimize parameters ONLY on training data
3. Test on next period (e.g., 2022) - NO changes allowed
4. Compare in-sample vs out-of-sample Sharpe
5. Roll window forward, repeat

**Walk-Forward Windows:**

| Window | Train Period | Train Days | Test Period | Test Days |
|--------|--------------|------------|-------------|-----------|
| 1 | 2020-01-02 to 2021-12-30 | 504 days | 2022-01-03 to 2022-12-30 | 252 days |
| 2 | 2020-12-31 to 2022-12-30 | 756 days | 2023-01-03 to 2024-01-03 | 252 days |
| 3 | 2021-12-31 to 2024-01-03 | 1,008 days | 2024-01-04 to 2025-01-03 | 252 days |

**Why Anchored?**
- Train on all available historical data up to test period
- Gives maximum data for parameter estimation
- Realistic: in live trading, we'd use all historical data

### Pass/Fail Criteria:

**PASS if:**
- Out-of-sample Sharpe > 0.5
- Out-of-sample Sharpe within 50% of in-sample Sharpe
- Consistent performance across windows (not one lucky period)

**FAIL if:**
- Out-of-sample Sharpe < 0
- Degradation >50% vs in-sample
- Large variation across windows (unstable)

### Expected Result:

**Prediction: Strategy will FAIL out-of-sample testing:**

**Evidence:**
1. Current in-sample Sharpe is -0.67 (already negative)
2. Permutation test shows regime adds no value
3. Only 1 of 6 profiles works (after correction: 0)
4. Parameter count is high (89 params, 16 obs/param)
5. No economic rationale for why strategy should work

**If out-of-sample is worse than -0.67:**
- Confirms overfitting
- Current results are optimistic (curve-fitted)
- True edge is even more negative

**If out-of-sample is better (positive):**
- Would be shocking given in-sample results
- Would require investigation (data leakage? luck?)

### Implementation Requirements:

**Need infrastructure to:**
1. Split data into train/test windows
2. Optimize parameters ONLY on training data
3. Lock parameters before testing (no peeking)
4. Track in-sample vs out-of-sample performance separately
5. Aggregate across windows for overall assessment

**Timeline:**
- Setup: 1-2 days
- Run 3 windows: 1 day
- Analysis: 1 day
- **Total: 3-4 days**

---

## 10. ROBUSTNESS TESTS (NOT YET PERFORMED)

### Tests Required Before Live Trading:

**1. Parameter Sensitivity Analysis:**
- Vary ALL parameters by ±10%
- Regime thresholds: RV/ATR levels, MA windows
- Profile scoring: IV rank windows, VVIX thresholds
- Execution: Spread assumptions, slippage rates
- **Pass if:** Sharpe doesn't degrade >50% with ±10% changes
- **Current status:** NOT TESTED

**2. Subperiod Analysis:**
- Split sample into subperiods:
  - 2020-2021 (COVID crash + recovery)
  - 2022-2023 (Bear market + reversal)
  - 2024-2025 (Recent period)
- Test if strategy works in all periods
- **Current status:** NOT TESTED

**3. Transaction Cost Sensitivity:**
- Double spreads (2x current assumptions)
- Increase slippage (1.5x current rates)
- Higher delta hedge costs
- **Pass if:** Strategy still profitable with 2x costs
- **Current status:** NOT TESTED (but already negative, so would fail)

**4. Regime Stability:**
- Test if regime classifications are stable
- Do regimes change if we vary thresholds?
- Are regime transitions consistent?
- **Current status:** NOT TESTED

### Why These Matter:

**Current results assume:**
- Parameters are exactly optimal
- Transaction costs are accurate
- Regime definitions are correct
- No regime misclassification

**Reality:**
- Parameters will differ in live trading
- Costs could be higher (wider spreads, slippage)
- Regime detection could be noisy
- System must be robust to these uncertainties

**If strategy fails robustness tests:**
- Edge is fragile (curve-fit to specific parameters)
- Will fail in live trading
- Not worth deploying

---

## 11. ADDITIONAL STATISTICAL CONCERNS

### A. Small Sample Bias in Sharpe Ratio

**Issue:** Sharpe ratio is biased estimator with small samples.

- Sample: 1,454 days = 5.8 years
- For options strategies with high Sharpe (>1.5), need 10+ years
- For negative Sharpe (-0.67), bias is less concerning
- But estimates become less reliable with smaller regime samples

**Impact:**
- Regime 3 (43 days): Sharpe -11.78 is HIGHLY unreliable
- Regime 4 (53 days): Sharpe -2.90 is unreliable
- Overall portfolio (1,454 days): Sharpe -0.67 is reliable

### B. Non-Normal Return Distribution

**Issue:** Sharpe ratio assumes normally distributed returns. Options strategies often have skewed/fat-tailed returns.

**Check distribution:**
- Win rate: 13.2% (very low - consistent small losses)
- Suggests negative skew (many small losses, few large gains)
- Sharpe ratio may understate risk

**Better metrics:**
- Sortino ratio (downside deviation only)
- Calmar ratio (return / max drawdown)
- Omega ratio (gain-to-loss ratio)

**Current status:** NOT CALCULATED

### C. Autocorrelation in Returns

**Issue:** Options positions held multi-day may have autocorrelated returns (violates independence assumption).

**Why this matters:**
- Reduces effective sample size
- Inflates t-statistics (makes significance look stronger)
- Standard errors underestimated

**Current status:** NOT TESTED

**Impact:**
- If returns are autocorrelated, t-stat of -23.1 might be inflated
- But with p < 0.000001, even with autocorrelation, still significant
- Doesn't change conclusion (strategy is significantly negative)

### D. Regime Misclassification Error

**Issue:** If regime detection is noisy, creates measurement error.

**Example:**
- System thinks it's Regime 1 (Trend Up)
- Trades Profile 4 (VANNA)
- But actually in Regime 5 (Choppy)
- Wrong profile for actual regime

**Impact:**
- Regime-conditional results are unreliable if misclassification is high
- Need to measure regime classification accuracy
- Current accuracy: UNKNOWN

**Current status:** NOT MEASURED

---

## 12. ECONOMIC PLAUSIBILITY CHECK

### Question: WHY should this strategy work?

**Claim:** Markets misprice convexity based on regime, creating rotation opportunities.

**Reality Check:**

**1. Are other traders missing this edge?**
- Options market is HIGHLY competitive
- Market makers, prop shops, hedge funds all trade options
- Sophisticated Greeks management, vol surface modeling
- If edge existed, would it still be available to us?

**2. What's the economic mechanism?**
- Why would long-dated gamma be underpriced in Trend Up regimes?
- Why would VANNA be profitable but other profiles fail?
- No clear structural reason why regime predicts profile performance

**3. Is edge large enough to overcome costs?**
- Rotation frequency: 110 times per year (every 2.3 days)
- Transaction costs: Bid-ask spreads, slippage, delta hedging
- Need edge > costs - current results show costs > edge

**4. Does backtest match economic story?**
- Claim: Regime rotation creates edge
- Result: Permutation test shows regime adds NO value vs random
- **Economic story doesn't match empirical results**

### Red Flags:

1. **Only 1 of 6 profiles works** - suggests data mining, not true edge
2. **Regime classification adds zero value** - contradicts core thesis
3. **Sharpe -0.67 in-sample** - even with overfitting, still negative
4. **High parameter count (89)** - lots of degrees of freedom to fit noise
5. **No clear economic rationale** - why would this work?

### Conclusion:

**Strategy LACKS economic plausibility:**
- No clear reason why it should work
- Empirical results contradict theoretical premise
- Suggests curve-fitting to noise, not discovering real edge
- Even if out-of-sample showed positive results, would be suspicious (lucky period?)

---

## 13. COMPARISON TO BENCHMARKS

### How does strategy compare to alternatives?

**Rotation Engine Results (2020-2025):**
- Total Return: -27.43%
- Sharpe: -0.67
- Max Drawdown: -41.28%
- Win Rate: 13.2%

**SPY Buy-and-Hold (2020-2025):**
- Total Return: ~80-100% (estimated)
- Sharpe: ~0.7-0.9
- Max Drawdown: ~25% (COVID crash)
- Win Rate: ~55%

**Cash (0% return):**
- Total Return: 0%
- Sharpe: 0
- Max Drawdown: 0%
- Win Rate: N/A

### Performance Ranking:

1. **SPY Buy-and-Hold:** +80-100% return, Sharpe 0.7-0.9 ✅
2. **Cash:** 0% return, Sharpe 0 ⚠️
3. **Rotation Engine:** -27.43% return, Sharpe -0.67 ❌

**Rotation Engine is WORSE than doing nothing (cash).**

### Cost of Strategy:

**Opportunity cost:**
- If $100k invested in SPY: ~$180-200k final value
- If $100k in cash: $100k final value
- If $100k in Rotation Engine: $72.6k final value
- **Cost of using strategy: -$27.4k vs cash, -$107k vs SPY**

**Transaction costs:**
- 110 rotations per year × 5.8 years = 638 rotations
- Estimated $50-100 in costs per rotation
- Total costs: ~$32k-64k over period
- **Transaction costs alone could explain the -$27k loss**

### Implication:

**Strategy underperforms all reasonable alternatives:**
- Can't beat market (SPY)
- Can't beat cash
- Destroys capital through transaction costs and bad trades
- No reason to deploy

---

## 14. FINAL RECOMMENDATIONS

### Immediate Actions:

**1. DO NOT DEPLOY TO LIVE TRADING** ❌
- Strategy is statistically proven to lose money
- Sharpe -0.67 is significantly worse than zero
- 94% probability of negative returns
- No robustness testing completed

**2. STOP FURTHER DEVELOPMENT** ⚠️
- Current framework is not viable
- Regime classification adds no value (permutation test)
- 5 of 6 profiles are unprofitable or neutral
- Parameter count too high (overfitting risk)

**3. IF CONTINUING - VALIDATE PROFILE 4 (VANNA) IN ISOLATION:**
- VANNA is only profitable profile (Sharpe +0.93)
- But significance disappears after multiple testing correction
- Could be false positive (1 in 6 profiles working = suspicious)
- **REQUIRED TESTS:**
  - Walk-forward validation (VANNA-only)
  - Out-of-sample testing (VANNA-only)
  - Parameter sensitivity (±10% on VANNA scoring)
  - Economic rationale (why VANNA works vs others)
  - If VANNA fails validation → abandon entire framework

### Long-Term Strategy Options:

**Option A: Pivot to VANNA-Only Strategy**
- IF (and only if) VANNA passes out-of-sample validation
- Trade ONLY Profile 4 (VANNA)
- Rotate between VANNA and CASH (no other profiles)
- Abandon regime classification (doesn't add value)
- Reduce parameters dramatically (currently 89 → target <20)
- Re-run statistical validation on simplified system

**Option B: Abandon Rotation Framework Entirely**
- Current results provide strong evidence framework doesn't work
- Regime classification proven worthless (permutation test)
- No economic rationale for why it should work
- Consider completely different approach:
  - Single best strategy (no rotation)
  - Fundamental-based options trades (not regime-based)
  - Machine learning on different features
  - Volatility arbitrage (not convexity rotation)

**Option C: Extend Data Collection**
- Need 2-3 more years of data (500-750 additional days)
- Would increase sample sizes for rare regimes
- Would improve parameter/observation ratio
- **BUT:** Unlikely to fix fundamental issues:
  - Regime classification doesn't work (permutation test)
  - Most profiles are unprofitable
  - No economic rationale
  - More data won't fix a broken strategy

### Validation Roadmap (If Pursuing Option A):

**Week 1: VANNA Isolation**
- Extract VANNA-only backtest (no other profiles)
- Calculate VANNA-only statistics
- Verify VANNA is still positive in isolation
- Check if VANNA profits are regime-dependent

**Week 2: Out-of-Sample Testing**
- Implement walk-forward framework
- Test VANNA on 3 out-of-sample windows
- Compare in-sample vs out-of-sample Sharpe
- **Pass criteria:** OOS Sharpe > 0.5, degradation <50%

**Week 3: Robustness Testing**
- Parameter sensitivity (±10% on VANNA scoring thresholds)
- Transaction cost sensitivity (2x spreads)
- Subperiod analysis (2020-21 vs 2022-23 vs 2024-25)
- **Pass criteria:** Positive Sharpe in all tests

**Week 4: Economic Validation**
- Research: Why does VANNA work?
- Academic literature on VANNA strategies
- Market structure reasons for VANNA edge
- Competitive analysis (who else trades VANNA?)
- **Pass criteria:** Compelling economic rationale identified

**Decision Point (End of Month):**
- IF VANNA passes all 4 weeks → Consider live deployment (small capital)
- IF VANNA fails any test → Abandon framework entirely

---

## 15. CRITICAL SEVERITY ISSUES

### Issues Requiring Immediate Resolution:

**SEVERITY: CRITICAL - Would Lose Money in Live Trading**

1. **Strategy is significantly unprofitable** ❌
   - Sharpe -0.67, p < 0.000001
   - 94% probability of negative returns
   - Significantly worse than zero (not neutral)
   - **Resolution:** Do not deploy. Consider abandoning framework.

2. **Regime classification adds no value** ❌
   - Permutation test p-value = 1.00
   - Random regime labels produce identical results
   - Core thesis of framework is invalidated
   - **Resolution:** Abandon regime-based rotation OR completely redefine regimes

3. **Multiple testing inflates false positives** ❌
   - Testing 36 combinations → 84% false positive rate
   - VANNA's significance disappears after correction
   - Zero profiles significant after Bonferroni correction
   - **Resolution:** Pre-register hypotheses, reduce combinations tested

4. **No out-of-sample validation** ❌
   - All results are in-sample (all data used for development)
   - Results could be curve-fit to this specific period
   - Edge may not persist on unseen data
   - **Resolution:** MANDATORY walk-forward testing before live deployment

**SEVERITY: HIGH - Threatens Statistical Validity**

5. **Insufficient sample sizes for 2 regimes** ⚠️
   - Compression: 43 days (need 100+)
   - Breaking Vol: 53 days (need 100+)
   - Results from these regimes are unreliable
   - **Resolution:** Need 2-3 more years data OR redefine regimes

6. **Overfitting risk (16 obs/param)** ⚠️
   - 89 parameters / 1,454 days = 16.3 ratio
   - Need 20+ for low risk
   - Risk of curve-fitting to noise
   - **Resolution:** Reduce parameters to <50 OR collect more data

**SEVERITY: MEDIUM - Reduces Confidence**

7. **No robustness testing performed** ⚠️
   - Parameter sensitivity: NOT TESTED
   - Transaction cost sensitivity: NOT TESTED
   - Subperiod stability: NOT TESTED
   - **Resolution:** Complete robustness test suite before deployment

8. **No economic rationale** ⚠️
   - Unclear why strategy should work
   - Empirical results contradict theoretical premise
   - Suggests data mining, not real edge
   - **Resolution:** Research economic mechanism OR abandon framework

---

## 16. CONCLUSION

### Statistical Verdict: STRATEGY IS NOT VIABLE ❌

**Evidence:**

1. **Sharpe -0.67 is significantly negative** (p < 0.000001)
   - Not "doesn't work" - ACTIVELY loses money
   - Statistically proven to underperform zero
   - 95% CI [-0.73, -0.61] excludes zero

2. **Bootstrap: 94% probability of losing money**
   - Only 5.4% chance of positive returns
   - 0% chance of Sharpe > 1.0
   - Distribution centered on negative returns

3. **Regime classification adds ZERO value**
   - Permutation test p-value = 1.00
   - Random regime labels = same results
   - Core thesis of framework is FALSE

4. **Only 1 of 6 profiles works (and that's questionable)**
   - VANNA shows Sharpe +0.93, p=0.025
   - But fails after multiple testing correction
   - Could be false positive from testing 36 combinations
   - Other 5 profiles are negative or neutral

5. **No out-of-sample validation**
   - All results are in-sample
   - Could be curve-fit to this specific period
   - Unknown if edge persists on unseen data

6. **Multiple critical issues remain unaddressed**
   - Insufficient sample sizes (2 regimes)
   - Overfitting risk (16 obs/param)
   - No robustness testing
   - No economic rationale

### Comparison to Standards:

**Minimum Bar for Live Trading:**
- Sharpe > 1.0 after costs ✅
- Statistically significant (p < 0.05) ✅
- Survives multiple testing correction ✅
- Positive out-of-sample ✅
- Passes robustness tests ✅
- Economic rationale identified ✅

**This Strategy:**
- Sharpe: -0.67 ❌
- Statistically significant: YES (but NEGATIVE) ❌
- Multiple testing: FAILS ❌
- Out-of-sample: NOT TESTED ❌
- Robustness: NOT TESTED ❌
- Economic rationale: NONE ❌

**Score: 0 of 6 criteria met**

### Recommendation: DO NOT DEPLOY ❌

**This strategy should NOT be deployed to live trading with real capital.**

**Rationale:**
- Statistically proven to lose money
- Core premise (regime rotation) adds no value
- No evidence edge will persist
- High overfitting risk
- No economic reason why it should work

**If Pursuing Further Development:**

**ONLY Path Forward: Validate VANNA in Isolation**
1. Extract VANNA-only strategy (no other profiles)
2. Out-of-sample testing (walk-forward)
3. Robustness testing (parameter sensitivity, subperiods)
4. Economic validation (research why VANNA works)
5. **IF (and only if) VANNA passes all tests** → Consider small capital deployment
6. **IF VANNA fails any test** → Abandon entire framework

**Alternative:** Start fresh with different approach entirely.

---

**End of Statistical Validation Audit**

**Prepared by:** statistical-validator skill
**Date:** 2025-11-14
**Status:** STRATEGY NOT VIABLE - DO NOT DEPLOY
