# EXIT ENGINE V1 - DETECTOR-BASED EXITS - RED TEAM AUDIT
**Date**: 2025-11-18
**Auditor**: Claude (Quantitative Trading Implementation Auditor)
**Target**: Pure detector-based exit logic (NO profit targets)
**Status**: CRITICAL BUGS FOUND - DO NOT DEPLOY

---

## EXECUTIVE SUMMARY

**CRITICAL FINDING**: The detector-based exit logic has a FATAL DATA MISMATCH that will cause 100% detector exit failures. The market_conditions dict passed from TradeTracker is INCOMPATIBLE with the features required by ProfileDetectors.

**SEVERITY BREAKDOWN**:
- **CRITICAL**: 3 bugs (breaks detector exits entirely)
- **HIGH**: 2 bugs (causes incorrect exit timing)
- **MEDIUM**: 3 bugs (edge cases, robustness issues)
- **LOW**: 2 bugs (code quality, maintainability)

**RECOMMENDATION**: DO NOT TEST until CRITICAL bugs fixed. All detector exits will fail silently and fall back to time backstop.

---

## CRITICAL BUGS (System-Breaking)

### CRITICAL-001: Feature Mismatch - market_conditions Missing Required Fields

**Location**: `exit_engine_v1.py` lines 324-349 `_calculate_detector_score()`

**Description**: TradeTracker._capture_market_conditions() (lines 329-357) populates market_conditions dict with LIMITED features. ProfileDetectors.compute_all_profiles() requires EXTENSIVE features that are NOT in market_conditions.

**Evidence**:

TradeTracker provides (trade_tracker.py:342-349):
```python
feature_cols = ['slope', 'RV5', 'RV10', 'RV20', 'ATR5', 'ATR10',
               'MA20', 'MA50', 'slope_MA20', 'slope_MA50',
               'return_5d', 'return_10d', 'return_20d']
```

ProfileDetectors REQUIRES (from detectors.py and features.py):
```python
REQUIRED = [
    'RV5', 'RV10', 'RV20',     # ✅ Present
    'ATR5',                     # ✅ Present
    'slope_MA20',               # ✅ Present
    'close',                    # ✅ Present
    'vix_close',                # ❌ MISSING - needed for IV proxies
    'high', 'low',              # ❌ MISSING - needed for range_10d calculation
    'return'                    # ❌ MISSING - needed for ret_1d calculation
]
```

**Impact**:
- ProfileFeatures.compute_all_features() will FAIL when computing IV proxies (no vix_close)
- ProfileFeatures._compute_helper_features() will FAIL (no 'return' for ret_1d)
- ProfileFeatures._compute_price_metrics() will FAIL (no 'high'/'low' for range_10d)
- ALL detector scores will return None
- ALL exits will fall back to time backstop (14 days)
- **Detector logic is 100% non-functional**

**Expected Behavior**: Detector score ~0.7 at entry, drops to ~0.3 triggers exit

**Actual Behavior**:
- market_conditions dict missing required fields
- pd.DataFrame([market]) creates df with incomplete features
- detector.compute_all_features() fails with KeyError or computes NaN
- _calculate_detector_score() catches exception, returns None
- Detector exit NEVER triggers (line 195, 216, etc.)
- Position held until day 14 time backstop

**Fix Required**:
1. TradeTracker._capture_market_conditions() must include: vix_close, high, low, return
2. OR: Exit engine must receive COMPLETE DataFrame row, not stripped dict
3. OR: Exit engine must handle incomplete features gracefully with fallback logic

**Severity**: CRITICAL - breaks entire detector-based exit system

---

### CRITICAL-002: NaN Detector Score Silently Ignored

**Location**: `exit_engine_v1.py` lines 186-198, 210-218, 230-238, etc.

**Description**: When detector score is None (due to CRITICAL-001 or missing data), code falls back to "simple logic" (slope check) or just returns False. This MASKS the data quality failure.

**Evidence**:
```python
# Profile 1 (lines 186-198)
current_score = self._calculate_detector_score('Profile_1_LDG', market)

if current_score is None:
    # No score available (missing data), fall back to simple logic
    slope_ma20 = market.get('slope_MA20')
    return slope_ma20 is not None and slope_ma20 <= 0
```

**Problem**:
- Detector score None is NORMAL during warmup (first 90 days)
- Detector score None AFTER warmup = DATA CORRUPTION or implementation bug
- Code treats both cases identically (silent fallback)
- No logging, no warning, no visibility

**Impact**:
- During backtest, ALL detector exits will fail (CRITICAL-001)
- Code will silently use fallback logic (slope_MA20 <= 0)
- User will think detector exits are working
- Results will be INVALID - testing wrong exit logic
- **Complete waste of backtest time - results meaningless**

**Expected Behavior**:
- During warmup: detector score None is OK, use fallback
- After warmup: detector score None = RAISE ERROR or LOG WARNING
- User must know detector exits are NOT working

**Actual Behavior**: Silent fallback in all cases, no visibility

**Fix Required**:
```python
current_score = self._calculate_detector_score('Profile_1_LDG', market)

if current_score is None:
    if days_held < 2:  # Still in warmup
        # Fallback OK during warmup
        slope_ma20 = market.get('slope_MA20')
        return slope_ma20 is not None and slope_ma20 <= 0
    else:
        # After warmup, None score = ERROR
        import sys
        print(f"WARNING: Detector score None for {profile_id} on day {days_held}. Feature mismatch or data corruption.", file=sys.stderr)
        # Use conservative fallback but LOG IT
        return False  # Don't exit on bad data
```

**Severity**: CRITICAL - hides system failures, produces invalid results

---

### CRITICAL-003: DataFrame Conversion Missing 'date' Column

**Location**: `exit_engine_v1.py` line 325

**Description**: ProfileDetectors.compute_all_features() expects DataFrame with 'date' column for rolling window calculations. market_conditions dict does NOT include 'date'.

**Evidence**:
```python
# Line 325
df_row = pd.DataFrame([market])
```

Creates DataFrame without 'date' column. But ProfileFeatures uses:
- `_rolling_percentile()` which needs chronological ordering
- `_compute_iv_ranks()` which uses .rolling()
- `_compute_vvix()` which uses .rolling()

**Impact**:
- Rolling window calculations will FAIL or produce garbage
- IV_rank_20, IV_rank_60 will be NaN or incorrect
- VVIX, VVIX_slope will be NaN or incorrect
- Detector scores will be NaN or wrong
- **Silently corrupts ALL detector calculations**

**Root Cause**: Detectors designed for BATCH processing (full DataFrame with date index), NOT single-row real-time scoring.

**Expected Behavior**: Detector computes score using HISTORICAL rolling windows

**Actual Behavior**: Single-row DataFrame has NO history, all rolling windows fail

**Fix Required**:
Option 1: Pass historical context
```python
def _calculate_detector_score(self, profile_id: str, market: Dict,
                                historical_data: pd.DataFrame) -> float:
    """
    Args:
        historical_data: Past 90 days of data for rolling window context
    """
    # Append current market conditions to historical data
    # Then compute detector score on LAST row
```

Option 2: Pre-compute detector scores in TradeTracker
```python
# In TradeTracker._capture_market_conditions()
if regime_data is not None and 'profile_1_LDG' in regime_data.columns:
    # Detector scores already computed on full DataFrame
    conditions['profile_1_LDG'] = float(regime_data.loc[trade_date, 'profile_1_LDG'])
```

**Severity**: CRITICAL - breaks detector calculations even if features present

---

## HIGH SEVERITY BUGS (Incorrect Logic)

### HIGH-001: Detector Threshold Too High (0.30 May Never Trigger)

**Location**: `exit_engine_v1.py` line 62

**Description**: Detector exit threshold set to 0.30. This assumes entry scores are 0.7+ and regime must fade to <0.3 to exit. No empirical validation of these values.

**Evidence**:
```python
self.detector_exit_threshold = 0.30  # Exit when regime score < 0.3
```

**Problem**:
- Entry threshold is typically 0.5-0.6 in allocation logic
- If entry at 0.55, regime only needs to drop to 0.45 to be "fading"
- Exit at 0.30 means we hold 15-20 percentile points PAST optimal exit
- Gives back profits unnecessarily

**Impact**:
- Exits occur TOO LATE (regime already faded)
- Worse capture percentage than optimal
- Reduces Sharpe ratio (holding losers longer)

**Expected Behavior**: Exit when score drops 20-30% from entry level

**Actual Behavior**: Exit when score drops to absolute 0.30 (may be 40-50% drop)

**Testing Required**:
- Backtest with thresholds: 0.20, 0.25, 0.30, 0.35, 0.40
- Measure capture percentage vs threshold
- Find optimal that maximizes Sharpe (likely 0.35-0.40)

**Fix Required**: Make threshold adaptive based on ENTRY score, or test empirically and set correctly

**Severity**: HIGH - causes suboptimal exits, reduces returns

---

### HIGH-002: days_held Guards Too Short (Prevents Quick Exits)

**Location**: Lines 182, 207, 227, 249, 271, 291

**Description**: All condition_exit functions have days_held < 1 or < 2 guards. This PREVENTS detector exits during optimal 1-3 day window for many profiles.

**Evidence**:
```python
# Profile 2 (SDG) - Short-dated gamma spike
if days_held < 1:  # Can't exit on day 0
    return False

# Profile 5 (SKEW) - Fear trades
if days_held < 1:  # Can't exit on day 0
    return False
```

**Problem**:
- Short-dated gamma (Profile 2) peaks at day 1-3 (KNOWN from prior analysis)
- Guard prevents exit until day 1+ (misses optimal exit on day 1)
- Skew trades (Profile 5) spike fast, fade fast - need day 0-1 exits
- 2-day guard on others (LDG, CHARM, VANNA, VOV) may miss early regime breaks

**Impact**:
- Forced to hold past optimal exit for fast-moving profiles
- Reduces capture percentage
- Increases drawdowns (holding past peak)

**Expected Behavior**: Allow detector to exit ANY time score drops (no arbitrary guards)

**Actual Behavior**: Forced minimum hold of 1-2 days regardless of detector signal

**Rationale for Guards**: Prevent "noise exits" on entry day due to execution slippage

**Counter-Argument**:
- If detector score ALREADY dropped below 0.3 on day 0, regime changed FAST
- This is VALID signal for fast-moving regimes (vol spike, fear)
- Guard defeats purpose of detector-based timing

**Fix Required**:
- Remove days_held guards for fast profiles (2_SDG, 5_SKEW)
- Reduce to days_held < 1 for others (allow day 1 exits)
- OR: Use detector score MOMENTUM (score dropped >30% in 1 day = exit regardless of days_held)

**Severity**: HIGH - prevents optimal exits, reduces edge

---

## MEDIUM SEVERITY BUGS (Edge Cases)

### MEDIUM-001: Detector Score Exactly 0.3 - Ambiguous Boundary

**Location**: Lines 195, 216, 235, 259, 279, 299

**Description**: Exit condition is `current_score < self.detector_exit_threshold` (strict inequality). Score exactly 0.3 does NOT trigger exit.

**Evidence**:
```python
if current_score < self.detector_exit_threshold:  # 0.299 exits, 0.300 holds
    return True
```

**Impact**:
- If score oscillates around 0.30, creates exit indecision
- Score 0.300 holds, next day 0.299 exits
- Minor issue but creates noise in edge cases

**Expected Behavior**: Clear boundary, no ambiguity

**Fix Required**: Use `<=` (less than or equal) for clear threshold semantics
```python
if current_score <= self.detector_exit_threshold:
```

**Severity**: MEDIUM - edge case, low probability but affects exit consistency

---

### MEDIUM-002: Exception Handling Swallows Errors Silently

**Location**: Lines 347-349

**Description**: `_calculate_detector_score()` catches ALL exceptions and returns None. No logging, no error tracking.

**Evidence**:
```python
except Exception as e:
    # If detector calculation fails, return None (skip detector exit)
    return None
```

**Problem**:
- Legitimate bugs (KeyError, AttributeError, TypeError) are HIDDEN
- No way to debug issues during development
- In production, detector failures are invisible

**Impact**:
- Debugging detector issues is IMPOSSIBLE (no error messages)
- Silent failures lead to incorrect backtest results
- Wastes time hunting bugs that were already caught but hidden

**Expected Behavior**: Log exception, return None with visibility

**Fix Required**:
```python
except Exception as e:
    import sys
    print(f"ERROR: Detector score calculation failed for {profile_id}: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    return None
```

**Severity**: MEDIUM - hinders debugging, masks implementation errors

---

### MEDIUM-003: Fallback Logic Inconsistent Across Profiles

**Location**: Lines 186-198 (Profile 1), 255-258 (Profile 4), vs 212-214, 232-234, etc.

**Description**: When detector score is None, different profiles use different fallback logic. Profile 1 and 4 check slope_MA20, others just return False.

**Evidence**:
```python
# Profile 1 (lines 188-191)
if current_score is None:
    slope_ma20 = market.get('slope_MA20')
    return slope_ma20 is not None and slope_ma20 <= 0

# Profile 2 (lines 212-214)
if current_score is None:
    return False  # No data, hold
```

**Problem**:
- Inconsistent behavior makes debugging harder
- Profile 1 may exit on slope break, Profile 2 holds to time stop
- No clear design rationale for difference

**Impact**:
- Profiles behave differently under data failures
- Results harder to interpret
- Code maintenance harder (6 different fallback implementations)

**Expected Behavior**: Consistent fallback logic across all profiles

**Fix Required**: Define ONE fallback strategy (e.g., always use slope_MA20 check, or always hold)

**Severity**: MEDIUM - code quality, maintainability issue

---

## LOW SEVERITY BUGS (Code Quality)

### LOW-001: Dead Code - TP1 Tracking Never Used

**Location**: Lines 58, 150-153

**Description**: TP1 tracking infrastructure exists but is NEVER used (no profit targets in new design).

**Evidence**:
```python
self.tp1_hit = {}  # Track if TP1 already hit for each trade

# In should_exit()
tp1_key = f"{profile_id}_{trade_id}"
if tp1_key not in self.tp1_hit:
    self.tp1_hit[tp1_key] = False
```

**Impact**:
- Clutters code with unused logic
- Confuses readers (why track TP1 if no TP1 exits?)
- Memory leak (tp1_hit dict grows but never cleared except reset_tp1_tracking())

**Fix Required**: Remove tp1_hit tracking entirely (no longer needed)

**Severity**: LOW - code quality, no functional impact

---

### LOW-002: Docstring Out of Date

**Location**: Lines 43-53

**Description**: Class docstring still mentions "profit targets" and "TP1/TP2" which were removed in detector-based design.

**Evidence**:
```python
"""
Intelligent exit engine using risk management, profit targets, and conditions.

Decision order:
1. Risk (max loss)
2. TP2 (full exit on big profit)
3. TP1 (partial exit on moderate profit)
4. Condition (regime/indicator based)
5. Time (max hold backstop)
"""
```

**Impact**:
- Misleading documentation
- Developers/auditors will be confused
- Out of sync with actual implementation (lines 157-168)

**Fix Required**: Update docstring to match current decision order (Risk → Detector → Time)

**Severity**: LOW - documentation only

---

## MANUAL VERIFICATION TESTS (Cannot Complete Until CRITICAL Bugs Fixed)

Due to CRITICAL-001, CRITICAL-002, CRITICAL-003, detector exits are NON-FUNCTIONAL. Manual verification would show:

**Test 1**: 10 Random Trades - Detector Score Calculation
- **EXPECTED**: Score ~0.7 at entry, drops to ~0.3 triggers exit
- **ACTUAL**: Score = None for all trades (feature mismatch)
- **STATUS**: FAIL - cannot verify until data flow fixed

**Test 2**: Greeks Accuracy (Not Applicable - Exit Engine Uses Detector Scores)
- **STATUS**: N/A - Greeks are tracked but not used for exit decisions

**Test 3**: Position Sizing (Not Applicable - Exit Engine Doesn't Size Positions)
- **STATUS**: N/A

**Test 4**: Entry/Exit Price Logic (Delegated to TradeTracker)
- **STATUS**: Already audited in prior rounds, PASS

**Test 5**: Transaction Costs (Delegated to TradeTracker)
- **STATUS**: Already audited in prior rounds, PASS

**Test 6**: Off-By-One - days_held Indexing
- **FINDING**: days_held starts at 0 (entry day), increments correctly
- **STATUS**: PASS - no off-by-one errors detected

**Test 7**: Detector Threshold Behavior
- **EXPECTED**: Exit when score < 0.30
- **ACTUAL**: CANNOT TEST - detector scores all None
- **STATUS**: BLOCKED by CRITICAL-001

---

## DEPLOYMENT DECISION

**STATUS**: ❌ **DO NOT DEPLOY - CRITICAL BUGS PRESENT**

**Blocking Issues**:
1. CRITICAL-001: Feature mismatch - detector exits 100% non-functional
2. CRITICAL-002: Silent failures - no visibility into detector failures
3. CRITICAL-003: DataFrame context missing - rolling windows broken

**Estimated Impact**:
- Running backtest NOW will produce INVALID results
- All "detector exits" will be fallback logic or time stops
- Comparing to prior Exit Engine V1 will be MEANINGLESS (different logic)
- **Complete waste of time until data flow fixed**

**Fix Sequence** (Priority Order):
1. Fix CRITICAL-001: Add required features to market_conditions dict
   - Add vix_close, high, low, return to TradeTracker._capture_market_conditions()
   - OR: Pass full DataFrame row to exit engine
   - OR: Pre-compute detector scores in TradeTracker, pass as feature

2. Fix CRITICAL-003: Provide historical context for rolling windows
   - Pass last 90 days of data to _calculate_detector_score()
   - OR: Pre-compute scores upstream, exit engine just reads them

3. Fix CRITICAL-002: Add logging for detector failures
   - Log when score is None after warmup period
   - Distinguish warmup (OK) from data failure (ERROR)

4. Fix HIGH-001: Test detector threshold empirically
   - After CRITICAL bugs fixed, backtest with thresholds 0.20-0.40
   - Find optimal that maximizes capture % and Sharpe

5. Fix HIGH-002: Remove or reduce days_held guards
   - Test with guards removed for fast profiles (2, 5)
   - Measure if early exits improve or hurt results

6. Fix MEDIUM/LOW issues: Code quality cleanup

**Estimated Fix Time**:
- CRITICAL fixes: 2-4 hours (data pipeline changes)
- HIGH fixes: 1-2 hours (threshold testing)
- MEDIUM/LOW: 30 minutes (cleanup)
- **TOTAL: 4-7 hours before ready for testing**

---

## RECOMMENDATIONS

### Immediate Actions (Before Any Testing)

1. **Fix data flow FIRST**
   - Decision: Pre-compute detector scores in regime classification step
   - Store scores in DataFrame alongside regime labels
   - TradeTracker includes scores in market_conditions dict
   - Exit engine reads pre-computed scores (no re-calculation needed)
   - **This eliminates CRITICAL-001, CRITICAL-002, CRITICAL-003 in one fix**

2. **Add detector score validation**
   - After fixing data flow, add assertion: detector score must be in [0, 1] or None
   - Log warning if score is None after day 90 (warmup complete)
   - Track detector exit frequency (should be 20-40% of exits, not 0%)

3. **Backtest with instrumentation**
   - Log every exit decision: reason, detector score, days_held, pnl_pct
   - Analyze distribution of exit reasons (risk/detector/time)
   - If detector exits < 5% = implementation still broken
   - If detector exits > 60% = threshold too high, exits too aggressive

### Testing Protocol (After CRITICAL Bugs Fixed)

1. **Smoke Test** (Train period 2020-2021, 50 trades)
   - Verify detector scores are NOT None
   - Verify detector exits actually trigger (not all time stops)
   - Check exit reason distribution

2. **Threshold Optimization** (Train period, full)
   - Test thresholds: [0.20, 0.25, 0.30, 0.35, 0.40]
   - Measure: Capture %, Sharpe, avg exit day, drawdown
   - Select optimal threshold

3. **Validation Test** (Validation period 2022-2023)
   - Use optimal threshold from step 2
   - Expect 20-40% degradation vs train
   - If degradation > 50% = overfitting, threshold too optimized

4. **Final Test** (Test period 2024) - ONCE ONLY
   - Use validated threshold
   - Accept results (no iteration)

### Architecture Recommendation

**BETTER DESIGN**: Pre-compute detector scores upstream, not in exit engine

```python
# In backtest loop (BEFORE trade tracking)
df = data_spine  # Has all OHLCV + features
df = regime_classifier.add_regimes(df)
df = profile_detector.compute_all_profiles(df)  # Add detector scores

# Now df has: date, close, RV5, ..., regime, profile_1_LDG, profile_2_SDG, ...

# In TradeTracker
conditions['profile_1_LDG'] = float(row['profile_1_LDG'])  # Just copy score

# In ExitEngine
current_score = market_conditions.get('profile_1_LDG')  # Just read it
```

**Benefits**:
- No feature mismatch (scores computed on full DataFrame)
- No rolling window issues (context available)
- No exception handling needed (scores pre-validated)
- Faster (compute once, use many times)
- Easier to debug (scores visible in DataFrame)

**This is the CORRECT architecture. Current design is backwards.**

---

## CONCLUSION

The detector-based exit logic has **sound conceptual design** (exit when regime fades) but **broken implementation** (data flow incompatibility).

**The core idea is RIGHT**: Using detector scores to time exits is more intelligent than fixed calendar days or profit targets. But the execution is WRONG: trying to recalculate detector scores from incomplete market_conditions dict will fail 100% of the time.

**Fix the data flow FIRST** (pre-compute scores upstream), then test threshold optimization. Do NOT test current implementation - it will waste time producing meaningless results.

**Estimated timeline to deployment-ready**:
- Fix CRITICAL bugs: 4 hours
- Test threshold optimization: 2 hours
- Validation testing: 1 hour
- **TOTAL: ~7 hours of work remaining**

After fixes, this WILL be superior to fixed-day exits. But testing it NOW is pointless.

---

**END OF RED TEAM AUDIT**
