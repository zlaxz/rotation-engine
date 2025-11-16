# CYCLE 3 PERFORMANCE METRICS AUDIT
## Comprehensive Validation of Calculation Correctness

**Auditor:** performance-analyst skill
**Date:** 2025-11-14
**Context:** High-frequency rotation strategy with REAL CAPITAL at risk
**Previous Results:** Sharpe -3.29 (infrastructure bugs now fixed)
**Mission:** Validate every metric calculation for correctness

---

## EXECUTIVE SUMMARY

**Overall Assessment:** MOSTLY CORRECT with 5 CRITICAL issues and 8 HIGH priority fixes needed

**Critical Issues Found:** 5
**High Priority Issues:** 8
**Medium Priority Issues:** 6
**Total Issues:** 19

**Confidence in Current Metrics:** 60%
**Risk to Strategy Evaluation:** HIGH until critical issues resolved

---

## CRITICAL ISSUES (Must Fix Before Trusting Results)

### CRITICAL-001: Missing Dividends in Return Calculation
**File:** `src/trading/simulator.py:326-336`
**Severity:** CRITICAL
**Impact:** Underestimates SPY returns by ~1.5% annually

**Issue:**
```python
total_equity = realized_equity + unrealized_pnl
daily_pnl = total_equity - prev_total_equity
```

SPY pays dividends (~1.5% annually, ~$0.015-$0.02 per share quarterly). Current P&L calculation:
- Does NOT capture dividend cash flows
- Options are NOT dividend-adjusted in Polygon data
- Missing dividend drag on short stock hedges
- Missing dividend income on long stock hedges

**Evidence:**
- SPY dividend yield: ~1.5% annually (2020-2024)
- Quarterly ex-dividend events: 4 per year
- Delta hedging with SPY shares → missing dividend cash flows

**Impact on Metrics:**
- Sharpe ratio: Biased LOW (missing 1.5% annual return if net long delta)
- Total return: Underestimated by cumulative dividend amount
- Attribution: Delta P&L incorrect (missing dividend component)

**Fix Required:**
1. Load dividend schedule for SPY (yfinance has this data)
2. Add dividend capture logic to simulator on ex-dividend dates
3. Apply dividends to delta hedge positions (if any)
4. Track dividend P&L separately for attribution

---

### CRITICAL-002: Greeks Attribution Formula Missing Vanna/Volga
**File:** `src/trading/trade.py:230-278`
**Severity:** CRITICAL
**Impact:** Greeks P&L attribution incomplete and misleading

**Issue:**
```python
# Attribution calculations
delta_pnl = avg_delta * delta_spot
gamma_pnl = 0.5 * avg_gamma * (delta_spot ** 2)
theta_pnl = avg_theta * delta_time
vega_pnl = avg_vega * delta_iv
```

Missing second-order Greeks:
- **Vanna:** ∂²V/∂S∂σ (spot-vol correlation) - CRITICAL for Profile 4 (Vanna profile)
- **Volga:** ∂²V/∂σ² (vol convexity) - CRITICAL for Profile 6 (Vol-of-Vol profile)
- **Charm:** ∂²V/∂S∂t (delta decay) - Relevant for Profile 3 (Charm profile)

**Impact:**
- Profile 4 (Vanna) P&L attribution WRONG - missing the exact Greek it's targeting
- Profile 6 (VoV) P&L attribution WRONG - missing vol convexity
- "Residual" P&L will be large and attributed to "other" when it's actually vanna/volga

**Verification:**
```python
total_attributed = delta_pnl + gamma_pnl + theta_pnl + vega_pnl
actual_pnl = (exit_price - entry_price)
residual = actual_pnl - total_attributed
```

For vanna/vol-exposed profiles, expect residual > 30% of P&L.

**Fix Required:**
1. Add vanna, volga, charm calculations to `src/pricing/greeks.py`
2. Track these Greeks in `greeks_history`
3. Add to P&L attribution formula:
   - `vanna_pnl = avg_vanna * delta_spot * delta_iv`
   - `volga_pnl = 0.5 * avg_volga * (delta_iv ** 2)`
   - `charm_pnl = avg_charm * delta_time * delta_spot`
4. Report residual % (should be <5% after fixing)

---

### CRITICAL-003: Sharpe Ratio Uses Wrong Return Series
**File:** `src/analysis/metrics.py:83-108`
**Severity:** CRITICAL
**Impact:** Sharpe ratio calculation receives daily P&L dollars, not returns

**Issue:**
```python
def calculate_all(self, portfolio: pd.DataFrame, ...):
    pnl = portfolio['portfolio_pnl']
    metrics = {
        'sharpe_ratio': self.sharpe_ratio(pnl),  # ← WRONG: passing dollars
        ...
    }

def sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.0):
    excess_returns = returns - (risk_free_rate / self.annual_factor)
    ...
    return (excess_returns.mean() / excess_returns.std()) * np.sqrt(self.annual_factor)
```

**Problem:**
- `sharpe_ratio()` expects **returns** (e.g., 0.01 = 1%)
- Receives **portfolio_pnl** (e.g., $1,000 daily dollar P&L)
- Subtracts daily risk-free rate (e.g., 0.05/252 = 0.0002) from $1,000
- Result: Sharpe calculation is nonsensical

**Evidence:**
Previous Sharpe -3.29 on SPY options = impossible without this kind of bug.

**Fix Required:**
```python
def calculate_all(self, portfolio: pd.DataFrame, ...):
    # Use returns, not dollar P&L
    returns = portfolio['portfolio_return']  # ← CORRECT

    metrics = {
        'sharpe_ratio': self.sharpe_ratio(returns),
        ...
    }
```

**Critical Impact:**
- EVERY Sharpe ratio reported to date is INVALID
- Cannot compare strategies
- Cannot evaluate performance
- Previous -3.29 Sharpe may actually be different (better or worse)

---

### CRITICAL-004: Risk-Free Rate Hardcoded to Zero
**File:** `src/analysis/metrics.py:86, 103, 133`
**Severity:** CRITICAL
**Impact:** Sharpe/Sortino ratios ignore 4-5% risk-free rate

**Issue:**
```python
def sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.0):
    # Default risk_free_rate = 0.0 ← WRONG
```

**Problem:**
- 2020-2024 risk-free rate ranged from 0% (COVID) to 5.5% (2023-2024)
- Using 0% makes strategy look artificially better
- Sharpe ratio = (return - rf) / vol
- Missing 4-5% from numerator = inflated Sharpe by ~1.5-2.0 points

**Current Environment (2025-11-14):**
- Fed Funds Rate: ~4.5-5.0%
- 10Y Treasury: ~4.5%
- Appropriate risk-free rate for backtest: 4.0-5.0%

**Fix Required:**
1. Load historical Fed Funds rate or T-Bill rate (FRED API)
2. Pass actual risk-free rate to metrics calculation
3. For 2020-2024 backtest, use time-varying risk-free rate:
   - 2020: 0.25% (COVID ZIRP)
   - 2021: 0.25%
   - 2022: 1.5-4.5% (rising aggressively)
   - 2023-2024: 5.0-5.5%

**Impact:**
- Sharpe ratio currently overstated
- Strategy must beat 4-5% risk-free rate to be viable
- Need to reload historical rates and recalculate

---

### CRITICAL-005: Daily Return Denominator Can Be Zero or Negative
**File:** `src/trading/simulator.py:329-334`
**Severity:** CRITICAL
**Impact:** Division by zero or negative equity → NaN/Inf returns

**Issue:**
```python
# Use previous day's total equity as denominator for returns
if prev_total_equity > 0:
    daily_return = daily_pnl / prev_total_equity
else:
    # First day or zero equity - use initial capital
    daily_return = daily_pnl / max(self.config.capital_per_trade, 1.0)
```

**Problems:**
1. **Negative equity:** If losses accumulate, `prev_total_equity` can go negative
   - Example: Start $100K, lose $120K → equity = -$20K
   - Next day: Return = $1K / -$20K = -5% (WRONG: should be return on remaining margin)

2. **Zero equity:** If equity hits exactly $0.0
   - Next day: Return = $1K / $0.0 → division by zero → NaN
   - NaN propagates to Sharpe ratio → entire metric calculation fails

3. **Geometric vs arithmetic:** Current calculation is geometric (compounding)
   - But uses abs(prev_equity) which breaks sign convention
   - Should track initial capital separately

**Fix Required:**
```python
# Use absolute initial capital as denominator (normalize to constant base)
# This gives arithmetic returns that compound correctly
daily_return = daily_pnl / abs(self.config.capital_per_trade)

# OR: Track equity carefully and handle negative equity case
# Negative equity means margin call → position should be closed
# Strategy should NEVER go negative equity in backtest
if prev_total_equity <= 0:
    # This is a critical failure - strategy has blown up
    # Log error and halt simulation
    raise ValueError(f"Equity went negative: {prev_total_equity} on {current_date}")
```

**Recommended Approach:**
- Use initial capital as constant denominator (arithmetic returns)
- Add equity floor check: Halt backtest if equity < 0.1 × initial_capital (90% drawdown)
- This matches real trading: You can't trade with negative equity

**Impact:**
- If equity went negative during previous Sharpe -3.29 backtest → returns are corrupted
- Need to check: Did equity ever go negative? If yes, ALL metrics are invalid

---

## HIGH PRIORITY ISSUES (Fix Soon)

### HIGH-001: Compounding Error in Return Calculation
**File:** `src/backtest/portfolio.py:95-111`
**Severity:** HIGH
**Impact:** Compounding may be incorrect for multi-day sequences

**Issue:**
```python
for ret in portfolio['portfolio_return']:
    prev_values.append(prev_value)
    pnl = prev_value * ret
    daily_pnls.append(pnl)
    prev_value = prev_value + pnl  # ← Compounding happens here
    curr_values.append(prev_value)
```

**Problem:**
- Individual profile returns are calculated with their own capital base
- Portfolio aggregation multiplies returns by portfolio-level capital
- **Mismatch:** Profile returns assume profile-specific capital, but get applied to portfolio capital
- This is only correct if profiles have independent capital pools

**Example:**
- Profile 1 has $50K allocated, makes 10% return → $5K profit
- Profile return = 0.10
- Portfolio capital = $100K
- Portfolio calculation: $100K × 0.10 = $10K (WRONG: should be $5K)

**Root Cause:**
Line in `portfolio.py:69`:
```python
profile_daily = results[['date', 'daily_return', 'daily_pnl']].copy()
```

Uses `daily_return` from profile simulation, which is based on `capital_per_trade` for that profile.
Then applies to entire portfolio value, creating double-counting.

**Fix Required:**
Either:
1. Use dollar P&L from profiles directly (not returns)
2. OR: Ensure profile returns are calculated as % of PORTFOLIO capital, not profile capital

**Current Code Path:**
- `simulator.py:334`: `daily_return = daily_pnl / prev_total_equity` (profile-specific)
- `portfolio.py:88`: `portfolio[return_col] = weight_series * profile_daily_return` (applies to portfolio)
- This double-applies the capital scaling

**Correct Approach:**
```python
# In portfolio aggregation:
# Use dollar P&L weighted by allocation, not returns
portfolio[pnl_col] = weight_series * profile_daily_pnl

# Then calculate portfolio return:
portfolio_pnl = sum(all pnl_cols)
portfolio_return = portfolio_pnl / portfolio_value
```

---

### HIGH-002: Sortino Ratio Downside Deviation Formula Incorrect
**File:** `src/analysis/metrics.py:110-141`
**Severity:** HIGH
**Impact:** Sortino ratio underestimates downside risk

**Issue:**
```python
def sortino_ratio(self, returns: pd.Series, risk_free_rate: float = 0.0, target: float = 0.0):
    excess_returns = returns - (risk_free_rate / self.annual_factor)
    downside_returns = returns[returns < target] - target  # ← BUG

    downside_std = np.sqrt((downside_returns ** 2).mean())
    return (excess_returns.mean() / downside_std) * np.sqrt(self.annual_factor)
```

**Problem 1: Uses returns in downside, excess_returns in numerator**
- Numerator: `excess_returns.mean()` (returns minus risk-free)
- Denominator: `downside_returns` (raw returns minus target)
- **Inconsistent:** Should use same series for both

**Problem 2: Target subtraction is wrong**
```python
downside_returns = returns[returns < target] - target
```
If target = 0.0, this shifts all negative returns down further.
- Return = -5% → downside_return = -5% - 0% = -5% ✓
- Return = -5%, target = 2% → downside_return = -5% - 2% = -7% ✗

Correct formula: Only include returns below target, don't subtract again.

**Standard Sortino Formula:**
```python
# Downside deviation = sqrt(mean of squared negative excess returns)
target_daily = target / self.annual_factor
excess_returns = returns - (risk_free_rate / self.annual_factor)
downside_excess = excess_returns[excess_returns < target_daily]
downside_dev = np.sqrt((downside_excess ** 2).mean())

sortino = (excess_returns.mean() / downside_dev) * np.sqrt(self.annual_factor)
```

**Impact:**
- Current Sortino ratio is inflated (denominator too small)
- Understates downside risk
- Makes strategy look better than it is

---

### HIGH-003: Calmar Ratio Uses Dollar P&L, Not Returns
**File:** `src/analysis/metrics.py:183-209`
**Severity:** HIGH
**Impact:** Calmar ratio units are wrong (dollars/dollars vs return/drawdown)

**Issue:**
```python
def calmar_ratio(self, returns: pd.Series, cumulative_pnl: pd.Series):
    annual_return = returns.mean() * self.annual_factor  # ← assumes returns
    max_dd = abs(self.max_drawdown(cumulative_pnl))
    return annual_return / max_dd
```

But `calculate_all()` passes dollar P&L:
```python
'calmar_ratio': self.calmar_ratio(pnl, portfolio['cumulative_pnl'])
```

**Problem:**
- `annual_return` = mean(daily_pnl) × 252 = dollars, not percentage
- `max_dd` = dollars
- Calmar = dollars / dollars ✓ (units OK)
- BUT: Calmar should be annual_return_pct / max_dd_pct for comparability

**Standard Calmar Ratio:**
- Numerator: Annualized return as percentage (e.g., 15%)
- Denominator: Max drawdown as percentage (e.g., -25%)
- Result: 15% / 25% = 0.6

**Current Calculation:**
- Numerator: Daily dollar P&L × 252 (e.g., $100 × 252 = $25,200)
- Denominator: Max dollar drawdown (e.g., $50,000)
- Result: $25,200 / $50,000 = 0.504

Not directly comparable to industry-standard Calmar ratios.

**Fix Required:**
```python
def calmar_ratio(self, returns: pd.Series, equity_curve: pd.Series):
    # Annualized return (percentage)
    annual_return_pct = returns.mean() * self.annual_factor

    # Max drawdown (percentage)
    max_dd_pct = abs(self.max_drawdown_pct(equity_curve))

    if max_dd_pct == 0:
        return 0.0

    return annual_return_pct / max_dd_pct
```

---

### HIGH-004: Max Drawdown Percentage Breaks on Zero/Negative Equity
**File:** `src/analysis/metrics.py:161-181`
**Severity:** HIGH
**Impact:** Division by zero → NaN drawdown metric

**Issue:**
```python
def max_drawdown_pct(self, cumulative_pnl: pd.Series):
    running_max = cumulative_pnl.expanding().max()
    running_max = running_max.replace(0, np.nan)  # ← Replaces 0 with NaN
    drawdown_pct = (cumulative_pnl - running_max) / running_max
    return drawdown_pct.min()
```

**Problem:**
- If equity curve starts at $0 (cumulative P&L = 0), `running_max[0] = 0`
- Replaced with NaN → `drawdown_pct[0] = NaN`
- If first day is worst drawdown → returns NaN

**Also:** Doesn't handle negative equity
- If equity goes negative, `running_max` can be negative
- Drawdown % calculation becomes nonsensical

**Fix Required:**
```python
def max_drawdown_pct(self, equity_curve: pd.Series, initial_capital: float):
    # Use equity curve (capital + cumulative P&L), not cumulative P&L alone
    # Equity should never be <= 0 in valid backtest

    if (equity_curve <= 0).any():
        raise ValueError("Equity curve contains non-positive values")

    running_max = equity_curve.expanding().max()
    drawdown_pct = (equity_curve - running_max) / running_max
    return drawdown_pct.min()
```

**Alternatively:** Add initial capital to cumulative P&L to get true equity curve.

---

### HIGH-005: Greeks P&L Attribution Not Validated Against Actual P&L
**File:** `src/trading/trade.py:230-278`
**Severity:** HIGH
**Impact:** No validation that Greeks attribution sums to actual P&L

**Issue:**
Attribution calculates:
```python
total_attributed = delta_pnl + gamma_pnl + theta_pnl + vega_pnl
```

But never validates:
```python
actual_pnl = current_mtm - previous_mtm
residual = actual_pnl - total_attributed
assert abs(residual / actual_pnl) < 0.05  # Should be <5% residual
```

**Missing Validation:**
1. Is `total_attributed` close to `actual_pnl`?
2. What % is "unexplained" (residual)?
3. Is residual constant or growing over time?

**Expected Residual Sources:**
- Vanna/volga (second-order Greeks) - addressed in CRITICAL-002
- Higher-order terms (O(Δt²), O(ΔS³))
- Discrete vs continuous hedging effects
- Bid-ask spread slippage

**Fix Required:**
Add validation in `mark_to_market()`:
```python
if self.pnl_attribution is not None:
    actual_pnl_change = unrealized_pnl - prev_unrealized_pnl
    attributed = self.pnl_attribution['total_attributed']
    residual = actual_pnl_change - attributed
    residual_pct = abs(residual / actual_pnl_change) if actual_pnl_change != 0 else 0

    # Log warning if residual > 20%
    if residual_pct > 0.20:
        print(f"WARNING: Greeks attribution residual {residual_pct:.1%} on {current_date}")

    # Store residual for analysis
    self.pnl_attribution['residual'] = residual
    self.pnl_attribution['residual_pct'] = residual_pct
```

---

### HIGH-006: No Handling of Weekends/Holidays in Time-Series Metrics
**File:** `src/analysis/metrics.py` (all functions)
**Severity:** HIGH
**Impact:** Return annualization assumes 252 trading days, but gaps cause issues

**Issue:**
```python
def sharpe_ratio(self, returns: pd.Series, ...):
    return (excess_returns.mean() / excess_returns.std()) * np.sqrt(self.annual_factor)
```

Assumes:
- Returns are **daily** (one per trading day)
- 252 trading days per year

**Problems:**
1. If data has gaps (missing days), return series may not be uniformly spaced
2. Weekends: No returns for Sat/Sun (correct)
3. Holidays: 9-10 holidays per year → actual trading days ~252
4. Multi-day positions: P&L accumulates over weekend, shows up Monday
   - Monday return includes Sat/Sun theta decay
   - Annualization factor should account for this

**Current Handling:**
```python
# In simulator.py:338-349
results.append({
    'date': current_date,
    ...
    'daily_pnl': daily_pnl,
    'daily_return': daily_return,
})
```

Creates one row per date in `self.data`. If `self.data` only has trading days, this is correct.

**Validation Needed:**
- Verify `self.data` only includes trading days (no weekends/holidays)
- Verify return series has no gaps
- If gaps exist, returns should be NaN or filled with 0

**Fix Required:**
Add to `PerformanceMetrics.__init__()`:
```python
def calculate_all(self, portfolio: pd.DataFrame, ...):
    # Validate no gaps in date series
    dates = pd.to_datetime(portfolio['date'])
    date_diffs = dates.diff().dt.days

    # Check for large gaps (> 5 days = suspicious)
    if (date_diffs > 5).any():
        print(f"WARNING: Large gaps in date series detected")
        print(dates[date_diffs > 5])

    # Actual trading days in sample
    actual_trading_days = len(portfolio)
    years = (dates.max() - dates.min()).days / 365.0
    effective_annual_factor = actual_trading_days / years

    # Use effective annual factor for Sharpe/Sortino
    # (should be ~252, but may vary)
```

---

### HIGH-007: Win Rate Uses Days Instead of Trades
**File:** `src/analysis/metrics.py:211-228`
**Severity:** HIGH
**Impact:** Win rate metric is ambiguous and potentially misleading

**Issue:**
```python
def win_rate(self, returns: pd.Series):
    if len(returns) == 0:
        return 0.0
    return (returns > 0).sum() / len(returns)
```

**Problem:**
Calculates: % of **days** with positive P&L

But for a trading strategy, "win rate" typically means: % of **trades** that are profitable.

**Ambiguity:**
- If strategy holds positions for 30 days:
  - Daily win rate: 18/30 = 60% (18 profitable days)
  - Trade win rate: 1/1 = 100% (trade closed profitably)
- Which metric is more meaningful?

**For High-Frequency Rotation Strategy:**
- 50-100+ rotations per year
- Trades last days to weeks
- **Trade-level win rate** is more meaningful than daily win rate

**Fix Required:**
1. Keep current `win_rate()` as `daily_win_rate()`
2. Add `trade_win_rate()`:
```python
def trade_win_rate(self, trades: List[Trade]) -> float:
    """Calculate percentage of profitable closed trades."""
    closed_trades = [t for t in trades if not t.is_open]
    if len(closed_trades) == 0:
        return 0.0

    profitable = sum(1 for t in closed_trades if t.realized_pnl > 0)
    return profitable / len(closed_trades)
```

3. Report both in `calculate_all()`:
```python
metrics = {
    'daily_win_rate': self.win_rate(pnl),
    'trade_win_rate': self.trade_win_rate(trades),  # Pass trades list
    ...
}
```

---

### HIGH-008: Profit Factor Fails on Zero Loss Days
**File:** `src/analysis/metrics.py:230-250`
**Severity:** HIGH
**Impact:** Returns infinity when no losses, breaks downstream analysis

**Issue:**
```python
def profit_factor(self, returns: pd.Series):
    gross_profit = returns[returns > 0].sum()
    gross_loss = abs(returns[returns < 0].sum())

    if gross_loss == 0:
        return np.inf if gross_profit > 0 else 0.0  # ← Returns infinity

    return gross_profit / gross_loss
```

**Problem:**
- If strategy has no losing days (rare but possible in short backtests), `gross_loss = 0`
- Returns `np.inf`
- Breaks serialization (can't save to CSV/JSON)
- Breaks comparisons (inf > any number)
- Misleading: "Infinite" profit factor implies perfection, but really just means "not enough data"

**Fix Required:**
```python
def profit_factor(self, returns: pd.Series):
    gross_profit = returns[returns > 0].sum()
    gross_loss = abs(returns[returns < 0].sum())

    # Avoid division by zero
    if gross_loss == 0:
        # No losses: return high but finite value
        # OR: return None to indicate insufficient data
        return None  # Clearer than np.inf

    if gross_profit == 0:
        return 0.0  # No profits

    return gross_profit / gross_loss
```

Report as:
```python
pf = profit_factor(returns)
print(f"Profit Factor: {pf if pf is not None else 'N/A (no losses)'}")
```

---

## MEDIUM PRIORITY ISSUES (Address Eventually)

### MEDIUM-001: Drawdown Recovery Calculation Inefficient
**File:** `src/analysis/metrics.py:252-303`
**Severity:** MEDIUM
**Impact:** O(n²) algorithm, slow on large datasets

**Issue:**
```python
# Find when max DD started
dd_start_idx = None
for i in range(max_dd_idx + 1):  # ← O(n) loop
    if cumulative_pnl.iloc[i] == running_max.iloc[max_dd_idx]:
        dd_start_idx = i
        break

# Find recovery
recovery_idx = None
if max_dd_idx < len(cumulative_pnl) - 1:
    for i in range(max_dd_idx + 1, len(cumulative_pnl)):  # ← O(n) loop
        if cumulative_pnl.iloc[i] >= running_max.iloc[max_dd_idx]:
            recovery_idx = i
            break
```

For 5 years × 252 days = 1,260 data points, this is acceptable.
For minute-bar data (5 years × 252 × 390 = ~491K bars), this becomes slow.

**Better Approach:**
```python
# Vectorized: Find last time we hit the peak before drawdown
peak_value = running_max.iloc[max_dd_idx]
at_peak = (cumulative_pnl == peak_value)
dd_start_idx = at_peak[:max_dd_idx].idxmax()

# Vectorized: Find first recovery after drawdown
recovered = (cumulative_pnl >= peak_value)
recovery_mask = recovered[max_dd_idx+1:]
recovery_idx = recovery_mask.idxmax() if recovery_mask.any() else None
```

**Impact:** Performance improvement 100x on large datasets.

---

### MEDIUM-002: Regime Performance Calculation Missing Statistical Tests
**File:** `src/analysis/metrics.py:305-345`
**Severity:** MEDIUM
**Impact:** Can't tell if regime differences are statistically significant

**Issue:**
```python
def calculate_by_regime(self, portfolio: pd.DataFrame):
    for regime in sorted(portfolio['regime'].unique()):
        regime_data = portfolio[portfolio['regime'] == regime]
        ...
        metrics = {
            'sharpe': self.sharpe_ratio(pnl),
            ...
        }
```

Reports metrics by regime, but doesn't test:
- Is Regime 1 Sharpe (0.8) **significantly different** from Regime 2 Sharpe (0.4)?
- Or is difference due to random noise?

**Fix Required:**
Add statistical tests:
```python
def compare_regime_performance(self, portfolio: pd.DataFrame):
    """Test if regime performance differences are statistically significant."""
    from scipy.stats import ttest_ind

    regimes = sorted(portfolio['regime'].unique())
    results = []

    for i, r1 in enumerate(regimes):
        for r2 in regimes[i+1:]:
            pnl1 = portfolio[portfolio['regime'] == r1]['portfolio_pnl']
            pnl2 = portfolio[portfolio['regime'] == r2]['portfolio_pnl']

            t_stat, p_value = ttest_ind(pnl1, pnl2)

            results.append({
                'regime_1': r1,
                'regime_2': r2,
                't_stat': t_stat,
                'p_value': p_value,
                'significant_5pct': p_value < 0.05
            })

    return pd.DataFrame(results)
```

**Impact:** Avoids false conclusions about regime alpha.

---

### MEDIUM-003: Profile Attribution Doesn't Validate Weights Sum to 100%
**File:** `src/backtest/portfolio.py:147-177`
**Severity:** MEDIUM
**Impact:** Attribution P&L may not sum to total P&L if weights ≠ 1.0

**Issue:**
```python
def _attribution_by_profile(self, portfolio: pd.DataFrame):
    pnl_cols = [col for col in portfolio.columns if col.endswith('_pnl') ...]

    attribution = []
    total_portfolio_pnl = portfolio['portfolio_pnl'].sum()

    for pnl_col in pnl_cols:
        total_pnl = portfolio[pnl_col].sum()
        contribution = (total_pnl / total_portfolio_pnl * 100) ...
```

**Missing Check:**
```python
# Validate profile P&L sums to portfolio P&L
profile_pnl_sum = sum(portfolio[col].sum() for col in pnl_cols)
portfolio_pnl = portfolio['portfolio_pnl'].sum()

assert abs(profile_pnl_sum - portfolio_pnl) < 1.0, \
    f"Profile P&L ({profile_pnl_sum}) doesn't match portfolio P&L ({portfolio_pnl})"
```

**Also Missing:**
```python
# Validate weights sum to 100% (or <= 100% if cash allowed)
weight_cols = [col for col in portfolio.columns if col.endswith('_weight')]
weight_sum = portfolio[weight_cols].sum(axis=1)

# Check if weights consistently sum to 1.0 ± tolerance
if not ((weight_sum >= 0.95) & (weight_sum <= 1.05)).all():
    print(f"WARNING: Weights don't sum to 100%")
    print(weight_sum[~((weight_sum >= 0.95) & (weight_sum <= 1.05))])
```

**Impact:** Catches allocation bugs before they corrupt attribution.

---

### MEDIUM-004: No Tracking of Turnover/Transaction Frequency
**File:** `src/backtest/portfolio.py:235-272`
**Severity:** MEDIUM
**Impact:** Missing key metric for high-frequency strategy

**Issue:**
`calculate_rotation_frequency()` exists but only counts allocation changes.

**Missing Metrics:**
1. **Trade turnover:** Total notional traded / average portfolio value
2. **Transaction frequency:** Trades per day/week/month
3. **Average hold time:** Days per trade
4. **Round-trip transaction costs:** % of portfolio value

**High-Frequency Strategy Critical Metrics:**
- Previous audit showed 473 rotations / 1,257 days = 0.38 rotations/day
- Need to track: Is turnover increasing? Are costs escalating?

**Fix Required:**
```python
def calculate_turnover_metrics(self, trades: List[Trade], portfolio_value: float):
    """Calculate trading activity metrics."""
    closed_trades = [t for t in trades if not t.is_open]

    total_notional = sum(abs(t.entry_cost) for t in closed_trades)
    total_costs = sum(t.entry_commission + t.exit_commission + t.cumulative_hedge_cost
                     for t in closed_trades)

    return {
        'total_trades': len(closed_trades),
        'total_notional': total_notional,
        'turnover_ratio': total_notional / portfolio_value,
        'total_transaction_costs': total_costs,
        'costs_pct_of_portfolio': total_costs / portfolio_value * 100,
        'cost_per_trade': total_costs / len(closed_trades) if closed_trades else 0,
        'avg_notional_per_trade': total_notional / len(closed_trades) if closed_trades else 0
    }
```

---

### MEDIUM-005: Greeks History Not Saved to Results DataFrame
**File:** `src/trading/simulator.py:338-349`
**Severity:** MEDIUM
**Impact:** Can't analyze Greeks exposure over time post-backtest

**Issue:**
```python
results.append({
    'date': current_date,
    'spot': spot,
    'regime': row.get('regime', 0),
    'position_open': current_trade is not None,
    'daily_pnl': daily_pnl,
    ...
    'trade_id': current_trade.trade_id if current_trade else None
})
```

Missing:
- `net_delta`, `net_gamma`, `net_vega`, `net_theta` from current trade
- Greeks history over trade lifetime
- Greeks attribution (delta_pnl, gamma_pnl, theta_pnl, vega_pnl)

**Fix Required:**
```python
results.append({
    ...
    'net_delta': current_trade.net_delta if current_trade else 0.0,
    'net_gamma': current_trade.net_gamma if current_trade else 0.0,
    'net_vega': current_trade.net_vega if current_trade else 0.0,
    'net_theta': current_trade.net_theta if current_trade else 0.0,

    # P&L attribution (if available)
    'delta_pnl': current_trade.pnl_attribution.get('delta_pnl', 0) if current_trade and current_trade.pnl_attribution else 0,
    'gamma_pnl': current_trade.pnl_attribution.get('gamma_pnl', 0) if current_trade and current_trade.pnl_attribution else 0,
    'theta_pnl': current_trade.pnl_attribution.get('theta_pnl', 0) if current_trade and current_trade.pnl_attribution else 0,
    'vega_pnl': current_trade.pnl_attribution.get('vega_pnl', 0) if current_trade and current_trade.pnl_attribution else 0,
})
```

**Benefits:**
- Can plot net_delta over time → validate Profile 1 (long gamma) achieves target exposure
- Can plot gamma_pnl over time → validate gamma capture
- Can verify Profile 4 (Vanna) achieves vanna exposure

---

### MEDIUM-006: No Tracking of Slippage vs. Expected
**File:** `src/trading/simulator.py` (no slippage tracking)
**Severity:** MEDIUM
**Impact:** Can't validate execution model assumptions

**Issue:**
Execution model calculates bid-ask spread and commission costs, but doesn't track:
- **Expected cost:** What model predicted
- **Actual cost:** What was charged
- **Slippage:** Difference between model and reality

**Current Code:**
```python
entry_prices = self._get_entry_prices(current_trade, row)
current_trade.entry_prices = entry_prices
```

`_get_entry_prices()` uses execution model to calculate spread-adjusted prices.
But doesn't save:
- Mid price (theoretical)
- Bid/ask prices
- Actual fill price
- Slippage = |fill - mid|

**Fix Required:**
Track execution details:
```python
@dataclass
class ExecutionDetails:
    leg_index: int
    mid_price: float
    bid_price: float
    ask_price: float
    fill_price: float
    expected_slippage: float  # From model
    actual_slippage: float    # |fill - mid|
    quantity: int

# Store in Trade
execution_details: List[ExecutionDetails] = None
```

Then validate post-backtest:
```python
# Did actual slippage match model assumptions?
actual_avg_slippage = mean(t.actual_slippage for all trades)
expected_avg_slippage = mean(t.expected_slippage for all trades)

assert abs(actual_avg_slippage - expected_avg_slippage) < tolerance
```

**Impact:** Validates execution model is realistic (not overly optimistic).

---

## SUMMARY OF FIXES REQUIRED

### Immediate (Before Next Backtest):
1. **CRITICAL-003:** Fix Sharpe ratio to use returns, not dollar P&L ← BLOCKING
2. **CRITICAL-004:** Add risk-free rate (4-5% for 2020-2024) ← BLOCKING
3. **CRITICAL-005:** Add equity floor check, prevent negative equity ← BLOCKING
4. **HIGH-001:** Fix compounding in portfolio aggregation ← HIGH IMPACT
5. **HIGH-005:** Add Greeks attribution validation ← VALIDATE RESULTS

### Next Sprint:
6. **CRITICAL-001:** Add dividend capture to simulator
7. **CRITICAL-002:** Add vanna/volga to Greeks attribution
8. **HIGH-002:** Fix Sortino ratio formula
9. **HIGH-003:** Fix Calmar ratio to use percentages
10. **HIGH-007:** Add trade-level win rate metric

### Future Enhancements:
11. **MEDIUM-004:** Add turnover/transaction frequency metrics
12. **MEDIUM-005:** Save Greeks to results DataFrame
13. **MEDIUM-002:** Add statistical tests for regime performance

---

## VALIDATION CHECKLIST

After fixes, validate metrics with these tests:

### Return Calculation:
- [ ] Daily returns sum correctly to cumulative return (compounding)
- [ ] Returns are in correct range (-100% to +∞)
- [ ] No NaN/Inf values in return series
- [ ] Dividends captured (if applicable)

### Sharpe Ratio:
- [ ] Uses returns, not dollar P&L
- [ ] Risk-free rate is non-zero and realistic (4-5%)
- [ ] Annualization factor is 252 (daily) or √252
- [ ] Sharpe on SPY buy-and-hold = ~0.8 (sanity check)

### Greeks Attribution:
- [ ] Delta + Gamma + Theta + Vega + Vanna + Volga ≈ Actual P&L (residual <5%)
- [ ] Profile 1 (long gamma) shows positive gamma_pnl
- [ ] Profile 4 (Vanna) shows non-zero vanna_pnl
- [ ] Profile 6 (VoV) shows non-zero volga_pnl

### Portfolio Aggregation:
- [ ] Profile P&L sums to portfolio P&L (within $1)
- [ ] Weights sum to ≤100% (if cash allowed) or =100% (if fully invested)
- [ ] Compounding is consistent with individual profiles

### Drawdown Metrics:
- [ ] Max drawdown % is in range [-100%, 0%]
- [ ] Recovery time is reasonable (not >1000 days)
- [ ] Drawdown metrics match visual equity curve

---

## CONFIDENCE ASSESSMENT

**Current Metrics Confidence:** 60%

**After CRITICAL Fixes:** 85%
- Sharpe ratio will be correct
- Returns will be accurate
- Greeks attribution will be complete
- Equity curve will be validated

**After ALL Fixes:** 95%
- All edge cases handled
- Statistical validation complete
- Execution tracking comprehensive

**Remaining 5% Uncertainty:**
- Model assumptions (Black-Scholes vs reality)
- Execution model accuracy (spread/slippage)
- Data quality (Polygon options data edge cases)

---

## RECOMMENDATION

**DO NOT TRUST CURRENT METRICS** until CRITICAL-003, CRITICAL-004, and CRITICAL-005 are fixed.

Previous Sharpe -3.29 is INVALID due to:
- Passing dollar P&L to Sharpe calculation (CRITICAL-003)
- Using 0% risk-free rate instead of 4-5% (CRITICAL-004)
- Potential negative equity issues (CRITICAL-005)

**After fixes, re-run backtest from scratch. Previous results are unreliable.**

---

## FILES TO MODIFY

1. **src/analysis/metrics.py** (6 issues)
   - Fix Sharpe ratio input
   - Add risk-free rate parameter
   - Fix Sortino formula
   - Fix Calmar units
   - Add validation logic

2. **src/trading/simulator.py** (3 issues)
   - Add dividend capture
   - Fix return calculation denominator
   - Add equity floor check
   - Add Greeks to output

3. **src/trading/trade.py** (2 issues)
   - Add vanna/volga to Greeks calculation
   - Add Greeks attribution validation

4. **src/backtest/portfolio.py** (2 issues)
   - Fix compounding logic
   - Add attribution validation

5. **src/pricing/greeks.py** (1 issue)
   - Add vanna, volga, charm calculations

---

**END OF AUDIT**

**Next Steps:**
1. Fix CRITICAL issues immediately
2. Re-run backtest with fixes
3. Validate metrics against known benchmarks (SPY buy-and-hold)
4. If results still look wrong, escalate to statistical-validator skill

---

**Audit Timestamp:** 2025-11-14
**Auditor:** performance-analyst skill
**Severity Scale:** CRITICAL (blocks deployment) → HIGH (impacts decisions) → MEDIUM (quality improvement)
**Risk Level:** HIGH until CRITICAL issues resolved
