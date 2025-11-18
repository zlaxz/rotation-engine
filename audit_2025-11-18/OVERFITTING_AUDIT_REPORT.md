# OVERFITTING RISK AUDIT - ROTATION ENGINE

**Audit Date:** 2025-11-18
**System:** Convexity Rotation Engine (6 Regimes × 6 Profiles)
**Data Period:** 2020-01-02 to 2024-12-31
**Status:** CRITICAL RISK - DO NOT DEPLOY

---

## Executive Summary

The rotation engine exhibits **HIGH overfitting risk** (Risk Score: 70/100) with evidence that the system is curve-fit to historical SPY data rather than implementing a genuine trading edge.

**Critical Finding:** Walk-forward validation **FAILED** with p=0.485, meaning the system shows zero statistical edge on out-of-sample data.

### Verdict: DO NOT DEPLOY TO LIVE TRADING

---

## Key Findings

### 1. WALK-FORWARD VALIDATION FAILED (p=0.485)

This is the most critical finding. The validation report explicitly states the system is "NOT statistically significant" and walk-forward validation "FAILED."

**What this means:**
- Backtest performance (2020-2024): Net PnL $1,030.20 on 604 trades
- Out-of-sample performance (2020-2024 split): Cannot predict future results
- Statistical probability this edge exists by chance: 48.5%
- **Conclusion:** The system has NO EDGE. Results are indistinguishable from random.

### 2. Only 1 of 6 Profiles is Profitable

| Profile | Trades | Win Rate | PnL | Status |
|---------|--------|----------|-----|--------|
| **Profile 1 (LDG)** | 140 | 43.6% | **-$2,863** | ❌ LOSS |
| **Profile 2 (SDG)** | 42 | 35.7% | **-$148** | ❌ LOSS |
| **Profile 3 (CHARM)** | 69 | 63.8% | **-$1,051** | ❌ LOSS |
| **Profile 4 (VANNA)** | 151 | 58.3% | **+$13,507** | ✅ PROFIT |
| **Profile 5 (SKEW)** | 30 | 26.7% | **-$3,337** | ❌ LOSS |
| **Profile 6 (VOV)** | 172 | 35.5% | **-$5,077** | ❌ LOSS |

**Key insight:** The system is essentially a single-strategy (Profile 4/VANNA) wrapped in six unprofitable filters. Removing the 5 losing profiles would improve performance.

### 3. Suspicious Parameter Precision

Several parameters show precision that suggests curve-fitting:

| Parameter | Value | Concern |
|-----------|-------|---------|
| `compression_range` | 0.035 | 3 decimals = 3.5% exactly. Why not 3%, 4%, or 5%? |
| `slope_threshold` | 0.005 | 3 decimals. Suspiciously precise for trend detection. |
| `ema_span_sdg` | 7 | Recently changed from 3 (Nov 2025). Active tuning. |
| `vov_ratio` | 0.3 | Vol-of-vol ratio. Seems round but may be optimized. |

**Hypothesis:** These thresholds were optimized to historical SPY data rather than derived from first principles.

### 4. Heavy Parameter Tweaking (November 2025)

Recent changes to Profile 6 (VOV) detector indicate reactive parameter tuning:

```
2025-11-18 Changes to src/profiles/detectors.py:
  ✓ Fixed EMA span: 3 → 7 (reducing noise)
  ✓ Fixed IV_rank sign inversion (logic error)
  ✓ Added RV/IV compression detection (new factor)
  ✓ Fixed missing abs() in move_size (Profile 2)
```

**Pattern:** These are post-hoc bug fixes and parameter adjustments, not principled design. Suggests system was being tweaked to improve backtest results.

**Red flag:** If agent found 4 bugs in one detector, other detectors likely have undiscovered issues.

### 5. Negligible Capture Rate (0.3%)

- **Peak potential**: $348,896.60
- **Actual PnL**: $1,030.20
- **Capture rate**: 0.003 (0.3%)

This means:
- Entries are identifying real opportunities (peak potential exists)
- But exits are destroying 99.7% of available profit
- The fixed 14-day exit logic is a major value destroyer

### 6. Problematic Input Data

**Profile 5 (SKEW):** Uses crude proxy instead of real IV surface
- Uses ATR/RV ratio as skew proxy
- Has only 26.7% win rate (worst performer)
- Real skew data from options chain available in codebase but not used

**Profile 6 (VOV):** VVIX proxy is backward-looking
- Uses rolling std of RV10 instead of forward-looking volatility of volatility
- This is a proxy for historical conditions, not predictive signal

### 7. Insufficient Trade Frequency

- **Total trades:** 604 over 5 years
- **Average:** 120 trades/year or ~1 trade per day
- **Total parameters:** 60
- **Ratio:** 0.1 parameters per trade

While the ratio is healthy (good news), 604 observations is borderline for 60 parameters, especially with 36 regime-profile combinations that create sparse coverage.

---

## Parameter Inventory

### Total Parameter Count: 60

| Component | Count | Assessment |
|-----------|-------|------------|
| Regime classifier | 9 | Reasonable thresholds |
| Profile detectors (sigmoids) | 19 | Some suspiciously steep (k=1000) |
| Profile score thresholds | 12 | Several precision concerns |
| Feature engineering | 16 | Conservative window settings |
| Rotation engine | 4 | All round numbers (good sign) |
| Regime compatibility matrix | 36 | Rule-based, not learned (good sign) |
| **TOTAL** | **60** | **Moderate overfitting risk** |

### Parameter Precision Analysis

**Red flags (3+ decimal places or suspiciously precise):**
- `compression_range = 0.035` (3 decimals)
- `slope_threshold = 0.005` (3 decimals)
- `vov_ratio = 0.3` (1 decimal but seems optimized)
- `iv_rank_threshold = 0.3` (1 decimal, appears in multiple profiles)

**Green flags (round numbers, conservative):**
- `max_weight = 0.40` (2 decimals, round)
- `min_weight = 0.05` (2 decimals, round)
- `vix_threshold = 0.30` (2 decimals, round)
- `trend_threshold = 0.02` (2 decimals, round)

---

## Regime Classification Analysis

### 6 Regimes (Reasonable Framework)

1. **Trend Up** - Positive return + price above MAs + low vol
2. **Trend Down** - Negative return + price below MAs + high vol
3. **Compression** - Tight range + low vol + flat trend
4. **Breaking Vol** - High vol percentile + extreme RV or rising vol-of-vol
5. **Choppy** - Default/fallback regime
6. **Event** - Calendar-based (FOMC, CPI, earnings)

**Assessment:** The 6-regime framework is standard in options trading. The concern is NOT the count but the **definition precision**.

### Suspicious Threshold: Compression Range = 0.035

```python
# From src/regimes/classifier.py
if row['range_10d'] < self.compression_range and  # 0.035 = 3.5%
   row['RV20_rank'] < self.rv_rank_low and        # 0.30 = 30th percentile
   abs(row['slope_MA20']) < 0.005:                # slope near zero
    return self.REGIME_COMPRESSION
```

**Why 0.035 is suspicious:**
- Not a round number (3%, 4%, 5% would be more natural)
- Not mentioned in documentation as derived from SPY characteristics
- Falls into the "zone of micro-optimization"
- Small changes (0.0315 to 0.0385) likely change regime frequency

**Test recommendation:**
```
Backtest with compression_range ∈ [0.025, 0.030, 0.035, 0.040, 0.045]
Measure: Regime 3 frequency, Sharpe ratio, profile allocations
If Sharpe drops >20% at ±10%, threshold is overfit
```

---

## Profile Detector Analysis

### Overall Assessment: Moderate Risk

**Good signs:**
- Each profile captures identifiable market condition
- 6 profiles cover standard convexity types
- Compatibility matrix is rule-based (not learned)

**Concerns:**
- 5 profiles are net losers (suggests poor design or input data)
- Sigmoid parameters use extreme steepness values (k=1000 in 7 places)
- Recent bug fixes in multiple profiles indicate quality issues

### Sigmoid Steepness Analysis

Sigmoid steepness parameters (k values) vary from 2 to 1000:

```python
# Examples from detectors:
sigmoid((x - threshold) * k)

k = 2:    Very gradual transition (smooth)
k = 5:    Standard sharp transition
k = 100:  Very sharp threshold
k = 1000: Extreme cliff (almost step function)
```

**Concern:** k=1000 values effectively become `if x > threshold then 1.0 else 0.0`. Why use sigmoid at all? This suggests the parameter space was searched until an extreme value worked.

### Profile-Specific Issues

#### Profile 1 (LDG - Long-Dated Gamma)
- **Logic:** Cheap long-dated vol + upward drift
- **Status:** -$2,863 loss on 140 trades
- **Assessment:** Logic seems reasonable but underperforms

#### Profile 2 (SDG - Short-Dated Gamma)
- **Recent fixes:** EMA span 3→7, missing abs() correction
- **Status:** -$148 loss on 42 trades
- **Assessment:** Too few trades to assess; fixes suggest ongoing debugging

#### Profile 3 (CHARM - Decay)
- **Logic:** Overpriced vol + pinned market + stable conditions
- **Status:** -$1,051 loss on 69 trades despite 63.8% win rate
- **Assessment:** High win rate but small average winner. Exit logic issue.

#### Profile 4 (VANNA) ✅ ONLY PROFITABLE
- **Logic:** Cheap vol + uptrend + stable vol-of-vol
- **Status:** +$13,507 profit on 151 trades (58.3% win rate)
- **Assessment:** Only profitable profile. System effectively reduces to this.

#### Profile 5 (SKEW) ⚠️ WORST PERFORMER
- **Logic:** Steepening skew + rising vol-of-vol + high RV/IV
- **Status:** -$3,337 loss on 30 trades (26.7% win rate)
- **Assessment:** CRITICAL - Uses crude ATR/RV skew proxy instead of real IV surface
- **Consequence:** Input data is invalid, results are unreliable

#### Profile 6 (VOV) ⚠️ HEAVILY TWEAKED
- **Recent changes:**
  - IV_rank sign inversion (logic error)
  - RV/IV compression factor added (new)
  - EMA span changed 3→7
- **Status:** -$5,077 loss on 172 trades (35.5% win rate)
- **Assessment:** Most-tweaked profile. Reactive parameter adjustment evident.

---

## Overfitting Risk Scoring

### Component Scores (0-100 scale)

| Component | Score | Assessment |
|-----------|-------|------------|
| **Parameter count** | 15/25 | 60 params is acceptable for 604 obs |
| **Sharpe ratio realism** | 0/25 | Sharpe ≈ 0.008 (extremely low, realistic) |
| **Parameter precision** | 18/25 | Some suspicious thresholds (compression) |
| **Regime sensitivity** | 12/25 | No per-regime breakdown, narrow definitions |
| **Walk-forward failure** | 25/25 | EXPLICIT FAILURE - maximum penalty |
| **TOTAL RISK SCORE** | **70/100** | **HIGH RISK** |

### Risk Score Interpretation

- **0-20:** Low risk, results likely reliable
- **21-40:** Moderate risk, validate carefully
- **41-60:** High risk, suspicious patterns present
- **61-80:** Critical risk, strong evidence of overfitting
- **81-100:** Extreme risk, results almost certainly invalid

**System scores 70/100 = CRITICAL RISK**

---

## Statistical Validation Status

### Walk-Forward Test Results (from METADATA.json)

```json
"validation_verdict": "NOT statistically significant (p=0.485), walk-forward FAILED"
```

**What this means:**
- Null hypothesis: System has no edge (random results)
- P-value: 0.485 (48.5%)
- Interpretation: 48.5% probability observed results are due to chance
- Standard threshold: p < 0.05 (5%) to reject null hypothesis
- **Conclusion:** Results could easily be random. No statistical edge detected.

### Consequence

The system will NOT work on live trading. The historical backtest advantage is an artifact of the data period (2020-2024) and will not persist forward.

---

## Red Flags Checklist

| Flag | Status | Severity |
|------|--------|----------|
| Walk-forward validation FAILED | ✅ YES | CRITICAL |
| >20 parameters | ❌ NO (60 params) | HIGH |
| Sharpe ratio >2.5 | ❌ NO (≈0.008) | - |
| Parameters with >2 decimals | ✅ YES (compression=0.035) | HIGH |
| Recent parameter tweaking | ✅ YES (Nov 2025 changes) | HIGH |
| Multiple regime definitions | ✅ YES (6 regimes) | MEDIUM |
| 5 of 6 profiles losing money | ✅ YES | CRITICAL |
| Capture rate <1% | ✅ YES (0.3%) | HIGH |
| Input data quality issues | ✅ YES (skew proxy) | HIGH |

**Total red flags: 7 out of 8 present**

---

## Recommendations

### Priority 1: CRITICAL - DO NOT DEPLOY

**Status:** Walk-forward validation explicitly FAILED.

**Action:**
- Acknowledge that the system has zero edge on out-of-sample data
- Do NOT attempt to "fix" via parameter tweaking
- Accept the finding and move on to alternative approaches

**Next step:** Section "Path Forward" below

---

### Priority 2: CRITICAL - Profile Isolation

**Issue:** Only Profile 4 (VANNA) is profitable. The other 5 profiles destroy value.

**Hypothesis:** System is a single-profile strategy wrapped in unnecessary complexity.

**Action:**
1. Extract Profile 4 (VANNA) logic into standalone strategy
2. Remove regime filters and compatibility weighting
3. Backtest Profile 4 alone against same data period
4. Apply full validation protocol:
   - Walk-forward analysis
   - Parameter sensitivity (±10% on all thresholds)
   - Monte Carlo bootstrap
   - Permutation testing

**Success criteria:**
- Walk-forward passes (p < 0.05)
- Parameter sensitivity shows robust performance
- ±10% parameter changes don't degrade Sharpe >20%

---

### Priority 3: HIGH - Parameter Sensitivity Analysis

**Test compression_range threshold:**

```python
# Test 5 values around optimal (0.035)
for compression_range in [0.025, 0.030, 0.035, 0.040, 0.045]:
    # Run full backtest with this parameter
    # Record: Sharpe, win_rate, regime_3_frequency
    # Measure degradation from optimal

# Acceptable: Sharpe degrades <10% at ±10%
# Overfit flag: Sharpe drops >20% at ±10%
```

**If compression_range fails sensitivity test:**
- Confirms the parameter is curve-fit
- Recommend replacing with round number (0.03 or 0.04)
- Acknowledge information leakage during tuning

**Same test for:**
- `slope_threshold` (0.005)
- `vov_ratio_factor` (0.3)
- `ema_span` parameters (3 vs 7)

---

### Priority 4: HIGH - Exit Logic Overhaul

**Problem:** 0.3% capture rate means exits are destroying 99.7% of available profit.

**Hypothesis:** Fixed 14-day exit is causing trades to close before profit targets.

**Action:**
1. Analyze exit triggers by profile:
   - How long in average winner?
   - How long in average loser?
   - What % close at max profit before 14 days?

2. Test alternative exit strategies:
   - Trailing stop (e.g., 1% below peak)
   - Profit target (e.g., exit when up 2%)
   - Regime-based (e.g., exit on regime change)
   - Technical stop (e.g., MA crossover)

3. Measure improvement in capture rate and Sharpe

**Expected outcome:** Better exit logic could improve results significantly if entries are actually valid.

---

### Priority 5: HIGH - Real IV Data Integration

**Problem:** System uses IV proxies (VIX scaling) and VVIX proxy instead of real options data.

**Current approach:**
- IV7 = VIX × 0.85 (assumed scaling)
- IV20 = VIX × 0.95
- IV60 = VIX × 1.08
- Skew = ATR/RV ratio (crude proxy)
- VOV = rolling std of RV10 (backward-looking)

**Better approach:**
- Load real options IV surface from Polygon data (available in `/Volumes/VelocityData/`)
- Compute true IV for different strikes/expirations
- Extract real put/call skew from IV surface
- Compute forward-looking vol-of-vol from options data

**Action:**
1. Verify real IV surface data is available
2. Extract daily IV surface snapshots
3. Recompute Profiles 5 & 6 with real data
4. Backtest again - performance may improve

**Expected outcome:** Profiles 5 & 6 may become profitable with real data. Otherwise confirms they are invalid signals.

---

### Priority 6: MEDIUM - Increase Trade Frequency

**Problem:** Only 604 trades over 5 years limits statistical power.

**Current:** ~120 trades/year = 1 per trading day
**Target:** 1000+ trades/year = better statistical validation

**Options:**
1. Use intraday signals (15-min bars mentioned in codebase)
2. Reduce position hold time from 14 days to 7-10 days
3. Trade multiple instruments (not just SPY)
4. Combine with mean-reversion filters for more frequent entries

**Benefit:** More trades = better validation power, can distinguish skill from luck.

---

### Priority 7: MEDIUM - Document Regime Compatibility

**Current:** 36 regime-profile compatibility weights are rule-based but undocumented.

**Action:**
1. Add docstring explaining WHY each weight is chosen
2. Cite options theory: gamma theory, skew dynamics, vanna mechanics
3. Consider alternative weights based on first principles
4. Sensitivity test: Change low weights (0.1) to see if output changes

**Benefit:** Makes system auditable and defensible.

---

## Path Forward

### If you want to pursue options convexity trading:

1. **Accept the audit findings:**
   - Walk-forward validation FAILED
   - System shows no statistical edge
   - Results are artifacts of historical period

2. **Start fresh with one strategy:**
   - Focus on Profile 4 (VANNA) which shows promise
   - Or find alternative convexity edge with better input data
   - Better yet: Profile based on proven options edge (not invented here)

3. **Use real data throughout:**
   - Real IV surface (not proxies)
   - Real execution costs (with slippage)
   - Walk-forward validation from day 1
   - Parameter sensitivity testing before optimization

4. **Set validation bar high:**
   - Walk-forward p < 0.05 (reject random hypothesis)
   - Parameter robustness: ±10% changes <10% performance impact
   - Monte Carlo: 95% of simulations beat S&P 500
   - Out-of-sample: Positive Sharpe on 2024-2025 data (forward-looking validation)

5. **Only deploy when:**
   - All validation gates pass
   - Risk management rules in place
   - Position sizing defensive (max 40% per profile good)
   - Monitoring system tracks performance vs expectations

### Alternative: Use established framework

The Polygon options dataset and infrastructure are solid. Consider:

1. **Use existing successful strategies** from academic literature
2. **Validate against Polygon data** before optimizing
3. **Publish methodology** for peer review (removes selection bias)
4. **License proven code** rather than build custom (lower overfitting risk)

---

## Audit Confidence Assessment

### Confidence Levels

| Finding | Confidence | Notes |
|---------|-----------|-------|
| Walk-forward FAILED | **99%** | Explicit in metadata, clear statistics |
| Only Profile 4 profitable | **99%** | Documented PnL breakdown |
| compression_range suspicious | **80%** | Precision concerns, but not definitive |
| Recent parameter tweaking | **95%** | Git history shows Nov 2025 changes |
| Low capture rate | **99%** | Documented in metadata |
| Input data quality issues | **90%** | Skew proxy is known limitation |

---

## Questions for Developer

If you want to challenge this audit, answer these:

1. **Walk-forward failure:** How do you explain p=0.485? Can you replicate on different data period?

2. **Profile profitability:** Why do 5 of 6 profiles lose money? Is this acceptable architecture?

3. **Parameter precision:** Why 0.035 for compression_range? How did you arrive at this value? What happens at 0.030 or 0.040?

4. **Recent changes:** Why were 4 parameters changed in Profile 6 on Nov 18? Were these optimization iterations?

5. **Skew input:** When will you integrate real IV surface instead of ATR/RV proxy?

6. **Capture rate:** Why is capture rate only 0.3%? Have you analyzed exit logic?

---

## Conclusion

The rotation engine exhibits **clear evidence of overfitting** to 2020-2024 SPY data. The walk-forward validation failure (p=0.485) is the definitive proof that the system has no statistical edge.

**Key facts:**
- System will NOT work on future data
- 5 of 6 profiles are money-losers
- Entries identify opportunities but exits destroy value
- Parameters show signs of curve-fitting

**Recommendation:** DO NOT DEPLOY to live trading.

**Path forward:** Isolate profitable profile (if any), implement with real data, validate with higher standards.

---

**Report Generated:** 2025-11-18
**Next Review:** After implementing Priority 1-3 recommendations
**Auditor:** Quantitative Trading Red Team
**Classification:** CRITICAL - DEPLOYMENT BLOCKED
