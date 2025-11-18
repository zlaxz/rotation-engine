# TRANSACTION COST REALITY CHECK - ROUND 4
## Execution Cost Audit: Backtest Infrastructure vs Real Markets

**Date:** 2025-11-18
**Auditor:** Market Microstructure Expert
**Scope:** Complete transaction cost validation across train/validation/test backtests
**Capital at Risk:** REAL MONEY
**Verdict:** 🔴 **NOT DEPLOYMENT READY** - Critical cost components missing

---

## EXECUTIVE SUMMARY

**Overall Grade: C+ (70/100)**

Your backtest infrastructure has a sophisticated execution cost model (`ExecutionModel`) but **DOESN'T ACTUALLY USE IT** in the backtests. The `TradeTracker` class that powers all three backtest scripts uses hardcoded costs that don't reflect market reality.

### The Big 3 Problems:

1. **CRITICAL: Delta hedging costs not modeled** - Missing $87-$218 per trade
2. **CRITICAL: Spread model ignored in backtests** - Using constant $0.03 instead of dynamic model
3. **CRITICAL: Cost model inconsistency** - ExecutionModel vs TradeTracker using different assumptions

### Bottom Line Impact:

**Current backtest returns are overstated by 15-50%** depending on strategy and market conditions.

**Profiles 1, 3, and 6 (gamma-heavy straddles) may be UNPROFITABLE after realistic hedging costs.**

---

## DETAILED FINDINGS

### 1. COMMISSION STRUCTURE ⚠️ CRITICAL INCONSISTENCY

**Reality Check:**
- Retail broker: $0.65/contract (TD Ameritrade, Interactive Brokers)
- OCC clearing fee: $0.055/contract
- Exchange fees: $0.02-$0.05/contract
- FINRA TAFC (short sales): $0.00205/contract
- **Total realistic cost: ~$0.75/contract per side**

**What Your Code Does:**

| Component | ExecutionModel | TradeTracker (Used in Backtests) |
|-----------|----------------|----------------------------------|
| Base commission | $0.65/contract | $2.60 flat per trade |
| OCC fees | $0.055 (included) | Unknown (buried in $2.60) |
| FINRA fees | $0.00205 (shorts) | Unknown |
| Exchange fees | Missing | Missing |
| **Per 2-leg straddle round-trip** | $2.60 + $0.22 = **$2.82** | $2.60 + $2.60 = **$5.20** |

**The Problem:**
- ExecutionModel is correct but **NOT USED**
- TradeTracker hardcodes $2.60 which is ~2x realistic for open, but may underestimate close
- Tastyworks charges $0 open / $10 close - if using that model, costs could be HIGHER
- **You have TWO different cost models in the same codebase**

**Impact:**
- Direction: MIXED (TradeTracker may overestimate entry, underestimate exit)
- Magnitude: $2-3 per round-trip difference
- Annual: **-1% to -2% on returns**

**Fix Required:**
```python
# TradeTracker should use ExecutionModel
entry_cost = exec_model.get_commission_cost(
    num_contracts=len(position['legs']),
    is_short=(qty < 0),
    premium=entry_price
)
# NOT hardcoded $2.60
```

---

### 2. BID-ASK SPREADS 🔴 CRITICAL - WRONG MODEL IN BACKTESTS

**Reality Check (SPY Options):**

| Market Condition | ATM Spread | Your Backtest Uses |
|------------------|------------|-------------------|
| Normal vol (VIX 12-20) | $0.01-$0.05 | $0.03 ✅ |
| High vol (VIX 30-40) | $0.10-$0.30 (3-5x) | $0.03 ❌ |
| Crisis (VIX 80+ Mar 2020) | $0.50-$2.00 (10-60x) | $0.03 ❌ |
| Short DTE (0-7 days) | $0.05-$0.20 (wider) | $0.03 ❌ |
| OTM 5% | $0.05-$0.15 normal | $0.03 ❌ |

**What Your Code Does:**

**ExecutionModel (NOT used in backtests):**
```python
base_spread_atm = $0.03
adjustments:
  - Moneyness: 1.0 + moneyness * 5.0 (linear)
  - DTE: 1.3x for <7 days, 1.15x for <14 days
  - VIX: 1.0x at VIX=15 → 2.0x at VIX=35+ (continuous)
  - Min: 5% of mid price
```
**Verdict:** ✅ Sophisticated and realistic

**TradeTracker (ACTUALLY used in backtests):**
```python
# Line 77
spread = 0.03  # Hardcoded constant
```
**Verdict:** ❌ **WRONG** - doesn't vary with anything

**The Disaster:**

Your backtests use Polygon bid/ask data PLUS add $0.03 spread on top. This:
1. **Double-counts spread** (Polygon already has bid/ask embedded)
2. **Never widens during high vol** (March 2020 same as calm 2024)
3. **Ignores your sophisticated ExecutionModel**

**Impact Analysis:**

| Period | VIX Range | Realistic Spread | Backtest Uses | Underestimation |
|--------|-----------|------------------|---------------|-----------------|
| Normal 2024 | 12-20 | $0.03-$0.05 | $0.03 | ~Correct |
| March 2020 Crisis | 80+ | $1.00-$2.00 | $0.03 | **10-60x wrong** |
| Typical high vol | 30-40 | $0.15-$0.40 | $0.03 | **5-13x wrong** |

**Your March 2020 backtest results are fantasy.** Real spreads were $1-2 per leg, not $0.03.

**Annual Impact:**
- Normal periods: -1% to -2%
- If backtest includes high vol: **-5% to -15%**
- Train period (2020-2021) includes COVID crash: **Returns severely inflated**

**Fix Required:**
```python
# TradeTracker.track_trade() - replace hardcoded spread
vix_proxy = get_vix_proxy(entry_row['RV20'])
moneyness = abs(strike - spot) / spot
dte = (expiry - entry_date).days

spread = exec_model.get_spread(
    mid_price=mid_price,
    moneyness=moneyness,
    dte=dte,
    vix_level=vix_proxy
)
# NOT: spread = 0.03
```

---

### 3. SLIPPAGE ⚠️ HIGH SEVERITY - MODEL EXISTS BUT NOT USED

**Reality Check:**

| Order Size | Market Order Slippage |
|------------|----------------------|
| 1-10 contracts | 10-20% of half-spread |
| 10-50 contracts | 25-50% of half-spread |
| 50+ contracts | Full spread + market impact |

**What Your Code Does:**

**ExecutionModel:**
```python
slippage_small = 0.10   # 10% of half-spread for 1-10 contracts
slippage_medium = 0.25  # 25% for 11-50
slippage_large = 0.50   # 50% for 50+

exec_price = mid ± half_spread ± (half_spread * slippage_pct)
```
**Verdict:** ✅ Realistic model

**TradeTracker:**
```python
# Entry: Uses Polygon ask (long) or bid (short)
# Exit: Uses mid ± hardcoded $0.03 spread
# Slippage: ZERO
```
**Verdict:** ❌ No slippage modeling

**Impact:**
- At current 1-2 contract size: Minor (-0.5% to -1% annual)
- If scaling to 10+ contracts: **Severe (-3% to -7% annual)**

**Fix Required:**
```python
exec_price = exec_model.get_execution_price(
    mid_price=mid,
    side='buy' if qty > 0 else 'sell',
    moneyness=moneyness,
    dte=dte,
    vix_level=vix,
    quantity=abs(qty)  # Size-based slippage
)
```

---

### 4. DELTA HEDGING COSTS 🔴 CRITICAL - COMPLETELY MISSING

**This is the biggest issue in your entire cost model.**

**Reality Check:**

For gamma-heavy strategies (long/short straddles), you MUST delta hedge or you're taking directional risk. Hedging is NOT optional - it's the entire point of selling theta while staying market-neutral.

**ES Futures Costs (per round-trip):**
- Commission: $2.50
- Bid-ask spread: 0.25 points = $12.50
- Half-spread (one-way): $6.25
- **Total per rebalance: $8.75**

**Hedging Frequency:**

| Strategy | Gamma Level | Rebalances per Trade | Cost per Trade |
|----------|-------------|---------------------|----------------|
| Profile 1: Long straddle 75 DTE | High | 10-15 | **$87-$131** |
| Profile 3: Short straddle 30 DTE | Very High | 15-25 | **$131-$218** |
| Profile 6: Long straddle 30 DTE | High | 10-20 | **$87-$175** |
| Current backtest assumption | N/A | 0 | **$0** |

**What Your Code Does:**

**ExecutionModel:**
```python
def get_delta_hedge_cost(contracts, es_mid_price):
    # Correct implementation: commission + spread + market impact
    return actual_contracts * (commission + half_spread) * impact_multiplier
```
**Verdict:** ✅ Realistic model

**TradeTracker / Backtest Scripts:**
```python
# Delta hedging implementation: NONE
# Greeks are calculated but never used for hedging
# Position delta is tracked but no rebalancing logic
```
**Verdict:** ❌ **COMPLETELY MISSING**

**The Disaster:**

You're backtesting gamma strategies **without modeling the cost of staying delta-neutral**. This is like:
- Backtesting a market-making strategy without bid-ask spreads
- Backtesting HFT without exchange fees
- Backtesting pairs trading without modeling both legs

**It's not just wrong - it makes the results meaningless.**

**Impact Analysis:**

Let's say your backtest shows Profile 1 (long straddle) makes $200 avg per trade.

| Scenario | Avg P&L | Hedging Cost | Net P&L | Impact |
|----------|---------|--------------|---------|--------|
| Current backtest | $200 | $0 | $200 | Baseline |
| Realistic (10 rebalances) | $200 | $87 | $113 | **-44%** |
| Realistic (15 rebalances) | $200 | $131 | $69 | **-66%** |
| If avg P&L was only $100 | $100 | $100 | $0 | **BREAK-EVEN** |
| If avg P&L was $50 | $50 | $100 | -$50 | **LOSING MONEY** |

**Profile 3 (short straddle) is even worse:**
- Collects tiny theta ($50-100/day)
- Pays massive gamma hedging costs ($131-218)
- **Likely unprofitable after realistic hedging**

**Annual Impact:**
- Gamma-heavy profiles (1, 3, 6): **-10% to -30%** or **complete strategy failure**
- Directional profiles (4, 5): Minimal (no hedging needed)

**Fix Required:**

This is NOT a small fix. You need to:

1. **Implement rebalancing logic:**
```python
def calculate_hedging_trades(position, daily_path):
    """
    Track position delta over time
    Trigger rebalance when delta exceeds ±10-20 threshold
    Calculate ES futures contracts needed
    Apply hedging costs
    """
    hedging_cost = 0.0
    current_delta = 0

    for day in daily_path:
        new_delta = day['greeks']['delta']
        delta_change = abs(new_delta - current_delta)

        if delta_change > 10:  # Rebalance threshold
            es_contracts = delta_change / 50  # ES delta = 50
            cost = exec_model.get_delta_hedge_cost(es_contracts)
            hedging_cost += cost
            current_delta = 0  # Reset after hedge

    return hedging_cost
```

2. **Add to P&L calculation:**
```python
mtm_pnl = mtm_value - entry_cost - exit_commission - hedging_cost
```

3. **Re-run ALL backtests** with realistic hedging

**Effort:** High - 1-2 days of work
**Priority:** CRITICAL - must fix before deployment
**Likelihood:** **Profiles 1, 3, 6 will fail after adding this cost**

---

### 5. OTHER COSTS ✅ MOSTLY COMPLETE

**OCC Fees:** $0.055/contract - ✅ Included in ExecutionModel
**FINRA Fees:** $0.00205/contract (shorts) - ✅ Included in ExecutionModel
**SEC Fees:** $0.00182 per $1000 premium (shorts) - ✅ Included correctly
**Exchange Fees:** $0.02-$0.05/contract - ❌ Missing (add $0.03/contract)

Minor issue - add $0.03/contract to commission in ExecutionModel.

---

### 6. EXECUTION TIMING ✅ ACCEPTABLE

- Entry: End-of-day on entry_date close - ✅ Conservative
- Exit: End-of-day on exit_date close - ✅ Acceptable
- After-hours: Not modeled - ✅ Acceptable limitation
- Settlement: N/A (not holding to expiration) - ✅ N/A

No issues here.

---

### 7. LIQUIDITY CONSTRAINTS ⚠️ NOT MODELED

**Current position size:** 1-2 contracts

**SPY options capacity:**
- ATM weeklies: 10,000-100,000 OI
- ATM monthlies: 50,000-500,000 OI
- **Your size is tiny - no capacity issues**

**Scaling analysis:**

| Size | Impact | Model Accuracy |
|------|--------|----------------|
| 1-10 contracts | None | ✅ Fine |
| 10-100 contracts | Minor (+10-20% spreads) | ⚠️ Should model |
| 100-1000 contracts | Significant market impact | ❌ Must model |

**Fix:** Add position size warning if order exceeds 1% of typical open interest.

---

## REALISTIC COST MODEL

### Per Round-Trip (2-leg ATM Straddle)

**Commissions & Fees:**
- Base commission: 2 legs × $0.65 × 2 (entry+exit) = $2.60
- OCC fees: 2 × $0.055 × 2 = $0.22
- Exchange fees: 2 × $0.03 × 2 = $0.12
- **Total: $2.94**

**Bid-Ask Spreads:**
- Normal vol: $0.05/leg × 2 legs × 2 = $0.20 to $0.40
- High vol: $0.30/leg × 2 × 2 = $1.20 to $2.40
- **Your backtest: $0.03 × 2 × 2 = $0.12** ❌

**Slippage:**
- Small order (1-2 contracts): $0.02 to $0.05
- **Your backtest: $0** ❌

**Delta Hedging:**
- Long straddle (Profile 1): $87 to $131
- Short straddle (Profile 3): $131 to $218
- **Your backtest: $0** ❌

**Total Realistic Cost per Trade:**

| Scenario | Commission | Spread | Slippage | Hedging | Total | Your Backtest |
|----------|-----------|---------|----------|---------|-------|---------------|
| Best case (normal vol, no hedging) | $2.94 | $0.30 | $0.03 | $0 | **$3.27** | $2.72 |
| Typical (normal vol + hedging Profile 1) | $2.94 | $0.30 | $0.03 | $100 | **$103.27** | $2.72 |
| Worst case (high vol + hedging) | $2.94 | $2.00 | $0.10 | $175 | **$180.04** | $2.72 |

**Your backtests assume $2.72 per trade.**

**Reality is $3 to $180 depending on strategy and market conditions.**

---

## DEGRADATION ESTIMATE

### Impact on Returns by Scenario

**If average trade P&L = $50:**
- Current backtest net: $50 - $2.72 = $47.28
- Realistic (no hedging): $50 - $4 = $46 (-2.7%)
- Realistic (with hedging): $50 - $120 = **-$70 (LOSING MONEY)**

**If average trade P&L = $200:**
- Current backtest net: $200 - $2.72 = $197.28
- Realistic (no hedging): $200 - $5 = $195 (-1.2%)
- Realistic (with hedging): $200 - $120 = $80 (**-59%**)

**If average trade P&L = $500:**
- Current backtest net: $500 - $2.72 = $497.28
- Realistic (no hedging): $500 - $5 = $495 (-0.5%)
- Realistic (with hedging): $500 - $120 = $380 (-24%)

### Annual Return Impact

| Cost Component | Impact on Annual Returns |
|----------------|-------------------------|
| Spread underestimation | -1% to -3% |
| Slippage missing | -0.5% to -1% |
| Delta hedging (gamma profiles) | **-10% to -30%** |
| March 2020 spread widening | -5% to -15% for that period |
| **TOTAL DEGRADATION** | **-15% to -50%** |

---

## VERDICT BY PROFILE

### Profile 1: Long-Dated Gamma (Long ATM Straddle, 75 DTE)
- **Hedging Required:** YES (high gamma)
- **Missing Costs:** Delta hedging ($87-$131/trade)
- **Verdict:** 🔴 **Returns SEVERELY overstated, likely unprofitable after hedging**

### Profile 2: Short-Dated Gamma Spike (Long Straddle, 7 DTE)
- **Hedging Required:** Minimal (fast decay)
- **Missing Costs:** Spread widening on short DTE (1.3x)
- **Verdict:** ⚠️ **Moderately overstated** (spread should be wider)

### Profile 3: Charm/Decay (Short ATM Straddle, 30 DTE)
- **Hedging Required:** YES (very high gamma)
- **Missing Costs:** Delta hedging ($131-$218/trade) - CRITICAL
- **Verdict:** 🔴 **LIKELY UNPROFITABLE** - theta edge destroyed by hedging costs

### Profile 4: Vanna (Long ATM Call, 60 DTE)
- **Hedging Required:** Optional (directional bet)
- **Missing Costs:** If hedged: $40-80/trade
- **Verdict:** ⚠️ **Depends on hedging strategy** - may be viable unhedged

### Profile 5: Skew (Long OTM Put, 45 DTE)
- **Hedging Required:** NO (directional)
- **Missing Costs:** OTM spread underestimated (1.5-2x wider)
- **Verdict:** ⚠️ **Moderately overstated**

### Profile 6: Vol-of-Vol (Long Straddle, 30 DTE)
- **Hedging Required:** YES (high gamma)
- **Missing Costs:** Delta hedging ($100-$150/trade)
- **Verdict:** 🔴 **Severely overstated**

---

## CRITICAL FIXES REQUIRED

### Priority 1: Implement Delta Hedging Simulation
**Issue:** Gamma-heavy strategies (Profiles 1, 3, 6) missing critical cost component

**Action Required:**
1. Add rebalancing logic to TradeTracker
2. Trigger rebalance when position delta exceeds ±10-20
3. Calculate ES futures contracts needed (delta / 50)
4. Apply ExecutionModel.get_delta_hedge_cost()
5. Add hedging cost to P&L calculation

**Impact:** Will likely eliminate edge on Profiles 1, 3, 6
**Effort:** High - 1-2 days
**Timeline:** **DO THIS FIRST**

### Priority 2: Fix Spread Modeling
**Issue:** TradeTracker uses hardcoded $0.03, ignores ExecutionModel's sophisticated spread calculation

**Action Required:**
1. Remove hardcoded `spread = 0.03` in TradeTracker
2. Calculate VIX proxy from RV20
3. Calculate moneyness = abs(strike - spot) / spot
4. Use ExecutionModel.get_spread(mid, moneyness, dte, vix)
5. Remove duplicate spread application (Polygon already has bid/ask)

**Impact:** -3% to -8% annual returns, more during high vol
**Effort:** Medium - 4-8 hours
**Timeline:** **Fix before next backtest**

### Priority 3: Unify Commission Model
**Issue:** ExecutionModel and TradeTracker use different assumptions

**Action Required:**
1. TradeTracker should call ExecutionModel.get_commission_cost()
2. Remove hardcoded $2.60
3. Pass num_contracts, is_short, premium

**Impact:** Minor impact on returns
**Effort:** Low - 1-2 hours
**Timeline:** **Quick fix**

### Priority 4: Add Size-Based Slippage
**Issue:** ExecutionModel has slippage, TradeTracker doesn't use it

**Action Required:**
1. Use ExecutionModel.get_execution_price() with quantity parameter
2. Apply size-based slippage (10%/25%/50% of half-spread)

**Impact:** Minor at 1-2 contracts, critical if scaling
**Effort:** Low - 1-2 hours
**Timeline:** **Before scaling capital**

---

## VALIDATION REQUIRED

Before trusting any backtest results:

1. **Compare vs actual broker statements**
   - Source: Tastyworks/TD Ameritrade account
   - Validate: Commission + fees match reality

2. **Validate spreads against real data**
   - Source: Polygon bid/ask data March 2020 vs normal 2024
   - Validate: VIX 80+ spreads are 5-10x normal, not constant

3. **Estimate realistic hedging frequency**
   - Method: Simulate gamma of actual positions
   - Count: ±10 delta threshold crossings
   - Validate: Rebalancing cost estimates

---

## FINAL VERDICT

### Deployment Readiness: 🔴 **NOT READY**

**Confidence in Current Results:** LOW

**Estimated Overstatement:** 15-50% depending on strategy

### What Must Happen Next:

1. ✅ Implement delta hedging simulation (CRITICAL)
2. ✅ Fix spread modeling to use ExecutionModel
3. ✅ Unify commission calculations
4. ✅ Re-run ALL backtests (train/validation/test) with realistic costs
5. ✅ Expect 15-50% degradation in returns
6. ✅ IF strategies still profitable → proceed to validation
7. ❌ IF strategies become unprofitable → abandon or redesign

### The Hard Truth:

**You have a sophisticated execution cost model (ExecutionModel) that you're not using.**

**Your backtests run on hardcoded assumptions that don't reflect market reality.**

**Your gamma-heavy strategies (Profiles 1, 3, 6) are missing the BIGGEST cost component - delta hedging.**

**Until you fix these issues, your backtest results are unreliable for deployment decisions.**

---

## NEXT ACTIONS

**Before running another backtest:**

1. Implement delta hedging (2 days)
2. Fix spread modeling (8 hours)
3. Unify commissions (2 hours)
4. Add slippage (2 hours)

**Then:**

5. Re-run train period (2020-2021)
6. Analyze degradation
7. If still viable → re-run validation (2022-2023)
8. If STILL viable → consider test (2024)

**Expected outcome:**

- Profiles 1, 3, 6 likely fail after hedging costs
- Profiles 2, 4, 5 show moderate degradation (5-15%)
- Overall strategy viability: UNCERTAIN

**Real capital is at risk. Get the costs right BEFORE deployment.**

---

*Audit complete. Results are what they are. Fix the issues or don't deploy.*
