# TRANSACTION COST VALIDATION CHECKLIST

**Quick reference for validating backtest cost assumptions before deployment**

---

## 1. POLYGON SPREAD VERIFICATION ❓ UNVERIFIED

**Hypothesis:** Polygon bid/ask spreads widen 10-50x during VIX spikes

**How to Test:**
```python
from src.data.polygon_options import PolygonOptionsLoader
from datetime import date

polygon = PolygonOptionsLoader()

# Crisis period
crisis_date = date(2020, 3, 16)  # VIX hit 82
# Normal period
normal_date = date(2024, 6, 15)  # VIX ~15

# Get ATM straddle spreads
def get_atm_spread(polygon, test_date):
    # Find SPY close on that date
    spy_close = get_spy_close(test_date)  # Need to implement
    strike = round(spy_close)

    # Get monthly expiry ~30 DTE
    expiry = get_monthly_expiry(test_date, dte=30)

    # Get call spread
    call_bid = polygon.get_option_price(test_date, strike, expiry, 'call', 'bid')
    call_ask = polygon.get_option_price(test_date, strike, expiry, 'call', 'ask')
    call_spread = call_ask - call_bid

    # Get put spread
    put_bid = polygon.get_option_price(test_date, strike, expiry, 'put', 'bid')
    put_ask = polygon.get_option_price(test_date, strike, expiry, 'put', 'ask')
    put_spread = put_ask - put_bid

    return call_spread, put_spread

crisis_call, crisis_put = get_atm_spread(polygon, crisis_date)
normal_call, normal_put = get_atm_spread(polygon, normal_date)

print(f"March 2020 Crisis (VIX 82):")
print(f"  Call spread: ${crisis_call:.2f}")
print(f"  Put spread:  ${crisis_put:.2f}")
print(f"\nNormal 2024 (VIX 15):")
print(f"  Call spread: ${normal_call:.2f}")
print(f"  Put spread:  ${normal_put:.2f}")
print(f"\nWidening Factor:")
print(f"  Call: {crisis_call / normal_call:.1f}x")
print(f"  Put:  {crisis_put / normal_put:.1f}x")
```

**Expected Result:**
- Normal 2024: $0.01-$0.05 per leg
- Crisis 2020: $0.50-$2.00 per leg (10-50x wider)

**If Spreads DON'T Widen:**
- Your March 2020 backtest is inflated by 50-100%
- Must apply ExecutionModel spread adjustments
- Train period (2020-2021) results are unreliable

**Action:** Run this test TODAY before trusting any backtest results

---

## 2. DELTA HEDGING FREQUENCY ESTIMATION 🔴 CRITICAL

**Hypothesis:** ATM straddles require 10-25 rebalances per 14-day window

**How to Test:**
```python
def estimate_hedging_frequency(daily_path, rebalance_threshold=15):
    """
    Count how many times position delta crosses threshold

    Args:
        daily_path: List of daily snapshots with Greeks
        rebalance_threshold: Delta change that triggers rebalance (e.g., 15)

    Returns:
        rebalance_count, total_cost
    """
    rebalances = 0
    current_delta = 0
    total_cost = 0

    ES_COMMISSION = 2.50
    ES_HALF_SPREAD = 6.25  # 0.25 points = $12.50 / 2
    COST_PER_REBALANCE = ES_COMMISSION + ES_HALF_SPREAD  # $8.75

    for day in daily_path:
        new_delta = day['greeks']['delta']
        delta_change = abs(new_delta - current_delta)

        if delta_change > rebalance_threshold:
            # Trigger rebalance
            es_contracts = delta_change / 50  # ES delta = 50
            cost = es_contracts * COST_PER_REBALANCE

            total_cost += cost
            rebalances += 1
            current_delta = 0  # Reset after hedge

    return rebalances, total_cost

# Run on sample trades
profile_1_trades = load_profile_trades('Profile_1_LDG')
rebalance_counts = []
costs = []

for trade in profile_1_trades[:50]:  # Sample 50 trades
    count, cost = estimate_hedging_frequency(trade['path'])
    rebalance_counts.append(count)
    costs.append(cost)

print(f"Profile 1 (Long Straddle 75 DTE, held 14 days):")
print(f"  Avg rebalances: {np.mean(rebalance_counts):.1f}")
print(f"  Avg hedging cost: ${np.mean(costs):.0f}")
print(f"  Min cost: ${np.min(costs):.0f}")
print(f"  Max cost: ${np.max(costs):.0f}")
print(f"  Median: ${np.median(costs):.0f}")
```

**Expected Result:**
- Profile 1 (75 DTE): 10-15 rebalances → $87-$131/trade
- Profile 3 (30 DTE): 15-25 rebalances → $131-$218/trade
- Profile 6 (30 DTE): 10-20 rebalances → $87-$175/trade

**If Hedging Cost > Avg P&L:**
- Strategy is UNPROFITABLE
- Must abandon or redesign

**Action:** Build this into TradeTracker BEFORE next backtest

---

## 3. SLIPPAGE VALIDATION ⚠️ MEDIUM PRIORITY

**Reality Check:** Market orders don't fill at exact bid/ask

**How to Validate:**
```python
# If you have actual trading history, compare:
# - Expected fill (bid/ask from Polygon)
# - Actual fill (from broker statements)
# - Slippage = actual - expected

# Example from real trades:
expected_fills = [2.05, 3.20, 1.85]  # Polygon ask prices
actual_fills = [2.06, 3.23, 1.88]     # Actual fills from broker
slippage = [a - e for a, e in zip(actual_fills, expected_fills)]
avg_slippage_pct = np.mean(slippage) / np.mean(expected_fills) * 100

print(f"Avg slippage: {avg_slippage_pct:.1f}% of fill price")

# Typical: 10-20% of half-spread for small orders
```

**Current Impact:**
- 1-2 contracts: -$0.02 to -$0.05/trade (minor)
- 10+ contracts: -$0.10 to -$0.50/trade (severe)

**Action:** Add to TradeTracker if scaling beyond 5 contracts

---

## 4. COMMISSION VERIFICATION ✅ CONSERVATIVE

**Current Model:**
- $2.60 per side (entry + exit)
- Total: $5.20 per round-trip

**Reality:**
- Base: $0.65/contract × 2 legs = $1.30
- OCC: $0.055/contract × 2 = $0.11
- Exchange: $0.03/contract × 2 = $0.06
- **Total: $1.47/side × 2 = $2.94**

**Verdict:** ✅ You're OVER-charging by 77% (conservative bias = good)

**Action:** None required unless seeking precision

---

## 5. EXECUTION TIMING ✅ ACCEPTABLE

**Current Model:**
- Entry: End-of-day close price
- Exit: End-of-day close price
- No after-hours trading

**Reality Check:**
- EOD pricing is conservative (no optimal timing)
- After-hours excluded (appropriate for backtest)
- No settlement/assignment risk (exit before expiration)

**Verdict:** ✅ Acceptable assumptions

**Action:** None required

---

## 6. LIQUIDITY CONSTRAINTS ✅ NO ISSUES AT CURRENT SCALE

**Current Size:** 1-2 contracts

**SPY Options Capacity:**
- ATM weekly: 10,000-100,000 OI
- ATM monthly: 50,000-500,000 OI

**Your Position as % of OI:** <0.01% (tiny)

**Scaling Limits:**

| Size | Impact | Action Required |
|------|--------|----------------|
| 1-10 contracts | None | ✅ Current model OK |
| 10-100 contracts | Minor (+10-20% spreads) | Add size penalty |
| 100-1000 contracts | Severe market impact | Complete redesign |

**Verdict:** ✅ No constraints at current scale

**Action:** Add warning if order exceeds 1% of typical OI

---

## VALIDATION SUMMARY

| Component | Status | Confidence | Action Required |
|-----------|--------|------------|-----------------|
| Bid/ask pricing | ✅ Fixed | High | None |
| Commissions | ✅ Conservative | High | None (overcharge OK) |
| Polygon spreads | ❓ Unverified | **ZERO** | 🔴 Test crisis spreads TODAY |
| Slippage | 🔴 Missing | Low | Add if scaling >5 contracts |
| Delta hedging | 🔴 Missing | **ZERO** | 🔴 Implement ASAP (1-2 days) |
| Execution timing | ✅ OK | Medium | None |
| Liquidity | ✅ OK | High | None at 1-2 contracts |

---

## DEPLOYMENT GATE CRITERIA

**Before deploying ANY strategy:**

- [ ] Polygon spread verification complete (crisis vs normal)
- [ ] Delta hedging simulation implemented for gamma strategies
- [ ] Slippage added if position size > 5 contracts
- [ ] Backtests re-run with realistic costs
- [ ] Strategy still profitable after cost degradation

**Gamma Strategies (Profiles 1, 3, 6) Additional Gates:**

- [ ] Delta hedging cost < 50% of avg P&L per trade
- [ ] Sharpe ratio > 1.0 after hedging costs
- [ ] Max drawdown acceptable after cost stress test
- [ ] Walk-forward validation shows consistent edge

**If ANY gate fails → DO NOT DEPLOY**

---

## QUICK DECISION TREE

```
Is strategy gamma-heavy (straddles/strangles)?
├─ YES → Delta hedging required
│   ├─ Hedging cost < 50% of P&L?
│   │   ├─ YES → Maybe viable (run full validation)
│   │   └─ NO → ABANDON strategy
│   └─
├─ NO → Directional strategy
    ├─ Verify Polygon spreads in crisis
    ├─ Add slippage if size > 5 contracts
    └─ Deploy if profitable after costs
```

---

*Use this checklist BEFORE every backtest and BEFORE deployment. Skip steps = lose money.*
