# Rotation Engine - Technical Audit Details
## Look-Ahead Bias Analysis - Deep Dive

---

## 1. WALK-FORWARD PERCENTILE IMPLEMENTATION

### Location: `/Users/zstoc/rotation-engine/src/regimes/signals.py:99-130`

```python
def _compute_walk_forward_percentile(self, series: pd.Series, window: int) -> pd.Series:
    """Compute percentile rank walk-forward (no look-ahead)."""
    result = pd.Series(index=series.index, dtype=float)

    for i in range(len(series)):
        if i < window:
            lookback = series.iloc[:i]           # When history is short, use all available past
        else:
            lookback = series.iloc[i-window:i]   # KEY: [:i] EXCLUDES current point

        if len(lookback) == 0:
            result.iloc[i] = 0.5                 # Default when no history
        else:
            current_val = series.iloc[i]
            pct = (lookback < current_val).sum() / len(lookback)  # Compare to PAST only
            result.iloc[i] = pct

    return result
```

### Why This Is Correct

**The Critical Line**: `series.iloc[i-window:i]`

In pandas/numpy slicing:
- `series.iloc[i-window:i]` returns elements from index `i-window` to `i-1` (excludes `i`)
- This means at each timestep `i`, only PAST data is used
- Current value at `i` is only used for the comparison, not for computing percentile

### Mathematical Verification

Given timeseries: `[10, 20, 15, 25, 30, 22]` with window=3

| i | Current | lookback | Calculation | Result |
|---|---------|----------|------------|--------|
| 0 | 10 | [] | No past data | 0.5 |
| 1 | 20 | [10] | 20 > 10 → 1/1 | 1.0 |
| 2 | 15 | [10, 20] | 15 > 10, 15 ≤ 20 → 1/2 | 0.5 |
| 3 | 25 | [10, 20, 15] | 25 > all → 3/3 | 1.0 |
| 4 | 30 | [20, 15, 25] | 30 > all → 3/3 | 1.0 |
| 5 | 22 | [15, 25, 30] | 22 > 15, 22 < 25,30 → 1/3 | 0.33 |

**All calculations use past data only. ✅ NO FUTURE LEAKAGE**

### Use Cases in Code

This function is used for:
1. **RV20 Percentile** (regime/signals.py:55)
   ```python
   df['RV20_percentile'] = self._compute_walk_forward_percentile(df['RV20'], window=60)
   ```
   At each day, RV20 is ranked against the past 60 days only.

2. **ATR Rank** (regime/signals.py:73)
   ```python
   df['ATR10_rank'] = self._compute_walk_forward_percentile(df['ATR10'], window=60)
   ```
   Same principle - ranks current ATR against past 60 days.

---

## 2. ROLLING PERCENTILE WITH PANDAS

### Location: `/Users/zstoc/rotation-engine/src/profiles/features.py:184-208`

```python
def _rolling_percentile(self, series: pd.Series, window: int) -> pd.Series:
    """Compute rolling percentile rank (walk-forward)."""

    def percentile_rank(x):
        """Rank current value vs past values."""
        if len(x) < 2:
            return 0.5
        past = x[:-1]           # EXCLUDE last element (current point)
        current = x[-1]         # Last element (current point)
        return (past < current).sum() / len(past)

    return series.rolling(window=window, min_periods=10).apply(
        percentile_rank, raw=True  # raw=True: receive numpy array
    )
```

### How Pandas Rolling.apply() Works

When you call `series.rolling(window=3).apply(func, raw=True)`:

**Example with data [1, 2, 3, 4, 5, 6, 7]**:

| Position | Window Passed to func | x array | past (x[:-1]) | current (x[-1]) | Result |
|----------|----------------------|---------|---------------|-----------------|--------|
| 0 | NaN | N/A | N/A | N/A | NaN |
| 1 | NaN | N/A | N/A | N/A | NaN |
| 2 | [1, 2, 3] | [1, 2, 3] | [1, 2] | 3 | (1<3)+(2<3) / 2 = 1.0 |
| 3 | [2, 3, 4] | [2, 3, 4] | [2, 3] | 4 | (2<4)+(3<4) / 2 = 1.0 |
| 4 | [3, 4, 5] | [3, 4, 5] | [3, 4] | 5 | (3<5)+(4<5) / 2 = 1.0 |
| 5 | [4, 5, 6] | [4, 5, 6] | [4, 5] | 6 | (4<6)+(5<6) / 2 = 1.0 |
| 6 | [5, 6, 7] | [5, 6, 7] | [5, 6] | 7 | (5<7)+(6<7) / 2 = 1.0 |

### Why This Avoids Look-Ahead Bias

Key insight: **`x[:-1]` explicitly removes the current element from the lookback**

This technique is fundamentally different from:
```python
# WRONG - Would include current in calculation:
def wrong_percentile(x):
    current = x[-1]
    return (x < current).sum() / len(x)  # Includes current in denominator!
```

The code correctly implements walk-forward by:
1. Receiving a window of data [past, past, past, current]
2. Separating: past = [past, past, past], current = current
3. Computing: current's rank only vs past
4. Result: No future data leakage

---

## 3. PANDAS ROLLING WINDOW SEMANTICS

### Key Insight: Rolling Windows Are Causal

**Location**: `/Users/zstoc/rotation-engine/src/data/features.py:22-42`

```python
def compute_realized_vol(df: pd.DataFrame, windows: list = [5, 10, 20]) -> pd.DataFrame:
    df = df.copy()
    for window in windows:
        rv = df['return'].rolling(window).std() * np.sqrt(252)
        df[f'RV{window}'] = rv
    return df
```

### How Pandas rolling() Indexing Works

**Data**: close prices [100, 101, 100.5, 102, 103, 102, 101, 104, 105, 106]

**Computation: df['close'].rolling(5).mean()**

| Index | Close | Window Data | rolling(5).mean() |
|-------|-------|-------------|-------------------|
| 0 | 100 | NaN | NaN |
| 1 | 101 | NaN | NaN |
| 2 | 100.5 | NaN | NaN |
| 3 | 102 | NaN | NaN |
| 4 | 103 | [100, 101, 100.5, 102, 103] | 101.3 |
| 5 | 102 | [101, 100.5, 102, 103, 102] | 101.7 |
| 6 | 101 | [100.5, 102, 103, 102, 101] | 101.7 |
| 7 | 104 | [102, 103, 102, 101, 104] | 102.4 |
| 8 | 105 | [103, 102, 101, 104, 105] | 103.0 |
| 9 | 106 | [102, 101, 104, 105, 106] | 103.6 |

### Critical Point

At position 4:
- rolling(5).mean() uses **data indices 0-4** (includes current 4, uses past 0-3)
- Does NOT use index 5 data (which would be future)
- At trading time t, only data through t is available
- Therefore, this is **causal and walk-forward compliant**

### Non-Negative Shift Only

The code uses:
```python
df['return'] = np.log(df['close'] / df['close'].shift(1))  # ✓ shift(1) = PAST
```

NOT:
```python
df['return'] = np.log(df['close'] / df['close'].shift(-1))  # ✗ shift(-1) = FUTURE
```

**Search result**: No `.shift(-N)` patterns found in codebase ✅

---

## 4. REGIME CLASSIFICATION FLOW

### Complete Data Flow for Regime Label

```
Engine loads full data
    ↓
engine.run() → load_spy_data()
    ↓
DataSpine.build_spine() computes features
    ↓
All features computed with rolling/walk-forward logic ✓
    ↓
RegimeClassifier.classify_period(df)
    ↓
RegimeSignals.compute_all_signals(df)
    ✓ RV20_percentile: walk-forward percentile
    ✓ ATR10_rank: walk-forward percentile
    ✓ VVIX: rolling stdev (causal)
    ✓ skew_z: z-score vs rolling mean/std
    ✓ RSI: rolling average of gains/losses
    ↓
RegimeClassifier._classify_row() applies rules
    ↓
regime_label column populated ✓
```

### Regime Rules Examined

**File**: `/Users/zstoc/rotation-engine/src/regimes/classifier.py:102-217`

Example: `_is_trend_up()` at line 147:
```python
def _is_trend_up(self, row: pd.Series) -> bool:
    return (
        row['return_20d'] > 0.02 and              # Past 20-day return > +2%
        row['price_to_MA20'] > 0 and              # Price > MA20 (same-day)
        row['price_to_MA50'] > 0 and              # Price > MA50 (same-day)
        row['slope_MA20'] > 0 and                 # MA slope (past 5 days)
        row['RV20_rank'] < self.rv_rank_mid_low   # RV rank (walk-forward %)
    )
```

**All components are walk-forward**:
- `return_20d`: Uses past 20 days of returns (no future data)
- `price_to_MA20`: Uses current price vs MA20 (MA20 itself uses past data only)
- `RV20_rank`: Walk-forward percentile (verified above)

---

## 5. BACKTEST LOOP TIMING

### Location: `/Users/zstoc/rotation-engine/src/trading/simulator.py:136-267`

```python
for idx, row in self.data.iterrows():
    date = row['date']
    spot = row['close']

    # 1. Check for EXIT
    if current_trade is not None and current_trade.is_open:
        # Exit signals from current row
        if exit_logic is not None and exit_logic(row, current_trade):
            # Exit using TODAY's prices
            exit_prices = self._get_exit_prices(current_trade, row)

    # 2. Check for ENTRY
    if current_trade is None and entry_logic(row, current_trade):
        # Enter using TODAY's prices
        entry_prices = self._get_entry_prices(current_trade, row)
```

### Temporal Correctness

**Entry Decision**: At date T
- Access: row with date T, close T, regime_label T, profile_score T
- All T-values computed with data ≤ T (no future)
- Entry price: Today's ask (if long) or bid (if short)
- Entry cost calculated immediately

**Exit Decision**: At date T
- Access: same row data as entry
- Compare current_trade entered at T-N
- Calculate mark-to-market at T prices
- Exit price: Today's bid (if long) or ask (if short)

**No Look-Ahead**: ✓ All decisions made with current-date info only

---

## 6. FEATURE ENGINEERING AUDIT

### Return Calculations

**Location**: `/Users/zstoc/rotation-engine/src/data/features.py:137-139`

```python
df['return_5d'] = df['close'] / df['close'].shift(5) - 1.0   # ✓ Past 5 days
df['return_10d'] = df['close'] / df['close'].shift(10) - 1.0  # ✓ Past 10 days
df['return_20d'] = df['close'] / df['close'].shift(20) - 1.0  # ✓ Past 20 days
```

Uses `.shift()` with POSITIVE values = uses PAST data ✅

### Moving Averages

**Location**: `/Users/zstoc/rotation-engine/src/data/features.py:89-90`

```python
df['MA20'] = df['close'].rolling(20).mean()   # ✓ Causal rolling window
df['MA50'] = df['close'].rolling(50).mean()   # ✓ Causal rolling window
```

Pandas rolling includes current bar but no future ✅

### Slopes

**Location**: `/Users/zstoc/rotation-engine/src/data/features.py:112-113`

```python
ma_prev = df[col].shift(lookback)             # lookback=5, so PAST MA value
slope = (df[col] - ma_prev) / ma_prev         # Current MA vs 5-days-ago MA
```

Slope calculated vs past value ✅

### ATR (Average True Range)

**Location**: `/Users/zstoc/rotation-engine/src/data/features.py:62-71`

```python
prev_close = df['close'].shift(1)             # Yesterday's close
tr1 = df['high'] - df['low']                  # Today's range
tr2 = abs(df['high'] - prev_close)            # Today's high vs yesterday's close
tr3 = abs(df['low'] - prev_close)             # Today's low vs yesterday's close

tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
df['ATR{window}'] = df['TR'].rolling(window).mean()
```

All components use past or current data only ✅

---

## 7. EXECUTION MODEL REALISM

### Location: `/Users/zstoc/rotation-engine/src/trading/execution.py`

**Spread Model** (lines 60-114):
```python
def get_spread(self, mid_price, moneyness, dte, vix_level=20.0, is_strangle=False):
    base = self.base_spread_otm if is_strangle else self.base_spread_atm
    moneyness_factor = 1.0 + moneyness * 2.0    # Wider for OTM
    dte_factor = 1.3 if dte < 7 else 1.15 if dte < 14 else 1.0  # Tighter for longer DTE
    vol_factor = 1.5 if vix_level > 30 else 1.2 if vix_level > 25 else 1.0
    spread = base * moneyness_factor * dte_factor * vol_factor
    min_spread = mid_price * 0.05  # At least 5% of mid
    return max(spread, min_spread)
```

**Realistic adjustments**:
- ✓ Spreads widen for OTM options
- ✓ Spreads widen for short DTE
- ✓ Spreads widen in high volatility
- ✓ Minimum floor to prevent unrealistic tightness

**Entry/Exit Pricing** (lines 116-161):
```python
if side == 'buy':
    return mid_price + half_spread + slippage  # Pay ask (realistic)
elif side == 'sell':
    return max(0.01, mid_price - half_spread - slippage)  # Receive bid (realistic)
```

Correctly uses:
- ✓ Ask for entries on long positions
- ✓ Bid for entries on short positions
- ✓ Reverses for exits

**Commissions**:
- ✓ $0.65 per contract
- ✓ SEC fees for shorts ($0.00182 per contract)
- ✓ ES futures hedging costs

**Verdict**: Execution model is realistic and properly implemented ✅

---

## 8. EDGE CASES & BOUNDARY CONDITIONS

### First Rows (Insufficient History)

**Percentile calculation at i=0, window=60**:
```python
if i < window:
    lookback = series.iloc[:i]  # Empty series
# ...
if len(lookback) == 0:
    result.iloc[i] = 0.5  # Default to middle
```

Result: Defaults to 0.5 (neutral percentile) ✅
- Not an error
- Prevents lookback bias
- After 60 bars, proper percentiles calculated

### Last Row (End of Data)

**Backtest ends at simulator.py:268-281**:
```python
if current_trade is not None and current_trade.is_open:
    final_row = self.data.iloc[-1]
    exit_prices = self._get_exit_prices(current_trade, final_row)
    current_trade.close(final_row['date'], exit_prices, "End of backtest")
```

Result: Open trades closed at final day's prices ✅
- Realistic exit
- No forward-looking

---

## 9. SUMMARY TABLE

| Component | Location | Type | Status | Notes |
|-----------|----------|------|--------|-------|
| Walk-forward percentile | regimes/signals.py:99-130 | Core | ✅ PASS | Excludes current bar explicitly |
| Rolling percentile | profiles/features.py:184-208 | Core | ✅ PASS | Uses x[:-1] to exclude current |
| Rolling RV | data/features.py:39 | Feature | ✅ PASS | Causal window |
| Moving averages | data/features.py:90 | Feature | ✅ PASS | Causal window |
| Return calculations | data/features.py:137 | Feature | ✅ PASS | Uses shift(n) for past |
| Regime classification | regimes/classifier.py | Signal | ✅ PASS | Walk-forward signals only |
| Backtest loop | trading/simulator.py:136 | Execution | ✅ PASS | Chronological, causal |
| Entry/exit pricing | trading/execution.py | Execution | ✅ PASS | Realistic model |
| Commission model | trading/execution.py | Cost | ✅ PASS | Realistic costs |

---

## 10. WHAT THIS CODE GOT RIGHT

1. **Understanding of percentile calculations**: Developers knew to exclude current bar
2. **Proper use of pandas semantics**: Leveraged built-in causal properties
3. **Temporal discipline**: No negative shifts, no future indexing
4. **Realistic execution**: Bid-ask spreads, commissions, slippage
5. **Robust defaults**: Handles early data gracefully
6. **Clear naming**: Code is readable and intent is obvious
7. **Modular design**: Separation of concerns makes auditing easier

---

## Conclusion

**This codebase demonstrates strong quantitative discipline.**

The developers understood the requirements for walk-forward, causality-respecting backtests and implemented them correctly throughout. The code is production-ready from a look-ahead bias perspective.

No critical issues found. ✅

