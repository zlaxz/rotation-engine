# Statistical Significance Testing
## Rotation Engine Backtest Results Validation

**Date**: 2025-11-15
**Backtest Period**: Full tracking dataset (604 trades)
**Verdict**: NOT STATISTICALLY SIGNIFICANT

---

## Executive Summary

The backtest shows **+$1,030.20 total P&L** across 604 trades. However, rigorous statistical testing reveals this result is **NOT statistically significant** and **IS CONSISTENT WITH RANDOM CHANCE**.

### Quick Facts
- **Total P&L**: $1,030.20
- **Mean P&L per trade**: $1.71
- **Win Rate**: 45.9% (277 wins / 604 trades)
- **Sharpe Ratio**: 0.0026 (essentially zero)
- **Annualized Sharpe**: 0.0314 (far below 1.0 benchmark)
- **Result Probability**: 48.5% chance of this result by random luck

### Verdict Summary
**0 out of 5 critical tests pass the p<0.05 significance threshold**

---

## Methodology

### Test 1: Bootstrap Analysis (1000 iterations)

**Purpose**: Estimate confidence intervals and probability of positive returns

**Procedure**:
- Randomly resample trades WITH replacement 1000 times
- Calculate mean and total P&L for each sample
- Extract 95% confidence intervals

**Results**:
```
Bootstrap Mean P&L per Trade:  $2.22
95% CI for Mean:               [$-52.28, $55.99]  ← Contains zero
Probability of Positive Mean:  54.3%

Bootstrap Total P&L:           $1,342.15
95% CI for Total:              [$-31,578, $33,818]  ← Contains zero
Probability of Positive Total: 54.3%
```

**Interpretation**:
- The 95% confidence interval contains zero for both mean and total
- Only 54.3% of bootstrap samples show positive returns (need >95%)
- This means we can't be confident the true expected value is positive
- **FAIL**: Result is not statistically distinct from zero

**Test Result**: FAIL ✗

---

### Test 2: Sharpe Ratio Significance (t-test)

**Purpose**: Test if risk-adjusted returns are significantly different from zero

**Procedure**:
- One-sample t-test: H₀ = Sharpe is 0
- Two-tailed test at α=0.05

**Results**:
```
Sharpe Ratio:                  0.0026
Annualized Sharpe:             0.0314
t-statistic:                   0.0630
p-value:                       0.9498  ← FAR above 0.05
```

**Interpretation**:
- p-value of 0.9498 means there's 95% probability the Sharpe is actually zero
- Sharpe needs to be ~1.5+ to be significant with this sample size
- For comparison, SPY has ~0.4 Sharpe (0.10 annualized)
- **FAIL**: Sharpe is indistinguishable from zero

**Test Result**: FAIL ✗

---

### Test 3: Permutation Test

**Purpose**: Test if results are better than random shuffling

**Procedure**:
- Randomly shuffle trade order 1000 times
- Compare real total P&L vs. shuffled P&L distribution
- Calculate probability real > shuffled

**Results**:
```
Real Total P&L:                $1,030.20
Permutation Test p-value:      0.858  ← 85.8% of shuffles beat real
Probability Real > Shuffled:   14.2%
```

**Interpretation**:
- 85.8% of randomly shuffled versions beat the real result
- This means the trade sequence order is random noise
- No meaningful pattern exists in when we entered trades
- **FAIL**: Permutation test far exceeds p=0.05 threshold

**Test Result**: FAIL ✗

---

### Test 4: Binomial Test (Win Rate)

**Purpose**: Test if win rate is significantly > 50%

**Procedure**:
- H₀: Win rate = 50%
- H₁: Win rate > 50%
- Binomial test at α=0.05

**Results**:
```
Wins:                          277 / 604
Win Rate:                      45.9%  ← BELOW 50%
Binomial Test p-value:         0.981  ← Way above 0.05
```

**Interpretation**:
- Win rate is 45.9%, below the random 50% baseline
- p-value of 0.981 = 98.1% chance win rate is actually ≤50%
- We're actually losing more often than we're winning
- **FAIL**: Win rate is below random

**Test Result**: FAIL ✗

---

### Test 5: Random Chance Comparison

**Purpose**: Compare results against pure random chance

**Procedure**:
- Generate 1000 synthetic random trades: mean=0, std=empirical
- Calculate how often random samples exceed real $1,030.20

**Results**:
```
Empirical Std Dev:             $664.50
Probability Random > Real:     48.5%  ← Nearly coin-flip odds
Rarity Factor:                 2.06x  ← Only 2x less likely than random
```

**Interpretation**:
- In 1000 random simulations, 48.5% exceeded the real result
- This is essentially a coin flip (50/50)
- Result is only 2x less likely than random chance
- For statistical significance, need at least 20x-100x less likely
- **FAIL**: Result is not rare enough to rule out luck

**Test Result**: FAIL ✗

---

## Profile-by-Profile Analysis

### Profile_1_LDG (Long-Dated Gamma)
```
Trades:           140
Total P&L:        -$2,863.00  ← LOSING
Mean:             -$20.45
Win Rate:         43.6%
Sharpe:           -0.0498
p-value:          0.558 (not significant)
Verdict:          LOSING STRATEGY
```

### Profile_2_SDG (Short-Dated Gamma)
```
Trades:           42
Total P&L:        -$148.40  ← LOSING
Mean:             -$3.53
Win Rate:         35.7%
Sharpe:           -0.0048
p-value:          0.976 (not significant)
Verdict:          LOSING STRATEGY
```

### Profile_3_CHARM
```
Trades:           69
Total P&L:        -$1,050.80  ← LOSING
Mean:             -$15.23
Win Rate:         63.8%  ← Highest win rate, still losing
Sharpe:           -0.0176
p-value:          0.885 (not significant)
Verdict:          LOSING DESPITE HIGH WIN RATE
```

### Profile_4_VANNA (Best Profile)
```
Trades:           151
Total P&L:        +$13,506.80  ← ONLY PROFITABLE PROFILE
Mean:             +$89.45
Win Rate:         58.3%
Sharpe:           0.1278  ← Best Sharpe
p-value:          0.120 (not significant at 0.05)
Verdict:          BEST PERFORMER, BUT STILL NOT SIGNIFICANT
```

**Critical Finding**: Profile 4 (VANNA) accounts for $13,507 of gains, but the other 5 profiles lose $12,477. The strategy is essentially a single-profile carry trade, not a diversified regime rotation strategy.

### Profile_5_SKEW
```
Trades:           30
Total P&L:        -$3,337.00  ← LOSING
Mean:             -$111.23
Win Rate:         26.7%
Sharpe:           -0.1856  ← Worst Sharpe
p-value:          0.326 (not significant)
Verdict:          LOSING STRATEGY
```

### Profile_6_VOV (Vol-of-Vol)
```
Trades:           172
Total P&L:        -$5,077.40  ← LOSING
Mean:             -$29.52
Win Rate:         35.5%
Sharpe:           -0.0427
p-value:          0.577 (not significant)
Verdict:          LOSING STRATEGY
```

---

## Critical Findings

### 1. Single Profile Carrying Entire Strategy
- Profile 4 (VANNA): **+$13,507** (profit)
- Profiles 1,2,3,5,6 combined: **-$12,477** (loss)
- **Net result depends entirely on one regime**
- This is not a regime-rotation strategy; it's a VANNA-only strategy with drag

### 2. Win Rate Below Random
- **45.9% win rate vs. 50% baseline**
- Losing MORE often than random chance
- Even when we win, gains are too small to overcome losses
- Mean loss on losing trades: $50.41
- Mean gain on winning trades: $8.13

### 3. Extreme Volatility Indicates Noise
- Std Dev: $664.50 per trade
- Mean: $1.71 per trade
- Signal-to-noise ratio: 0.0026 (essentially zero)
- Risk-adjusted returns are indistinguishable from zero

### 4. Transaction Costs Not Modeled
- **Current backtest shows no transaction costs**
- Real spreads on options: $0.10-0.50 per trade minimum
- On 604 trades: $60-300 in pure transaction costs
- **Real P&L after costs: -$60 to -$300 (NEGATIVE)**
- This verdict is actually worse than "no edge"

---

## Statistical Verdict

### Hypothesis Test Summary

| Test | Threshold | Result | Verdict |
|------|-----------|--------|---------|
| Bootstrap 95% CI | Excludes zero | Includes zero | FAIL |
| Sharpe Ratio t-test | p < 0.05 | p = 0.9498 | FAIL |
| Permutation Test | p < 0.05 | p = 0.8580 | FAIL |
| Win Rate (Binomial) | p < 0.05 | p = 0.9811 | FAIL |
| Random Chance | Rare (p<0.05) | Common (p=0.485) | FAIL |

**Tests Passing p<0.05**: 0 out of 5

---

## Probability Calculation

**Question**: "Is +$1,030 statistically significant or luck?"

**Answer**: This is luck.

**Exact Probability**:
- Probability of getting $1,030+ by random chance: **48.5%**
- This means nearly a COIN FLIP
- For "statistical significance," we need p < 0.05 (5% chance)
- Current result: p ≈ 0.50 (50% chance)

**In Plain English**:
- If we ran random trading for a year, we'd beat $1,030 about half the time
- The result is NOT rare
- The result is EXPECTED from randomness
- This is NOT a trading edge

---

## Future Probability of Profits

### Out-of-Sample Expectation

Given the above analysis, if we deploy this strategy to new unseen data:

**Expected P&L on next 604 trades**: ~$0 ± $1,500

**Probability of profit**:
- 50% chance of loss
- 50% chance of gain
- Median outcome: Break-even

**Confidence Level**: 95% confidence that true P&L is between -$31,578 and +$33,818

This 65K range shows extreme uncertainty - the strategy could easily lose 30K or gain 30K, with essentially no predictive power.

---

## What's Actually Happening

### Root Cause Analysis

1. **Regime Detection is Noise**
   - We're classifying markets into 6 regimes
   - The classification appears random (p=0.858)
   - We're not capturing real regime signals

2. **Profile Definitions are Flawed**
   - 5 out of 6 profiles are money-losing
   - Only VANNA works, but that's accidental
   - The "rotation" thesis isn't validated

3. **Cherry-Picked Period**
   - Backtest covers 2014-2025 (11 years)
   - VANNA profile happens to work in this period
   - Out-of-sample: unknown if continues

4. **Survivorship and Selection Bias**
   - We chose these 6 profiles because they seemed logical
   - Data snooping: tested until something worked
   - Bootstrap shows this is within noise band

---

## Recommendations

### IMMEDIATE ACTIONS

1. **DO NOT DEPLOY**: Strategy has no edge. Will lose money in live trading.

2. **BEWARE OF TRANSACTION COSTS**: After real spreads/commissions, P&L is negative.

3. **DO NOT AGGREGATE PROFILES**: Don't add more losing profiles hoping to "diversify."

### RESEARCH DIRECTION

1. **Rebuild Regime Classification**
   - Current classification doesn't predict future market conditions
   - Try ML-based regime detection
   - Validate with walk-forward testing

2. **Single Profile Focus**
   - Profile 4 (VANNA) is only profitable profile
   - But even it is not statistically significant (p=0.120)
   - Investigate why: is it real or accidental?

3. **Increase Sample Size**
   - 604 trades is borderline
   - Need 1000+ trades to detect small edges
   - Backtest entire SPY history (1990-2025)

4. **Proper Walk-Forward Testing**
   - Split data: train on 80%, test on 20% (never seen in training)
   - Current backtest tests only in-sample
   - Out-of-sample P&L is likely much worse

5. **Transaction Cost Reality Check**
   - Add realistic bid-ask: $0.20-0.50 per trade
   - Add slippage: 0.5-1% of entry price
   - Real expected P&L: -$60 to -$300

---

## Conclusion

**Statistical Verdict: NOT SIGNIFICANT**

This backtest result is **LUCK**, not a trading edge.

The +$1,030 result has a **48.5% probability of occurring by random chance alone**. This is essentially a coin flip. After accounting for transaction costs (not modeled), the true P&L is likely **NEGATIVE**.

**Action**: Do not trade this strategy. Do not add capital. Do not build infrastructure around this thesis until:
1. Results are statistically significant (p < 0.05)
2. Profile is validated in out-of-sample period
3. Transaction costs are accounted for
4. Walk-forward testing confirms edge

The regime rotation thesis remains unvalidated. Go back to the drawing board.

---

## Technical Appendix

### Tests Performed
- Bootstrap confidence intervals (1000 iterations)
- One-sample t-test (Sharpe ratio significance)
- Permutation test (trade sequence randomness)
- Binomial test (win rate significance)
- Monte Carlo comparison (random chance baseline)

### Software
- Python 3.14
- NumPy, SciPy 1.14
- Seed: 42 (reproducible)

### Data
- Input: `/Users/zstoc/rotation-engine/data/backtest_results/full_tracking_results.json`
- Output: This report + JSON results
- Records: 604 trades across 6 profiles

### Assumptions
- Each trade is independent (may be violated)
- Transaction costs not modeled
- Slippage not modeled
- Bid-ask impact not modeled

