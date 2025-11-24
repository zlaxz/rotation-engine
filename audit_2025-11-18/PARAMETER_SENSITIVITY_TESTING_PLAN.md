# Parameter Sensitivity Testing Plan

## Overview

This document details how to conduct rigorous parameter sensitivity testing to validate (or invalidate) the rotation engine's parameter choices.

---

## Test 1: Compression Range Threshold

**File:** `src/regimes/classifier.py`
**Current value:** `compression_range = 0.035` (3.5%)
**Concern:** 3 decimal places, suspiciously precise

### Test Protocol

```python
import subprocess
import json

test_values = [0.025, 0.030, 0.035, 0.040, 0.045]
results = {}

for compression_range in test_values:
    # 1. Edit classifier.py
    # 2. Run full backtest
    # 3. Record metrics

    results[compression_range] = {
        "sharpe": None,           # From backtest output
        "win_rate": None,         #
        "regime_3_frequency": None,  # % of days in Regime 3
        "total_pnl": None,
        "capture_rate": None
    }

# 4. Analyze results
baseline_sharpe = results[0.035]["sharpe"]

for value, metrics in results.items():
    degradation = (baseline_sharpe - metrics["sharpe"]) / baseline_sharpe * 100
    print(f"compression_range={value:.3f}: Sharpe degradation {degradation:+.1f}%")

# 5. Flag if degradation > 20% at ±10%
if results[0.0315]["sharpe"] < baseline_sharpe * 0.8:  # 20% threshold
    print("⚠️ OVERFIT FLAG: Parameter shows brittle sensitivity")
```

### Expected Outcomes

**Robust parameter (good sign):**
- Sharpe ratio relatively flat across values
- Degradation <10% at ±10% parameter change
- Regime 3 frequency stable

**Overfit parameter (red flag):**
- Sharpe peaks sharply at 0.035
- Degradation >20% at ±10%
- Regime 3 frequency collapses at adjacent values

### Interpretation

If compression_range fails this test, it indicates:
- Parameter was optimized to historical data
- System will not generalize to future data
- Regime 3 definition is brittle and SPY-specific

---

## Test 2: Slope Threshold

**File:** `src/regimes/classifier.py`
**Current value:** `slope_threshold = 0.005`
**Concern:** 3 decimal places, may be optimized to MA20 dynamics

### Test Protocol

```python
test_values = [0.0025, 0.005, 0.010, 0.015, 0.020]

for slope_threshold in test_values:
    # Edit classifier._is_compression() and similar methods
    # Run backtest
    # Record: Sharpe, Regime 1/2 frequency (trend detection quality)

# Analyze trend regime frequency
baseline = results[0.005]["regime_1_frequency"]
for value, metrics in results.items():
    delta = abs(metrics["regime_1_frequency"] - baseline)
    print(f"slope_threshold={value}: Trend detection frequency change {delta:+.1%}")
```

### Critical Check

Does changing slope_threshold affect trend detection quality?
- Regime 1 (Trend Up) should INCREASE in uptrends
- Regime 2 (Trend Down) should INCREASE in downtrends
- If frequency is insensitive: parameter is okay
- If frequency collapses: parameter is overfit

---

## Test 3: EMA Smoothing Span

**File:** `src/profiles/detectors.py`
**Current value:** `span=7` (recently changed from 3)
**Concern:** Changed in Nov 2025, suggests active parameter search

### Test Protocol

```python
test_values = [3, 5, 7, 10, 14]

for span in test_values:
    # Edit lines: df['profile_2_SDG'] = df['profile_2_SDG_raw'].ewm(span=span, adjust=False).mean()
    # Also: df['profile_5_SKEW'] = df['profile_5_SKEW_raw'].ewm(span=span, adjust=False).mean()
    # Run backtest
    # Record: Profile 2 and Profile 5 performance

baseline = results[7]["profile_2_pnl"]
for span, metrics in results.items():
    degradation = (baseline - metrics["profile_2_pnl"]) / abs(baseline) * 100
    print(f"EMA span={span}: Profile 2 PnL degradation {degradation:+.1f}%")
```

### Key Question

Why was 3 changed to 7? If 7 is genuinely better:
- Performance should improve cleanly
- Should work at span 5, 6, 8, 9 similarly
- Degradation at 3 should be substantial

If 7 was chosen through trial-and-error:
- Performance will peak sharply at 7
- Will degrade >20% at span 5 and 10
- This indicates overfitting to test data

---

## Test 4: Profile Score Thresholds

**File:** `src/profiles/detectors.py`
**Current:** Multiple thresholds used in sigmoid arguments

### Critical Thresholds

| Profile | Threshold | Parameter | Current |
|---------|-----------|-----------|---------|
| 1 (LDG) | RV/IV ratio | `sigmoid((rv_iv_ratio - 0.9) * 5)` | 0.9 |
| 1 (LDG) | IV rank | `sigmoid((0.4 - IV_rank) * 5)` | 0.4 |
| 2 (SDG) | RV/IV ratio | `sigmoid((rv_iv_ratio - 0.8) * 5)` | 0.8 |
| 2 (SDG) | Move size | `sigmoid((move_size - 1.0) * 3)` | 1.0 |
| 3 (CHARM) | IV/RV ratio | `sigmoid((iv_rv_ratio - 1.4) * 5)` | 1.4 |
| 3 (CHARM) | Range | `sigmoid((0.035 - range_10d) * 100)` | 0.035 |
| 4 (VANNA) | IV rank | `sigmoid((0.3 - IV_rank) * 5)` | 0.3 |
| 5 (SKEW) | Skew z-score | `sigmoid((skew_z - 1.0) * 2)` | 1.0 |
| 5 (SKEW) | RV/IV ratio | `sigmoid((rv_iv_ratio - 1.0) * 5)` | 1.0 |
| 6 (VOV) | VVIX | `sigmoid((vvix_ratio - 1.0) * 5)` | 1.0 |
| 6 (VOV) | IV rank | `sigmoid((0.5 - IV_rank) * 5)` | 0.5 |
| 6 (VOV) | RV/IV | `sigmoid((1.0 - rv_iv_ratio) * 5)` | 1.0 |

### Test Protocol for Each Threshold

```python
# Example: Profile 1 IV_rank threshold (currently 0.4)
test_values = [0.3, 0.35, 0.4, 0.45, 0.5]

for iv_rank_threshold in test_values:
    # Edit: factor2 = sigmoid((iv_rank_threshold - df['IV_rank_20']) * 5)
    # Run backtest, recording Profile 1 performance
    # Measure Sharpe, win_rate for Profile 1 only

# Question: Does Profile 1 sharpe peak sharply at 0.4?
# If yes: Overfit to this data
# If no: Threshold is robust
```

### Testing Priority

**High priority** (most suspicious):
1. Profile 1 IV_rank = 0.4
2. Profile 3 IV/RV = 1.4
3. Profile 6 IV_rank = 0.5

**Medium priority:**
4. Profile 2 move_size = 1.0
5. Profile 5 skew_z = 1.0

**Low priority** (seem reasonable):
6. Profile 4 IV_rank = 0.3 (this profile works, so threshold likely good)

---

## Test 5: Sigmoid Steepness Parameters (k values)

**File:** `src/profiles/detectors.py`
**Current:** k values range from 2 to 1000
**Concern:** Extreme values (k=1000) create near-step functions

### Examples of Extreme k Values

```python
# Profile 2, Factor 3 (VVIX slope)
factor3 = sigmoid(df['VVIX_slope'] * 1000)  # Equivalent to: if VVIX_slope > 0 then 1.0 else 0.0

# Profile 3, Factor 3 (VVIX declining)
factor3 = sigmoid(-df['VVIX_slope'] * 1000)  # Equivalent to: if VVIX_slope < 0 then 1.0 else 0.0
```

### Test Protocol

For each extreme k value, test sensitivity:

```python
for k in [100, 500, 1000, 1500, 2000]:
    # Edit: factor3 = sigmoid(df['VVIX_slope'] * k)
    # Run backtest
    # Record profile performance

# Question: Does changing k=1000 to k=500 affect results significantly?
# If yes: k was micro-optimized
# If no: k=1000 and k=100 are equivalent (both are thresholds)
```

### Interpretation

If k=1000 is truly optimal vs k=500:
- Suggests system was tuned to find exact cliff point
- Indicates overfitting to volatility dynamics of 2020-2024

If k=500 and k=1000 give similar results:
- Both are threshold-like
- Could replace with deterministic if/then logic
- Would be more interpretable

---

## Test 6: Regime Compatibility Matrix

**File:** `src/backtest/rotation.py`
**Current:** REGIME_COMPATIBILITY dictionary with 36 weights

### Sample Weights

```python
1: {  # Trend Up
    'profile_1': 1.0,  # Strong
    'profile_2': 0.0,  # Avoid
    'profile_3': 0.3,  # Weak
    'profile_4': 1.0,  # Strong
    'profile_5': 0.0,  # Avoid
    'profile_6': 0.2   # Weak
}
```

### Test Protocol

**Approach 1: Remove weak weights**

```python
# Set all weights < 0.5 to 0.0
# Question: Does backtest improve by removing weak profiles?

for regime in [1, 2, 3, 4, 5, 6]:
    for profile in [1, 2, 3, 4, 5, 6]:
        original = REGIME_COMPATIBILITY[regime][f'profile_{profile}']
        if original < 0.5:
            REGIME_COMPATIBILITY[regime][f'profile_{profile}'] = 0.0

# Run backtest
# If performance improves: weak weights were noise
# If performance degrades: weak weights provide value
```

**Approach 2: Equal weighting**

```python
# Set all non-zero weights to equal value
# Question: Is careful tuning necessary or is equal allocation fine?

for regime in [1, 2, 3, 4, 5, 6]:
    for profile in [1, 2, 3, 4, 5, 6]:
        if REGIME_COMPATIBILITY[regime][f'profile_{profile}'] > 0:
            REGIME_COMPATIBILITY[regime][f'profile_{profile}'] = 1.0

# Run backtest
# If performance similar: tuned weights don't matter
# If performance degrades significantly: weights are important
```

### Key Question

If regime-profile compatibility is truly important, the weights should reflect options theory principles (gamma, skew dynamics, etc.). If weights were optimized via trial-and-error, changing them slightly should break performance.

---

## Test 7: Walk-Forward Replication

**Goal:** Verify walk-forward failure is real and reproducible

### Protocol

```python
# Original test period: 2020-01-02 to 2024-12-31

# Test 1: Original split (what was done)
# Training: 2020-2021
# Test: 2022-2024
# Measure: Sharpe on 2022-2024 vs 2020-2024

# Test 2: Different split
# Training: 2020-2022
# Test: 2023-2024
# Measure: Sharpe on 2023-2024 vs 2020-2024

# Test 3: Earlier data
# Training: 2015-2019
# Test: 2020-2024
# Measure: Sharpe on 2020-2024

# Test 4: Rolling window (most rigorous)
# For each month in 2022-2024:
#   Training: Previous 12 months
#   Test: Next 1 month
#   Record: Monthly Sharpe
# Analyze: What fraction of months beat buy-and-hold?
```

### Expected Results

**If system has edge:**
- Test performance >70% of baseline
- Walk-forward Sharpe >0.5
- Consistency across different splits

**If system is overfit:**
- Test performance <50% of baseline
- Walk-forward Sharpe <0.1
- Performance varies wildly across splits

---

## Test Execution Order

1. **Phase 1 (Week 1):** Tests 1-3 (threshold parameters)
2. **Phase 2 (Week 2):** Tests 4-5 (profile scores, sigmoid)
3. **Phase 3 (Week 3):** Test 6 (compatibility matrix)
4. **Phase 4 (Week 4):** Test 7 (walk-forward replication)

---

## Success Criteria

### Minimum Standards to NOT Flag as Overfit

- **Threshold sensitivity:** ±10% parameter change → <10% Sharpe degradation
- **Profile isolation:** Each profile's Sharpe remains stable within ±20% across parameter changes
- **Walk-forward:** Training Sharpe → Test Sharpe drop <30%
- **Regime frequency:** Changing threshold ±20% changes regime frequency <5%

### Red Flags (Evidence of Overfitting)

- **Parameter shows cliff:** Sharpe peaks sharply at one value, falls off quickly
- **Sensitivity >20%:** Changing parameter ±10% degrades Sharpe >20%
- **Walk-forward failure:** Test Sharpe <70% of training Sharpe
- **Weight optimization:** Changing compatibility weights <10% breaks performance

---

## Tools & Infrastructure

### Required Code Modifications

**1. Parameterized backtest runner:**
```python
def run_backtest_with_params(
    compression_range=0.035,
    slope_threshold=0.005,
    ema_span=7,
    # ... other params
):
    # Run full backtest with custom parameters
    # Return: results dict with Sharpe, win_rate, PnL, etc.
    pass
```

**2. Sensitivity analysis wrapper:**
```python
def test_parameter_sensitivity(param_name, test_values):
    # For each value, run backtest
    # Return: results keyed by parameter value
    # Plot: degradation vs parameter
    pass
```

**3. Results aggregation:**
```python
def aggregate_sensitivity_results(results_dir):
    # Collect all test results
    # Generate summary tables
    # Flag parameters with >20% sensitivity
    pass
```

### Output Format

For each test, generate:
1. **CSV table:** Parameter value, Sharpe, win_rate, etc.
2. **Line chart:** Sharpe vs parameter value
3. **Summary:** Robust parameters vs brittle parameters
4. **Red flags:** Any parameter showing overfitting evidence

---

## Conclusion

This testing plan will definitively answer:

1. **Are parameters overfit?** (Yes if >20% sensitivity)
2. **Which parameters are brittle?** (Compression range, slope?)
3. **Does compatibility matrix matter?** (Yes if weights optimize results)
4. **Is walk-forward failure real?** (Yes if replicable across time splits)

**Timeline:** 4 weeks to complete all tests
**Effort:** ~200 backtest runs
**Cost:** Computational (not monetary)

**Payoff:** Know definitively if system has real edge or is curve-fit to historical data.
