# REQUIRED ACTIONS TO FIX BUG-001 AND UNBLOCK DEPLOYMENT

## Priority: CRITICAL - Blocks all deployments

## Root Cause

TradeTracker and Trade.py use different entry_cost formulas:

```python
# TradeTracker (fixed, but creates inconsistency)
entry_cost = sum(qty * (price ± spread) * 100) + commission

# Trade.py (not updated)
entry_cost = sum(qty * price * 100)
```

Result: **$860 difference on 100 trades = 17% P&L difference**

---

## Analysis: Which System is "Right"?

### Check: What does Simulator actually pass to Trade.py?

**File**: `src/trading/simulator.py`, lines 424-429

```python
if real_bid is not None and real_ask is not None:
    self.stats['real_prices_used'] += 1
    if leg.quantity > 0:
        exec_price = real_ask  # Buy at ask
    else:
        exec_price = real_bid  # Sell at bid
```

**Answer**: Simulator passes **EXECUTION PRICES** (ask for long, bid for short)

These prices **ALREADY INCLUDE THE SPREAD**!

---

### Implication

If Simulator passes ask/bid (execution prices), then:

- Trade.py is **CORRECT** (uses execution prices as-is)
- TradeTracker is **WRONG** (adds spread to already-spread prices)

TradeTracker adds spread TWICE:
1. Once implicitly in the execution price (ask/bid from Polygon)
2. Again explicitly (lines 97, 100)

---

## Solution: Fix TradeTracker to Not Double-Add Spread

### Current TradeTracker Code (WRONG)

**File**: `src/analysis/trade_tracker.py`, lines 83-104

```python
for leg in position['legs']:
    opt_type = leg['type']
    qty = leg['qty']

    # Gets MID price from Polygon
    price = self.polygon.get_option_price(
        entry_date, position['strike'], position['expiry'], opt_type, 'mid'
    )

    # Lines 95-100: ADDS spread to mid price
    if qty > 0:
        leg_cost = qty * (price + spread) * 100  # ADDS spread
    else:
        leg_cost = qty * (price - spread) * 100  # ADDS spread

    entry_cost += leg_cost

entry_cost += commission
```

**Problem**: Gets MID prices, then adds spread. This is correct IF Polygon returns true mid prices.

But need to verify: Does `get_option_price(..., 'mid')` return:
- True mid = (bid + ask) / 2?
- Or something else?

---

### Action Item 1: Verify Polygon Price Type Behavior

**File**: `src/data/polygon_options.py`

Search for `price_type='mid'` implementation:

```python
def get_option_price(self, trade_date, strike, expiry, option_type, price_type):
    # What does price_type='mid' actually return?
    # - If (bid+ask)/2: TradeTracker is correct to add spread
    # - If something else: Need to adjust
```

**Action**:
1. Read the implementation
2. If it returns true mid: TradeTracker is correct
3. If it returns something else: Update TradeTracker accordingly

---

### Solution Path A: If Polygon Returns True Mid Prices

Then TradeTracker is correct as-is.

**Action**: Update Trade.py to match TradeTracker:

```python
# File: src/trading/trade.py, lines 99-103
# Add spread and commission to entry_cost

def __post_init__(self):
    if self.entry_prices:
        spread = 0.03  # From config
        commission = 2.60  # From config

        self.entry_cost = 0
        for i, price in self.entry_prices.items():
            qty = self.legs[i].quantity
            if qty > 0:
                leg_cost = qty * (price + spread) * 100
            else:
                leg_cost = qty * (price - spread) * 100
            self.entry_cost += leg_cost

        self.entry_cost += commission
```

---

### Solution Path B: If Simulator Passes Execution Prices

Then Trade.py is correct as-is.

**Action**: Update TradeTracker to NOT add spread:

```python
# File: src/analysis/trade_tracker.py, lines 83-104
# Change to get execution prices (ask/bid) instead of mid

for leg in position['legs']:
    opt_type = leg['type']
    qty = leg['qty']

    # Change: Get execution prices (ask for long, bid for short)
    if qty > 0:
        price = self.polygon.get_option_price(..., 'ask')
    else:
        price = self.polygon.get_option_price(..., 'bid')

    # Change: Don't add spread (already in ask/bid)
    leg_cost = qty * price * 100  # No ± spread addition

    entry_cost += leg_cost

entry_cost += commission
```

---

## Decision: Which Path to Take?

**RECOMMENDED: Solution Path B** (Use execution prices everywhere)

**Rationale**:
- Simulator already uses execution prices (real_ask, real_bid)
- Trade.py already expects execution prices
- Only TradeTracker needs to change
- Simpler: no duplication of spread logic
- More realistic: single source of truth

---

## Implementation Steps (Solution Path B)

### Step 1: Update TradeTracker.py

**File**: `/Users/zstoc/rotation-engine/src/analysis/trade_tracker.py`

**Change lines 79-104** from:

```python
for leg in position['legs']:
    opt_type = leg['type']
    qty = leg['qty']

    price = self.polygon.get_option_price(
        entry_date, position['strike'], position['expiry'], opt_type, 'mid'
    )
    if price is None:
        return None

    entry_prices[opt_type] = price

    # FIX BUG-001: Correct sign convention
    if qty > 0:
        leg_cost = qty * (price + spread) * 100
    else:
        leg_cost = qty * (price - spread) * 100

    entry_cost += leg_cost

entry_cost += commission
```

To:

```python
for leg in position['legs']:
    opt_type = leg['type']
    qty = leg['qty']

    # FIX BUG-001: Use execution prices (ask for long, bid for short)
    # Don't add spread - it's already in ask/bid prices
    if qty > 0:
        price = self.polygon.get_option_price(
            entry_date, position['strike'], position['expiry'], opt_type, 'ask'
        )
    else:
        price = self.polygon.get_option_price(
            entry_date, position['strike'], position['expiry'], opt_type, 'bid'
        )

    if price is None:
        return None

    entry_prices[opt_type] = price

    # Correct sign convention (no spread adjustment needed)
    if qty > 0:
        leg_cost = qty * price * 100  # Long: positive outflow
    else:
        leg_cost = qty * price * 100  # Short: negative inflow

    entry_cost += leg_cost

entry_cost += commission  # Always a cost
```

### Step 2: Verify Trade.py Entry Cost Calculation

**File**: `/Users/zstoc/rotation-engine/src/trading/trade.py`

Lines 99-103 should already be correct:

```python
if self.entry_prices:
    self.entry_cost = sum(
        self.legs[i].quantity * price * CONTRACT_MULTIPLIER
        for i, price in self.entry_prices.items()
    )
```

**Action**: Confirm this is unchanged from original (it is)

### Step 3: Add Unit Test to Verify Consistency

**Create file**: `/Users/zstoc/rotation-engine/test_entry_cost_consistency.py`

```python
"""
Test that entry_cost is consistent between Trade.py and TradeTracker.py

This test verifies that BUG-001 is fixed: both systems calculate the same
entry_cost for identical trades.
"""

import unittest
from datetime import datetime, date
from src.trading.trade import Trade, TradeLeg
from src.analysis.trade_tracker import TradeTracker

class TestEntryConsistency(unittest.TestCase):

    def test_long_call_entry_cost(self):
        """Long 1 call: Trade.py and TradeTracker should match."""
        # Trade.py calculation
        trade = Trade(
            trade_id="TEST",
            profile_name="TEST",
            entry_date=datetime(2025, 1, 1),
            legs=[TradeLeg(strike=100, expiry=datetime(2025, 1, 31), qty=1, option_type='call')],
            entry_prices={0: 3.50}  # Execution price (ask)
        )
        trade.entry_commission = 2.60
        trade.__post_init__()

        trade_entry_cost = trade.entry_cost  # Should be 350 + 2.60 = 352.60

        # TradeTracker calculation (simulated)
        # get_option_price('ask') returns 3.50
        # entry_cost = 1 * 3.50 * 100 + 2.60 = 352.60
        tracker_entry_cost = 1 * 3.50 * 100 + 2.60

        self.assertAlmostEqual(trade_entry_cost, tracker_entry_cost, places=2,
                             msg=f"Entry costs don't match: Trade={trade_entry_cost}, Tracker={tracker_entry_cost}")

    def test_short_call_entry_cost(self):
        """Short 1 call: Trade.py and TradeTracker should match."""
        # Trade.py calculation
        trade = Trade(
            trade_id="TEST",
            profile_name="TEST",
            entry_date=datetime(2025, 1, 1),
            legs=[TradeLeg(strike=100, expiry=datetime(2025, 1, 31), qty=-1, option_type='call')],
            entry_prices={0: 3.45}  # Execution price (bid)
        )
        trade.entry_commission = 2.60
        trade.__post_init__()

        trade_entry_cost = trade.entry_cost  # Should be -1 * 345 + 2.60 = -342.40

        # TradeTracker calculation (simulated)
        # get_option_price('bid') returns 3.45
        # entry_cost = -1 * 3.45 * 100 + 2.60 = -342.40
        tracker_entry_cost = -1 * 3.45 * 100 + 2.60

        self.assertAlmostEqual(trade_entry_cost, tracker_entry_cost, places=2,
                             msg=f"Entry costs don't match: Trade={trade_entry_cost}, Tracker={tracker_entry_cost}")

    def test_straddle_entry_cost(self):
        """Long straddle: Trade.py and TradeTracker should match."""
        # Trade.py calculation
        trade = Trade(
            trade_id="TEST",
            profile_name="TEST",
            entry_date=datetime(2025, 1, 1),
            legs=[
                TradeLeg(strike=100, expiry=datetime(2025, 1, 31), qty=1, option_type='call'),
                TradeLeg(strike=100, expiry=datetime(2025, 1, 31), qty=1, option_type='put')
            ],
            entry_prices={0: 3.50, 1: 2.45}  # Execution prices (ask)
        )
        trade.entry_commission = 2.60
        trade.__post_init__()

        trade_entry_cost = trade.entry_cost  # Should be 350 + 245 + 2.60 = 597.60

        # TradeTracker calculation (simulated)
        # Call: 1 * 3.50 * 100 = 350
        # Put: 1 * 2.45 * 100 = 245
        # Total: 350 + 245 + 2.60 = 597.60
        tracker_entry_cost = (1 * 3.50 * 100) + (1 * 2.45 * 100) + 2.60

        self.assertAlmostEqual(trade_entry_cost, tracker_entry_cost, places=2,
                             msg=f"Entry costs don't match: Trade={trade_entry_cost}, Tracker={tracker_entry_cost}")


if __name__ == '__main__':
    unittest.main()
```

**Run test**:
```bash
cd /Users/zstoc/rotation-engine
python -m pytest test_entry_cost_consistency.py -v
```

All tests should PASS after the fix.

### Step 4: Run Integration Test

Create test trade, run through complete pipeline:
1. Simulator enters trade (gets execution prices)
2. Trade.py calculates entry_cost
3. TradeTracker analyzes same trade (gets execution prices)
4. Verify both systems produce identical entry_cost

**Command**:
```bash
python test_entry_cost_consistency.py
```

### Step 5: Re-run Full Backtest

After fixing TradeTracker:

```bash
python run_backtest.py  # Your main backtest script
```

Verify:
- Backtest completes without errors
- P&L numbers are reasonable (not suspiciously high)
- Equity curve looks realistic
- Compare to pre-fix results (should show difference of ~$8.60 per trade)

### Step 6: Update Documentation

**File**: `src/analysis/trade_tracker.py`

Add explicit comment at the top explaining entry_cost convention:

```python
"""
Entry Cost Convention (BUG-001 FIX):
=====================================

entry_cost represents the cash flow at trade entry, including execution spread and commission.

Sign Convention:
- LONG positions (qty > 0): positive entry_cost (cash outflow when buying)
- SHORT positions (qty < 0): negative entry_cost (cash inflow when selling)
- Commission: always positive (cost to trade)

Formula:
  leg_cost = qty * execution_price * 100
  entry_cost = sum(leg_cost) + commission

Where execution_price is:
  - ask_price for long positions (we pay this to buy)
  - bid_price for short positions (we receive this to sell)

Consistency:
- TradeTracker uses execution prices (ask/bid)
- Trade.py uses execution prices (ask/bid)
- Simulator provides execution prices
- All systems calculate identical entry_cost
"""
```

---

## Verification Checklist

Before considering BUG-001 FIXED:

- [ ] TradeTracker.py updated to use ask/bid prices (not mid + spread)
- [ ] TradeTracker.py doesn't double-add spread
- [ ] Trade.py entry_cost unchanged (already correct)
- [ ] Simulator still passes execution prices (verify no changes)
- [ ] Unit test created and PASSES
- [ ] Integration test created and PASSES
- [ ] Documentation updated with entry_cost convention
- [ ] Full backtest re-run
- [ ] Results compare correctly to pre-fix
- [ ] P&L shows expected difference (~$8.60 per trade lower)

---

## Estimated Work Time

- Investigation/decision: 0.5 hours
- Implementation: 1 hour
- Testing: 1 hour
- Backtest re-run: 2 hours
- **Total: 4.5 hours**

---

## Sign-Off

After all steps complete, you can deploy with confidence that:

✅ All 4 critical bugs are fixed
✅ P&L calculation is consistent across systems
✅ Backtest results are valid
✅ No look-ahead bias
✅ Greeks properly scaled
✅ Commissions correctly treated
✅ Hedging properly implemented

**THEN you can trade real capital.**

