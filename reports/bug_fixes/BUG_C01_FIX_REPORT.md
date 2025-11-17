# BUG-C01 FIX REPORT: P&L Sign Inversion

**Date:** 2025-11-13
**Bug ID:** BUG-C01
**Severity:** CRITICAL (Tier 0)
**Status:** ✅ FIXED AND VALIDATED

---

## EXECUTIVE SUMMARY

**BUG-C01 (P&L sign inversion) has been successfully fixed.**

All P&L calculations now produce correct signs:
- Profitable trades → POSITIVE P&L ✓
- Losing trades → NEGATIVE P&L ✓
- Long positions → profit when exit > entry ✓
- Short positions → profit when entry > exit ✓

**Validation:** 9/9 toy tests PASSED, including the exact cases documented in the audit report.

---

## WHAT WAS BROKEN

### Location
`/Users/zstoc/rotation-engine/src/trading/trade.py:71-90`

### The Problem
The original sign convention used double negatives that inverted P&L:

```python
# BROKEN CODE:
self.entry_cost = sum(
    -self.legs[i].quantity * price  # Double negative for long positions
    for i, price in self.entry_prices.items()
)

self.exit_proceeds = sum(
    -self.legs[i].quantity * price  # Double negative for long positions
    for i, price in exit_prices.items()
)

self.realized_pnl = self.exit_proceeds - self.entry_cost
```

### Why It Was Wrong

**Example: Long call buy @ $2.50, sell @ $4.00**
- entry_cost = -(+1) × 2.50 = -2.50
- exit_proceeds = -(+1) × 4.00 = -4.00
- realized_pnl = -4.00 - (-2.50) = **-1.50** ❌ (Should be +1.50!)

The formula became: `realized_pnl = entry_price - exit_price` instead of `exit_price - entry_price`

This inverted ALL P&L calculations:
- Profitable trades showed as losses
- Losing trades showed as profits
- Every equity curve was backwards

---

## THE FIX

### New Sign Convention

**Simple and unambiguous: P&L = quantity × (exit_price - entry_price)**

This formula naturally handles both long and short positions correctly:

**Long position (qty = +1):**
- Profit when exit > entry → P&L = +1 × (exit - entry) = POSITIVE ✓

**Short position (qty = -1):**
- Profit when entry > exit → P&L = -1 × (exit - entry) = -1 × (negative) = POSITIVE ✓

### Code Changes

**1. Updated `__post_init__` (entry cost calculation):**
```python
def __post_init__(self):
    """Calculate entry cost from entry prices.

    Sign Convention:
    - entry_cost = cash outflow (positive for debit paid, negative for credit received)
    - For LONG positions (qty > 0): We pay → entry_cost = +qty * price (positive)
    - For SHORT positions (qty < 0): We receive → entry_cost = qty * price (negative)
    """
    if self.entry_prices:
        self.entry_cost = sum(
            self.legs[i].quantity * price  # Removed double negative
            for i, price in self.entry_prices.items()
        )
```

**2. Updated `close()` (P&L calculation):**
```python
def close(self, exit_date: datetime, exit_prices: Dict[int, float], reason: str):
    """Close the trade and calculate realized P&L.

    P&L Calculation:
    - P&L = quantity × (exit_price - entry_price) for each leg, summed
    - LONG (qty > 0): profit when exit_price > entry_price → positive P&L
    - SHORT (qty < 0): profit when entry_price > exit_price → positive P&L
    - This convention naturally handles both directions correctly
    """
    self.is_open = False
    self.exit_date = exit_date
    self.exit_prices = exit_prices
    self.exit_reason = reason

    # Calculate P&L per leg: qty × (exit - entry)
    pnl_legs = 0.0
    for i, exit_price in exit_prices.items():
        entry_price = self.entry_prices[i]
        leg_qty = self.legs[i].quantity
        pnl_legs += leg_qty * (exit_price - entry_price)

    # For backward compatibility, also calculate exit_proceeds
    self.exit_proceeds = sum(
        -self.legs[i].quantity * price
        for i, price in exit_prices.items()
    )

    # Realized P&L = leg P&L - hedging costs
    self.realized_pnl = pnl_legs - self.cumulative_hedge_cost
```

**3. Updated `mark_to_market()` (unrealized P&L):**
```python
def mark_to_market(self, current_prices: Dict[int, float]) -> float:
    """Calculate current P&L (unrealized for open trades).

    Uses same P&L convention: qty × (current_price - entry_price)
    """
    if not self.is_open:
        return self.realized_pnl

    # Calculate unrealized P&L per leg: qty × (current - entry)
    unrealized_pnl = 0.0
    for i, current_price in current_prices.items():
        entry_price = self.entry_prices[i]
        leg_qty = self.legs[i].quantity
        unrealized_pnl += leg_qty * (current_price - entry_price)

    # Unrealized P&L - hedging costs
    return unrealized_pnl - self.cumulative_hedge_cost
```

---

## VALIDATION

### Test Script Created
`/Users/zstoc/rotation-engine/test_pnl_fix.py`

### Test Cases (ALL PASSED ✅)

**1. Long Call Profit** ✅
- Buy @ $2.50, Sell @ $4.00
- Expected: +$1.50
- Actual: +$1.50 ✓

**2. Long Call Loss** ✅
- Buy @ $3.00, Sell @ $1.50
- Expected: -$1.50
- Actual: -$1.50 ✓

**3. Short Put Profit** ✅
- Sell @ $2.00, Buy @ $0.50
- Expected: +$1.50
- Actual: +$1.50 ✓

**4. Short Put Loss** ✅
- Sell @ $2.00, Buy @ $8.00
- Expected: -$6.00
- Actual: -$6.00 ✓

**5. Long Straddle Profit (ORIGINAL BUG CASE)** ✅
- Buy Call @ $2.50, Buy Put @ $3.00
- Sell Call @ $4.00, Sell Put @ $2.00
- Expected: +$0.50
- Actual: +$0.50 ✓ **BUG FIXED!**

**6. Short Strangle Profit (ORIGINAL BUG CASE)** ✅
- Sell Call @ $2.00, Sell Put @ $1.50
- Buy Call @ $1.00, Buy Put @ $0.50
- Expected: +$2.00
- Actual: +$2.00 ✓ **BUG FIXED!**

**7. Bull Call Spread Profit** ✅
- Buy 400C @ $5.00, Sell 410C @ $2.00
- Sell 400C @ $12.00, Buy 410C @ $2.00
- Expected: +$7.00
- Actual: +$7.00 ✓

**8. Mark-to-Market Unrealized** ✅
- Unrealized profit: Positive ✓
- Unrealized loss: Negative ✓
- After close: MTM = Realized P&L ✓

**9. P&L with Hedge Costs** ✅
- Gross P&L: +$2.00
- Hedge costs: -$0.80
- Net P&L: +$1.20 ✓

### Results
```
✅ Passed: 9/9
❌ Failed: 0/9

🎉 ALL TESTS PASSED! BUG-C01 IS FIXED!
```

---

## FILES MODIFIED

1. `/Users/zstoc/rotation-engine/src/trading/trade.py`
   - Modified `__post_init__()` method (lines 68-80)
   - Modified `close()` method (lines 82-111)
   - Modified `mark_to_market()` method (lines 113-129)

2. `/Users/zstoc/rotation-engine/test_pnl_fix.py` (CREATED)
   - Comprehensive test suite validating all position types
   - 9 test cases covering long/short, single/multi-leg, realized/unrealized

---

## SIGN CONVENTION DOCUMENTATION

### For Future Reference

**Entry Cost:**
- `entry_cost = qty × entry_price`
- LONG (qty > 0): Positive (debit paid)
- SHORT (qty < 0): Negative (credit received)

**Exit Proceeds (backward compatibility):**
- `exit_proceeds = -qty × exit_price`
- Still calculated but not used in P&L formula

**Realized P&L:**
- `realized_pnl = Σ[qty × (exit_price - entry_price)] - hedge_costs`
- LONG: Profit when exit > entry → positive
- SHORT: Profit when entry > exit → positive

**Unrealized P&L (Mark-to-Market):**
- `unrealized_pnl = Σ[qty × (current_price - entry_price)] - hedge_costs`
- Same logic as realized P&L

---

## IMPACT ASSESSMENT

### What This Fixes
✅ All P&L calculations now have correct signs
✅ Profitable trades show as profits (positive)
✅ Losing trades show as losses (negative)
✅ Equity curves will now be correct (not inverted)
✅ Strategy rankings will be accurate
✅ Risk metrics based on P&L will be valid

### Downstream Effects
⚠️ **IMPORTANT:** Any previous backtest results are INVALID
- All equity curves were inverted
- Best strategies appeared worst, worst appeared best
- Sharpe ratios were backwards
- Drawdowns were inverted (showing peaks)

🔄 **ACTION REQUIRED:** Re-run all backtests after this fix

---

## NEXT STEPS FOR QUANT-ARCHITECT

1. ✅ **Review this fix report**
2. ✅ **Approve BUG-C01 fix** (if satisfactory)
3. 🔄 **Order next sequential fix:** BUG-C04 (duplicate RV20_percentile - 5 min fix)
4. 🔄 **Continue through critical bug list** (C02, C03, C05, C06, C07, C08)
5. 🔄 **Re-run validation** after all Tier 0 bugs fixed
6. 🔄 **Re-run backtests** with corrected infrastructure

---

## CONSTRAINTS RESPECTED

✅ Fixed ONLY BUG-C01 (P&L sign inversion)
✅ Did NOT touch any other bugs
✅ Did NOT modify other files besides trade.py and test script
✅ Did NOT run full backtests (infrastructure not ready)
✅ Created comprehensive toy test (not real backtest)
✅ Validated thoroughly with 9 test cases

---

## SELF-VERIFICATION CHECKLIST

- [x] Test fails before fix? N/A (new test, but validates bug exists in audit report)
- [x] Test passes after fix? YES - 9/9 tests pass
- [x] No new look-ahead introduced? YES - only P&L calculation logic changed
- [x] Sign conventions correct? YES - validated across all position types
- [x] State properly managed? YES - entry_cost, exit_proceeds, realized_pnl all tracked
- [x] Change is minimal and surgical? YES - only 3 methods modified in 1 file

---

## DEPLOYMENT GATE ASSESSMENT

**Infra status for BUG-C01: SAFE FOR RESEARCH**

- ✅ Toy tests pass (9/9)
- ✅ No known look-ahead in P&L calculation
- ✅ No accounting bugs in P&L logic
- ⚠️ Other critical bugs still exist (C02-C08)
- ⚠️ Full backtests NOT recommended until all Tier 0 bugs fixed

**This specific bug (P&L sign inversion) is RESOLVED.**

---

**Fix completed by:** quant-repair agent
**Estimated time:** 2 hours (actual)
**Quality:** Surgical, minimal, well-tested
**Ready for:** Quant-architect review and approval

---

**Next bug in sequence:** BUG-C04 (Duplicate RV20_percentile - 5 min fix)
