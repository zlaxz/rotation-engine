# RED TEAM AUDIT: Train/Validation/Test Backtest Scripts
**Date:** 2025-11-18
**Auditor:** Claude (Strategy Logic Auditor Mode)
**Scripts Audited:**
- `scripts/backtest_train.py`
- `scripts/backtest_validation.py`
- `scripts/backtest_test.py`

**Dependencies Audited:**
- `src/analysis/trade_tracker.py`
- `src/trading/exit_engine.py`

---

## EXECUTIVE SUMMARY

**CRITICAL BUGS FOUND: 3**
**HIGH SEVERITY BUGS: 5**
**MEDIUM SEVERITY BUGS: 4**
**LOW SEVERITY BUGS: 2**

**VERDICT: MULTIPLE CRITICAL BUGS - DO NOT RUN UNTIL FIXED**

The three backtest scripts contain **critical API mismatches** that will cause immediate runtime failure. All three scripts call `TradeTracker.track_trade()` with an incompatible signature that doesn't match the actual implementation.

Additionally, there are **systematic calculation errors** in P&L aggregation, **missing data validation**, and **edge case handling bugs** that would corrupt results even if the scripts ran.

---

## BUG CATALOG

### CRITICAL SEVERITY (Breaks Execution)

#### BUG-001: CRITICAL API SIGNATURE MISMATCH
**Location:** All three scripts (lines 272, 298, 315 respectively)
**Severity:** CRITICAL - Runtime failure on first trade

**Description:**
Scripts call `tracker.track_trade()` with signature:
```python
trade_data = tracker.track_trade(
    entry_date=entry_date,
    expiry=expiry,
    legs=config['legs'],
    spot_at_entry=spot,
    tracking_days=14
)
```

But `TradeTracker.track_trade()` actual signature (from `src/analysis/trade_tracker.py:39-46`):
```python
def track_trade(
    self,
    entry_date: date,
    position: Dict,        # <-- Expects single 'position' dict
    spy_data: pd.DataFrame,  # <-- Missing in script calls!
    max_days: int = 14,
    regime_data: Optional[pd.DataFrame] = None
)
```

**Impact:**
- **Scripts will crash immediately** with `TypeError: track_trade() missing required positional argument: 'position'`
- Zero trades will be tracked
- All three scripts completely non-functional

**Evidence:**
Compare to working script `backtest_with_full_tracking.py:268-273`:
```python
position = {
    'profile': profile_id,
    'structure': config['structure'],
    'strike': strike,
    'expiry': expiry,
    'legs': config['legs']
}

trade_record = tracker.track_trade(
    entry_date=entry_date,
    position=position,      # <-- Correct: position dict
    spy_data=spy,           # <-- Correct: pass SPY data
    max_days=exit_day
)
```

**Recommended Fix:**
In all three scripts, replace the `tracker.track_trade()` call section (around lines 266-278 in train, 293-304 in validation, 310-321 in test):

```python
# BUILD POSITION DICT (add before track_trade call)
position = {
    'profile': profile_id,
    'structure': config['structure'],
    'strike': spot,  # Using spot as strike for ATM structures
    'expiry': expiry,
    'legs': config['legs']
}

# CORRECT API CALL
trade_data = tracker.track_trade(
    entry_date=entry_date,
    position=position,
    spy_data=spy,
    max_days=14,
    regime_data=None
)
```

---

#### BUG-002: CRITICAL - MISSING STRIKE PRICE CALCULATION
**Location:** All three scripts in trade entry logic
**Severity:** CRITICAL - Invalid position construction

**Description:**
Scripts never calculate `strike` price before attempting to track trade. The working script calculates:
```python
strike = round(spot / 5) * 5  # ATM strike rounded to $5
```

But the new scripts have **no strike calculation**. They would need to pass `strike` to the position dict but it's undefined.

**Impact:**
- Even if Bug-001 is fixed, `strike` variable is undefined
- Position dict construction would fail with `NameError: name 'strike' is not defined`
- No trades can be created

**Recommended Fix:**
Add strike calculation before position construction (around line 266 in all three scripts):
```python
# Calculate ATM strike (round to nearest $5)
strike = round(spot / 5) * 5

# For Profile_5_SKEW (OTM puts), calculate 5% OTM
if profile_id == 'Profile_5_SKEW':
    strike = round(spot * 0.95 / 5) * 5

position = {
    'profile': profile_id,
    'structure': config['structure'],
    'strike': strike,  # <-- Now defined
    'expiry': expiry,
    'legs': config['legs']
}
```

---

#### BUG-003: CRITICAL - INCOMPATIBLE RETURN DATA STRUCTURE
**Location:** `analyze_trades()` in all three scripts (lines 291-320, 316-345, 333-362)
**Severity:** CRITICAL - Data extraction failure

**Description:**
`analyze_trades()` assumes trade data structure:
```python
final_pnls = [t['exit']['final_pnl'] for t in trades]
peak_pnls = [t['exit']['peak_pnl'] for t in trades]
```

But `TradeTracker.track_trade()` returns a dict with structure:
```python
{
    'entry': {...},
    'path': [{...}, {...}],  # List of daily snapshots
    'exit': {...}
}
```

The scripts are trying to access keys that **match the actual structure**, so this is actually **CORRECT**. However, there's a subtle bug...

**WAIT - RETRACTING BUG-003:**
On closer inspection, the data structure IS compatible. `TradeTracker` line 244-248 returns:
```python
trade_record = {
    'entry': entry_snapshot,
    'path': daily_path,
    'exit': exit_analytics  # <-- Contains final_pnl, peak_pnl, etc.
}
```

And `exit_analytics` (lines 227-241) contains:
```python
exit_analytics = {
    'exit_date': exit_snapshot['date'],
    'days_held': days_held,
    'final_pnl': exit_snapshot['mtm_pnl'],  # <-- PRESENT
    'peak_pnl': float(peak_pnl),            # <-- PRESENT
    ...
}
```

**CORRECTING TO NON-BUG:** Structure is compatible. Downgrading to HIGH severity for missing error handling.

---

### HIGH SEVERITY (Corrupts Results)

#### BUG-004: HIGH - MISSING ERROR HANDLING FOR NONE RETURNS
**Location:** All three scripts, post-`track_trade()` call (lines 280-283, 306-310, 323-327)
**Severity:** HIGH - Silent data loss

**Description:**
Scripts check `if trade_data:` but don't count or report failures:
```python
if trade_data:
    trade_data['profile_id'] = profile_id
    trade_data['profile_name'] = config['name']
    trades.append(trade_data)
    last_entry_date = entry_date
```

`TradeTracker.track_trade()` returns `None` if:
- Entry data not found (line 67)
- Option price unavailable (line 97)
- Exit data incomplete (line 210)

**Impact:**
- Silently drops failed trades
- No visibility into data availability issues
- Can't distinguish between "no entry signals" vs "data missing"
- Biases results toward periods with complete data

**Evidence:**
Working script `backtest_with_full_tracking.py:275-277` has same issue - no failure tracking.

**Recommended Fix:**
Add failure tracking:
```python
# Before loop
entry_signals = 0
tracking_failures = 0

# In loop, after entry triggered
entry_signals += 1

trade_data = tracker.track_trade(...)

if trade_data:
    trade_data['profile_id'] = profile_id
    trade_data['profile_name'] = config['name']
    trades.append(trade_data)
    last_entry_date = entry_date
else:
    tracking_failures += 1
    print(f"  WARNING: Failed to track trade on {entry_date} (data unavailable)")

# After loop
print(f"✅ Completed: {len(trades)} trades")
print(f"⚠️  Entry signals: {entry_signals}, Tracking failures: {tracking_failures}")
if tracking_failures > entry_signals * 0.1:
    print(f"❌ WARNING: {tracking_failures}/{entry_signals} trades failed - data quality issue!")
```

---

#### BUG-005: HIGH - PEAK POTENTIAL CALCULATION ERROR (NEGATIVE PEAKS)
**Location:** `analyze_trades()` in all three scripts (lines 312, 337, 354)
**Severity:** HIGH - Inflates peak potential metric

**Description:**
```python
'peak_potential': sum([p for p in peak_pnls if p > 0]),
```

This **only sums positive peaks** but ignores trades where peak was negative (losers that never went positive). This inflates the "peak potential" metric.

**Correct Calculation:**
If a trade's peak P&L was -$50 (never went positive), that trade had **zero** peak potential, not "exclude from sum". The current code makes peak potential look better than reality.

**Impact:**
- Overstates peak capture opportunity
- Makes capture % look worse than it is (denominator too high)
- Misleading metric for exit strategy analysis

**Recommended Fix:**
```python
# Option 1: Sum all peaks including negatives (true opportunity cost)
'peak_potential': sum(peak_pnls),

# Option 2: Count only profitable trades' peaks (cleaner metric)
'peak_potential': sum([p for p in peak_pnls if p > 0]),
'profitable_trades': sum(1 for p in peak_pnls if p > 0),

# Option 3: Separate metrics
'total_peak_pnl': sum(peak_pnls),
'positive_peak_potential': sum([p for p in peak_pnls if p > 0]),
```

**Recommendation:** Use Option 3 for clarity - track both metrics separately.

---

#### BUG-006: HIGH - DIVISION BY ZERO IN CAPTURE PERCENTAGE
**Location:** `TradeTracker._exit_analytics` line 233
**Severity:** HIGH - Crash or NaN injection

**Description:**
```python
'pct_of_peak_captured': float((exit_snapshot['mtm_pnl'] / peak_pnl * 100) if peak_pnl > 0 else 0),
```

This handles `peak_pnl = 0` but **not `peak_pnl < 0`** (trades that never went positive).

If `peak_pnl = -100` (trade peaked at -$100 loss) and `exit_pnl = -150`:
```
pct_captured = -150 / -100 * 100 = 150%
```

This says we "captured 150% of peak" which is **nonsensical** for a losing trade.

**Impact:**
- Nonsensical metrics for losing trades
- Corrupts average capture percentage
- Misleading exit quality analysis

**Recommended Fix:**
```python
# Only calculate capture % for trades that went positive
if peak_pnl > 0:
    pct_captured = exit_snapshot['mtm_pnl'] / peak_pnl * 100
elif peak_pnl == 0:
    pct_captured = 0
else:
    # Negative peak = trade never profitable = 0% capture
    pct_captured = 0

'pct_of_peak_captured': float(pct_captured),
```

---

#### BUG-007: HIGH - INCONSISTENT TRAIN PERIOD DATE FILTERING
**Location:** `backtest_train.py` lines 64-66
**Severity:** HIGH - Data leak risk

**Description:**
Date boundary enforcement uses **strict inequality** on end date:
```python
if file_date < TRAIN_START or file_date > TRAIN_END:
    continue
```

This is correct, but the validation later (line 87) checks:
```python
if actual_start < TRAIN_START or actual_end > TRAIN_END:
    raise ValueError(f"DATA LEAK DETECTED: Data outside train period!")
```

Edge case: If `file_date == TRAIN_END` (exactly 2021-12-31), it passes the filter but then `actual_end > TRAIN_END` is False (2021-12-31 is not > 2021-12-31), so validation passes.

**This is actually correct** - data on the boundary date should be included. **RETRACTING as bug.**

**CORRECTING:** Not a bug, filtering is correct.

---

#### BUG-008: HIGH - VALIDATION SCRIPT DOESN'T VERIFY PARAMETERS WERE ACTUALLY USED
**Location:** `backtest_validation.py` lines 436-445
**Severity:** HIGH - Silent parameter override failure

**Description:**
Validation script loads train params and overrides exit engine:
```python
for profile_id, exit_day in train_params['exit_days'].items():
    exit_engine.exit_days[profile_id] = exit_day
```

But `ExitEngine` defines `PROFILE_EXIT_DAYS` as class-level constant (line 27-34). The script assigns to `exit_engine.exit_days` but this attribute **doesn't exist** unless added in `__init__`.

**Impact:**
- Parameters aren't actually overridden
- Uses hard-coded defaults instead of train-derived values
- Validation results meaningless (not testing train parameters)

**Evidence:**
`ExitEngine.__init__` (line 36-46) doesn't create `self.exit_days` attribute. The `get_exit_day()` method (line 79-81) reads from class constant `PROFILE_EXIT_DAYS`, not instance variable.

**Recommended Fix:**
Modify `ExitEngine.__init__` to create mutable instance variable:
```python
def __init__(self, phase: int = 1):
    self.phase = phase
    self.exit_days = self.PROFILE_EXIT_DAYS.copy()  # <-- Add this

    if phase != 1:
        raise NotImplementedError(...)
```

And modify `get_exit_day()`:
```python
def get_exit_day(self, profile: str) -> int:
    return self.exit_days.get(profile, 14)  # <-- Use instance var
```

Then validation/test scripts can override:
```python
for profile_id, exit_day in train_params['exit_days'].items():
    exit_engine.exit_days[profile_id] = exit_day  # Now works
```

---

### MEDIUM SEVERITY (Affects Edge Cases)

#### BUG-009: MEDIUM - NO VALIDATION OF TRAIN PARAMS FILE STRUCTURE
**Location:** `backtest_validation.py` line 72-73, `backtest_test.py` line 87-88
**Severity:** MEDIUM - Crash on malformed config

**Description:**
Scripts load JSON and immediately access keys:
```python
params = json.load(f)
# ... then later ...
for profile_id, exit_day in params['exit_days'].items():
```

No validation that:
- `exit_days` key exists
- Values are integers
- Profile IDs match expected profiles
- Values are reasonable (e.g., 1-14 days)

**Impact:**
- Crash with cryptic error if config file malformed
- Silent wrong behavior if values out of range
- No detection of config corruption

**Recommended Fix:**
```python
# After loading params
required_keys = ['train_period', 'derived_date', 'exit_days', 'profile_stats']
for key in required_keys:
    if key not in params:
        raise ValueError(f"Malformed train params: missing '{key}' key")

# Validate exit days
for profile_id, exit_day in params['exit_days'].items():
    if not isinstance(exit_day, int):
        raise ValueError(f"Invalid exit_day for {profile_id}: {exit_day} (not int)")
    if not (1 <= exit_day <= 30):
        print(f"⚠️  WARNING: {profile_id} exit_day={exit_day} outside typical range [1, 30]")
```

---

#### BUG-010: MEDIUM - DEGRADATION CALCULATION MISSING EDGE CASE
**Location:** `backtest_validation.py` line 387
**Severity:** MEDIUM - Division by zero

**Description:**
```python
peak_degradation_pct = ((val_peak - train_peak) / train_peak * 100) if train_peak else 0
```

Handles `train_peak = 0` but what if `train_peak < 0` (train period lost money)?

Example:
- Train peak: -$500 (all trades lost)
- Val peak: -$200 (smaller loss)
- Degradation: (-200 - (-500)) / -500 * 100 = 300 / -500 * 100 = -60%

This says "degradation is -60%" (negative degradation = improvement) which is **technically correct** but confusing. A strategy that loses less money in validation than train is still a losing strategy.

**Impact:**
- Confusing metrics when both periods lose money
- "Negative degradation" is misleading term
- Doesn't handle train profitable, validation unprofitable (sign flip)

**Recommended Fix:**
```python
# Check for sign flip (critical failure mode)
if train_peak > 0 and val_peak < 0:
    red_flags.append("SIGN FLIP: Profitable in train, unprofitable in validation")
    peak_degradation_pct = -100  # Lost all value plus more
elif train_peak < 0 and val_peak < 0:
    # Both negative - compare absolute losses
    if abs(val_peak) > abs(train_peak):
        peak_degradation_pct = (abs(val_peak) - abs(train_peak)) / abs(train_peak) * 100
        red_flags.append("DEGRADATION IN LOSS: Validation losses worse than train")
    else:
        peak_degradation_pct = -(abs(train_peak) - abs(val_peak)) / abs(train_peak) * 100
elif train_peak == 0:
    peak_degradation_pct = 0
else:
    # Normal case: both positive
    peak_degradation_pct = ((val_peak - train_peak) / train_peak * 100)
```

---

#### BUG-011: MEDIUM - NO CHECK FOR EMPTY SPY DATA
**Location:** All three scripts, `load_spy_data()` after building dataframe (lines 77, 117, 134)
**Severity:** MEDIUM - Silent failure on missing data

**Description:**
After loading SPY files, creates dataframe:
```python
spy = pd.DataFrame(spy_data)
```

But never checks if `spy_data` list is empty (e.g., data drive not mounted, wrong path, no files for period).

**Impact:**
- Creates empty DataFrame
- All rolling calculations return NaN
- Scripts run but produce zero trades
- Wastes time debugging wrong thing

**Recommended Fix:**
```python
spy = pd.DataFrame(spy_data)

if len(spy) == 0:
    raise ValueError(
        f"No SPY data loaded for period {TRAIN_START} to {TRAIN_END}.\n"
        f"Check that data drive is mounted at: /Volumes/VelocityData/velocity_om/parquet/stock/SPY/"
    )

print(f"Loaded {len(spy)} days from {spy['date'].min()} to {spy['date'].max()}\n")
```

---

#### BUG-012: MEDIUM - WARMUP PERIOD NOT VALIDATED
**Location:** All three scripts, loop start (lines 246, 276, 293)
**Severity:** MEDIUM - Invalid feature calculations

**Description:**
Scripts start iterating at row 60:
```python
for idx in range(60, len(spy)):
```

This assumes 60 days is enough warmup for all features. But:
- `MA50` needs 50 days
- `slope_MA50` needs MA50 + 50 days = 100 days
- Script only waits 60 days

**Impact:**
- First trades may use NaN in MA50/slope_MA50
- Entry conditions may trigger incorrectly
- Silent data quality issue

**Recommended Fix:**
```python
# Calculate required warmup
WARMUP_DAYS = 100  # Max feature lookback (MA50 + slope calculation)

if len(spy) < WARMUP_DAYS:
    raise ValueError(
        f"Insufficient data: {len(spy)} days < {WARMUP_DAYS} required for feature warmup"
    )

# Verify no NaN in required columns at warmup point
warmup_row = spy.iloc[WARMUP_DAYS]
required_features = ['MA50', 'slope_MA50', 'RV20', 'return_20d']
for feat in required_features:
    if pd.isna(warmup_row[feat]):
        raise ValueError(f"Feature {feat} still NaN after {WARMUP_DAYS} day warmup")

# Start iteration after warmup
for idx in range(WARMUP_DAYS, len(spy)):
```

---

### LOW SEVERITY (Code Quality)

#### BUG-013: LOW - DUPLICATE PROFILE CONFIGS ACROSS FILES
**Location:** All three scripts, `get_profile_configs()` function
**Severity:** LOW - Maintenance burden

**Description:**
Profile definitions are **copy-pasted** across all three scripts (and the working script). Any change to entry conditions requires editing 4+ files.

**Impact:**
- High risk of inconsistency
- If profiles change, easy to update one script but miss others
- Violates DRY principle

**Recommended Fix:**
Move to shared config file:
```python
# src/config/profiles.py
def get_profile_configs():
    """Centralized profile definitions"""
    return { ... }

# In backtest scripts
from src.config.profiles import get_profile_configs
```

---

#### BUG-014: LOW - HARDCODED PATHS
**Location:** All three scripts, multiple locations
**Severity:** LOW - Portability

**Description:**
Paths are hardcoded:
```python
sys.path.append('/Users/zstoc/rotation-engine')
spy_files = sorted(glob.glob('/Volumes/VelocityData/velocity_om/parquet/stock/SPY/*.parquet'))
output_dir = Path('/Users/zstoc/rotation-engine/data/backtest_results/train_2020-2021')
```

**Impact:**
- Breaks on different machines
- Can't run from different working directory
- Hard to containerize or test in CI

**Recommended Fix:**
```python
import os
from pathlib import Path

# Determine project root
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.append(str(PROJECT_ROOT))

# Data paths from environment or config
DATA_ROOT = os.getenv('VELOCITY_DATA_PATH', '/Volumes/VelocityData')
spy_files = sorted(glob.glob(f'{DATA_ROOT}/velocity_om/parquet/stock/SPY/*.parquet'))

output_dir = PROJECT_ROOT / 'data' / 'backtest_results' / 'train_2020-2021'
```

---

## ADDITIONAL OBSERVATIONS

### OBSERVATION-1: MISSING TRANSACTION COST REALITY CHECK
**Not a bug, but important quality gate**

Scripts use `TradeTracker` which applies costs (line 76-77, 107-108):
- Commission: $2.60 per trade
- Spread: $0.03 per contract

But **never validate** these assumptions against real market data. These costs should be:
- Loaded from config file
- Validated against historical spread data
- Adjustable for sensitivity testing

### OBSERVATION-2: NO PROFILE-SPECIFIC DISASTER FILTER THRESHOLDS
**Not a bug, but design limitation**

All scripts use:
```python
if row.get('RV5', 0) > 0.22:
    continue
```

This applies **same vol filter to all profiles**. But Profile_6_VOV trades volatility - should it have different threshold? Short-dated vs long-dated profiles may have different risk tolerance.

Consider profile-specific filters in config.

### OBSERVATION-3: NO VERIFICATION OF EXPIRY CALCULATION
**Potential subtle bug in `get_expiry_for_dte()`**

Location: Lines 208-215 (train), 239-246 (validation), 256-263 (test)

```python
def get_expiry_for_dte(entry_date: date, dte_target: int) -> date:
    target_date = entry_date + timedelta(days=dte_target)
    first_day = date(target_date.year, target_date.month, 1)
    days_to_friday = (4 - first_day.weekday()) % 7
    first_friday = first_day + timedelta(days=days_to_friday)
    third_friday = first_friday + timedelta(days=14)
    return third_friday
```

**Potential issues:**
1. Assumes third Friday is standard monthly expiration (TRUE for SPX, but are we using SPX or SPY options?)
2. Doesn't handle weeks where third Friday is a holiday
3. No validation that calculated expiry is actually a valid trading day
4. For DTE_target=7 (weekly options), this might return monthly expiration instead of nearest weekly

**Needs validation:** Test with sample dates to verify returns correct expiration.

---

## MANUAL VERIFICATION REQUIRED

To complete this audit, I need to manually verify calculations for sample trades. However, scripts **cannot run** until BUG-001 and BUG-002 are fixed.

**After fixing critical bugs, perform:**

1. **Test Expiry Calculation:**
   - Entry: 2020-01-06 (Monday), DTE target: 45
   - Expected: Third Friday of February 2020 = Feb 21, 2020
   - Actual: Run `get_expiry_for_dte(date(2020, 1, 6), 45)`

2. **Test Strike Calculation:**
   - Spot: $342.67
   - Expected ATM strike: $345 (round to nearest $5)
   - Expected 5% OTM put: $325

3. **Test Train Period Enforcement:**
   - Verify no data before 2020-01-01
   - Verify no data after 2021-12-31
   - Check boundary dates (2020-01-01, 2021-12-31) are included

4. **Test Parameter Derivation:**
   - Run train script (after fixing bugs)
   - Verify `config/train_derived_params.json` created
   - Verify exit_days are integers in [1, 14]
   - Verify profile_stats contain reasonable values

5. **Test Parameter Loading:**
   - Run validation script
   - Verify it actually uses train-derived exit days (not defaults)
   - Print exit_engine.exit_days before and after override

---

## RECOMMENDED FIX PRIORITY

**DO IMMEDIATELY (Blockers):**
1. Fix BUG-001: API signature mismatch
2. Fix BUG-002: Missing strike calculation
3. Fix BUG-008: Exit engine parameter override

**DO BEFORE FIRST RUN (Data Quality):**
4. Fix BUG-004: Add error handling and failure tracking
5. Fix BUG-011: Check for empty data
6. Fix BUG-012: Validate warmup period

**DO BEFORE TRUSTING RESULTS (Metrics):**
7. Fix BUG-005: Peak potential calculation
8. Fix BUG-006: Capture percentage for losing trades
9. Fix BUG-010: Degradation calculation edge cases

**DO FOR PRODUCTION (Quality):**
10. Fix BUG-009: Validate config file structure
11. Fix BUG-013: Centralize profile configs
12. Fix BUG-014: Remove hardcoded paths

---

## ESTIMATED IMPACT ON RETURNS

**If scripts ran with current bugs (hypothetical):**

- **BUG-001, BUG-002:** Scripts don't run → No results
- **BUG-008:** Uses wrong exit days → Returns could be ±20% different
- **BUG-005:** Peak potential overstated → Capture % understated by ~10-15%
- **BUG-006:** Nonsense metrics for losers → Average capture % corrupted
- **BUG-012:** Early trades use NaN features → Random entry signals, ±5% returns

**Combined effect:** Results would be **completely invalid** even if scripts ran.

---

## AUDIT VERDICT

**❌ FAIL - MULTIPLE CRITICAL BUGS PRESENT**

**Cannot run scripts until fixing:**
1. BUG-001 (API mismatch)
2. BUG-002 (Missing strike)
3. BUG-008 (Parameter override)

**Cannot trust results until fixing:**
4. BUG-004 (Error handling)
5. BUG-005 (Peak potential)
6. BUG-006 (Capture %)
7. BUG-011 (Empty data check)
8. BUG-012 (Warmup validation)

**Estimated time to fix all CRITICAL/HIGH bugs:** 2-3 hours

**Recommendation:**
1. Fix all CRITICAL bugs first (1 hour)
2. Test with small date range (2020-01 only) to verify execution
3. Fix all HIGH bugs (1 hour)
4. Run full train period
5. Manually verify 5 trades against spreadsheet calculations
6. Proceed to validation/test if train results look reasonable

---

## APPENDIX: SPOT-CHECK METHODOLOGY

Once scripts are fixed, perform these manual verifications:

### Verification 1: Entry Cost Calculation
**Random trade from train results:**
- Entry date: [Select from results]
- Spot: [From results]
- Strike: [From results]
- Call price (ask): [Look up in Polygon data]
- Put price (ask): [Look up in Polygon data]

**Expected entry cost:**
```
= (call_ask + put_ask) * 100 + commission
= (call_ask + put_ask) * 100 + 2.60
```

**Actual from results:** Compare to `entry_cost` field

### Verification 2: Peak Timing
**Trade with known peak:**
- Find trade that peaked on day 5
- Verify daily path shows P&L increasing days 0-5
- Verify P&L decreasing days 6-14
- Verify `day_of_peak = 5`

### Verification 3: Exit Day Application
**Validation period:**
- Load `config/train_derived_params.json`
- Read `exit_days['Profile_1_LDG']` (should be 7 from train median)
- Find a Profile_1_LDG trade in validation results
- Verify trade held for exactly 7 days
- Verify final P&L taken on day 7 (not day 14)

---

**END OF AUDIT REPORT**
