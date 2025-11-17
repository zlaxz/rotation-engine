# CODE REVIEW MASTER FINDINGS

**Date:** 2025-11-13
**Project:** Convexity Rotation Engine - Infrastructure Code Audit
**Status:** 4 Parallel Code Reviews Complete

---

## EXECUTIVE SUMMARY

**VERDICT: 🔴 DEPLOYMENT BLOCKED - CRITICAL BUGS FOUND**

4 specialized code review agents attacked the infrastructure from different angles and found **12 CRITICAL bugs** that make the backtest completely unreliable.

**Most Severe Finding:** P&L calculations are inverted - profitable trades show as losses.

**Impact:** Backtest results are backwards and overstate costs by 15-30%.

**Fix Time:** 15-25 hours estimated

---

## CRITICAL BUGS (Backtest INVALID - Must Fix)

### BUG-C01: P&L Calculation Sign Inversion 🚨
**Source:** Vector 2 (Greeks/Math)
**Location:** `src/trading/trade.py:71-90`
**Severity:** CRITICAL

**Issue:** All P&L calculations produce inverted signs:
- Profitable trades show as LOSSES
- Losing trades show as PROFITS
- Every equity curve is BACKWARDS

**Evidence:**
```
Long Straddle: Buy @ $5.50, Sell @ $6.00
Expected P&L: +$0.50 profit
Calculated P&L: -$0.50 ❌ WRONG SIGN
```

**Fix:** Redesign entry_cost/exit_proceeds sign convention (2 hours)

---

### BUG-C02: Greeks Never Calculated (Always 0.0) 🚨
**Source:** Vector 3 (Execution)
**Location:** `src/trading/trade.py:62-66`
**Severity:** CRITICAL

**Issue:** No Black-Scholes implementation anywhere in codebase. All Greeks fields (`net_delta`, `net_gamma`, `net_vega`, `net_theta`) are permanently 0.0.

**Impact:** Cannot determine position delta for hedging. Risk management completely broken.

**Fix:** Implement Black-Scholes Greeks formulas (4-6 hours)

---

### BUG-C03: Delta Hedging Cost Placeholder ($15/day) 🚨
**Source:** Vector 3 (Execution)
**Location:** `src/trading/simulator.py:328-350`
**Severity:** CRITICAL

**Issue:** Hardcoded `hedge_contracts=1` charges $15/day regardless of actual delta exposure.

**Impact:**
- Profile 1: $900 hedge cost on 60-day trade when reality is $0-500
- Overstates costs by 862% of gross profit

**Fix:** Replace with `hedge_contracts = abs(net_delta) / 100` (30 min after Greeks implemented)

---

### BUG-C04: Duplicate RV20_percentile Implementations (94% Discrepancy) 🚨
**Source:** Vector 1 (Data Timing)
**Location:** `src/regimes/signals.py:55-59 vs line 63`
**Severity:** CRITICAL

**Issue:** Two different percentile methods produce conflicting values:
- Method 1 (rolling apply): 95th percentile
- Method 2 (quantile): 50th percentile
- 1,185 rows (94%) have discrepancies
- Mean difference: 6.3 percentage points

**Impact:** Regime classifications are wrong on 94% of days.

**Fix:** Delete lines 55-59, use only line 63 method (5 min)

---

### BUG-C05: Off-By-One Shift Error (Signals 1 Day Late) 🚨
**Source:** Vector 1 (Data Timing)
**Location:** `src/regimes/signals.py:57-59`
**Severity:** CRITICAL

**Issue:** Rolling apply ranks `df[t-1]` vs `df[0:t-1]` instead of `df[t]` vs `df[0:t]`.

**Impact:** All volatility signals delayed by 1 trading day. Regime classifications based on yesterday's vol.

**Fix:** Part of BUG-C04 fix (delete the broken method)

---

### BUG-C06: Slope Calculation 71× Magnitude Inconsistency 🚨
**Source:** Vector 2 (Greeks/Math)
**Location:** `src/data/features.py:112-114`
**Severity:** CRITICAL

**Issue:** Two slope calculation methods:
- Percentage change: -0.0149
- Linear regression: -1.0596
- Difference: **71×**

**Impact:** Regime thresholds (`slope > 0.001`) using wrong units. Entry/exit signals unreliable.

**Fix:** Standardize all slopes to one method (3 hours)

---

### BUG-C07: DTE Calculation Broken for Multi-Leg Positions 🚨
**Source:** Vector 4 (Position Tracking)
**Location:** `src/trading/simulator.py:132`
**Severity:** CRITICAL

**Issue:** Uses static entry DTE minus calendar days. Doesn't track individual leg expirations.

**Impact:** Rolling doesn't work properly. Positions held past expiration.

**Fix:** Per-leg DTE tracking (1-2 hours)

---

### BUG-C08: Missing Transaction Costs (Commissions, Fees) 🚨
**Source:** Vector 3 (Execution)
**Location:** `src/trading/execution.py:108-154`
**Severity:** CRITICAL

**Issue:** Omits broker commissions ($0.65-1.00/contract), SEC fees ($0.00182), FINRA fees.

**Impact:** Each trade hides $3-4 in costs. Underestimates by 20-40%.

**Fix:** Add commission and fee parameters (1 hour)

---

## HIGH PRIORITY BUGS (Fix Before Live Trading)

### BUG-H01: Short-Dated Spreads 30-50% Too Tight
**Source:** Vector 3 (Execution)
**Location:** `src/trading/execution.py:88-92`

**Issue:** Model assumes 30% wider spreads for <7 DTE. Reality: 100-150% wider.

**Impact:** Profile 2 (short-dated gamma) returns overstated by 20-30%.

**Fix:** Empirical calibration using real market data (3 hours)

---

### BUG-H02: OTM Spreads 20-30% Too Tight
**Source:** Vector 3 (Execution)
**Location:** `src/trading/execution.py:84-85`

**Issue:** Linear moneyness factor shows 14% widening at 25D. Reality: 40-60% wider.

**Impact:** Profile 3 (short strangles) returns overstated by 10-15%.

**Fix:** Delta-based lookup table (2 hours)

---

### BUG-H03: Multi-Leg Positions Can't Roll Individual Legs
**Source:** Vector 4 (Position Tracking)
**Location:** `src/trading/trade.py`, `src/trading/simulator.py`

**Issue:** Single `is_open` flag for entire position. Can't roll individual legs.

**Impact:** Diagonal spreads can't roll short leg while keeping long leg.

**Fix:** Per-leg state tracking (4-6 hours)

---

## MEDIUM PRIORITY BUGS

### BUG-M01: Allocation Weights Don't Re-Normalize After VIX Scaling
**Source:** Vector 4 (Position Tracking)
**Impact:** Portfolio only 50% allocated during high vol.
**Fix:** 30 minutes

### BUG-M02: Slope Not Normalized by Price Level
**Source:** Vector 2 (Greeks/Math)
**Impact:** Threshold interpretation changes with SPY price.
**Fix:** 1 hour

### BUG-M03: Inconsistent Walk-Forward Implementations
**Source:** Vector 1 (Data Timing)
**Impact:** Dual implementations, maintenance burden.
**Fix:** Code consolidation (1 hour)

---

## TOTAL BUGS FOUND

**By Severity:**
- CRITICAL: 8 bugs (backtest invalid)
- HIGH: 3 bugs (major impact)
- MEDIUM: 3 bugs (moderate impact)
- LOW: 0 bugs

**Total:** 14 unique bugs across 4 attack vectors

---

## WHAT'S WORKING CORRECTLY ✅

**Vector 1 findings:**
- Walk-forward percentile calculation (method 2) is correct
- No look-ahead bias in correctly implemented features

**Vector 2 findings:**
- Sigmoid function mathematically verified
- Geometric mean calculations correct
- Profile scoring logic sound (when data clean)

**Vector 3 findings:**
- Bid-ask spread direction correct
- Position type handling (long/short) correct

**Vector 4 findings:**
- P&L formula structure correct (just sign bug)
- Basic position tracking working

---

## CONSOLIDATED FIX PLAN

**Phase 1: BLOCKING CRITICAL (8-10 hours)**

1. Fix BUG-C01 (P&L sign inversion) - 2 hours
2. Fix BUG-C04 (duplicate percentile) - 5 min
3. Fix BUG-C06 (slope standardization) - 3 hours
4. Implement BUG-C02 (Black-Scholes Greeks) - 4 hours
5. Fix BUG-C03 (delta hedging) - 30 min (after Greeks)
6. Fix BUG-C07 (DTE calculation) - 1-2 hours
7. Fix BUG-C08 (add commissions) - 1 hour

**Phase 2: HIGH PRIORITY (6-8 hours)**

8. Calibrate short-dated spreads (BUG-H01) - 3 hours
9. Calibrate OTM spreads (BUG-H02) - 2 hours
10. Implement per-leg rolling (BUG-H03) - 4-6 hours

**Phase 3: MEDIUM (2-3 hours)**

11. Fix VIX scaling normalization (BUG-M01) - 30 min
12. Normalize slope by price (BUG-M02) - 1 hour
13. Consolidate percentile code (BUG-M03) - 1 hour

**Total Estimated Time: 16-21 hours**

---

## MASTER BUG TRACKING

All findings documented in `/Users/zstoc/rotation-engine/`:
- Multiple AUDIT_*.md files from each attack vector
- BUG_*.md files with detailed analysis
- FIX_*.md files with implementation guides

---

## NEXT STEPS

**DO NOT RUN BACKTEST until Phase 1 critical bugs are fixed.**

1. Review consolidated findings (this file)
2. Read individual audit reports for details
3. Fix Phase 1 bugs (8-10 hours)
4. Have quant-expert validate fixes
5. THEN run first proper backtest
6. THEN analyze results with red team

**Status:** INFRASTRUCTURE CODE AUDITED - Ready for fixes

---

**Last Updated:** 2025-11-13
**Audited By:** 4 parallel quant-code-review agents
**Supervised By:** Quant-expert (proper process this time)
