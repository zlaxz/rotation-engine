# ROUND 8 SPECIFIC FINDINGS - DETAILED CODE LOCATIONS

---

## CRITICAL ISSUE #1: Data Contamination

### Root Cause

All backtests run on 2020-2024 full period. Parameters derived from and validated on same data.

### Evidence

**File:** `src/backtest/engine.py`

```python
def run(self, start_date=None, end_date=None, data=None):
    """Run complete rotation engine backtest."""

    if data is None:
        data = load_spy_data()  # Loads full dataset: 2020-2024

    # No date filtering happens here that splits into train/val/test
    # All 5 years processed together
```

**File:** `SESSION_STATE.md` (Round 6 notes)

```markdown
## CRITICAL DISCOVERY: ZERO PROPER DATA SPLITTING

Everything is contaminated by in-sample overfitting:
- Fixed 22 bugs using full dataset (2020-2024)
- Derived exit timing from full dataset
- "Validated" on same dataset
- Never implemented train/validation/test splits

Consequence: ALL results worthless for live trading.
```

### What Needs to Happen

**Create:** `/Users/zstoc/rotation-engine/backtest_train.py`

```python
# Run engine on 2020-2021 ONLY
from src.backtest.engine import RotationEngine

engine = RotationEngine()
results = engine.run(
    start_date='2020-01-01',
    end_date='2021-12-31'  # Train period only
)

# Save results to: /Users/zstoc/rotation-engine/data/backtest_results/train_period.csv
```

**Create:** `/Users/zstoc/rotation-engine/backtest_validation.py`

```python
# Run engine on 2022-2023 ONLY (no parameter changes)
from src.backtest.engine import RotationEngine

engine = RotationEngine()
results = engine.run(
    start_date='2022-01-01',
    end_date='2023-12-31'  # Validation period only
)

# Save results to: /Users/zstoc/rotation-engine/data/backtest_results/validation_period.csv
# Compare performance vs. train period
# Expected degradation: 20-40%
```

**Create:** `/Users/zstoc/rotation-engine/backtest_test.py`

```python
# Run engine on 2024 ONLY (no parameter changes)
from src.backtest.engine import RotationEngine

engine = RotationEngine()
results = engine.run(
    start_date='2024-01-01',
    end_date='2024-12-31'  # Test period only
)

# Save results to: /Users/zstoc/rotation-engine/data/backtest_results/test_period.csv
# Accept whatever performance you get
```

### How to Verify Fix

After creating scripts:
```bash
python backtest_train.py
python backtest_validation.py
python backtest_test.py

# Compare results:
# Train Sharpe: X
# Validation Sharpe: should be 0.6X to X
# Test Sharpe: accept whatever it is
```

---

## CRITICAL ISSUE #2: Parameter Overfitting

### Root Cause

All parameters derived on full dataset without validation on independent period.

### Evidence

**File:** `src/backtest/engine.py`, lines 81-87

```python
self.profile_configs = {
    'profile_1': {'threshold': 0.6, 'regimes': [1, 3]},  # How was 0.6 chosen?
    'profile_2': {'threshold': 0.5, 'regimes': [2, 5]},  # How was 0.5 chosen?
    'profile_3': {'threshold': 0.5, 'regimes': [3]},
    'profile_4': {'threshold': 0.5, 'regimes': [1]},
    'profile_5': {'threshold': 0.4, 'regimes': [2]},
    'profile_6': {'threshold': 0.6, 'regimes': [4]}
}
```

**Unknown:** Were these thresholds optimized on backtest performance?

**File:** `src/regimes/classifier.py`, lines 44-67

```python
def __init__(self, ...):
    self.trend_threshold = trend_threshold  # 0.02 (2%)
    self.compression_range = compression_range  # 0.035 (3.5%)
    self.rv_rank_low = rv_rank_low  # 0.30
    self.rv_rank_high = rv_rank_high  # 0.80
    self.rv_rank_mid_low = rv_rank_mid_low  # 0.40
    self.rv_rank_mid_high = rv_rank_mid_high  # 0.60
```

**Unknown:** Were these optimized on full dataset?

**File:** `src/trading/execution.py`, lines 20-21

```python
base_spread_atm: float = 0.20,  # BUG FIX Round 7: was 0.03
base_spread_otm: float = 0.30,  # BUG FIX Round 7: was 0.05
```

**Problem:** Changed during Round 7 bug fixing, not validated on independent data

### What Needs to Happen

**Step 1: Document parameter origins**

Add comment to each parameter group:

```python
# src/backtest/engine.py
self.profile_configs = {
    # VALIDATED: These thresholds were derived on train period (2020-2021)
    # and validated on validation period (2022-2023) with <40% degradation
    'profile_1': {'threshold': 0.6, 'regimes': [1, 3]},
    ...
}
```

**Step 2: Re-derive on train period only**

After running backtest_train.py, analyze which parameters maximize Sharpe ratio **on train period only**.

```python
# Pseudo-code for parameter optimization (on train period only)
best_params = None
best_sharpe = -999

for threshold in [0.4, 0.5, 0.6, 0.7]:
    for regimes in [all 36 regime combinations]:
        engine.profile_configs['profile_1'] = {'threshold': threshold, 'regimes': regimes}
        results = engine.run(start_date='2020-01-01', end_date='2021-12-31')  # TRAIN ONLY

        if results['sharpe'] > best_sharpe:
            best_sharpe = results['sharpe']
            best_params = {'threshold': threshold, 'regimes': regimes}

# Use best_params for validation/test
```

**Step 3: Validate on validation period**

```python
# Use best_params from train period
engine.profile_configs = best_params

# Run on validation period WITHOUT FURTHER CHANGES
results_val = engine.run(start_date='2022-01-01', end_date='2023-12-31')

# Measure degradation
degradation = (train_sharpe - val_sharpe) / train_sharpe

if degradation < 0.40:
    print("PASS: Strategy generalizes")
else:
    print("FAIL: Strategy is overfit")
```

### How to Verify Fix

After parameter re-derivation:
```
Train Sharpe: X (derived from train period)
Validation Sharpe: Y (expect Y ≥ 0.6*X)
Degradation: (X-Y)/X < 40%?

If YES: Parameters are valid
If NO: Parameters are overfit
```

---

## HIGH ISSUE #1: Warmup Period Edge Case

### Root Cause

RV20_rank calculation uses partial history during first 60 days

### Code Location

**File:** `src/regimes/signals.py`, lines 114-130

```python
def _compute_walk_forward_percentile(self, series: pd.Series, window: int) -> pd.Series:
    """Compute percentile rank walk-forward (no look-ahead).

    For each point, compute its percentile relative to the PAST window,
    not including the current point.
    """
    result = pd.Series(index=series.index, dtype=float)

    for i in range(len(series)):
        if i < window:  # PROBLEM: When window=60
            # On day 30: only 30 days of history
            lookback = series.iloc[:i]
        else:
            lookback = series.iloc[i-window:i]

        if len(lookback) == 0:
            result.iloc[i] = 0.5  # Default to middle
        else:
            current_val = series.iloc[i]
            pct = (lookback < current_val).sum() / len(lookback)
            result.iloc[i] = pct  # PROBLEM: Unreliable early

    return result
```

### The Problem

On Day 30 of backtest:
```
RV20_rank calculation:
- lookback = series.iloc[:30]  (only 30 days)
- RV20_rank = percentile(RV20[0:30])
- This is NOT the same as percentile(RV20[0:30]) in train period later

Early regime assignments unreliable
```

### What This Causes

**Example impact:**
- Days 1-30: regime classification based on 1-30 days of data
- Day 30: "High vol regime" when RV is low historically (in 30-day sample)
- Later in backtest: same RV level is "low vol regime" (in 60-day sample)
- Entry signals fire at wrong times

**Estimate:** 5-10% P&L degradation in early period

### How to Fix

**Option A: Skip trading during warmup (RECOMMENDED)**

```python
# src/backtest/engine.py, in simulate() method

WARMUP_DAYS = 60

for idx, row in self.data.iterrows():
    current_date = row['date']

    # Skip trading during warmup
    if idx < WARMUP_DAYS:
        # Accumulate features but don't trade
        continue

    # Normal trading after warmup
    [normal trading logic]
```

**Option B: Adjust position size based on confidence**

```python
def get_position_size(self, data_points_available, window=60):
    """Scale position size based on data confidence."""
    if data_points_available < window:
        confidence = data_points_available / window
        return base_size * confidence
    else:
        return base_size
```

### How to Verify Fix

After implementing fix:

```python
# Measure: Do most trades occur after Day 60?
trade_dates = [t.entry_date for t in simulator.trades]
trades_before_day60 = sum(1 for d in trade_dates if d < start_date + timedelta(days=60))
trades_after_day60 = sum(1 for d in trade_dates if d >= start_date + timedelta(days=60))

# Should see:
# trades_before_day60 < 10% of total
# trades_after_day60 > 90% of total
```

---

## HIGH ISSUE #2: Transaction Costs Underestimated

### Root Cause

Slippage for large orders (50+ contracts) assumes 50% of half-spread, but real markets are 2-4x worse.

### Code Location

**File:** `src/trading/execution.py`, lines 127-186

```python
def get_execution_price(
    self,
    mid_price: float,
    side: str,
    moneyness: float,
    dte: int,
    vix_level: float = 20.0,
    is_strangle: bool = False,
    quantity: int = 1
) -> float:
    """
    Get realistic execution price including bid-ask spread and slippage.
    """
    spread = self.get_spread(mid_price, moneyness, dte, vix_level, is_strangle)
    half_spread = spread / 2.0

    # Size-based slippage as % of half-spread
    abs_qty = abs(quantity)
    if abs_qty <= 10:
        slippage_pct = self.slippage_small  # 10% of half-spread
    elif abs_qty <= 50:
        slippage_pct = self.slippage_medium  # 25% of half-spread
    else:
        slippage_pct = self.slippage_large  # 50% of half-spread

    slippage = half_spread * slippage_pct

    if side == 'buy':
        return mid_price + half_spread + slippage
```

### The Problem

Example: 50-contract ATM straddle on 2 DTE

```
Calculation:
- Mid price: $5.00
- Spread: $0.50 (base $0.20 × 1.0 × 1.3 × 1.25)
- Half-spread: $0.25
- Slippage (50% of half): $0.125
- Total cost: 2 × ($0.25 + $0.125) = $0.75 per contract
- Total for 100 contracts: $75

Real market execution:
- Typical 2 DTE ATM straddle spread: $0.50-1.00
- Bid-ask for 50 contracts: likely $1.00-2.00 wider
- Real slippage: $1.00-2.00 per contract
- Real total: $100-200 per contract

Underestimation: 2-4x too low
```

### Impact on P&L

```
Number of trades: ~500 per year
Avg trade cost per contract: 100 contracts

Simulated cost: $75 × 500 = $37,500
Real cost: $150-300 × 500 = $75,000-150,000

P&L inflated by: $37,500-112,500 in backtest
This is massive on a ~$100,000 strategy
```

### How to Fix

**Step 1: Research real execution costs**

```python
# Real data needed (from broker/market data)
# Example for 2 DTE ATM straddles:
#   10 contracts: $0.25 spread
#   50 contracts: $1.00 spread (4x wider!)
#   100 contracts: $2.00 spread (8x wider!)

# For 50-contract orders on 2 DTE:
# Real slippage is NOT 50% of half-spread
# Real slippage is more like 2-3x the half-spread
```

**Step 2: Update slippage percentages**

```python
# src/trading/execution.py, lines 56-59
self.slippage_small = slippage_small  # 10% of half-spread (1-10 contracts)
self.slippage_medium = slippage_medium  # 50% of half-spread (11-50 contracts)
self.slippage_large = slippage_large  # 200% of half-spread (50+ contracts) ← INCREASE THIS

# Change from:
# slippage_large = 0.50  (50% of half-spread)
# To:
# slippage_large = 2.00  (200% of half-spread, closer to reality)
```

**Step 3: Add position sizing constraints**

```python
# src/trading/profiles/profile_*.py
# Add constraint: Never trade more than 20 contracts at once

class Profile1LongGamma:
    def trade_constructor(self, row, trade_id):
        # ... existing logic ...

        # ADD: Constrain position size
        MAX_CONTRACTS = 20  # Never more than 20 contracts
        quantity = min(quantity, MAX_CONTRACTS)

        return trade
```

**Step 4: Validate against real data**

```python
# Get real market quotes for SPY straddles
# Example: lookup real 2 DTE ATM straddle quotes from Polygon data
# Compare simulated vs. real execution prices
# Iterate until slippage percentages match reality
```

### How to Verify Fix

```python
# After adjusting slippage:

# Test on single trade:
trade = create_straddle_trade(strike=450, dte=2, quantity=50)
exec_prices = execution_model.get_execution_price(
    mid_price=5.00,
    side='buy',
    quantity=50,
    dte=2
)

# Should see:
# OLD: total cost ~$75
# NEW: total cost ~$150-200 (2-3x higher)
# This matches real market costs
```

---

## MEDIUM ISSUE #1: Portfolio Aggregation Validation

### Code Location

**File:** `src/backtest/portfolio.py`, lines 24-118

### The Question

How are profile weights transformed from regime/score-based allocation to dollar weights?

```python
# Line 83: What is weight_series?
weight_series = portfolio[weight_col] if weight_col in portfolio.columns else 0.0

# Where did these weights come from?
# Are they discrete (0.0, 0.2, 0.5, 1.0)?
# Or continuous (0.0, 0.15, 0.37, 0.62)?
```

### What Needs Investigation

**File:** `src/backtest/rotation.py` (NOT provided in audit, but referenced)

```python
# This file contains RotationAllocator.allocate_daily()
# which generates the weight columns
# Need to verify:
# 1. Are weights discrete rebalancing or continuous?
# 2. What's the rebalancing frequency?
# 3. Are weights realistic?
```

### How to Fix

1. Review `src/backtest/rotation.py` allocate_daily() method
2. Print sample allocations for 10-day window
3. Verify no mid-day weight changes
4. Verify weights match realistic capital allocation

---

## MEDIUM ISSUE #2: Profile Smoothing Span

### Code Location

**File:** `src/profiles/detectors.py`, lines 66-70

```python
# 3. Apply EMA smoothing to noisy profiles (SDG, SKEW)
# BUG FIX (2025-11-18): Agent #3 found span=3 too short, causes noise
# Increased to span=7 for better noise reduction
df['profile_2_SDG'] = df['profile_2_SDG_raw'].ewm(span=7, adjust=False).mean()
df['profile_5_SKEW'] = df['profile_5_SKEW_raw'].ewm(span=7, adjust=False).mean()
```

### The Question

**Was span=7 validated on independent data?**

Evidence: It was changed during bug fixing, not validated with proper methodology.

### What This Means

```
EMA span=7 for daily data ≈ ~2 weeks of smoothing

If raw score spikes on Day 1 (high gamma):
- Without smoothing: entry on Day 1
- With span=7: entry gradually by Day 5-7
- Loss of 5-7 days of opportunity

For short-dated gamma (2-3 DTE moves), this is significant
```

### How to Fix

**Test different spans on train period only:**

```python
# Test span values: 3, 5, 7, 10, 14
for span in [3, 5, 7, 10, 14]:
    df_test = data.copy()
    df_test['profile_2_SDG'] = df_test['profile_2_SDG_raw'].ewm(span=span, adjust=False).mean()

    # Run backtest on train period (2020-2021)
    results = engine.run(data=df_test, start_date='2020-01-01', end_date='2021-12-31')

    print(f"span={span}: Sharpe={results['sharpe']:.3f}, avg_entry_delay={calc_entry_delay(df_test)}")

# Choose span that maximizes Sharpe on train period
# Then validate on validation period without further changes
```

### How to Verify Fix

After selecting optimal span:

```python
# Measure entry delay impact
def calc_entry_delay(df):
    raw_entries = (df['profile_2_SDG_raw'] > 0.5) & (df['profile_2_SDG_raw'].shift(1) <= 0.5)
    smoothed_entries = (df['profile_2_SDG'] > 0.5) & (df['profile_2_SDG'].shift(1) <= 0.5)

    # Measure days between raw and smoothed entry signals
    # Should be < window_size
    return (raw_entries.rolling(window=20).sum() - smoothed_entries.rolling(window=20).sum()).mean()
```

---

## SUMMARY: FILES TO MODIFY

| Issue | File | Lines | Action |
|-------|------|-------|--------|
| Data split | CREATE | - | `backtest_train.py` |
| Data split | CREATE | - | `backtest_validation.py` |
| Data split | CREATE | - | `backtest_test.py` |
| Parameter docs | `src/backtest/engine.py` | 81-87 | Add comments on parameter origin |
| Warmup edge case | `src/regimes/signals.py` | 114-130 | Add skip-warmup or confidence adjustment |
| Warmup edge case | `src/trading/simulator.py` | 148-160 | Skip trading on days < 60 |
| Transaction costs | `src/trading/execution.py` | 56-59 | Increase slippage_large from 0.50 to 2.00 |
| Transaction costs | `src/trading/profiles/*.py` | Various | Add MAX_CONTRACTS constraint |
| Profile smoothing | `src/profiles/detectors.py` | 66-70 | Test span values 3-14 on train period |
| Portfolio validation | `src/backtest/rotation.py` | TBD | Review allocate_daily() implementation |

---

**Total remediation effort:** 7-11 hours

