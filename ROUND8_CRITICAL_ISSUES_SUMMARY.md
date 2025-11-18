# ROUND 8 - CRITICAL ISSUES SUMMARY

**Status:** DEPLOYMENT BLOCKED
**Bugs Found:** 4 CRITICAL
**Date:** 2025-11-18

---

## QUICK REFERENCE: 4 BUGS TO FIX

### BUG #1: Vega 100x Overstatement
- **File:** `src/pricing/greeks.py:200`
- **Issue:** Vega returned as 52.5, multiplied by 100 again = 5250 (100x too large)
- **Fix:** Scale vega by 0.01 in greeks.py line 200, OR remove multiplier from trade.py
- **Time:** 10 min
- **Impact:** Greeks hedging broken

### BUG #2: Exit Slippage Not Sized
- **File:** `src/trading/simulator.py:509-514`
- **Issue:** Slippage calculated on quantity=1 (default) instead of actual position size
- **Root:** apply_spread_to_price doesn't pass quantity to get_execution_price
- **Fix:** Add quantity parameter to line 260-262
- **Time:** 5 min
- **Impact:** Exit prices 10x-100x too good

### BUG #3: Missing Quantity Parameter
- **File:** `src/trading/execution.py:260-262`
- **Issue:** get_execution_price called without quantity parameter (uses default=1)
- **Fix:** Change line 260-262 to pass `quantity=quantity`
- **Time:** 2 min
- **Impact:** All slippage calculations wrong

### BUG #4: Sharpe First Return Misaligned
- **File:** `src/analysis/metrics.py:119-126`
- **Issue:** pct_change() concat might duplicate/misalign first return
- **Fix:** Verify index alignment, potentially rewrite concat logic
- **Time:** 30 min
- **Impact:** Sharpe ratio potentially 5-10% off

---

## FIX PRIORITY ORDER

1. **Bug #3 (2 min)** → fixes #2 automatically
2. **Bug #1 (10 min)** → Greeks working
3. **Bug #4 (30 min)** → Metrics reliable
4. **Re-run backtest** (see P&L change direction)

**Total Time: ~45 minutes**

---

## CRITICAL: BUG #3 EXAMPLE FIX

**File:** `src/trading/execution.py` lines 227-262

**Current (WRONG):**
```python
def apply_spread_to_price(self, mid_price, quantity, moneyness, dte, vix_level=20.0, is_strangle=False) -> float:
    side = 'buy' if quantity > 0 else 'sell'
    return self.get_execution_price(
        mid_price, side, moneyness, dte, vix_level, is_strangle
        # Missing quantity!
    )
```

**Fixed (RIGHT):**
```python
def apply_spread_to_price(self, mid_price, quantity, moneyness, dte, vix_level=20.0, is_strangle=False) -> float:
    side = 'buy' if quantity > 0 else 'sell'
    return self.get_execution_price(
        mid_price, side, moneyness, dte, vix_level, is_strangle, quantity
        # Add quantity parameter
    )
```

---

## CRITICAL: BUG #1 EXAMPLE FIX

**File:** `src/pricing/greeks.py` line 200

**Current (WRONG):**
```python
return S * norm.pdf(d1) * np.sqrt(T)  # Line 200
```

**Fixed (RIGHT - Option A - Scale in greeks.py):**
```python
# Vega per 1% change in volatility
return S * norm.pdf(d1) * np.sqrt(T) * 0.01  # Scale by 0.01
```

**OR Option B - Remove multiplier from trade.py line 343:**
```python
# In trade.py, change line 343:
# self.net_vega += leg.quantity * leg_greeks['vega'] * contract_multiplier
# To:
self.net_vega += leg.quantity * leg_greeks['vega']  # Don't multiply - vega already scaled
```

**Recommendation:** Option A (scale in greeks.py) - cleaner, documents intent

---

## IMPACT OF BUGS

### If Unfixed:
1. Greeks hedging wrong by 100x → position risks blown up
2. Exit costs massively understated → P&L inflated
3. Sharpe ratio unreliable → metrics questionable
4. Can't deploy to live

### After Fixes:
1. P&L likely decreases significantly (higher costs revealed)
2. Sharpe ratio potentially drops
3. Greeks hedging becomes reliable
4. Must implement train/val/test splits before deploying

---

## NEXT STEPS

1. **Fix Bugs #1-4** (45 min)
2. **Re-run backtest** (observe P&L change)
3. **Implement train/val/test methodology** (2-3 hours)
4. **Run fresh audit on train period**
5. **Test on validation period**
6. **Deploy only if validation passes**

---

**See ROUND8_FINAL_QUALITY_GATE_AUDIT.md for complete details**
