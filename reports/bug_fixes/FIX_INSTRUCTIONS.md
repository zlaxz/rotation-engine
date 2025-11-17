# FIX INSTRUCTIONS - CRITICAL BUG #1
**Generated:** 2025-11-13
**Priority:** BLOCKING - Must fix before any deployment

---

## BUG #1: SLOPE CALCULATION INCONSISTENCY

### Current State (BROKEN):

**File: `src/data/features.py` lines 108-116**
```python
def compute_slope(df: pd.DataFrame, lookback: int = 5) -> pd.DataFrame:
    """Compute MA slopes."""
    df = df.copy()

    for col in ['MA20', 'MA50']:
        if col in df.columns:
            ma_prev = df[col].shift(lookback)
            slope = (df[col] - ma_prev) / ma_prev  # ❌ PERCENTAGE CHANGE
            df[f'slope_{col}'] = slope

    return df
```

This calculates **5-day percentage change**, NOT slope.

**File: `src/regimes/signals.py` lines 73-78**
```python
# Vol-of-vol slope (is vol-of-vol rising or falling?)
df['vol_of_vol_slope'] = (
    df['vol_of_vol']
    .rolling(window=5, min_periods=3)
    .apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) >= 2 else 0, raw=False)  # ✅ LINEAR REGRESSION
)
```

This calculates **linear regression slope**.

**Inconsistent!**

---

## RECOMMENDED FIX: OPTION 1 (Linear Regression)

### Step 1: Fix `src/data/features.py`

Replace lines 96-116 with:

```python
def compute_slope(df: pd.DataFrame, lookback: int = 5) -> pd.DataFrame:
    """
    Compute MA slopes using linear regression.

    For each point, fits a line through past `lookback` days and returns slope.
    Walk-forward compliant (only uses past data).

    Args:
        df: DataFrame with MA columns
        lookback: Days to look back for slope calculation (default 5)

    Returns:
        DataFrame with slope_MA20, slope_MA50 columns (in price units per day)
    """
    df = df.copy()

    for col in ['MA20', 'MA50']:
        if col in df.columns:
            # Linear regression slope over rolling window
            slope = (
                df[col]
                .rolling(window=lookback, min_periods=max(2, lookback-2))
                .apply(
                    lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) >= 2 else 0,
                    raw=False
                )
            )
            df[f'slope_{col}'] = slope

    return df
```

### Step 2: Fix Thresholds (MAYBE NEEDED)

The current thresholds may work with linear regression. Test first.

**In `src/regimes/classifier.py`:**
- Line 160: `row['slope_MA20'] > 0` - **OK (just positive)**
- Line 177: `row['slope_MA20'] < 0` - **OK (just negative)**
- Line 192: `abs(row['slope_MA20']) < 0.005` - **TEST THIS**

**Testing required:**
```python
# After fix, check typical slope magnitudes
df['slope_MA20'].describe()
```

If typical slopes are ~0.5-2.0, then threshold of 0.005 is too tight.
Adjust to something like `abs(slope) < 0.1` (10 cents/day is "flat").

**In `src/profiles/detectors.py`:**
- Line 91: `sigmoid(df['slope_MA20'] * 100)` - **ADJUST SCALING**
- Line 185: `sigmoid(df['slope_MA20'] * 100)` - **ADJUST SCALING**

After fix, test what `slope_MA20 * 100` looks like:
```python
# Typical range after fix
(df['slope_MA20'] * 100).describe()
```

If typical values are 10-100, sigmoid will saturate. May need to change to:
```python
sigmoid(df['slope_MA20'] * 1000)  # More aggressive scaling
# OR
sigmoid(df['slope_MA20'] / df['close'].mean())  # Normalize by price
```

**Action:** Fix the calculation first, then run validation to see if thresholds need adjustment.

---

## ALTERNATIVE FIX: OPTION 2 (Percentage Change)

### Step 1: Fix `src/regimes/signals.py`

Replace lines 73-78 with:

```python
# Vol-of-vol slope (5-day percentage change)
df['vol_of_vol_slope'] = (df['vol_of_vol'] - df['vol_of_vol'].shift(5)) / df['vol_of_vol'].shift(5)
```

### Step 2: Adjust ALL Sigmoid Scalings

**Problem:** Percentage changes are typically -10% to +10% (-0.1 to +0.1).
Linear regression slopes for SPY MA20 are typically -5 to +5 (dollars/day).

**Current code assumes larger magnitudes:**
```python
sigmoid(df['slope_MA20'] * 100)  # Assumes slope ~ 0.01 → scaled to 1.0
```

With percentage change, slope ~ 0.01 means 1% over 5 days (reasonable).
Scaling by 100 → sigmoid(1.0) = 0.73 (OK).

**Verdict:** Percentage change method MIGHT work with current scaling.

But inconsistency still exists with vol_of_vol_slope.

---

## RECOMMENDED CHOICE: OPTION 1 (Linear Regression)

**Why:**
1. More common in quant finance (measures trend direction)
2. Already used for vol_of_vol_slope
3. More interpretable (dollars per day)
4. Better for detecting trend changes (fits all points, not just endpoints)

**Why NOT percentage change:**
1. Ignores intermediate data (just start vs end)
2. Less sensitive to trend changes mid-window
3. Harder to set universal thresholds

---

## VERIFICATION AFTER FIX

### Step 1: Re-run Red Team Audit
```bash
cd /Users/zstoc/rotation-engine
python3 red_team_audit.py
```

Expected output:
```
✅ PASS: Slope calculation accurate
✅ NO BUGS FOUND
Status: PRODUCTION READY
```

### Step 2: Re-run Day 2 Validation
```bash
python3 validate_day2.py
```

Check:
- Do regime classifications still make sense?
- Are historical validation checks still passing?
- COVID crash (2020-03-16) still detected as Trend Down?

### Step 3: Re-run Day 3 Validation
```bash
python3 validate_day3.py
```

Check:
- Profile scores still in [0, 1]?
- Regime alignment still reasonable?
- Smoothness still good?

### Step 4: Visual Inspection
```bash
python3 create_plots.py
```

Look at:
- `regime_bands_2020_2024.png` - Do regimes look reasonable?
- `profile_scores_2020_2024.png` - Do scores look reasonable?

### Step 5: Check Slope Magnitudes
```python
import pandas as pd
from src.data.loaders import load_spy_data

df = load_spy_data()
print(df['slope_MA20'].describe())
```

Expected after fix:
```
mean    ~0.5     # Average SPY gains ~$0.50/day over long term
std     ~3.0     # Volatility in daily slope
min     -20      # Crash days
max     +20      # Recovery rallies
```

If you see values like:
```
mean    0.0005   # Too small
std     0.002    # Suspiciously small
```

Then percentage change method is still being used.

---

## EDGE CASE TO TEST

After fix, verify slope calculation at boundaries:

```python
# Test: First few days (insufficient data)
df.iloc[0:10]['slope_MA20']  # Should be NaN or 0 for first few

# Test: Very volatile period
df[(df['date'] >= '2020-03-01') & (df['date'] <= '2020-04-01')]['slope_MA20'].describe()

# Test: Stable period
df[(df['date'] >= '2021-10-01') & (df['date'] <= '2021-11-01')]['slope_MA20'].describe()
```

---

## ESTIMATED FIX TIME

- **Code change:** 15 minutes
- **Re-run validations:** 30 minutes
- **Visual inspection:** 15 minutes
- **Threshold adjustments (if needed):** 1-2 hours
- **Re-test:** 30 minutes

**Total:** 2-4 hours

---

## AFTER FIX IS VERIFIED

Update documentation:

**File: `docs/FRAMEWORK.md`**
Add clarification:
```markdown
### Slope Calculation Method

All slope calculations use **linear regression** over a 5-day rolling window:
```python
slope = np.polyfit(range(5), ma_values, 1)[0]
```

This returns slope in **price units per day** (e.g., $/day for SPY).

For normalized slope (% per day), divide by price level:
```python
normalized_slope = slope / ma_values.mean()
```
```

**File: `SESSION_STATE.md`**
Add to Decision Log:
```markdown
**2025-11-13:** Fixed slope calculation inconsistency (Bug #1)
- **Decision:** Standardized on linear regression method
- **Why:** More common in quant finance, already used in vol_of_vol_slope
- **Alternatives:** Percentage change (rejected - less interpretable)
- **Impact:** Re-ran all validations (Day 2-6), adjusted sigmoid scalings
```

---

## FINAL CHECKLIST

- [ ] Fix `src/data/features.py` (use linear regression)
- [ ] Re-run `red_team_audit.py` (should pass)
- [ ] Re-run `validate_day2.py` (regime classification)
- [ ] Re-run `validate_day3.py` (profile scores)
- [ ] Visual check plots (regimes + profiles look reasonable)
- [ ] Check slope magnitudes (print `.describe()`)
- [ ] Adjust sigmoid scalings if needed
- [ ] Update documentation (FRAMEWORK.md, SESSION_STATE.md)
- [ ] Commit changes with message: "FIX: Standardize slope calculation to linear regression (Bug #1)"

**Only after ALL checks pass → proceed to Day 6 validation (portfolio aggregation)**

---

**Real money depends on fixing this correctly. Take your time. Verify thoroughly.**
