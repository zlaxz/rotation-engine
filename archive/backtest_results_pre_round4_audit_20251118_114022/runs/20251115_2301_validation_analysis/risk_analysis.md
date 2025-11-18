# ROTATION ENGINE - RISK ANALYSIS REPORT

**Date:** 2025-11-15
**Backtest Data:** `data/backtest_results/full_tracking_results.json`
**Trades Analyzed:** 604 across 6 profiles (LDG, SDG, CHARM, VANNA, SKEW, VOV)
**Account Size Modeled:** $1,000,000

---

## EXECUTIVE SUMMARY

**RISK VERDICT: HIGH RISK - Strategy requires optimization before live trading on $1M**

**Risk Score: 5/10** (where 2 = low, 4 = medium, 6+ = high)

**Key Findings:**
- 45.9% win rate (below 50% threshold) - most trades lose
- 1.01x profit factor (weak) - barely covers costs after transaction fees
- $5,498 max intra-trade drawdown (0.55% of $1M account)
- $23,172 portfolio drawdown across period (cluster risk detected)
- Average PnL per trade: $1.71 (negligible after trading costs)
- **Critical:** Strategy is currently unprofitable and highly vulnerable to execution slippage

---

## SECTION 1: TRADE STATISTICS

### Aggregate Performance
| Metric | Value |
|--------|-------|
| Total Trades | 604 |
| Winners | 277 (45.9%) |
| Losers | 327 (54.1%) |
| Avg Win | $537.63 |
| Avg Loss | -$452.27 |
| Largest Win | $3,455.80 |
| Largest Loss | -$3,490.20 |
| Total PnL | $1,030.20 |

### Interpretation
- **Win rate below 50%:** 45.9% means most individual trades lose money. This is a red flag.
- **Win/Loss Ratio 1.19x:** Slightly favorable (winners $538 vs losers $452), but not enough to overcome 55% loss frequency
- **Near-zero total PnL:** $1,030 on $803,823 deployed capital = 0.13% return. This is **entirely within noise from transaction costs** (typical options commissions/spreads).

**Risk Assessment:** ⚠️ **HIGH** - Strategy does not beat transaction costs in current form.

---

## SECTION 2: INTRA-TRADE DRAWDOWN ANALYSIS

### Drawdown Distribution
| Metric | Value |
|--------|-------|
| Max Intra-Trade DD | -$5,498.00 |
| Median Intra-Trade DD | -$573.50 |
| Mean Intra-Trade DD | -$813.58 |
| Std Dev | $757.10 |

### Top 5 Worst Intra-Trade Drawdowns
1. **Profile_6_VOV (2025-04-01):** -$5,498 DD, final PnL +$920 (recovered)
2. **Profile_3_CHARM (2025-02-20):** -$5,361 DD, final PnL -$3,490 (realized loss)
3. **Profile_3_CHARM (2022-05-27):** -$5,210 DD, final PnL -$3,162 (realized loss)
4. **Profile_6_VOV (2022-09-12):** -$4,838 DD, final PnL +$2,510 (recovered)
5. **Profile_3_CHARM (2022-01-05):** -$4,214 DD, final PnL -$868 (realized loss)

### Key Observations
- Worst-case intra-trade loss: **-$5,498** (from entry cost ~$1,330 = 4.1x multiple)
- Profile_3_CHARM shows clustering of large drawdowns - profile may have structural risk
- Some trades recover from huge drawdowns (VOV profile shows resilience)
- Median drawdown of -$574 means 50% of trades hit at least this level

**Risk Assessment:** ⚠️ **MEDIUM-HIGH** - Drawdowns are moderate but concentrated in certain profiles

---

## SECTION 3: POSITION SIZING FOR $1M ACCOUNT

### Current Estimated Position Sizing
- **Median Entry Cost:** $1,465.60
- **Mean Entry Cost:** $1,330.83
- **Tests Run At:** Approximately $10K-$15K account (estimated)

### Scaling to $1M Account

#### Conservative Approach: 2% Max Loss Per Trade
**Target:** Lose no more than 2% of account ($20,000) on any single trade

**Calculation:**
```
Worst historical DD:    -$5,498
Target max loss:        -$20,000
Scale factor:           3.64x
Recommended position:   $4,841 (vs current avg $1,331)
```

**Position Size Recommendation: $3,000 - $5,000 per trade**

This allows scaling worst-case historical drawdown to acceptable 0.5% account risk.

#### Portfolio Heat Management
- **5% Portfolio Heat Limit:** $50,000 active risk
- **Average DD per position:** $813.58
- **Recommended simultaneous positions:** ~61 (unrealistic - portfolio would become unmanageable)
- **Practical limit:** 10-15 concurrent positions = $8K-$12K portfolio heat (manageable)

#### Execution Reality Check
**⚠️ CRITICAL ISSUE:** These position sizes assume ability to:
1. Buy/sell spreads at modeled entry prices (likely optimistic)
2. Execute at mid-market quotes without slippage
3. Close at mid-market on exit without deterioration

**Realistic impact of transaction costs:**
- Long straddles: $15-30 bid-ask spread per leg = $30-60 per trade
- At current 0.13% return, the strategy loses money to execution
- At scaled position size, loses would increase proportionally

---

## SECTION 4: PORTFOLIO-LEVEL STATISTICS

### Cumulative Performance
| Metric | Value |
|--------|-------|
| Total Capital Deployed | $803,823 |
| Total PnL | $1,030 |
| Return on Capital | 0.13% |
| Avg PnL per Trade | $1.71 |

### Portfolio Drawdown Analysis
| Metric | Value |
|--------|-------|
| Max Portfolio Drawdown | -$23,172 |
| Drawdown Duration | 593 trades |
| Pct of Portfolio (at $1M) | 2.3% |

**Key Finding:** The portfolio drawdown spans 593 of 604 trades (98% of period). This indicates:
- No sustained recovery period
- Strategy experiences clusters of losses interspersed with rare large wins
- Risk is NOT contained to individual trade periods

**Risk Assessment:** ⚠️ **HIGH** - Portfolio drawdown suggests regime detection is unreliable

---

## SECTION 5: RISK-ADJUSTED RETURNS

### Profitability Metrics
| Metric | Value | Benchmark |
|--------|-------|-----------|
| Win Rate | 45.9% | Target >55% |
| Profit Factor | 1.01x | Target >2.0x |
| Win/Loss Ratio | 1.19x | Target >1.5x |
| Avg Win | $537.63 | |
| Avg Loss | -$452.27 | |

**Interpretation:**
- **Profit Factor 1.01x** is critically weak. After trading costs (2-4 basis points typical):
  - Costs eat entire profit
  - Strategy becomes negative expected value in live trading
  - Rule of thumb: Need >1.5x to survive execution costs

### Risk Metrics
| Metric | Value | Interpretation |
|--------|-------|-----------------|
| Return Volatility | 49.94% | Extremely high |
| Sharpe Ratio (approx) | 0.005 | Zero risk-adjusted return |
| Max Consecutive Losses | 20 trades | Significant |

**Sharpe Ratio Analysis:**
- 0.005 Sharpe means: essentially random walk with slight positive drift
- A coin flip has ~0 Sharpe ratio
- This strategy is marginally above coin flip with 20x leverage (high volatility)
- **Benchmark:** Good strategies >0.5, Acceptable >0.2, Unacceptable <0.1

**Risk Assessment:** 🔴 **CRITICAL** - Risk-adjusted returns are insufficient

---

## SECTION 6: RISK ASSESSMENT FOR $1M ACCOUNT

### Risk Factor Scorecard

#### Factor 1: Win Rate (45.9% - Below 50%)
**Risk Level: HIGH** (+2 points)
- Below 50% win rate means majority of trades lose
- At current 45.9%, every 2 trades that lose eats profit from 3 winners
- Not recoverable with current P&L structure (1.19x ratio)

#### Factor 2: Max Intra-Trade Drawdown ($5,498 = 0.55% of $1M)
**Risk Level: OK** (0 points)
- Individual trade drawdowns are contained at 0.55% of account
- With position sizing of $4-5K, translates to 1.1% account risk (acceptable)
- Historically recovered in some cases (VOV profile)

#### Factor 3: Profit Factor (1.01x - Weak)
**Risk Level: HIGH** (+2 points)
- Profit factor 1.01x barely covers trading costs (estimated 1-2%)
- In live trading with realistic execution, strategy becomes unprofitable
- This is the **critical failure mode** - looks good in backtest, fails on first trade

#### Factor 4: Portfolio Drawdown ($23,172 = 2.3% of $1M)
**Risk Level: LOW** (0 points)
- Max portfolio DD is contained
- However, 593-trade duration suggests regime detection catches clusters poorly

#### Factor 5: Consecutive Losses (20 trades)
**Risk Level: MEDIUM** (+1 point)
- 20 consecutive losses means 10-15 days of drawdown
- Psychologically challenging for trader
- Risk of panic exit or over-trading to recover

### OVERALL RISK SCORE

**Total Score: 5 / 10**

- 0-2: LOW RISK ✅
- 3-4: MEDIUM RISK ⚠️
- 5-6: HIGH RISK 🔴
- 7-10: CRITICAL RISK ⛔

**This strategy is in HIGH RISK territory.**

---

## SECTION 7: CAN FAMILY AFFORD MAX DRAWDOWN?

### Scenario Analysis for $1M Account

#### Scenario A: Position Size $1,330 (Current Scale)
- Max loss per trade: -$5,498
- Concurrent positions: ~15
- Max portfolio loss in one day: -$82,470 (8.2% if all 15 hit simultaneously)
- Likelihood: Remote but possible in market stress

**Verdict:** Family could absorb 8% loss and recover. Not catastrophic.

#### Scenario B: Position Size $5,000 (Recommended Scale)
- Max loss per trade: -$5,498 (historical max)
- Concurrent positions: ~10 (at 5% heat limit)
- Max portfolio loss in one day: -$54,980 (5.5% if all 10 hit simultaneously)
- Likelihood: Remote but possible

**Verdict:** Family could absorb 5-6% loss. Still manageable for long-term account.

#### Scenario C: Stress Test - Market Dislocation
- What if intra-trade DD increases 50% (to -$8,247)?
- What if 5 positions all hit maximum loss simultaneously?
- Max loss: ~$41,235 (4.1% of account)

**Verdict:** Survivable but concerning.

### Critical Risk: Execution Slippage

**Biggest unknown:** Current backtest assumes perfect mid-market execution. In reality:

**Options bid-ask spreads:**
- SPY call spreads: $0.15-0.40 wide (typical)
- SPY put spreads: $0.20-0.50 wide (typical)
- Long straddles hit BOTH spreads on entry
- Exit same spreads (potentially worse)
- **Realistic execution cost: 3-5 cents per dollar of notional**

**Impact on $1M account:**
- Current profit: $1,030 on $803,823 deployed (0.13%)
- Execution costs: 3-5 basis points = $2,400-4,000
- **Strategy turns negative before first trade**

---

## SECTION 8: RED FLAGS & FAILURE MODES

### 🔴 Critical Red Flag: Negative Expected Value
- Strategy returns 0.13% vs. estimated 0.3-0.5% execution costs
- **In live trading, this strategy loses money on every position**
- This is not a minor issue - it's a structural failure

### 🔴 Critical Red Flag: Profile Concentration
- Profile_3_CHARM has 3 of top 5 worst drawdowns
- Profile_6_VOV has 2 of top 5 worst (but recovers)
- Profiles are NOT independent - suggests common failure mode
- Regime classification may be flawed

### ⚠️ High Flag: Win Rate Below 50%
- At 45.9%, every 11 trades: 5 lose, 6 win
- Winners must cover both losers AND trading costs
- Current structure: barely covers losers, nothing left for costs

### ⚠️ High Flag: Regime Misclassification
- Portfolio drawdown spans 98% of backtest period
- Suggests regime classifier either:
  - Not working correctly
  - Returns too frequently
  - Doesn't add value over baseline
- No sustained periods of profit/recovery

### ⚠️ Medium Flag: Profile Convexity Assumption
- Thesis assumes markets misprice convexity by regime
- Backtest doesn't validate this - just shows historical performance
- No out-of-sample test, no bootstrap validation
- High risk of curve-fit

---

## SECTION 9: RECOMMENDATIONS

### DO NOT TRADE until:

1. **Fix negative expected value problem**
   - Reduce commission costs (use market maker rebates?)
   - Improve entry/exit prices (better execution logic?)
   - Increase trade frequency or hold time (might not be possible)
   - Add transaction cost modeling to backtest (model slippage)

2. **Improve win rate to >55%**
   - Current 45.9% mathematically doomed with 1.19x ratio
   - Need either:
     - Better regime detection (only trade confirmed regimes)
     - Better entry timing (wait for higher probability setups)
     - Better exit logic (don't exit at time decay if peak not reached)

3. **Validate out-of-sample**
   - Run backtest on hold-out data (2024-2025)
   - Implement walk-forward validation
   - Check results are robust to parameter variation
   - Test on different underlyings (QQQ, IWM, etc.)

4. **Stress test execution**
   - Model realistic bid-ask spreads
   - Model slippage on exit
   - Test position sizing at actual liquidity levels
   - Run on low-volume days to see impact

5. **Profile-by-profile validation**
   - Profile_3_CHARM needs investigation - why so many large losses?
   - Profile_6_VOV - why does it recover from huge drawdowns?
   - Is one profile subsidizing others?

### IF you decide to trade anyway:

1. **Position Size Conservative**
   - Start at $2,000 per trade (not $5,000)
   - Max 5 concurrent positions ($10K portfolio heat)
   - Target: 1% max loss per trade

2. **Execution Discipline**
   - Do NOT chase entries - use limit orders only
   - Accept 20% of signals if you can't get fill
   - Exit at planned time - do not average down
   - Track actual execution vs. model (will be worse)

3. **Risk Management**
   - Hard stop: If portfolio DD hits -$40K, shut down
   - Regime validation: Only trade when regime confidence >70%
   - Monthly reviews: Calculate actual Sharpe, check for regime drift

4. **Be Prepared to Lose**
   - Worst case at $2K position size: -$20K first trade
   - Could lose 2% of account on 1-2 trades before pattern clear
   - Have capital buffer for this reality check

---

## SECTION 10: VERDICT FOR FAMILY

### Can You Afford This Strategy on $1M?

**Technical Answer:** YES
- Max intra-trade loss: $5,498 (0.55% of account)
- Max portfolio loss: $23,172 (2.3% during backtest period)
- Family could absorb either of these

**Practical Answer:** UNCERTAIN
- Strategy currently loses money to execution costs
- Execution slippage will reveal whether edge is real
- High probability strategy fails on live trading
- Better to validate on small account first

**Honest Answer:** NOT RECOMMENDED
- Risk score 5/10 (HIGH RISK)
- Backtest doesn't prove live trading edge
- Transaction cost reality not validated
- Multiple red flags (negative EV, low win rate, portfolio DD)

### Recommended Path Forward

1. **Phase 1 (Validation):** $10K account, $100 positions
   - Run 50 trades and measure actual execution
   - Is win rate really 45.9% or worse?
   - What are real costs?
   - Can you reach 50%+ win rate?

2. **Phase 2 (Proof):** Scale to $50K if Phase 1 positive
   - 200+ trades to validate regime detection
   - Check for regime drift (2024-2025 market is different)
   - Confirm 0.5%+ daily return target is achievable

3. **Phase 3 (Deployment):** Only if Phase 2 > 0.3% daily
   - Scale to $250K-$500K
   - NOT $1M until proven at scale

**Timeline:** 6-12 months of trading before $1M capital is appropriate

---

## APPENDIX: DATA QUALITY NOTES

### Source Data
- 604 trades across 6 profiles
- Period: 2014-2025 (11 years)
- Entry costs range: $500-$5,000 (median $1,466)
- Exit dates range: 4-60 days hold time (median ~14 days)

### Analysis Assumptions
- Transaction costs NOT included in backtest (critical gap)
- Bid-ask spreads assumed at mid-market (optimistic)
- No slippage modeling (optimistic)
- Regime classification assumed correct (unvalidated)
- Position correlations NOT analyzed
- Greeks calculations NOT validated

### Known Limitations
1. Backtest uses "good data" - live markets will be noisier
2. Entry prices are idealized (assuming passive limit orders filled)
3. Exit prices assume liquidity at any time (may not be true for OTM spreads)
4. No commission modeling (real cost: $1-5 per trade)
5. Portfolio heat assumes all positions hit simultaneously (unlikely but possible)

---

## CONCLUSION

**The Rotation Engine backtest shows a strategy that:**
- ✅ Has positive total PnL ($1,030)
- ✅ Keeps individual trade losses bounded
- ✅ Can be scaled to $1M account
- ❌ Loses money to transaction costs before trading
- ❌ Has 45.9% win rate (below minimum viability)
- ❌ Shows 1.01x profit factor (barely covers losers)
- ❌ Is untested on live market execution
- ❌ Has NOT been validated out-of-sample

**Risk Verdict: HIGH RISK - Requires validation before capital deployment**

**Recommendation: Start with $10K-$50K validation phase before considering $1M**

---

**Report Generated:** 2025-11-15
**Analysis Tool:** Python backtesting analysis
**Confidence Level:** HIGH (based on 604 trades over 11 years)

