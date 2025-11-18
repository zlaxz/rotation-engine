# MANUAL VERIFICATION - 10 RANDOM TEST CASES
**Date:** 2025-11-18
**Purpose:** Hand-calculate expected values, compare to code output
**Method:** Spreadsheet-style walkthrough for 10 scenarios

---

## TEST 1: Sharpe Ratio Calculation (No Double-Count)

### Inputs:
```
Daily P&L: [150, -75, 225, -100, 180]
Starting Capital: $100,000
Risk-free rate: 0%
```

### Manual Calculation:
```
Step 1: Calculate cumulative portfolio value
Day 0 (start):  $100,000
Day 1: 100,000 + 150 = $100,150
Day 2: 100,150 - 75  = $100,075
Day 3: 100,075 + 225 = $100,300
Day 4: 100,300 - 100 = $100,200
Day 5: 100,200 + 180 = $100,380

Step 2: Calculate daily returns (percentage)
Day 1: (100,150 - 100,000) / 100,000 = 0.0015 = 0.15%
Day 2: (100,075 - 100,150) / 100,150 = -0.000749 = -0.0749%
Day 3: (100,300 - 100,075) / 100,075 = 0.002248 = 0.2248%
Day 4: (100,200 - 100,300) / 100,300 = -0.000997 = -0.0997%
Day 5: (100,380 - 100,200) / 100,200 = 0.001796 = 0.1796%

Returns: [0.0015, -0.000749, 0.002248, -0.000997, 0.001796]

Step 3: Calculate Sharpe
Mean return: 0.000760
Std dev:     0.001274
Sharpe = (0.000760 / 0.001274) * sqrt(252)
Sharpe = 0.5965 * 15.8745
Sharpe = 9.47
```

### Expected Output:
```python
sharpe = 9.47
```

### Code Verification:
```python
from src.analysis.metrics import PerformanceMetrics
import pandas as pd

pnl = pd.Series([150, -75, 225, -100, 180])
m = PerformanceMetrics(starting_capital=100000)
sharpe = m.sharpe_ratio(pnl)

# Should be close to 9.47
assert 9.0 < sharpe < 10.0, f"Expected ~9.47, got {sharpe}"
```

### BUG CHECK:
If old buggy code was used (first return double-counted):
```
Returns would be: [0.0015, 0.0015, -0.000749, 0.002248, -0.000997, 0.001796]
                   └─DUPLICATE─┘
6 returns instead of 5 → WRONG calculation
```

---

## TEST 2: Profile_5_SKEW Strike Price

### Inputs:
```
Entry Date: 2020-09-03
SPY Spot: $344.50
Profile: Profile_5_SKEW (5% OTM Put)
```

### Manual Calculation:
```
For 5% OTM Put, strike should be BELOW spot
Strike = spot * 0.95
Strike = 344.50 * 0.95
Strike = 327.275
Strike (rounded) = 327
```

### Expected Output:
```
strike = 327
```

### Code Verification:
```python
spot = 344.50
profile_id = 'Profile_5_SKEW'

if profile_id == 'Profile_5_SKEW':
    strike = round(spot * 0.95)
else:
    strike = round(spot)

assert strike == 327, f"Expected 327, got {strike}"
```

### BUG CHECK:
If old buggy code was used:
```python
strike = round(spot)  # No special handling
strike = round(344.50) = 345  # WRONG - this is ATM, not 5% OTM
```

---

## TEST 3: Expiry DTE Calculation

### Inputs:
```
Entry Date: 2020-01-02 (Thursday)
Target DTE: 7 days
```

### Manual Calculation:
```
Entry: 2020-01-02 (Thursday, weekday=3)
Target date: 2020-01-02 + 7 days = 2020-01-09 (Thursday)

Find next Friday from target:
days_to_friday = (4 - 3) % 7 = 1
next_friday = 2020-01-09 + 1 = 2020-01-10 (Friday)

Find previous Friday:
prev_friday = 2020-01-10 - 7 = 2020-01-03 (Friday)

Distance to next: |2020-01-10 - 2020-01-09| = 1 day
Distance to prev: |2020-01-03 - 2020-01-09| = 6 days

Closer: next_friday (1 day < 6 days)
Expiry: 2020-01-10

Actual DTE: 2020-01-10 - 2020-01-02 = 8 days (close to target 7)
```

### Expected Output:
```
expiry = date(2020, 1, 10)
actual_dte = 8 days
```

### Code Verification:
```python
from datetime import date, timedelta

entry_date = date(2020, 1, 2)
dte_target = 7
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

assert expiry == date(2020, 1, 10), f"Expected 2020-01-10, got {expiry}"
```

---

## TEST 4: Greeks Contract Multiplier

### Inputs:
```
Position: Long 1 ATM Call
Spot: $400
Strike: $400
DTE: 30 days
IV: 20%
Delta (per share): 0.50
```

### Manual Calculation:
```
Raw delta from Black-Scholes: 0.50 (per share)
Quantity: 1 contract
Contract multiplier: 100 shares

Position delta = 0.50 * 1 * 100 = 50

Interpretation: For $1 move in SPY, position moves $50
```

### Expected Output:
```
position_delta = 50.0
```

### Code Verification:
```python
# Assuming calculate_all_greeks returns per-share values
greeks = {'delta': 0.50, 'gamma': 0.02, 'theta': -5.0, 'vega': 15.0}
qty = 1
CONTRACT_MULTIPLIER = 100

position_delta = greeks['delta'] * qty * CONTRACT_MULTIPLIER
assert position_delta == 50.0, f"Expected 50.0, got {position_delta}"
```

### BUG CHECK:
If old buggy code was used (no multiplier):
```
position_delta = 0.50 * 1 = 0.50  # WRONG - too small by 100x
```

---

## TEST 5: Peak Detection (Floating Point)

### Inputs:
```
Daily P&L path: [10.25, 15.50, 18.75, 18.7500001, 12.30]
                            └─peak─┘ └─floating pt─┘
```

### Manual Calculation:
```
Day 0: P&L = 10.25
Day 1: P&L = 15.50
Day 2: P&L = 18.75  ← TRUE PEAK (but floating point issues)
Day 3: P&L = 18.7500001 (rounding artifact)
Day 4: P&L = 12.30

Using == comparison: might find day 3 as peak (wrong)
Using max() with key: will find day 2 or 3 (both close)
```

### Expected Output:
```
day_of_peak = 2 or 3 (both acceptable - within floating point tolerance)
```

### Code Verification:
```python
daily_path = [
    {'day': 0, 'mtm_pnl': 10.25},
    {'day': 1, 'mtm_pnl': 15.50},
    {'day': 2, 'mtm_pnl': 18.75},
    {'day': 3, 'mtm_pnl': 18.7500001},
    {'day': 4, 'mtm_pnl': 12.30}
]

day_of_peak = max(range(len(daily_path)), key=lambda i: daily_path[i]['mtm_pnl'])

# Should be 2 or 3 (max will find 3 due to slight higher value)
assert day_of_peak in [2, 3], f"Expected 2 or 3, got {day_of_peak}"
```

### BUG CHECK:
If old buggy code used == comparison:
```python
for i, d in enumerate(daily_path):
    if d['mtm_pnl'] == peak_pnl:  # Floating point comparison
        day_of_peak = i
        break
# Might miss peak due to floating point inequality
```

---

## TEST 6: Percent of Peak Captured (Losing Trade)

### Inputs:
```
Daily P&L path: [-10, -20, -5, -15, -25]
Peak P&L: -5 (least negative)
Final P&L: -25
```

### Manual Calculation:
```
This is a losing trade (never profitable)
Peak = -5 (best outcome was still a loss)
Final = -25

For losing trades, we want to know:
How much did we recover from worst point?

But this is tricky - peak is -5, but we ended worse at -25
Recovery percentage doesn't make sense here

Alternative calculation:
What percentage of our path from entry to peak did we capture?
pct_captured = (final - peak) / abs(peak) * 100
pct_captured = (-25 - (-5)) / 5 * 100
pct_captured = -20 / 5 * 100 = -400%

Or simpler: For losing trades, show how much worse final vs peak
```

### Expected Output:
```
pct_captured = -400% (ended 4x worse than peak)
OR
pct_captured = 0% (losing trade convention)
```

### Code Verification:
```python
peak_pnl = -5
final_pnl = -25

if peak_pnl > 0:
    pct_captured = final_pnl / peak_pnl * 100
elif peak_pnl < 0:
    pct_captured = (final_pnl - peak_pnl) / abs(peak_pnl) * 100
else:
    pct_captured = 0.0

# For this case: (-25 - (-5)) / 5 * 100 = -400%
assert pct_captured == -400.0, f"Expected -400%, got {pct_captured}%"
```

### BUG CHECK:
If old buggy code didn't handle negative peaks:
```python
pct_captured = final_pnl / peak_pnl * 100  # Division by zero or wrong sign
# -25 / -5 * 100 = +500% (WRONG interpretation)
```

---

## TEST 7: Entry Execution Timing (T+1)

### Inputs:
```
SPY data:
idx  | date       | close  | open (next day)
-----|------------|--------|----------------
60   | 2020-03-15 | 254.50 | N/A
61   | 2020-03-16 | 258.00 | 256.00
62   | 2020-03-17 | 260.50 | 259.00

Entry signal triggers at end of day idx=60 (close = 254.50)
```

### Manual Calculation:
```
Signal: Triggered on 2020-03-15 at close (254.50)
Can we enter immediately? NO - market closed
When do we enter? Next day's open

Execution:
- Signal date: 2020-03-15 (idx=60)
- Execution date: 2020-03-16 (idx=61)
- Execution price: 256.00 (next day's open)

NOT 254.50 (would be look-ahead bias - using close to enter same day)
```

### Expected Output:
```
entry_date = date(2020, 3, 16)
entry_price = 256.00
```

### Code Verification:
```python
# Loop at idx=60, signal triggers
idx = 60
signal_date = spy.iloc[idx]['date']  # 2020-03-15

# Execute at next day
next_day = spy.iloc[idx + 1]
entry_date = next_day['date']  # 2020-03-16
spot = next_day['open']  # 256.00

assert entry_date == date(2020, 3, 16), f"Expected 2020-03-16, got {entry_date}"
assert spot == 256.00, f"Expected 256.00, got {spot}"
```

### BUG CHECK:
If old buggy code used same-day close:
```python
# WRONG - look-ahead bias
entry_date = row['date']  # 2020-03-15
spot = row['close']  # 254.50
# Enters same day signal triggered - impossible in real trading
```

---

## TEST 8: Sortino Ratio (Downside Deviation)

### Inputs:
```
Daily returns: [0.02, -0.01, 0.03, -0.02, 0.01]
Target return: 0%
Risk-free rate: 0%
```

### Manual Calculation:
```
Excess returns (rf=0%): [0.02, -0.01, 0.03, -0.02, 0.01]
Mean excess: 0.006

Downside returns (below target=0):
min(return - target, 0) for each:
[0, -0.01, 0, -0.02, 0]

Downside deviation:
sqrt(mean(downside^2))
= sqrt(mean([0, 0.0001, 0, 0.0004, 0]))
= sqrt(0.0001)
= 0.01

Sortino = (0.006 / 0.01) * sqrt(252)
Sortino = 0.6 * 15.8745
Sortino = 9.52
```

### Expected Output:
```
sortino = 9.52
```

### Code Verification:
```python
returns_pct = pd.Series([0.02, -0.01, 0.03, -0.02, 0.01])
m = PerformanceMetrics()
sortino = m.sortino_ratio(returns_pct, risk_free_rate=0.0, target=0.0)

assert 9.0 < sortino < 10.0, f"Expected ~9.52, got {sortino}"
```

### BUG CHECK:
If old buggy code calculated downside incorrectly:
```python
# WRONG - using only negative returns
downside_returns = returns_pct[returns_pct < target]
# Should use min(return - target, 0) for ALL returns
```

---

## TEST 9: Calmar Ratio (CAGR vs Max DD %)

### Inputs:
```
Starting capital: $100,000
Cumulative P&L: [500, 1200, 800, 2000, 1500, 2500]
Days: 252 (1 year)
```

### Manual Calculation:
```
Step 1: Portfolio value series
Day 0: 100,000 (start)
Day 1: 100,500
Day 2: 101,200
Day 3: 100,800  ← local peak at 101,200, DD starts
Day 4: 102,000  ← new peak, DD recovered
Day 5: 101,500
Day 6: 102,500  ← final

Step 2: Calculate CAGR
Starting: 100,000
Ending: 102,500
Total return: (102,500 / 100,000) - 1 = 0.025 = 2.5%
Period: 252 days = 1 year
CAGR = 2.5% (for 1 year, CAGR = total return)

Step 3: Max drawdown percentage
Running max: [100000, 100500, 101200, 101200, 102000, 102000, 102500]
Portfolio:   [100000, 100500, 101200, 100800, 102000, 101500, 102500]
Drawdown %:  [0%, 0%, 0%, -0.395%, 0%, -0.490%, 0%]

Max DD% = -0.490% = -0.00490

Step 4: Calmar ratio
Calmar = CAGR / abs(MaxDD%)
Calmar = 0.025 / 0.00490
Calmar = 5.10
```

### Expected Output:
```
calmar = 5.10
```

### Code Verification:
```python
cumulative_pnl = pd.Series([500, 1200, 800, 2000, 1500, 2500])
m = PerformanceMetrics(starting_capital=100000, annual_factor=252)
pnl = pd.Series([500, 700, -400, 1200, -500, 1000])  # Daily P&L

calmar = m.calmar_ratio(pnl, cumulative_pnl)

assert 5.0 < calmar < 5.5, f"Expected ~5.10, got {calmar}"
```

### BUG CHECK:
If old buggy code used dollars vs dollars:
```python
# WRONG - unit mismatch
cagr_dollars = cumulative_pnl.iloc[-1] / len(cumulative_pnl)
max_dd_dollars = abs(max_drawdown(cumulative_pnl))
calmar = cagr_dollars / max_dd_dollars  # Nonsense units
```

---

## TEST 10: Drawdown Recovery Time

### Inputs:
```
Cumulative P&L: [0, 100, 200, 150, 100, 180, 220, 250]
Dates: ['2020-01-01', '2020-01-02', ..., '2020-01-08']
```

### Manual Calculation:
```
Running max: [0, 100, 200, 200, 200, 200, 220, 250]
Drawdown:    [0,   0,   0, -50, -100, -20,   0,   0]

Maximum drawdown:
Value: -100 (at index 4, date 2020-01-05)
Started: index 2 (date 2020-01-03, peak of 200)
Recovered: index 6 (date 2020-01-07, back to 220 > 200)

Recovery time: 6 - 2 = 4 days
```

### Expected Output:
```
max_dd_value = -100
max_dd_date = '2020-01-05'
dd_recovery_days = 4
dd_recovered = True
```

### Code Verification:
```python
dates = pd.date_range('2020-01-01', periods=8)
cumulative_pnl = pd.Series([0, 100, 200, 150, 100, 180, 220, 250], index=dates)
m = PerformanceMetrics()

dd = m.drawdown_analysis(cumulative_pnl)

assert dd['max_dd_value'] == -100, f"Expected -100, got {dd['max_dd_value']}"
assert dd['dd_recovery_days'] == 4, f"Expected 4, got {dd['dd_recovery_days']}"
assert dd['dd_recovered'] == True, f"Expected True, got {dd['dd_recovered']}"
```

### BUG CHECK:
If old buggy code used wrong variable name:
```python
max_dd_idx = drawdown.argmin()  # Defined as max_dd_idx
...
'max_dd_date': cumulative_pnl.index[max_dd_position]  # WRONG - undefined variable
# NameError: name 'max_dd_position' is not defined
```

---

## SUMMARY OF MANUAL VERIFICATION

### Test Results:

| Test | Component | Expected | Status |
|------|-----------|----------|--------|
| 1 | Sharpe ratio | 9.47 | ✅ Can verify |
| 2 | Profile_5 strike | 327 | ✅ Can verify |
| 3 | Expiry DTE | 2020-01-10 | ✅ Can verify |
| 4 | Greeks multiplier | 50.0 | ✅ Can verify |
| 5 | Peak detection | 2 or 3 | ✅ Can verify |
| 6 | Pct captured (loss) | -400% | ✅ Can verify |
| 7 | Entry timing | T+1 | ✅ Can verify |
| 8 | Sortino ratio | 9.52 | ✅ Can verify |
| 9 | Calmar ratio | 5.10 | ✅ Can verify |
| 10 | DD recovery | 4 days | ✅ Can verify |

### Verification Method:
1. Run each test case
2. Compare actual output to manual calculation
3. Assert values within acceptable tolerance (±1% for floating point)
4. Document any deviations

### Next Steps:
1. Create Python script to run all 10 tests
2. Generate test output report
3. Flag any tests that fail
4. Investigate failures (bug or calculation error?)

---

**Manual verification complete. All 10 test cases have detailed calculations.**
**Ready to implement as unit tests.**
