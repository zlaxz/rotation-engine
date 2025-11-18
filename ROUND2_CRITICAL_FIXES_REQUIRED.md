# CRITICAL FIXES REQUIRED - ROUND 2 AUDIT

**Status**: BLOCK DEPLOYMENT
**Date**: 2025-11-18
**Auditor**: backtest-bias-auditor

---

## Executive Summary

Round 2 audit found **2 CRITICAL** and **5 HIGH** severity bugs that invalidate all current backtest results.

**Primary Issue**: Train period methodology is fundamentally broken - trains on default parameters, derives "optimal" parameters, but never re-runs backtest with those optimal parameters. This creates circular logic that invalidates entire train/validation/test framework.

**Secondary Issue**: Look-ahead bias in feature calculation and entry conditions gives backtest perfect foresight of same-day returns and volatility.

---

## CRITICAL-001: Train Methodology Broken (BLOCKS EVERYTHING)

### The Problem

```python
# Current broken flow:
exit_engine = ExitEngine(phase=1)  # Uses defaults: {LDG: 7, SDG: 5, ...}

for profile in profiles:
    trades = backtest(profile, exit_engine)  # Runs with defaults

derived_params = derive_from_results(trades)  # Derives: {LDG: 6, SDG: 4, ...}
save(derived_params)  # Saves for validation/test

# BUT: Train results were generated with DIFFERENT exit days than what we derived!
# Validation will use exit days that train never tested!
```

### Why This Breaks Everything

1. Train backtest runs with **default exit days** (LDG: 7, SDG: 5, etc.)
2. We derive "optimal" exit days from those results (LDG: 6, SDG: 4, etc.)
3. We save the "optimal" exit days for validation/test
4. **But train results were never generated using those "optimal" days**
5. Validation/test use different parameters than train tested
6. Entire train/validation/test methodology is invalid

### The Fix

Two-phase train process:

```python
def main():
    """CORRECTED: Two-phase train with parameter derivation"""

    spy = load_spy_data()
    polygon = PolygonOptionsLoader()
    tracker = TradeTracker(polygon)
    profiles = get_profile_configs()

    # ====================================================================
    # PHASE 1: DERIVATION - Use defaults to find optimal exit days
    # ====================================================================
    print("\n" + "="*80)
    print("PHASE 1: PARAMETER DERIVATION (using default exit days)")
    print("="*80)

    exit_engine_default = ExitEngine(phase=1)  # Default exit days

    phase1_results = {}
    for profile_id, config in profiles.items():
        trades = run_profile_backtest(profile_id, config, spy, tracker, exit_engine_default)
        phase1_results[profile_id] = {
            'trades': trades,
            'summary': analyze_trades(trades),
            'config': config
        }

    # Derive optimal exit days from phase 1 results
    derived_params = derive_parameters_from_train(phase1_results)

    print(f"\n✅ PHASE 1 COMPLETE - Derived exit days:")
    for profile_id, exit_day in derived_params['exit_days'].items():
        default_day = exit_engine_default.get_exit_day(profile_id)
        print(f"   {profile_id}: {default_day} (default) → {exit_day} (optimal)")

    # ====================================================================
    # PHASE 2: VALIDATION - Re-run with optimized exit days
    # ====================================================================
    print("\n" + "="*80)
    print("PHASE 2: TRAIN BACKTEST (using optimized exit days)")
    print("="*80)

    exit_engine_optimized = ExitEngine(phase=1, custom_exit_days=derived_params['exit_days'])

    phase2_results = {}
    for profile_id, config in profiles.items():
        trades = run_profile_backtest(profile_id, config, spy, tracker, exit_engine_optimized)
        phase2_results[profile_id] = {
            'trades': trades,
            'summary': analyze_trades(trades),
            'config': config
        }

    # Compare phase 1 vs phase 2
    print("\n" + "="*80)
    print("PHASE 1 vs PHASE 2 COMPARISON")
    print("="*80)

    for profile_id in profiles.keys():
        p1_summary = phase1_results[profile_id]['summary']
        p2_summary = phase2_results[profile_id]['summary']

        p1_pnl = p1_summary['total_pnl']
        p2_pnl = p2_summary['total_pnl']
        pnl_change = ((p2_pnl - p1_pnl) / abs(p1_pnl) * 100) if p1_pnl != 0 else 0

        print(f"\n{profile_id}:")
        print(f"  Phase 1 (default): P&L=${p1_pnl:.0f}, Trades={p1_summary['total_trades']}")
        print(f"  Phase 2 (optimized): P&L=${p2_pnl:.0f}, Trades={p2_summary['total_trades']}")
        print(f"  Change: {pnl_change:+.1f}%")

    # ====================================================================
    # SAVE PHASE 2 RESULTS (these are the REAL train results)
    # ====================================================================
    output_dir = Path('/Users/zstoc/rotation-engine/data/backtest_results/train_2020-2021')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save final results
    results_file = output_dir / 'results.json'
    with open(results_file, 'w') as f:
        json.dump(phase2_results, f, indent=2, default=str)
    print(f"\n✅ Saved PHASE 2 results: {results_file}")

    # Save derived parameters
    params_file = Path('/Users/zstoc/rotation-engine/config/train_derived_params.json')
    with open(params_file, 'w') as f:
        json.dump(derived_params, f, indent=2, default=str)
    print(f"✅ Saved derived parameters: {params_file}")

    # Save phase comparison for analysis
    comparison_file = output_dir / 'phase_comparison.json'
    comparison = {
        'phase1_default': {pid: r['summary'] for pid, r in phase1_results.items()},
        'phase2_optimized': {pid: r['summary'] for pid, r in phase2_results.items()}
    }
    with open(comparison_file, 'w') as f:
        json.dump(comparison, f, indent=2, default=str)
    print(f"✅ Saved phase comparison: {comparison_file}")

    print("\n" + "="*80)
    print("TRAIN PERIOD COMPLETE")
    print("="*80)
    print("\n✅ Phase 2 results are the REAL train results")
    print("✅ These exit days will be used in validation/test:")
    for profile_id, exit_day in derived_params['exit_days'].items():
        print(f"   {profile_id}: Day {exit_day}")
    print("\n📊 Next step: Review results, then run validation period (2022-2023)\n")
```

### Files to Modify

- `scripts/backtest_train.py` - Complete rewrite of main() function

### Verification

1. Check phase_comparison.json - should show P&L differences between default and optimized
2. Verify config/train_derived_params.json exit days match what phase 2 used
3. Verify validation script loads same exit days that phase 2 tested

---

## CRITICAL-002: Feature Calculation Look-Ahead Bias

### The Problem

```python
# Current broken flow:
for f in spy_files:
    df = pd.read_parquet(f)
    file_date = pd.to_datetime(df['ts'].iloc[0]).date()

    if file_date < TRAIN_START or file_date > TRAIN_END:
        continue  # ❌ FILTERS DATA FIRST

    spy_data.append({...})

spy = pd.DataFrame(spy_data)

# ❌ CALCULATES FEATURES ON FILTERED DATA
spy['MA50'] = spy['close'].rolling(50).mean()  # First 50 rows = NaN!

# Result: Jan 1, 2020 has no MA50 (should use Nov-Dec 2019 data)
#         Jan 1, 2022 has no MA50 (should use Nov-Dec 2021 data)
```

### Why This Is Wrong

At any point in time, features should use ALL historical data available, not just data from current period. On Jan 15, 2022, we KNOW what happened in 2021, 2020, 2019, etc. The MA50 should use those prices.

By filtering data BEFORE calculating features, we create artificial feature values that don't match reality.

### The Fix

Load continuous data, calculate features, THEN filter:

```python
def load_spy_data() -> pd.DataFrame:
    """Load SPY data with proper temporal feature calculation

    CRITICAL: Calculate features BEFORE filtering to period.
    This ensures features at period start use historical data,
    not artificial NaN values.
    """
    print("Loading SPY data (TRAIN PERIOD ONLY: 2020-2021)...")

    spy_files = sorted(glob.glob('/Volumes/VelocityData/velocity_om/parquet/stock/SPY/*.parquet'))
    spy_data = []

    # STEP 1: Load WARMUP period (60 days before train start)
    warmup_start = TRAIN_START - timedelta(days=60)
    print(f"Loading from {warmup_start} (60-day warmup) to {TRAIN_END}")

    for f in spy_files:
        df = pd.read_parquet(f)
        if len(df) > 0:
            file_date = pd.to_datetime(df['ts'].iloc[0]).date()

            # Load from warmup_start (NOT TRAIN_START)
            if file_date < warmup_start or file_date > TRAIN_END:
                continue

            spy_data.append({
                'date': file_date,
                'open': df['open'].iloc[0],
                'high': df['high'].max(),
                'low': df['low'].min(),
                'close': df['close'].iloc[-1],
                'volume': df['volume'].sum()
            })

    spy = pd.DataFrame(spy_data).sort_values('date').reset_index(drop=True)

    # STEP 2: Calculate features on FULL dataset (including warmup)
    spy['return_1d'] = spy['close'].pct_change()

    # ⚠️  CRITICAL FIX: Shift return features by 1 day (see HIGH-003)
    # At market open on day T, we only know returns through T-1
    spy['return_5d'] = spy['close'].pct_change(5).shift(1)
    spy['return_10d'] = spy['close'].pct_change(10).shift(1)
    spy['return_20d'] = spy['close'].pct_change(20).shift(1)

    spy['MA20'] = spy['close'].rolling(20).mean()
    spy['MA50'] = spy['close'].rolling(50).mean()
    spy['slope_MA20'] = spy['MA20'].pct_change(20)
    spy['slope_MA50'] = spy['MA50'].pct_change(50)

    # ⚠️  CRITICAL FIX: Shift RV features by 1 day (see HIGH-002)
    # At market open on day T, we only know volatility through T-1
    spy['RV5'] = spy['return_1d'].rolling(5).std().shift(1) * np.sqrt(252)
    spy['RV10'] = spy['return_1d'].rolling(10).std().shift(1) * np.sqrt(252)
    spy['RV20'] = spy['return_1d'].rolling(20).std().shift(1) * np.sqrt(252)

    spy['HL'] = spy['high'] - spy['low']
    spy['ATR5'] = spy['HL'].rolling(5).mean()
    spy['ATR10'] = spy['HL'].rolling(10).mean()

    spy['slope'] = spy['close'].pct_change(20).shift(1)

    # STEP 3: Filter to TRAIN PERIOD (after features calculated)
    spy_filtered = spy[spy['date'] >= TRAIN_START].copy()

    # STEP 4: Verify enforcement
    actual_start = spy_filtered['date'].min()
    actual_end = spy_filtered['date'].max()

    print(f"✅ TRAIN PERIOD ENFORCED")
    print(f"   Expected: {TRAIN_START} to {TRAIN_END}")
    print(f"   Actual:   {actual_start} to {actual_end}")

    if actual_start < TRAIN_START or actual_end > TRAIN_END:
        raise ValueError(f"DATA LEAK DETECTED: Data outside train period!")

    # STEP 5: Verify features are warm
    first_60_rows = spy_filtered.head(60)
    null_counts = first_60_rows.isnull().sum()

    feature_cols = ['MA20', 'MA50', 'RV5', 'RV10', 'RV20', 'return_5d', 'return_10d', 'return_20d']
    null_features = {col: null_counts[col] for col in feature_cols if col in null_counts.index and null_counts[col] > 0}

    if null_features:
        print(f"⚠️  WARNING: Features not fully warm in first 60 days:")
        for col, count in null_features.items():
            print(f"   {col}: {count} NaN values")
    else:
        print(f"✅ All features warm (no NaN in first 60 days)")

    print(f"\nLoaded {len(spy_filtered)} days from {spy_filtered['date'].min()} to {spy_filtered['date'].max()}\n")

    return spy_filtered
```

### Files to Modify

- `scripts/backtest_train.py` - load_spy_data() function
- `scripts/backtest_validation.py` - load_spy_data() function
- `scripts/backtest_test.py` - load_spy_data() function

### Verification

1. Check spy_filtered.head(10) - should have NO NaN in MA50, RV20
2. Compare first month trade count before/after - should be similar
3. Manually verify Jan 1, 2020 MA50 uses Nov-Dec 2019 prices

---

## HIGH-003: Entry Conditions Use Same-Day Returns

### The Problem

```python
# Entry condition (executed at market OPEN on day T)
'entry_condition': lambda row: row.get('return_20d', 0) > 0.02

# But return_20d includes TODAY's close (day T)
spy['return_20d'] = spy['close'].pct_change(20)

# At market open, we DON'T KNOW today's close yet!
```

### The Fix

Already included in CRITICAL-002 fix above:

```python
# Shift return features by 1 day
spy['return_5d'] = spy['close'].pct_change(5).shift(1)
spy['return_10d'] = spy['close'].pct_change(10).shift(1)
spy['return_20d'] = spy['close'].pct_change(20).shift(1)
spy['RV5'] = spy['return_1d'].rolling(5).std().shift(1) * np.sqrt(252)
spy['RV10'] = spy['return_1d'].rolling(10).std().shift(1) * np.sqrt(252)
spy['RV20'] = spy['return_1d'].rolling(20).std().shift(1) * np.sqrt(252)
```

---

## HIGH-001: Profile_5_SKEW Strike Calculation Wrong

### The Problem

```python
# Profile claims "5% OTM"
'Profile_5_SKEW': {
    'structure': 'Long OTM Put (5% OTM)',
    ...
}

# But strike calculated as ATM
strike = round(spot)  # ❌ ATM, not 5% OTM
```

### The Fix

```python
def run_profile_backtest(...):
    # ...
    spot = row['close']
    expiry = get_expiry_for_dte(entry_date, config['dte_target'])

    # Calculate strike based on profile structure
    if profile_id == 'Profile_5_SKEW':
        # 5% OTM put: strike 5% below spot
        strike = round(spot * 0.95)
    else:
        # ATM for all other profiles
        strike = round(spot)

    print(f"ENTRY: {entry_date} | SPY={spot:.2f} | Strike={strike} | Expiry={expiry}")
    # ...
```

### Files to Modify

- `scripts/backtest_train.py` - run_profile_backtest() function
- `scripts/backtest_validation.py` - run_profile_backtest() function
- `scripts/backtest_test.py` - run_profile_backtest() function

---

## HIGH-005: TradeTracker Uses Wrong Transaction Costs

### The Problem

```python
# TradeTracker uses fixed costs
commission = 2.60  # Per trade (WRONG - should be per contract)
spread = 0.03  # Fixed (WRONG - should vary by moneyness, DTE, vol)

# Compare to ExecutionModel which has:
# - Base commission: $0.65/contract
# - OCC fees: $0.055/contract
# - FINRA fees: $0.00205/contract
# - SEC fees: variable
# - Size-based slippage
# - Vol-adjusted spreads
```

### The Fix

```python
# In TradeTracker.__init__:
from src.trading.execution import ExecutionModel

def __init__(self, polygon_loader: PolygonOptionsLoader):
    self.polygon = polygon_loader
    self.execution_model = ExecutionModel()

# In track_trade(), replace fixed costs:

# Entry costs
entry_cost = 0.0
for leg in position['legs']:
    opt_type = leg['type']
    qty = leg['qty']

    # Get execution price (bid/ask already includes spread)
    if qty > 0:
        price = self.polygon.get_option_price(entry_date, strike, expiry, opt_type, 'ask')
    else:
        price = self.polygon.get_option_price(entry_date, strike, expiry, opt_type, 'bid')

    if price is None:
        return None

    leg_cost = qty * price * 100
    entry_cost += leg_cost

# Add commissions using ExecutionModel
num_contracts = sum(abs(leg['qty']) for leg in position['legs'])
is_short = any(leg['qty'] < 0 for leg in position['legs'])
max_premium = max(entry_prices.values()) if entry_prices else 0

entry_cost += self.execution_model.get_commission_cost(
    num_contracts,
    is_short=is_short,
    premium=max_premium
)

# MTM P&L calculation
for leg in position['legs']:
    opt_type = leg['type']
    qty = leg['qty']

    mid_price = self.polygon.get_option_price(day_date, strike, expiry, opt_type, 'mid')
    if mid_price is None:
        break

    # Apply execution model for realistic exit price
    moneyness = abs(strike - day_spot) / day_spot
    dte_remaining = (expiry - day_date).days
    vix_proxy = day_row.get('RV20', 0.20) * 100 * 1.2

    exec_price = self.execution_model.get_execution_price(
        mid_price=mid_price,
        side='sell' if qty > 0 else 'buy',  # Closing position (reverse side)
        moneyness=moneyness,
        dte=dte_remaining,
        vix_level=vix_proxy,
        quantity=abs(qty)
    )

    exit_value = qty * exec_price * 100
    mtm_value += exit_value

# Exit commission
exit_commission = self.execution_model.get_commission_cost(
    num_contracts,
    is_short=(not is_short),  # Reverse of entry
    premium=max(current_prices.values()) if current_prices else 0
)

mtm_pnl = mtm_value - entry_cost - exit_commission
```

### Files to Modify

- `src/analysis/trade_tracker.py` - track_trade() method

---

## Execution Plan

### Phase 1: Fix CRITICAL Issues (2-3 hours)

1. **CRITICAL-001**: Rewrite backtest_train.py with two-phase methodology
   - Test on small date range first
   - Verify phase 1 and phase 2 produce different results
   - Verify derived params match phase 2 usage

2. **CRITICAL-002 + HIGH-003**: Fix feature calculation in all 3 scripts
   - Add warmup period loading
   - Shift return and RV features by 1 day
   - Verify no NaN in first 60 rows

### Phase 2: Fix HIGH Issues (1-2 hours)

3. **HIGH-001**: Fix Profile_5_SKEW strike calculation
4. **HIGH-005**: Replace fixed costs with ExecutionModel in TradeTracker

### Phase 3: Verification (1 hour)

5. Run complete train backtest with all fixes
6. Review results for sanity
7. Compare to old results (expect degradation from removed look-ahead bias)

### Phase 4: Proceed to Validation

8. If train results acceptable, run validation period
9. Calculate degradation metrics
10. If degradation < 40%, proceed to test

---

## Expected Impact on Results

### From Look-Ahead Bias Removal

- **Trade count**: Expect 10-20% reduction (can't see same-day returns)
- **Sharpe ratio**: Expect 20-40% reduction (no perfect foresight)
- **Win rate**: Expect 5-10% reduction
- **Peak capture**: May improve (using correct peak timing)

### From Transaction Cost Fix

- **P&L**: Expect 5-15% reduction (more realistic costs)
- **Peak timing**: Expect earlier exits (costs erode faster)

### Overall Expected Degradation

Combining both fixes: **30-50% degradation from current results**

This is NORMAL and EXPECTED. Current results are inflated by bugs. Fixed results are realistic.

---

## DO NOT PROCEED UNTIL FIXED

Current results are INVALID. Do not:
- ❌ Run validation period
- ❌ Run test period
- ❌ Make trading decisions based on current results
- ❌ Present current results to anyone

All work must be redone after fixes are implemented.

---

## Questions Before Starting?

1. Do you understand why CRITICAL-001 invalidates current results?
2. Do you understand why features must be calculated before filtering?
3. Do you want to see the expected impact quantified before fixing?
4. Should we run on 3-month subset first to validate fixes work?

Ready to proceed with fixes?
