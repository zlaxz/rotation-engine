# BUG-CRIT-001: Regime Classifier Look-Ahead Bias

**Severity:** 🔴 CRITICAL
**Component:** Regime Classifier
**File:** `src/regimes/signals.py`
**Lines:** 99-130
**Found By:** Agent #2 (DeepSeek Reasoner)
**Status:** 🔴 UNFIXED

---

## Description

The `_compute_walk_forward_percentile` function has fundamental look-ahead bias that uses future information in regime classification. This invalidates ALL backtest results.

## The Bug

```python
def _compute_walk_forward_percentile(self, series: pd.Series, window: int) -> pd.Series:
    result = pd.Series(index=series.index, dtype=float)
    for i in range(len(series)):
        if i < window:
            lookback = series.iloc[:i]  # ← BUG: Includes current point when i=0
        else:
            lookback = series.iloc[i-window:i]  # ← Correct: excludes current

        if len(lookback) == 0:
            result.iloc[i] = 0.5
        else:
            current_val = series.iloc[i]  # ← BUG: Uses CURRENT value (future data!)
            pct = (lookback < current_val).sum() / len(lookback)
            result.iloc[i] = pct
    return result
```

**Problem:** At time `i`, we compare `series.iloc[i]` (current/future value) against historical data. This means we're using information that wouldn't be available at decision time.

## Impact

- **Regime detection uses future data** = All regime labels invalid
- **Backtest results are inflated** = False edge from look-ahead bias
- **Strategy will fail live trading** = Edge disappears with real-time data
- **All prior backtest results must be discarded**

## Root Cause

The function is designed to compute a percentile rank, but it includes the current value in the comparison. In walk-forward analysis, at time `t`, you only know values up to `t-1`.

## The Fix

```python
def _compute_walk_forward_percentile(self, series: pd.Series, window: int) -> pd.Series:
    """
    Compute percentile rank walk-forward (no look-ahead).

    At time t, we compute where the PREVIOUS value (t-1) ranks
    relative to history (t-window to t-2).
    """
    result = pd.Series(index=series.index, dtype=float)

    for i in range(1, len(series)):  # Start from 1, not 0
        if i <= window:
            # Use all history up to i-1
            lookback = series.iloc[:i]
        else:
            # Use window of history ending at i-1
            lookback = series.iloc[i-window:i]

        if len(lookback) < 2:
            # Need at least 2 points for meaningful percentile
            result.iloc[i] = 0.5
        else:
            # Compare most recent PAST value against earlier history
            recent_val = lookback.iloc[-1]  # Value at i-1
            historical = lookback.iloc[:-1]  # Values from i-window to i-2

            if len(historical) == 0:
                result.iloc[i] = 0.5
            else:
                pct = (historical < recent_val).sum() / len(historical)
                result.iloc[i] = pct

    result.iloc[0] = 0.5  # Handle first element
    return result
```

## Secondary Issues

**Related functions also have look-ahead bias:**

1. **vol_of_vol calculation (Line 59-63):**
```python
# WRONG
df['vol_of_vol'] = df['RV10'].rolling(window=20).std()

# CORRECT
df['vol_of_vol'] = df['RV10'].shift(1).rolling(window=20).std()
```

2. **Slope calculation (Line 66-70):**
```python
# WRONG
df['slope_MA20'] = df['MA20'].rolling(window=5).apply(self._linear_slope)

# CORRECT
df['slope_MA20'] = df['MA20'].shift(1).rolling(window=5).apply(self._linear_slope)
```

## Validation

After fixing, verify:
1. ✅ Backtest results change significantly (proves fix worked)
2. ✅ No future data used in any calculation (manual code review)
3. ✅ Unit test: regime at time t depends only on data ≤ t-1
4. ✅ Walk-forward test: train/test split shows more realistic degradation

## Files to Fix

- [ ] `src/regimes/signals.py:99-130` - Main fix
- [ ] `src/regimes/signals.py:59-63` - vol_of_vol
- [ ] `src/regimes/signals.py:66-70` - slope calculation
- [ ] Add unit tests: `tests/test_regime_signals.py`

## Priority

**HIGHEST PRIORITY - BLOCKS ALL OTHER WORK**

Cannot proceed with ANY backtesting until this is fixed. All prior results are invalid.
