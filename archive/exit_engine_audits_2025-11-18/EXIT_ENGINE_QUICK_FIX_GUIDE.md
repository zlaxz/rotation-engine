# EXIT ENGINE V1 - QUICK FIX GUIDE

**Priority**: ALL CRITICAL/HIGH bugs must be fixed before any backtest results are used.

---

## IMMEDIATE ACTIONS

### 1. FIX BUG-EXIT-001 (CRITICAL) - Idempotency

**File**: `/Users/zstoc/rotation-engine/src/trading/exit_engine_v1.py`

**Current code (Line 299-376)**:
```python
def apply_to_tracked_trade(self, profile_id: str, trade_data: Dict) -> Dict:
    entry_cost = trade_data['entry']['entry_cost']
    daily_path = trade_data['path']
    trade_id = trade_data['entry']['entry_date']

    for day in daily_path:
        # ... check exit logic
```

**Fix**: Add state reset at line 327 (after trade_id is set)
```python
def apply_to_tracked_trade(self, profile_id: str, trade_data: Dict) -> Dict:
    entry_cost = trade_data['entry']['entry_cost']
    daily_path = trade_data['path']
    trade_id = trade_data['entry']['entry_date']

    # FIX: Reset TP1 state for this trade to ensure idempotency
    tp1_key = f"{profile_id}_{trade_id}"
    if tp1_key in self.tp1_hit:
        del self.tp1_hit[tp1_key]

    for day in daily_path:
        # ... rest unchanged
```

**Verification**:
```python
# Run this test after fix
engine = ExitEngineV1()
result1 = engine.apply_to_tracked_trade('Profile_1_LDG', trade)
result2 = engine.apply_to_tracked_trade('Profile_1_LDG', trade)
assert result1 == result2, "Still broken!"
```

---

### 2. INVESTIGATE BUG-EXIT-002 (HIGH) - Short Sign Convention

**File**: `/Users/zstoc/rotation-engine/src/trading/trade.py` (where trades are created)

**Step 1**: Find where entry_cost and mtm_pnl are calculated for SHORT positions
- Look for negative entry_cost assignments
- Check how mtm_pnl is calculated (positive vs negative for profit)

**Step 2**: Create test case
```python
# Add to tests/test_exit_engine.py
def test_short_position_tp1():
    """Verify TP1 triggers correctly for short positions"""
    engine = ExitEngineV1()

    short_trade = {
        'entry': {'entry_date': '2025-01-01', 'entry_cost': -100.0},
        'path': [
            {'day': 0, 'mtm_pnl': -60.0, 'market_conditions': {}, 'greeks': {}}
        ]
    }

    result = engine.apply_to_tracked_trade('Profile_3_CHARM', short_trade)

    # Should exit on TP1, not time
    assert result['exit_reason'] == 'tp1_60%', f"Got {result['exit_reason']}"
    assert result['exit_fraction'] == 1.0  # Full exit for shorts
```

**Step 3**: If test fails, implement fix:
```python
# Option A: In apply_to_tracked_trade, before should_exit call:
if entry_cost < 0:
    # For shorts, check if mtm_pnl needs sign flip
    # Depends on TradeTracker convention - test to determine
    mtm_pnl_for_calc = day['mtm_pnl']  # or -day['mtm_pnl']
else:
    mtm_pnl_for_calc = day['mtm_pnl']

pnl_pct = mtm_pnl_for_calc / entry_cost
```

---

### 3. FIX BUG-APPLY-001 (HIGH) - Degradation Calculation

**File**: `/Users/zstoc/rotation-engine/scripts/apply_exit_engine_v1.py`

**Line 162** (per-profile degradation):
```python
# BEFORE:
degradation = (val_pnl - train_pnl) / abs(train_pnl) * 100

# AFTER:
if abs(train_pnl) < 0.01:
    degradation = 0
else:
    degradation = (val_pnl - train_pnl) / train_pnl * 100
```

**Line 168** (total degradation):
```python
# BEFORE:
total_deg = (val_total - train_total) / abs(train_total) * 100 if train_total != 0 else 0

# AFTER:
total_deg = (val_total - train_total) / train_total * 100 if train_total != 0 else 0
```

**Verification**:
```python
# Test with negative baseline
train_pnl = -1000
val_pnl = -500
degradation = (val_pnl - train_pnl) / train_pnl * 100
assert degradation == -50.0, f"Expected -50%, got {degradation}%"
```

---

### 4. FIX BUG-APPLY-002 (HIGH) - Improvement Calculation

**File**: `/Users/zstoc/rotation-engine/scripts/apply_exit_engine_v1.py`

**Line 83** (improvement percentage):
```python
# BEFORE:
improvement_pct = (improvement / abs(original_pnl) * 100)

# AFTER:
if abs(original_pnl) < 0.01:
    improvement_pct = 0
else:
    improvement_pct = (improvement / original_pnl) * 100
```

**Verification**:
```python
# Test with negative baseline that got worse
original_pnl = -1000
improvement = -200  # Lost more money
improvement_pct = improvement / original_pnl * 100
assert improvement_pct == 20.0, f"Expected 20%, got {improvement_pct}%"
# 20% means: original was -1000, got 20% worse (-1200 = -1000 * 1.2)
```

---

## VALIDATION CHECKLIST

After fixing, verify:

- [ ] **BUG-EXIT-001**: apply_to_tracked_trade() idempotency test passes
- [ ] **BUG-EXIT-002**: Short position test passes (or skip if TradeTracker sign is correct)
- [ ] **BUG-APPLY-001**: Negative baseline degradation shows negative %
- [ ] **BUG-APPLY-002**: Negative baseline improvement calculation correct
- [ ] All unit tests pass
- [ ] Backtest results rerun and compared (should be identical)
- [ ] Report metrics reviewed (degradation/improvement directions correct)

---

## TESTING TEMPLATE

```python
# Add to tests/test_exit_engine_v1.py

import unittest
from src.trading.exit_engine_v1 import ExitEngineV1

class TestExitEngineV1(unittest.TestCase):

    def setUp(self):
        self.engine = ExitEngineV1()

    def test_idempotency_bug_001(self):
        """BUG-EXIT-001: Same trade should produce same exit"""
        trade = {
            'entry': {'entry_date': '2025-01-01', 'entry_cost': 100.0},
            'path': [
                {'day': 0, 'mtm_pnl': 50.0, 'market_conditions': {}, 'greeks': {}}
            ]
        }

        result1 = self.engine.apply_to_tracked_trade('Profile_1_LDG', trade)
        result2 = self.engine.apply_to_tracked_trade('Profile_1_LDG', trade)

        self.assertEqual(result1['exit_reason'], result2['exit_reason'])
        self.assertEqual(result1['exit_fraction'], result2['exit_fraction'])
        self.assertEqual(result1['exit_pnl'], result2['exit_pnl'])

    def test_short_position_tp1_bug_002(self):
        """BUG-EXIT-002: TP1 should trigger on short positions"""
        short_trade = {
            'entry': {'entry_date': '2025-01-01', 'entry_cost': -100.0},
            'path': [
                {'day': 0, 'mtm_pnl': -60.0, 'market_conditions': {}, 'greeks': {}}
            ]
        }

        result = self.engine.apply_to_tracked_trade('Profile_3_CHARM', short_trade)

        # Should exit on TP1 (60% of premium collected)
        self.assertEqual(result['exit_reason'], 'tp1_60%')
        self.assertEqual(result['exit_fraction'], 1.0)

if __name__ == '__main__':
    unittest.main()
```

---

## EXPECTED BEHAVIOR AFTER FIX

### BUG-EXIT-001 (Idempotency)
```
Before: Same trade gives TP1 first time, max_tracking_days second time
After:  Same trade always gives TP1
```

### BUG-EXIT-002 (Short TP1)
```
Before: Short straddle with 60% profit doesn't exit on TP1
After:  Short straddle with 60% profit exits correctly on TP1
```

### BUG-APPLY-001 (Degradation)
```
Before: Val -500 vs Train -1000 shows +50% degradation
After:  Val -500 vs Train -1000 shows -50% degradation (improvement)
```

### BUG-APPLY-002 (Improvement)
```
Before: Exit Engine worse P&L shows ambiguous -20%
After:  Exit Engine worse P&L shows clear 20% worse
```

---

## CRITICAL: Invalidate Current Results

**After all fixes are applied**, ALL previous Exit Engine analysis results must be regenerated:

1. Delete old `exit_engine_v1_analysis.json`
2. Re-run `scripts/apply_exit_engine_v1.py`
3. Compare new results to old (should differ if bugs were real)
4. Update any reports or presentations that used old results

---

## Questions to Resolve First

Before implementing the fixes, answer these:

1. **TradeTracker Sign Convention**: How is mtm_pnl marked for SHORT positions?
   - Location: Check `src/trading/trade.py` or wherever trades calculated
   - Look for: How is mark-to-market value calculated for shorts?

2. **Short Position Profiles**: Which profiles are actually short?
   - Profile 3 (CHARM): Short straddle? YES
   - Profile 5 (SKEW): Short OTM puts? YES
   - Confirm these are definitely shorts, not synthetics

3. **Entry Cost Convention**: Is negative always short?
   - Verify across all profile definitions in _get_profile_configs()

---

## Rollback Plan

If fixes introduce new issues:

```bash
# Current version (broken):
git checkout HEAD src/trading/exit_engine_v1.py
git checkout HEAD scripts/apply_exit_engine_v1.py

# Then make minimal changes:
# 1. Fix idempotency first (most critical)
# 2. Test thoroughly
# 3. Add short position test
# 4. Only then fix APPLY script
```

---

## Timeline

- **Day 1**: Fix BUG-EXIT-001 (idempotency) + test
- **Day 2**: Investigate BUG-EXIT-002 (short sign), implement if confirmed
- **Day 3**: Fix BUG-APPLY-001 and BUG-APPLY-002 (calculation errors)
- **Day 4**: Regenerate all analysis, update reports
- **Day 5**: Validate total impact on strategy performance
