# Statistical Audit Report - Rotation Engine
**Date:** 2025-11-18
**Audit Focus:** Round 4 validation - empyrical metrics library
**Verdict:** CRITICAL ERRORS FOUND - Results are statistically invalid

---

## Executive Summary

The metrics calculation system has a **CRITICAL BUG** that invalidates all Sharpe ratio, Sortino ratio, and risk-adjusted return calculations. The system passes **dollar P&L values** to `empyrical` library functions that expect **percentage returns**, resulting in meaningless (often infinite or extremely inflated) metric values.

**Status:** IMMEDIATE FIX REQUIRED before deploying any strategy based on these metrics.

---

## Critical Error #1: Input Type Mismatch in empyrical Library

### Location
- **File:** `src/analysis/metrics_empyrical.py`
- **Lines:** 38-48
- **Severity:** CRITICAL

### The Bug

```python
# Line 38: WRONG - passes dollar P&L
returns = portfolio['portfolio_pnl']  # <- This is DOLLAR amounts, not returns!

# Lines 42-48: empyrical functions receive dollar values instead of returns
metrics = {
    'sharpe_ratio': ep.sharpe_ratio(returns, period='daily'),      # <- WRONG!
    'sortino_ratio': ep.sortino_ratio(returns, period='daily'),    # <- WRONG!
    'calmar_ratio': ep.calmar_ratio(returns, period='daily'),      # <- WRONG!
    'annual_return': ep.annual_return(returns, period='daily'),    # <- WRONG!
    'annual_volatility': ep.annual_volatility(returns, period='daily'),  # <- WRONG!
    # ...
}
```

### Root Cause

Portfolio P&L is created as **dollar amounts** in `src/backtest/portfolio.py` (lines 103-109):

```python
for ret in portfolio['portfolio_return']:
    prev_values.append(prev_value)
    pnl = prev_value * ret              # <- Dollar amount
    daily_pnls.append(pnl)              # <- Dollar amount (e.g., $1000, not 0.001)
    prev_value = prev_value + pnl
    curr_values.append(prev_value)

portfolio['portfolio_pnl'] = daily_pnls  # <- Dollar P&L Series
```

But `empyrical` functions expect **returns** (0.001 = 0.1%, not $1000):

```python
# empyrical.sharpe_ratio() signature:
sharpe_ratio(returns, risk_free_rate=0.0, period='daily')
#            ^^^^^^^ - expects float returns like 0.001, not dollars like 1000
```

### Mathematical Impact

**With $1,000,000 initial capital and 0.1% daily returns:**

| Metric | Correct (Using Returns) | Wrong (Using Dollar PnL) | Inflation |
|--------|------------------------|--------------------------|-----------|
| Daily mean return | 0.001 (0.1%) | $1,000 | 1,000,000x |
| Daily std dev | 0.01 (1%) | $10,000 | 1,000,000x |
| Sharpe ratio | ~2.5 | **Infinite or extreme** | **1,000,000x+** |
| Annual return | 25% | Meaningless | Invalid |
| Annual volatility | 16% | Meaningless | Invalid |

**Consequence:** All published metrics are invalid. A strategy with true Sharpe ratio of 1.0 might show Sharpe of 100,000+ in results.

---

## Critical Error #2: No Convert-to-Returns Step

### Issue

The code **never converts** dollar P&L back to returns before passing to empyrical.

**The right approach:**

```python
# Option 1: Use portfolio_return directly
metrics = {
    'sharpe_ratio': ep.sharpe_ratio(portfolio['portfolio_return'], period='daily'),
    'sortino_ratio': ep.sortino_ratio(portfolio['portfolio_return'], period='daily'),
    # ...
}

# Option 2: Convert dollar PnL back to returns
portfolio_returns = portfolio['portfolio_pnl'] / portfolio['portfolio_prev_value']
metrics = {
    'sharpe_ratio': ep.sharpe_ratio(portfolio_returns, period='daily'),
    # ...
}
```

**Current code:** Uses dollar P&L directly (WRONG)

---

## Data Quality Findings

### ✓ Sample Size: ADEQUATE

| Metric | Value | Status |
|--------|-------|--------|
| Total observations | 698 | ✓ Good (2.77 years) |
| Valid for statistics | 678 (97.1%) | ✓ Good |
| Date range | 2023-01-03 to 2025-10-14 | ✓ Good |
| Minimum for Sharpe tests | ~100-250 obs | ✓ Exceeded |

Sample size is **sufficient for reliable statistical testing** (>250 observations).

### ⚠️ Regime Distribution: Sparse Coverage

| Regime | Count | % | Sufficient? |
|--------|-------|-----|-------------|
| Trend Up | 197 | 28.2% | ✓ Yes |
| Trend Down | 54 | 7.7% | ⚠️ Marginal |
| Compression | 31 | 4.4% | ❌ No (n<30) |
| Breaking Vol | 25 | 3.6% | ❌ No (n<25) |
| Choppy | 282 | 40.4% | ✓ Yes |
| Event | 109 | 15.6% | ✓ Yes |

**Issue:** Regimes 3 (Compression) and 4 (Breaking Vol) have <30 observations each. **Statistical tests on these regimes are unreliable.** Minimum recommended: 30-50 observations per regime.

---

## Multiple Testing Corrections Needed

### Hypothesis Testing Count

Estimated tests performed across system:

| Test Type | Count |
|-----------|-------|
| Individual profile Sharpe ratios | 6 |
| Regime-conditional Sharpes (6 profiles × 6 regimes) | 36 |
| Profile feature correlations | 10 |
| Greeks significance tests | 20 |
| Transaction cost validity tests | 5 |
| Regime transition tests | 6 |
| Profitability tests per regime | 6 |
| Parameter sensitivity tests (3 params × 6 profiles) | 18 |
| **Total** | **~107 tests** |

### False Positive Analysis

With 107 tests and **uncorrected α = 0.05**:

- **Expected false positives:** 5.4
- **Probability of at least one false positive:** 99.6%
- **Bonferroni correction:** α_adjusted = 0.05/107 = **0.000467**
- **Holm-Bonferroni:** More powerful, but still requires correction

### Recommendation

**IF multiple tests are reported with p-values:**
- Apply Holm-Bonferroni correction to all p-values
- Report adjusted significance levels
- Document which tests passed correction

**IF parameter grid search was performed:**
- Report how many parameter combinations were tested
- Apply multiple testing correction
- Use out-of-sample validation (walk-forward) to validate results

---

## Feature Calculation Audit

### ✓ Realized Volatility (RV): CORRECT

**Formula:** RV = sqrt(252) × std(log returns)

- Calculation verified ✓
- Annualization factor correct ✓
- Walk-forward compliant ✓

### ✓ IV Rank Percentiles: CORRECT

**Location:** `src/profiles/features.py` lines 207-231

- Uses past data only (no lookahead bias) ✓
- Correct percentile ranking implementation ✓
- Range [0, 1] validated ✓

### ✓ Z-Score Calculations (Skew): CORRECT

**Location:** `src/profiles/features.py` lines 173-196

- Formula: (value - mean) / std ✓
- 60-day rolling window ✓
- Epsilon (1e-6) prevents division by zero ✓

### ✓ IV Proxies: CORRECT

**Location:** `src/profiles/features.py` lines 81-121

- VIX-based (forward-looking) ✓
- Reasonable term structure scaling (0.85x, 0.95x, 1.08x) ✓
- Fallback to RV when VIX unavailable (backward-looking) ⚠️

---

## Annualization Factors: CORRECT

| Calculation | Factor | Usage | Status |
|-------------|--------|-------|--------|
| Volatility annualization | √252 ≈ 15.87 | RV20 daily → annual vol | ✓ Correct |
| Return annualization | 252 | daily returns → annual return | ✓ Correct |
| empyrical period param | 'daily' | tells library to use 252 factor | ✓ Correct |

---

## Walk-Forward Compliance: ✓ VERIFIED

**Key Files Audited:**
1. `src/profiles/features.py` - Percentile ranks use past data only ✓
2. `src/regimes/classifier.py` - Uses only historical data ✓
3. `src/data/features.py` - RV calculations walk-forward compliant ✓

**Potential Risk:** Portfolio P&L calculation must use walk-forward regime/profile scores. **Audit recommendation:** Verify that profile scores and regime labels at time `t` never use data from time `t` or later.

---

## Summary of Errors

### CRITICAL (Must Fix Immediately)

1. **Empyrical input type mismatch**
   - Location: `src/analysis/metrics_empyrical.py:38`
   - Issue: Passing dollar P&L instead of returns
   - Impact: All Sharpe, Sortino, Calmar ratios are invalid
   - Fix: Use `portfolio['portfolio_return']` or convert P&L to returns
   - **ALL BACKTEST RESULTS ARE INVALID UNTIL FIXED**

### HIGH (Fix Before Deployment)

2. **Insufficient regime samples for Breaking Vol and Compression**
   - Issue: <30 observations in 2 of 6 regimes
   - Impact: Statistical tests on these regimes unreliable
   - Fix: Extend backtest period or handle small-sample regimes separately

### MEDIUM (Recommended)

3. **Multiple testing corrections not documented**
   - Issue: ~107 tests with no multiple testing correction mentioned
   - Impact: Results may include statistical false positives
   - Fix: Apply Holm-Bonferroni correction if reporting p-values

---

## Detailed Recommendations

### Immediate (Before Publishing Any Results)

```python
# Fix 1: Use portfolio_return instead of portfolio_pnl
# File: src/analysis/metrics_empyrical.py, line 38

# WRONG:
# returns = portfolio['portfolio_pnl']

# RIGHT:
returns = portfolio['portfolio_return']

metrics = {
    'sharpe_ratio': ep.sharpe_ratio(returns, period='daily'),
    'sortino_ratio': ep.sortino_ratio(returns, period='daily'),
    'calmar_ratio': ep.calmar_ratio(returns, period='daily'),
    'annual_return': ep.annual_return(returns, period='daily'),
    'annual_volatility': ep.annual_volatility(returns, period='daily'),
    # ... etc
}
```

### Short-term (Before Strategy Deployment)

1. **Extend backtest period to get 50+ observations per regime**
   - Current: 25-31 obs for Compression/Breaking Vol
   - Target: 50+ for reliable statistical testing
   - Timeline: ~6-9 months more data needed

2. **If reporting p-values:**
   - Document all statistical tests performed
   - Apply Holm-Bonferroni multiple testing correction
   - Report adjusted p-values

3. **Validate walk-forward compliance:**
   - Code review: Ensure regime/profile scores at time t use only data up to time t
   - Audit: Check for any forward-looking bias in profile calculations

### Long-term (System Improvements)

1. **Add statistical significance tests:**
   - Bootstrap confidence intervals for Sharpe ratios
   - Permutation tests for regime performance differences
   - Out-of-sample validation (walk-forward)

2. **Document all assumptions:**
   - IV proxy methodology and limitations
   - Regime classification thresholds and rationale
   - Profile scoring weights and sensitivity

3. **Implement quality gates:**
   - Automated check that empyrical receives returns, not P&L
   - Automated check for regime sample sizes
   - Automated multiple testing correction

---

## Files That Need Review

### CRITICAL
- [ ] `src/analysis/metrics_empyrical.py` - Fix line 38 input type

### HIGH
- [ ] `src/backtest/portfolio.py` - Verify portfolio_pnl/portfolio_return semantics
- [ ] Any results published with Sharpe ratio metrics - **INVALIDATE**

### MEDIUM
- [ ] `src/regimes/classifier.py` - Verify all thresholds and validate small-sample regimes
- [ ] Any parameter sweep code - Check for multiple testing corrections
- [ ] Statistical validation scripts - Verify p-values are from walk-forward data

---

## Testing Checklist

- [ ] Sharpe ratio now using returns, not dollar P&L
- [ ] Sharpe values are now in reasonable range (typically 0.5-3.0 for good strategies)
- [ ] All previous results from old code are invalidated and re-run
- [ ] Walk-forward validation confirms no lookahead bias
- [ ] Regime sample sizes checked (minimum 30 per regime)
- [ ] Multiple testing corrections applied (if applicable)

---

## References & Standards

**Empyrical Library:**
- GitHub: quantopian/empyrical
- Docs: Uses percentage returns (0.01 = 1%), not dollar amounts

**Sharpe Ratio:**
- Requires returns data, not P&L
- Standard form: (mean return × √252) / (std return × √252)

**Multiple Testing Correction:**
- Bonferroni: α_adjusted = α / n_tests
- Holm-Bonferroni: More powerful, recommended
- False Discovery Rate (FDR): For exploratory analysis

**Walk-Forward Validation:**
- Standard in quantitative trading
- Prevents look-ahead bias
- Better predictor of live trading performance than overfitting on full backtest period

---

## Conclusion

The statistical infrastructure has **one critical data type error** that invalidates all risk-adjusted return metrics. Once fixed (single line change), the system has adequate sample size and generally sound methodology.

**Next Action:** Fix `src/analysis/metrics_empyrical.py` line 38, re-run all backtests, and re-validate results.

