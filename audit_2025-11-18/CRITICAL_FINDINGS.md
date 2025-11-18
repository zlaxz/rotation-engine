# CRITICAL FINDINGS - DeepSeek Swarm Audit
**Date:** 2025-11-18
**Method:** 10 DeepSeek Reasoner agents analyzing COMPLETE files (no filtering)
**Cost:** ~$0.10 total (vs $1.20 with Haiku)
**Status:** 🔴 DO NOT DEPLOY - Critical bugs found

---

## TOP 5 CRITICAL BUGS

### 1. SHARPE RATIO CALCULATION FUNDAMENTALLY BROKEN (CRITICAL)
**Agent:** #9 (Metrics)
**File:** `src/analysis/metrics.py:83-108`
**Bug:** P&L vs Returns confusion - treating dollar P&L as returns
**Impact:** Sharpe of 0.0026 is MEANINGLESS - explains why results look like noise
**Evidence:** Current Sharpe 0.0026 ≈ zero (should be -3.29 or positive if working)
**Fix:** Convert P&L to returns before calculating Sharpe

```python
# CURRENT (WRONG):
def sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    excess_returns = returns - (risk_free_rate / self.annual_factor)  # Assumes returns
    return (excess_returns.mean() / excess_returns.std()) * np.sqrt(self.annual_factor)

# CORRECT:
def sharpe_ratio(self, pnl: pd.Series, risk_free_rate: float = 0.0) -> float:
    # Convert P&L to returns first
    cumulative = pnl.cumsum()
    returns = cumulative.pct_change().dropna()
    excess_returns = returns - (risk_free_rate / self.annual_factor)
    if excess_returns.std() == 0:
        return 0.0
    return (excess_returns.mean() / excess_returns.std()) * np.sqrt(self.annual_factor)
```

**Priority:** #1 - **Explains why ALL performance metrics are garbage**

---

### 2. PROFILE 4 (VANNA) WRONG SIGN + POSSIBLE LOOK-AHEAD (CRITICAL)
**Agent:** #3 (Profiles)
**File:** `src/profiles/detectors.py:212-244`
**Bug:** IV_rank formula has wrong sign, possible look-ahead in calculation
**Impact:** +1094% OOS improvement is impossible without bias
**Evidence:** Suspicious out-of-sample performance that defies statistical logic
**Fix:** Correct sign and validate IV_rank uses only past data

```python
# CURRENT (WRONG SIGN):
factor1 = sigmoid(-df['IV_rank_20'] * 5 + 2.5)  # High when rank near 0

# CORRECT:
factor1 = sigmoid((0.3 - df['IV_rank_20']) * 5)  # High when rank < 0.3
```

**Priority:** #2 - **Explains overfitting symptoms in Profile 4**

---

### 3. PROFILE 3 (CHARM) LOGIC CONTRADICTS DESCRIPTION (CRITICAL)
**Agent:** #3 (Profiles)
**File:** `src/profiles/detectors.py:179-210`
**Bug:** Factor3 uses negative VVIX slope but description says "VVIX declining = positive"
**Impact:** Sign flip in train/test - logic doesn't match stated strategy
**Evidence:** Profile 3 flipped from best to worst between periods
**Fix:** Align formula with description or fix description

---

### 4. CORPORATE ACTIONS NOT HANDLED (CRITICAL)
**Agent:** #1 (Loaders)
**File:** `src/data/loaders.py` (multiple locations)
**Bug:** No split/dividend adjustments for options strikes and prices
**Impact:** Pre-split option prices used with post-split underlying = catastrophic errors
**Fix:** Implement corporate action adjustments using yfinance data

**Priority:** #3 - **Makes ALL historical data unreliable**

---

### 5. DATA ALIGNMENT MISMATCH IN ENGINE (CRITICAL)
**Agent:** #10 (Integration)
**File:** `src/backtest/engine.py`
**Bug:** Profile backtests use `data` while allocations use `data_with_scores`
**Impact:** Date/index misalignment between components = invalid results
**Fix:** Use consistent dataset across all backtest components

**Priority:** #4 - **Integration bug that invalidates portfolio results**

---

## HIGH SEVERITY BUGS

### 6. DELTA HEDGING STILL HAS BUGS (HIGH)
**Agent:** #4 (Simulator)
**File:** `simulator.py:_perform_delta_hedge()`
**Finding:** Agent says direction logic is REVERSED (contradicts previous BUG-004 fix)
**Status:** CONFLICTING - needs manual verification
**Action:** Manually verify hedge direction is correct

### 7. MTM PRICING INCONSISTENCY (HIGH)
**Agent:** #4 (Simulator)
**Bug:** Mark-to-market uses mid prices, entry/exit use bid/ask
**Impact:** Unrealistic P&L smoothing during holding period
**Fix:** Use consistent bid/ask pricing throughout

### 8. PROFILE 2 (SDG) NORMALIZATION BUG (HIGH)
**Agent:** #3 (Profiles)
**Bug:** Raw ret_1d not normalized, move_size calculation wrong
**Fix:** Use `abs(ret_1d)` and normalize properly

### 9. CACHING MEMORY LEAK (HIGH)
**Agent:** #1b (Polygon)
**Bug:** Unlimited cache growth, no eviction policy
**Impact:** Memory leaks in long-running processes
**Fix:** Add cache size limits

### 10. TICKER PARSING BRITTLENESS (HIGH)
**Agent:** #1b (Polygon)
**Bug:** Assumes 3-character underlying (SPY hardcoded)
**Impact:** Breaks on any non-SPY options
**Fix:** Dynamic symbol detection

---

## AGENT STATUS

**Completed (6/10):**
- ✅ Agent 1: loaders.py (14KB output)
- ✅ Agent 1b: polygon_options.py (13KB output)
- ✅ Agent 3: profiles/detectors.py (20KB output)
- ✅ Agent 4: trading/simulator.py (14KB output)
- ✅ Agent 9: analysis/metrics.py (25KB output)
- ✅ Agent 10: backtest/engine.py (16KB output)

**Failed/Timeout (4/10):**
- ❌ Agent 2: regimes/signals.py
- ❌ Agent 5: trading/trade.py
- ❌ Agent 6b: trading/execution.py
- ❌ Agent 8: backtest/rotation.py

---

## IMMEDIATE ACTIONS REQUIRED

1. **Fix Sharpe Ratio** - ALL metrics are broken, can't trust any performance numbers
2. **Fix Profile 4 (VANNA)** - Explains +1094% anomaly
3. **Fix Profile 3 (CHARM)** - Sign flip issue
4. **Verify Delta Hedging** - Agent says it's STILL wrong (conflicts with previous fix)
5. **Add Corporate Actions** - Historical data unreliable without this

---

## VALIDATION REQUIRED

The most CRITICAL finding: **Agent #4 says delta hedging direction is REVERSED**, but we supposedly fixed this in BUG-004. This needs immediate manual verification:

**Check:** `src/trading/simulator.py:734-745`
- Is `hedge_direction = -1` for `net_delta > 0` CORRECT or WRONG?
- Agent says it's reversed, but code comments say it's correct

**Next Step:** I need to manually verify this before proceeding.
