# CYCLE 3: MONTE CARLO STRESS TEST

**Project:** Rotation Engine - Convexity Rotation Trading Strategy
**Date:** 2025-11-14
**Capital:** $1,000,000 (Real capital at risk)
**Status:** ⚠️ CRITICAL - DO NOT DEPLOY

---

## EXECUTIVE SUMMARY

### VERDICT: STRATEGY NOT VIABLE FOR DEPLOYMENT

**Critical Findings:**

1. **Baseline P&L:** $-37,632.15 (Negative)
2. **Probability of Profit:** 0.0%
3. **95th Percentile Drawdown:** -1.5%
4. **Probability of Ruin (<$100K):** 0.00%
5. **Transaction Cost Sensitivity:** EXTREME (strategy already unprofitable)

**Risk Assessment:**
- 🔴 CRITICAL: Expected return is NEGATIVE
- 🔴 CRITICAL: Already losing money at baseline costs
- 🔴 CRITICAL: Any cost increase makes losses worse
- 🔴 HIGH: Extremely narrow profitable parameter space
- 🔴 HIGH: High correlation risk (diversification may fail)

**Recommendation:** DO NOT DEPLOY. Fundamental redesign required.

---

## TEST 1: DRAWDOWN DISTRIBUTION

Bootstrapped 5,000 alternate return sequences to estimate drawdown distribution.

### Maximum Drawdown Percentiles

| Percentile | Max Drawdown |
|------------|--------------|
| 50th | -4.49% |
| 75th | -3.07% |
| 90th | -2.03% |
| 95th | -1.53% |
| 99th | -0.83% |

### Tail Risk

- **P(DD > 50%):** 0.00%
- **P(DD > 70%):** 0.00%
- **P(Ruin < $100K):** 0.00%

### Terminal Capital

- **Median:** $961,931.55
- **Mean:** $962,570.23
- **Starting Capital:** $1,000,000.00

⚠️ **WARNING:** Median terminal capital is BELOW starting capital.
Expected outcome is LOSS of capital.

---

## TEST 2: PARAMETER UNCERTAINTY

Tested 1,000 random parameter combinations (±20% variation).

### Results

- **Median Sharpe Ratio:** -0.19
- **P(Sharpe > 0):** 0.0%
- **P&L 5th Percentile:** $-37,756.29
- **P&L 95th Percentile:** $-37,506.71

⚠️ **CRITICAL:** Less than 50% of parameter space is profitable.
Strategy is EXTREMELY FRAGILE to parameter uncertainty.

---

## TEST 3: MARKET REGIME SCENARIOS

Tested 4 extreme market scenarios:

| Scenario | Description | Adjusted P&L | Survives? |
|----------|-------------|--------------|-----------|
| Scenario 1: 2008 Crash | VIX 80, SPY -40% in 6 months | $-42,492 | ✅ YES |
| Scenario 2: 2017 Grind | VIX 10, SPY +20% steadily | $3,425 | ✅ YES |
| Scenario 3: 2022 Bear | VIX 25-35, SPY -20% grind | $-20,739 | ✅ YES |
| Scenario 4: Flash Crash | SPY -10% single day | $-94,250 | ✅ YES |

**Scenarios Survived:** 4/4


---

## TEST 4: TRANSACTION COST SENSITIVITY

Tested strategy performance at various transaction cost levels.

| Cost Multiplier | Adjusted P&L | Status |
|-----------------|--------------|--------|
| 1.0x | $-37,632.15 | Break-even |
| 1.5x | $-37,648.45 | Break-even |
| 2.0x | $-37,664.75 | Break-even |
| 2.5x | $-37,681.05 | Break-even |
| 3.0x | $-37,697.35 | Break-even |
| 4.0x | $-37,729.95 | Break-even |
| 5.0x | $-37,762.55 | Break-even |

⚠️ **CRITICAL:** Strategy is already unprofitable at baseline costs (1.0x).
Any increase in transaction costs makes losses worse.

---

## TEST 5: CORRELATION SCENARIOS

Tested impact of increased profile correlation during crisis.

| Scenario | Correlation | Sharpe Impact |
|----------|-------------|---------------|
| Low correlation (0.2) | 0.2 | 1.20x |
| Medium correlation (0.5) | 0.5 | 1.08x |
| High correlation (0.8) | 0.8 | 1.03x |
| Perfect correlation (1.0) | 1.0 | 1.00x |

**Finding:** If profiles become highly correlated (>0.8), diversification
benefit is lost and Sharpe ratio degrades by ~50%.

---

## TEST 6: BLACK SWAN EVENTS

Tested portfolio resilience to extreme tail events.

| Event | Loss | Probability/Year | Expected Loss |
|-------|------|------------------|---------------|
| Trading Halt (3 days) | $150,000 | 0.10% | $150 |
| Deep ITM Assignment | $100,000 | 1.00% | $1,000 |
| Overnight Gap (5%) | $250,000 | 2.00% | $5,000 |
| Data Feed Failure (2 days) | $80,000 | 0.50% | $400 |
| Broker Failure (1 week) | $200,000 | 0.20% | $400 |

**Total Expected Annual Loss:** $6,950.00

**Recommendations:**
- Keep 10-15% cash buffer for black swan events
- Have backup broker and data feeds
- Implement circuit breakers for extreme moves
- Never fully deploy capital (max 85%)

---

## TEST 7: SURVIVABILITY ANALYSIS

Estimated probability that capital stays above critical thresholds.

| Threshold | Probability |
|-----------|-------------|
| 90% capital | 98.0% |
| 75% capital | 100.0% |
| 50% capital | 100.0% |
| 25% capital | 100.0% |
| 10% capital (ruin) | 100.0% |

**Probability of Ruin (<$100K):** 0.00%

**Time to Recover:** CANNOT RECOVER (Negative expected return)

---

## TEST 8: STRATEGY FRAGILITY

Tested how many parameters need to be wrong for strategy to fail.

### Single Parameter 50% Wrong

Critical parameters tested with 50% error:
- Base spread: FAIL
- Slippage: FAIL
- Roll DTE: FAIL
- Max loss %: FAIL

⚠️ **CRITICAL:** Strategy fails if ANY single parameter is 50% wrong.

### Robustness Score: 0.0%

Only 0.0% of parameter space is profitable.

**Assessment:** FRAGILE - Very narrow profitable parameter space.

---

## RISK LIMITS & CAPITAL ALLOCATION GUIDANCE

### RECOMMENDED RISK LIMITS

**Given strategy is unprofitable, deployment is NOT recommended.**

If strategy were profitable (after fixes):

1. **Maximum Allocation:** 15% of total capital
2. **Stop-Loss:** -10% of allocated capital
3. **Daily VaR Limit:** 2% of allocated capital
4. **Maximum Drawdown:** -15% before pause/review
5. **Position Limits:**
   - Max 40% in any single profile
   - Max 25% in any single regime
   - Maintain 15% cash buffer

### CAPITAL ALLOCATION

**Starting Capital:** $1,000,000

| Allocation | Amount | Purpose |
|------------|--------|---------|
| Strategy Capital | $850,000 | Active trading |
| Cash Buffer | $150,000 | Black swan events, margin |

**NOTE:** Given current unprofitability, allocate $0 to strategy until fixed.

---

## WHAT NEEDS TO BE FIXED

Before this strategy can be deployed:

1. **Fix Fundamental P&L Issue**
   - Root cause analysis of negative returns
   - Validate profile scoring logic
   - Verify Greeks calculations
   - Check regime classification accuracy

2. **Reduce Transaction Costs**
   - Lower rotation frequency (add minimum hold period)
   - Better trade timing (avoid high-cost periods)
   - Consider alternative execution strategies

3. **Improve Robustness**
   - Widen profitable parameter space
   - Add regime filters (don't trade in unprofitable regimes)
   - Implement position sizing based on confidence

4. **Add Risk Management**
   - Circuit breakers for extreme moves
   - Dynamic position sizing based on volatility
   - Correlation-based position limits

---

## CONCLUSION

**Status:** ⚠️ STRATEGY NOT VIABLE

The rotation engine in its current form should NOT be deployed with real capital.
Expected outcome is LOSS of capital with high probability.

**Next Steps:**
1. Root cause analysis of negative returns
2. Fundamental strategy redesign
3. Re-run stress tests after fixes
4. Only deploy if:
   - Sharpe > 1.0 in backtest
   - >70% of parameter space profitable
   - Survives all extreme scenarios
   - Positive expected return with confidence >90%

**DO NOT DEPLOY UNTIL ALL CRITICAL ISSUES RESOLVED.**

---

*Report generated: 2025-11-14*
*Tool: monte_carlo_stress_test.py*
