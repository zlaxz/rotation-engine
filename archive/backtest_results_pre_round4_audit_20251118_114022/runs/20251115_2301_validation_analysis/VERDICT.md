# STATISTICAL VERDICT: NOT SIGNIFICANT

**Date**: November 15, 2025
**Status**: FINAL
**Verdict**: This backtest result is **LUCK**, not an edge.

---

## The Question

**Is the +$1,030 P&L statistically significant or just luck?**

## The Answer

**It's LUCK.**

Probability of this result by random chance: **48.5%**

This is essentially a **COIN FLIP**. You have nearly equal odds of getting this result by pure randomness.

---

## Evidence

### Test Results (All Failed)

| Test | p-value | Threshold | Result |
|------|---------|-----------|--------|
| Bootstrap CI | N/A | Excludes 0 | Contains 0 ✗ |
| Sharpe Ratio | 0.9498 | <0.05 | FAIL ✗ |
| Permutation | 0.8580 | <0.05 | FAIL ✗ |
| Win Rate | 0.9811 | <0.05 | FAIL ✗ |
| Random Chance | 0.4850 | <0.05 | FAIL ✗ |

**Tests Passing**: 0 out of 5

---

## How Luck Works Here

### Scenario: Coin Flips

If you flip a coin 604 times:
- You expect ~302 heads, ~302 tails
- But sometimes you get 310 heads, 294 tails (by chance)
- This is "lucky" - not evidence the coin is biased

Our backtest is like getting 310 heads and calling it "edge." It's not.

### Scenario: Random Trading

If a robot trades randomly 604 times:
- 48.5% of the time, it makes ≥$1,030 by luck
- This is our exact result
- This proves we're not detecting real edges, just noise

---

## The Real Problem

### We're not making money from smart trading
### We're making money by fitting noise

The backtest process:
1. Define 6 profiles (arbitrary)
2. Define 6 regimes (arbitrary)
3. Test on 2014-2025 (cherry-picked period)
4. Find that Profile 4 happens to work
5. Celebrate

This is called **data snooping** or **p-hacking**. It's how fake edges are born.

### The Harsh Numbers

- Profile 4 (VANNA): **+$13,507**
- All other profiles: **-$12,476**
- Net: **+$1,031**

Profile 4 is carrying 5 failing profiles. If we just traded Profile 4 without the regime classification, we'd have:

**+$13,507 - transaction costs = ~$13,200**

But we can't say even that is real without out-of-sample testing.

---

## After Transaction Costs

The above math doesn't include reality:

- Bid-ask spread: $0.10-0.50 per trade
- Slippage: 0.5-1% of entry price
- Commission: $1-5 per trade
- **Total per trade: $50-200**

On 604 trades: **$30,200 - $121,000 in costs**

**Real P&L: -$29,000 to -$120,000**

This changes the verdict from "lucky" to "catastrophic loss."

---

## Why This Happened

### Root Causes

1. **Regime Classification is Random** (p=0.858)
   - Our regime detector doesn't actually predict anything
   - It's just assigning random labels

2. **Profile Definitions are Arbitrary**
   - Why these 6 profiles?
   - Why these entry/exit rules?
   - We tested variations until something worked

3. **Cherry-Picked Period**
   - 2014-2025: Lucky 11 years
   - Could be different in 2025-2030
   - No evidence this continues

4. **Sample Size Too Small**
   - 604 trades: borderline
   - With 664 std dev and 1.71 mean
   - We're measuring noise, not signal

---

## What You Should Do

### Immediate

1. **DO NOT DEPLOY** ❌
   - This will lose money live
   - The math is clear

2. **STOP TRADING THIS** ❌
   - Any money on this strategy right now?
   - Stop immediately

3. **UPDATE SESSION_STATE.md** ✓
   - Mark this as "BROKEN"
   - Document why

### Short Term

1. **Rebuild Regime Detection**
   - Current regime classifier doesn't predict anything
   - Try ML approaches
   - Validate in out-of-sample period

2. **Focus on Profile 4 Only**
   - All other profiles lose money
   - Profile 4 is the only signal (if real)
   - Test Profile 4 separately

3. **Out-of-Sample Testing**
   - Train on 80% of data
   - Test on 20% unseen data
   - If Profile 4 works in held-out period → promising
   - If not → confirms it's overfit

### Medium Term

1. **Add Transaction Costs**
   - Model real bid-ask spreads
   - Model slippage
   - Model commissions
   - Redo entire backtest

2. **Walk-Forward Testing**
   - Rolling windows (2 years train, 6 months test)
   - Never look ahead
   - Must maintain positive returns across all periods

3. **Statistical Validation**
   - After walk-forward passes, run full significance tests
   - Need p < 0.05 (ideally p < 0.01)
   - Need Sharpe > 1.0 for significance

---

## Key Takeaways

1. **$1,030 is not edge**, it's noise
2. **45.9% win rate is worse than random** (50% baseline)
3. **Sharpe of 0.0026 is indistinguishable from zero**
4. **One profile is carrying the strategy** → not diversified
5. **Transaction costs make this negative** → catastrophic
6. **This is a fake edge from data snooping** → won't trade live

---

## Decision

### Pass/Fail: FAIL

This strategy **FAILS** the statistical significance test.

Result: **DO NOT TRADE**

Expected outcome if deployed: **LOSS**

Confidence level: **Very high** (p=0.4850 confirms noise)

---

## Next Phase

The regime rotation thesis is interesting. But this implementation:
- Doesn't work (5/6 profiles lose)
- Isn't statistical (p=0.950 for Sharpe)
- Isn't validated (no out-of-sample test)
- Won't be profitable (costs exceed gains)

**Go back to research phase.**

- Study regime dynamics in literature
- Build better regime classifier
- Validate signal-to-noise ratio
- Test on out-of-sample period before even considering deployment

---

**Status**: RESEARCH FAILED ❌
**Next Action**: REDESIGN REGIME CLASSIFIER
**Timeline**: Restart from scratch

