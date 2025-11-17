# BUG REPORT - ROTATION ENGINE
**Generated:** 2025-11-13
**Red Team Audit Results**
**Status:** 🔴 CRITICAL ISSUE - DO NOT DEPLOY

---

## BUGS RANKED BY SEVERITY

### CRITICAL: 1 Issue (Causes Incorrect Results)

#### BUG #1: Slope Calculation Inconsistency
**Files:** `src/data/features.py:112-114`, `src/regimes/signals.py:74-78`

**Problem:**
Two different "slope" calculation methods used:
- `slope_MA20`: 5-day **percentage change** `(MA[t] - MA[t-5]) / MA[t-5]`
- `vol_of_vol_slope`: Linear **regression slope** `polyfit(x, y, 1)[0]`

**Evidence:**
```
Date: 2022-07-11
- Percentage change method: -0.014891
- Linear regression method: -1.059636
Difference: 71x magnitude difference!
```

**Impact:**
- Regime thresholds assume regression semantics (e.g., `slope > 0.001`)
- But calculation gives percentage semantics (e.g., 0.001 = 0.1% change)
- Likely causing regime misclassification
- Affects all profile scores that use slope

**Fix:**
```python
# OPTION 1 (Recommended): Use linear regression consistently
def compute_slope(df: pd.DataFrame, lookback: int = 5) -> pd.DataFrame:
    df = df.copy()
    for col in ['MA20', 'MA50']:
        if col in df.columns:
            slope = (
                df[col]
                .rolling(window=lookback, min_periods=3)
                .apply(lambda x: np.polyfit(range(len(x)), x, 1)[0]
                       if len(x) >= 2 else 0, raw=False)
            )
            df[f'slope_{col}'] = slope
    return df

# OPTION 2: Use percentage change but rescale ALL thresholds
# E.g., change `slope_MA20 > 0.001` to `slope_MA20 > 0.0001`
```

**Action Required:** FIX BEFORE ANY DEPLOYMENT

---

### MEDIUM: 2 Issues (Edge Cases, Affects Accuracy)

#### BUG #2: Slope Not Normalized by Price Level
**File:** `src/data/features.py:112-114`

**Problem:**
Linear regression slope (if Bug #1 fixed) returns absolute $/day, not rate.
- At SPY=$400: Slope of $1/day = 0.25% daily
- At SPY=$200: Slope of $1/day = 0.5% daily

**Impact:**
- Thresholds like `slope > 0.001` mean different things at different price levels
- Regime classification less stable over long periods
- Not critical for 2020-2024 (SPY range $300-$500 is ~2x, not 10x)

**Fix:**
```python
# Normalize by price level
slope_dollars = np.polyfit(range(len(x)), x, 1)[0]
slope_normalized = slope_dollars / x.mean()  # Now in %/day
```

**Priority:** Fix after Bug #1, before live trading

---

#### BUG #3: First 20-30 Days Have NaN Values
**Files:** `src/regimes/signals.py`, `src/profiles/features.py`

**Problem:**
Rolling windows need warmup period → first ~30 days have NaN for:
- `vol_of_vol`
- `slope_MA20`
- `IV_rank_20`
- Other rolling calculations

**Impact:**
- Cannot classify regime for first 20-30 days
- Acceptable for long backtests (1257 days)
- Limits short-term testing

**Fix:**
```python
# Document minimum required warmup
MIN_WARMUP_DAYS = 30

# Add validation
assert len(df[df['regime_label'].notna()]) >= len(df) - MIN_WARMUP_DAYS

# Or use expanding window for first N days
df['RV20_rank'] = df['RV20'].expanding().apply(...)
```

**Priority:** Document now, fix if needed for short-term testing

---

## VERIFIED ACCURATE (NO BUGS)

✅ **Percentile Calculations**
- Walk-forward compliance: VERIFIED (no lookahead bias)
- Accuracy: 3/3 manual checks passed (exact match)
- RV20_rank, IV_rank calculations: CORRECT

✅ **Profile Score Calculations**
- LDG score: 3/3 manual checks passed (exact match)
- Geometric mean: CORRECT
- Sigmoid transformations: CORRECT
- Score range [0,1]: VERIFIED (all profiles in valid range)

✅ **No Lookahead Bias**
- Tested by removing last 30 days → no historical changes
- Walk-forward compliance: VERIFIED

✅ **Edge Case Handling**
- Division by zero: Protected
- Extreme values: Handled correctly (2020 crash RV=96% is valid)
- Zero volume days: None found in data

---

## NOT AUDITED (REQUIRES FOLLOW-UP)

⚠️ **Trade Execution Timing**
- Question: Signal at bar N → enter at bar N or N+1?
- Need to verify realistic execution (can't trade on same bar as signal)
- Check: `trading/profiles/profile_*.py`

⚠️ **Transaction Cost Application**
- Need to verify costs applied to ALL trades (entries AND exits)
- Spot-check 10 random trades
- Sensitivity test: double costs → see impact on returns

⚠️ **Greeks Accuracy**
- Not computed from options data (synthetic Greeks?)
- Need benchmark comparison (QuantLib, py_vollib)
- Test 5 ITM + 5 ATM + 5 OTM at various DTE

⚠️ **Portfolio Aggregation**
- Need to run Day 6 validation
- Verify: weights sum ≤ 1.0 at all times
- Verify: weighted P&L adds up correctly

⚠️ **Timezone Consistency**
- All timestamps same timezone?
- Option expirations at correct time (4:00 PM ET)?
- Overnight gaps handled?

---

## RECOMMENDED FIX ORDER

### BLOCKING (Cannot Deploy):
1. ✅ Fix Bug #1 (slope calculation) - **2-4 hours**
2. ✅ Re-run all validation scripts (Day 1-6)
3. ✅ Re-run red team audit to verify fix

### Before Paper Trading:
4. ⚠️ Audit trade execution timing
5. ⚠️ Audit transaction cost application
6. ⚠️ Run Day 6 validation (portfolio)
7. ⚠️ Fix Bug #2 (normalize slope by price)
8. ⚠️ Document Bug #3 (warmup period)

### Before Live Trading:
9. ⚠️ Benchmark Greeks vs QuantLib
10. ⚠️ Audit timezone consistency
11. ⚠️ Stress test on 2008 crisis data
12. ⚠️ Sensitivity analysis (2x costs, etc.)

---

## OVERALL ASSESSMENT

**Code Quality:** 8/10
- Clean architecture
- Good separation of concerns
- Comprehensive testing infrastructure
- Walk-forward compliance enforced

**Calculation Accuracy:** 6/10
- Core calculations verified accurate (percentiles, profiles)
- **CRITICAL slope calculation bug found**
- Missing normalization for price levels
- Greeks not benchmarked

**Production Readiness:** 3/10
- **BLOCKED by Bug #1** (slope calculation)
- Missing trade execution audit
- Missing transaction cost verification
- Missing portfolio aggregation verification

**Recommendation:**
Fix Bug #1 immediately. Then run comprehensive Day 6 validation. Only then proceed to paper trading.

---

## CONCLUSION

**The good news:** 90% of the system is solid. Core regime detection and profile scoring are mathematically sound and walk-forward compliant.

**The bad news:** The slope calculation inconsistency is a CRITICAL bug that likely affects regime classification accuracy.

**The fix:** Straightforward - standardize on one slope method, re-run validations, done.

**Estimated time to production-ready:** 4-8 hours (fix + re-validation + follow-up audits)

---

**Real capital depends on fixing these bugs. Family depends on accuracy. Take pride in thorough auditing.**
