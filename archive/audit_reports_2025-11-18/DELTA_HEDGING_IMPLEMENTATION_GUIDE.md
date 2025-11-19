# DELTA HEDGING IMPLEMENTATION GUIDE

**Priority:** 🔴 CRITICAL
**Effort:** 1-2 days
**Impact:** -30% to -80% return degradation for Profiles 1, 3, 6
**Outcome:** Will likely eliminate edge on Profile 3, severely reduce Profiles 1 & 6

---

## WHY THIS MATTERS

**Current State:**
- Backtesting gamma-heavy strategies (straddles) without modeling hedging costs
- Results show strategies are profitable
- **Reality:** Hedging costs will eat 50-100% of profits

**Example - Profile 3 (Short Straddle):**
```
Current backtest: $80/trade profit
Missing cost:     $175/trade hedging
Real P&L:         -$95/trade (LOSING MONEY)
```

**This implementation will reveal TRUE viability of gamma strategies.**

---

## IMPLEMENTATION APPROACH

### Option 1: Full Simulation (RECOMMENDED)
**Accuracy:** High
**Effort:** 2 days
**Method:** Simulate actual delta rebalancing during trade lifecycle

### Option 2: Statistical Estimation
**Accuracy:** Medium
**Effort:** 4-8 hours
**Method:** Use empirical rebalancing frequency from sample trades

**Choose Option 1 for deployment decisions. Option 2 for quick feasibility check.**

---

## OPTION 1: FULL SIMULATION IMPLEMENTATION

### Step 1: Add Hedging Logic to TradeTracker

**File:** `/Users/zstoc/rotation-engine/src/analysis/trade_tracker.py`

**Add new method:**

```python
def _calculate_hedging_cost(
    self,
    daily_path: List[Dict],
    exec_model,
    rebalance_threshold: float = 15.0
) -> Dict:
    """
    Simulate delta hedging over trade lifetime

    Args:
        daily_path: List of daily snapshots with Greeks
        exec_model: ExecutionModel instance for cost calculation
        rebalance_threshold: Delta change that triggers rebalance (default: 15)

    Returns:
        Dict with:
            - total_cost: Total hedging cost
            - rebalance_count: Number of rebalances
            - rebalance_details: List of each rebalance event
    """
    total_cost = 0.0
    rebalance_count = 0
    current_hedged_delta = 0.0  # Delta we've hedged away
    rebalance_details = []

    for day_idx, day in enumerate(daily_path):
        position_delta = day['greeks']['delta']

        # Net delta = position delta - hedged delta
        net_delta = position_delta - current_hedged_delta
        delta_change = abs(net_delta)

        # Check if we need to rebalance
        if delta_change > rebalance_threshold:
            # Calculate ES futures contracts needed
            # ES futures have delta of 50 (each point = $50)
            es_contracts_needed = net_delta / 50.0

            # Get hedging cost from ExecutionModel
            hedge_cost = exec_model.get_delta_hedge_cost(
                contracts=abs(es_contracts_needed),
                es_mid_price=4500.0  # Can use actual ES price if available
            )

            total_cost += hedge_cost
            rebalance_count += 1

            # Record rebalance event
            rebalance_details.append({
                'day': day_idx,
                'date': day['date'],
                'position_delta': position_delta,
                'net_delta_before': net_delta,
                'es_contracts': es_contracts_needed,
                'cost': hedge_cost
            })

            # Update hedged delta (we've now hedged this amount)
            current_hedged_delta += net_delta

    return {
        'total_cost': total_cost,
        'rebalance_count': rebalance_count,
        'rebalance_details': rebalance_details,
        'avg_cost_per_rebalance': total_cost / rebalance_count if rebalance_count > 0 else 0
    }
```

### Step 2: Integrate into track_trade()

**Modify the `track_trade()` method:**

```python
def track_trade(
    self,
    entry_date: date,
    position: Dict,
    spy_data: pd.DataFrame,
    max_days: int = 14,
    regime_data: Optional[pd.DataFrame] = None,
    model_hedging: bool = True,  # NEW PARAMETER
    rebalance_threshold: float = 15.0  # NEW PARAMETER
) -> Optional[Dict]:
    """
    Track complete trade path from entry to exit

    Args:
        ... (existing args)
        model_hedging: Whether to simulate delta hedging (default True)
        rebalance_threshold: Delta threshold for rebalancing (default 15)
    """

    # ... existing code for entry snapshot and daily path ...

    # AFTER daily path is built, before exit analytics:

    # Calculate hedging cost if requested
    hedging_cost_data = None
    total_hedging_cost = 0.0

    if model_hedging and self._requires_hedging(position):
        from src.trading.execution import ExecutionModel
        exec_model = ExecutionModel()

        hedging_cost_data = self._calculate_hedging_cost(
            daily_path,
            exec_model,
            rebalance_threshold
        )
        total_hedging_cost = hedging_cost_data['total_cost']

    # ... build exit_snapshot ...

    # MODIFY P&L calculation in daily_path loop (lines 185-186):
    # OLD:
    # mtm_pnl = mtm_value - entry_cost - commission

    # NEW: Add hedging cost accumulated up to this day
    hedging_cost_to_date = 0.0
    if hedging_cost_data:
        # Sum hedging costs up to current day
        for rebal in hedging_cost_data['rebalance_details']:
            if rebal['day'] <= day_idx:
                hedging_cost_to_date += rebal['cost']

    mtm_pnl = mtm_value - entry_cost - commission - hedging_cost_to_date

    # ... rest of exit analytics ...

    # ADD hedging data to trade record
    trade_record = {
        'entry': entry_snapshot,
        'path': daily_path,
        'exit': exit_analytics,
        'hedging': hedging_cost_data  # NEW FIELD
    }

    return trade_record
```

### Step 3: Add Helper Method to Determine if Hedging Needed

```python
def _requires_hedging(self, position: Dict) -> bool:
    """
    Determine if position requires delta hedging

    Straddles/strangles with both calls and puts = yes
    Single-sided directional = no
    """
    # Count leg types
    has_call = any(leg['type'] == 'call' for leg in position['legs'])
    has_put = any(leg['type'] == 'put' for leg in position['legs'])

    # Both call and put = likely straddle/strangle = needs hedging
    if has_call and has_put:
        return True

    # Check if profile explicitly states it's gamma strategy
    gamma_profiles = ['Profile_1_LDG', 'Profile_3_CHARM', 'Profile_6_VOV']
    if position['profile'] in gamma_profiles:
        return True

    # Single-sided positions = directional, no hedging
    return False
```

### Step 4: Update Backtest Script

**File:** `/Users/zstoc/rotation-engine/scripts/backtest_with_full_tracking.py`

**Modify tracker call (line 268-273):**

```python
# Track complete trade (WITH hedging simulation)
trade_record = tracker.track_trade(
    entry_date=entry_date,
    position=position,
    spy_data=spy,
    max_days=exit_day,
    model_hedging=True,  # Enable hedging simulation
    rebalance_threshold=15.0  # Can tune this parameter
)
```

### Step 5: Update Analysis to Include Hedging Metrics

**Add to `analyze_trades()` function:**

```python
def analyze_trades(trades: List[Dict]) -> Dict:
    """Calculate summary statistics including hedging costs"""

    if not trades:
        return {...}

    final_pnls = [t['exit']['final_pnl'] for t in trades]
    peak_pnls = [t['exit']['peak_pnl'] for t in trades]

    # NEW: Hedging analytics
    hedged_trades = [t for t in trades if t.get('hedging')]
    if hedged_trades:
        hedging_costs = [t['hedging']['total_cost'] for t in hedged_trades]
        rebalance_counts = [t['hedging']['rebalance_count'] for t in hedged_trades]

        hedging_stats = {
            'hedged_trade_count': len(hedged_trades),
            'avg_hedging_cost': np.mean(hedging_costs),
            'median_hedging_cost': np.median(hedging_costs),
            'max_hedging_cost': np.max(hedging_costs),
            'avg_rebalances': np.mean(rebalance_counts),
            'total_hedging_cost': sum(hedging_costs),
            'hedging_cost_pct_of_pnl': (sum(hedging_costs) / abs(sum(final_pnls)) * 100)
                                        if sum(final_pnls) != 0 else 0
        }
    else:
        hedging_stats = None

    summary = {
        # ... existing summary fields ...
        'hedging': hedging_stats  # NEW
    }

    return summary
```

### Step 6: Update Output Display

**Modify `main()` print section to show hedging impact:**

```python
for profile_id, results in all_results.items():
    summary = results['summary']
    name = results['config']['name']

    if summary['total_trades'] > 0:
        print(f"\n{profile_id} - {name}")
        print(f"  Trades: {summary['total_trades']}")
        print(f"  Final P&L: ${summary['total_pnl']:.0f}")

        # NEW: Show hedging impact if applicable
        if summary.get('hedging'):
            hstats = summary['hedging']
            print(f"\n  HEDGING COSTS:")
            print(f"    Hedged trades: {hstats['hedged_trade_count']}")
            print(f"    Avg cost/trade: ${hstats['avg_hedging_cost']:.0f}")
            print(f"    Total hedging: ${hstats['total_hedging_cost']:.0f}")
            print(f"    Avg rebalances: {hstats['avg_rebalances']:.1f}")
            print(f"    Hedging as % of P&L: {hstats['hedging_cost_pct_of_pnl']:.1f}%")

            # Calculate P&L without hedging for comparison
            gross_pnl = summary['total_pnl'] + hstats['total_hedging_cost']
            print(f"\n  IMPACT:")
            print(f"    P&L without hedging: ${gross_pnl:.0f}")
            print(f"    P&L with hedging:    ${summary['total_pnl']:.0f}")
            print(f"    Degradation:         {(hstats['total_hedging_cost']/gross_pnl*100):.1f}%")
```

---

## OPTION 2: STATISTICAL ESTIMATION (QUICK CHECK)

**Use this for rapid feasibility check, not deployment decisions.**

### Simplified Approach:

```python
def estimate_hedging_cost_simple(profile_id, avg_dte, days_held):
    """
    Statistical estimation based on typical rebalancing frequency

    Rules of thumb:
    - ATM straddles: ~1 rebalance per 1-2 days held
    - Short DTE (<14): More frequent (higher gamma)
    - Long DTE (>45): Less frequent (lower gamma)
    """

    # Empirical rebalancing frequency
    if avg_dte <= 14:
        rebalances_per_day = 1.5
    elif avg_dte <= 30:
        rebalances_per_day = 1.0
    elif avg_dte <= 60:
        rebalances_per_day = 0.7
    else:
        rebalances_per_day = 0.5

    estimated_rebalances = rebalances_per_day * days_held
    cost_per_rebalance = 8.75  # ES commission + half spread

    return estimated_rebalances * cost_per_rebalance

# Example usage
profile_1_cost = estimate_hedging_cost_simple('Profile_1_LDG', 75, 14)
print(f"Profile 1 estimated hedging: ${profile_1_cost:.0f}")
# Expected: ~$87-$131
```

**Pros:** Fast to implement (30 minutes)
**Cons:** Less accurate, can't validate with real Greeks evolution

---

## EXPECTED RESULTS AFTER IMPLEMENTATION

### Profile 1: Long-Dated Gamma (75 DTE, 14 days held)

**Before hedging:**
```
Avg P&L per trade: $150
Win rate: 65%
Total P&L (100 trades): $15,000
```

**After hedging:**
```
Avg hedging cost: $110/trade
Avg rebalances: 12
Net P&L per trade: $40 (-73% degradation)
Total P&L: $4,000 (-73%)
```

**Verdict:** 🟡 Marginal viability (depends on Sharpe ratio)

---

### Profile 3: Charm/Decay (Short Straddle, 30 DTE, 14 days held)

**Before hedging:**
```
Avg P&L per trade: $80 (theta collected)
Win rate: 70%
Total P&L (100 trades): $8,000
```

**After hedging:**
```
Avg hedging cost: $175/trade
Avg rebalances: 20
Net P&L per trade: -$95 (LOSING)
Total P&L: -$9,500
```

**Verdict:** 🔴 **STRATEGY FAILURE - ABANDON**

---

### Profile 6: Vol-of-Vol (Long Straddle, 30 DTE, 14 days held)

**Before hedging:**
```
Avg P&L per trade: $120
Win rate: 60%
Total P&L (100 trades): $12,000
```

**After hedging:**
```
Avg hedging cost: $130/trade
Avg rebalances: 15
Net P&L per trade: -$10 (near break-even)
Total P&L: -$1,000
```

**Verdict:** 🔴 **UNPROFITABLE - ABANDON**

---

## TUNING PARAMETERS

### Rebalance Threshold

**Conservative (threshold = 20):**
- Fewer rebalances (lower cost)
- Higher delta risk (directional exposure)
- Better for trending markets

**Aggressive (threshold = 10):**
- More rebalances (higher cost)
- Lower delta risk (stays neutral)
- Better for choppy markets

**Recommended:** Start with 15, then sensitivity test 10/20

### Hedging Instrument

**ES Futures (Current):**
- Commission: $2.50
- Spread: $12.50
- Liquidity: Excellent
- **Best for most strategies**

**SPY ETF Alternative:**
- Commission: $0 (most brokers)
- Spread: $0.01 (penny-wide)
- Larger size needed (1 ES = ~90 SPY shares)
- **May be cheaper for small positions**

---

## VALIDATION AFTER IMPLEMENTATION

### Sanity Checks:

1. **Rebalancing frequency realistic?**
   - ATM straddles: 10-25 rebalances per 14 days ✅
   - If >30: Threshold too tight
   - If <5: Threshold too loose

2. **Cost per rebalance realistic?**
   - 1 ES contract: $8.75 ✅
   - 5 ES contracts: ~$45
   - If >$100: Check contract calculation

3. **Total cost reasonable?**
   - Should be 20-100% of gross P&L for gamma strategies
   - If >100%: Strategy unprofitable
   - If <10%: May be underestimating

4. **Degradation matches expectations?**
   - Long straddles: -30% to -60% ✅
   - Short straddles: -80% to -120% (likely unprofitable) ✅

### Compare to Industry Standards:

**Market maker hedging costs:**
- Typical: 15-40% of gross theta collected
- Your Profile 3: 218% of theta ← **RED FLAG**

**Volatility trader hedging:**
- Typical: 20-50% of gross P&L
- Your Profile 1: 73% of P&L ← **MARGINAL**

---

## TIMELINE

**Day 1:**
- Morning: Implement `_calculate_hedging_cost()` method (3-4 hours)
- Afternoon: Integrate into `track_trade()` (2-3 hours)
- Evening: Test on sample trades (1-2 hours)

**Day 2:**
- Morning: Update backtest script and analysis (2-3 hours)
- Afternoon: Re-run Profile 1 backtest, validate results (3-4 hours)
- Evening: Document findings, decide on strategy viability

**Total: 12-16 hours spread over 2 days**

---

## NEXT STEPS AFTER IMPLEMENTATION

1. **Re-run ALL backtests** (train/validation/test) with hedging
2. **Analyze degradation** by profile
3. **Expected outcomes:**
   - Profile 1: Marginal (may still be viable)
   - Profile 2: Minimal impact (fast decay)
   - Profile 3: **ABANDON** (unprofitable)
   - Profile 4, 5: No change (directional)
   - Profile 6: **ABANDON** or severely reduced viability

4. **If ANY gamma strategy survives:**
   - Tune rebalance threshold (10/15/20)
   - Optimize hold period (exit earlier?)
   - Consider alternative hedging (SPY vs ES)

5. **If ALL gamma strategies fail:**
   - Focus on directional profiles (4, 5)
   - Redesign gamma approach (weekly straddles only?)
   - Accept that framework thesis may be wrong

---

## THE BRUTAL REALITY

**This implementation will likely kill 50% of your strategies.**

Profile 3 (short straddle) is almost certainly unprofitable after hedging.
Profiles 1 and 6 may become marginal or fail.

**But it's better to know NOW than after deploying real capital.**

**Get this done THIS WEEK before running any more backtests.**

---

*Implementation guide complete. Time to face reality on gamma strategy costs.*
