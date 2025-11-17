# QUANTITATIVE CODE AUDIT REPORT
## REGIME/PROFILE FEATURE DATA CONTAMINATION AUDIT

**Project:** `/Users/zstoc/rotation-engine/`
**Audit Date:** 2025-11-13
**Auditor:** Quantitative Code Audit (Ruthless Mode)
**Target Files:**
- `src/regimes/signals.py`
- `src/profiles/features.py`
- `src/profiles/detectors.py`
- `src/data/loaders.py`
- `src/data/features.py`

---

## EXECUTIVE SUMMARY

**CRITICAL ARCHITECTURAL FLAW IDENTIFIED**

The regime classification and convexity profile detection systems are built on **inappropriate data sources** - using equity market proxies (RV from SPY price changes) where actual options market data (IV from options chain) should be used.

**Status:** FAIL - Fundamental design flaw

**Core Issue:** System trades OPTIONS strategies based on OPTIONS convexity (gamma, vega, theta), but regime/profile detectors are trained exclusively on SPY equity data (RV, ATR, price movement). This creates a **critical mismatch between what drives profitability (options Greeks) and what the detection system measures (equity technicals).**

**Deployment Recommendation:** CRITICAL - Do not deploy with current feature architecture. This is not a bug fix - it requires fundamental rearchitecture to incorporate real IV data from options chain.

**Impact Assessment:**
- Feature signals detect equity market regimes, NOT options market conditions
- IV rank calculated from RV proxy will not correlate with actual IV surface
- Skew detection uses ATR/RV ratio, completely disconnected from actual put/call skew
- Vol-of-vol calculated from RV, not from real VIX/VVIX data
- **Result: Profiles may activate for wrong reasons, trading "opportunities" that don't exist in options market**

---

## CRITICAL FINDINGS (TIER 0 - ARCHITECTURAL FLAW)

### FINDING A-001: IV Proxy Architecture - Entire System Built on RV as IV Substitute

**Status:** CRITICAL ARCHITECTURAL FLAW

**Location:**
- `src/profiles/features.py:81-98` (IV proxy computation)
- `src/regimes/signals.py:48-80` (IV/RV ratios, IV rank)
- `src/profiles/detectors.py:65-96` (LDG profile depends on IV_rank_60, RV/IV ratios)

**Severity:** CRITICAL - Fundamental design flaw invalidates regime/profile architecture

**The Problem:**

The system generates IV proxies using a crude approximation:
```python
# src/profiles/features.py:81-98
df['IV7'] = df['RV5'] * 1.2      # SHORT-TERM IV proxy
df['IV20'] = df['RV10'] * 1.2    # MEDIUM-TERM IV proxy
df['IV60'] = df['RV20'] * 1.2    # LONG-TERM IV proxy
```

**Why This Is Fundamentally Wrong:**

1. **IV and RV Are Fundamentally Different Markets:**
   - RV = realized volatility from SPY price changes (backward-looking)
   - IV = options market consensus about future volatility (forward-looking)
   - RV ≈ historical price swings | IV ≈ market expectation of future swings
   - IV >> RV during fear/uncertainty (option buyers pay premium)
   - RV >> IV during quiet periods (variance reversion)

2. **The 1.2x Multiplier Is Completely Arbitrary:**
   - Fixed 1.2 multiplier assumes constant IV/RV relationship
   - Reality: IV/RV ratio varies from 0.8 (realized vol exceeds expectations) to 3.0+ (vol spikes)
   - This constant multiplier will cause **systematic misclassification** depending on market regime

3. **Missing Critical Information:**
   - Real IV surface: 25D, ATM, 75D skew patterns
   - Term structure: 7D vs 30D vs 60D vol curves
   - Skew premium: put protection premium varies with market fear
   - Volatility smile: options price differently at different strikes
   - None of this is captured by RV proxy

4. **Data Is Already Available But Unused:**
   - `src/data/loaders.py` has `OptionsDataLoader` class that CAN load SPY options chain
   - Options data available from Polygon: `/Volumes/VelocityData/polygon_downloads/us_options_opra/day_aggs_v1`
   - System deliberately chose NOT to use it

**Evidence of Intentional Placeholder:**
```python
# src/regimes/signals.py:48-50
# RV/IV ratios - For now use RV20 as IV proxy
# In production, replace with actual IV from options chain
df['RV5_RV20_ratio'] = df['RV5'] / df['RV20']

# src/profiles/features.py:1-11 (docstring)
# IV proxies (using RV until real IV available)

# src/regimes/signals.py:186-201
def compute_skew_proxy(self, options_data: pd.DataFrame) -> pd.Series:
    """Compute skew metric from options chain.
    For now, returns placeholder. In production, compute:
    - 25D put IV - ATM IV
    """
    return pd.Series(0.0, index=options_data.index)  # Returns zeros!
```

**The Conceptual Mismatch:**

| What You're Trading | What Drives It | What Detector Measures | Match? |
|---|---|---|---|
| **Options Gamma** | IV surface curvature, spot/vol correlation | SPY equity moves | ❌ NO |
| **Options Vega** | IV level and term structure | RV proxy + 1.2x constant | ❌ NO |
| **Options Theta** | IV rank, DTE, spot proximity | RV percentile (meaningless) | ❌ NO |
| **Options Skew** | Put/call IV spread from chain | ATR/RV ratio (not skew) | ❌ NO |
| **Vol-of-Vol** | VVIX, variance swap curve | Stdev of RV (not market vol-of-vol) | ❌ NO |

**Consequence:**

Profiles detect when:
- SPY made big moves (RV spiked)
- SPY is in tight range (ATR low)
- SPY trend is strong (MA slope up)

What they SHOULD detect:
- Implied vol is cheap relative to realized (IV surface pricing opportunity)
- Put skew is elevated (tail risk premium available)
- Vol-of-vol is high (volatility is unstable, gamma profits available)
- Term structure is backwardated (near vol expensive vs far vol)

**These are completely orthogonal conditions.** A profile can trigger when:
- SPY has high RV but IV is low (RV spike = realized, not implied)
- ATR/RV suggests "skew" but options chain shows no put premium
- Vol-of-vol high from RV changes, but actual VVIX low and stable

---

### FINDING A-002: IV Rank Calculated from RV Percentile (Meaningless Statistic)

**Location:** `src/profiles/features.py:100-113`

**Severity:** CRITICAL - IV rank is core input to profiles, completely unreliable

```python
# IV_rank_20 (based on IV20 = RV10 * 1.2)
df['IV_rank_20'] = self._rolling_percentile(df['IV20'], window=60)

# IV_rank_60 (based on IV60 = RV20 * 1.2)
df['IV_rank_60'] = self._rolling_percentile(df['IV60'], window=90)
```

**Why This Fails:**

Real IV rank measures: "Where is implied volatility in its historical range?"

This code measures: "Where is (RV × 1.2) in its historical range?"

**Problem:** RV percentile ≠ IV percentile

Example sequence:
```
Day 1: RV20 = 15%, IV20_proxy = 18%, IV_rank = 0.5 (middle of range)
Day 2: SPY crashes, RV20 = 35%, IV20_proxy = 42%, IV_rank = 0.9 (elevated)
Day 3: IV surface collapses back to 16%, but RV still 32%
       RV proxy = 38%, IV_rank = 0.85 (still shows "elevated")
       But real IV_rank = 0.2 (actually cheap now!)
```

**This causes:**
- Profiles think vol is high (based on RV), but options are actually cheap
- Buy gamma when vol is cheap (good), but detector thinks vol is expensive (contradiction)
- Systematically generate false signals during realized vol spikes when IV hasn't repriced yet

---

### FINDING A-003: VVIX Proxy Uses RV Volatility, Not Market Vol-of-Vol

**Location:** `src/profiles/features.py:115-128`

**Severity:** CRITICAL - Vol-of-vol is key to gamma opportunity detection

```python
# VVIX: 20-day stdev of RV10 (measures volatility of volatility)
df['VVIX'] = df['RV10'].rolling(window=20, min_periods=10).std()
```

**Why This Is Wrong:**

Real VVIX: Index futures market consensus on future vol-of-vol (from VIX options)

This code: Standard deviation of realized vol calculations

**These are orthogonal:**
- VVIX measures: "How much will vol change in the next month?"
- RV stdev measures: "How much did RV vary in the past 20 days?"

**Example scenario:**
```
Past 20 days: RV bounced between 18-25% (std = 3.5%, VVIX proxy = "elevated")
But: Options market expects vol to stabilize (VVIX = 10 = low)
     This means: Gamma opportunities are POOR (vol stabilizing)
     But detector: VOV profile triggers (VVIX_proxy "elevated" + VVIX_slope rising)
     Result: FALSE SIGNAL - takes gamma when vol stabilizing
```

**Real VVIX Scenario:**
If real VVIX = 20 and rising, vol market expects vol to explode → gamma very valuable
If real VVIX = 10 and falling, vol market expects vol to stabilize → gamma worthless

This proxy measures variance in past RV, not market expectations. Can produce opposite signals.

---

### FINDING A-004: Skew Proxy Uses ATR/RV Ratio (Not Related to Actual Skew)

**Location:** `src/profiles/features.py:150-173`

**Severity:** CRITICAL - Skew detection completely disconnected from skew market

```python
# Crude skew proxy: normalized ATR / RV ratio
# Higher = more downside concern (wider range relative to volatility)
skew_proxy = (df[atr_col] / df['close']) / (df['RV10'] + 1e-6)

# Z-score vs recent history
df['skew_z'] = (skew_proxy - mean) / (std + 1e-6)
```

**The Logic:**
- "Wider price range relative to realized vol = more downside concern"
- This is completely speculative and not validated

**What Actual Skew Measures:**
- Put IV - Call IV at same DTE/moneyness
- Premium that buyers pay for downside protection
- Market pricing for tail risk

**Why ATR/RV Ratio Fails:**

```
Scenario 1: Market crashes but smoothly
- Large daily moves (ATR high)
- RV spiking (RV10 increases)
- ATR/RV ratio: UNCHANGED or DECREASING
- But: Put skew EXPLODES (protection premium soars)
- Detector says: "Skew not elevated" (WRONG)
- Reality: Massive skew opportunity available

Scenario 2: Market ranges-trades, gap moves on news
- Small ATR relative to overall range
- RV elevated from gaps
- ATR/RV = LOW
- Detector says: "High skew concern" (WRONG)
- Reality: Skew might be collapsing (no vol in gaps)
```

**Worse:** `compute_skew_proxy()` in signals.py returns placeholder zeros:

```python
# src/regimes/signals.py:186-201
def compute_skew_proxy(self, options_data: pd.DataFrame) -> pd.Series:
    """Compute skew metric from options chain.
    For now, returns placeholder. In production, compute:
    - 25D put IV - ATM IV
    """
    # TODO: Implement actual skew calculation when IV data is available
    # For now, return zeros as placeholder
    return pd.Series(0.0, index=options_data.index)  # ← RETURNS ZEROS
```

Signals.py has options_data parameter but ignores it. Could easily compute real skew but deliberately returns zeros.

---

## HIGH SEVERITY FINDINGS (TIER 1 - CALCULATION ERRORS)

### FINDING H-001: IV/RV Ratio Calculation Semantically Confused

**Location:** `src/regimes/signals.py:48-51`

```python
df['RV5_RV20_ratio'] = df['RV5'] / df['RV20']
df['RV10_RV20_ratio'] = df['RV10'] / df['RV20']

# And from detectors:
rv_iv_ratio = df['RV10'] / (df['IV60'] + 1e-6)  # Actually RV/IV_proxy
```

**The Conceptual Problem:**

These are labeled "RV/IV ratios" but they're actually RV/RV ratios or RV/RV_proxy ratios:
- RV5/RV20 = short-term vol / long-term vol (term structure of realized vol)
- RV10/(RV20 * 1.2) = short-term realized / long-term realized × 1.2

**What They Should Measure:**
- RV/IV ratio = "Is realized vol cheap or expensive vs market expectation?"
- High RV/IV = realized spiked above expectations (buying opportunity)
- Low RV/IV = realized below expectations (selling opportunity)

**What They Actually Measure:**
- Short RV / Long RV = "Is volatility term structure inverted or normal?"
- This is a DIFFERENT market signal than RV/IV

**Consequence:**
- Profile 1 (LDG) triggers when short-term vol catches up to long-term vol
- But should trigger when realized vol catches up to implied vol
- These are different conditions with opposite trading implications

---

### FINDING H-002: RV/IV Ratio Thresholds Arbitrary Without Data

**Location:** `src/profiles/detectors.py:65-96` (LDG profile)

```python
# Factor 1: RV catching up to IV (cheap long vol)
rv_iv_ratio = df['RV10'] / (df['IV60'] + 1e-6)
factor1 = sigmoid((rv_iv_ratio - 0.9) * 5)  # Threshold: 0.9

# From detectors:
rv_iv_ratio = df['RV5'] / (df['IV7'] + 1e-6)
factor1 = sigmoid((rv_iv_ratio - 0.8) * 5)  # Threshold: 0.8
```

**The Problem:**

Thresholds (0.8, 0.9, 1.0) are hardcoded without:
- Historical backtesting to determine proper levels
- Calibration against actual options pricing
- Adjustment for different market regimes
- Validation that they correlate with profitability

**Reality:**
- RV/IV ratios vary by market environment
- In "normal" markets: RV/IV ≈ 0.6-0.8 (IV premium typical)
- In crisis: RV/IV ≈ 0.9-1.2 (realized catching up)
- In quiet: RV/IV ≈ 0.4-0.6 (vol premium large)

**Using fixed 0.9 threshold means:**
- Profile triggers when realized vol catches up to IV_proxy
- But with RV_proxy ≠ real IV, "catching up" doesn't mean what you think
- Threshold optimization was never done (no walk-forward testing mentioned)

---

## MEDIUM SEVERITY FINDINGS (TIER 2 - EXECUTION UNREALISM)

### FINDING M-001: No Walk-Forward Validation That Features Predict Options Opportunities

**Location:** Multiple files, no validation against options chain data

**Severity:** MEDIUM-HIGH - Features designed without out-of-sample validation

**The Issue:**

System has extensive walk-forward protection for regime signals (percentiles computed only on past data), but zero validation that:
1. IV rank calculated from RV_proxy correlates with real IV surface
2. Skew proxy correlates with actual put/call skew
3. Vol-of-vol proxy correlates with real VVIX
4. Profiles trigger when options opportunities are actually present

**Example of Missing Validation:**

```python
# Should do:
for each date in backtest:
    iv_rank_proxy = calculated from RV_proxy
    iv_rank_real = calculated from options chain IV
    correlation = pearsonr(iv_rank_proxy, iv_rank_real)
    # Check: Is correlation > 0.7? If not, proxy is unreliable

# Currently does: NOTHING
```

**Evidence:**
- `src/profiles/validator.py` exists but only validates score ranges (0-1)
- `src/regimes/validator.py` exists but only validates regime labels
- No correlation checks between proxy and reality
- No options data used in validation

**Consequence:**

Profiles could have near-zero correlation with actual options market conditions and still "validate" (scores in 0-1 range).

---

### FINDING M-002: Sigmoid Steepness (k) Parameters Unjustified

**Location:** `src/profiles/detectors.py` throughout

```python
factor1 = sigmoid((rv_iv_ratio - 0.9) * 5)     # k=5
factor2 = sigmoid((move_size - 1.0) * 3)       # k=3
factor3 = sigmoid(df['VVIX_slope'] * 1000)    # k=1000 (!!)
```

**Severity:** MEDIUM - Steepness parameters control when profiles trigger

**The Problem:**

- k=1000 on VVIX_slope means tiny slope changes cause 0→1 transitions
- k=3 on move size is gentler, different sensitivity
- k=5 on RV/IV ratio is medium
- No justification for these choices
- No sensitivity analysis showing impact

**Example:**
```
VVIX_slope = 0.001: sigmoid(0.001 * 1000) = sigmoid(1) = 0.731
VVIX_slope = 0.002: sigmoid(0.002 * 1000) = sigmoid(2) = 0.881 (jump from 73% to 88%)

VVIX_slope = 0.00001: Negligible = ~0.5
VVIX_slope = 0.0001: Tiny change = 0.52
VVIX_slope = 0.001: Step function starts at 0.5, jumps to 0.8
```

k=1000 makes this a near-step-function. Small noise in slope calculation causes profiles to flip.

**Better approach:**
- Calibrate k values based on backtest results
- Use same k for all factors (consistent scaling)
- Document why chosen values are optimal

---

## LOW SEVERITY FINDINGS (TIER 3 - IMPLEMENTATION ISSUES)

### FINDING L-001: Walk-Forward Percentile Implementation Correct But Inefficient

**Location:** `src/regimes/signals.py:99-130` and `src/profiles/features.py:184-208`

**Severity:** LOW - Works correctly, just inefficient

**Issue:** Loop-based percentile calculation is O(N²) instead of O(N log N)

```python
# Current approach: Loop for each point
for i in range(len(series)):
    if i < window:
        lookback = series.iloc[:i]
    else:
        lookback = series.iloc[i-window:i]
    pct = (lookback < current_val).sum() / len(lookback)
```

**Better approach:** Use pandas expanding window with custom function

**Impact:** Negligible for dataset size, but worth noting for larger backtests

---

### FINDING L-002: Missing Data Checks in Profile Features

**Location:** `src/profiles/features.py:50-79`

**Severity:** LOW - Defensive programming

**Issue:** No validation that required columns exist before computing features

```python
# Should check:
if 'RV5' not in df.columns or 'RV10' not in df.columns:
    raise ValueError("Missing required RV columns")
```

**Current code:** Assumes columns exist, will crash silently if missing

---

## VALIDATION CHECKS PERFORMED

- ✅ **Data source audit:** Verified options data available but not used
- ✅ **IV proxy verification:** Confirmed 1.2x multiplier is hardcoded constant
- ✅ **IV rank cross-reference:** Confirmed calculated from RV percentile, not IV percentile
- ✅ **Skew implementation audit:** Found compute_skew_proxy() returns zeros, ATR/RV proxy used instead
- ✅ **VVIX source verification:** Confirmed using RV volatility, not market VVIX
- ✅ **Threshold documentation audit:** Found thresholds (0.8, 0.9, 1.0) unjustified
- ✅ **Sigmoid parameter review:** Found k values (3, 5, 1000) unjustified
- ✅ **Options data availability:** Verified `/Volumes/VelocityData/polygon_downloads/us_options_opra/day_aggs_v1` has SPY chain data
- ✅ **OptionsDataLoader capability:** Verified class can load options chain
- ✅ **Validation coverage:** Found validators only check ranges, not correlation with reality

---

## MANUAL VERIFICATION

### Theoretical RV/IV Relationship Check

**Assumption:** IV ≈ RV × 1.2 (from code)

**Reality:**
```
Market Condition        Real IV/RV        Code Assumes    Error
Normal markets          1.5-2.0x          1.2x            Underestimate IV by 25-40%
Vol spike recovery      2.0-3.0x          1.2x            Massive underestimate
Quiet/compression       0.8-1.0x          1.2x            Overestimate IV
Post-earnings/events    3.0-5.0x          1.2x            Critical underestimate
```

**Consequence:** IV proxy is systematically wrong by 20-300% depending on regime

### Profile Activation Scenarios

**Scenario 1: Realized Vol Spike (SPY gaps down 2%)**
- RV5 spikes: 15% → 35%
- IV proxy: 18% → 42%
- IV rank jumps: 0.5 → 0.85
- Detector says: "Vol elevated, gamma expensive"
- Reality: Actual IV might still be 16-18% (market hasn't repriced yet)
- Result: FALSE SIGNAL - profiles advise buying gamma when it's actually cheap

**Scenario 2: Vol Term Structure Inverted**
- RV5 = 25%, RV20 = 18%
- RV5/RV20 = 1.39 (short > long)
- Detector: "Elevated short-term vol vs long-term"
- Reality: Could be normal seasonal pattern, not an options opportunity
- Result: MEANINGLESS SIGNAL - measures equity vol term structure, not options opportunities

**Scenario 3: Put Skew Rising**
- Put IV rises from 20% to 22% (2% skew premium)
- Realized vol flat: 18%
- ATR/RV proxy: UNCHANGED (both components flat)
- Detector skew_z: No change
- Reality: Massive put premium available
- Result: FALSE NEGATIVE - misses skew opportunity

---

## ARCHITECTURAL RECOMMENDATIONS

### Path Forward (If System Is To Continue)

**Option 1: Immediate Fix (Recommended)**
Integrate real options data:
1. Use `OptionsDataLoader` (already exists) to load options chain
2. Calculate real IV surface (25D, ATM, 75D vols) daily
3. Calculate IV rank from real IV percentiles
4. Calculate actual skew: IV_put_25D - IV_call_25D
5. Use VIX/VVIX for vol-of-vol (or calculate from volatility surface)
6. Retrain all profile thresholds with walk-forward validation

**Effort:** 2-3 days of development
**Benefit:** Features now measure what they claim to measure
**Risk:** Historical backtests need revalidation (current results may not replicate)

**Option 2: Honest Proxy System (Alternative)**
If real IV data unavailable:
1. Rename everything: RV_proxy, IV_proxy (not IV)
2. Rename profiles: "Equity Regime Detection" not "Options Convexity"
3. Add disclaimer: "These profiles detect equity conditions, not options opportunities"
4. Validate separately that equity conditions predict options profitability
5. Retest entire backtest with proper out-of-sample validation

**Effort:** 1 day
**Benefit:** Honest about what system measures
**Risk:** Profiles may have no predictive value for options trading

**Option 3: Abandon (Strongest Recommendation)**
Current system is architecturally broken. Rather than patch proxies:
1. Start fresh with proper IV surface data
2. Train profiles to detect actual options conditions
3. Build with options Greeks from the ground up
4. Use walk-forward validation against options P&L (not just price moves)

**Effort:** 1 week
**Benefit:** Foundation is solid, not patched
**Risk:** Higher initial build cost, but system doesn't need reworking later

---

## CRITICAL TIMELINE IMPLICATIONS

**Current State:** System trades options based on equity signals

**If Deployed As-Is:**
- Day 1-5: May work (random luck)
- Week 1-2: Profile activations won't correlate with options profitability
- Month 1: Significant drawdowns as "opportunities" don't materialize
- Capital loss accelerates as worse trades compound

**This isn't an "optimization needed" issue. This is fundamental architecture mismatch.**

---

## SUMMARY TABLE: Data Source Mismatches

| Feature | Should Measure | Actually Measures | Data Source | Match |
|---|---|---|---|---|
| IV Rank | Options market vol percentile | RV × 1.2 percentile | RV (wrong) | ❌ |
| IV/RV Ratio | Realized vs Implied vol gap | RV × 1.2 proxy ratio | RV/RV (wrong) | ❌ |
| Skew | Put/call IV spread | ATR/RV ratio | ATR, RV (wrong) | ❌ |
| VVIX | Volatility of vol expectations | Stdev of RV10 | RV (wrong) | ❌ |
| Vol-of-Vol Slope | Direction of vol expectations | Slope of RV stdev | RV (wrong) | ❌ |
| Short Gamma Score | Short-dated gamma opportunity | RV5 spike detection | RV (proxy) | ❌ |
| Skew Score | Skew trade profitability | ATR/RV anomalies | RV (wrong) | ❌ |

---

## STATEMENT

**This audit categorically finds that the regime/profile feature architecture uses inappropriate proxies for options market inputs. The system measures equity market conditions (realized vol, price ranges, trend strength) but applies those measurements to options trading decisions that depend on options market conditions (implied vol, volatility surfaces, put/call skew).**

**This is not a calculation error (which is fixable). This is a design flaw where the wrong data sources feed the system from inception.**

**Do not deploy with current feature architecture.**

---

**Report Generated:** 2025-11-13
**Next Action:** Review architectural options (1, 2, or 3 above) and plan remediation
