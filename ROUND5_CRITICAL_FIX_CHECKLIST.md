# CRITICAL BUG FIX CHECKLIST - ROUND 5
## Rotation Engine - Pre-Backtest Validation

**Status:** DO NOT RUN BACKTEST until all CRITICAL fixes applied
**Estimated Fix Time:** 1-2 hours
**Files to Modify:** 3 backtest scripts + 2 support files

---

## TIER 0 BUGS - LOOK-AHEAD BIAS (MUST FIX)

### FIX-001: Rolling Windows Include Current Bar

**Priority:** CRITICAL - Affects all backtests
**Files affected:**
- `scripts/backtest_train.py` (lines 96-99)
- `scripts/backtest_validation.py` (lines 136-139)
- `scripts/backtest_test.py` (lines 153-156)

**Current code:**
```python
spy['MA20'] = spy['close'].rolling(20).mean()
spy['MA50'] = spy['close'].rolling(50).mean()
spy['slope_MA20'] = spy['MA20'].pct_change(20)
spy['slope_MA50'] = spy['MA50'].pct_change(50)
```

**Fix:**
```python
# Calculate using only past bars (exclude current bar)
spy['MA20'] = spy['close'].shift(1).rolling(20).mean()
spy['MA50'] = spy['close'].shift(1).rolling(50).mean()
spy['slope_MA20'] = spy['MA20'].pct_change(20)
spy['slope_MA50'] = spy['MA50'].pct_change(50)
```

**Verification:**
- [ ] Compile and test train script
- [ ] Verify MA20 at row 100 uses closes from rows 79-99 (not 100)
- [ ] Apply same fix to all 3 scripts
- [ ] Commit: "fix: Remove current bar from rolling window calculations"

---

### FIX-002: Verify pct_change() Timing

**Priority:** CRITICAL - Conditional on code review
**Files affected:**
- `scripts/backtest_train.py` (lines 91-94)
- `scripts/backtest_validation.py` (lines 131-134)
- `scripts/backtest_test.py` (lines 148-151)

**Review checklist:**
```python
# These are CORRECT (backward-looking):
spy['return_1d'] = spy['close'].pct_change()      # (t / t-1) - 1 ✓
spy['return_5d'] = spy['close'].pct_change(5)     # (t / t-5) - 1 ✓
spy['return_10d'] = spy['close'].pct_change(10)   # (t / t-10) - 1 ✓
spy['return_20d'] = spy['close'].pct_change(20)   # (t / t-20) - 1 ✓

# These are DANGEROUS (forward-looking if misused):
# DON'T DO: spy['future_return'] = spy['close'].pct_change(-5)  # LOOK-AHEAD!
```

**Action:**
- [ ] Verify no `.pct_change()` with NEGATIVE arguments
- [ ] Verify no `.shift(-1)` or `.shift(-n)` in feature calculations
- [ ] Verify entry conditions don't use future data
- [ ] Add comment: "# All features use backward-looking calculations only"

---

## TIER 1 BUGS - CALCULATION ERRORS (MUST FIX BEFORE PRODUCTION)

### FIX-003: Greeks MTM Pricing Consistency

**Priority:** HIGH - Affects Greeks accuracy
**File affected:** `src/analysis/trade_tracker.py`

**Current problem:**
- Entry uses actual ask/bid prices
- MTM uses mid + manual spread
- These don't reconcile

**Location: Lines 85-94 (Entry)**
```python
if qty > 0:
    price = self.polygon.get_option_price(
        entry_date, position['strike'], position['expiry'], opt_type, 'ask'
    )
else:
    price = self.polygon.get_option_price(
        entry_date, position['strike'], position['expiry'], opt_type, 'bid'
    )
```

**Location: Lines 160-170 (MTM)**
```python
price = self.polygon.get_option_price(
    day_date, position['strike'], position['expiry'], opt_type, 'mid'
)
exit_value = qty * (price - (spread if qty > 0 else -spread)) * 100
```

**CHOOSE ONE: Option A or Option B**

**OPTION A: Use consistent ask/bid throughout (RECOMMENDED)**
```python
# In MTM calculation (lines 160-170), replace:
for leg in position['legs']:
    opt_type = leg['type']
    qty = leg['qty']

    # Use same ask/bid logic as entry
    if qty > 0:
        # Long: use ask (what we'd pay to exit)
        price = self.polygon.get_option_price(
            day_date, position['strike'], position['expiry'], opt_type, 'ask'
        )
    else:
        # Short: use bid (what we'd receive to exit)
        price = self.polygon.get_option_price(
            day_date, position['strike'], position['expiry'], opt_type, 'bid'
        )

    current_prices[opt_type] = price
    exit_value = qty * price * 100  # Remove spread adjustment
```

**OR**

**OPTION B: Use mid + consistent spread throughout**
```python
# If using mid + spread, ensure it's consistent everywhere
mid = self.polygon.get_option_price(day_date, ..., 'mid')
spread = self.ExecutionModel.get_spread(...)  # Use consistent model
price_for_calc = mid + (spread/2 if qty > 0 else -spread/2)
```

**Action:**
- [ ] Choose Option A or B
- [ ] Implement in trade_tracker.py
- [ ] Update entry calculation if using Option B
- [ ] Test: Entry cost should match initial MTM value (zero P&L on day 0)
- [ ] Commit: "fix: Consistent ask/bid pricing in MTM and entry calculations"

---

### FIX-004: IV Estimation Methodology

**Priority:** HIGH - Greeks accuracy
**File affected:** `src/analysis/trade_tracker.py` (lines 270-279)

**Current (WRONG):**
```python
iv = max(0.10, price / spot * np.sqrt(365 / dte) * 2)
```

**Problem:** No theoretical basis, produces unrealistic IVs

**OPTION A: Use empirical IV from polygon data (BEST)**
```python
# If polygon has IV data, use it:
iv = self.polygon.get_implied_volatility(
    date, strike, expiry, option_type, 'mid'
)
if iv is None:
    iv = 0.20  # Default fallback
```

**OPTION B: Use proper Newton-Raphson solver (BEST IF IV not in data)**
```python
from scipy.optimize import brentq
from src.pricing.greeks import calculate_delta

def estimate_iv_from_price(S, K, T, r, market_price, option_type,
                           iv_guess=0.20, max_iter=100):
    """Solve for IV using Newton-Raphson."""
    def price_diff(iv):
        # Use Black-Scholes to calculate price at given IV
        # Return difference from market price
        pass

    try:
        iv = brentq(price_diff, 0.001, 3.0)
    except:
        iv = iv_guess
    return iv
```

**OPTION C: Use improved heuristic (MINIMUM)**
```python
# Better formula for ATM options
if abs(strike - spot) / spot < 0.05:  # ATM
    iv = 2.0 * np.sqrt(price / (spot * np.sqrt(dte / 252)))
else:  # OTM
    iv = 2.5 * np.sqrt(price / (spot * np.sqrt(dte / 252)))
iv = np.clip(iv, 0.05, 3.0)  # Realistic bounds
```

**Action:**
- [ ] Check if polygon has IV data
- [ ] If yes: Use Option A
- [ ] If no: Use Option B (scipy) or Option C (heuristic)
- [ ] Test: IV should be 0.15-0.35 for normal markets
- [ ] Commit: "fix: Replace crude IV estimation with proper methodology"

---

## TIER 2 BUGS - EXECUTION REALISM (SHOULD FIX)

### FIX-005: Peak P&L Calculation Timing

**Priority:** MEDIUM-HIGH
**File affected:** `src/analysis/trade_tracker.py` (lines 178-183, 233)

**Current problem:**
- Peak calculated from MTM values
- MTM uses mid ± spread (modeled)
- Entry uses ask/bid (real)
- Inconsistency creates bias

**After fixing FIX-003 (consistent pricing), verify:**
```python
# At line 178-183:
peak_pnl = -entry_cost  # Initialize

for daily data:
    mtm_pnl = ... # Should be calculated same way as entry
    if mtm_pnl > peak_pnl:
        peak_pnl = mtm_pnl
```

**Action:**
- [ ] Only fix after FIX-003 (pricing consistency) is done
- [ ] Test: First daily MTM should be close to -entry_cost (near zero with spread cost)
- [ ] Verify: Peak is not biased by pricing method changes
- [ ] Commit: "fix: Align peak P&L calculation with consistent pricing"

---

### FIX-006: Handle Division by Zero in pct_captured

**Priority:** MEDIUM
**File affected:** `src/analysis/trade_tracker.py` (line 233)

**Current:**
```python
'pct_of_peak_captured': float((exit_snapshot['mtm_pnl'] / peak_pnl * 100) if peak_pnl > 0 else 0),
```

**Problem:** When peak_pnl ≤ 0, metric is meaningless

**Fix:**
```python
# Calculate pct_captured only for profitable trades
if peak_pnl > 0:
    pct_of_peak_captured = (exit_snapshot['mtm_pnl'] / peak_pnl * 100)
else:
    # Trade never had positive peak - mark as invalid
    pct_of_peak_captured = -999  # Flag for filtering

exit_analytics = {
    ...
    'pct_of_peak_captured': float(pct_of_peak_captured),
    'peak_was_positive': bool(peak_pnl > 0),  # Add flag
    ...
}
```

**Then in analyze_trades():**
```python
def analyze_trades(trades):
    # Filter to only trades with positive peaks
    profitable_trades = [t for t in trades if t['exit']['peak_was_positive']]

    if not profitable_trades:
        return {...}  # Empty results

    pct_captured = [t['exit']['pct_of_peak_captured'] for t in profitable_trades]
    # Use only valid metrics
```

**Action:**
- [ ] Add peak_was_positive flag to exit_analytics
- [ ] Set pct_captured = -999 when peak ≤ 0
- [ ] Filter metrics in analyze_trades()
- [ ] Test: Trades with losses don't skew pct_captured metric
- [ ] Commit: "fix: Handle edge case where peak P&L is non-positive"

---

## TIER 3 BUGS - ROBUSTNESS (NICE TO HAVE)

### FIX-007: Type Safety - JSON Integer Conversion

**Priority:** LOW
**File affected:** `scripts/backtest_validation.py` (lines 449-450), `backtest_test.py` (lines 481)

**Current:**
```python
exit_engine = ExitEngine(phase=1, custom_exit_days=train_params['exit_days'])
# exit_days might have string values from JSON
```

**Fix:**
```python
# Ensure integers after loading from JSON
exit_days_int = {k: int(v) for k, v in train_params['exit_days'].items()}
exit_engine = ExitEngine(phase=1, custom_exit_days=exit_days_int)
```

**Action:**
- [ ] Add int() conversion in both validation and test scripts
- [ ] Test: No TypeError when comparing exit_days
- [ ] Commit: "fix: Ensure exit days are integers after JSON load"

---

### FIX-008: Improve Exception Handling

**Priority:** LOW
**File affected:** All 3 backtest scripts (lines 255-259, 283-287, 300-304)

**Current:**
```python
try:
    if not config['entry_condition'](row):
        continue
except Exception:
    continue  # Silent skip
```

**Fix:**
```python
try:
    if not config['entry_condition'](row):
        continue
except KeyError as e:
    print(f"WARNING: Entry condition missing field {e} at row {idx}")
    continue
except Exception as e:
    print(f"ERROR: Entry condition crashed: {e}")
    print(f"  Row data: {row.to_dict()}")
    raise  # Stop execution to see the real error
```

**Action:**
- [ ] Add specific KeyError handling
- [ ] Add debug output for troubleshooting
- [ ] Re-raise unknown exceptions
- [ ] Commit: "fix: Improve exception handling in entry condition checks"

---

## FIX EXECUTION ORDER

**Do in this order:**

1. **FIX-001** (Rolling windows): Quick, affects all backtests
2. **FIX-002** (pct_change review): Code review, zero changes needed usually
3. **FIX-003** (Pricing consistency): Medium effort, critical for Greeks
4. **FIX-004** (IV estimation): Medium effort, critical for Greeks
5. **FIX-005** (Peak P&L timing): Depends on FIX-003
6. **FIX-006** (Edge case): Easy, improves data quality
7. **FIX-007** (Type safety): Easy, improves robustness
8. **FIX-008** (Exception handling): Easy, improves debugging

---

## TESTING AFTER FIXES

After applying all fixes:

```bash
# 1. Test that train script runs without errors
python scripts/backtest_train.py 2>&1 | head -100

# 2. Verify period enforcement works
# Should see: "✅ TRAIN PERIOD ENFORCED"

# 3. Check for NaNs in derived features
python -c "
import pandas as pd
import glob
import sys
sys.path.append('/Users/zstoc/rotation-engine')

# Load partial data and check features
from scripts.backtest_train import load_spy_data
spy = load_spy_data()
print('Feature NaN counts:')
print(spy[['MA20', 'MA50', 'return_5d', 'RV5']].isna().sum())
print('\nFirst non-NaN MA20:', spy[spy['MA20'].notna()]['MA20'].iloc[0])
print('Date of first MA20:', spy[spy['MA20'].notna()]['date'].iloc[0])
"

# 4. Run full train period and check output
python scripts/backtest_train.py > train_output.log 2>&1
tail -50 train_output.log
```

---

## DEPLOYMENT CHECKLIST

Before running backtest:

- [ ] FIX-001: Rolling windows use shift(1)
- [ ] FIX-002: No forward-looking features confirmed
- [ ] FIX-003: Consistent pricing method implemented
- [ ] FIX-004: IV estimation replaced
- [ ] FIX-005: Peak calculation verified
- [ ] FIX-006: Edge case handling added
- [ ] FIX-007: Type safety applied
- [ ] FIX-008: Exception handling improved
- [ ] All 3 scripts compile without syntax errors
- [ ] Train script produces output files
- [ ] Derived parameters saved correctly

**Once all boxes checked:**

```bash
python scripts/backtest_train.py
# Review results
python scripts/backtest_validation.py
# Review degradation
python scripts/backtest_test.py
# Accept final results (no iterations)
```

---

**Estimated Total Fix Time:** 60-120 minutes
**Complexity:** Medium
**Risk of breakage:** Low (fixes are surgical)
**Expected improvement:** Eliminates 5-20% systematic bias from results
