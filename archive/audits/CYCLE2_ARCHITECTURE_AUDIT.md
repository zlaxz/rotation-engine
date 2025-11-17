# CYCLE 2: ARCHITECTURE AUDIT REPORT
**Project:** Rotation Engine - Event-Driven Backtest Architecture
**Auditor:** backtest-architect (Quantitative Options Trading Expert)
**Date:** 2025-11-14
**Scope:** Event flow, position tracking, state management, trade lifecycle
**Status:** ⚠️ **7 CRITICAL ISSUES FOUND** - Architecture has fundamental design flaws

---

## EXECUTIVE SUMMARY

**VERDICT: Architecture has CRITICAL flaws that cause P&L corruption and position tracking errors.**

**Key Findings:**
- 🔴 **CRITICAL:** Dual P&L accounting systems create conflicting calculations (ARCH-001)
- 🔴 **CRITICAL:** Portfolio equity based on last day's P&L, not actual position state (ARCH-002)
- 🔴 **CRITICAL:** No multi-position tracking - only supports 1 trade at a time (ARCH-003)
- 🔴 **CRITICAL:** Trade entry happens SAME day as signal (look-ahead bias) (ARCH-004)
- 🟡 **HIGH:** Rotation engine has fundamental architecture mismatch (ARCH-005)
- 🟡 **HIGH:** Greeks never updated after entry (stale risk metrics) (ARCH-006)
- 🟠 **MEDIUM:** Position sizing ignores growing equity (ARCH-007)

**Impact:** Current backtest results are UNRELIABLE. P&L calculations don't reflect actual portfolio state.

---

## CRITICAL ISSUE #1: DUAL P&L ACCOUNTING SYSTEMS (ARCH-001)

**Severity:** 🔴 CRITICAL
**Impact:** P&L calculations conflict, risk of double-counting or missing P&L

### Problem

System has TWO separate P&L tracking mechanisms that calculate the same thing differently:

**Method 1: Trade-based accounting (Trade.py:92-142)**
```python
# In Trade.close()
pnl_legs = sum(qty × (exit - entry) for each leg)
realized_pnl = pnl_legs - entry_commission - exit_commission - hedge_costs

# In Trade.mark_to_market()
unrealized_pnl = sum(qty × (current - entry) for each leg)
return unrealized_pnl - entry_commission - hedge_costs
```

**Method 2: Return-based accounting (simulator.py:268-277, portfolio.py:95-116)**
```python
# In simulator: tracks equity trajectory
total_equity = realized_equity + unrealized_pnl
daily_pnl = total_equity - prev_total_equity
daily_return = daily_pnl / prev_total_equity

# In portfolio: converts returns back to P&L
portfolio_return = sum(weight × profile_return)
daily_pnl = prev_portfolio_value × portfolio_return
```

### Why This Is Critical

1. **Conflicting definitions:**
   - Trade: `pnl = qty × (exit - entry) - costs`
   - Portfolio: `pnl = prev_value × return`
   - These DON'T produce the same result when costs differ

2. **Return calculation ambiguity:**
   - Simulator: `return = pnl / prev_total_equity` (uses equity)
   - Portfolio: Uses returns on arbitrary capital base
   - Returns are NOT invariant to capital allocation

3. **Cost accounting mismatch:**
   - Trade tracks: entry_commission, exit_commission, hedge_cost
   - Portfolio has NO cost tracking - relies on returns that already include costs
   - Can't separate performance from costs in portfolio view

4. **Double-counting risk:**
   - Trade.realized_pnl already includes all costs
   - If portfolio applies costs again to returns → double-count
   - If portfolio doesn't apply costs → missing costs

### Evidence

**File:** `src/trading/trade.py:92-142`
```python
# Direct P&L calculation
pnl_legs = leg_qty × (exit_price - entry_price) × 100
realized_pnl = pnl_legs - commissions - hedge_costs
```

**File:** `src/trading/simulator.py:268-277`
```python
# Return-based calculation
total_equity = realized_equity + unrealized_pnl  # Uses trade's P&L
daily_pnl = total_equity - prev_total_equity    # Delta equity
daily_return = daily_pnl / prev_total_equity    # Convert to return
```

**File:** `src/backtest/portfolio.py:95-116`
```python
# Converts returns BACK to P&L
portfolio_return = sum(weight × profile_return)
daily_pnl = prev_portfolio_value × portfolio_return  # Different calculation!
```

### Consequence

- **Portfolio P&L ≠ Sum(Trade P&L)** due to calculation differences
- Attribution doesn't match actual trade results
- Can't verify portfolio P&L against trade-level P&L
- Errors compound over time as equity base changes

### Fix Required

**Option A: Single source of truth (RECOMMENDED)**
- Portfolio aggregates Trade.realized_pnl and Trade.mark_to_market() directly
- NO return-based calculations
- Direct dollar P&L throughout

**Option B: Consistent return framework**
- Define return as: `(exit_value - entry_cost - costs) / abs(entry_cost)`
- Use consistently everywhere
- Verify portfolio P&L = sum(trade P&L) every day

---

## CRITICAL ISSUE #2: PORTFOLIO EQUITY FROM STALE P&L (ARCH-002)

**Severity:** 🔴 CRITICAL
**Impact:** Portfolio value doesn't reflect actual position values

### Problem

Portfolio equity calculated as:
```python
prev_value = starting_capital
for daily_return in returns:
    pnl = prev_value × daily_return
    curr_value = prev_value + pnl
    prev_value = curr_value
```

**This is WRONG because:**
1. `daily_return` comes from PREVIOUS iteration's mark-to-market
2. Doesn't account for NEW trades entered today
3. Doesn't account for position rolls/exits
4. Compounding based on stale values

### Evidence

**File:** `src/backtest/portfolio.py:95-111`
```python
prev_value = self.starting_capital
for ret in portfolio['portfolio_return']:
    prev_values.append(prev_value)
    pnl = prev_value × ret              # ← Uses PREVIOUS equity
    daily_pnls.append(pnl)
    prev_value = prev_value + pnl       # ← Compounds on stale value
    curr_values.append(prev_value)
```

**File:** `src/trading/simulator.py:268-277`
```python
# Simulator calculates returns correctly
total_equity = realized_equity + unrealized_pnl  # ← Current portfolio value
daily_pnl = total_equity - prev_total_equity
daily_return = daily_pnl / prev_total_equity
```

But portfolio aggregator ignores this and recalculates from returns!

### Consequence

- Portfolio value drifts from actual position values
- Can show positive P&L when trades are losing (or vice versa)
- Daily P&L doesn't match sum of trade-level P&L
- Attribution is meaningless

### Example Failure Case

Day 1:
- Enter trade costing $10,000
- Mark-to-market: $10,200
- Simulator return: 0.02 (2%)

Day 2:
- Portfolio uses: pnl = $1,000,000 × 0.02 = $20,000 ← WRONG
- Actual trade P&L: $200
- Error: 100x overstatement

### Fix Required

Portfolio should aggregate ACTUAL position values:
```python
for date in dates:
    # Get all open positions on this date
    position_values = [trade.mark_to_market(prices[date])
                      for trade in open_trades]
    portfolio_value = cash + sum(position_values)
    daily_pnl = portfolio_value - prev_portfolio_value
```

---

## CRITICAL ISSUE #3: NO MULTI-POSITION SUPPORT (ARCH-003)

**Severity:** 🔴 CRITICAL
**Impact:** Can't track 6 simultaneous profiles (fundamental requirement failure)

### Problem

Simulator tracks only ONE trade at a time:

**File:** `src/trading/simulator.py:140-144`
```python
current_trade: Optional[Trade] = None  # ← SINGLE trade only

for idx, row in self.data.iterrows():
    if current_trade is None:  # Only enter if no position
        if entry_logic(row, current_trade):
            current_trade = trade_constructor(row, trade_id)
```

**But rotation engine requires 6 simultaneous positions:**
- Allocation: Profile 1 = 20%, Profile 2 = 15%, ..., Profile 6 = 10%
- Need to track ALL active positions simultaneously
- Need to mark-to-market ALL positions daily
- Need to exit/enter positions independently

### Architecture Mismatch

**What rotation engine expects:**
```python
portfolio_state = {
    'profile_1': Trade(...),  # LDG position
    'profile_2': Trade(...),  # SDG position
    'profile_3': None,        # No position
    'profile_4': Trade(...),  # Vanna position
    ...
}
```

**What simulator provides:**
```python
current_trade = Trade(...)  # Only 1 position
```

### Consequence

- Rotation engine CAN'T work with current simulator
- Each profile runs independently (separate backtests)
- Portfolio aggregator tries to combine them POST-HOC by weighting returns
- This is fundamentally wrong:
  - Can't track actual capital allocated to each profile
  - Can't handle portfolio-level risk constraints
  - Can't model real trading (would have all positions open simultaneously)

### Evidence of Mismatch

**File:** `src/backtest/engine.py:154-157`
```python
# Runs each profile INDEPENDENTLY
for profile_name, runner in runners.items():
    profile_results, trades = runner(data, profile_scores, ...)
    results[profile_name] = profile_results
```

Then tries to combine with weights:
**File:** `src/backtest/portfolio.py:88`
```python
portfolio[return_col] = weight × profile_return  # Post-hoc weighting
```

**This doesn't model actual trading:**
- In reality: Open Profile 1 with $200K, Profile 2 with $150K simultaneously
- In simulator: Run Profile 1 backtest separately, Profile 2 separately, weight results
- These are NOT the same (path-dependent, timing issues, risk interactions)

### Fix Required

**Major architecture change needed:**

Option A: Multi-position simulator
```python
class MultiPositionSimulator:
    def __init__(self):
        self.positions: Dict[str, Trade] = {}  # Multiple positions
        self.cash = starting_capital

    def simulate_day(self, date, allocations):
        # Mark all positions to market
        total_unrealized = 0
        for profile, trade in self.positions.items():
            if trade:
                total_unrealized += trade.mark_to_market(prices)

        # Calculate available capital
        equity = self.cash + total_unrealized

        # Allocate to each profile
        for profile, weight in allocations.items():
            target_capital = equity × weight
            # Enter/exit/size position to match target
```

Option B: Portfolio-level simulator (RECOMMENDED)
- Don't run 6 separate backtests
- Run ONE backtest with portfolio state
- Track all 6 positions simultaneously
- Apply rotation logic in real-time

---

## CRITICAL ISSUE #4: SAME-DAY ENTRY (LOOK-AHEAD BIAS) (ARCH-004)

**Severity:** 🔴 CRITICAL
**Impact:** Uses future information (next day's price) for entry decision

### Problem

Entry logic executed with t+1 fill delay, but check uses WRONG timing:

**File:** `src/trading/simulator.py:251-260`
```python
# Last day check
is_last_row = idx == total_rows - 1

if (current_trade is None
    and not pending_entry_signal
    and not is_last_row           # ← BUG: allows entry on second-to-last day
    and entry_logic(row, current_trade)):
    pending_entry_signal = True
```

**Next iteration:**
```python
if pending_entry_signal and current_trade is None:
    pending_entry_signal = False
    current_trade = trade_constructor(row, trade_id)  # Uses CURRENT row
```

### Why This Is Wrong

**Timeline:**
- Day T: entry_logic(row_T) returns True → set pending_entry_signal
- Day T+1: Uses row_T+1 data to construct trade

**But entry_logic already sees Day T data:**
- Profile scores computed from Day T features
- Regime classification from Day T signals
- Then uses Day T+1 price for entry

**This is look-ahead bias if:**
- entry_logic uses any features that depend on Day T close price
- Trade constructor uses Day T+1 open (correct) but entry decision saw T close (wrong)

### Evidence

**File:** `src/trading/profiles/profile_1.py:52-82`
```python
def entry_logic(self, row: pd.Series, current_trade: Optional[Trade]) -> bool:
    # Uses row data (Day T)
    score = row.get('profile_1_score', 0.0)  # ← Computed from Day T features
    regime = int(row.get('regime', 0))       # ← Classified from Day T data

    if score < self.score_threshold:
        return False
    if regime not in self.regime_filter:
        return False
    return True  # Decision made with Day T info
```

**Then:**
```python
def trade_constructor(self, row: pd.Series, trade_id: str) -> Trade:
    spot = row['close']  # ← Uses Day T+1 close price
    atm_strike = round(spot / 5) * 5
```

**Problem:** Decision uses Day T data, execution uses Day T+1 price.

### Correct Implementation

**Option A: Signal day T, entry day T+1 with T+1 data**
```python
# Day T: Check entry logic
if entry_logic_uses_yesterday_data(row_T_minus_1):
    signal_entry = True

# Day T+1: Execute entry
if signal_entry:
    trade = construct_trade(row_T_plus_1)  # Uses only T+1 data
```

**Option B: EOD signal, next-day-open execution**
```python
# Day T EOD: entry_logic uses Day T close
signal_entry = entry_logic(row_T)

# Day T+1 open: Execute with T+1 open price
trade.entry_price = get_next_day_open(T+1)
```

### Fix Required

Audit all entry_logic functions:
1. Document what data they use (T close? T features?)
2. Verify trade_constructor uses ONLY T+1 data
3. Add explicit timing comments
4. Consider using separate feature rows (yesterday's features for decision, today's price for execution)

---

## HIGH ISSUE #5: ROTATION ENGINE ARCHITECTURE MISMATCH (ARCH-005)

**Severity:** 🟡 HIGH
**Impact:** Fundamental design doesn't support true rotation

### Problem

System is NOT a rotation engine. It's "6 independent strategy runners + post-hoc weighting."

**Current Architecture:**
```
RotationEngine:
  1. Run profile_1_backtest() independently → results_1
  2. Run profile_2_backtest() independently → results_2
  ...
  6. Run profile_6_backtest() independently → results_6
  7. Calculate allocation weights
  8. Weight returns: portfolio_return = Σ(weight_i × return_i)
```

**Problems:**
1. Each profile backtest uses FULL capital (no constraints)
2. Allocation weights applied POST-HOC (not during backtest)
3. Can't model real portfolio behavior:
   - Capital constraints (100% total allocation)
   - Timing of rotations (when do you exit Profile 1 to enter Profile 2?)
   - Transaction costs of rotation (exit costs + entry costs)
   - Cash drag while positions are being rotated

### What Real Rotation Looks Like

**True Portfolio State:**
```
Day 1:
  Cash: $100K
  Profile 1: Long straddle, cost $200K, weight 20% → allocated $200K
  Profile 2: Long strangle, cost $150K, weight 15% → allocated $150K
  ...
  Total allocated: $1M
  Leverage: 10x (options on $1M capital)

Day 2 (regime change):
  Old allocation: [20%, 15%, 10%, 25%, 20%, 10%]
  New allocation: [10%, 25%, 15%, 20%, 15%, 15%]
  Actions:
    - Reduce Profile 1: 20% → 10% (exit half position, pay costs)
    - Increase Profile 2: 15% → 25% (add position, pay costs)
    - Calculate rotation costs
  Updated positions reflect new allocation
```

**Current implementation can't model this because:**
- No unified portfolio state
- No rotation logic (when to rebalance?)
- No transaction costs for rotation
- Each profile thinks it has 100% of capital

### Evidence

**File:** `src/backtest/engine.py:246-302`
```python
def _run_profile_backtests(self, data, profile_scores):
    results = {}
    for profile_name, runner in runners.items():
        # Each runner gets FULL data and FULL capital
        profile_results, trades = runner(
            data=data,  # Full dataset
            profile_scores=profile_scores,
            score_threshold=config['threshold'],
            regime_filter=config['regimes']
        )
        results[profile_name] = profile_results  # Independent results
    return results
```

Then weights applied:
**File:** `src/backtest/portfolio.py:88`
```python
portfolio[return_col] = weight_series × profile_return  # Post-hoc multiplication
```

### Missing Components

1. **Rotation Logic:** When to rebalance positions?
   - On allocation weight change > threshold (5%)?
   - On regime change?
   - Daily? Weekly?
   - No code implements this

2. **Rebalancing Execution:**
   - How to calculate target position sizes?
   - How to size new positions?
   - When to exit old positions?
   - Code doesn't exist

3. **Rotation Costs:**
   - Exit costs for old positions
   - Entry costs for new positions
   - Market impact from rebalancing
   - Not modeled anywhere

4. **Portfolio Risk Management:**
   - Total leverage constraint
   - Greeks limits at portfolio level
   - Margin requirements
   - Not implemented

### Fix Required

**Requires major architectural redesign:**

Option A: True portfolio simulator
```python
class PortfolioRotationSimulator:
    def __init__(self, starting_capital):
        self.cash = starting_capital
        self.positions: Dict[str, Trade] = {}  # All active positions
        self.target_allocations = {}

    def simulate_day(self, date, new_allocations):
        # 1. Mark all positions to market
        total_value = self.cash + sum(position.mtm() for position in self.positions.values())

        # 2. Calculate target sizes
        for profile, weight in new_allocations.items():
            target_size = total_value × weight
            current_size = self.positions[profile].value if profile in self.positions else 0

            # 3. Rebalance if needed
            if abs(target_size - current_size) > threshold:
                self.rebalance(profile, current_size, target_size)

        # 4. Track rotation costs
        self.record_rotation_costs()
```

Option B: Accept post-hoc weighting but document limitations
- Add big warning: "Results don't reflect actual portfolio behavior"
- Document missing: rotation costs, timing effects, capital constraints
- Use only for hypothesis testing, not production

---

## HIGH ISSUE #6: STALE GREEKS (NEVER UPDATED) (ARCH-006)

**Severity:** 🟡 HIGH
**Impact:** Risk metrics (delta, gamma, vega, theta) never updated after entry

### Problem

Greeks calculated ONCE at entry, never updated:

**File:** `src/trading/simulator.py:176-182`
```python
# At entry
current_trade.calculate_greeks(
    underlying_price=spot,
    current_date=current_date,
    implied_vol=vix_proxy,
    risk_free_rate=0.05
)
```

Then NEVER updated except during delta hedge:
**File:** `src/trading/simulator.py:653-662`
```python
def _perform_delta_hedge(self, trade: Trade, row: pd.Series) -> float:
    # Update Greeks for hedging decision
    trade.calculate_greeks(...)

    # Use net_delta for hedge calculation
    # But Greeks NOT stored back to trade for risk tracking
```

### Consequences

1. **Stale delta:** Can't track real delta exposure as underlying moves
2. **Stale gamma:** Can't see convexity changes as position ages
3. **Stale theta:** Decay rate changes as expiration approaches
4. **Stale vega:** Volatility sensitivity changes with moneyness

5. **Delta hedging uses updated Greeks but trade object has stale Greeks**
   - Hedge decisions based on current Greeks
   - Position tracking shows entry Greeks
   - Mismatch between hedging and reporting

### Evidence

**Greeks lifecycle:**

1. Entry (simulator.py:176-182): Greeks calculated ✅
2. Daily loop (simulator.py:148-290): Greeks NOT updated ❌
3. Delta hedge (simulator.py:653-662): Greeks calculated temporarily, discarded ❌
4. Exit (simulator.py:226-239): Greeks not used ❌

**Trade object Greeks never change:**
```python
trade.net_delta  # Set at entry, frozen forever
trade.net_gamma  # Set at entry, frozen forever
trade.net_vega   # Set at entry, frozen forever
trade.net_theta  # Set at entry, frozen forever
```

### Fix Required

Update Greeks daily in simulation loop:

```python
# In simulator.simulate()
if current_trade is not None and current_trade.is_open:
    # Update Greeks for risk tracking
    current_trade.calculate_greeks(
        underlying_price=spot,
        current_date=current_date,
        implied_vol=vix_proxy,
        risk_free_rate=0.05
    )

    # Record Greeks for analysis
    results.append({
        'date': current_date,
        'net_delta': current_trade.net_delta,
        'net_gamma': current_trade.net_gamma,
        'net_vega': current_trade.net_vega,
        'net_theta': current_trade.net_theta
    })
```

---

## MEDIUM ISSUE #7: POSITION SIZING IGNORES EQUITY GROWTH (ARCH-007)

**Severity:** 🟠 MEDIUM
**Impact:** Trade sizes don't scale with portfolio performance

### Problem

Position sizing uses fixed capital:

**File:** `src/trading/simulator.py:43`
```python
capital_per_trade: float = 100_000.0  # Fixed
```

Used for return calculation:
**File:** `src/trading/simulator.py:271-275`
```python
if prev_total_equity > 0:
    daily_return = daily_pnl / prev_total_equity
else:
    daily_return = daily_pnl / max(self.config.capital_per_trade, 1.0)
```

But trade constructor doesn't use this:
**File:** `src/trading/profiles/profile_1.py:141`
```python
trade = create_straddle_trade(
    strike=atm_strike,
    expiry=expiry,
    dte=(expiry - entry_date).days,
    quantity=1  # ← FIXED quantity, ignores capital
)
```

### Consequence

- Portfolio at $1.5M trades same size as at $0.5M
- Doesn't compound gains
- Risk management doesn't scale with performance
- Return calculation assumes fixed capital but trades don't use it

### Fix Required

Option A: Scale quantity by equity
```python
def trade_constructor(self, row: pd.Series, trade_id: str) -> Trade:
    spot = row['close']

    # Get current equity from portfolio state
    current_equity = self.portfolio.get_equity()

    # Calculate quantity to match target allocation
    target_cost = current_equity × self.allocation_pct
    estimated_straddle_cost = 2 × atm_option_price
    quantity = int(target_cost / estimated_straddle_cost)

    return create_straddle_trade(..., quantity=quantity)
```

Option B: Normalize to fixed capital (current approach)
- Accept that trades are fixed size
- Use capital_per_trade as normalization constant
- Document: "Returns are per $100K allocated, actual $ P&L may differ"

---

## ARCHITECTURAL RECOMMENDATIONS

### Immediate Fixes (Before Next Backtest)

1. **ARCH-004 (Look-ahead bias):** Add timing audit
   - Document when each feature is available
   - Verify entry_logic uses only T-1 data
   - Verify trade_constructor uses only T data

2. **ARCH-001 (Dual P&L):** Choose single accounting method
   - Recommend: Direct dollar P&L (no returns)
   - Add validation: portfolio_pnl = sum(trade_pnl)

3. **ARCH-006 (Stale Greeks):** Update Greeks daily
   - Add to simulation loop
   - Record for analysis

### Medium-Term Refactoring (Before Production)

4. **ARCH-002 (Portfolio equity):** Fix equity calculation
   - Calculate from actual position values
   - Don't compound returns (use actual mark-to-market)

5. **ARCH-007 (Position sizing):** Implement capital scaling
   - Link trade size to portfolio equity
   - Or document fixed-size limitation

### Long-Term Redesign (Before Live Trading)

6. **ARCH-003 (Multi-position):** Build true multi-position simulator
   - Track multiple simultaneous positions
   - Portfolio-level risk management
   - Realistic capital allocation

7. **ARCH-005 (Rotation):** Implement true rotation logic
   - When to rebalance
   - How to size positions
   - Transaction costs of rotation
   - Portfolio-level constraints

---

## STATE CONSISTENCY CHECKS

### Add These Validation Checks

```python
# After each simulation day
def validate_portfolio_state(self):
    """Verify portfolio state is consistent."""

    # Check 1: Portfolio equity = cash + positions
    calculated_equity = self.cash + sum(pos.mark_to_market()
                                       for pos in self.positions.values())
    assert abs(self.equity - calculated_equity) < 0.01, \
        f"Equity mismatch: {self.equity} vs {calculated_equity}"

    # Check 2: Realized P&L = sum(closed trade P&L)
    calculated_realized = sum(trade.realized_pnl
                            for trade in self.closed_trades)
    assert abs(self.realized_pnl - calculated_realized) < 0.01, \
        f"Realized P&L mismatch"

    # Check 3: Portfolio Greeks = sum(position Greeks)
    calculated_delta = sum(pos.net_delta for pos in self.positions.values())
    assert abs(self.net_delta - calculated_delta) < 0.01, \
        f"Delta mismatch"

    # Check 4: Allocated % <= 100%
    total_allocated = sum(self.allocations.values())
    assert total_allocated <= 1.0 + 1e-6, \
        f"Over-allocated: {total_allocated*100:.1f}%"
```

---

## EVENT FLOW DIAGRAM

### Current (BROKEN) Architecture

```
RotationEngine.run()
│
├─> Load data (data.py)
│
├─> Compute profile scores (detectors.py)
│
├─> Run 6 INDEPENDENT backtests (NO communication)
│   ├─> Profile 1 backtest (simulator.py)
│   │   └─> Uses FULL capital, no portfolio awareness
│   ├─> Profile 2 backtest (simulator.py)
│   │   └─> Uses FULL capital, no portfolio awareness
│   ...
│   └─> Profile 6 backtest (simulator.py)
│       └─> Uses FULL capital, no portfolio awareness
│
├─> Calculate allocations (rotation.py)
│   └─> Weights based on scores + regime
│       (But backtests already ran - can't use these!)
│
└─> Aggregate with POST-HOC weighting (portfolio.py)
    └─> portfolio_return = Σ(weight × profile_return)
        (Pretends this represents actual portfolio)
```

**Problem:** Allocations calculated AFTER backtests complete. Can't affect trade sizing or timing.

### Correct Architecture (NEEDED)

```
PortfolioRotationSimulator.run()
│
├─> Initialize portfolio state
│   ├─> Cash: $1M
│   └─> Positions: {} (empty)
│
└─> FOR EACH DAY:
    │
    ├─> Mark all positions to market
    │   ├─> Calculate position values
    │   ├─> Update Greeks
    │   └─> Calculate unrealized P&L
    │
    ├─> Calculate portfolio equity
    │   └─> equity = cash + Σ(position_values)
    │
    ├─> Compute profile scores (detectors.py)
    │
    ├─> Calculate target allocations (rotation.py)
    │   ├─> desirability = score × regime_compatibility
    │   └─> weights = normalize(desirability)
    │
    ├─> Check for rotations needed
    │   ├─> FOR EACH PROFILE:
    │   │   ├─> current_allocation = position_value / equity
    │   │   ├─> target_allocation = weights[profile]
    │   │   └─> IF |current - target| > threshold:
    │   │       └─> Rebalance needed
    │
    ├─> Execute rebalancing
    │   ├─> Exit positions (pay exit costs)
    │   ├─> Enter new positions (pay entry costs)
    │   └─> Update cash
    │
    └─> Record daily state
        ├─> equity, P&L, positions
        ├─> allocations, rotation costs
        └─> Greeks, risk metrics
```

---

## TRADE LIFECYCLE VERIFICATION

### Profile 1 Example

**Entry Flow:**
```
1. entry_logic(row_T) → True (score > threshold, regime match)
   - Uses: row_T.profile_1_score (from features at T)
   - Uses: row_T.regime (from signals at T)

2. pending_entry_signal = True

3. Next day (T+1):
   trade = trade_constructor(row_T+1, trade_id)
   - Uses: row_T+1.close (spot price)
   - ⚠️ BUG: Should use T+1 open or T EOD for consistency

4. Get entry prices (simulator._get_entry_prices)
   - Tries real Polygon data
   - Falls back to toy pricing
   - Applies spread model (long pays ask, short receives bid)

5. Calculate entry commission
   - Based on total contracts + short flag

6. Calculate Greeks
   - Uses T+1 spot, VIX proxy
   - Greeks frozen (never updated) ← ARCH-006

7. trade.is_open = True
```

**Holding Flow:**
```
For each day while open:
1. Check exit conditions
   - Custom exit_logic (regime change)
   - DTE threshold (< 5 days)
   - Max loss (> 50% of entry cost)
   - Max days (> 120 days)

2. Mark to market
   - Get current prices (mid)
   - Calculate unrealized P&L

3. Delta hedge (if enabled)
   - Update Greeks (temporarily)
   - Calculate hedge quantity
   - Add hedge cost

4. Record daily state
   - daily_pnl, daily_return
   - position_open flag
```

**Exit Flow:**
```
1. Exit triggered by one of:
   - exit_logic() → True
   - DTE threshold
   - Max loss
   - Max days

2. Get exit prices (simulator._get_exit_prices)
   - Tries real Polygon data
   - Reverse of entry (long sells at bid, short covers at ask)

3. Calculate exit commission

4. trade.close(exit_date, exit_prices, reason)
   - Calculates realized P&L:
     pnl = Σ(qty × (exit - entry)) - entry_comm - exit_comm - hedge_costs

5. Append to closed trades list

6. Set current_trade = None (ready for new trade)
```

**⚠️ Missing:** Greeks never updated during holding (ARCH-006)
**⚠️ Issue:** exit_logic sees current day data but exit happens same day (potential bias)

---

## DATA DEPENDENCY ANALYSIS

### What Data Is Available When?

**Day T-1 EOD:**
- SPY: open, high, low, close, volume (complete)
- Features: RV, ATR, MA, slopes (complete)
- Regime: classification (complete)
- Profile scores: computed from T-1 features (complete)

**Day T open:**
- SPY: open price available
- Options: open prices available (from Polygon day agg = open/high/low/close)
- Trade decision: Can use ALL of T-1 data + T open

**Day T intraday:**
- SPY: high, low updating
- Options: bid/ask updating
- Cannot see until EOD

**Day T close:**
- SPY: close price available
- Options: close prices available
- Features: RV, ATR compute from T close
- Regime: classifies using T data
- Profile scores: computed from T features

### Current Implementation Timing

**Entry decision (entry_logic):**
- Called with row_T data
- Uses profile_1_score (from T features including T close)
- Uses regime (from T classification including T close)
- ⚠️ **USES T CLOSE DATA**

**Trade construction (trade_constructor):**
- Called next day with row_T+1 data
- Uses row_T+1.close as spot
- ⚠️ **INCONSISTENT:** Decision sees T close, execution uses T+1 close

**Correct timing:**

Option A: T-1 data for decision, T execution
```python
# Day T: Use only T-1 data for decision
if entry_logic(features_T_minus_1, regime_T_minus_1):
    pending_entry = True

# Day T+1: Execute with T open or T close
trade = construct_trade(spot=row_T.open or row_T.close)
```

Option B: T EOD decision, T+1 open execution
```python
# Day T EOD: Use T data for decision
if entry_logic(row_T):  # Uses T close
    pending_entry = True

# Day T+1 open: Execute with T+1 open
trade = construct_trade(spot=row_T_plus_1.open)
```

**Current implementation is neither - it's inconsistent.**

---

## FILES REQUIRING CHANGES

### Critical (Must Fix Before Next Backtest)

1. **src/trading/simulator.py**
   - Fix: Update Greeks daily (ARCH-006)
   - Fix: Add timing documentation (ARCH-004)
   - Fix: Add state validation checks

2. **src/backtest/portfolio.py**
   - Fix: Calculate equity from actual positions (ARCH-002)
   - Fix: Choose single P&L accounting method (ARCH-001)
   - Add: Validation that portfolio_pnl = sum(trade_pnl)

3. **src/trading/profiles/profile_*.py** (all 6)
   - Audit: What data does entry_logic use?
   - Document: Timing assumptions
   - Verify: No look-ahead bias (ARCH-004)

### Medium Priority (Before Production)

4. **src/backtest/rotation.py**
   - Add: Rotation trigger logic (ARCH-005)
   - Add: Rebalancing execution (ARCH-005)
   - Add: Rotation cost tracking (ARCH-005)

5. **src/trading/trade.py**
   - Consider: Standardize P&L calculation (ARCH-001)
   - Add: Greeks history tracking (ARCH-006)

### Long-Term Redesign

6. **NEW: src/backtest/portfolio_simulator.py**
   - Implement: Multi-position tracking (ARCH-003)
   - Implement: True rotation logic (ARCH-005)
   - Implement: Portfolio-level risk management

---

## TESTING RECOMMENDATIONS

### Unit Tests Needed

```python
# Test dual P&L consistency
def test_trade_pnl_matches_portfolio_pnl():
    """Verify Trade.realized_pnl = portfolio calculation."""
    pass

# Test equity calculation
def test_portfolio_equity_from_positions():
    """Verify equity = cash + sum(position_values)."""
    pass

# Test Greeks updates
def test_greeks_updated_daily():
    """Verify Greeks change as underlying moves."""
    pass

# Test multi-position
def test_simultaneous_positions():
    """Verify can track 6 positions at once."""
    pass

# Test timing
def test_no_look_ahead_in_entry():
    """Verify entry_logic doesn't use future data."""
    pass
```

### Integration Tests Needed

```python
# Test complete trade lifecycle
def test_trade_lifecycle_timing():
    """Verify: signal day T, entry day T+1, Greeks updated, exit correct."""
    pass

# Test rotation execution
def test_portfolio_rotation():
    """Verify: old position exits, new position enters, costs tracked."""
    pass

# Test state consistency
def test_portfolio_state_consistency():
    """Verify: equity=cash+positions, pnl=sum(trades), allocated<=100%."""
    pass
```

---

## CONCLUSION

**System has fundamental architectural flaws that make current results unreliable.**

**Must fix before trusting backtest:**
1. ARCH-004: Look-ahead bias in entry timing
2. ARCH-001: Choose single P&L accounting method
3. ARCH-006: Update Greeks daily
4. ARCH-002: Fix portfolio equity calculation

**Must redesign before live trading:**
5. ARCH-003: Multi-position tracking
6. ARCH-005: True rotation logic with costs
7. ARCH-007: Position sizing that scales with equity

**Current -3.29 Sharpe is UNRELIABLE due to these issues.**

Re-run backtest only after fixing CRITICAL issues (ARCH-001, 002, 004, 006).

---

**Next Steps:**
1. Fix ARCH-004 (timing) - Add explicit timing audit
2. Fix ARCH-006 (Greeks) - Update daily in simulation loop
3. Fix ARCH-001 (P&L) - Choose direct dollar accounting
4. Fix ARCH-002 (Equity) - Calculate from positions
5. Add state validation checks
6. Re-run backtest
7. If results still poor, consider ARCH-003/005 (major redesign)
