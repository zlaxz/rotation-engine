# CYCLE 1: GREEKS & PRICING AUDIT REPORT

**Auditor:** options-pricing-expert skill
**Date:** 2025-11-14
**Scope:** Greeks calculations, IV handling, options pricing correctness
**Context:** Real capital at risk, Sharpe -3.29 backtest, system built by agents without quant supervision

---

## EXECUTIVE SUMMARY

**VERDICT: 4 CRITICAL, 5 HIGH, 3 MEDIUM issues found**

**CRITICAL FINDING:** Profiles 3 and 4 claim to trade "Charm" and "Vanna" but **these Greeks are NOT IMPLEMENTED**. Second-order Greeks calculations are completely missing.

**Greeks calculations (Delta, Gamma, Vega, Theta) are mathematically correct** but:
- Missing second-order Greeks (Charm, Vanna) that Profiles 3 & 4 require
- No rho calculation (low priority for SPY but missing)
- No dividend adjustments (SPY pays dividends - Black-Scholes assumes zero)
- IV handling uses proxy (RV × 1.2) not real IV from Polygon data
- Greeks calculated at entry but never recalculated during position lifecycle

**This is NOT a minor issue. Two profiles are trading on Greek exposures that don't exist in the code.**

---

## CRITICAL ISSUES (Fix Before Any Live Trading)

### CRITICAL-1: Second-Order Greeks Missing (Charm, Vanna)

**File:** `src/pricing/greeks.py`
**Lines:** N/A (not implemented)

**Problem:**
- Profile 3 is called "Charm/Decay Dominance" (line 2 of `profile_3.py`)
- Profile 4 is called "Vanna Convexity" (line 2 of `profile_4.py`)
- **Neither Charm nor Vanna calculations exist anywhere in the codebase**

**Charm = dDelta/dTime** (rate of change of delta with respect to time)
```
Charm = -n'(d1) * (2*r*T - d2*sigma*sqrt(T)) / (2*T*sigma*sqrt(T)) - r*e^(-r*T)*N(d2)  [for calls]
```

**Vanna = dDelta/dVol = dVega/dSpot** (sensitivity of delta to volatility changes)
```
Vanna = -n(d1) * d2 / sigma
```

**Impact:**
- Profiles 3 & 4 are trading WITHOUT the Greek exposures they claim to target
- Profile 3 shorts strangles expecting charm decay but never measures charm
- Profile 4 trades call diagonals for vanna convexity but never calculates vanna
- Backtest results for these profiles are unreliable (not measuring what matters)

**Evidence:**
```bash
$ grep -r "charm" src/pricing/
# No results - charm calculation doesn't exist

$ grep -r "vanna" src/pricing/
# No results - vanna calculation doesn't exist
```

**Fix Required:**
1. Implement `calculate_charm()` in `greeks.py`
2. Implement `calculate_vanna()` in `greeks.py`
3. Add to `calculate_all_greeks()` return dict
4. Update `Trade.calculate_greeks()` to track net_charm and net_vanna
5. Update Profile 3 & 4 entry logic to actually use these Greeks
6. Add unit tests comparing to known benchmark values

**Severity:** CRITICAL
**Blocks:** Production deployment of Profiles 3 & 4

---

### CRITICAL-2: IV Proxy Instead of Real Implied Volatility

**File:** `src/trading/simulator.py`
**Lines:** 151, 655

**Problem:**
System uses RV × 1.2 proxy for IV instead of extracting real IV from Polygon options data:

```python
# Line 151:
vix_proxy = get_vix_proxy(row.get('RV20', 0.20))

# Line 655:
vix_proxy = get_vix_proxy(row.get('RV20', 0.20))

# execution.py:258-274
def get_vix_proxy(rv_20: float) -> float:
    return rv_20 * 100 * 1.2  # RV to IV with 20% premium
```

**Why This is Wrong:**
- Real Polygon data contains actual bid/ask prices
- Can back out implied volatility using Black-Scholes solver
- RV × 1.2 is a crude approximation that:
  - Doesn't capture term structure (30D IV ≠ 60D IV)
  - Doesn't capture skew (OTM put IV > ATM IV)
  - Doesn't reflect actual market pricing
  - Can be systematically wrong during stress periods

**Impact:**
- Greeks calculations use wrong volatility → wrong delta, gamma, vega values
- Delta hedging based on wrong Greeks → wrong hedge ratios
- Profile 6 (Vol-of-Vol) depends on IV dynamics but uses proxy IV
- Underestimates/overestimates position risk depending on IV regime

**Example Error:**
During 2020 COVID crash:
- Real VIX: 80+
- RV20 × 1.2: Maybe 35-40
- Greeks calculated with IV=40 when market IV=80 → **delta half of actual**

**Fix Required:**
1. Implement Newton-Raphson IV solver in `greeks.py`
2. Function signature: `solve_implied_vol(market_price, S, K, T, r, option_type)`
3. Extract IV from ATM straddle prices (most liquid)
4. Cache IV by DTE bucket (7D, 30D, 60D, 90D) for efficiency
5. Fallback to RV × 1.2 only if Polygon data missing (rare)
6. Add validation: IV should be in [5%, 150%] range

**Severity:** CRITICAL
**Blocks:** Accurate Greeks, realistic backtesting

---

### CRITICAL-3: No Dividend Adjustment (SPY Pays ~1.5% Annually)

**File:** `src/pricing/greeks.py`
**Lines:** 10-14 (documentation says "No dividends")

**Problem:**
Black-Scholes implementation assumes zero dividends:

```python
# Line 10-14 (documentation):
"""
Assumptions:
- European-style options (no early exercise)
- No dividends  # <--- WRONG FOR SPY
- Constant risk-free rate and volatility
"""
```

**SPY Reality:**
- Pays dividends quarterly (~$1.50/share annually)
- Dividend yield ~1.4-1.6%
- Dividends reduce call values, increase put values
- Ex-dividend dates cause discrete delta jumps

**Impact:**
- Call deltas overestimated (should be discounted by dividend yield)
- Put deltas underestimated
- Long calls over-hedged, short puts under-hedged
- Magnitude: ~1.5% error on delta (5% on ATM straddle delta)

**Example:**
- ATM call, 60 DTE, no dividends: delta = 0.50
- ATM call, 60 DTE, q=1.5%: delta = 0.48 (2% lower)
- Over 100 contracts: delta error = 200 shares (4 ES contracts)

**Fix Required:**
1. Add dividend yield parameter to Black-Scholes functions:
   ```python
   def calculate_delta(S, K, T, r, q, sigma, option_type):
       # q = continuous dividend yield
       d1 = (np.log(S/K) + (r - q + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
       if option_type == 'call':
           return np.exp(-q*T) * norm.cdf(d1)
   ```
2. Use q = 0.015 (1.5% annual) for SPY
3. Adjust all Greeks formulas for dividend yield
4. Update tests to include dividend cases

**Severity:** CRITICAL (for accurate hedging)
**Blocks:** Precise delta hedging, call/put parity

---

### CRITICAL-4: Greeks Never Recalculated During Position Lifecycle

**File:** `src/trading/simulator.py`
**Lines:** 177-182 (entry only), 657-662 (hedge recalc only)

**Problem:**
Greeks calculated at entry and then never updated except during delta hedging:

```python
# Line 177-182: Calculate Greeks at entry
current_trade.calculate_greeks(
    underlying_price=spot,
    current_date=current_date,
    implied_vol=vix_proxy,
    risk_free_rate=0.05
)

# Line 657-662: Recalculate ONLY during delta hedging
trade.calculate_greeks(
    underlying_price=spot,
    current_date=current_date,
    implied_vol=vix_proxy,
    risk_free_rate=0.05
)
```

**What's Missing:**
- Greeks are NOT updated during mark-to-market (line 248)
- Greeks are NOT available for P&L attribution analysis
- Profile scoring never checks current Greeks vs target Greeks
- Exit logic can't use "Greeks outside target range" conditions

**Impact:**
- Can't analyze if strategy achieved target Greek exposures
- Can't attribute P&L to delta, gamma, theta, vega components
- Can't implement exit rules like "close if gamma < threshold"
- Profiles 3 & 4 (charm/vanna focused) have no idea if they achieved target

**Fix Required:**
1. Add `Trade.update_greeks()` method
2. Call during mark-to-market (before P&L calc)
3. Store Greeks history: `trade.greeks_history = []`
4. Enable P&L attribution by Greek:
   ```python
   delta_pnl = net_delta * (spot_t - spot_{t-1})
   gamma_pnl = 0.5 * net_gamma * (spot_t - spot_{t-1})**2
   theta_pnl = net_theta * (1/365)  # Daily theta decay
   vega_pnl = net_vega * (IV_t - IV_{t-1}) * 0.01
   ```
5. Add to trade summary: avg_delta, avg_gamma, max_gamma, etc.

**Severity:** CRITICAL (for strategy validation)
**Blocks:** Understanding if strategy actually works

---

## HIGH SEVERITY ISSUES

### HIGH-1: ATM Expiration Delta Discontinuity Wrong

**File:** `src/pricing/greeks.py`
**Lines:** 109-114

**Problem:**
At expiration (T=0), delta calculation assumes discontinuous jump:

```python
# Line 109-114:
if T <= 0:
    # At expiration: ITM = 1/-1, OTM = 0
    if option_type == 'call':
        return 1.0 if S > K else 0.0
    else:
        return -1.0 if S < K else 0.0
```

**What Happens at S = K (ATM at expiration)?**
- Code returns: delta = 0.0 (OTM check fails)
- Reality: ATM options at expiration have undefined delta (Dirac delta function)
- Should return: 0.5 (50% chance of finishing ITM)

**Impact:**
- Short-dated gamma spike trades (Profile 2: 1-3 DTE) affected
- ATM straddles near expiration report delta=0 when should be ~0
- Hedging breaks down in final hours before expiration
- Rare but causes wild delta jumps in last bar

**Fix Required:**
```python
if T <= 0:
    if option_type == 'call':
        if S > K:
            return 1.0
        elif S == K:
            return 0.5  # ATM at expiration
        else:
            return 0.0
    else:  # put
        if S < K:
            return -1.0
        elif S == K:
            return -0.5  # ATM at expiration
        else:
            return 0.0
```

**Severity:** HIGH
**Affects:** Profile 2 (short-dated gamma spike)

---

### HIGH-2: No Greeks Bounds Checking / Numerical Stability

**File:** `src/pricing/greeks.py`
**Lines:** 46-50, 157-158

**Problem:**
No guards against numerical instability in Greeks calculations:

```python
# Line 50: Division by zero possible
return (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
# If T=0 or sigma=0: division by zero

# Line 158: Gamma formula
return norm.pdf(d1) / (S * sigma * np.sqrt(T))
# If S=0 or T=0 or sigma=0: division by zero
```

**Missing Guards:**
- Very low vol (sigma < 0.01): gamma explodes
- Very short DTE (T < 1hr): gamma explodes
- Deep ITM/OTM (|d1| > 6): norm.pdf(d1) ≈ 0 (numerical precision loss)
- Zero spot price (shouldn't happen but no guard)

**Impact:**
- NaN/Inf in Greeks → crashes delta hedging
- Extreme gamma values (>1000) → massive over-hedging
- Silent failures where Greeks are 0.0 when should be small but non-zero

**Fix Required:**
```python
def calculate_gamma(S, K, T, r, sigma):
    if T <= 0:
        return 0.0

    # Guard against extreme parameters
    T = max(T, 1e-4)  # Minimum 1 hour
    sigma = max(sigma, 0.01)  # Minimum 1% vol
    S = max(S, 1.0)  # Minimum $1 spot

    d1 = _calculate_d1(S, K, T, r, sigma)

    # Guard against extreme d1 (numerical precision loss)
    if abs(d1) > 10:
        return 0.0  # Deep ITM/OTM: gamma ≈ 0

    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))

    # Cap gamma at reasonable maximum
    return min(gamma, 10.0)  # Max 10 delta per $1 move
```

**Severity:** HIGH
**Affects:** All profiles (can cause crashes)

---

### HIGH-3: Theta Sign Convention Not Explicit

**File:** `src/pricing/greeks.py`
**Lines:** 209-253

**Problem:**
Theta calculation is correct but sign convention unclear in code:

```python
# Line 215-216 (docs):
"""
Theta is typically negative (options lose value as time passes).
"""
# Docs say "typically negative" but doesn't clarify for short positions
```

**Confusion:**
- Long option: theta < 0 (you lose $X per day)
- Short option: theta > 0 (you gain $X per day)
- Code calculates per-share theta, then multiplies by quantity (line 207)
- Negative quantity (short) × negative theta = positive theta ✅ CORRECT
- But not explicitly documented

**Risk:**
- Future developer might "fix" sign thinking it's wrong
- User might misinterpret theta values in trade summary
- P&L attribution might attribute theta incorrectly

**Fix Required:**
1. Add explicit sign convention documentation:
   ```python
   """
   Theta Sign Convention:
   - Long option: theta < 0 (time decay costs money)
   - Short option: theta > 0 (time decay earns money)
   - Net theta = sum(quantity × theta_per_share)
   - Negative quantity automatically flips sign
   """
   ```
2. Add unit test explicitly checking short option theta > 0

**Severity:** HIGH (documentation/maintenance risk)
**Affects:** All profiles

---

### HIGH-4: Vega Units Confusion (Per 1% vs Per 1 Unit)

**File:** `src/pricing/greeks.py`
**Lines:** 161-198

**Problem:**
Vega calculation is correct but units are confusing:

```python
# Line 172-173 (docs):
"""
Note: Vega is typically quoted per 1% change in volatility.
This function returns vega per 1 unit change (multiply by 0.01 for 1%).
"""

# Line 198:
return S * norm.pdf(d1) * np.sqrt(T)
# This is vega per 1 unit (e.g., 0.30 → 0.31 is 0.01 unit change = 1%)
```

**Confusion:**
- Market convention: vega quoted per 1% vol move (e.g., IV 20% → 21%)
- Code returns: vega per unit move (e.g., sigma 0.20 → 0.21)
- These are THE SAME but documentation is confusing
- User might multiply by 0.01 thinking they need to convert

**Example:**
- ATM 30D call, S=100, sigma=0.30
- Vega = 100 × norm.pdf(d1) × sqrt(30/365) ≈ 11.5
- If IV goes from 30% → 31% (1% move = 0.01 unit move):
  - Code vega: 11.5 × 0.01 = $0.115 per share = $11.50 per contract ✅
  - This is correct but confusing documentation

**Fix Required:**
```python
def calculate_vega(S, K, T, r, sigma):
    """
    Calculate option vega using Black-Scholes model.

    Vega measures option value change for 1% volatility move.

    Vega = S * n(d1) * sqrt(T) / 100

    Units: Dollars per 1% volatility change (e.g., 30% → 31%)
    Example: Vega = 11.5 means option gains $11.50 per contract
             when IV increases from 30% to 31%

    Returns:
    --------
    vega : float
        Vega per 1% volatility move (in dollars per share)
    """
    if T <= 0:
        return 0.0

    d1 = _calculate_d1(S, K, T, r, sigma)
    # Divide by 100 to get vega per 1% move (not per unit move)
    return S * norm.pdf(d1) * np.sqrt(T) / 100
```

**Severity:** HIGH (documentation/user error risk)
**Affects:** All profiles, especially Profile 6 (Vol-of-Vol)

---

### HIGH-5: Greeks Aggregation Doesn't Handle Expired Legs

**File:** `src/trading/trade.py`
**Lines:** 181-207

**Problem:**
Greeks aggregation skips expired legs correctly but doesn't mark them:

```python
# Line 185-189:
time_to_expiry = (expiry - current_dt).days / 365.0

# Skip if expired
if time_to_expiry <= 0:
    continue
```

**What Happens:**
- Expired legs silently skipped (no error, no warning)
- Net Greeks calculated only from active legs ✅ CORRECT
- BUT: No record that some legs expired
- Trade summary shows "2 legs" when only 1 active

**Impact:**
- Profile 4 (call diagonal with rolling short leg) loses track
- Roll logic might try to close already-expired leg
- P&L calculation might double-count expired legs

**Fix Required:**
```python
# In Trade class:
@dataclass
class Trade:
    # ... existing fields ...
    expired_legs: List[int] = None  # Indices of expired legs

    def __post_init__(self):
        if self.expired_legs is None:
            self.expired_legs = []

def calculate_greeks(self, underlying_price, current_date, implied_vol, risk_free_rate):
    # ... existing code ...

    for i, leg in enumerate(self.legs):
        expiry = self._normalize_datetime(leg.expiry)
        time_to_expiry = (expiry - current_dt).days / 365.0

        # Mark expired legs
        if time_to_expiry <= 0:
            if i not in self.expired_legs:
                self.expired_legs.append(i)
            continue

        # ... rest of Greeks calc ...
```

**Severity:** HIGH
**Affects:** Profile 4 (multi-leg with rolling)

---

## MEDIUM SEVERITY ISSUES

### MEDIUM-1: No Rho Calculation (Low Priority for SPY)

**File:** `src/pricing/greeks.py`
**Lines:** N/A (not implemented)

**Problem:**
Rho (sensitivity to interest rate changes) not implemented.

**Impact:**
- Low impact for SPY options (rates relatively stable)
- Matters for LEAPS (long-dated options)
- Profile 1 (60-90 DTE) slightly affected
- If Fed cuts rates 0.50%: ATM call loses ~$0.10/share (1% of premium)

**Fix Required:**
```python
def calculate_rho(S, K, T, r, sigma, option_type):
    """Rho: sensitivity to 1% interest rate change."""
    if T <= 0:
        return 0.0

    d2 = _calculate_d2(S, K, T, r, sigma)

    if option_type == 'call':
        return K * T * np.exp(-r * T) * norm.cdf(d2) / 100
    else:
        return -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
```

**Severity:** MEDIUM (nice-to-have, not critical)

---

### MEDIUM-2: Greeks Not Tested Near American Exercise Boundary

**File:** `tests/test_greeks.py`
**Lines:** All tests use European assumptions

**Problem:**
- SPY options are AMERICAN style (early exercise possible)
- Black-Scholes assumes EUROPEAN (no early exercise)
- Deep ITM puts can be worth more than Black-Scholes (early exercise value)
- Greeks near exercise boundary are wrong

**When It Matters:**
- Deep ITM puts (intrinsic > time value)
- Near expiration + dividends coming (ex-div arbitrage)
- Short puts near expiration (assignment risk)

**Impact:**
- Profile 2 (short straddles) can get assigned early
- Delta estimate wrong for deep ITM short puts
- Rare but can cause unexpected P&L

**Fix Required:**
1. Add warning in docs: "American options - Greeks approximate"
2. Add flag check: if ITM amount > 2× time value, warn about early exercise
3. Consider Barone-Adesi-Whaley approximation for deep ITM

**Severity:** MEDIUM (edge case, rare)

---

### MEDIUM-3: No Greeks Sensitivity Analysis in Tests

**File:** `tests/test_greeks.py`
**Lines:** Tests check absolute values, not sensitivities

**Problem:**
Tests verify Greeks values but not derivatives:
- No test checking dDelta/dSpot ≈ Gamma
- No test checking dDelta/dVol ≈ Vanna (not implemented anyway)
- No test checking dDelta/dTime ≈ Charm (not implemented anyway)

**Impact:**
- Can't verify internal consistency of Greeks
- Might miss sign errors or scaling errors
- Hard to catch bugs in second-order effects

**Fix Required:**
```python
def test_delta_gamma_relationship():
    """Test that dDelta/dSpot ≈ Gamma."""
    S = 100.0
    K = 100.0
    T = 30/365
    r = 0.05
    sigma = 0.30

    # Calculate delta at S and S + 1
    delta1 = calculate_delta(S, K, T, r, sigma, 'call')
    delta2 = calculate_delta(S + 1, K, T, r, sigma, 'call')

    # Numerical derivative
    dDelta_dS = delta2 - delta1

    # Compare to gamma
    gamma = calculate_gamma(S, K, T, r, sigma)

    # Should match within 5%
    assert abs(dDelta_dS - gamma) / gamma < 0.05
```

**Severity:** MEDIUM (testing quality)

---

## ADDITIONAL OBSERVATIONS

### Greeks Implementation Quality

**What's Good:**
✅ Black-Scholes formula implemented correctly
✅ Delta, gamma, vega, theta calculations match benchmarks within 15%
✅ Put-call parity relationships correct
✅ Edge cases at expiration handled (mostly)
✅ Multi-leg aggregation correct (multiply by quantity × 100)
✅ Test coverage decent (29 tests passing)

**What's Missing:**
❌ Second-order Greeks (Charm, Vanna, Volga, Vomma)
❌ Dividend adjustments
❌ Real IV extraction from market prices
❌ Greeks history tracking
❌ P&L attribution by Greek

### Profile-Specific Greeks Issues

**Profile 1 (Long-Dated Gamma):**
- Uses: Gamma, Theta
- Issue: No dividend adjustment (1.5% error on delta hedge)
- Severity: MEDIUM

**Profile 2 (Short-Dated Gamma):**
- Uses: Gamma
- Issue: ATM expiration delta discontinuity
- Severity: HIGH

**Profile 3 (Charm/Decay):**
- Uses: **Charm (NOT IMPLEMENTED)**
- Issue: No charm calculation exists
- Severity: CRITICAL

**Profile 4 (Vanna):**
- Uses: **Vanna (NOT IMPLEMENTED)**
- Issue: No vanna calculation exists
- Severity: CRITICAL

**Profile 5 (Skew):**
- Uses: Delta (skew exposure)
- Issue: No term structure modeling
- Severity: LOW

**Profile 6 (Vol-of-Vol):**
- Uses: Vega
- Issue: IV proxy instead of real IV
- Severity: CRITICAL (for vol trading)

---

## RECOMMENDATIONS

### Immediate Actions (Before Next Backtest):

1. **Fix CRITICAL-1:** Implement Charm and Vanna calculations
2. **Fix CRITICAL-2:** Extract real IV from Polygon bid/ask (Newton-Raphson solver)
3. **Fix CRITICAL-3:** Add dividend yield to Black-Scholes
4. **Fix CRITICAL-4:** Recalculate Greeks during mark-to-market

### Next Priority:

5. **Fix HIGH-1:** ATM expiration delta handling
6. **Fix HIGH-2:** Add numerical stability guards
7. **Fix HIGH-3:** Document theta sign convention
8. **Fix HIGH-4:** Clarify vega units in docs
9. **Fix HIGH-5:** Track expired legs explicitly

### Lower Priority:

10. **Fix MEDIUM-1:** Add rho calculation (nice-to-have)
11. **Fix MEDIUM-2:** Add American exercise warnings
12. **Fix MEDIUM-3:** Add Greeks sensitivity tests

---

## FORMULA REFERENCE (For Implementation)

### Second-Order Greeks

**Charm (dDelta/dTime):**
```
Call Charm = -n'(d1) × [2rT - d2×σ×√T] / (2T×σ×√T) - r×e^(-rT)×N(d2)
Put Charm  = -n'(d1) × [2rT - d2×σ×√T] / (2T×σ×√T) + r×e^(-rT)×N(-d2)

Where:
n'(x) = derivative of normal PDF = -x × n(x)
```

**Vanna (dDelta/dVol = dVega/dSpot):**
```
Vanna = -n(d1) × d2 / σ

Same for calls and puts
```

### Dividend-Adjusted Black-Scholes

**d1 with dividends:**
```
d1 = [ln(S/K) + (r - q + 0.5σ²)T] / (σ√T)

Where q = continuous dividend yield
```

**Delta with dividends:**
```
Call Delta = e^(-qT) × N(d1)
Put Delta  = e^(-qT) × [N(d1) - 1] = -e^(-qT) × N(-d1)
```

---

## CONCLUSION

**Greeks implementation is fundamentally sound but incomplete.**

The Black-Scholes calculations are mathematically correct and match benchmarks. The critical failure is **missing second-order Greeks** that two profiles depend on.

**This is not a "nice-to-have" issue.** Profiles 3 and 4 cannot function correctly without Charm and Vanna calculations. The backtest results for these profiles are unreliable.

**Before running any more backtests:**
1. Implement Charm and Vanna
2. Switch from IV proxy to real IV extraction
3. Add dividend adjustments
4. Enable Greeks tracking during position lifecycle

**Estimated fix time:** 6-8 hours for CRITICAL issues, 2-4 hours for HIGH issues.

---

**Next Audit:** Transaction cost modeling and execution realism (market-microstructure-expert)

