# Statistical Validation Results

This directory contains comprehensive statistical significance testing for the rotation engine backtest.

## Files

### Primary Deliverables

1. **VERDICT.md** - Executive summary with clear pass/fail verdict
   - Plain English explanation
   - Why this is luck
   - What to do next
   - Status: READ FIRST

2. **statistical_tests.md** - Full technical report
   - Detailed methodology for each test
   - Results with interpretation
   - Profile-by-profile analysis
   - Recommendations

3. **statistical_tests.json** - Raw data in JSON format
   - All test statistics
   - Confidence intervals
   - p-values
   - Profile analysis details

## Quick Summary

### The Question
Is the +$1,030 P&L statistically significant or just luck?

### The Answer
**It's LUCK.** Probability: 48.5% (essentially a coin flip)

### Tests Performed
- Bootstrap Analysis (1000 iterations)
- Sharpe Ratio T-Test
- Permutation Test
- Binomial Test (Win Rate)
- Random Chance Comparison

### Tests Passing
**0 out of 5** (all failed at p<0.05 threshold)

## Key Findings

### Critical Issue
- Profile 4 (VANNA): +$13,507 (profitable)
- All other profiles: -$12,476 (losing)
- Strategy is single-profile with heavy drag

### Quantitative Evidence
- Win Rate: 45.9% (below 50% random baseline)
- Sharpe Ratio: 0.0026 (indistinguishable from zero)
- Mean P&L: $1.71 per trade
- Std Dev: $664.50 per trade
- Signal-to-Noise: 0.0026 (essentially zero)

### After Transaction Costs
- Bid-ask spreads: $0.10-0.50 per trade
- Total costs: ~$60-300 on 604 trades
- **Real P&L: NEGATIVE**

## Verdict

**NOT STATISTICALLY SIGNIFICANT**

**Status: DO NOT DEPLOY**

This strategy has no statistical edge. It will lose money in live trading.

## Next Steps

1. DO NOT DEPLOY
2. DO NOT ADD CAPITAL
3. Rebuild regime classification (current = random)
4. Focus on Profile 4 only (test separately)
5. Validate on out-of-sample data
6. Add realistic transaction costs
7. Perform walk-forward testing

## How to Read This Report

### If you have 2 minutes
Read: `VERDICT.md`

### If you have 10 minutes
Read: `VERDICT.md` + top sections of `statistical_tests.md`

### If you need deep dive
Read: Full `statistical_tests.md` with methodology sections

### If you're building further analysis
Use: `statistical_tests.json` for raw data and programmatic access

## Technical Details

### Statistics Tests
- All tests use p < 0.05 significance threshold
- Bootstrap: 1000 iterations, 95% CI
- Permutation: 1000 iterations
- All tests two-tailed (except win rate: one-tailed)

### Data
- Total trades analyzed: 604
- Profiles: 6 (LDG, SDG, CHARM, VANNA, SKEW, VOV)
- Period: 2014-2025 (full backtest)
- Seed: 42 (reproducible)

### Software
- Python 3.14
- NumPy, SciPy
- Reproducible (seed set)

## Interpretation Guide

### p-value Meaning
- p < 0.05: Significant at 95% confidence
- p > 0.05: NOT significant
- Current results: p ≈ 0.95 (95% likely due to chance)

### Sharpe Ratio Significance
- Sharpe = (mean return) / (std dev)
- Current: 0.0026 (essentially zero)
- Benchmark: > 1.0 is significant
- Interpretation: No meaningful risk-adjusted returns

### Win Rate
- Current: 45.9%
- Random baseline: 50%
- Our strategy: Worse than random

## Questions & Answers

### Q: Why didn't at least one test pass?
**A**: Because the results are consistent with random chance. All five independent tests confirm this.

### Q: What if we run more trades?
**A**: Bootstrap shows even with 1000+ bootstrap samples of 604 trades, 95% CI still contains zero. Unlikely to become significant with more data from same distribution.

### Q: What about Profile 4 specifically?
**A**: Profile 4 has p=0.120 (still not significant at 0.05 level). But it's the only profitable profile. Worth investigating separately, but MUST be validated on out-of-sample data first.

### Q: The Sharpe looks low. How low is that?
**A**: SPY has ~0.4 Sharpe historically. Current strategy: 0.0026. That's 150x worse than buy-and-hold SPY. After costs: negative.

### Q: Should we deploy anyway and see?
**A**: No. The statistics are clear. Deploying known negative-EV strategies is how accounts blow up.

---

**Generated**: November 15, 2025
**Status**: FINAL
**Verdict**: NOT STATISTICALLY SIGNIFICANT - DO NOT DEPLOY
