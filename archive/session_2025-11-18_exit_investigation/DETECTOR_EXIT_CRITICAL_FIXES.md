# DETECTOR EXIT - CRITICAL BUG FIXES
**Concrete code patches to fix 3 CRITICAL bugs**

---

## FIX 1: Pre-compute Detector Scores (Fixes CRITICAL-001, 002, 003)

**THE RIGHT ARCHITECTURE**: Compute scores ONCE in regime classifier, not per-exit-check

### Patch 1A: Add detector scores to regime classification output

**File**: `src/regimes/classifier.py` or wherever regime classification happens

```python
# AFTER regime classification, BEFORE backtesting
from src.profiles.detectors import ProfileDetectors

# Compute detector scores on full DataFrame (has all context)
detector = ProfileDetectors()
df = detector.compute_all_profiles(df)

# Now df has columns: profile_1_LDG, profile_2_SDG, ..., profile_6_VOV
# These are pre-computed with full rolling window context
```

### Patch 1B: TradeTracker includes detector scores in market_conditions

**File**: `src/analysis/trade_tracker.py`
**Location**: Lines 329-357 `_capture_market_conditions()`

```python
def _capture_market_conditions(
    self,
    row: pd.Series,
    regime_data: Optional[pd.DataFrame],
    trade_date: date
) -> Dict:
    """Capture market conditions at a point in time"""

    conditions = {
        'close': float(row['close']),
    }

    # Add any derived features from row
    feature_cols = ['slope', 'RV5', 'RV10', 'RV20', 'ATR5', 'ATR10',
                   'MA20', 'MA50', 'slope_MA20', 'slope_MA50',
                   'return_5d', 'return_10d', 'return_20d',
                   'vix_close', 'high', 'low', 'return']  # ADDED

    for col in feature_cols:
        if col in row.index:
            val = row[col]
            conditions[col] = float(val) if pd.notna(val) else None

    # ADD: Include pre-computed detector scores
    detector_cols = ['profile_1_LDG', 'profile_2_SDG', 'profile_3_CHARM',
                     'profile_4_VANNA', 'profile_5_SKEW', 'profile_6_VOV']

    for col in detector_cols:
        if col in row.index:
            val = row[col]
            conditions[col] = float(val) if pd.notna(val) else None

    # Add regime if available
    if regime_data is not None:
        regime_row = regime_data[regime_data['date'] == trade_date]
        if len(regime_row) > 0:
            conditions['regime'] = int(regime_row.iloc[0]['regime'])

    return conditions
```

### Patch 1C: Exit Engine reads pre-computed scores (SIMPLIFY)

**File**: `src/trading/exit_engine_v1.py`
**Location**: Lines 308-349 `_calculate_detector_score()`

**REPLACE ENTIRE METHOD** with simple lookup:

```python
def _calculate_detector_score(self, profile_id: str, market: Dict) -> Optional[float]:
    """
    Get pre-computed detector score for a profile.

    Scores are computed upstream in regime classification with full
    DataFrame context (rolling windows, historical data).

    Args:
        profile_id: Profile identifier
        market: Market conditions dict with pre-computed scores

    Returns:
        Detector score in [0, 1], or None if not available
    """
    # Map profile_id to score column name
    score_col_map = {
        'Profile_1_LDG': 'profile_1_LDG',
        'Profile_2_SDG': 'profile_2_SDG',
        'Profile_3_CHARM': 'profile_3_CHARM',
        'Profile_4_VANNA': 'profile_4_VANNA',
        'Profile_5_SKEW': 'profile_5_SKEW',
        'Profile_6_VOV': 'profile_6_VOV'
    }

    score_col = score_col_map.get(profile_id)
    if not score_col:
        return None

    # Read pre-computed score from market conditions
    score = market.get(score_col)

    # Validate score is in [0, 1] range
    if score is not None:
        if not (0 <= score <= 1):
            import sys
            print(f"WARNING: Detector score {score} out of range [0,1] for {profile_id}", file=sys.stderr)
            return None

    return score
```

**BENEFIT**: Eliminates ALL 3 CRITICAL bugs:
- No feature mismatch (scores computed on full DataFrame upstream)
- No rolling window issues (context available during computation)
- Simple to debug (scores visible in market_conditions dict)

---

## FIX 2: Add Logging for Detector Failures (Visibility)

**File**: `src/trading/exit_engine_v1.py`
**Location**: Lines 186-198 (Profile 1), repeat for all 6 profiles

**BEFORE** (silent fallback):
```python
def _condition_exit_profile_1(self, market: Dict, greeks: Dict, days_held: int) -> bool:
    if days_held < 2:
        return False

    current_score = self._calculate_detector_score('Profile_1_LDG', market)

    if current_score is None:
        # No score available (missing data), fall back to simple logic
        slope_ma20 = market.get('slope_MA20')
        return slope_ma20 is not None and slope_ma20 <= 0

    if current_score < self.detector_exit_threshold:
        return True

    return False
```

**AFTER** (with logging):
```python
def _condition_exit_profile_1(self, market: Dict, greeks: Dict, days_held: int) -> bool:
    if days_held < 2:
        return False

    current_score = self._calculate_detector_score('Profile_1_LDG', market)

    if current_score is None:
        # Detector score unavailable - log if this is unexpected
        if days_held >= 90:  # After warmup period
            import sys
            print(f"WARNING: Profile_1_LDG detector score is None on day {days_held}. "
                  f"Data corruption or implementation bug.", file=sys.stderr)

        # Fall back to simple logic
        slope_ma20 = market.get('slope_MA20')
        fallback_exit = slope_ma20 is not None and slope_ma20 <= 0

        if fallback_exit:
            print(f"INFO: Profile_1_LDG using FALLBACK exit (slope check) on day {days_held}", file=sys.stderr)

        return fallback_exit

    # Normal detector-based exit
    if current_score < self.detector_exit_threshold:
        return True

    return False
```

**Apply same pattern to all 6 profiles**: Lines 200-218, 220-238, 240-262, 264-282, 284-302

---

## FIX 3: Add Detector Exit Tracking (Validation)

**File**: `src/trading/exit_engine_v1.py`
**Location**: Add after __init__ method

```python
def __init__(self):
    """Initialize Exit Engine V1 with profile configurations"""
    self.configs = self._get_profile_configs()
    self.tp1_hit = {}  # Track if TP1 already hit for each trade
    self.detector = ProfileDetectors()  # For calculating detector scores

    # Detector score exit thresholds (exit when score drops below)
    self.detector_exit_threshold = 0.30  # Exit when regime score < 0.3

    # ADD: Exit reason tracking for validation
    self.exit_reason_counts = {
        'max_loss': 0,
        'detector_exit': 0,
        'time_stop': 0,
        'detector_fallback': 0,
        'unknown': 0
    }

def should_exit(
    self,
    profile_id: str,
    trade_id: str,
    days_held: int,
    pnl_pct: float,
    market_conditions: Dict,
    position_greeks: Dict
) -> tuple[bool, float, str]:
    """..."""
    # ... existing logic ...

    # Before returning, track exit reason
    if should_exit:
        reason_category = self._categorize_exit_reason(reason)
        self.exit_reason_counts[reason_category] += 1

    return (should_exit, fraction, reason)

def _categorize_exit_reason(self, reason: str) -> str:
    """Map exit reason to category for tracking"""
    if 'max_loss' in reason:
        return 'max_loss'
    elif 'detector_exit' in reason:
        return 'detector_exit'
    elif 'time_stop' in reason or 'max_tracking_days' in reason:
        return 'time_stop'
    elif 'fallback' in reason:
        return 'detector_fallback'
    else:
        return 'unknown'

def print_exit_summary(self):
    """Print exit reason distribution (call at end of backtest)"""
    total = sum(self.exit_reason_counts.values())
    if total == 0:
        print("No exits tracked")
        return

    print("\n=== EXIT REASON DISTRIBUTION ===")
    for reason, count in sorted(self.exit_reason_counts.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        print(f"{reason:20s}: {count:4d} ({pct:5.1f}%)")
    print(f"{'TOTAL':20s}: {total:4d}")

    # Validation checks
    detector_pct = self.exit_reason_counts['detector_exit'] / total * 100
    if detector_pct < 5:
        print("\n⚠️  WARNING: Detector exits < 5% - implementation may be broken")
    elif detector_pct > 80:
        print("\n⚠️  WARNING: Detector exits > 80% - threshold may be too high")
    else:
        print(f"\n✅ Detector exits {detector_pct:.1f}% - within expected range")
```

**Usage in backtest**:
```python
exit_engine = ExitEngineV1()

# Run backtest...
for trade in trades:
    should_exit, fraction, reason = exit_engine.should_exit(...)
    # ...

# At end of backtest
exit_engine.print_exit_summary()
```

**VALIDATION**:
- If detector_exit < 5% → Implementation broken, scores not working
- If detector_exit 20-60% → Normal, detector logic working
- If detector_exit > 80% → Threshold too high, exits too aggressive

---

## TESTING PROTOCOL AFTER FIXES

### Step 1: Smoke Test (Verify detector scores present)
```python
# In backtest, add instrumentation
for i, trade in enumerate(trades[:10]):  # First 10 trades
    market = trade['daily_path'][5]  # Day 5
    score = market['market_conditions'].get('profile_1_LDG')
    print(f"Trade {i}, Day 5: Detector score = {score}")

# EXPECTED: Scores in [0, 1] range, NOT None
# If all None → Fix 1 didn't work, scores not being computed
```

### Step 2: Exit Reason Distribution
```python
exit_engine.print_exit_summary()

# EXPECTED:
# detector_exit: 25-50%
# max_loss: 5-15%
# time_stop: 40-60%

# If detector_exit = 0% → Implementation still broken
```

### Step 3: Threshold Optimization (After smoke test passes)
```python
for threshold in [0.20, 0.25, 0.30, 0.35, 0.40]:
    exit_engine.detector_exit_threshold = threshold
    results = run_backtest(...)
    print(f"Threshold {threshold}: Sharpe={results['sharpe']}, Capture%={results['capture_pct']}")

# Find threshold with best risk-adjusted returns
```

---

## SUMMARY

**3 Patches Fix All CRITICAL Bugs**:
1. Pre-compute detector scores upstream (eliminates data flow issues)
2. Add logging for failures (visibility into problems)
3. Track exit reason distribution (validation detector logic works)

**Estimated Implementation Time**: 2-3 hours
**Estimated Testing Time**: 1-2 hours
**Total**: 4-5 hours to deployment-ready

**After fixes, detector-based exits will work correctly and be testable.**
