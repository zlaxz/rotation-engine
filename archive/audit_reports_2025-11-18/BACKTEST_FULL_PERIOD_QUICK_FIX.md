# QUICK FIX REFERENCE - backtest_full_period.py

## STOP: DO NOT RUN THIS SCRIPT YET

This script has **9 critical bugs** that will either crash it or produce invalid results.

---

## TIER 0 BUGS (Backtest Invalid)

### BUG-001: Wrong Period (BLOCKS EVERYTHING)
**Location:** Line 45
```python
# WRONG (current):
PERIOD_END = date(2024, 12, 31)  # ← 4 years of data!

# CORRECT:
PERIOD_END = date(2021, 12, 31)  # ← Train period only
```

**Why:** Script header says "2020-2021 ONLY" but uses "2020-2024" → contaminated results

---

### BUG-002: Script Will Crash (BLOCKS EXECUTION)
**Location:** Line 486
```python
# WRONG (current):
print(f"  Avg % of Peak Captured: {summary['avg_pct_captured']:.1f}%")

# CORRECT:
print(f"  Agg % of Peak Captured: {summary['aggregate_pct_captured']:.1f}%")
```

**Why:** Dictionary key doesn't exist. Script crashes with `KeyError`

---

## TIER 1 BUGS (Calculation Errors)

### BUG-003: Data Shifting Ambiguity
**Location:** Lines 108-112

Check if slopes are calculated after MA is shifted.
**Result:** Potentially includes future data in entry conditions.
**Action:** Trace through entry condition for each profile to verify.

---

## TIER 2 BUGS (Execution Unrealism)

### BUG-004: No Entry Slippage
- Entry uses exact `open` price with NO spread
- Real cost: +$0.10-$0.30 per contract
- **Fix:** Add bid-ask adjustment

### BUG-005: Strike/Expiry May Not Exist
- Code assumes strike is available at rounded price
- No liquidity check
- **Fix:** Verify strike/expiry in polygon data

### BUG-006: No Exit Slippage
- Exit uses exact bid price with NO slippage
- Real cost: -$0.10-$0.35 per contract
- **Fix:** Reduce exit prices by slippage amount

### BUG-007: No Open Interest Check
- Trades 1 contract without verifying liquidity
- **Fix:** Check OI > 10 before entry

---

## BEFORE NEXT SESSION

- [ ] Fix BUG-001 (period boundaries)
- [ ] Fix BUG-002 (metrics key)
- [ ] Verify BUG-003 (data shifting)
- [ ] Consider BUG-004 (entry slippage)
- [ ] Consider BUG-006 (exit slippage)

**TL;DR:** Fix the two TIER 0 bugs (1 minute + 2 minutes = 3 minutes total), then you can test infrastructure. Leave execution realism fixes for later if you want.

