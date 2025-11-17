# Red Team Engineering Protocol

**"We WILL NOT build it right the first try. There WILL be holes. GUARANTEED."**

## Philosophy

Every quant backtest lies. Our job is to find the lies before we risk capital.

The red team's mission: **Attack the backtest ruthlessly until it breaks or proves itself bulletproof.**

## The Red Team Squad

### Agent 1: `backtest-bias-auditor`
**Specialty:** Look-ahead bias, survivorship bias, data snooping

**Attack vectors:**
- ❌ Using future data in regime classification?
- ❌ Optimizing parameters on full dataset (should be walk-forward)?
- ❌ Cherry-picking time periods that work?
- ❌ Using information unavailable at trade time?
- ❌ Regime labels computed with future data?
- ❌ Greeks/IV calculated with end-of-day data for intraday decisions?

**Deliverables:**
- List of every potential look-ahead bias
- Severity rating (CRITICAL / HIGH / MEDIUM / LOW)
- Fix recommendations

---

### Agent 2: `overfitting-detector`
**Specialty:** Curve-fitting, parameter sensitivity, robustness

**Attack vectors:**
- ❌ Change regime thresholds ±10% → does edge disappear?
- ❌ Walk-forward performance degrades out-of-sample?
- ❌ Shuffle regime labels → does performance vanish (permutation test)?
- ❌ Too many free parameters (>20 = overfitting likely)?
- ❌ Sharpe ratio suspiciously high (>2.5 = probably overfit)?
- ❌ Regime compatibility weights optimized or hardcoded?

**Deliverables:**
- Parameter sensitivity analysis
- Walk-forward performance degradation chart
- Permutation test results (p-values)
- Overfitting risk score (0-100)

---

### Agent 3: `statistical-validator`
**Specialty:** Statistical significance, hypothesis testing

**Attack vectors:**
- ❌ Sharpe ratio statistically significant? (t-test, bootstrap CI)
- ❌ Regime transitions truly predictive? (vs descriptive)
- ❌ Multiple testing problem (testing 100 configs = 5 false positives expected)
- ❌ Regime autocorrelation (persistent or random walk)?
- ❌ Monte Carlo simulation (random strategy distribution)
- ❌ Are results better than random coin flip strategy?

**Deliverables:**
- Statistical significance tests (p-values, confidence intervals)
- Multiple testing corrections (Bonferroni, Holm-Bonferroni)
- Monte Carlo baseline (random strategy performance)
- Regime predictive power analysis

---

### Agent 4: `market-microstructure-expert`
**Specialty:** Transaction cost realism, execution quality

**Attack vectors:**
- ❌ Bid-ask spreads too narrow? (check against real SPY options data)
- ❌ Slippage underestimated? (market orders vs limit orders)
- ❌ Delta hedging costs realistic? (ES futures commissions × frequency)
- ❌ Liquidity constraints ignored? (can you get filled at size?)
- ❌ Pin risk, assignment risk, early exercise modeled?
- ❌ Spread widening in Breaking Vol regimes accounted for?
- ❌ After-hours execution assumptions unrealistic?

**Deliverables:**
- Realistic transaction cost model (bid-ask, slippage, commissions)
- Delta hedging cost analysis (frequency × cost)
- Liquidity impact analysis
- Execution quality report

---

### Agent 5: `strategy-logic-auditor`
**Specialty:** Implementation correctness, bugs

**Attack vectors:**
- ❌ Regime signals calculated correctly? (manual verification)
- ❌ Greeks computed correctly? (compare to known benchmarks)
- ❌ Position sizing math correct? (manual spot checks)
- ❌ Entry/exit prices using bid/ask correctly?
- ❌ Transaction costs applied consistently?
- ❌ Off-by-one errors in indexing?
- ❌ Timezone issues (options settle at different times)?

**Deliverables:**
- Manual verification of 10 random trades
- Greeks accuracy report (compare to benchmark)
- Logic audit checklist (all calculations verified)
- Bug report (if any found)

---

## The Gauntlet: 5-Phase Red Team Process

### Phase 1: BUILD
**Duration:** 1-2 weeks
**Agents:** `backtest-architect`, `options-strategy-builder`

**Deliverables:**
- 6-module backtesting harness implemented
- Running on 2020-2024 SPY data
- Initial results generated (Sharpe, returns, drawdowns)

---

### Phase 2: RED TEAM ATTACK (First Pass)
**Duration:** 3-5 days
**Agents:** All 5 red team agents **launched in parallel**

**Process:**
1. Launch all 5 agents simultaneously
2. Each agent attacks from their specialty
3. Agents generate findings reports
4. Aggregate all findings into master issue list
5. Triage by severity (CRITICAL → LOW)

**Expected outcome:** 10-30 issues found

---

### Phase 3: FIX & ITERATE
**Duration:** 1-2 weeks
**Process:**

For each CRITICAL/HIGH issue:
1. Understand the problem
2. Implement fix
3. Re-run backtest
4. Verify fix worked

**Expected outcome:** Cleaner backtest, lower performance (transaction costs more realistic)

---

### Phase 4: RED TEAM ATTACK (Second Pass)
**Duration:** 2-3 days
**Agents:** All 5 red team agents **again**

**Process:**
- Same 5 agents attack the FIXED version
- Look for new issues introduced by fixes
- Verify CRITICAL/HIGH issues are actually resolved

**Expected outcome:** 3-10 remaining issues (mostly MEDIUM/LOW)

**Gate:** Only proceed if <5 CRITICAL/HIGH issues remain

---

### Phase 5: STRESS TESTING
**Duration:** 3-5 days
**Agents:** `performance-analyst`, `monte-carlo-simulator`

**Stress tests:**
- 2020 crash (Feb-Mar 2020)
- 2021 melt-up low vol
- 2022 bear market
- 2023 choppy low vol
- Event weeks (FOMC, CPI)

**Cross-validation:**
- QQQ (tech-heavy)
- IWM (small cap)
- XLK (sector)

**Sensitivity tests:**
- 2× transaction costs
- Remove top 5 best days
- Delay delta hedging by 1 hour
- Add ±20bps random noise to fills

**Gate:** If backtest survives all stress tests → we have something real

---

## Success Criteria

### Backtest PASSES Red Team If:

**Bias audit:**
- ✅ Zero look-ahead bias
- ✅ Walk-forward validation throughout
- ✅ No cherry-picking

**Overfitting:**
- ✅ Parameter changes ±10% → Sharpe degrades <20%
- ✅ Walk-forward Sharpe within 30% of in-sample
- ✅ Permutation tests show p < 0.05

**Statistical significance:**
- ✅ Sharpe t-test p < 0.05
- ✅ Monte Carlo: outperforms 95% of random strategies
- ✅ Regime transitions have predictive power

**Transaction costs:**
- ✅ Bid-ask spreads match real SPY options data
- ✅ Slippage realistic (verified against paper trading)
- ✅ Delta hedging costs included

**Implementation:**
- ✅ Manual verification of 10 trades = all correct
- ✅ Greeks accuracy within 1% of benchmark
- ✅ No bugs found

**Stress testing:**
- ✅ Positive Sharpe in 4/5 market regimes tested
- ✅ Max drawdown <40%
- ✅ Cross-validation: similar performance on QQQ/IWM

### Backtest FAILS Red Team If:

**Any of:**
- ❌ Look-ahead bias found
- ❌ Walk-forward Sharpe <50% of in-sample (severe overfitting)
- ❌ Permutation tests p > 0.1 (not significant)
- ❌ Transaction costs underestimated by >30%
- ❌ Implementation bugs found in >10% of random checks
- ❌ Blows up in 2020 crash (drawdown >70%)

---

## Red Team Launch Protocol

**When backtest is ready for red team:**

```bash
# Launch all 5 red team agents in parallel
# Each agent gets full backtest code + results
# Each agent generates findings report

# Command (conceptual):
launch_red_team_gauntlet \
  --backtest-code ./src/ \
  --results ./data/backtest_results/ \
  --data ./data/processed/ \
  --agents backtest-bias-auditor,overfitting-detector,statistical-validator,market-microstructure-expert,strategy-logic-auditor \
  --parallel true \
  --severity-threshold HIGH
```

**Agents will:**
1. Analyze code and results independently
2. Generate findings reports (markdown)
3. Assign severity ratings
4. Recommend fixes
5. Return reports to coordinator (Prime)

**Coordinator (Prime) will:**
1. Aggregate all findings
2. Triage by severity
3. Present to user with fix recommendations
4. Track fixes and re-test

---

## Remember

**"There WILL be holes. GUARANTEED."**

The red team's job is to find them before we risk real capital.

Better to discover overfitting in backtest than in live trading with $100k at risk.

---

**Last Updated:** 2025-11-13
**Status:** PROTOCOL DEFINED - ready to deploy after backtest build
