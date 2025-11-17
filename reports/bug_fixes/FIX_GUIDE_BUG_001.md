# FIX GUIDE: BUG-001 P&L SIGN INVERSION

## Problem Summary

The P&L calculation in `trade.py` uses a confusing double-negative sign convention that produces inverted P&L results. All profitable trades show as losses, and all losing trades show as profits.

## Root Cause

Lines 71-74 and 84-87 use the formula: `-quantity * price` which creates ambiguous semantics.

```python
# Current (buggy) code
entry_cost = sum(
    -self.legs[i].quantity * price  # Double negative confusion
    for i, price in self.entry_prices.items()
)

exit_proceeds = sum(
    -self.legs[i].quantity * price  # Double negative confusion
    for i, price in exit_prices.items()
)

realized_pnl = exit_proceeds - entry_cost
```

This produces:
- LONG trade (qty=+1): `realized_pnl = -exit - (-entry) = -(exit - entry)` ← WRONG SIGN
- SHORT trade (qty=-1): `realized_pnl = exit - entry = (entry - exit)` ← WRONG SIGN

## Solution

### Option A: Clearest Fix (Recommended)

Replace the `__post_init__` and `close` methods with explicit per-leg P&L calculation:

```python
def __post_init__(self):
    """Calculate entry cost from entry prices."""
    if self.entry_prices:
        # entry_cost represents cash outflow (positive = paid, negative = received)
        # For long (qty > 0): we pay → entry_cost is positive
        # For short (qty < 0): we receive → entry_cost is negative
        self.entry_cost = sum(
            self.legs[i].quantity * price  # Remove the minus sign
            for i, price in self.entry_prices.items()
        )

def close(self, exit_date: datetime, exit_prices: Dict[int, float], reason: str):
    """Close the trade and calculate realized P&L."""
    self.is_open = False
    self.exit_date = exit_date
    self.exit_prices = exit_prices
    self.exit_reason = reason

    # Calculate P&L per leg using standard accounting
    self.realized_pnl = 0.0
    for i, exit_price in exit_prices.items():
        leg = self.legs[i]
        entry_price = self.entry_prices[i]

        # P&L per leg = quantity * (exit_price - entry_price)
        # For long (qty > 0): profit when exit > entry
        # For short (qty < 0): profit when entry > exit
        leg_pnl = leg.quantity * (exit_price - entry_price)
        self.realized_pnl += leg_pnl

    # Subtract hedging costs
    self.realized_pnl -= self.cumulative_hedge_cost
```

### Option B: Keep Current Structure, Fix Sign

If you want to keep the double-negative pattern, just adjust the final formula:

```python
def __post_init__(self):
    """Calculate entry cost from entry prices."""
    if self.entry_prices:
        self.entry_cost = sum(
            -self.legs[i].quantity * price  # Keep this
            for i, price in self.entry_prices.items()
        )

def close(self, exit_date: datetime, exit_prices: Dict[int, float], reason: str):
    """Close the trade and calculate realized P&L."""
    self.is_open = False
    self.exit_date = exit_date
    self.exit_prices = exit_prices
    self.exit_reason = reason

    # Calculate exit proceeds
    self.exit_proceeds = sum(
        -self.legs[i].quantity * price  # Keep this
        for i, price in exit_prices.items()
    )

    # FIX: Change formula to NEGATE the subtraction
    # Was: self.realized_pnl = self.exit_proceeds - self.entry_cost - self.cumulative_hedge_cost
    # Now:
    self.realized_pnl = self.entry_cost - self.exit_proceeds - self.cumulative_hedge_cost
    # This flips the sign back to correct
```

### Option C: Python Idiom Fix

Use Pythonic accounting idioms:

```python
def __post_init__(self):
    """Calculate entry cost from entry prices."""
    if self.entry_prices:
        # Cash flow convention:
        # - Positive: money we paid out (debit)
        # - Negative: money we received (credit)
        self.entry_cost = 0.0
        for i, price in self.entry_prices.items():
            leg = self.legs[i]
            if leg.quantity > 0:  # Long
                self.entry_cost += leg.quantity * price  # Money paid
            else:  # Short
                self.entry_cost += leg.quantity * price  # Negative = money received

def close(self, exit_date: datetime, exit_prices: Dict[int, float], reason: str):
    """Close the trade and calculate realized P&L."""
    self.is_open = False
    self.exit_date = exit_date
    self.exit_prices = exit_prices
    self.exit_reason = reason

    # Calculate exit cash flows
    self.exit_proceeds = 0.0
    for i, price in exit_prices.items():
        leg = self.legs[i]
        if leg.quantity > 0:  # Closing long
            self.exit_proceeds -= leg.quantity * price  # Money received as negative
        else:  # Closing short
            self.exit_proceeds -= leg.quantity * price  # Money paid as positive

    # P&L = proceeds - cost - hedges
    self.realized_pnl = self.exit_proceeds - self.entry_cost - self.cumulative_hedge_cost
```

## Testing the Fix

### Before Fix (Broken)

```python
# Long straddle: buy call @ $2.50, buy put @ $3.00
# Sell at $4.00, $2.00
entry_prices = [2.50, 3.00]
exit_prices = [4.00, 2.00]
quantities = [1, 1]

trade = Trade(...)
trade.entry_prices = {0: 2.50, 1: 3.00}
trade.__post_init__()
# entry_cost = -1*2.50 + -1*3.00 = -5.50

trade.close(exit_prices={0: 4.00, 1: 2.00})
# exit_proceeds = -1*4.00 + -1*2.00 = -6.00
# realized_pnl = -6.00 - (-5.50) = -0.50 ❌ WRONG (should be +0.50)
```

### After Fix (Correct)

```python
# Same trade
trade = Trade(...)
trade.entry_prices = {0: 2.50, 1: 3.00}
trade.__post_init__()
# entry_cost = 1*2.50 + 1*3.00 = 5.50

trade.close(exit_prices={0: 4.00, 1: 2.00})
# Using Option A:
# realized_pnl = 1*(4.00-2.50) + 1*(2.00-3.00) = 1.50 + (-1.00) = 0.50 ✓ CORRECT
```

## Also Fix: mark_to_market Method

The `mark_to_market` method (lines 92-104) has the same issue:

```python
# Current (buggy)
def mark_to_market(self, current_prices: Dict[int, float]) -> float:
    """Calculate current P&L (unrealized for open trades)."""
    if not self.is_open:
        return self.realized_pnl

    current_value = sum(
        -self.legs[i].quantity * price  # Same double negative problem
        for i, price in current_prices.items()
    )

    return current_value - self.entry_cost - self.cumulative_hedge_cost

# After fix (using Option A approach):
def mark_to_market(self, current_prices: Dict[int, float]) -> float:
    """Calculate current P&L (unrealized for open trades)."""
    if not self.is_open:
        return self.realized_pnl

    # Current value of position
    current_pnl = 0.0
    for i, current_price in current_prices.items():
        leg = self.legs[i]
        entry_price = self.entry_prices[i]

        # P&L = qty * (current - entry)
        leg_pnl = leg.quantity * (current_price - entry_price)
        current_pnl += leg_pnl

    return current_pnl - self.cumulative_hedge_cost
```

## Implementation Steps

1. **Backup current version**
   ```bash
   cp src/trading/trade.py src/trading/trade.py.backup
   ```

2. **Apply fix** (Use Option A - it's clearest)
   - Replace `__post_init__` method (lines 68-74)
   - Replace `close` method (lines 76-90)
   - Replace `mark_to_market` method (lines 92-104)

3. **Run tests**
   ```bash
   python3 tests/test_trade_pnl.py  # If exists
   python3 PNL_BUG_DEMO.py  # Should now show all ✓
   ```

4. **Validate backtest**
   ```bash
   python3 validate_day1.py
   python3 validate_day2.py
   # ... etc
   ```

5. **Manual spot check**
   - Pick 10 random closed trades
   - Calculate P&L manually
   - Compare to reported P&L
   - Should match exactly

## Code Diff Summary

### Current (Buggy) - 47 lines
```
Line 71-74: entry_cost = sum(-qty * price)
Line 84-87: exit_proceeds = sum(-qty * price)
Line 90:    realized_pnl = exit_proceeds - entry_cost
Line 93-101: current_value = sum(-qty * price)
Line 104:   return current_value - entry_cost
```

### Fixed (Option A) - 57 lines
```
Line 68-77: __post_init__ uses qty * price (no minus)
Line 79-99: close uses qty * (exit - entry) per leg
Line 101-114: mark_to_market uses qty * (current - entry)
```

**Diff size:** ~10 lines changed, logic completely replaced

## Validation Checklist

After applying fix:

- [ ] Code compiles without syntax errors
- [ ] All imports still work
- [ ] `test_long_straddle()` returns +profit
- [ ] `test_short_strangle()` returns +profit
- [ ] `test_call_spread()` returns correct sign
- [ ] Equity curve is monotonically increasing (for winning strategy)
- [ ] Sharpe ratio is positive (for winning strategy)
- [ ] Win rate increases (if bugs were making it appear worse)
- [ ] Day 1-6 validation all pass
- [ ] Manual spot check of 20 trades all correct

## Timeline

- **Fix application:** 30 minutes
- **Testing:** 1 hour
- **Validation:** 30 minutes
- **Documentation:** 30 minutes
- **Total:** ~2.5 hours

## Risk Assessment

**Risk of fixing:** LOW
- Bug is in isolated P&L calculation
- Fix is straightforward and clear
- Can be tested immediately
- Easy to revert if needed

**Risk of NOT fixing:** EXTREME
- All backtest results are inverted
- Real capital will be lost
- Strategy rankings are backwards

## Recommendation

**APPLY FIX IMMEDIATELY**

This is a show-stopper bug. Do not proceed with any trading (paper or real) until this is fixed and thoroughly validated.

---

**Document:** Fix Guide for BUG-001
**Created:** 2025-11-13
**Status:** READY TO IMPLEMENT
