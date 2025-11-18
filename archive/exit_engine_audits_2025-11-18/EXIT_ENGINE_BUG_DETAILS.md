# EXIT ENGINE V1 - DETAILED BUG ANALYSIS

---

## BUG-EXIT-001: Idempotency Failure (CRITICAL)

### The Problem

The `apply_to_tracked_trade()` method maintains state in `self.tp1_hit` dictionary that persists across calls. This causes the same trade to produce different exit decisions on subsequent applications.

### Code Location

File: `/Users/zstoc/rotation-engine/src/trading/exit_engine_v1.py`
Lines: 299-376 (method), 58 (state variable)

### Root Cause

```python
# Line 58: State persists in instance
self.tp1_hit = {}  # Track if TP1 already hit for each trade

# Line 299-376: apply_to_tracked_trade() uses self.tp1_hit
def apply_to_tracked_trade(self, profile_id: str, trade_data: Dict) -> Dict:
    # ...
    trade_id = trade_data['entry']['entry_date']  # Line 327

    for day in daily_path:
        # ... Line 341: Check if exit triggered
        should_exit, fraction, reason = self.should_exit(
            profile_id=profile_id,
            trade_id=trade_id,  # This creates key
            days_held=day_idx,
            pnl_pct=pnl_pct,
            # ...
        )
```

### How self.should_exit() Uses State

```python
# Line 155: Create key from profile + trade_id
tp1_key = f"{profile_id}_{trade_id}"

# Line 156-157: Initialize tracking if new
if tp1_key not in self.tp1_hit:
    self.tp1_hit[tp1_key] = False

# Line 170-173: TP1 logic depends on persistent state
if cfg.tp1_pct is not None and pnl_pct >= cfg.tp1_pct:
    if not self.tp1_hit[tp1_key]:  # ← STATE CHECK
        self.tp1_hit[tp1_key] = True  # ← STATE MUTATION
        return (True, cfg.tp1_fraction, f"tp1_{cfg.tp1_pct:.0%}")
```

### Why This Is a Bug

**First Application**:
- tp1_key = "Profile_1_LDG_2025-01-01"
- self.tp1_hit is empty
- Line 156: tp1_hit_key initialized to False
- Line 170-173: Condition is True, TP1 triggers, state set to True
- **Result: Returns exit signal with fraction=0.5 (partial exit)**

**Second Application of Same Trade**:
- tp1_key = "Profile_1_LDG_2025-01-01"  (Same key!)
- self.tp1_hit[tp1_key] is ALREADY True
- Line 156: Skip initialization (key exists)
- Line 170-173: Condition is False (state already True), skip TP1
- Continues to line 180: Time check triggers instead
- **Result: Returns exit signal with fraction=1.0 (full exit, different reason!)**

### Test Output Proof

```
First apply: exit_reason='tp1_50%', exit_fraction=0.5
Second apply: exit_reason='max_tracking_days', exit_fraction=1.0
❌ SAME TRADE, DIFFERENT RESULTS
```

### Impact on Backtest

If a backtest framework re-applies Exit Engine to same trades (for validation, analysis, or debugging):
- First run: TP1 triggers at day 0, closes 50%
- Second run: TP1 doesn't trigger, closes at day 14 (max hold)
- Reported P&L is different
- Results are non-reproducible

This violates the fundamental principle: **same input must produce same output**.

### The Fix

**Option A: Reset state before each trade** (Safest)
```python
def apply_to_tracked_trade(self, profile_id: str, trade_data: Dict) -> Dict:
    # Get trade identifier
    trade_id = trade_data['entry']['entry_date']
    tp1_key = f"{profile_id}_{trade_id}"

    # RESET: Clear TP1 state for this trade to ensure idempotency
    if tp1_key in self.tp1_hit:
        del self.tp1_hit[tp1_key]

    # ... rest of logic unchanged
```

**Option B: Use local state** (Better design)
```python
def apply_to_tracked_trade(self, profile_id: str, trade_data: Dict) -> Dict:
    entry_cost = trade_data['entry']['entry_cost']
    daily_path = trade_data['path']
    trade_id = trade_data['entry']['entry_date']

    # Local TP1 state (not instance state)
    tp1_hit_local = {}
    tp1_key = f"{profile_id}_{trade_id}"
    tp1_hit_local[tp1_key] = False

    for day in daily_path:
        day_idx = day['day']
        mtm_pnl = day['mtm_pnl']

        if abs(entry_cost) < 0.01:
            pnl_pct = 0
        else:
            pnl_pct = mtm_pnl / entry_cost

        should_exit, fraction, reason = self._should_exit_internal(
            profile_id=profile_id,
            trade_id=trade_id,
            days_held=day_idx,
            pnl_pct=pnl_pct,
            market_conditions=day.get('market_conditions', {}),
            position_greeks=day.get('greeks', {}),
            tp1_hit=tp1_hit_local  # Pass local state
        )
```

---

## BUG-EXIT-002: Short Position TP1 Sign Convention

### The Problem

For short positions (negative entry_cost), the TP1 trigger logic may not work correctly if TradeTracker marks positive mtm_pnl as profit.

### Code Location

File: `/Users/zstoc/rotation-engine/src/trading/exit_engine_v1.py`
Lines: 125-184 (should_exit), 166-173 (TP1 logic)

### Mathematical Analysis

**Profile 3 (CHARM): Short Straddle Example**

Entry:
- Sell straddle for $100 premium
- entry_cost = -100 (negative, premium collected)
- max_loss_pct = -1.50 (allow up to 1.5x loss before forced exit)
- tp1_pct = 0.60 (take profit at 60% of premium collected)

**Profit Scenario**: At day 5, straddle worth $60 less
- We keep: $100 - $60 = $40 profit
- Or thinking in %: We've kept 60% of the premium collected
- So: pnl_pct should be +0.60 (60% profit)

**The Question**: How does TradeTracker mark this in mtm_pnl?

**Scenario A: TradeTracker uses positive = profit (like normal P&L)**
```
mtm_pnl = +40  (positive because we made $40)
pnl_pct = 40 / -100 = -0.40 = -40%

Then TP1 check at line 170:
if pnl_pct >= cfg.tp1_pct:
if -0.40 >= 0.60:  → FALSE ❌
```
**TP1 DOESN'T TRIGGER WHEN IT SHOULD!**

**Scenario B: TradeTracker uses negative = profit for shorts**
```
mtm_pnl = -40  (negative because it's reducing the short liability)
pnl_pct = -40 / -100 = +0.40 = +40%

Then TP1 check:
if -0.40 >= 0.60:  → FALSE ❌
```
**Still doesn't work!**

### The Real Problem

The issue is that we need to know:
1. Is this position long or short?
2. How does TradeTracker mark mtm_pnl for each?

Currently the code has NO way to distinguish.

### How to Verify

Check `/Users/zstoc/rotation-engine/src/trading/trade.py` or wherever trades are created:

```python
# Look for where entry_cost is set
# For shorts: entry_cost should be negative
# For longs: entry_cost should be positive

# Look for where mtm_pnl is calculated
# Does it use: abs(current_price - entry_price) * quantity?
# Or signed: (current_price - entry_price) * quantity?
```

### The Fix

Add explicit position type to exit config:

```python
@dataclass
class ExitConfig:
    position_type: str  # 'long' or 'short' - ADDED
    max_loss_pct: float
    tp1_pct: Optional[float]
    tp1_fraction: Optional[float]
    tp2_pct: Optional[float]
    max_hold_days: int
    condition_exit_fn: Callable[[Dict], bool]

# Then in should_exit():
def should_exit(self, profile_id: str, trade_id: str, days_held: int,
                pnl_pct: float, market_conditions: Dict, position_greeks: Dict) -> tuple:
    cfg = self.configs.get(profile_id)

    # Normalize P&L % based on position type
    if cfg.position_type == 'short':
        # For shorts, pnl_pct sign might need flipping
        # depending on TradeTracker convention
        if pnl_pct > 0:  # Positive P&L for short
            pnl_pct_normalized = pnl_pct  # Already correct
        else:
            pnl_pct_normalized = -pnl_pct  # Flip sign?
    else:
        pnl_pct_normalized = pnl_pct

    # Then use pnl_pct_normalized for all comparisons
```

### Why This Matters

Profiles that use short positions:
- Profile 3 (CHARM): Short theta straddle
- Profile 5 (SKEW): Short OTM puts for fear premiums

If TP1 doesn't trigger correctly, these positions hold longer than designed and lose more money.

---

## BUG-APPLY-001: Degradation Calculation Inverted

### The Problem

When comparing train vs validation P&L, the degradation calculation uses `abs()` denominator, which inverts the meaning when P&L is negative.

### Code Location

File: `/Users/zstoc/rotation-engine/scripts/apply_exit_engine_v1.py`
Lines: 162, 168

### The Code

```python
# Line 162 (per-profile degradation):
degradation = (val_pnl - train_pnl) / abs(train_pnl) * 100

# Line 168 (total degradation):
total_deg = (val_total - train_total) / abs(train_total) * 100 if train_total != 0 else 0
```

### Test Case

**Scenario**: Strategy has negative returns
```python
train_total = -1000  # Lost $1000 in train period
val_total = -500     # Lost $500 in validation period

# Current calculation:
degradation = (-500 - (-1000)) / abs(-1000) * 100
            = (500) / 1000 * 100
            = 50%

# Interpretation: "50% degradation" (strategy got worse)
# Reality: Validation was 50% BETTER (lost half as much)
# 🔴 COMPLETELY BACKWARDS
```

### Why abs() Breaks It

Normal percentage change formula:
```
change % = (new - old) / old * 100
```

With negative denominator:
```
If old = -1000:
  change % = (-500 - (-1000)) / (-1000) * 100
           = 500 / -1000 * 100
           = -50%

Interpretation: "-50% change" = 50% improvement ✓ CORRECT
```

But with abs():
```
If old = -1000:
  change % = (-500 - (-1000)) / abs(-1000) * 100
           = 500 / 1000 * 100
           = 50%

Interpretation: "50% change" (which direction?) ❌ CONFUSING
```

### Visual Example

```
Train: -$1000 ──────────────────────
Val:   -$500  ────

Improvement: Went from losing $1000 to losing $500
That's 50% BETTER performance

But code shows: 50% degradation ❌
```

### The Fix

Remove abs() and use signed denominator:

```python
# Line 162:
if abs(train_pnl) < 0.01:  # Already near-zero safe
    degradation = 0
else:
    degradation = (val_pnl - train_pnl) / train_pnl * 100

# Line 168:
total_deg = (val_total - train_total) / train_total * 100 if train_total != 0 else 0
```

Or keep abs() but interpret results correctly:
```python
degradation = (val_pnl - train_pnl) / abs(train_pnl) * 100

# Then interpret:
# If train_pnl < 0:
#   degradation > 0 means more loss (worse)
#   degradation < 0 means less loss (better)
```

### Impact

Users see train vs validation report:
```
Profile_1: Train $1000 vs Val $500 → Shows "50% degradation"
```

They think: "Validation is 50% worse, don't deploy"
Reality: "Validation is 50% better, definitely deploy"

**Strategic decision could be completely backwards.**

---

## BUG-APPLY-002: Improvement Percentage Inverted

### The Problem

Similar to BUG-APPLY-001, the improvement percentage uses `abs()` denominator, making results ambiguous for negative original P&L.

### Code Location

File: `/Users/zstoc/rotation-engine/scripts/apply_exit_engine_v1.py`
Line: 83

### The Code

```python
# Line 76-83:
original_pnl = profile_data['summary']['total_pnl']
improvement = total_pnl_v1 - original_pnl

if abs(original_pnl) < 0.01:
    improvement_pct = 0
else:
    improvement_pct = (improvement / abs(original_pnl) * 100)
```

### Test Case

**Scenario**: Exit Engine made performance worse
```python
original_pnl = -1000  # Lost $1000 with 14-day tracking
total_pnl_v1 = -1200  # Lost $1200 with Exit Engine (worse!)
improvement = -1200 - (-1000) = -200  # Negative = worse

# Current calculation:
improvement_pct = -200 / abs(-1000) * 100
               = -200 / 1000 * 100
               = -20%

# Interpretation: "-20% improvement" (ambiguous!)
# Could mean:
#   A) Made things 20% worse ✓ CORRECT
#   B) Achieved -20% of the goal ✗ CONFUSING
```

### Why This Is Ambiguous

The result "-20%" is ambiguous:
- Is it "20% worse"?
- Is it "negative 20% improvement"?
- Is it "-20% improvement" (meaning 20% improvement)?

For positive original_pnl, it's clear:
```python
original_pnl = 1000
improvement = 200
improvement_pct = 200 / 1000 * 100 = 20%
# Interpretation: "20% better" ✓ CLEAR
```

But for negative, it breaks:
```python
original_pnl = -1000
improvement = -200
improvement_pct = -200 / abs(-1000) * 100 = -20%
# Interpretation: "-20%" (which direction?) ❌ AMBIGUOUS
```

### The Fix

**Option A: Use signed denominator (cleaner)**
```python
if original_pnl != 0:
    improvement_pct = (improvement / original_pnl) * 100
else:
    improvement_pct = 0

# Then interpret normally:
# positive = better
# negative = worse
```

**Option B: Normalize sign**
```python
if abs(original_pnl) < 0.01:
    improvement_pct = 0
else:
    improvement_pct = (improvement / abs(original_pnl)) * 100

# Then interpret with sign awareness:
# If original_pnl < 0:
#   positive improvement_pct = made things worse
#   negative improvement_pct = made things better
# If original_pnl > 0:
#   positive improvement_pct = made things better
#   negative improvement_pct = made things worse
```

### Example Impact

Report shows:
```
Profile_3 CHARM:
  Original P&L: -$1000
  With Exit Engine: -$1200
  Improvement: -$200 (-20%)
```

Analyst reads: "That's a -20% improvement, so it made things slightly worse?"
Reality: "Made things 20% worse, lost additional $200"

**Clarity issue makes report hard to interpret.**

---

## Testing Protocol

To verify these bugs are fixed:

### Test 1: Idempotency
```python
from src.trading.exit_engine_v1 import ExitEngineV1

engine = ExitEngineV1()
trade = {
    'entry': {'entry_date': '2025-01-01', 'entry_cost': 100.0},
    'path': [
        {'day': 0, 'mtm_pnl': 50.0, 'market_conditions': {}, 'greeks': {}}
    ]
}

result1 = engine.apply_to_tracked_trade('Profile_1_LDG', trade)
result2 = engine.apply_to_tracked_trade('Profile_1_LDG', trade)

assert result1['exit_reason'] == result2['exit_reason'], "BUG-EXIT-001 not fixed!"
assert result1['exit_fraction'] == result2['exit_fraction'], "BUG-EXIT-001 not fixed!"
print("✓ Idempotency test passed")
```

### Test 2: Short Position TP1
```python
# Need to trace actual TradeTracker behavior first
# Then add test case like:
short_trade = {
    'entry': {'entry_date': '2025-01-01', 'entry_cost': -100.0},
    'path': [
        {'day': 0, 'mtm_pnl': -60.0, 'market_conditions': {}, 'greeks': {}}
    ]
}

result = engine.apply_to_tracked_trade('Profile_3_CHARM', short_trade)
assert result['exit_reason'] == 'tp1_60%', "Short TP1 not triggering!"
```

### Test 3: Degradation
```python
# Create mock results with negative P&L
train_results = {'profile1': {'exit_engine_v1_pnl': -1000}}
val_results = {'profile1': {'exit_engine_v1_pnl': -500}}

degradation = (-500 - (-1000)) / (-1000) * 100  # Should be -50%
assert degradation == -50, f"Expected -50%, got {degradation}%"
print("✓ Degradation test passed")
```

### Test 4: Improvement
```python
original = -1000
new = -1200
improvement = new - original  # -200

improvement_pct = improvement / original * 100  # Should be 20%
assert improvement_pct == 20, f"Expected 20%, got {improvement_pct}%"
# 20% means the original -1000 got 20% more negative = worse
print("✓ Improvement test passed")
```

---

## Summary

| Bug | Severity | Root Cause | Impact |
|-----|----------|-----------|--------|
| EXIT-001 | CRITICAL | Persistent self.tp1_hit state | Non-deterministic exit decisions |
| EXIT-002 | HIGH | Unknown sign convention for short mtm_pnl | TP1 may not trigger on shorts |
| APPLY-001 | HIGH | abs() denominator inverts meaning | Degradation shown backwards |
| APPLY-002 | HIGH | abs() denominator makes sign ambiguous | Improvement shown ambiguously |

All 4 bugs must be fixed before backtest results are trustworthy.
