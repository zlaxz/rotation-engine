# BACKTEST BIAS AUDIT REPORT - ROUND 2

## Executive Summary
**FAIL** - Overall assessment
**2** CRITICAL issues found
**5** HIGH severity issues found
**3** MEDIUM severity issues found
**4** LOW severity issues found

**Recommendation**: **BLOCK DEPLOYMENT** - Critical temporal violations and parameter contamination found

---

## CRITICAL Issues (Block Deployment)

### CRITICAL-001: Train-Derived Parameters Used During Train Period Derivation
**Severity**: CRITICAL
**Location**: scripts/backtest_train.py:411-412
**Violation Type**: Circular dependency / Look-ahead bias

**Description**:
The train script initializes ExitEngine with default parameters (line 411), then derives new parameters from backtest results (line 432), but never re-runs the backtest with the newly derived parameters. This creates a fundamental logical contradiction:

1. Backtest runs with default exit days (lines 235-240: gets exit_day from engine)
2. Derives "optimal" exit days from those results (lines 335-391)
3. Saves derived parameters for validation/test periods
4. But train results were NOT generated using those "derived" parameters

**Evidence**:
```python
# Line 411: Initialize with defaults
exit_engine = ExitEngine(phase=1)  # Uses PROFILE_EXIT_DAYS defaults

# Lines 422-423: Run backtest with defaults
for profile_id, config in profiles.items():
    trades = run_profile_backtest(profile_id, config, spy, tracker, exit_engine)

# Line 432: Derive parameters from results generated with defaults
derived_params = derive_parameters_from_train(all_results)
```

**Impact**:
This is a fundamental methodology violation:
- Train results are invalid because they don't use train-derived parameters
- Validation/test will use different exit days than what train used
- Creates train/test mismatch that invalidates entire walk-forward methodology
- The "derived" parameters were not actually derived from train - they're post-hoc analysis of wrong parameters

**Fix**:
Two-phase train process required:

```python
def main():
    # PHASE 1: Derive parameters
    spy = load_spy_data()
    polygon = PolygonOptionsLoader()
    tracker = TradeTracker(polygon)

    # Use defaults to derive optimal exit days
    exit_engine = ExitEngine(phase=1)

    # Run backtests with defaults
    phase1_results = {}
    for profile_id, config in profiles.items():
        trades = run_profile_backtest(profile_id, config, spy, tracker, exit_engine)
        phase1_results[profile_id] = {'trades': trades, 'config': config}

    # Derive optimal parameters
    derived_params = derive_parameters_from_train(phase1_results)

    # PHASE 2: Re-run with derived parameters
    exit_engine_optimized = ExitEngine(phase=1, custom_exit_days=derived_params['exit_days'])

    # Run final train backtest with optimized parameters
    final_results = {}
    for profile_id, config in profiles.items():
        trades = run_profile_backtest(profile_id, config, spy, tracker, exit_engine_optimized)
        final_results[profile_id] = analyze_trades(trades)

    # Save final results (using optimized parameters)
    save_results(final_results, derived_params)
```

**Verification**:
1. Check that train results use same exit days as validation/test
2. Verify derived_params['exit_days'] matches exit days used in train backtest
3. Compare phase1 vs phase2 results to quantify parameter optimization impact

---

### CRITICAL-002: Feature Calculation Violates Temporal Boundaries
**Severity**: CRITICAL
**Location**: All three scripts (train/validation/test) - load_spy_data() function
**Violation Type**: Look-ahead bias via rolling window initialization

**Description**:
The scripts enforce strict period boundaries (e.g., 2020-2021 for train) but calculate rolling features AFTER filtering data. This means the first 50+ days of each period use rolling features that were calculated WITHOUT data from the preceding period, creating different feature values than would exist in live trading or if periods were analyzed sequentially.

**Evidence**:
```python
# backtest_train.py lines 59-75
for f in spy_files:
    df = pd.read_parquet(f)
    if len(df) > 0:
        file_date = pd.to_datetime(df['ts'].iloc[0]).date()

        # ENFORCE TRAIN PERIOD: Skip data outside train boundaries
        if file_date < TRAIN_START or file_date > TRAIN_END:
            continue  # Data filtered BEFORE feature calculation

        spy_data.append(...)

spy = pd.DataFrame(spy_data)

# Lines 96-104: Rolling features calculated on filtered data
spy['MA20'] = spy['close'].rolling(20).mean()  # First 20 rows = NaN
spy['MA50'] = spy['close'].rolling(50).mean()  # First 50 rows = NaN
spy['RV20'] = spy['return_1d'].rolling(20).std() * np.sqrt(252)
```

**Impact**:
- Train period (2020-01-01 start): MA50 is NaN until 2020-03-01 (50 days later)
- Validation period (2022-01-01 start): MA50 is NaN until 2022-03-01
- Test period (2024-01-01 start): MA50 is NaN until 2024-03-01
- In live trading (or proper sequential backtest), January 2022 would use MA50 from November-December 2021
- This creates artificial regime/feature differences that don't exist in reality
- Entry conditions depend on these features, so trade timing is contaminated

**Fix**:
Load continuous data, calculate features, THEN filter to period:

```python
def load_spy_data() -> pd.DataFrame:
    """Load SPY data with proper temporal feature calculation"""

    print("Loading SPY data (TRAIN PERIOD ONLY: 2020-2021)...")

    spy_files = sorted(glob.glob('/Volumes/VelocityData/velocity_om/parquet/stock/SPY/*.parquet'))
    spy_data = []

    # STEP 1: Load broader range (60 days before train start for warmup)
    warmup_start = TRAIN_START - timedelta(days=60)

    for f in spy_files:
        df = pd.read_parquet(f)
        if len(df) > 0:
            file_date = pd.to_datetime(df['ts'].iloc[0]).date()

            # Load from warmup_start (not TRAIN_START)
            if file_date < warmup_start or file_date > TRAIN_END:
                continue

            spy_data.append(...)

    spy = pd.DataFrame(spy_data)

    # STEP 2: Calculate features on full dataset (including warmup)
    spy['return_1d'] = spy['close'].pct_change()
    spy['MA20'] = spy['close'].rolling(20).mean()
    spy['MA50'] = spy['close'].rolling(50).mean()
    spy['RV20'] = spy['return_1d'].rolling(20).std() * np.sqrt(252)

    # STEP 3: Filter to actual train period AFTER features calculated
    spy = spy[spy['date'] >= TRAIN_START].copy()

    # STEP 4: Verify enforcement
    actual_start = spy['date'].min()
    actual_end = spy['date'].max()

    print(f"✅ TRAIN PERIOD ENFORCED")
    print(f"   Expected: {TRAIN_START} to {TRAIN_END}")
    print(f"   Actual:   {actual_start} to {actual_end}")

    if actual_start < TRAIN_START or actual_end > TRAIN_END:
        raise ValueError(f"DATA LEAK DETECTED: Data outside train period!")

    # STEP 5: Verify features are warm (no NaN for first 60 rows)
    warmup_rows = 60
    if spy.head(warmup_rows).isnull().any().any():
        print("⚠️  WARNING: Features not fully warmed up at period start")

    return spy
```

**Verification**:
1. Check spy.head(60) - should have NO NaN values in MA50, RV20 after fix
2. Compare first month of trades before/after fix - should be different
3. Verify Jan 2022 MA50 matches Dec 2021 close prices (continuity check)

---

## HIGH Severity Issues

### HIGH-001: Strike Calculation Missing for OTM Profiles
**Severity**: HIGH
**Location**: All three backtest scripts - Profile_5_SKEW definition
**Violation Type**: Implementation bug causing execution to fail

**Description**:
Profile_5_SKEW is defined as "Long OTM Put (5% OTM)" but the strike calculation uses ATM rounding (`strike = round(spot)`). This means the strategy is buying ATM puts, not 5% OTM puts as specified.

**Evidence**:
```python
# Line 186-189: Profile definition claims OTM
'Profile_5_SKEW': {
    'structure': 'Long OTM Put (5% OTM)',
    ...
}

# Line 270: Strike calculated as ATM (NOT 5% OTM)
strike = round(spot)
```

**Impact**:
- Profile_5_SKEW results are invalid - testing wrong structure
- ATM vs 5% OTM puts have very different Greeks and pricing
- Skew convexity thesis cannot be tested with ATM puts
- All Profile_5_SKEW metrics are meaningless

**Fix**:
```python
def run_profile_backtest(...):
    # ...
    spot = row['close']
    expiry = get_expiry_for_dte(entry_date, config['dte_target'])

    # Calculate strike based on profile structure
    if config.get('otm_pct'):
        # OTM put: strike below spot
        if 'put' in config['structure'].lower() and 'otm' in config['structure'].lower():
            strike = round(spot * (1 - config['otm_pct']))
        # OTM call: strike above spot
        elif 'call' in config['structure'].lower() and 'otm' in config['structure'].lower():
            strike = round(spot * (1 + config['otm_pct']))
        else:
            strike = round(spot)  # ATM
    else:
        strike = round(spot)  # ATM default

# Update Profile_5_SKEW config:
'Profile_5_SKEW': {
    'name': 'Skew Convexity',
    'structure': 'Long OTM Put (5% OTM)',
    'otm_pct': 0.05,  # ADD THIS
    ...
}
```

**Verification**:
1. Check strike vs spot for Profile_5_SKEW trades - should be 5% below
2. Verify put delta is ~0.30-0.35 (typical for 5% OTM) not ~0.50 (ATM)
3. Re-run backtest and compare results

---

### HIGH-002: Disaster Filter Uses Future Data (RV5)
**Severity**: HIGH
**Location**: All three scripts, line ~262
**Violation Type**: Subtle look-ahead bias

**Description**:
The disaster filter checks `row.get('RV5', 0) > 0.22` BEFORE entering trade, but RV5 is a 5-day rolling volatility. On day T, RV5 includes returns from days T-4 through T, but we're making a decision at market open on day T when we only know returns through T-1.

**Evidence**:
```python
# Line 262 (all scripts)
if row.get('RV5', 0) > 0.22:
    continue

# But RV5 calculation (line 102):
spy['RV5'] = spy['return_1d'].rolling(5).std() * np.sqrt(252)

# And return_1d calculation (line 91):
spy['return_1d'] = spy['close'].pct_change()
```

**Impact**:
- At entry decision time (market open day T), return_1d for day T is not yet known
- Using row['RV5'] includes return from T (today), which is future data
- This gives backtest perfect foresight about today's volatility when making entry decision
- May allow avoiding entries on days that spike intraday (disaster prevention we won't have live)

**Fix**:
Shift RV features back by 1 day:

```python
# Calculate features
spy['return_1d'] = spy['close'].pct_change()

# RV features use LAGGED returns (available at market open)
spy['RV5'] = spy['return_1d'].shift(1).rolling(5).std() * np.sqrt(252)
spy['RV10'] = spy['return_1d'].shift(1).rolling(10).std() * np.sqrt(252)
spy['RV20'] = spy['return_1d'].shift(1).rolling(20).std() * np.sqrt(252)

# OR: Use prior day close explicitly
spy['RV5_lag'] = spy['return_1d'].rolling(5).std().shift(1) * np.sqrt(252)

# Disaster filter
if row.get('RV5', 0) > 0.22:  # Now uses RV through yesterday, not today
    continue
```

**Verification**:
1. Manually check a high-vol day entry - does RV5 include that day's return?
2. Compare trade count before/after fix
3. Check if fix causes entries on disaster days that were previously filtered

---

### HIGH-003: Entry Condition Uses Same-Day Return Data
**Severity**: HIGH
**Location**: All scripts - Profile entry conditions
**Violation Type**: Look-ahead bias in entry signals

**Description**:
Multiple entry conditions use return_20d, return_10d, return_5d which include TODAY's return (day T) when making entry decision at market open on day T.

**Evidence**:
```python
# Profile_1_LDG entry (line 134)
'entry_condition': lambda row: row.get('return_20d', 0) > 0.02,

# Profile_2_SDG entry (line 146)
'entry_condition': lambda row: row.get('return_5d', 0) > 0.03,

# Profile_5_SKEW entry (line 182-184)
'entry_condition': lambda row: (
    row.get('return_10d', 0) < -0.02 and
    row.get('slope_MA20', 0) > 0.005
),

# But features calculated with pct_change (line 91-94):
spy['return_1d'] = spy['close'].pct_change()
spy['return_5d'] = spy['close'].pct_change(5)  # Includes today's close
spy['return_10d'] = spy['close'].pct_change(10)
spy['return_20d'] = spy['close'].pct_change(20)
```

**Impact**:
- At market open on day T, we don't know T's close price yet
- Entry conditions using return_5d/10d/20d have perfect foresight of today's return
- This allows entering AFTER knowing day will be good/bad
- Significantly inflates backtest performance vs live trading

**Fix**:
Shift all return features by 1 period OR use explicit lag:

```python
# OPTION 1: Shift all return features
spy['return_1d'] = spy['close'].pct_change().shift(1)  # Yesterday's return
spy['return_5d'] = spy['close'].pct_change(5).shift(1)  # 5-day return through yesterday
spy['return_10d'] = spy['close'].pct_change(10).shift(1)
spy['return_20d'] = spy['close'].pct_change(20).shift(1)

# OPTION 2: Explicit lagged calculations (clearer)
spy['close_lag1'] = spy['close'].shift(1)
spy['return_5d'] = (spy['close_lag1'] / spy['close'].shift(5) - 1)
spy['return_10d'] = (spy['close_lag1'] / spy['close'].shift(10) - 1)
spy['return_20d'] = (spy['close_lag1'] / spy['close'].shift(20) - 1)
```

**Verification**:
1. Check first trade entry - return_20d should NOT include entry day's close
2. Compare trade counts before/after - expect significant reduction
3. Compare Sharpe ratio - expect meaningful degradation (this bias is large)

---

### HIGH-004: ExitEngine Parameter Override Not Tested
**Severity**: HIGH
**Location**: src/trading/exit_engine.py
**Violation Type**: Untested critical path

**Description**:
The fix for BUG-008 added `custom_exit_days` parameter to ExitEngine constructor (line 36), but this code path is not tested and has potential bugs:

1. Instance attribute `self.exit_days` created from class constant (line 48)
2. Then updated with custom_exit_days (line 52)
3. But `should_exit()` uses `self.exit_days.get()` (line 80)
4. And `get_exit_day()` uses `self.exit_days.get()` (line 90)

The implementation LOOKS correct, but without tests, we can't verify that validation/test scripts actually use custom parameters instead of defaults.

**Evidence**:
```python
# Line 36: Parameter added
def __init__(self, phase: int = 1, custom_exit_days: Dict[str, int] = None):

# Lines 48-52: Instance override
self.exit_days = self.PROFILE_EXIT_DAYS.copy()
if custom_exit_days:
    self.exit_days.update(custom_exit_days)

# Line 80: Uses instance attribute (CORRECT)
exit_day = self.exit_days.get(profile, 14)
```

**Impact**:
- If override doesn't work, validation/test use wrong (default) exit days
- Would invalidate entire train/validation/test methodology
- Results would be meaningless for out-of-sample validation
- HIGH severity because this is MISSION CRITICAL for methodology

**Fix**:
Add unit test to verify custom_exit_days override works:

```python
# tests/test_exit_engine.py
def test_custom_exit_days_override():
    """Verify custom_exit_days parameter overrides defaults"""

    # Custom exit days (different from defaults)
    custom = {
        'Profile_1_LDG': 10,  # Default is 7
        'Profile_2_SDG': 8,   # Default is 5
    }

    engine = ExitEngine(phase=1, custom_exit_days=custom)

    # Verify overrides applied
    assert engine.get_exit_day('Profile_1_LDG') == 10
    assert engine.get_exit_day('Profile_2_SDG') == 8

    # Verify non-overridden profiles use defaults
    assert engine.get_exit_day('Profile_3_CHARM') == 3  # Default

    # Verify get_all_exit_days returns merged dict
    all_days = engine.get_all_exit_days()
    assert all_days['Profile_1_LDG'] == 10
    assert all_days['Profile_3_CHARM'] == 3
```

**Verification**:
1. Run unit test
2. Add debug print in validation script to show exit days used
3. Verify validation script output shows custom days, not defaults

---

### HIGH-005: Missing Transaction Costs in TradeTracker
**Severity**: HIGH
**Location**: src/analysis/trade_tracker.py lines 156-176
**Violation Type**: Incomplete execution model

**Description**:
TradeTracker calculates MTM P&L during trade path tracking but uses incomplete transaction cost model:

1. Uses fixed spread ($0.03) instead of ExecutionModel (lines 77, 169)
2. Uses fixed commission ($2.60) instead of per-contract model (line 76)
3. No OCC fees, FINRA fees, SEC fees (should be ~$0.10+/contract)
4. No size-based slippage
5. Different from ExecutionModel in execution.py

**Evidence**:
```python
# Lines 76-77: Fixed costs (WRONG)
commission = 2.60  # Per trade
spread = 0.03  # Per contract

# Line 169: Fixed spread application (WRONG)
exit_value = qty * (price - (spread if qty > 0 else -spread)) * 100

# Compare to ExecutionModel.get_commission_cost():
# - Base commission: $0.65/contract
# - OCC fees: $0.055/contract
# - FINRA fees: $0.00205/contract
# - SEC fees: variable
# = ~$0.71-0.75/contract minimum
```

**Impact**:
- Trade path P&L is overstated (missing ~$0.40/contract in fees)
- Peak timing analysis based on inflated P&L
- Exit day derivation contaminated by incorrect costs
- Train-derived parameters are wrong
- Creates false confidence in strategy profitability

**Fix**:
Use ExecutionModel for all cost calculations:

```python
# In TradeTracker.__init__:
def __init__(self, polygon_loader: PolygonOptionsLoader):
    self.polygon = polygon_loader
    self.execution_model = ExecutionModel()  # ADD THIS

# In track_trade():
# Entry costs
entry_cost = 0.0
for leg in position['legs']:
    opt_type = leg['type']
    qty = leg['qty']

    # Get execution price (includes spread)
    if qty > 0:
        price = self.polygon.get_option_price(..., 'ask')
    else:
        price = self.polygon.get_option_price(..., 'bid')

    leg_cost = qty * price * 100
    entry_cost += leg_cost

# Add commissions using ExecutionModel
num_contracts = sum(abs(leg['qty']) for leg in position['legs'])
entry_cost += self.execution_model.get_commission_cost(
    num_contracts,
    is_short=any(leg['qty'] < 0 for leg in position['legs']),
    premium=max(prices.values())  # Use max premium for SEC fee calc
)

# Exit costs (line 169)
mtm_value = 0.0
for leg in position['legs']:
    opt_type = leg['type']
    qty = leg['qty']

    mid_price = self.polygon.get_option_price(..., 'mid')

    # Apply execution model (not fixed spread)
    moneyness = abs(position['strike'] - day_spot) / day_spot
    dte_remaining = (position['expiry'] - day_date).days
    vix_proxy = day_row.get('RV20', 0.20) * 100 * 1.2

    exec_price = self.execution_model.get_execution_price(
        mid_price=mid_price,
        side='sell' if qty > 0 else 'buy',  # Closing position
        moneyness=moneyness,
        dte=dte_remaining,
        vix_level=vix_proxy,
        quantity=abs(qty)
    )

    exit_value = qty * exec_price * 100
    mtm_value += exit_value

# Add exit commissions
mtm_pnl = mtm_value - entry_cost - self.execution_model.get_commission_cost(...)
```

**Verification**:
1. Re-run train backtest with fixed costs
2. Compare peak timing before/after - should shift earlier (costs erode profits faster)
3. Verify total P&L drops significantly (10-20%+)

---

## MEDIUM Severity Issues

### MEDIUM-001: Expiry Calculation Bug for Year-End Dates
**Severity**: MEDIUM
**Location**: All scripts - get_expiry_for_dte() function
**Violation Type**: Edge case bug

**Description**:
The expiry calculation finds third Friday of target month, but for entries near year-end with DTE > 30, the target month could be next year. The calculation uses `target_date.year` and `target_date.month` which could cause incorrect expiry calculation across year boundaries.

**Evidence**:
```python
# Lines 208-215 (train script)
def get_expiry_for_dte(entry_date: date, dte_target: int) -> date:
    target_date = entry_date + timedelta(days=dte_target)
    first_day = date(target_date.year, target_date.month, 1)
    days_to_friday = (4 - first_day.weekday()) % 7
    first_friday = first_day + timedelta(days=days_to_friday)
    third_friday = first_friday + timedelta(days=14)
    return third_friday
```

**Impact**:
- For entry on Dec 15, 2020 with dte_target=75:
  - target_date = Feb 28, 2021
  - Calculates third Friday of Feb 2021 (correct)
- For entry on Dec 1, 2020 with dte_target=45:
  - target_date = Jan 15, 2021
  - Should work correctly
- Edge case: What if first_day calculation fails? (It shouldn't, but no error handling)

**Fix**:
Add validation and error handling:

```python
def get_expiry_for_dte(entry_date: date, dte_target: int) -> date:
    """Calculate appropriate expiry date for target DTE

    Returns third Friday of month that is ~dte_target days away
    """
    if dte_target < 0:
        raise ValueError(f"dte_target must be positive, got {dte_target}")

    target_date = entry_date + timedelta(days=dte_target)

    # Get first day of target month
    first_day = date(target_date.year, target_date.month, 1)

    # Calculate third Friday
    # Friday is weekday 4 (Monday=0)
    days_to_friday = (4 - first_day.weekday()) % 7
    first_friday = first_day + timedelta(days=days_to_friday)
    third_friday = first_friday + timedelta(days=14)

    # Validation: expiry should be after entry
    if third_friday <= entry_date:
        raise ValueError(
            f"Calculated expiry {third_friday} is before entry {entry_date}"
        )

    return third_friday
```

**Verification**:
1. Test with year-end dates: Dec 15, Dec 30, Dec 31
2. Test with DTE targets: 7, 30, 45, 60, 75, 120
3. Verify all expiries are in correct month and after entry date

---

### MEDIUM-002: Missing Validation of SPY Data Continuity
**Severity**: MEDIUM
**Location**: All scripts - load_spy_data() function
**Violation Type**: Data quality issue

**Description**:
The load_spy_data() function loads SPY data from parquet files but doesn't validate:
1. No gaps in dates (missing trading days)
2. No duplicate dates
3. Sufficient data loaded (minimum row count)
4. Features are monotonically reasonable (no 1000% returns)

**Evidence**:
```python
# Lines 59-75: Data loading with no validation
for f in spy_files:
    df = pd.read_parquet(f)
    if len(df) > 0:
        file_date = pd.to_datetime(df['ts'].iloc[0]).date()

        if file_date < TRAIN_START or file_date > TRAIN_END:
            continue

        spy_data.append({...})  # No validation of values

spy = pd.DataFrame(spy_data)  # No validation of completeness
```

**Impact**:
- Missing dates could cause trade tracking to fail silently
- Duplicate dates could cause incorrect feature calculations
- Bad data (price spikes, errors) could generate false signals
- Low severity because Polygon data is generally clean, but defense-in-depth missing

**Fix**:
Add data quality validation:

```python
def load_spy_data() -> pd.DataFrame:
    # ... existing loading code ...

    spy = pd.DataFrame(spy_data)

    # VALIDATION 1: Check date continuity
    spy = spy.sort_values('date').reset_index(drop=True)
    date_diffs = spy['date'].diff()

    # Trading days should be 1-4 days apart (allowing weekends/holidays)
    large_gaps = date_diffs[date_diffs > timedelta(days=5)]
    if len(large_gaps) > 0:
        print(f"⚠️  WARNING: Found {len(large_gaps)} gaps > 5 days in data:")
        for idx in large_gaps.index:
            print(f"   Gap at {spy.loc[idx, 'date']}: {date_diffs.loc[idx].days} days")

    # VALIDATION 2: Check for duplicates
    duplicates = spy['date'].duplicated()
    if duplicates.any():
        raise ValueError(f"Duplicate dates found: {spy[duplicates]['date'].values}")

    # VALIDATION 3: Check minimum data
    expected_trading_days = (TRAIN_END - TRAIN_START).days * 5/7  # ~252 days/year
    if len(spy) < expected_trading_days * 0.8:
        print(f"⚠️  WARNING: Expected ~{expected_trading_days:.0f} trading days, got {len(spy)}")

    # VALIDATION 4: Check for price anomalies
    daily_returns = spy['close'].pct_change()
    extreme_moves = daily_returns[abs(daily_returns) > 0.15]  # >15% daily move
    if len(extreme_moves) > 0:
        print(f"⚠️  WARNING: Found {len(extreme_moves)} days with >15% moves:")
        for idx in extreme_moves.index:
            print(f"   {spy.loc[idx, 'date']}: {extreme_moves.loc[idx]*100:.1f}%")

    # Calculate derived features
    # ... existing feature code ...

    return spy
```

**Verification**:
1. Run on train/validation/test periods
2. Check if any warnings appear
3. Manually verify a few dates have correct OHLCV data

---

### MEDIUM-003: No Logging of Entry Rejections
**Severity**: MEDIUM
**Location**: All scripts - run_profile_backtest() function
**Violation Type**: Debugging/transparency issue

**Description**:
The backtest loop silently skips entries when conditions aren't met (lines 250-263), making it impossible to debug why certain profiles have low trade counts or analyze near-miss opportunities.

**Evidence**:
```python
# Lines 250-263: Silent continues
if last_entry_date and (entry_date - last_entry_date).days < min_days_between_trades:
    continue  # No logging

try:
    if not config['entry_condition'](row):
        continue  # No logging
except Exception:
    continue  # No logging of exception!

if row.get('RV5', 0) > 0.22:
    continue  # No logging
```

**Impact**:
- Can't debug why profiles have 0 or few trades
- Can't analyze if entry conditions are too restrictive
- Can't see if disaster filter is triggering too often
- Exception in entry_condition silently caught (could hide bugs)

**Fix**:
Add rejection logging:

```python
def run_profile_backtest(...):
    # ...
    trades = []
    last_entry_date = None

    # REJECTION TRACKING
    rejection_stats = {
        'too_soon': 0,
        'entry_condition': 0,
        'disaster_filter': 0,
        'exception': 0
    }

    for idx in range(60, len(spy)):
        row = spy.iloc[idx]
        entry_date = row['date']

        # Check if enough time since last trade
        if last_entry_date and (entry_date - last_entry_date).days < min_days_between_trades:
            rejection_stats['too_soon'] += 1
            continue

        # Check entry condition
        try:
            if not config['entry_condition'](row):
                rejection_stats['entry_condition'] += 1
                continue
        except Exception as e:
            rejection_stats['exception'] += 1
            print(f"⚠️  Entry condition exception on {entry_date}: {e}")
            continue

        # DISASTER FILTER
        if row.get('RV5', 0) > 0.22:
            rejection_stats['disaster_filter'] += 1
            continue

        # Entry triggered
        # ...

    # Print rejection summary
    print(f"✅ Completed: {len(trades)} trades")
    print(f"   Rejections: {sum(rejection_stats.values())} total")
    print(f"   - Too soon: {rejection_stats['too_soon']}")
    print(f"   - Entry condition: {rejection_stats['entry_condition']}")
    print(f"   - Disaster filter: {rejection_stats['disaster_filter']}")
    print(f"   - Exceptions: {rejection_stats['exception']}\n")

    return trades
```

**Verification**:
1. Run backtest and check console output
2. Verify rejection counts make sense
3. Check if any exceptions are caught (indicates bug in entry condition)

---

## LOW Severity Issues

### LOW-001: Hardcoded Path in sys.path.append
**Severity**: LOW
**Location**: All scripts, line 29
**Violation Type**: Portability issue

**Description**:
All scripts use hardcoded absolute path: `sys.path.append('/Users/zstoc/rotation-engine')` which will break if project is moved or run by another user.

**Evidence**:
```python
# Line 29 (all scripts)
sys.path.append('/Users/zstoc/rotation-engine')
```

**Impact**:
- Scripts fail if project moved to different directory
- Scripts fail if run by different user
- Can't run from different working directory
- Low severity because this is solo project, but bad practice

**Fix**:
Use relative path from script location:

```python
import sys
from pathlib import Path

# Add project root to path (scripts/ is subdirectory)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
```

**Verification**:
1. Move project to different directory
2. Run scripts - should still work

---

### LOW-002: Magic Numbers in Entry Conditions
**Severity**: LOW
**Location**: All scripts - get_profile_configs()
**Violation Type**: Maintainability issue

**Description**:
Entry conditions use magic numbers (0.02, 0.03, 0.22, etc.) without explanation or named constants.

**Evidence**:
```python
# Profile_1_LDG
'entry_condition': lambda row: row.get('return_20d', 0) > 0.02,  # Why 0.02?

# Profile_2_SDG
'entry_condition': lambda row: row.get('return_5d', 0) > 0.03,  # Why 0.03?

# Disaster filter
if row.get('RV5', 0) > 0.22:  # Why 0.22?
```

**Impact**:
- Hard to understand rationale for thresholds
- Hard to adjust for sensitivity testing
- Hard to ensure consistency across scripts
- Low severity because values are working, just unclear

**Fix**:
Use named constants:

```python
# At top of script
ENTRY_THRESHOLDS = {
    'return_5d_momentum': 0.03,   # 3% 5-day return for momentum trades
    'return_10d_dip': -0.02,      # -2% 10-day for dip-buying
    'return_20d_trend': 0.02,     # 2% 20-day for trend following
    'disaster_rv5': 0.22,         # 22% annualized RV5 = disaster mode
    'min_days_between': 7         # Minimum days between trades
}

# In profile configs:
'entry_condition': lambda row: row.get('return_20d', 0) > ENTRY_THRESHOLDS['return_20d_trend'],
```

**Verification**:
1. Scripts still run
2. Easier to adjust thresholds for sensitivity testing

---

### LOW-003: Missing Type Hints
**Severity**: LOW
**Location**: All functions
**Violation Type**: Code quality issue

**Description**:
Functions lack type hints, making it harder to catch type errors and understand interfaces.

**Evidence**:
```python
# Missing return type hint
def get_profile_configs() -> Dict:  # Dict of what?

# Missing parameter types
def run_profile_backtest(profile_id, config, spy, tracker, exit_engine, min_days_between_trades=7):
```

**Impact**:
- Type errors not caught by static analysis
- Harder to understand function interfaces
- No IDE autocomplete for return values
- Low severity because code is working

**Fix**:
Add comprehensive type hints:

```python
from typing import Dict, List, Callable

def get_profile_configs() -> Dict[str, Dict]:
    """Returns dict mapping profile_id -> config dict"""

def run_profile_backtest(
    profile_id: str,
    config: Dict,
    spy: pd.DataFrame,
    tracker: TradeTracker,
    exit_engine: ExitEngine,
    min_days_between_trades: int = 7
) -> List[Dict]:
```

**Verification**:
1. Run mypy for static type checking
2. Verify IDE autocomplete works better

---

### LOW-004: Inconsistent String Formatting
**Severity**: LOW
**Location**: All scripts
**Violation Type**: Code style issue

**Description**:
Mix of f-strings, format(), and % formatting throughout scripts.

**Evidence**:
```python
# Line 113: % formatting
print(f"Loaded {len(spy)} days from {spy['date'].min()} to {spy['date'].max()}\n")

# Line 83: f-string (inconsistent style)
print(f"✅ TRAIN PERIOD ENFORCED")
```

**Impact**:
- Style inconsistency
- Harder to read
- Very low severity - cosmetic issue

**Fix**:
Standardize on f-strings (most modern):

```python
# Use f-strings everywhere
print(f"Loaded {len(spy)} days from {spy['date'].min()} to {spy['date'].max()}")
```

**Verification**:
Visual inspection

---

## Walk-Forward Integrity Assessment

**Data Separation**: FAIL
- CRITICAL-001: Train period doesn't use train-derived parameters (circular logic)
- CRITICAL-002: Features calculated within period boundaries (temporal violation)
- HIGH-003: Entry conditions use same-day data (look-ahead bias)

**Out-of-Sample Testing**: COMPROMISED
- Train/validation/test periods properly separated (GOOD)
- But train results invalid due to CRITICAL-001 (BAD)
- Validation will use different parameters than train tested (BAD)
- Test holdout concept is correct but execution is flawed (BAD)

**Parameter Stability**: UNKNOWN
- Cannot assess until CRITICAL-001 fixed
- Need to compare phase1 (default params) vs phase2 (optimized params) results
- Need sensitivity analysis: ±1 day on exit timing

**Overfitting Risk**: HIGH
- Deriving parameters from same backtest that will report performance (CRITICAL-001)
- No cross-validation within train period
- No parameter sensitivity testing
- Single optimization pass without robustness checks

---

## Recommendations

### Priority 1 - CRITICAL Fixes (Block Deployment)

1. **Fix CRITICAL-001**: Implement two-phase train process
   - Phase 1: Run with defaults to derive optimal exit days
   - Phase 2: Re-run with derived exit days to get ACTUAL train performance
   - Validate phase2 uses same exit days as validation/test

2. **Fix CRITICAL-002**: Load continuous data for feature calculation
   - Load 60-day warmup before period start
   - Calculate features on full dataset
   - Filter to period AFTER features calculated
   - Verify first 60 rows have no NaN features

3. **Fix HIGH-003**: Shift all return features by 1 period
   - Entry conditions must use only data available at market open
   - return_5d/10d/20d should end at yesterday's close, not today's

### Priority 2 - HIGH Fixes (Required Before Validation)

4. **Fix HIGH-001**: Implement OTM strike calculation for Profile_5_SKEW
5. **Fix HIGH-002**: Shift RV features by 1 period for disaster filter
6. **Fix HIGH-004**: Add unit tests for ExitEngine custom_exit_days
7. **Fix HIGH-005**: Replace fixed costs in TradeTracker with ExecutionModel

### Priority 3 - MEDIUM Improvements (Strongly Recommended)

8. **Fix MEDIUM-001**: Add validation to expiry calculation
9. **Fix MEDIUM-002**: Add data quality validation to load_spy_data()
10. **Fix MEDIUM-003**: Add rejection logging to understand trade counts

### Priority 4 - LOW Cleanup (Nice to Have)

11. **Fix LOW-001**: Use relative imports instead of hardcoded paths
12. **Fix LOW-002**: Extract magic numbers to named constants
13. **Fix LOW-003**: Add comprehensive type hints
14. **Fix LOW-004**: Standardize on f-string formatting

### Additional Validation Steps Needed

After fixing CRITICAL and HIGH issues:

1. **Parameter Sensitivity Testing**:
   - Test exit days ±1, ±2 from optimal
   - Verify results degrade smoothly (not cliff edge)
   - Check if multiple peaks in sensitivity curve (sign of overfitting)

2. **Cross-Validation Within Train**:
   - Split train into 2020 and 2021
   - Derive parameters from 2020, test on 2021
   - Check consistency with full train results

3. **Statistical Significance Testing**:
   - Bootstrap confidence intervals on Sharpe ratio
   - Permutation tests on strategy returns
   - Multiple testing correction (6 profiles × multiple metrics)

4. **Transaction Cost Sensitivity**:
   - Test with spreads 2x, 3x higher
   - Test with commissions 2x higher
   - Verify strategy still profitable under stress

---

## Certification

- [ ] **CRITICAL-001 must be fixed** - Train methodology is fundamentally broken
- [ ] **CRITICAL-002 must be fixed** - Feature calculation creates temporal violations
- [ ] All HIGH issues must be fixed before validation period
- [ ] Walk-forward validation must be re-run after fixes
- [ ] Current backtest results are INVALID and cannot be deployed

---

## Final Verdict

**STATUS**: BLOCK DEPLOYMENT

**Reason**: Two critical methodology violations that invalidate all current results:

1. Train period doesn't use train-derived parameters (circular logic)
2. Features calculated within period boundaries (look-ahead bias)

**Action Required**: Fix all CRITICAL and HIGH issues, then re-run entire train/validation/test sequence from scratch.

**Estimated Rework**: 4-8 hours to fix issues + 2-4 hours to re-run full backtest suite

**Next Steps**:
1. Fix CRITICAL-001 (two-phase train process)
2. Fix CRITICAL-002 (continuous feature calculation)
3. Fix HIGH-003 (shift return features)
4. Fix HIGH-005 (ExecutionModel in TradeTracker)
5. Re-run train period with fixes
6. Review train results before proceeding to validation
7. If train results acceptable, run validation period
8. Compare degradation metrics (expect 20-40% degradation)
9. If validation passes, lock methodology
10. Run test period ONCE

**DO NOT proceed to validation/test until train methodology is fixed and validated.**
