# BUG-001: CRITICAL INCONSISTENCY IN P&L SIGN CONVENTION

## Executive Summary

The fix to BUG-001 in `trade_tracker.py` is **mathematically correct** but **reveals a systemic inconsistency** with `trade.py`. These two systems use **different entry_cost calculations**, which will produce **different P&L results for identical positions**.

**This inconsistency BLOCKS deployment.**

---

## Root Cause: Two Different Sign Conventions

### System 1: TradeTracker (Fixed)

**File**: `/Users/zstoc/rotation-engine/src/analysis/trade_tracker.py`
**Lines**: 91-104

```python
# FIX BUG-001: Correct sign convention
if qty > 0:
    # Long position - we PAY the ask (include spread)
    leg_cost = qty * (price + spread) * 100  # Positive for outflow
else:
    # Short position - we RECEIVE the bid (subtract spread)
    leg_cost = qty * (price - spread) * 100  # Negative for inflow

entry_cost += leg_cost

# Commission is always a cost (positive addition)
entry_cost += commission  # $2.60
```

**This calculates**:
```
entry_cost = sum(qty_i * (price_i ± spread) * 100) + commission
```

**For LONG positions**: Positive entry_cost (cash outflow when buying)
**For SHORT positions**: Negative entry_cost (cash inflow when selling)

---

### System 2: Trade.py (NOT Updated)

**File**: `/Users/zstoc/rotation-engine/src/trading/trade.py`
**Lines**: 99-103

```python
if self.entry_prices:
    self.entry_cost = sum(
        self.legs[i].quantity * price * CONTRACT_MULTIPLIER
        for i, price in self.entry_prices.items()
    )
```

**This calculates**:
```
entry_cost = sum(qty_i * price_i * 100)
```

**Key Differences**:
1. Uses `price` directly (assumes mid price)
2. NO spread adjustment (±0.03)
3. NO commission added ($2.60)

---

## Concrete Example: Where They Diverge

### Trade: Long 1 ATM Call + Long 1 ATM Put (Straddle)

**Market Conditions** (Day 1, Entry):
- Spot = $505
- Call strike = $505
- Put strike = $505
- Mid prices: Call = $3.00, Put = $2.50
- Spread (both legs) = $0.03
- Commission = $2.60 per trade (we count it once for entry)

---

### TradeTracker Calculation

```python
# Entry prices
entry_prices = {'call': 3.00, 'put': 2.50}

# Call leg (qty=+1, buying at ask)
call_cost = 1 * (3.00 + 0.03) * 100 = +303

# Put leg (qty=+1, buying at ask)
put_cost = 1 * (2.50 + 0.03) * 100 = +253

# Total
entry_cost = 303 + 253 + 2.60 = $558.60

# This represents: We PAID $558.60 to enter the straddle
```

---

### Trade.py Calculation

Assuming `entry_prices` dict passed from simulator:

```python
# Entry prices
entry_prices = {0: 3.00, 1: 2.50}  # Assuming indices for call, put

# Calculation (ignoring spread and commission)
entry_cost = 1 * 3.00 * 100 + 1 * 2.50 * 100 = 300 + 250 = $550

# This represents: Mid price for 1 call + 1 put = $550
```

---

## Impact on P&L Calculation

### Day 2: Mark-to-Market

Call now worth $3.15, Put now worth $2.60

**TradeTracker Unrealized P&L**:
```python
# MTM value (using mid prices for fair value)
mtm_value = (1 * 3.15 * 100) + (1 * 2.60 * 100) = 315 + 260 = $575

# Unrealized P&L (from entry)
unrealized = $575 - $558.60 - $2.60 (exit commission estimate) = $13.80
```

**Trade.py Unrealized P&L**:
```python
# Unrealized (using entry_prices = $550)
unrealized = (1 * (3.15 - 3.00) * 100) + (1 * (2.60 - 2.50) * 100)
           = 15 + 10 = $25

# Different! Because entry_cost was $550, not $558.60
```

**Difference**: $25 - $13.80 = **$11.20 discrepancy**

---

## Why This Matters for Backtesting

### Scenario: 100 Trades Over 1 Year

Each trade is a straddle at:
- Mid entry: $5.50
- Entry cost (TradeTracker): $5.50 * 100 + $0.03 * 100 * 2 + $2.60 = $558.60
- Entry cost (Trade.py): $5.50 * 100 = $550

**Over 100 trades**:
- TradeTracker total cost: 100 * $558.60 = $55,860
- Trade.py total cost: 100 * $550 = $55,000
- Discrepancy: **$860 difference in entry costs alone**

### If Average Exit is +$0.50 per straddle (net $50):
- TradeTracker P&L: 100 * $50 - $860 = $4,140
- Trade.py P&L: 100 * $50 = $5,000
- Backtest shows **$860 (17%) difference** for same trades!

---

## Where Entry Prices Come From

### TradeTracker
Uses execution prices in `_estimate_option_price()`:
```python
# Lines 83-85
price = self.polygon.get_option_price(entry_date, strike, expiry, opt_type, 'mid')
# Then adds spread in lines 95-100:
leg_cost = qty * (price + spread) * 100  # With spread!
```

### Trade.py via Simulator
The `entry_prices` dict comes from `_get_entry_prices()`:
```python
# Lines 426-429
if leg.quantity > 0:
    exec_price = real_ask  # Buy at ask
else:
    exec_price = real_bid  # Sell at bid
entry_prices[i] = exec_price
```

**Wait - the Simulator DOES use bid/ask!**

But then Trade.__post_init__() uses it as-is:
```python
# Lines 99-103
self.entry_cost = sum(
    self.legs[i].quantity * price * CONTRACT_MULTIPLIER
    for i, price in self.entry_prices.items()
)
```

**Problem**: If Simulator passes execution prices (real_ask for longs), Trade.py should work correctly. But if it passes mid prices, Trade.py will be wrong.

---

## Verification: What Does Simulator Actually Pass?

**File**: `/Users/zstoc/rotation-engine/src/trading/simulator.py`
**Lines**: 174-176

```python
entry_prices = self._get_entry_prices(current_trade, row)
current_trade.entry_prices = entry_prices
current_trade.__post_init__()
```

**_get_entry_prices()** (lines 424-429):
```python
if real_bid is not None and real_ask is not None:
    self.stats['real_prices_used'] += 1
    if leg.quantity > 0:
        exec_price = real_ask  # Buy at ask
    else:
        exec_price = real_bid  # Sell at bid
```

**Conclusion**: Simulator passes **execution prices** (ask for long, bid for short)

---

## The Real Problem

### TradeTracker Applies Spread AGAIN

TradeTracker shouldn't add spread if Simulator already included it!

**Current TradeTracker code** (lines 95-100):
```python
if qty > 0:
    # Long position - we PAY the ask (include spread)
    leg_cost = qty * (price + spread) * 100  # ADDS spread
else:
    # Short position - we RECEIVE the bid (subtract spread)
    leg_cost = qty * (price - spread) * 100  # SUBTRACTS spread
```

**If `price` is already the ask price**, then adding spread is WRONG!

---

## Two Solutions

### Solution A: TradeTracker Uses Mid Prices, Adds Spread

Requirements:
- TradeTracker must get MID prices from Polygon
- TradeTracker adds spread (current implementation)
- Trade.py must also use mid prices and add spread

Cost:
- Trade.py needs to be updated to apply spread and commission to entry_cost
- Requires access to mid vs ask/bid in Trade.py

### Solution B: TradeTracker Uses Execution Prices, No Spread Addition

Requirements:
- TradeTracker gets execution prices (ask for long, bid for short)
- TradeTracker DOES NOT add spread (entry price is already adjusted)
- Trade.py uses same execution prices

Cost:
- TradeTracker code must be updated to NOT add spread
- Need to pass 'mid' vs 'ask'/'bid' flag to TradeTracker

---

## Recommended Fix

**Use Solution B: Execution Prices, No Spread Addition**

### In TradeTracker (lines 83-100):

```python
# CHANGE: Get execution prices, not mid
for leg in position['legs']:
    opt_type = leg['type']
    qty = leg['qty']

    # Get execution prices (ask for long, bid for short)
    if qty > 0:
        price = self.polygon.get_option_price(..., 'ask')  # Change to ask
    else:
        price = self.polygon.get_option_price(..., 'bid')  # Change to bid

    # CHANGE: Don't add spread (already in ask/bid)
    leg_cost = qty * price * 100  # No ± spread addition

entry_cost += leg_cost
entry_cost += commission
```

### In Trade.py (lines 99-103):

Keep as-is - it already uses execution prices correctly.

### In Simulator (lines 424-429):

Already correct - passes execution prices.

---

## Validation After Fix

Run a single trade through all three systems and verify:

1. **Simulator**:
   - Enters trade with execution prices (ask/bid)
   - entry_prices dict contains ask for longs, bid for shorts
   - Passes to Trade.py

2. **Trade.py**:
   - Receives entry_prices (execution prices)
   - Calculates: entry_cost = sum(qty * exec_price * 100) + commission
   - Uses this for P&L calculations

3. **TradeTracker** (if analyzing same trade):
   - Gets execution prices (ask/bid) from Polygon
   - Calculates: entry_cost = sum(qty * exec_price * 100) + commission
   - Should match Trade.py exactly

**Expected**: All three systems should produce identical P&L for same trade

---

## Checklist for Deployment

- [ ] Update TradeTracker to get execution prices (ask/bid) not mid
- [ ] Update TradeTracker to NOT add spread to execution prices
- [ ] Verify Trade.py entry_cost matches TradeTracker entry_cost
- [ ] Run test: single trade through all systems, verify P&L consistency
- [ ] Run test: 100 trades, verify equity curves match
- [ ] Update documentation with entry_cost sign convention
- [ ] Add unit tests for entry_cost calculation
- [ ] Re-run full backtest
- [ ] Verify results make sense (not too good, not too bad)
- [ ] Get approval before live trading

