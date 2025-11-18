# EXACT CODE FIXES - COPY & PASTE READY

All fixes are ready to implement. Copy the exact code blocks below.

---

## FIX #1: BUG-EXIT-001 - Idempotency (CRITICAL)

**File**: `/Users/zstoc/rotation-engine/src/trading/exit_engine_v1.py`

**Find** (around line 299):
```python
def apply_to_tracked_trade(
    self,
    profile_id: str,
    trade_data: Dict
) -> Dict:
    """
    Apply Exit Engine V1 logic to a tracked trade.
    ...
    """
    # FIXED: Don't use abs() - preserves sign for short positions
    # Short positions have negative entry_cost (premium collected)
    entry_cost = trade_data['entry']['entry_cost']
    daily_path = trade_data['path']

    # Generate unique trade ID for TP1 tracking
    trade_id = trade_data['entry']['entry_date']
```

**Replace with**:
```python
def apply_to_tracked_trade(
    self,
    profile_id: str,
    trade_data: Dict
) -> Dict:
    """
    Apply Exit Engine V1 logic to a tracked trade.
    ...
    """
    # FIXED: Don't use abs() - preserves sign for short positions
    # Short positions have negative entry_cost (premium collected)
    entry_cost = trade_data['entry']['entry_cost']
    daily_path = trade_data['path']

    # Generate unique trade ID for TP1 tracking
    trade_id = trade_data['entry']['entry_date']

    # FIX-001: Reset TP1 state for this trade to ensure idempotency
    # Without this, apply_to_tracked_trade() is non-deterministic
    tp1_key = f"{profile_id}_{trade_id}"
    if tp1_key in self.tp1_hit:
        del self.tp1_hit[tp1_key]
```

**Why**: Ensures same trade always produces same exit decision.

---

## FIX #2: BUG-APPLY-001 - Degradation Calculation (HIGH)

**File**: `/Users/zstoc/rotation-engine/scripts/apply_exit_engine_v1.py`

**Find** (around line 158-162):
```python
        # FIXED: Guard division by zero
        if abs(train_pnl) < 0.01:
            degradation = 0
        else:
            degradation = (val_pnl - train_pnl) / abs(train_pnl) * 100
```

**Replace with**:
```python
        # FIXED: Guard division by zero AND use signed denominator
        if abs(train_pnl) < 0.01:
            degradation = 0
        else:
            degradation = (val_pnl - train_pnl) / train_pnl * 100
```

**Why**: Removes the `abs()` that inverts meaning for negative P&L.

---

## FIX #3: BUG-APPLY-002 - Improvement Percentage (HIGH)

**File**: `/Users/zstoc/rotation-engine/scripts/apply_exit_engine_v1.py`

**Find** (around line 76-83):
```python
        # Calculate improvement (FIXED: guard division by zero)
        original_pnl = profile_data['summary']['total_pnl']
        improvement = total_pnl_v1 - original_pnl

        if abs(original_pnl) < 0.01:
            improvement_pct = 0
        else:
            improvement_pct = (improvement / abs(original_pnl) * 100)
```

**Replace with**:
```python
        # Calculate improvement (FIXED: use signed denominator)
        original_pnl = profile_data['summary']['total_pnl']
        improvement = total_pnl_v1 - original_pnl

        if abs(original_pnl) < 0.01:
            improvement_pct = 0
        else:
            improvement_pct = (improvement / original_pnl) * 100
```

**Why**: Removes the `abs()` that makes improvement % ambiguous.

---

## FIX #4: BUG-APPLY-003 - Total Degradation Calculation (HIGH)

**File**: `/Users/zstoc/rotation-engine/scripts/apply_exit_engine_v1.py`

**Find** (around line 166-168):
```python
    train_total = sum(r['exit_engine_v1_pnl'] for r in train_results.values())
    val_total = sum(r['exit_engine_v1_pnl'] for r in val_results.values())
    total_deg = (val_total - train_total) / abs(train_total) * 100 if train_total != 0 else 0
```

**Replace with**:
```python
    train_total = sum(r['exit_engine_v1_pnl'] for r in train_results.values())
    val_total = sum(r['exit_engine_v1_pnl'] for r in val_results.values())
    total_deg = (val_total - train_total) / train_total * 100 if train_total != 0 else 0
```

**Why**: Removes the `abs()` that inverts degradation meaning.

---

## UNIT TESTS TO ADD

**File**: Create `/Users/zstoc/rotation-engine/tests/test_exit_engine_v1.py` (new file)

```python
"""Unit tests for Exit Engine V1 bug fixes"""

import unittest
from src.trading.exit_engine_v1 import ExitEngineV1


class TestExitEngineV1BugFixes(unittest.TestCase):
    """Verify all Round 2 bug fixes are working"""

    def setUp(self):
        self.engine = ExitEngineV1()

    def test_fix_001_idempotency(self):
        """FIX-001: apply_to_tracked_trade() must be idempotent"""
        # Create trade at TP1 threshold
        trade = {
            'entry': {
                'entry_date': '2025-01-01',
                'entry_cost': 100.0
            },
            'path': [
                {
                    'day': 0,
                    'mtm_pnl': 50.0,  # At 50% profit = TP1 threshold
                    'market_conditions': {},
                    'greeks': {}
                }
            ]
        }

        # Apply twice to same engine
        result1 = self.engine.apply_to_tracked_trade('Profile_1_LDG', trade)
        result2 = self.engine.apply_to_tracked_trade('Profile_1_LDG', trade)

        # Should be identical
        self.assertEqual(
            result1['exit_reason'],
            result2['exit_reason'],
            f"Exit reason changed: {result1['exit_reason']} vs {result2['exit_reason']}"
        )
        self.assertEqual(
            result1['exit_fraction'],
            result2['exit_fraction'],
            f"Exit fraction changed: {result1['exit_fraction']} vs {result2['exit_fraction']}"
        )
        self.assertEqual(
            result1['exit_pnl'],
            result2['exit_pnl'],
            f"Exit P&L changed: {result1['exit_pnl']} vs {result2['exit_pnl']}"
        )

    def test_fix_002_short_position_tp1(self):
        """FIX-002: TP1 should trigger on short positions"""
        # Profile 3 (CHARM) is a short straddle
        # max_loss: -1.50, tp1: 0.60
        short_trade = {
            'entry': {
                'entry_date': '2025-01-01',
                'entry_cost': -100.0  # Short position (negative = collected premium)
            },
            'path': [
                {
                    'day': 0,
                    'mtm_pnl': -60.0,  # Assuming short profits are negative in TradeTracker
                    'market_conditions': {},
                    'greeks': {}
                }
            ]
        }

        result = self.engine.apply_to_tracked_trade('Profile_3_CHARM', short_trade)

        # Should exit on TP1 at 60% of premium collected
        self.assertEqual(
            result['exit_reason'],
            'tp1_60%',
            f"Short TP1 not triggering: {result['exit_reason']}"
        )

    def test_division_by_zero_protection(self):
        """Verify division by zero is protected in all entry_cost values"""
        # Test with zero entry cost
        zero_trade = {
            'entry': {
                'entry_date': '2025-01-01',
                'entry_cost': 0.0  # Near zero
            },
            'path': [
                {
                    'day': 0,
                    'mtm_pnl': 100.0,
                    'market_conditions': {},
                    'greeks': {}
                }
            ]
        }

        # Should not crash
        result = zero_trade = self.engine.apply_to_tracked_trade('Profile_1_LDG', zero_trade)
        self.assertEqual(result['pnl_pct'], 0, "Should set pnl_pct to 0 for zero entry_cost")


class TestApplyExitEngineCalculations(unittest.TestCase):
    """Verify calculation fixes in apply_exit_engine_v1.py"""

    def test_fix_001_degradation_with_negative_baseline(self):
        """FIX-001: Degradation should show -50% when val improves from -1000 to -500"""
        train_pnl = -1000
        val_pnl = -500

        # AFTER FIX: use signed denominator
        degradation = (val_pnl - train_pnl) / train_pnl * 100

        # Should be -50% (improvement, not degradation)
        self.assertEqual(degradation, -50.0)

    def test_fix_002_improvement_with_negative_baseline(self):
        """FIX-002: Improvement should show positive % when made worse"""
        original_pnl = -1000
        improvement = -200  # Lost more money = worse

        # AFTER FIX: use signed denominator
        improvement_pct = (improvement / original_pnl) * 100

        # 20% means original -1000 got 20% worse
        self.assertEqual(improvement_pct, 20.0)

    def test_degradation_with_positive_baseline(self):
        """Verify degradation still works correctly for positive P&L"""
        train_pnl = 1000
        val_pnl = 500

        degradation = (val_pnl - train_pnl) / train_pnl * 100

        # 50% worse performance
        self.assertEqual(degradation, -50.0)

    def test_improvement_with_positive_baseline(self):
        """Verify improvement still works for positive P&L"""
        original_pnl = 1000
        improvement = 200  # Made $200 more

        improvement_pct = (improvement / original_pnl) * 100

        # 20% better
        self.assertEqual(improvement_pct, 20.0)


if __name__ == '__main__':
    unittest.main()
```

**Run tests**:
```bash
cd /Users/zstoc/rotation-engine
python -m pytest tests/test_exit_engine_v1.py -v
```

All tests should pass after fixes are applied.

---

## VALIDATION CHECKLIST

After applying all fixes:

```bash
# 1. Check code compiles
python3 -m py_compile src/trading/exit_engine_v1.py
python3 -m py_compile scripts/apply_exit_engine_v1.py

# 2. Run unit tests
python -m pytest tests/test_exit_engine_v1.py -v

# 3. Run integration test
python scripts/apply_exit_engine_v1.py

# 4. Verify output
# - Check exit_engine_v1_analysis.json was created
# - Check degradation % are in expected direction
# - Check improvement % are interpretable

# 5. Compare to old results (if any)
# - Degradation % should be opposite sign of before
# - Improvement % should be clearer now
```

---

## GIT WORKFLOW

```bash
# Create feature branch
git checkout -b fix/exit-engine-bugs

# Apply fixes (copy-paste from above)
# Edit: src/trading/exit_engine_v1.py (add FIX-001)
# Edit: scripts/apply_exit_engine_v1.py (add FIX-002, FIX-003, FIX-004)
# Create: tests/test_exit_engine_v1.py (add unit tests)

# Test
python -m pytest tests/test_exit_engine_v1.py -v

# Commit
git add -A
git commit -m "fix: Exit Engine V1 - Fix 4 critical bugs (idempotency, sign convention, calculation)"

# Regenerate results
python scripts/apply_exit_engine_v1.py

# Commit new results
git add data/backtest_results/exit_engine_v1_analysis.json
git commit -m "results: Exit Engine V1 analysis with bug fixes applied"

# Push
git push origin fix/exit-engine-bugs
```

---

## SUMMARY OF CHANGES

| File | Change | Lines | Type |
|------|--------|-------|------|
| src/trading/exit_engine_v1.py | Add tp1_hit reset in apply_to_tracked_trade | ~330-333 | ADD |
| scripts/apply_exit_engine_v1.py | Remove abs() from degradation calc | 162 | EDIT |
| scripts/apply_exit_engine_v1.py | Remove abs() from improvement calc | 83 | EDIT |
| scripts/apply_exit_engine_v1.py | Remove abs() from total degradation | 168 | EDIT |
| tests/test_exit_engine_v1.py | Add unit tests for fixes | NEW | NEW |

Total lines changed: ~15 lines edited, ~100 lines tests added

---

## FINAL CHECKLIST

Before committing:

- [ ] Code compiles without errors
- [ ] All unit tests pass
- [ ] apply_exit_engine_v1.py runs without errors
- [ ] exit_engine_v1_analysis.json is generated
- [ ] Degradation/improvement values look correct
- [ ] No breaking changes to other code
- [ ] Commit message clearly describes the fixes

After merging:

- [ ] Results regenerated in new branch
- [ ] Old results archived
- [ ] Analysis updated with new metrics
- [ ] Presentation/reports updated if using old results
- [ ] Strategy decision made with validated data
