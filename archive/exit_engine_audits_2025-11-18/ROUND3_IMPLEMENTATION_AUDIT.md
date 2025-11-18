# ROUND 3 IMPLEMENTATION AUDIT REPORT
**Date:** 2025-11-18
**Auditor:** Claude (Strategy Logic Auditor Mode)
**Target:** Post-bug-fix implementation verification
**Objective:** ZERO BUGS or complete bug catalog
**Methodology:** Manual verification, calculation walkthroughs, edge case testing

---

## AUDIT SCOPE

**Files Audited:**
1. `/Users/zstoc/rotation-engine/scripts/backtest_train.py` (540 lines)
2. `/Users/zstoc/rotation-engine/scripts/backtest_validation.py` (584 lines)
3. `/Users/zstoc/rotation-engine/scripts/backtest_test.py` (620 lines)
4. `/Users/zstoc/rotation-engine/src/analysis/trade_tracker.py` (357 lines)
5. `/Users/zstoc/rotation-engine/src/trading/exit_engine.py` (95 lines)
6. `/Users/zstoc/rotation-engine/src/trading/execution.py` (321 lines)
7. `/Users/zstoc/rotation-engine/src/analysis/metrics.py` (406 lines)

**Focus Areas:**
- Verify 10 recent bug fixes didn't introduce new bugs
- Off-by-one errors
- Calculation accuracy (Greeks, P&L, metrics)
- Edge case handling
- NaN propagation
- Index errors
- Type mismatches
- Sign convention errors

---

## SECTION 1: EXPIRY CALCULATION LOGIC

### Code Location: `backtest_train.py` lines 233-258

```python
def get_expiry_for_dte(entry_date: date, dte_target: int) -> date:
    target_date = entry_date + timedelta(days=dte_target)

    days_to_friday = (4 - target_date.weekday()) % 7
    if days_to_friday == 0:
        expiry = target_date
    else:
        next_friday = target_date + timedelta(days=days_to_friday)
        prev_friday = next_friday - timedelta(days=7)

        if abs((next_friday - target_date).days) < abs((prev_friday - target_date).days):
            expiry = next_friday
        else:
            expiry = prev_friday

    return expiry
```

### Manual Verification:

**Test Case 1: Entry = Monday, DTE = 75**
- Entry: 2020-01-06 (Monday, weekday=0)
- Target: 2020-01-06 + 75 = 2020-03-21 (Saturday, weekday=5)
- days_to_friday = (4 - 5) % 7 = -1 % 7 = 6 days
- next_friday = 2020-03-21 + 6 days = 2020-03-27 (Friday)
- prev_friday = 2020-03-27 - 7 = 2020-03-20 (Friday)
- Distance to next: |6| = 6 days
- Distance to prev: |1| = 1 day
- **Result: 2020-03-20 (closer)** ✅

**Test Case 2: Entry = Wednesday, target lands on Friday**
- Entry: 2020-01-08 (Wednesday, weekday=2)
- Target: 2020-01-08 + 7 = 2020-01-15 (Wednesday, weekday=2)
- Wait, DTE=7 should land on following week
- Let me recalculate: Entry Wed Jan 8, +7 days = Wed Jan 15
- weekday() for Jan 15, 2020: (weekday=2, Wednesday)
- days_to_friday = (4 - 2) % 7 = 2 days
- next_friday = Jan 15 + 2 = Jan 17 (Friday)
- prev_friday = Jan 17 - 7 = Jan 10 (Friday)
- Distance to next: 2 days
- Distance to prev: 5 days
- **Result: Jan 17 (closer)** ✅

**Test Case 3: Target IS Friday**
- Entry: 2020-01-06 (Monday)
- DTE: 4 days → Target: Jan 10 (Friday, weekday=4)
- days_to_friday = (4 - 4) % 7 = 0
- **Result: Jan 10 (target itself)** ✅

### Edge Cases:

**❌ POTENTIAL BUG #1: DTE = 0**
- Entry = Friday, DTE = 0
- Target = same Friday
- days_to_friday = (4 - 4) % 7 = 0
- **Result: Same day expiry** ← This works, but is this intentional?
- **Severity: LOW** - Edge case, unlikely in practice

**✅ VERIFIED: Leap years handled correctly** (timedelta is date arithmetic, handles this automatically)

**✅ VERIFIED: Year boundaries** (timedelta handles automatically)

### Verdict: **CLEAN** (with minor edge case note)

---

## SECTION 2: STRIKE CALCULATION FOR OTM OPTIONS

### Code Location: `backtest_train.py` lines 312-318

```python
# Calculate strike based on profile structure
if profile_id == 'Profile_5_SKEW':
    # 5% OTM put: strike below spot
    strike = round(spot * 0.95)
else:
    # ATM for all other profiles
    strike = round(spot)
```

### Manual Verification:

**Test Case 1: Profile_5_SKEW with SPY at $450.67**
- Calculation: round(450.67 * 0.95) = round(428.1365) = 428
- Actual OTM: (450.67 - 428) / 450.67 = 5.03% ✅
- **CORRECT**

**Test Case 2: Profile_5_SKEW with SPY at $299.99**
- Calculation: round(299.99 * 0.95) = round(284.9905) = 285
- Actual OTM: (299.99 - 285) / 299.99 = 5.00% ✅
- **CORRECT**

**Test Case 3: ATM with SPY at $450.67**
- Calculation: round(450.67) = 451
- Moneyness: |451 - 450.67| / 450.67 = 0.07% ✅
- **CORRECT**

### Edge Cases:

**✅ VERIFIED: Rounding doesn't break ITM/OTM classification**
- OTM put: strike = 0.95 * spot → always < spot → always OTM ✅
- ATM: round(spot) → at most 0.5 off → still considered ATM ✅

**✅ VERIFIED: Strike is integer** (options trade on whole-dollar strikes for SPY) ✅

### Verdict: **CLEAN**

---

## SECTION 3: SHIFT OPERATIONS FOR LOOK-AHEAD BIAS

### Code Location: `backtest_train.py` lines 89-114

```python
# Calculate derived features
# CRITICAL: Shift by 1 to avoid look-ahead bias

spy['return_1d'] = spy['close'].pct_change().shift(1)
spy['return_5d'] = spy['close'].pct_change(5).shift(1)
spy['return_10d'] = spy['close'].pct_change(10).shift(1)
spy['return_20d'] = spy['close'].pct_change(20).shift(1)

spy['MA20'] = spy['close'].shift(1).rolling(20).mean()
spy['MA50'] = spy['close'].shift(1).rolling(50).mean()
```

### Manual Verification - Walk-Through Timeline:

```
Day 0: close=100
Day 1: close=101
Day 2: close=102

Without shift:
  return_1d[1] = (101-100)/100 = 1.0%  (knows Day 1 close)
  return_1d[2] = (102-101)/101 = 0.99% (knows Day 2 close)

With shift(1):
  return_1d[0] = NaN
  return_1d[1] = NaN  (shifted from Day 0's pct_change which is NaN)
  return_1d[2] = 1.0% (shifted from Day 1's calculation)
```

**Wait, this is WRONG! Let me recalculate:**

```python
spy['close'] = [100, 101, 102, 103]

# Step 1: pct_change()
pct = spy['close'].pct_change()
# pct = [NaN, 1.0%, 0.99%, 0.98%]

# Step 2: shift(1)
return_1d = pct.shift(1)
# return_1d = [NaN, NaN, 1.0%, 0.99%]
```

**On Day 2 (index=2), return_1d = 1.0% = Day 1's return**

**This means: On Day 2, we know Day 0 → Day 1 price change, but NOT Day 1 → Day 2 change** ✅

**Entry logic: Evaluate condition on Day 2, enter at Day 2 close**
- Condition uses return_1d[2] = 1.0% (Day 0→Day 1 change)
- Enter at close[2] = 102
- **NO LOOK-AHEAD** ✅

### ❌ **CRITICAL BUG #2: MA Calculation Has Look-Ahead**

```python
spy['MA20'] = spy['close'].shift(1).rolling(20).mean()
```

**Manual calculation:**
```
Day 20: We calculate MA20[20] = mean(close[0:20])
        But close[0:20] INCLUDES close[19]
        On Day 20, we DON'T know close[20] yet ✅

BUT WAIT: rolling(20) on shifted series:

shifted = spy['close'].shift(1)
# shifted[0] = NaN
# shifted[1] = close[0]
# shifted[20] = close[19]

MA20[20] = mean(shifted[1:21]) = mean(close[0:20])
```

**On Day 20, MA20 uses close[0] through close[19] - this is CORRECT** ✅

**Re-verification: Is shift BEFORE or AFTER rolling?**
- Code: `spy['close'].shift(1).rolling(20).mean()`
- Order: shift FIRST, then rolling
- shifted[20] = close[19]
- rolling window [1:21] on shifted = close[0:20]
- **NO LOOK-AHEAD** ✅

### Verdict: **CLEAN** (initial suspicion resolved upon careful analysis)

---

## SECTION 4: WARMUP PERIOD SUFFICIENCY

### Code Location: `backtest_train.py` lines 55-138

```python
WARMUP_DAYS = 60
warmup_start = TRAIN_START - timedelta(days=90)  # 90 calendar days = ~60 trading days

# Filter to train period AFTER calculating features
spy_with_warmup = spy.copy()
spy = spy[spy['date'] >= TRAIN_START].reset_index(drop=True)

# Verify warmup provided clean features
first_ma50 = spy['MA50'].iloc[0]
if pd.isna(first_ma50):
    raise ValueError(f"WARMUP INSUFFICIENT: MA50 still NaN at train period start!")
```

### Manual Verification:

**MA50 needs 50 trading days of data BEFORE train start:**
- Train start: 2020-01-01 (approx trading day)
- Warmup: 90 calendar days = ~63 trading days (252/365 * 90 ≈ 62)
- MA50 calculation at train start:
  - Uses shifted close, rolling 50
  - Needs data from [train_start - 51 trading days : train_start - 1]
  - Warmup provides ~63 days
  - **63 > 50 → SUFFICIENT** ✅

**But what about return_20d?**
- return_20d = pct_change(20).shift(1)
- pct_change(20) needs 21 days of data
- shift(1) pushes back by 1
- Total lookback: 22 trading days
- **63 > 22 → SUFFICIENT** ✅

**Verification check in code:**
```python
first_ma50 = spy['MA50'].iloc[0]
if pd.isna(first_ma50):
    raise ValueError(...)
```

**This catches insufficient warmup** ✅

### ❌ **POTENTIAL BUG #3: Hardcoded 90 calendar days**

What if:
- Market closed for extended period (COVID, etc.)
- Holidays cluster near start
- 90 calendar days might not yield 60 trading days

**Test Case: Market closed 2020-12-24, 12-25, 12-31, 2021-01-01**
- If warmup_start = Oct 2, 2020
- Train_start = Jan 1, 2021
- Need to count actual trading days in warmup

**Current code assumes ~70% of calendar days are trading days**
- Reality: 252/365 = 69% ✅
- 90 * 0.69 = 62 trading days (conservative estimate)

**Mitigation:** Code VALIDATES warmup sufficiency by checking for NaN
- If insufficient, raises ValueError
- **Built-in safety check** ✅

### Verdict: **CLEAN** (validation catches edge cases)

---

## SECTION 5: GREEKS CALCULATION - CONTRACT MULTIPLIER

### Code Location: `trade_tracker.py` lines 308-325

```python
# Calculate Greeks for each leg and sum
CONTRACT_MULTIPLIER = 100  # FIX BUG-002: Options represent 100 shares per contract
net_greeks = {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}

for leg in legs:
    opt_type = leg['type']
    qty = leg['qty']

    greeks = calculate_all_greeks(
        spot, strike, dte / 365.0, r, iv, opt_type
    )

    # Scale by quantity (positive = long, negative = short) AND contract multiplier
    net_greeks['delta'] += greeks['delta'] * qty * CONTRACT_MULTIPLIER
    net_greeks['gamma'] += greeks['gamma'] * qty * CONTRACT_MULTIPLIER
    net_greeks['theta'] += greeks['theta'] * qty * CONTRACT_MULTIPLIER
    net_greeks['vega'] += greeks['vega'] * qty * CONTRACT_MULTIPLIER
```

### Manual Verification:

**Assumption: calculate_all_greeks() returns per-share Greeks**
- Delta = 0.50 (per share)
- 1 contract = 100 shares
- Net delta = 0.50 * 1 * 100 = 50 (portfolio delta) ✅

**Test Case: Long ATM straddle**
- Legs: [{'type': 'call', 'qty': 1}, {'type': 'put', 'qty': 1}]
- Call delta = +0.50, Put delta = -0.50
- Net delta = (0.50 * 1 * 100) + (-0.50 * 1 * 100) = 50 - 50 = 0 ✅
- **CORRECT: ATM straddle is delta-neutral**

**Test Case: Short straddle**
- Legs: [{'type': 'call', 'qty': -1}, {'type': 'put', 'qty': -1}]
- Call delta = +0.50, Put delta = -0.50
- Net delta = (0.50 * -1 * 100) + (-0.50 * -1 * 100) = -50 + 50 = 0 ✅
- **CORRECT: Short straddle also delta-neutral**

**Test Case: Gamma for long straddle**
- Call gamma = 0.05, Put gamma = 0.05 (gamma always positive)
- Net gamma = (0.05 * 1 * 100) + (0.05 * 1 * 100) = 5 + 5 = 10 ✅
- **CORRECT: Long straddle is long gamma**

### Edge Case: Verify gamma sign convention

**Greek sign conventions:**
- Delta: positive for calls (+spot exposure), negative for puts (-spot exposure)
- Gamma: ALWAYS positive for single options
- Theta: negative for longs (decay hurts), positive for shorts (decay helps)
- Vega: positive for longs (vol helps), negative for shorts (vol hurts)

**Code verification:**
- No sign manipulation beyond qty multiplication ✅
- Assumes calculate_all_greeks() follows standard conventions ✅

### Verdict: **CLEAN** (assuming calculate_all_greeks() is correct)

---

## SECTION 6: P&L CALCULATION - ENTRY/EXIT PRICING

### Code Location: `trade_tracker.py` lines 79-108

```python
for leg in position['legs']:
    opt_type = leg['type']
    qty = leg['qty']

    # FIX BUG-001 (SYSTEMIC): Get execution prices (ask/bid), not mid+spread
    if qty > 0:
        # Long: pay the ask
        price = self.polygon.get_option_price(
            entry_date, position['strike'], position['expiry'], opt_type, 'ask'
        )
    else:
        # Short: receive the bid
        price = self.polygon.get_option_price(
            entry_date, position['strike'], position['expiry'], opt_type, 'bid'
        )

    if price is None:
        return None

    entry_prices[opt_type] = price

    # Entry cost calculation (price already includes spread via ask/bid)
    # For long (qty > 0): positive = cash outflow (we paid ask)
    # For short (qty < 0): negative = cash inflow (we received bid)
    leg_cost = qty * price * 100

    entry_cost += leg_cost

entry_cost += commission  # Commission is always a cost (positive addition)
```

### Manual Verification:

**Test Case: Long ATM call**
- qty = 1, ask = $5.00
- leg_cost = 1 * 5.00 * 100 = $500
- entry_cost = $500 + $2.60 = $502.60
- **Cash outflow: $502.60** ✅

**Test Case: Short ATM put**
- qty = -1, bid = $4.80
- leg_cost = -1 * 4.80 * 100 = -$480
- entry_cost = -$480 + $2.60 = -$477.40
- **Cash inflow: $477.40** ✅

**Test Case: Long straddle (call ask=$5.00, put ask=$4.90)**
- Call: qty=1, price=5.00, leg_cost = $500
- Put: qty=1, price=4.90, leg_cost = $490
- entry_cost = $500 + $490 + $2.60 = $992.60
- **Total cost: $992.60** ✅

### Exit Pricing Verification (lines 160-180):

```python
for leg in position['legs']:
    opt_type = leg['type']
    qty = leg['qty']

    # FIXED: Use consistent ask/bid pricing (same as entry)
    # Long positions would exit at bid (selling), short at ask (buying to cover)
    if qty > 0:
        # Long: exit at bid (we're selling)
        price = self.polygon.get_option_price(
            day_date, position['strike'], position['expiry'], opt_type, 'bid'
        )
    else:
        # Short: exit at ask (we're buying to cover)
        price = self.polygon.get_option_price(
            day_date, position['strike'], position['expiry'], opt_type, 'ask'
        )
```

**Test Case: Exit long call**
- Entered: qty=1, paid ask=$5.00
- Exit: qty=1, receive bid=$5.50
- exit_value = 1 * 5.50 * 100 = $550
- P&L = $550 - $500 - $2.60 (entry) - $2.60 (exit) = $44.80
- **CORRECT** ✅

**Test Case: Exit short put**
- Entered: qty=-1, received bid=$4.80, cost = -$480
- Exit: qty=-1, pay ask=$4.00 (profit scenario)
- exit_value = -1 * 4.00 * 100 = -$400
- P&L = -$400 - (-$480) - $2.60 = $80 - $2.60 = $77.40
- **CORRECT** ✅

### ❌ **CRITICAL BUG #4: Commission Applied Twice?**

```python
# Line 108: entry_cost += commission
# Line 186: mtm_pnl = mtm_value - entry_cost - commission
```

**Wait, is commission double-counted?**

**Analysis:**
- entry_cost INCLUDES entry commission (line 108)
- mtm_pnl subtracts ANOTHER commission for exit (line 186)
- Total commissions: 1 for entry + 1 for exit = 2 ✅
- **CORRECT: Round-trip needs both**

**Verification:**
- Entry: Pay $500 + $2.60 commission = $502.60 outflow
- entry_cost = $502.60
- Exit: Receive $550 - $2.60 commission = $547.40 inflow
- mtm_value = $550 (gross)
- mtm_pnl = $550 - $502.60 - $2.60 = $44.80 (net)
- **CORRECT** ✅

### Verdict: **CLEAN**

---

## SECTION 7: METRICS CALCULATION - SHARPE RATIO

### Code Location: `metrics.py` lines 87-132

```python
def sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    # AUTO-DETECT: If values > 1.0, likely dollar P&L not percentage returns
    if returns.abs().mean() > 1.0:
        # Input is dollar P&L - convert to returns
        cumulative_portfolio_value = self.starting_capital + returns.cumsum()
        returns_pct = cumulative_portfolio_value.pct_change().dropna()
        if len(returns_pct) > 0:
            first_return = returns.iloc[0] / self.starting_capital
            returns_pct = pd.concat([pd.Series([first_return], index=[returns.index[0]]), returns_pct])
    else:
        returns_pct = returns

    excess_returns = returns_pct - (risk_free_rate / self.annual_factor)

    if excess_returns.std() == 0 or len(excess_returns) == 0:
        return 0.0

    return (excess_returns.mean() / excess_returns.std()) * np.sqrt(self.annual_factor)
```

### Manual Verification:

**Test Case: Daily P&L series = [100, -50, 200, -80, 150]**
- starting_capital = $100,000
- Mean: 64
- abs().mean() = 116 > 1.0 → Dollar P&L detected ✅

**Conversion to returns:**
```
cumulative_portfolio_value:
  Day 0: $100,000 (start)
  Day 1: $100,000 + 100 = $100,100
  Day 2: $100,100 - 50 = $100,050
  Day 3: $100,050 + 200 = $100,250
  Day 4: $100,250 - 80 = $100,170
  Day 5: $100,170 + 150 = $100,320

pct_change():
  Day 1: ($100,100 - $100,000) / $100,000 = 0.001 (0.1%)
  Day 2: ($100,050 - $100,100) / $100,100 = -0.0005 (-0.05%)
  Day 3: ($100,250 - $100,050) / $100,050 = 0.002 (0.2%)
  Day 4: ($100,170 - $100,250) / $100,250 = -0.0008 (-0.08%)
  Day 5: ($100,320 - $100,170) / $100,170 = 0.0015 (0.15%)
```

**First return handling:**
```python
first_return = returns.iloc[0] / self.starting_capital
# = 100 / 100000 = 0.001
```

**BUT WAIT: pct_change() already calculated first return correctly!**
- pct_change()[1] = 0.001 (from Day 0 to Day 1)
- Code then PREPENDS another first_return = 0.001

### ❌ **CRITICAL BUG #5: First Return Double-Counted**

```python
returns_pct = cumulative_portfolio_value.pct_change().dropna()
if len(returns_pct) > 0:
    first_return = returns.iloc[0] / self.starting_capital
    returns_pct = pd.concat([pd.Series([first_return], ...), returns_pct])
```

**Issue:**
- pct_change() on cumulative value ALREADY includes first return
- dropna() removes the first NaN
- Then code ADDS first_return again
- **Result: First return is in the series TWICE**

**Proof:**
```python
cumulative = [100000, 100100, 100050, ...]
pct = cumulative.pct_change()
# pct = [NaN, 0.001, -0.0005, ...]

pct_no_nan = pct.dropna()
# pct_no_nan = [0.001, -0.0005, ...]  (length = 4)

first_return = 100 / 100000 = 0.001

concat([0.001], [0.001, -0.0005, ...])
# Result: [0.001, 0.001, -0.0005, ...]  (length = 5, first value duplicated!)
```

**Impact:**
- If first day is large gain: Sharpe inflated
- If first day is large loss: Sharpe deflated
- **Systematic bias in Sharpe calculation**

**Severity: CRITICAL** - Affects all Sharpe calculations when using dollar P&L

### ❌ **CRITICAL BUG #6: Same Issue in Sortino Ratio**

Lines 160-168 have identical bug:
```python
returns_pct = cumulative_portfolio_value.pct_change().dropna()
if len(returns_pct) > 0:
    first_return = returns.iloc[0] / self.starting_capital
    returns_pct = pd.concat([pd.Series([first_return], index=[returns.index[0]]), returns_pct])
```

**Severity: CRITICAL**

### Verdict: **2 CRITICAL BUGS FOUND**

---

## SECTION 8: METRICS - CALMAR RATIO CALCULATION

### Code Location: `metrics.py` lines 222-268

```python
def calmar_ratio(self, returns: pd.Series, cumulative_pnl: pd.Series) -> float:
    # FIX BUG-METRICS-003: CAGR calculation needs portfolio value, not cumulative P&L
    starting_value = self.starting_capital
    ending_value = self.starting_capital + cumulative_pnl.iloc[-1]

    if starting_value <= 0:
        return 0.0

    total_return = (ending_value / starting_value) - 1
    years = len(cumulative_pnl) / self.annual_factor
    cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else total_return

    # Get max drawdown percentage (calculate from portfolio value, not cumulative P&L)
    portfolio_value = self.starting_capital + cumulative_pnl
    max_dd_pct = abs(self.max_drawdown_pct(portfolio_value))

    if max_dd_pct == 0 or np.isnan(max_dd_pct):
        return 0.0

    return cagr / max_dd_pct
```

### Manual Verification:

**Test Case:**
- starting_capital = $100,000
- cumulative_pnl = [0, 1000, 1500, 1200, 2000, 1800]
- Days: 6 trading days

**CAGR Calculation:**
```
ending_value = $100,000 + $1,800 = $101,800
total_return = (101,800 / 100,000) - 1 = 0.018 = 1.8%
years = 6 / 252 = 0.0238 years
cagr = (1.018) ^ (1/0.0238) - 1 = (1.018) ^ 42.02 - 1
     ≈ 2.09 - 1 = 109% annualized
```

**Max Drawdown:**
```
portfolio_value = [100000, 101000, 101500, 101200, 102000, 101800]
running_max =     [100000, 101000, 101500, 101500, 102000, 102000]
dd_pct =          [0%,     0%,     0%,     -0.30%, 0%,     -0.20%]
max_dd_pct = -0.30%
```

**Calmar Ratio:**
```
calmar = 109% / 0.30% = 363
```

**Seems very high, but mathematically correct for short period with small DD** ✅

### Edge Case: Zero Drawdown

```python
if max_dd_pct == 0 or np.isnan(max_dd_pct):
    return 0.0
```

**Issue:** If strategy has no drawdown (unlikely but possible in short test), Calmar = CAGR / 0 = infinity
**Code handles this:** Returns 0.0 instead of infinity
**Alternative:** Could return CAGR or np.inf
**Current behavior:** Conservative (0.0) ✅

### Verdict: **CLEAN**

---

## SECTION 9: DRAWDOWN ANALYSIS - INDEX ERROR

### Code Location: `metrics.py` lines 311-363

```python
def drawdown_analysis(self, cumulative_pnl: pd.Series) -> Dict:
    running_max = cumulative_pnl.expanding().max()
    drawdown = cumulative_pnl - running_max

    # Find maximum drawdown period
    # BUG FIX (2025-11-18): Final audit - use argmin() for position, not idxmin()
    max_dd_position = drawdown.argmin()  # Returns integer position
    max_dd_value = drawdown.min()

    # ... recovery logic ...

    return {
        'max_dd_value': max_dd_value,
        'max_dd_date': cumulative_pnl.index[max_dd_idx] if hasattr(...), 'date') else max_dd_idx,
        # ...
    }
```

### ❌ **CRITICAL BUG #7: Undefined Variable `max_dd_idx`**

**Line 358:**
```python
'max_dd_date': cumulative_pnl.index[max_dd_idx] if hasattr(cumulative_pnl.index[max_dd_idx], 'date') else max_dd_idx,
```

**Problem:**
- Variable defined: `max_dd_position` (line 330)
- Variable used: `max_dd_idx` (line 358)
- **NameError: max_dd_idx is not defined**

**This would cause immediate crash when function is called**

**How was this not caught in testing?**
- Possible: drawdown_analysis() never called in current test suite
- Possible: Code was added but not tested

**Fix:**
```python
'max_dd_date': cumulative_pnl.index[max_dd_position] if hasattr(cumulative_pnl.index[max_dd_position], 'date') else max_dd_position,
```

**Severity: CRITICAL** - Function is broken, will crash on first call

### Verdict: **CRITICAL BUG FOUND**

---

## SECTION 10: EXECUTION MODEL - SLIPPAGE CALCULATION

### Code Location: `execution.py` lines 122-180

```python
def get_execution_price(self, mid_price: float, side: str, moneyness: float,
                        dte: int, vix_level: float = 20.0, is_strangle: bool = False,
                        quantity: int = 1) -> float:
    spread = self.get_spread(mid_price, moneyness, dte, vix_level, is_strangle)
    half_spread = spread / 2.0

    # Size-based slippage as % of half-spread
    abs_qty = abs(quantity)
    if abs_qty <= 10:
        slippage_pct = self.slippage_small  # 0.10 = 10%
    elif abs_qty <= 50:
        slippage_pct = self.slippage_medium  # 0.25 = 25%
    else:
        slippage_pct = self.slippage_large  # 0.50 = 50%

    slippage = half_spread * slippage_pct

    if side == 'buy':
        # Pay ask + slippage
        return mid_price + half_spread + slippage
    elif side == 'sell':
        # Receive bid - slippage
        return max(0.01, mid_price - half_spread - slippage)
```

### Manual Verification:

**Test Case: Buy 1 contract, mid=$5.00, spread=$0.10**
- half_spread = $0.05
- abs_qty = 1 → slippage_pct = 0.10
- slippage = $0.05 * 0.10 = $0.005
- exec_price = $5.00 + $0.05 + $0.005 = $5.055 ✅

**Test Case: Sell 100 contracts, mid=$5.00, spread=$0.10**
- half_spread = $0.05
- abs_qty = 100 → slippage_pct = 0.50 (large order)
- slippage = $0.05 * 0.50 = $0.025
- exec_price = max(0.01, $5.00 - $0.05 - $0.025) = $4.925 ✅

**Edge Case: Sell into zero bid**
- mid = $0.05, spread = $0.10
- half_spread = $0.05
- slippage = $0.025 (50% for large order)
- calc = $0.05 - $0.05 - $0.025 = -$0.025
- exec_price = max(0.01, -$0.025) = $0.01 ✅
- **Floor prevents negative prices** ✅

### Verdict: **CLEAN**

---

## SECTION 11: EXECUTION MODEL - SPREAD CALCULATION

### Code Location: `execution.py` lines 65-120

```python
def get_spread(self, mid_price: float, moneyness: float, dte: int,
               vix_level: float = 20.0, is_strangle: bool = False) -> float:
    base = self.base_spread_otm if is_strangle else self.base_spread_atm

    # BUG FIX (2025-11-18): Final audit - linear scaling more realistic
    moneyness_factor = 1.0 + moneyness * 5.0  # Linear widening

    # Adjust for DTE
    dte_factor = 1.0
    if dte < 7:
        dte_factor = 1.3
    elif dte < 14:
        dte_factor = 1.15

    # Adjust for volatility (continuous scaling)
    vol_factor = 1.0 + max(0, (vix_level - 15.0) / 20.0)
    vol_factor = min(3.0, vol_factor)

    # Final spread
    spread = base * moneyness_factor * dte_factor * vol_factor

    # Ensure spread is at least 5% of mid price
    min_spread = mid_price * 0.05
    return max(spread, min_spread)
```

### Manual Verification:

**Test Case: ATM, 30 DTE, VIX=20**
- base = $0.03 (base_spread_atm)
- moneyness = 0.0 → moneyness_factor = 1.0
- dte = 30 → dte_factor = 1.0
- vix = 20 → vol_factor = 1.0 + (20-15)/20 = 1.25
- spread = $0.03 * 1.0 * 1.0 * 1.25 = $0.0375
- mid = $5.00 → min_spread = $0.25
- **Final spread = max($0.0375, $0.25) = $0.25** ✅

**Test Case: 5% OTM, 7 DTE, VIX=35**
- base = $0.03
- moneyness = 0.05 → moneyness_factor = 1.0 + 0.05*5 = 1.25
- dte = 7 → dte_factor = 1.3 (weekly options)
- vix = 35 → vol_factor = 1.0 + (35-15)/20 = 2.0
- spread = $0.03 * 1.25 * 1.3 * 2.0 = $0.0975
- mid = $2.00 → min_spread = $0.10
- **Final spread = max($0.0975, $0.10) = $0.10** ✅

**Test Case: Very cheap option, mid=$0.10**
- Calculated spread = $0.05
- min_spread = $0.10 * 0.05 = $0.005
- **Final spread = max($0.05, $0.005) = $0.05**
- **Spread is 50% of mid price** ← This seems high

### ❌ **WARNING BUG #8: Min Spread Floor Too Low for Penny Options**

**Scenario: Option trading at $0.20**
- Realistic spread: $0.05 (25% of mid)
- Calculated spread: $0.08
- min_spread = $0.20 * 0.05 = $0.01
- **Final: max($0.08, $0.01) = $0.08** ✅ Actually OK

**BUT: Option trading at $0.05**
- Realistic spread: $0.02-0.05 (40-100% of mid)
- Calculated spread: $0.04
- min_spread = $0.05 * 0.05 = $0.0025
- **Final: max($0.04, $0.0025) = $0.04 (80% of mid)** ← Might be realistic for penny options

**Analysis:** For very cheap options (<$0.10), spreads CAN be 50-100% of mid in reality
**Current behavior:** Allows this
**Severity: LOW** - Might actually be realistic for penny options

### Verdict: **CLEAN** (with low-severity note on penny options)

---

## SECTION 12: EXIT ENGINE - PARAMETER OVERRIDE

### Code Location: `exit_engine.py` lines 36-52

```python
def __init__(self, phase: int = 1, custom_exit_days: Dict[str, int] = None):
    self.phase = phase

    # Create mutable instance copy that can be overridden
    self.exit_days = self.PROFILE_EXIT_DAYS.copy()

    # Override with custom exit days if provided
    if custom_exit_days:
        self.exit_days.update(custom_exit_days)
```

### Manual Verification:

**Test Case: Default initialization**
```python
engine = ExitEngine(phase=1)
# exit_days should be copy of PROFILE_EXIT_DAYS
assert engine.exit_days == {
    'Profile_1_LDG': 7,
    'Profile_2_SDG': 5,
    # ...
}
```
✅

**Test Case: Custom override**
```python
custom = {'Profile_1_LDG': 10, 'Profile_2_SDG': 8}
engine = ExitEngine(phase=1, custom_exit_days=custom)

# Should have:
# Profile_1_LDG: 10 (overridden)
# Profile_2_SDG: 8 (overridden)
# Profile_3_CHARM: 3 (default)
# ...
```

**Verification:**
```python
base = PROFILE_EXIT_DAYS.copy()  # All 6 profiles
base.update({'Profile_1_LDG': 10, 'Profile_2_SDG': 8})
# base now has Profile_1_LDG=10, others unchanged ✅
```

### Edge Case: Partial override with missing profiles

```python
custom = {'Profile_1_LDG': 10}  # Only one profile
engine = ExitEngine(phase=1, custom_exit_days=custom)
# Other profiles should keep defaults ✅
```

### Verdict: **CLEAN**

---

## SECTION 13: TRADE TRACKER - PEAK CAPTURE CALCULATION

### Code Location: `trade_tracker.py` lines 237-245

```python
# FIXED: Handle division by zero and negative peak scenarios
if peak_pnl > 0:
    pct_captured = float(exit_snapshot['mtm_pnl'] / peak_pnl * 100)
elif peak_pnl < 0:
    # Trade never went positive - losing trade throughout
    pct_captured = 0.0
else:
    # peak_pnl == 0 (broke even at best)
    pct_captured = 0.0
```

### Manual Verification:

**Test Case 1: Normal winner**
- Peak P&L = $100
- Exit P&L = $80
- pct_captured = 80 / 100 * 100 = 80% ✅

**Test Case 2: Exit after peak**
- Peak P&L = $100
- Exit P&L = $60
- pct_captured = 60 / 100 * 100 = 60% ✅

**Test Case 3: Losing trade (never profitable)**
- Peak P&L = -$20 (best it got was -$20 loss)
- Exit P&L = -$50
- pct_captured = 0.0% ✅ (Correct: can't capture peak of losing trade)

**Test Case 4: Break-even**
- Peak P&L = $0
- Exit P&L = -$10
- pct_captured = 0.0% ✅ (Avoids division by zero)

**Test Case 5: Exit at exact peak**
- Peak P&L = $100
- Exit P&L = $100
- pct_captured = 100 / 100 * 100 = 100% ✅

### Edge Case: What if exit > peak? (Shouldn't happen, but...)

**Analysis:**
- peak_pnl is updated as max of all mtm_pnl values
- exit_snapshot is LAST value in daily_path
- peak_pnl = max(all daily pnls)
- exit_pnl = daily_path[-1]
- **By definition: exit_pnl <= peak_pnl** ✅

**But wait, let me check the code:**
```python
# Line 189-190
if mtm_pnl > peak_pnl:
    peak_pnl = mtm_pnl
```

**This updates peak DURING iteration, including the last day**
**So exit_snapshot['mtm_pnl'] could equal peak_pnl, but never exceed** ✅

### Verdict: **CLEAN**

---

## SECTION 14: TRADE TRACKER - IV ESTIMATION

### Code Location: `trade_tracker.py` lines 288-306

```python
# Estimate IV from option price (improved heuristic)
# FIXED: Better IV estimation using Brenner-Subrahmanyam approximation
iv = 0.20  # Default fallback
for leg in legs:
    opt_type = leg['type']
    if opt_type in prices:
        price = prices[opt_type]
        moneyness = abs(strike - spot) / spot

        # Brenner-Subrahmanyam approximation for ATM options
        if moneyness < 0.05:  # Near ATM
            iv = price / spot * np.sqrt(2 * np.pi / (dte / 365.0))
            iv = np.clip(iv, 0.05, 2.0)
        else:  # OTM options
            iv = price / spot * np.sqrt(2 * np.pi / (dte / 365.0)) * 1.5
            iv = np.clip(iv, 0.05, 3.0)
        break
```

### Manual Verification:

**Brenner-Subrahmanyam Formula (ATM approximation):**
```
σ ≈ (C_ATM / S) * √(2π / T)
```

**Test Case: ATM option**
- Spot = $450
- Strike = $450 (ATM, moneyness = 0%)
- Price = $18
- DTE = 30 days = 30/365 = 0.0822 years
- Formula: iv = (18 / 450) * √(2 * π / 0.0822)
-         = 0.04 * √(76.4)
-         = 0.04 * 8.74
-         = 0.35 = 35% IV ✅

**Reality check: Is 35% IV reasonable for $18 option on $450 stock with 30 DTE?**
- Quick Black-Scholes estimate: C ≈ S * σ * √T
- C ≈ 450 * 0.35 * √0.0822 = 450 * 0.35 * 0.287 = $45 ← Wait, this is way off

**Let me recalculate B-S formula correctly:**
- For ATM option, approximate: C ≈ 0.4 * S * σ * √T
- Solving for σ: σ = C / (0.4 * S * √T)
- σ = 18 / (0.4 * 450 * √0.0822)
- σ = 18 / (0.4 * 450 * 0.287)
- σ = 18 / 51.7 = 0.348 = 34.8% ✅

**Brenner-Subrahmanyam gives 35%, matches rough B-S** ✅

**Test Case: OTM option**
- Spot = $450, Strike = $470 (4.4% OTM)
- Price = $5, DTE = 30
- moneyness = 4.4% < 5% → Uses ATM formula
- iv = (5 / 450) * √(2π / 0.0822) = 0.0111 * 8.74 = 0.097 = 9.7%
- Clipped to: max(0.05, min(9.7%, 2.0)) = 9.7% ✅

**Edge Case: Very OTM (moneyness > 5%)**
- Spot = $450, Strike = $495 (10% OTM)
- Price = $2, DTE = 30
- moneyness = 10% > 5% → Uses OTM formula (1.5x multiplier)
- iv_atm = (2 / 450) * √(2π / 0.0822) = 0.0044 * 8.74 = 0.039
- iv_otm = 0.039 * 1.5 = 0.058 = 5.8%
- **Multiplier accounts for OTM options having lower vega** ✅

### Verdict: **CLEAN** (reasonable approximation)

---

## COMPREHENSIVE BUG SUMMARY

### CRITICAL BUGS (Must Fix Before Running)

**BUG #5: Sharpe Ratio - First Return Double-Counted**
- **File:** `src/analysis/metrics.py`
- **Line:** 118-122
- **Issue:** First return is already in pct_change() output, then prepended again
- **Impact:** Sharpe ratio systematically biased (inflated if first day wins, deflated if loses)
- **Fix:**
```python
# REMOVE these lines:
if len(returns_pct) > 0:
    first_return = returns.iloc[0] / self.starting_capital
    returns_pct = pd.concat([pd.Series([first_return], index=[returns.index[0]]), returns_pct])

# pct_change().dropna() already has correct returns
```

**BUG #6: Sortino Ratio - Same First Return Issue**
- **File:** `src/analysis/metrics.py`
- **Line:** 165-168
- **Issue:** Identical to Bug #5
- **Impact:** Sortino ratio systematically biased
- **Fix:** Same as Bug #5

**BUG #7: Drawdown Analysis - Undefined Variable**
- **File:** `src/analysis/metrics.py`
- **Line:** 358
- **Issue:** Uses `max_dd_idx` but variable is named `max_dd_position`
- **Impact:** Function crashes with NameError when called
- **Fix:**
```python
# Change line 358:
'max_dd_date': cumulative_pnl.index[max_dd_position] if hasattr(cumulative_pnl.index[max_dd_position], 'date') else max_dd_position,
```

---

### LOW SEVERITY ISSUES (Edge Cases, Unlikely in Practice)

**BUG #1: Edge Case - DTE = 0**
- **File:** `scripts/backtest_train.py`
- **Line:** 233-258
- **Issue:** get_expiry_for_dte() allows same-day expiry
- **Impact:** Edge case, unlikely in practice (min DTE is 7 in profiles)
- **Severity:** LOW

**BUG #8: Min Spread Floor for Penny Options**
- **File:** `src/trading/execution.py`
- **Line:** 119-120
- **Issue:** 5% floor might be too low for very cheap options (<$0.10)
- **Impact:** Might underestimate spreads on penny options
- **Severity:** LOW (penny options rare in SPY)

---

### CLEAN SECTIONS (Zero Bugs Found)

✅ **Strike calculation for OTM options** - Correct math, proper rounding
✅ **Shift operations for look-ahead prevention** - Proper walk-forward compliance
✅ **Warmup period sufficiency** - Adequate + validation check
✅ **Greeks calculation with contract multiplier** - Correct scaling
✅ **P&L entry/exit pricing** - Proper bid/ask, commission handling
✅ **Calmar ratio calculation** - Correct CAGR and DD percentage math
✅ **Execution model slippage** - Realistic size-based tiers
✅ **Exit engine parameter override** - Clean dict.update() logic
✅ **Peak capture calculation** - Handles all edge cases
✅ **IV estimation heuristic** - Brenner-Subrahmanyam accurate for ATM

---

## FINAL VERDICT

**Status:** 3 CRITICAL BUGS FOUND (must fix before running backtests)

**Critical Bugs:**
1. Sharpe ratio: First return double-counted
2. Sortino ratio: First return double-counted
3. Drawdown analysis: Undefined variable crash

**Impact:**
- Current Sharpe/Sortino results are INVALID (systematic bias)
- Drawdown analysis will crash if called
- Backtest results cannot be trusted until fixed

**Recommendation:**
1. Fix 3 critical bugs immediately
2. Re-run all backtests (train/validation/test)
3. Verify metrics match expected values with manual calculations
4. Add unit tests for metrics module to prevent regression

**All other code sections: CLEAN**

---

## MANUAL VERIFICATION CHECKLIST

✅ Expiry calculation - spot-checked 3 scenarios
✅ Strike calculation - verified ATM and OTM
✅ Shift operations - timeline walk-through confirmed
✅ Warmup sufficiency - verified 50-day MA has data
✅ Greeks scaling - contract multiplier verified
✅ P&L calculation - entry/exit pricing verified
✅ Sharpe calculation - **FOUND BUG #5**
✅ Sortino calculation - **FOUND BUG #6**
✅ Calmar calculation - CAGR math verified
✅ Drawdown analysis - **FOUND BUG #7**
✅ Execution slippage - size tiers verified
✅ Spread calculation - moneyness/DTE/vol factors verified
✅ Exit engine - parameter override verified
✅ Peak capture - division by zero handled
✅ IV estimation - B-S approximation verified

**Total Tests:** 14 critical paths verified
**Bugs Found:** 3 critical, 2 low-severity
**Clean Sections:** 11 of 14

---

**Audit Complete: 2025-11-18**
**Next Action: Fix 3 critical bugs, then re-run backtests**
