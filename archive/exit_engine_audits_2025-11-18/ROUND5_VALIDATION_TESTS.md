# ROUND 5: VALIDATION PHASE - OVERFITTING DETECTION TESTS

**When to run:** After train period completes, BEFORE test period
**Purpose:** Detect if strategy is overfit to train period
**Framework:** Industrial overfitting detection protocols

---

## TEST 1: Out-of-Sample Sharpe Ratio Degradation

### What We're Testing
Does the strategy's risk-adjusted return degrade gracefully from train to validation?

### The Hypothesis
- **Robust strategy:** Sharpe ratio degrades 20-40% (natural)
- **Overfit strategy:** Sharpe drops >50% or goes negative

### How to Test

```python
import json
import numpy as np

# Load results
with open('data/backtest_results/train_2020-2021/results.json', 'r') as f:
    train_results = json.load(f)

with open('data/backtest_results/validation_2022-2023/results.json', 'r') as f:
    val_results = json.load(f)

def calculate_sharpe(returns, risk_free_rate=0.02):
    """Calculate annualized Sharpe ratio"""
    excess_returns = returns - risk_free_rate / 252  # Daily risk-free rate
    return np.sqrt(252) * np.mean(excess_returns) / np.std(excess_returns)

# Calculate degradation
train_sharpe = calculate_sharpe([...])  # From train results
val_sharpe = calculate_sharpe([...])    # From validation results

degradation_pct = (train_sharpe - val_sharpe) / train_sharpe * 100

print(f"Train Sharpe: {train_sharpe:.2f}")
print(f"Validation Sharpe: {val_sharpe:.2f}")
print(f"Degradation: {degradation_pct:.1f}%")

# Assessment
if degradation_pct < 0:
    print("⚠️  OOS better than IS (unlikely, check for errors)")
elif degradation_pct < 20:
    print("✅ Excellent: Minimal degradation")
elif degradation_pct < 40:
    print("✅ Acceptable: Moderate degradation")
elif degradation_pct < 50:
    print("⚠️  Warning: Significant degradation")
else:
    print("❌ SEVERE: Likely overfit")
```

### Pass/Fail Criteria

| Degradation | Assessment | Decision |
|------------|-----------|----------|
| < 20% | Excellent | ✅ Proceed |
| 20-40% | Acceptable | ✅ Proceed |
| 40-50% | Warning | ⚠️ Re-evaluate |
| > 50% | Severe | ❌ Abandon |
| Negative | Failure | ❌ Abandon |

---

## TEST 2: Per-Profile Degradation Analysis

### What We're Testing
Does each profile degrade similarly or do some collapse?

### The Hypothesis
- **Robust:** All profiles degrade 20-40% uniformly
- **Overfit:** Some profiles degrade severely while others don't

### How to Test

```python
import json
import pandas as pd

with open('data/backtest_results/train_2020-2021/results.json') as f:
    train = json.load(f)
with open('data/backtest_results/validation_2022-2023/results.json') as f:
    val = json.load(f)

# Create comparison table
profiles = list(train.keys())
degradation_data = []

for profile in profiles:
    train_peak = train[profile]['summary']['peak_potential']
    train_pnl = train[profile]['summary']['total_pnl']
    train_capture = train[profile]['summary']['median_pct_captured']

    val_peak = val[profile]['summary']['peak_potential']
    val_pnl = val[profile]['summary']['total_pnl']
    val_capture = val[profile]['summary']['median_pct_captured']

    peak_degrade = (val_peak - train_peak) / train_peak * 100 if train_peak > 0 else 0
    pnl_degrade = (val_pnl - train_pnl) / train_pnl * 100 if train_pnl > 0 else 0
    capture_degrade = (val_capture - train_capture) / train_capture * 100 if train_capture > 0 else 0

    degradation_data.append({
        'Profile': profile,
        'Train Peak': train_peak,
        'Val Peak': val_peak,
        'Peak Degrade %': peak_degrade,
        'Train PnL': train_pnl,
        'Val PnL': val_pnl,
        'PnL Degrade %': pnl_degrade,
        'Train Capture': train_capture,
        'Val Capture': val_capture,
        'Capture Degrade %': capture_degrade
    })

df = pd.DataFrame(degradation_data)
print(df.to_string())

# Calculate consistency
mean_degrade = df['Peak Degrade %'].mean()
std_degrade = df['Peak Degrade %'].std()
coefficient_of_variation = std_degrade / abs(mean_degrade)

print(f"\nDegradation Consistency:")
print(f"  Mean degradation: {mean_degrade:.1f}%")
print(f"  Std degradation: {std_degrade:.1f}%")
print(f"  Coefficient of variation: {coefficient_of_variation:.2f}")

if coefficient_of_variation < 0.3:
    print("  ✅ Consistent across profiles")
elif coefficient_of_variation < 0.6:
    print("  ⚠️  Moderate variation")
else:
    print("  ❌ Inconsistent - some profiles fail while others don't")
```

### Pass/Fail Criteria

| Pattern | Assessment | Decision |
|---------|-----------|----------|
| All profiles degrade 20-40% uniformly | Excellent | ✅ Pass |
| Most profiles degrade 20-40%, 1-2 outliers | Acceptable | ✅ Pass |
| Half profiles degrade, half collapse | Warning | ⚠️ Investigate |
| Most profiles collapse (>50% degrade) | Failure | ❌ Fail |
| Some profiles improve dramatically | Suspicious | ⚠️ Check for errors |

---

## TEST 3: Win Rate Stability

### What We're Testing
Does the percentage of profitable trades stay consistent?

### The Hypothesis
- **Robust:** Win rate degrades 5-15%
- **Overfit:** Win rate degrades >20% or flips sign

### How to Test

```python
import json

with open('data/backtest_results/train_2020-2021/results.json') as f:
    train = json.load(f)
with open('data/backtest_results/validation_2022-2023/results.json') as f:
    val = json.load(f)

# Calculate win rates
def calculate_win_rate(results):
    """Win rate from summary"""
    total_trades = results['summary']['total_trades']
    winners = results['summary']['winners']
    return (winners / total_trades * 100) if total_trades > 0 else 0

for profile in train.keys():
    train_wr = calculate_win_rate(train[profile])
    val_wr = calculate_win_rate(val[profile])

    degrade = train_wr - val_wr

    print(f"{profile}:")
    print(f"  Train: {train_wr:.1f}% win rate")
    print(f"  Valid: {val_wr:.1f}% win rate")
    print(f"  Change: {degrade:+.1f}%")

    if degrade > 20:
        print(f"  ⚠️  Large degradation")
    elif val_wr < 0:
        print(f"  ❌ Strategy became net negative")
    else:
        print(f"  ✅ Acceptable")
```

### Pass/Fail Criteria

- ✅ Win rate degrades <15%
- ⚠️ Win rate degrades 15-20%
- ❌ Win rate degrades >20% or flips sign

---

## TEST 4: Capture Rate Stability

### What We're Testing
Does the strategy capture consistent percentage of peak potential?

### The Hypothesis
- **Robust:** Capture rate degrades 10-30%
- **Overfit:** Capture rate degrades >40% or flips sign

### How to Test

```python
import json

with open('data/backtest_results/train_2020-2021/results.json') as f:
    train = json.load(f)
with open('data/backtest_results/validation_2022-2023/results.json') as f:
    val = json.load(f)

for profile in train.keys():
    train_capture = train[profile]['summary']['median_pct_captured']
    val_capture = val[profile]['summary']['median_pct_captured']

    degrade = train_capture - val_capture
    degrade_pct = (degrade / train_capture * 100) if train_capture > 0 else 0

    print(f"{profile}:")
    print(f"  Train: {train_capture:.1%} of peak")
    print(f"  Valid: {val_capture:.1%} of peak")
    print(f"  Degradation: {degrade_pct:+.1f}%")

    if val_capture < 0:
        print(f"  ❌ Exit strategy completely failed")
    elif degrade_pct > 40:
        print(f"  ⚠️  Large degradation")
    else:
        print(f"  ✅ Acceptable")
```

### Pass/Fail Criteria

- ✅ Capture degrades <20%
- ⚠️ Capture degrades 20-40%
- ❌ Capture degrades >40% or goes negative

---

## TEST 5: Trade Frequency Consistency

### What We're Testing
Does the strategy generate similar number of trades in different periods?

### The Hypothesis
- **Robust:** Trade frequency similar across periods (±30%)
- **Overfit:** Train period had many trades, validation has few (or vice versa)

### How to Test

```python
import json

with open('data/backtest_results/train_2020-2021/results.json') as f:
    train = json.load(f)
with open('data/backtest_results/validation_2022-2023/results.json') as f:
    val = json.load(f)

# Total trades per period
train_total = sum(r['summary']['total_trades'] for r in train.values())
val_total = sum(r['summary']['total_trades'] for r in val.values())

train_trading_days = 500  # ~2020-2021
val_trading_days = 500     # ~2022-2023

train_freq = train_total / train_trading_days
val_freq = val_total / val_trading_days

freq_ratio = val_freq / train_freq if train_freq > 0 else 0

print(f"Trade frequency:")
print(f"  Train: {train_freq:.1%} of days ({train_total} trades)")
print(f"  Valid: {val_freq:.1%} of days ({val_total} trades)")
print(f"  Ratio: {freq_ratio:.2f}x")

if 0.7 < freq_ratio < 1.3:
    print("  ✅ Consistent frequency")
elif 0.5 < freq_ratio < 1.5:
    print("  ⚠️  Moderate variation")
else:
    print("  ❌ Large variation - possible overfitting to entry selection")
```

### Pass/Fail Criteria

- ✅ Ratio 0.7-1.3 (within 30%)
- ⚠️ Ratio 0.5-1.5 (within 50%)
- ❌ Ratio <0.5 or >1.5 (large variation)

---

## TEST 6: Metric Sign Consistency

### What We're Testing
Do positive metrics stay positive and negative metrics stay negative?

### The Hypothesis
- **Robust:** Same sign across train and validation
- **Overfit:** Flips sign (profitable train → unprofitable validation)

### How to Test

```python
import json

with open('data/backtest_results/train_2020-2021/results.json') as f:
    train = json.load(f)
with open('data/backtest_results/validation_2022-2023/results.json') as f:
    val = json.load(f)

sign_flips = []

for profile in train.keys():
    train_pnl = train[profile]['summary']['total_pnl']
    val_pnl = val[profile]['summary']['total_pnl']

    train_capture = train[profile]['summary']['median_pct_captured']
    val_capture = val[profile]['summary']['median_pct_captured']

    # Check PnL sign flip
    if (train_pnl > 0 and val_pnl < 0) or (train_pnl < 0 and val_pnl > 0):
        sign_flips.append(f"{profile} PnL: {train_pnl:.0f} → {val_pnl:.0f}")

    # Check capture sign flip
    if (train_capture > 0 and val_capture < 0) or (train_capture < 0 and val_capture > 0):
        sign_flips.append(f"{profile} Capture: {train_capture:.1%} → {val_capture:.1%}")

if sign_flips:
    print("❌ SIGN FLIPS DETECTED (Severe overfitting indicator):")
    for flip in sign_flips:
        print(f"  {flip}")
else:
    print("✅ No sign flips - consistent direction across periods")
```

### Pass/Fail Criteria

- ✅ Zero sign flips across all metrics and profiles
- ❌ Any sign flip = severe overfitting indicator

---

## TEST 7: Statistical Validation (Optional but Recommended)

### What We're Testing
Is the strategy's performance statistically significant?

### The Hypothesis
- **Real edge:** Outperforms random by statistically significant margin
- **Luck:** Performance within noise range of random

### How to Test

**Invoke the `statistical-validator` skill:**

```bash
# This skill will run:
# 1. Bootstrap confidence intervals on Sharpe ratio
# 2. Permutation tests (shuffle entry signals randomly)
# 3. Calculate p-values
# 4. Report statistical significance
```

**Interpretation:**
- p-value < 0.05: Strategy has real edge
- p-value > 0.05: Could be due to luck
- 95% CI excludes zero: Significant
- 95% CI includes zero: Uncertain

---

## TEST 8: Degradation Pattern Analysis

### What We're Testing
Is the degradation pattern economically sensible?

### The Hypothesis
- **Sensible:** Degradation explained by market regime change (2022 was bear market)
- **Suspicious:** Random degradation with no logical explanation

### How to Test

```python
# Analyze 2022 market conditions
# 2022: SPY down ~18%, VIX up, vol expansion
# 2023: SPY up ~24%, VIX down, vol contraction

# Compare strategy performance to market conditions
print("Market Context Analysis:")
print("=" * 60)
print("Training period (2020-2021):")
print("  - 2020: COVID crash + recovery (high vol)")
print("  - 2021: Bull market (low vol)")
print()
print("Validation period (2022-2023):")
print("  - 2022: Bear market (-18%), vol expansion (vol spike)")
print("  - 2023: Recovery (+24%), vol normalization")
print()
print("Questions:")
print("1. Did strategy degrade more in 2022 than 2023?")
print("2. Is degradation explained by vol environment change?")
print("3. Did long vol strategies (LDG, etc) suffer in 2022?")
print("4. Did short vol strategies (CHARM) improve in 2022?")
print()
print("If answer is yes to all: Degradation is SENSIBLE")
print("If no clear pattern: Degradation is SUSPICIOUS")
```

### Pass/Fail Criteria

- ✅ Degradation explained by market regime (2022 was harder)
- ⚠️ Some unexplained degradation
- ❌ Degradation makes no economic sense

---

## OVERALL ASSESSMENT FRAMEWORK

### Combine All Tests

**Create a scorecard:**

```
VALIDATION PHASE OVERFITTING ASSESSMENT
========================================

Test 1: Sharpe Degradation     ✅ PASS / ⚠️ WARN / ❌ FAIL
Test 2: Per-Profile Degradation ✅ PASS / ⚠️ WARN / ❌ FAIL
Test 3: Win Rate Stability      ✅ PASS / ⚠️ WARN / ❌ FAIL
Test 4: Capture Rate Stability  ✅ PASS / ⚠️ WARN / ❌ FAIL
Test 5: Trade Frequency        ✅ PASS / ⚠️ WARN / ❌ FAIL
Test 6: Sign Consistency       ✅ PASS / ⚠️ WARN / ❌ FAIL
Test 7: Statistical Validation ✅ PASS / ⚠️ WARN / ❌ FAIL
Test 8: Degradation Pattern    ✅ PASS / ⚠️ WARN / ❌ FAIL

Total Passes: X / 8
Total Warnings: X / 8
Total Failures: X / 8

DECISION:
- 6+ PASS: ✅ PROCEED TO TEST PERIOD
- 4-5 PASS: ⚠️ MARGINAL - CONSIDER RE-ITERATION
- <4 PASS: ❌ ABANDON STRATEGY
```

---

## What NOT to Do During Validation

### ❌ Don't Re-Tune Parameters

**Wrong:** "Exit day for Profile 1 didn't work, let me change it to Day 6"

**Right:** Accept the result. If validation fails, go back to train period and investigate why median peak of 7 days doesn't work.

### ❌ Don't Run Validation Multiple Times

**Wrong:** Run validation, see results, run again with "better" parameters

**Right:** Run validation once with locked train parameters.

### ❌ Don't Pick and Choose Profiles

**Wrong:** "These 4 profiles worked, let me just trade those"

**Right:** Accept all profiles or none. Picking profitable ones after seeing results is data mining.

### ❌ Don't Move the Goal Posts

**Wrong:** "I thought Sharpe >1.0 was success, but 0.8 is fine too"

**Right:** Set acceptance criteria BEFORE seeing results.

### ❌ Don't Look for Excuses

**Wrong:** "Validation failed but the macro environment was weird"

**Right:** If it fails, it fails. Market regime changes are part of reality. Strategy needs to work anyway.

---

## Success Definition

**Validation passes if:**
1. Sharpe ratio degrades 20-40% (acceptable range)
2. All profiles degrade consistently (no outliers collapse)
3. Win rates stable (degradation <15%)
4. Capture rates stable (degradation <30%)
5. Trade frequency consistent (±30%)
6. No sign flips on major metrics
7. Results are statistically significant (optional)
8. Degradation pattern makes economic sense

**If all 8 tests pass:** Proceed to test period with confidence

**If 1-2 tests warn:** Marginal pass, acceptable but watch carefully

**If 3+ tests warn or 1+ tests fail:** Do not proceed, re-iterate or abandon

---

## Documents Created for This Phase

- `ROUND5_METHODOLOGY_AUDIT.md` - Full methodology assessment
- `ROUND5_EXECUTIVE_SUMMARY.md` - One-page verdict
- `ROUND5_EXECUTION_CHECKLIST.md` - Step-by-step execution
- `ROUND5_VALIDATION_TESTS.md` - This document

---

**Print this page during validation execution**

**Follow tests methodically - this is what separates real quant research from YouTube trading**
