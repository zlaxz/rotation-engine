# EXIT ENGINE V1 - DETAILED BUG REFERENCE

Quick lookup guide for all bugs with exact line numbers and fix code.

---

## BUG #1: CRITICAL - Condition Exit Defaults to True on Missing Data

**Files affected:**
- `src/trading/exit_engine_v1.py` lines 186-286

**All condition functions:**

### Profile 1 (LDG) - Lines 186-209
```python
# BROKEN CODE
def _condition_exit_profile_1(self, market: Dict, greeks: Dict) -> bool:
    # Line 196 - PROBLEM: Default 0 is indistinguishable from zero slope
    if market.get('slope_MA20', 0) <= 0:
        return True
    # ...
    return False
```

**Why it breaks:**
- When slope_MA20 is missing, `.get('slope_MA20', 0)` returns 0
- Condition `0 <= 0` is True
- Function returns True (exit) for missing data

**Fix for Profile 1:**
```python
def _condition_exit_profile_1(self, market: Dict, greeks: Dict) -> bool:
    """Profile 1 (LDG) - Long-Dated Gamma condition exit"""

    # Trend broken - BUT ONLY IF WE HAVE DATA
    slope = market.get('slope_MA20', None)  # CHANGED: No default
    if slope is not None and slope <= 0:  # CHANGED: Check None explicitly
        return True

    # Price below MA20
    close = market.get('close', None)  # CHANGED: No default
    ma20 = market.get('MA20', None)    # CHANGED: No default
    if close is not None and ma20 is not None and close > 0 and ma20 > 0:  # CHANGED: Check both
        if close < ma20:
            return True

    return False
```

### Profile 2 (SDG) - Lines 211-222
```python
# BROKEN CODE (but harmless - always returns False)
def _condition_exit_profile_2(self, market: Dict, greeks: Dict) -> bool:
    # All conditions are TODOs, returns False always
    return False  # Safe, but incomplete
```

### Profile 3 (CHARM) - Lines 224-235
```python
# BROKEN CODE (but harmless - always returns False)
def _condition_exit_profile_3(self, market: Dict, greeks: Dict) -> bool:
    # All conditions are TODOs, returns False always
    return False  # Safe, but incomplete
```

### Profile 4 (VANNA) - Lines 237-251
```python
# BROKEN CODE
def _condition_exit_profile_4(self, market: Dict, greeks: Dict) -> bool:
    # Line 247 - PROBLEM: Same as Profile 1
    if market.get('slope_MA20', 0) <= 0:
        return True
    return False
```

**Fix:**
```python
def _condition_exit_profile_4(self, market: Dict, greeks: Dict) -> bool:
    """Profile 4 (VANNA) - Vol-Spot Correlation condition exit"""

    # Trend weakening - ONLY IF WE HAVE DATA
    slope = market.get('slope_MA20', None)  # CHANGED
    if slope is not None and slope <= 0:    # CHANGED
        return True

    return False
```

### Profile 5 (SKEW) - Lines 253-264
```python
# BROKEN CODE (but harmless - always returns False)
def _condition_exit_profile_5(self, market: Dict, greeks: Dict) -> bool:
    # All conditions are TODOs, returns False always
    return False  # Safe, but incomplete
```

### Profile 6 (VOV) - Lines 266-286
```python
# PARTIALLY BROKEN CODE
def _condition_exit_profile_6(self, market: Dict, greeks: Dict) -> bool:
    # Line 279-283 - Uses RV10/RV20
    rv10 = market.get('RV10', 0)  # PROBLEM: Default 0
    rv20 = market.get('RV20', 0)  # PROBLEM: Default 0

    if rv10 > 0 and rv20 > 0 and rv10 >= rv20:
        return True
    return False
```

**Fix:**
```python
def _condition_exit_profile_6(self, market: Dict, greeks: Dict) -> bool:
    """Profile 6 (VOV) - Vol-of-Vol Convexity condition exit"""

    # Use RV10/RV20 as proxy for volatility compression state
    rv10 = market.get('RV10', None)   # CHANGED
    rv20 = market.get('RV20', None)   # CHANGED

    # Only check if we have both values
    if rv10 is not None and rv20 is not None:  # CHANGED
        if rv10 > 0 and rv20 > 0 and rv10 >= rv20:
            return True

    return False
```

---

## BUG #2: CRITICAL - TP1 Tracking Collision on Same-Day Trades

**File:** `src/trading/exit_engine_v1.py` lines 155-157, 322

**Problem code:**
```python
# Line 322 - BROKEN
trade_id = trade_data['entry']['entry_date']  # Only date - NOT UNIQUE!

# Line 155 - Uses non-unique trade_id
tp1_key = f"{profile_id}_{trade_id}"

# Line 156-157 - Tracking shared across trades with same profile+date
if tp1_key not in self.tp1_hit:
    self.tp1_hit[tp1_key] = False
```

**Example collision:**
```
Trade A: Profile_1_LDG, entry_date=2025-01-01, strike=420, expiry=2025-01-17
  tp1_key = "Profile_1_LDG_2025-01-01"

Trade B: Profile_1_LDG, entry_date=2025-01-01, strike=430, expiry=2025-01-24
  tp1_key = "Profile_1_LDG_2025-01-01"  # SAME KEY!

When Trade A hits TP1:
  tp1_hit["Profile_1_LDG_2025-01-01"] = True

When Trade B hits TP1:
  Checks: if not self.tp1_hit[tp1_key]  → False (already True from Trade A)
  Skips TP1 exit!
```

**Fix:**
```python
# Line 322 - FIXED
# Use combination of date, strike, expiry for uniqueness
trade_id = f"{trade_data['entry']['entry_date']}_{trade_data['entry']['strike']}_{trade_data['entry']['expiry']}"

# Alternatively (more robust):
# Require a unique trade_id from caller, or use trade hash
import hashlib
trade_dict_str = str(trade_data['entry'])
trade_id = hashlib.md5(trade_dict_str.encode()).hexdigest()[:8]
```

---

## BUG #3: CRITICAL - Empty Path Crashes

**File:** `src/trading/exit_engine_v1.py` lines 352-360

**Problem code:**
```python
# Line 352-360 - BROKEN
# No guard against empty path
last_day = daily_path[-1]  # ← IndexError if daily_path is empty!
return {
    'exit_day': last_day['day'],
    'exit_reason': 'max_tracking_days',
    'exit_pnl': last_day['mtm_pnl'],
    'exit_fraction': 1.0,
    'entry_cost': entry_cost,
    'pnl_pct': last_day['mtm_pnl'] / entry_cost if entry_cost > 0 else 0
}
```

**Crash scenario:**
```
TradeTracker.track_trade() returns:
  'path': []  # Empty if data unavailable

apply_to_tracked_trade() loops daily_path:
  for day in daily_path:  # Empty, no iterations
    # Never enters loop, reaches line 352

  last_day = daily_path[-1]  # IndexError!
```

**Fix:**
```python
# Line 352 - FIXED
if not daily_path:  # ADD THIS CHECK
    # Return default exit info when path is empty
    return {
        'exit_day': 0,
        'exit_reason': 'empty_path_no_data',
        'exit_pnl': 0.0,
        'exit_fraction': 1.0,
        'entry_cost': entry_cost,
        'pnl_pct': 0.0
    }

# Original fallback now safe
last_day = daily_path[-1]
return {
    'exit_day': last_day['day'],
    'exit_reason': 'max_tracking_days',
    'exit_pnl': last_day['mtm_pnl'],
    'exit_fraction': 1.0,
    'entry_cost': entry_cost,
    'pnl_pct': last_day['mtm_pnl'] / entry_cost if entry_cost > 0 else 0
}
```

---

## BUG #4: CRITICAL - Decision Order Violated

**File:** `src/trading/exit_engine_v1.py` lines 159-184

**Issue:** Due to Bug #1, condition exits trigger before TIME check.

**Problem code:**
```python
# Lines 159-184 - Decision order defined but violated
# The order SHOULD be:
# 1. Risk (line 162)
# 2. TP2 (line 166)
# 3. TP1 (line 170)
# 4. Condition (line 176) ← BUG: Triggers when should reach TIME
# 5. Time (line 180)

# Root cause: Condition always returns True due to Bug #1
```

**Example violation:**
```
Hold day 5 of max_hold=14:
  Risk: pnl=-10% vs max_loss=-50% → False, continue
  TP2: pnl=30% vs tp2=100% → False, continue
  TP1: pnl=25% vs tp1=50% → False, continue
  Condition: slope_MA20 missing → defaults 0 → returns True

Result: Exit day 5 with reason "condition_exit"
Expected: Hold to day 14 (TIME)
Impact: 9-day early exit
```

**Fix:** Fix Bug #1 (condition defaults). This automatically fixes decision order.

---

## BUG #5: HIGH - Negative Entry Cost Handling

**File:** `src/trading/exit_engine_v1.py` lines 318, 330

**Problem code:**
```python
# Line 318 - Removes sign information
entry_cost = abs(trade_data['entry']['entry_cost'])  # BROKEN

# Line 330 - Returns 0 for credit positions
pnl_pct = mtm_pnl / entry_cost if entry_cost > 0 else 0  # BROKEN
```

**Why it breaks:**
```python
# Credit position: entry_cost = -500 (received $500)
#
# Line 318: entry_cost = abs(-500) = 500  # Removes sign
# Line 330: 500 > 0 → True, calculates pnl_pct = mtm_pnl / 500
#
# This works mathematically, BUT...
#
# Direct approach would be:
# entry_cost = -500
# pnl_pct = mtm_pnl / entry_cost = mtm_pnl / -500
# If mtm_pnl = -100: pnl_pct = -100 / -500 = +20% (WRONG! Lost money)
#
# So abs() is necessary to get correct sign:
# pnl_pct = -100 / abs(-500) = -100 / 500 = -20% (Correct!)
```

But there's a deeper issue:

```python
# If entry_cost was NOT abs()'d:
entry_cost = -500

# Line 330 check:
if entry_cost > 0:  # -500 > 0 → False
    pnl_pct = mtm_pnl / entry_cost
else:
    pnl_pct = 0  # Returns 0 for ALL credit positions!
```

**Real-world consequence:**
```python
# Short straddle: entry_cost = -500 (collected credit)
# Day 0: mtm_pnl = -100 (lost $100)
#
# Current code:
# entry_cost = abs(-500) = 500  (OK mathematically)
# pnl_pct = -100 / 500 = -20%  (Correct)
#
# But what if someone looks at entry_cost for position direction?
# Can't tell if long or short anymore!

# Check line 162 (max loss comparison):
if pnl_pct <= cfg.max_loss_pct:  # Works correctly
    return (True, 1.0, f"max_loss_{cfg.max_loss_pct:.0%}")
```

Actually, after careful analysis, the abs() and the check work correctly. But it's confusing and fragile.

**Better fix:**
```python
# Line 318 - FIXED
entry_cost_raw = trade_data['entry']['entry_cost']
entry_cost_abs = abs(entry_cost_raw)  # For calculations

# Line 330 - FIXED (clearer)
pnl_pct = mtm_pnl / entry_cost_abs if entry_cost_abs > 0 else 0
```

Or even better, distinguish position direction:
```python
# Line 318 - FIXED
entry_cost = trade_data['entry']['entry_cost']  # Keep sign
is_debit = entry_cost > 0  # True if long (debit paid)

# Line 330 - FIXED
if entry_cost != 0:
    pnl_pct = mtm_pnl / abs(entry_cost)
else:
    pnl_pct = 0
```

---

## BUG #6: HIGH - Version Confusion

**Files affected:**
- `src/trading/exit_engine.py` (ExitEngine - Phase 1, simple)
- `src/trading/exit_engine_v1.py` (ExitEngineV1 - Phase 2, complex)
- `scripts/apply_exit_engine_v1.py` (imports ExitEngineV1, not ExitEngine)
- `docs/EXIT_STRATEGY_PHASE1_SPEC.md` (specs ExitEngine, not V1)

**Problem:**
```python
# Spec says (EXIT_STRATEGY_PHASE1_SPEC.md line 73):
from exit_engine import ExitEngine  # Phase 1 - simple fixed time

# But apply script does (scripts/apply_exit_engine_v1.py line 22):
from src.trading.exit_engine_v1 import ExitEngineV1  # Phase 2 - complex
```

**Which should be used?**

Option A: ExitEngine (spec says Phase 1 first)
```python
# src/trading/exit_engine.py
class ExitEngine:
    PROFILE_EXIT_DAYS = {
        'Profile_1_LDG': 7,
        'Profile_2_SDG': 5,
        'Profile_3_CHARM': 3,
        'Profile_4_VANNA': 8,
        'Profile_5_SKEW': 5,
        'Profile_6_VOV': 7
    }

    def should_exit(self, trade, current_date: date, profile: str) -> tuple[bool, str]:
        days_held = (current_date - trade.entry_date).days
        exit_day = self.PROFILE_EXIT_DAYS.get(profile, 14)
        if days_held >= exit_day:
            return (True, f"Phase1_Time_Day{exit_day}")
        return (False, "")
```

Option B: ExitEngineV1 (multi-factor, but broken)

**Recommendation:**
- If goal is Phase 1 baseline: Use ExitEngine, delete ExitEngineV1
- If goal is Phase 2: Fix ExitEngineV1 bugs first, update spec

**Fix:**
```python
# If using Phase 1 (recommended for baseline):
# scripts/apply_exit_engine_v1.py line 22
from src.trading.exit_engine import ExitEngine  # CHANGED

# And rename script:
# scripts/apply_exit_engine_phase1.py
```

---

## BUG #7: HIGH - Fractional Exit P&L Not Scaled

**Files affected:**
- `src/trading/exit_engine_v1.py` line 346
- `scripts/apply_exit_engine_v1.py` line 74

**Problem code:**
```python
# Line 346 in exit_engine_v1.py - BROKEN
return {
    'exit_pnl': mtm_pnl,  # Full P&L, not scaled by fraction!
    'exit_fraction': fraction,
}

# Line 74 in apply script - BROKEN
total_pnl_v1 += exit_info['exit_pnl']  # Doesn't use fraction
```

**Why it breaks:**
```python
# Position: 2 contracts
# Entry cost: $1000 total (2 × $500)
# Day 0 P&L: +$500 (both contracts)

# TP1 triggers with fraction=0.5:
# Expected: Close 1 contract, keep 1 contract
#   exit_pnl should be half of $500 = $250
#   remaining position = $250

# Current code:
# exit_pnl = $500 (full amount)  ← WRONG!
# Remaining = $500 (same as full)
# Total profit counted = $500 + $500 = $1000 ← DOUBLE COUNTED!
```

**Fix:**
```python
# Line 346 - FIXED
should_exit, fraction_to_close, reason = self.should_exit(...)

if should_exit:
    return {
        'exit_day': day_idx,
        'exit_reason': reason,
        'exit_pnl': mtm_pnl * fraction_to_close if fraction_to_close < 1.0 else mtm_pnl,  # CHANGED
        'exit_fraction': fraction_to_close,  # For reference
        'entry_cost': entry_cost,
        'pnl_pct': pnl_pct
    }
```

Or explicitly document that exit_pnl is full position P&L:
```python
# If exit_pnl is full position, apply script must scale:
# Line 74 - FIXED
total_pnl_v1 += exit_info['exit_pnl'] * exit_info['exit_fraction']
```

---

## BUG #8: MEDIUM - TP1 Only for Positive Entry Cost

**File:** `src/trading/exit_engine_v1.py` line 330

**Problem code:**
```python
# Line 330
pnl_pct = mtm_pnl / entry_cost if entry_cost > 0 else 0

# Line 170 - TP1 check
if cfg.tp1_pct is not None and pnl_pct >= cfg.tp1_pct:
    # TP1 never triggers if pnl_pct=0
    if not self.tp1_hit[tp1_key]:
        return (True, cfg.tp1_fraction, f"tp1_{cfg.tp1_pct:.0%}")
```

**Why it breaks:**
```python
# Credit position: entry_cost = -500
# After fix to line 330:
if entry_cost > 0:  # -500 > 0 → False
    pnl_pct = mtm_pnl / entry_cost
else:
    pnl_pct = 0  # Returns 0 for ALL credit positions

# TP1 check at line 170:
if 0 >= cfg.tp1_pct:  # 0 >= 0.50 → False
    # Never triggers!
```

**Root cause:** Bug #5 - Credit positions return pnl_pct=0

**Fix:** See Bug #5 fix.

---

## BUG #9: MEDIUM - Incomplete Condition Implementations

**File:** `src/trading/exit_engine_v1.py` lines 211-286

**Problem code:**

Profile 2 (lines 211-222):
```python
def _condition_exit_profile_2(self, market: Dict, greeks: Dict) -> bool:
    """Profile 2 (SDG) - Short-Dated Gamma Spike condition exit

    Exit if:
    - Fear fading (VVIX_slope < 0) - NOT TRACKED YET
    - Spike receding (move_size < 1.0) - NOT TRACKED YET
    - RV spike failed (RV5/IV7 <= 0.80) - NOT TRACKED YET
    """
    # TODO: Add VVIX, move_size, IV7 tracking
    # For now, rely on time/profit targets only
    return False  # STUB
```

Profile 3 (lines 224-235):
```python
def _condition_exit_profile_3(self, market: Dict, greeks: Dict) -> bool:
    """Profile 3 (CHARM) - Theta/Decay condition exit

    Exit if:
    - Pin broken (range_10d > 0.04) - NOT TRACKED YET
    - Vol-of-vol rising (VVIX_slope > 0) - NOT TRACKED YET
    - Rich vol edge gone (IV20/RV10 < 1.20) - NOT TRACKED YET
    """
    # TODO: Add range_10d, VVIX, IV20 tracking
    # For now, rely on profit targets
    return False  # STUB
```

And similar for Profiles 5 and 6.

**Why it matters:**
- Condition exits are disabled (return False)
- Positions exit via time or profit targets only
- Condition logic has no effect

**Fix:**
Either implement full conditions or document as Phase 2 (not available yet).

---

## TESTING CHECKLIST

Use this to verify all bugs are fixed:

```
[ ] Bug #1: Test with missing slope_MA20 - should NOT exit
[ ] Bug #1: Test with missing RV10/RV20 - should NOT exit
[ ] Bug #2: Test two trades same profile/date - track separately
[ ] Bug #3: Test with empty path - returns default, no crash
[ ] Bug #4: Test decision order - verify risk > TP2 > TP1 > condition > time
[ ] Bug #5: Test credit position - pnl_pct calculated correctly
[ ] Bug #6: Clarify which engine to use
[ ] Bug #7: Test TP1 partial exit - exit_pnl is fraction of total
[ ] Bug #8: Test credit position TP1 - triggers when should
[ ] Bug #9: Document which conditions are active vs stubbed
```

---

## REFERENCE

- **Specification:** `docs/EXIT_STRATEGY_PHASE1_SPEC.md`
- **Implementation:** `src/trading/exit_engine_v1.py`
- **Application:** `scripts/apply_exit_engine_v1.py`
- **Audit Report:** `EXIT_ENGINE_V1_AUDIT_REPORT.md`

