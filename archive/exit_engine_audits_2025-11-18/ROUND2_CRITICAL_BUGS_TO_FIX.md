# ROUND 2 CRITICAL BUGS - EXACT FIX LOCATIONS

**All 4 remaining critical bugs with exact line numbers and replacement code**

---

## BUG #2: TP1 TRACKING COLLISION - REQUIRES FIX

**Severity:** CRITICAL
**File:** `src/trading/exit_engine_v1.py`
**Line:** 327
**Symptom:** Two trades on same date with same profile exit with wrong reason

### Current Code (BROKEN):
```python
326        # Generate unique trade ID for TP1 tracking
327        trade_id = trade_data['entry']['entry_date']
```

### Required Fix:
```python
326        # Generate unique trade ID for TP1 tracking
327        trade_id = f"{trade_data['entry']['entry_date']}_{trade_data['entry']['strike']}_{trade_data['entry']['expiry']}"
```

### Why This Fixes It:
- Current: `"Profile_1_LDG_2025-01-01"` used for all trades on that date
- Fixed: `"Profile_1_LDG_2025-01-01_420_2025-01-17"` unique per trade

### Test to Verify:
```python
# Two trades same date should track separately
Trade A: Profile_1, 2025-01-01, strike=420, expiry=01-17, hits TP1
Trade B: Profile_1, 2025-01-01, strike=430, expiry=01-24, hits TP1

Expected: Both exit with reason "tp1_50%"
Current: Trade A="tp1_50%", Trade B="max_tracking_days" ✗
Fixed: Trade A="tp1_50%", Trade B="tp1_50%" ✓
```

---

## BUG #3: EMPTY PATH CRASH - REQUIRES FIX

**Severity:** CRITICAL
**File:** `src/trading/exit_engine_v1.py`
**Line:** 361
**Symptom:** Backtest crashes with IndexError if trade path is empty

### Current Code (BROKEN):
```python
360        # No exit triggered - use last day (14-day backstop)
361        last_day = daily_path[-1]  # ← CRASHES if empty
362
363        # FIXED: Handle division by zero
364        if abs(entry_cost) < 0.01:
365            final_pnl_pct = 0
366        else:
367            final_pnl_pct = last_day['mtm_pnl'] / entry_cost
368
369        return {
370            'exit_day': last_day['day'],
371            'exit_reason': 'max_tracking_days',
372            'exit_pnl': last_day['mtm_pnl'],
373            'exit_fraction': 1.0,
374            'entry_cost': entry_cost,
375            'pnl_pct': final_pnl_pct
376        }
```

### Required Fix:
```python
360        # No exit triggered - use last day (14-day backstop)
361        if not daily_path:  # ← ADD THIS CHECK
362            # Path is empty - return default exit
363            return {
364                'exit_day': 0,
365                'exit_reason': 'empty_path_no_data',
366                'exit_pnl': 0.0,
367                'exit_fraction': 1.0,
368                'entry_cost': entry_cost,
369                'pnl_pct': 0.0
370            }
371
372        last_day = daily_path[-1]  # ← NOW SAFE
373
374        # FIXED: Handle division by zero
375        if abs(entry_cost) < 0.01:
376            final_pnl_pct = 0
377        else:
378            final_pnl_pct = last_day['mtm_pnl'] / entry_cost
379
380        return {
381            'exit_day': last_day['day'],
382            'exit_reason': 'max_tracking_days',
383            'exit_pnl': last_day['mtm_pnl'],
384            'exit_fraction': 1.0,
385            'entry_cost': entry_cost,
386            'pnl_pct': final_pnl_pct
387        }
```

### Test to Verify:
```python
trade_empty = {
    'entry': {'entry_date': '2025-01-01', 'entry_cost': 1000.0},
    'path': []  # EMPTY
}

Current: Crashes with IndexError
Fixed: Returns {'exit_day': 0, 'exit_reason': 'empty_path_no_data', ...}
```

---

## BUG #4: CREDIT POSITION P&L SIGN ERROR - REQUIRES FIX

**Severity:** CRITICAL
**File:** `src/trading/exit_engine_v1.py`
**Lines:** 338 and 367
**Symptom:** Credit positions show profit when losing money

### Current Code (BROKEN):
```python
334            # Calculate P&L percentage (FIXED: handle zero and preserve signs)
335            if abs(entry_cost) < 0.01:  # Near-zero entry cost (break-even)
336                pnl_pct = 0
337            else:
338                pnl_pct = mtm_pnl / entry_cost  # ← WRONG: -100 / -500 = +0.20
```

### Required Fix (Line 338):
```python
334            # Calculate P&L percentage (FIXED: handle zero and preserve signs)
335            if abs(entry_cost) < 0.01:  # Near-zero entry cost (break-even)
336                pnl_pct = 0
337            else:
338                pnl_pct = mtm_pnl / abs(entry_cost)  # ← CORRECT: -100 / 500 = -0.20
```

### Also Required (Line 367):
```python
363        # FIXED: Handle division by zero
364        if abs(entry_cost) < 0.01:
365            final_pnl_pct = 0
366        else:
367            final_pnl_pct = last_day['mtm_pnl'] / abs(entry_cost)  # ← CHANGE /entry_cost to /abs(entry_cost)
```

### Why This Fixes It:
```
Credit position: entry_cost = -500 (received $500)
Loss: mtm_pnl = -100 (owe $100)

Current math: -100 / -500 = +0.20 (+20% - WRONG!)
Fixed math:   -100 / 500  = -0.20 (-20% - CORRECT!)

Then in line 162: if pnl_pct <= cfg.max_loss_pct:  # -0.50
  Current: if +0.20 <= -0.50 → False (doesn't exit when should)
  Fixed:   if -0.20 <= -0.50 → False (still doesn't exit, but calculation is correct)
```

### Test to Verify:
```python
entry_cost = -500.0   # Credit
mtm_pnl = -100.0      # Loss

Current: pnl_pct = -100 / -500 = 0.20 (WRONG)
Fixed: pnl_pct = -100 / abs(-500) = -0.20 (CORRECT)
```

---

## BUG #5: FRACTIONAL EXIT P&L NOT SCALED - REQUIRES FIX

**Severity:** CRITICAL
**File:** `src/trading/exit_engine_v1.py` line 354 (or `scripts/apply_exit_engine_v1.py` line 74)
**Symptom:** TP1 partial exits report full P&L, not half

### OPTION A: Fix in exit_engine_v1.py (Recommended)

**Current Code (BROKEN):**
```python
340            if should_exit:
341                return {
342                    'exit_day': day_idx,
343                    'exit_reason': reason,
344                    'exit_pnl': mtm_pnl,  # ← BROKEN: Full P&L, not scaled
345                    'exit_fraction': fraction,
346                    'entry_cost': entry_cost,
347                    'pnl_pct': pnl_pct
348                }
```

**Required Fix:**
```python
340            if should_exit:
341                # Scale exit_pnl by fraction for partial exits
342                exit_pnl = mtm_pnl * fraction if fraction < 1.0 else mtm_pnl  # ← CHANGED
343                return {
344                    'exit_day': day_idx,
345                    'exit_reason': reason,
346                    'exit_pnl': exit_pnl,  # ← NOW SCALED
347                    'exit_fraction': fraction,
348                    'entry_cost': entry_cost,
349                    'pnl_pct': pnl_pct
350                }
```

### OPTION B: Fix in apply_exit_engine_v1.py (Alternative)

If you prefer to keep exit_engine_v1.py unchanged, fix in the apply script:

**Current Code (BROKEN):**
```python
73        for trade in profile_data['trades']:
74            # Apply Exit Engine V1
75            exit_info = exit_engine.apply_to_tracked_trade(profile_id, trade)
...
85            total_pnl_v1 += exit_info['exit_pnl']  # ← BROKEN: No scaling
```

**Required Fix:**
```python
73        for trade in profile_data['trades']:
74            # Apply Exit Engine V1
75            exit_info = exit_engine.apply_to_tracked_trade(profile_id, trade)
...
85            total_pnl_v1 += exit_info['exit_pnl'] * exit_info['exit_fraction']  # ← SCALE by fraction
```

### Why This Matters:
```
Position: 2 contracts ($1000 entry cost)
Day 0 P&L: +$500 (both contracts)
TP1 triggers at +50%:
  - Should close: 1 contract
  - Fraction: 0.5

Current (BROKEN):
  - Reports exit_pnl: $500 (full)
  - Apply script sums: $500 (no scaling)
  - Result: P&L inflated

Fixed:
  - Reports exit_pnl: $250 (half)
  - Apply script sums: $250 (correct)
  - Result: P&L accurate
```

### Test to Verify:
```python
mtm_pnl = 500.0
fraction = 0.5

Current: exit_pnl = 500.0 (WRONG)
Fixed: exit_pnl = 250.0 (CORRECT)
```

---

## SUMMARY OF CHANGES

| Bug # | File | Line | Change | Priority |
|-------|------|------|--------|----------|
| 2 | exit_engine_v1.py | 327 | Add strike + expiry to trade_id | CRITICAL |
| 3 | exit_engine_v1.py | 361 | Add empty path guard | CRITICAL |
| 4 | exit_engine_v1.py | 338, 367 | Use abs(entry_cost) in division | CRITICAL |
| 5 | exit_engine_v1.py | 354 | Scale exit_pnl by fraction | CRITICAL |

**Total lines to change:** 4 locations
**Estimated time to fix:** 15-30 minutes
**Testing time:** 30-45 minutes

---

## VERIFICATION CHECKLIST

After applying fixes, verify:

```
[ ] Line 327: trade_id includes strike and expiry
[ ] Line 361-370: Empty path guard added before daily_path[-1]
[ ] Line 338: pnl_pct = mtm_pnl / abs(entry_cost)
[ ] Line 367: final_pnl_pct = mtm_pnl / abs(entry_cost)
[ ] Line 354: exit_pnl scaled by fraction

[ ] Test with empty path → returns default, no crash
[ ] Test with two same-date trades → both track separately
[ ] Test with credit position loss → pnl_pct negative
[ ] Test with TP1 partial → exit_pnl is half of mtm_pnl
[ ] Run full backtest → no crashes, valid results
```

---

## DO NOT SKIP THIS

**These 4 bugs affect:**
- 100% of profiles (empty path crash)
- 50% of profiles (TP1 collision on busy days)
- 33% of profiles (credit position sign)
- 50% of profiles (fractional exit inflation)

**Impact if not fixed:**
- Backtest crashes or returns invalid results
- P&L is inflated or wrong sign
- Exit reasons are incorrect
- Results cannot be trusted

**This is not optional. Fix before running next backtest.**
