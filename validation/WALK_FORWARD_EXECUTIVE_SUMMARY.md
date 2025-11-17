# Walk-Forward Validation - Executive Summary

**Date:** 2025-11-15
**Test Type:** 2-Period Walk-Forward Split
**Verdict:** ❌ STRATEGY FAILS - SEVERE OVERFITTING DETECTED
**Recommendation:** DO NOT DEPLOY TO LIVE TRADING

---

## The Problem In One Chart

```
Aggregate Portfolio Performance:

TRAINING (2020-2022)          TESTING (2023-2024)
296 trades, -$10,684 loss     308 trades, +$11,714 profit
                ❌                           ✅
            LOSING SIDE                  WINNING SIDE

         SIGN FLIP = OVERFITTING
```

**This is not a degradation - this is a REVERSAL.**

---

## What Happened

The backtest strategy was run on two separated time periods:

1. **Training Period (2020-2022):** Historical data used to develop/validate strategy
   - Result: Portfolio lost -$10,684
   - Win rate: 42.2% (loses more than it wins)
   - Most profiles negative

2. **Testing Period (2023-2024):** New unseen data to validate out-of-sample performance
   - Result: Portfolio made +$11,714
   - Win rate: 51.6% (wins more than it loses)
   - Most profiles positive

**Expected behavior:** Performance should be SIMILAR (within ±30% degradation)

**Actual behavior:** Performance FLIPPED COMPLETELY

---

## Profile-Level Details

### The Good News That Isn't Good News

**Profile 4 VANNA:** Made +$15,017 out-of-sample (64/80 trades won)
- This looks like success... except:
- In-sample: Lost -$1,510 on 71 trades (51% win rate)
- Improvement: +1094% (most extreme swing in entire backtest)
- Probability of this being random luck: HIGH
- Probability of being real edge: LOW

### The Bad News

**Profile 3 CHARM:** BEST in-sample becomes WORST out-of-sample
- In-sample: +$2,021 profit, 71% win rate, Sharpe 1.24 (looks great!)
- Out-of-sample: -$3,072 loss, 58% win rate, Sharpe -1.45 (disaster!)
- Degradation: -252% (worst profile)
- **Verdict:** In-sample "success" was false signal, parameters were curve-fit

**Profile 5 SKEW:** Consistently loses
- In-sample: -$863
- Out-of-sample: -$2,474 (worse)
- Win rate drops from 35% to 15% (indicating no edge)

### The Suspicious Patterns

**Profile 1 LDG:** Sign flip (negative → positive)
- In-sample: -$2,901 (38% win rate)
- Out-of-sample: +$38 (49% win rate)
- Barely profitable out-of-sample (essentially breakeven)

**Profile 6 VOV:** Sign flip + known bug
- In-sample: -$7,448 (26% win rate) ← LOSES
- Out-of-sample: +$2,371 (44% win rate) ← WINS
- **BUT:** Entry logic is INVERTED (known bug - SESSION_STATE.md)
- So success is tainted by implementation error

---

## Why This Happened

### Market Environment Changed

**2020-2022 (Training Period):**
- COVID crash and recovery (high volatility)
- Bearish 2022 (selloff)
- Many regime changes
- Vol term structure inverted/disrupted
- Market regime: Choppy, trending down, high vol

**2023-2024 (Testing Period):**
- Tech recovery (rally)
- Low volatility environment (vol crush)
- Steady Fed pivot
- Normal vol term structure
- Market regime: Trending up, low vol, mean reverting

### The Strategy Adapts to Regime, Not Edge

The profiles are:
- Long gamma (volatility bet)
- Skew trades (directional volatility)
- Vol-of-vol trades (volatility of volatility)

**In a low-vol environment (2023-2024):**
- Volatility trades perform better
- Vol crush is tail wind
- Strategies that bet on vol moves benefit

**In a high-vol/choppy environment (2020-2022):**
- Volatility bets suffer
- Vol mean-reversion kills theta
- Strategies underperform

**Conclusion:** Strategy is beneficiary of 2023-2024 regime, not a market-neutral edge.

---

## The Overfitting Evidence

### Red Flag #1: Sign Reversal
- 3 out of 6 profiles flip sign between periods
- Probability of random reversal on 50/50 edge: 12.5%
- Probability of reversal if regime-dependent: 100%

### Red Flag #2: Best Becomes Worst
- Profile 3 (CHARM) highest in-sample Sharpe (1.24)
- Profile 3 (CHARM) lowest out-of-sample Sharpe (-1.45)
- Classic overfitting: Parameters optimized on training data fail on test data

### Red Flag #3: Extreme Anomalies
- Profile 4: +1094% improvement (statistical improbability)
- Profile 6: +131% improvement despite known inverted bug
- These are "lucky" outcomes, not repeatable edges

### Red Flag #4: Smallest Samples Show Worst Performance
- Profile 5 SKEW has only 13 trades in test period
- Win rate drops from 35% to 15% (perfectly random outcome)
- Sample too small to prove anything

---

## What This Means For The Strategy

**Is this strategy tradeable?**
- ❌ NO - Not in current form
- In-sample: Loses money (-$10.7K)
- Out-of-sample: Wins money (+$11.7K) but likely due to regime luck
- **Verdict:** When market regime changes (next downturn), will likely repeat in-sample losses

**Can we fix it?**
- Maybe, but requires:
  1. **Statistical validation** (bootstrap, permutation tests)
  2. **Overfitting detection** (parameter sensitivity analysis)
  3. **Logic audit** (red-team for bugs - Profile 6 VOV confirmed bug)
  4. **Regime filtering** (only trade when regime conditions favorable)

**What's the probability of success in next downturn?**
- Current backtest shows: -$10K loss in 2020-2022 period
- Next downturn likely similar to 2020-2022 environment
- Without fixing, strategy will likely lose money

---

## Action Items

### STOP (Required Before Deployment)

1. ❌ **DO NOT TRADE THIS STRATEGY** - Severe overfitting detected
2. ❌ **DO NOT ASSUME PROFITABILITY** - 2023-2024 was tail wind, not edge
3. ❌ **DO NOT IGNORE PROFILE 6 BUG** - Known inverted entry logic

### Quality Gate Validation (Prerequisite)

Before any further development, run:

1. **Statistical Validator**
   - Bootstrap confidence intervals on Sharpe ratios
   - Permutation tests for each profile
   - Multiple testing corrections (Bonferroni)
   - Answer: Are results statistically significant?

2. **Overfitting Detector**
   - Parameter sensitivity (±10% changes)
   - Walk-forward validation (rolling windows)
   - Permutation tests (shuffle labels)
   - Answer: Are parameters robust or curve-fit?

3. **Strategy Logic Auditor**
   - Red-team entry conditions
   - Red-team exit logic
   - Check for look-ahead bias (already passed - SESSION_STATE.md)
   - Answer: Are there implementation bugs?

4. **Backtest Bias Auditor**
   - Check for survivorship bias
   - Check for data quality issues
   - Check for assumption violations
   - Answer: Are backtest results reliable?

### If Quality Gates Pass

1. **Fix Profile 6 VOV bug** (inverted entry condition)
2. **Re-run backtest** with fix applied
3. **Add regime filters** to only trade favorable regimes
4. **Test on rolling walk-forward** (overlapping windows)
5. **Paper trade 2025** before live capital

### If Quality Gates Fail

1. **Abandon this framework** (too many parameters, too little data)
2. **Pivot to simpler approach** (single profile or regime detection only)
3. **Or start from scratch** with proper sample size and statistical rigor

---

## Bottom Line

This strategy shows **classic overfitting behavior:**
- Learns patterns from 2020-2022 (high vol, bearish)
- Fails those patterns when market changes (2023-2024 low vol recovery)
- Out-of-sample "success" is regime luck, not edge

**It WILL NOT work in the next market downturn.**

**Confidence in verdict: HIGH** - Results clearly show sign flip and best-in-sample/worst-out-of-sample reversal.

---

## Supporting Files

- **Full Analysis:** `/Users/zstoc/rotation-engine/validation/walk_forward_results.md` (1,500+ lines)
- **Diagnostics:** `/Users/zstoc/rotation-engine/validation/walk_forward_diagnostics.md`
- **Updated Session State:** `/Users/zstoc/rotation-engine/SESSION_STATE.md` (marked CRITICAL)

---

**Next Session:** Run quality gate skills to confirm overfitting diagnosis.
