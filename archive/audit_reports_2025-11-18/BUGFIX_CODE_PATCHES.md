# EXIT ENGINE V1 - BUGFIX CODE PATCHES

**Three critical bugs. Three simple fixes. 20 lines of code changes.**

---

## FIX #1: Profile_1_LDG Early Exit Bug

**File:** `src/trading/exit_engine_v1.py`
**Lines:** 186-210
**Function:** `_condition_exit_profile_1()`

### BEFORE (BUGGY):

```python
def _condition_exit_profile_1(self, market: Dict, greeks: Dict) -> bool:
    """
    Profile 1 (LDG) - Long-Dated Gamma condition exit

    Exit if:
    - Trend broken (slope_MA20 <= 0)
    - Price under MA20 (close < MA20)
    - Cheap vol thesis invalid (RV10/IV60 < 0.90)
    """
    # FIXED: Validate data exists and is not None
    slope_ma20 = market.get('slope_MA20')
    if slope_ma20 is not None and slope_ma20 <= 0:
        return True  # ← BUG: Exits Day 1 if trend breaks

    # Price below MA20
    close = market.get('close')
    ma20 = market.get('MA20')
    if close is not None and ma20 is not None and close > 0 and ma20 > 0 and close < ma20:
        return True

    # Cheap vol thesis broken (would need IV60 - not currently tracked)
    # For now, skip this condition
    # TODO: Add IV tracking to market_conditions

    return False
```

### AFTER (FIXED):

```python
def _condition_exit_profile_1(self, market: Dict, greeks: Dict, days_held: int) -> bool:
    """
    Profile 1 (LDG) - Long-Dated Gamma condition exit

    Exit if:
    - Days held >= 3 (let gamma develop first)
    - Trend broken (slope_MA20 <= 0)
    - Price under MA20 (close < MA20)
    - Cheap vol thesis invalid (RV10/IV60 < 0.90)
    """
    # FIXED: Don't exit on trend break if trade hasn't developed yet
    # Long-dated gamma edge needs 3+ days to materialize
    # Trend breaks on Day 1 are often noise
    if days_held < 3:
        return False

    # Trend broken
    slope_ma20 = market.get('slope_MA20')
    if slope_ma20 is not None and slope_ma20 <= 0:
        return True

    # Price below MA20
    close = market.get('close')
    ma20 = market.get('MA20')
    if close is not None and ma20 is not None and close > 0 and ma20 > 0 and close < ma20:
        return True

    # Cheap vol thesis broken (would need IV60 - not currently tracked)
    # For now, skip this condition
    # TODO: Add IV tracking to market_conditions

    return False
```

**Changes:**
1. Add `days_held: int` parameter to function signature (line 186)
2. Add guard check at top (lines 194-197)

---

## FIX #2: Profile_4_VANNA Early Exit Bug

**File:** `src/trading/exit_engine_v1.py`
**Lines:** 238-253
**Function:** `_condition_exit_profile_4()`

### BEFORE (BUGGY):

```python
def _condition_exit_profile_4(self, market: Dict, greeks: Dict) -> bool:
    """
    Profile 4 (VANNA) - Vol-Spot Correlation condition exit

    Exit if:
    - Trend weakening (slope_MA20 <= 0)
    - Vol no longer cheap (IV_rank_20 > 0.70) - NOT TRACKED YET
    - Vol-of-vol instability (VVIX_slope > 0) - NOT TRACKED YET
    """
    # FIXED: Validate data exists
    slope_ma20 = market.get('slope_MA20')
    if slope_ma20 is not None and slope_ma20 <= 0:
        return True  # ← BUG: Exits Day 1 if trend breaks

    # TODO: Add IV_rank_20, VVIX tracking
    return False
```

### AFTER (FIXED):

```python
def _condition_exit_profile_4(self, market: Dict, greeks: Dict, days_held: int) -> bool:
    """
    Profile 4 (VANNA) - Vol-Spot Correlation condition exit

    Exit if:
    - Days held >= 3 (let vanna edge develop first)
    - Trend weakening (slope_MA20 <= 0)
    - Vol no longer cheap (IV_rank_20 > 0.70) - NOT TRACKED YET
    - Vol-of-vol instability (VVIX_slope > 0) - NOT TRACKED YET
    """
    # FIXED: Don't exit on trend break if trade hasn't developed yet
    # Vanna edge needs 3+ days to materialize
    # Trend breaks on Day 1 are often noise
    if days_held < 3:
        return False

    # Trend weakening
    slope_ma20 = market.get('slope_MA20')
    if slope_ma20 is not None and slope_ma20 <= 0:
        return True

    # TODO: Add IV_rank_20, VVIX tracking
    return False
```

**Changes:**
1. Add `days_held: int` parameter to function signature (line 238)
2. Add guard check at top (lines 247-250)

---

## FIX #3: Profile_6_VOV Early Exit Bug

**File:** `src/trading/exit_engine_v1.py`
**Lines:** 268-289
**Function:** `_condition_exit_profile_6()`

### BEFORE (BUGGY):

```python
def _condition_exit_profile_6(self, market: Dict, greeks: Dict) -> bool:
    """
    Profile 6 (VOV) - Vol-of-Vol Convexity condition exit

    Exit if:
    - VVIX not elevated (VVIX/VVIX_80pct <= 1.0) - NOT TRACKED YET
    - Vol-of-vol stopped rising (VVIX_slope <= 0) - NOT TRACKED YET
    - Compression resolved (RV10/IV20 >= 1.0) - NOT TRACKED YET
    """
    # TODO: Add VVIX tracking
    # For now, rely on RV ratios we DO track

    # Use RV10/RV20 as proxy for volatility compression state
    # FIXED: Validate data exists
    rv10 = market.get('RV10')
    rv20 = market.get('RV20')

    # If RV normalized (RV10 >= RV20), compression resolved
    if rv10 is not None and rv20 is not None and rv10 > 0 and rv20 > 0 and rv10 >= rv20:
        return True  # ← BUG: Exits Day 1 if RV normalizes

    return False
```

### AFTER (FIXED):

```python
def _condition_exit_profile_6(self, market: Dict, greeks: Dict, days_held: int) -> bool:
    """
    Profile 6 (VOV) - Vol-of-Vol Convexity condition exit

    Exit if:
    - Days held >= 5 (let compression develop first)
    - VVIX not elevated (VVIX/VVIX_80pct <= 1.0) - NOT TRACKED YET
    - Vol-of-vol stopped rising (VVIX_slope <= 0) - NOT TRACKED YET
    - Compression resolved (RV10/IV20 >= 1.0)
    """
    # FIXED: Don't exit on RV normalization if trade hasn't developed yet
    # RV ratios are very noisy on Day 1-2
    # Vol-of-vol compression edge needs 5+ days to materialize
    if days_held < 5:
        return False

    # TODO: Add VVIX tracking
    # For now, rely on RV ratios we DO track

    # Use RV10/RV20 as proxy for volatility compression state
    rv10 = market.get('RV10')
    rv20 = market.get('RV20')

    # If RV normalized (RV10 >= RV20) after 5+ days, compression resolved
    if rv10 is not None and rv20 is not None and rv10 > 0 and rv20 > 0 and rv10 >= rv20:
        return True

    return False
```

**Changes:**
1. Add `days_held: int` parameter to function signature (line 268)
2. Add guard check at top (lines 278-281)

---

## MASTER FIX #4: Update Function Signatures (2 locations)

### Location 1: ExitConfig dataclass signature (line 40)

**BEFORE:**
```python
condition_exit_fn: Callable[[Dict], bool]  # Function that checks market conditions
```

**AFTER:**
```python
condition_exit_fn: Callable[[Dict, Dict, int], bool]  # market, greeks, days_held
```

### Location 2: Calling the condition function (line 176)

**BEFORE:**
```python
# 4. CONDITION: Profile-specific exit conditions
if cfg.condition_exit_fn(market_conditions, position_greeks):
    return (True, 1.0, "condition_exit")
```

**AFTER:**
```python
# 4. CONDITION: Profile-specific exit conditions
if cfg.condition_exit_fn(market_conditions, position_greeks, days_held):
    return (True, 1.0, "condition_exit")
```

---

## ALL CONDITION FUNCTIONS - Parameter Updates

Update all 6 condition function signatures:

```python
# ALL need: (self, market: Dict, greeks: Dict, days_held: int) -> bool

def _condition_exit_profile_1(self, market: Dict, greeks: Dict, days_held: int) -> bool:
def _condition_exit_profile_2(self, market: Dict, greeks: Dict, days_held: int) -> bool:
def _condition_exit_profile_3(self, market: Dict, greeks: Dict, days_held: int) -> bool:
def _condition_exit_profile_4(self, market: Dict, greeks: Dict, days_held: int) -> bool:
def _condition_exit_profile_5(self, market: Dict, greeks: Dict, days_held: int) -> bool:
def _condition_exit_profile_6(self, market: Dict, greeks: Dict, days_held: int) -> bool:
```

---

## SUMMARY OF CHANGES

| File | Lines | Change | Impact |
|------|-------|--------|--------|
| exit_engine_v1.py | 40 | Update ExitConfig signature | All profiles |
| exit_engine_v1.py | 176 | Pass days_held to condition_exit_fn | All profiles |
| exit_engine_v1.py | 186 | Add days_held param to Profile_1 | Fix BUG-001 |
| exit_engine_v1.py | 194-197 | Add days_held < 3 guard to Profile_1 | Fix BUG-001 |
| exit_engine_v1.py | 212 | Add days_held param to Profile_2 | Consistency (no changes needed) |
| exit_engine_v1.py | 225 | Add days_held param to Profile_3 | Consistency (no changes needed) |
| exit_engine_v1.py | 238 | Add days_held param to Profile_4 | Fix BUG-002 |
| exit_engine_v1.py | 247-250 | Add days_held < 3 guard to Profile_4 | Fix BUG-002 |
| exit_engine_v1.py | 255 | Add days_held param to Profile_5 | Consistency (no changes needed) |
| exit_engine_v1.py | 268 | Add days_held param to Profile_6 | Fix BUG-003 |
| exit_engine_v1.py | 278-281 | Add days_held < 5 guard to Profile_6 | Fix BUG-003 |

**Total changes:** ~20 lines
**Time to implement:** 15-30 minutes
**Testing:** Re-run apply_exit_engine_v1.py and verify capture rate improves

---

## VERIFICATION SCRIPT

After applying fixes, run this to verify improvements:

```python
# Quick test
python3 << 'EOF'
from src.trading.exit_engine_v1 import ExitEngineV1

engine = ExitEngineV1()

# Test Profile_1 with Day 1 trend break
market = {'slope_MA20': -0.1}
greeks = {}

# Before fix: would return True (exit)
# After fix: should return False (wait for Day 3)
for days_held in [1, 2, 3, 4]:
    should_exit = engine.configs['Profile_1_LDG'].condition_exit_fn(market, greeks, days_held)
    print(f"Profile_1 Day {days_held} with trend break: {should_exit}")
    # Expected: False, False, True, True
EOF
```

---

## EXPECTED IMPACT

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Capture rate | 0.3% | 5-15% | 10-50x improvement |
| Profile_1 P&L | -$2,863 | TBD | Should improve |
| Profile_4 P&L | +$13,507 | +$50k-100k | Should improve significantly |
| Profile_6 P&L | -$5,077 | TBD | Should improve |

---

## DEPLOYMENT CHECKLIST

- [ ] Apply all 3 fixes to src/trading/exit_engine_v1.py
- [ ] Run verification script above
- [ ] Re-run `python scripts/apply_exit_engine_v1.py`
- [ ] Check capture rate improves to 5%+
- [ ] Run full backtest on train period
- [ ] Run validation on validation period
- [ ] Re-audit with AGGRESSIVE_AUDIT_EXIT_ENGINE_V1_FINAL.md
- [ ] Document results
- [ ] Proceed to live trading testing (if validation passes)

