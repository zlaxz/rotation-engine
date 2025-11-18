# Walk-Forward Validation - Diagnostic Details

## Trade-by-Trade Analysis: Profile 4 VANNA (The Suspicious Winner)

Profile 4 shows +1094% improvement from training to testing. This is the most suspicious result.
Let's examine whether this is:
1. Real edge in different market regime
2. Luck/random walk
3. Data quality issue

### VANNA Entry/Exit Pattern Analysis

### Training Period (2020-2023) (71 trades)

| Month | Trades | Win Rate | Total P&L | Avg P&L |
|-------|--------|----------|-----------|----------|
| 2020-04 | 1 | 100% | $149 | $149 |
| 2020-05 | 2 | 100% | $980 | $490 |
| 2020-06 | 3 | 33% | $-641 | $-214 |
| 2020-07 | 4 | 100% | $2,048 | $512 |
| 2020-08 | 4 | 50% | $410 | $103 |
| 2020-10 | 3 | 33% | $-621 | $-207 |
| 2020-11 | 3 | 100% | $1,038 | $346 |
| 2020-12 | 4 | 75% | $576 | $144 |
| 2021-01 | 3 | 67% | $362 | $121 |
| 2021-02 | 3 | 0% | $-1,261 | $-420 |
| 2021-03 | 1 | 100% | $1,760 | $1760 |
| 2021-04 | 5 | 40% | $45 | $9 |
| 2021-05 | 1 | 0% | $-292 | $-292 |
| 2021-06 | 3 | 100% | $875 | $292 |
| 2021-07 | 4 | 100% | $1,139 | $285 |
| 2021-08 | 4 | 50% | $-559 | $-140 |
| 2021-09 | 1 | 0% | $-625 | $-625 |
| 2021-10 | 2 | 100% | $2,210 | $1105 |
| 2021-11 | 4 | 25% | $-466 | $-116 |
| 2021-12 | 1 | 0% | $-798 | $-798 |
| 2022-01 | 1 | 0% | $-1,122 | $-1122 |
| 2022-03 | 2 | 0% | $-1,150 | $-575 |
| 2022-04 | 2 | 0% | $-2,334 | $-1167 |
| 2022-06 | 1 | 0% | $-1,278 | $-1278 |
| 2022-07 | 2 | 100% | $3,839 | $1919 |
| 2022-08 | 4 | 0% | $-3,629 | $-907 |
| 2022-11 | 2 | 0% | $-1,104 | $-552 |
| 2022-12 | 1 | 0% | $-1,061 | $-1061 |

### Testing Period (2023-2024) (80 trades)

| Month | Trades | Win Rate | Total P&L | Avg P&L |
|-------|--------|----------|-----------|----------|
| 2023-01 | 2 | 100% | $1,130 | $565 |
| 2023-02 | 3 | 0% | $-2,812 | $-937 |
| 2023-04 | 4 | 25% | $-986 | $-246 |
| 2023-05 | 1 | 100% | $722 | $722 |
| 2023-06 | 4 | 100% | $3,078 | $770 |
| 2023-07 | 4 | 50% | $-32 | $-8 |
| 2023-08 | 1 | 0% | $-878 | $-878 |
| 2023-09 | 1 | 0% | $-934 | $-934 |
| 2023-11 | 3 | 100% | $1,937 | $646 |
| 2023-12 | 4 | 50% | $1,321 | $330 |
| 2024-01 | 4 | 100% | $3,400 | $850 |
| 2024-02 | 4 | 100% | $2,332 | $583 |
| 2024-03 | 4 | 50% | $-101 | $-25 |
| 2024-04 | 1 | 0% | $-1,107 | $-1107 |
| 2024-05 | 4 | 100% | $2,078 | $520 |
| 2024-06 | 2 | 100% | $1,116 | $558 |
| 2024-07 | 3 | 0% | $-2,743 | $-914 |
| 2024-08 | 2 | 0% | $-862 | $-431 |
| 2024-09 | 3 | 100% | $1,605 | $535 |
| 2024-10 | 4 | 75% | $250 | $63 |
| 2024-11 | 4 | 75% | $66 | $17 |
| 2024-12 | 1 | 0% | $-741 | $-741 |
| 2025-01 | 2 | 50% | $185 | $92 |
| 2025-05 | 5 | 80% | $3,475 | $695 |
| 2025-06 | 2 | 100% | $2,404 | $1202 |
| 2025-07 | 3 | 67% | $268 | $89 |
| 2025-08 | 2 | 50% | $135 | $67 |
| 2025-09 | 3 | 67% | $710 | $237 |


## Market Context: Why Does Out-of-Sample Win But In-Sample Lose?

### 2020-2022 Market Environment (Training Period - VANNA LOSES)
- **2020:** COVID crash → vol explosion → VVIX spikes → Vol structure inverted
- **2021:** Low vol grind → Skew expensive → VANNA suffers (short vega)
- **2022:** Bear market → Selloff vol → Vol crush in summer → VANNA loses

**Result: -$1,510 loss on 71 trades (50.7% win rate)**

### 2023-2024 Market Environment (Testing Period - VANNA WINS)
- **2023:** Post-SVB panic recovery → Tech rally → Vol crush into Q4
- **2024:** AI boom, carry trade expansion → LOW vol environment → VVIX collapses
- **Q1-Q3 2024:** Soft landing narrative → Vol term structure normal

**Result: +$15,017 profit on 80 trades (65% win rate)**

### Key Insight: VANNA is Vol-Crush Beneficiary
- Short vega (sells vol when it's high)
- When VVIX high (2020-2022): Strategy loses
- When VVIX low (2023-2024): Strategy wins
- **This is NOT an edge - it's regime correlation**

---

## Overfitting Signature Analysis

The results show classic overfitting symptoms:

### Symptom 1: In-Sample Optimization
- Multiple profiles had heavy losses in 2020-2022
- Suggests parameters were tuned on 2023-2024 expectations
- Or parameters optimized on high-vol period, fail in low-vol

### Symptom 2: Sign Reversals
- 3 profiles FLIP sign between periods
- CHARM: +$2,021 → -$3,072
- VANNA: -$1,510 → +$15,017
- VOV: -$7,448 → +$2,371
- Probability of 3 simultaneous sign flips by chance: < 1/8 (12.5%)
- **More likely: Different market regime exposed opposite side of curve-fit**

### Symptom 3: Worst Profile Becomes Best
- Profile 3 CHARM = highest in-sample Sharpe (1.24)
- Profile 3 CHARM = lowest out-of-sample Sharpe (-1.45)
- Classic curve-fitting: Optimized parameters on training period
- Then parameters fail spectacularly on test period

### Symptom 4: Sample Size Problem
- Profile 5 SKEW: Only 13 trades in test period
- Win rate plummets from 35% to 15%
- With 13 samples, normal variance = ±√13 = ±3.6 trades
- So win rate ±27.8pp is easily explained by chance

---

## Statistical Significance Reality Check

### Likelihood Analysis for Out-of-Sample Wins

**Profile 4 VANNA: +$15,017 on 80 trades**
- Mean per trade: $187.71
- Null hypothesis: zero edge (break-even)
- If positions are independent and market-neutral:
  - Probability of 65/80 wins (vs 50/50 chance): Binomial test p < 0.0001
  - **BUT:** This assumes no regime bias
  - **Actually:** Regime bias in 2023-2024 (bull market) makes 65% wins expected
  - Need to: Test against SPY return benchmark (does VANNA beat SPY long bias?)

**Profile 3 CHARM: +$2,021 training → -$3,072 testing**
- In-sample Sharpe: 1.24 (appears significant)
- Out-of-sample Sharpe: -1.45 (clearly spurious)
- **Verdict:** In-sample high Sharpe was false signal, not predictive power

### What We Need to Do

Before declaring statistical significance, need:
1. Bootstrap test: Are 65/80 wins significant? (control for regime)
2. Permutation test: Shuffle profile labels, do results persist?
3. Bonferroni correction: 6 profiles = p-value threshold 0.05/6 = 0.0083
4. Multiple testing: Original backtest had many parameters - need full correction

---

## Conclusion

**The walk-forward test reveals a strategy that is:**
1. **Regime-dependent** (not market-neutral)
2. **Curve-fit** (optimized on 2020-2022, reversed on 2023-2024)
3. **Lucky in out-of-sample period** (benefited from tech rally)
4. **Not robust** (fails multiple profiles, sign reversals)

**Next steps:**
- Run statistical-validator to quantify significance
- Run overfitting-detector to test parameter robustness
- Fix Profile 6 VOV bug and re-run backtest
- Consider if regime-filtered strategy works better

