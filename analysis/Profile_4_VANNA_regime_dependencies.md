# Profile 4: VANNA - Regime Dependencies Analysis

**Date:** 2025-11-16
**Data:** 151 trades across 2020-2025, $13,507 realized PnL, 58.3% win rate
**Critical Finding:** Strategy is mislabeled - NOT pure VANNA, actually DIRECTIONAL GAMMA with decay

---

## Executive Summary

Profile 4 (Long ATM Call) labeled "VANNA" but actually exploits **directional gamma**, not vol-correlation:

| Metric | Value | Insight |
|--------|-------|---------|
| Win Rate | 58.3% | Decent but regime-dependent |
| Total PnL | $13,507 | $163/trade average (Event/Catalyst) |
| Peak Potential | $79,238 | Only 17% capture = leaving money on table |
| Entry Vega | ~76 | Long vega but profit NEGATIVE vol changes |
| Winners Vol Change | -2.31% to -2.48% | **Vega almost irrelevant to profit** |
| Profit Driver | **Spot movement (+2.5-2.7%)** | Gamma, not vega, drives PnL |

---

## Regime-Specific Performance

### 1. EVENT/CATALYST REGIME ✓ (PRIMARY FOCUS)

**Performance:** 108 trades, 63% win rate, +$17,609 PnL ($163/trade)

**Winner Profile:**
- **Entry:** Captures post-event dislocations when vol isn't a clean regime
- **Hold period:** 13.8 days (52 DTE entry → ~38-39 DTE exit)
- **Exit delta:** 0.687 (ITM position, collecting intrinsic value)
- **Spot move:** +2.55% during hold
- **Vol change:** -2.31% (compression, beneficial for long call)
- **Max drawdown:** -41.2% but exits well before hitting it

**Loser Profile:**
- **Exit delta:** 0.440 (barely ITM or OTM)
- **Spot move:** +0.88% (insufficient for gamma profits)
- **Vol change:** -0.96% (not enough compression)
- **Max drawdown:** -830% (theta decay kills unmoving position)

**Exit Signal:** TIME-BASED
- Hold until day 13-14 (before gamma starts accelerating)
- Don't hold to expiration (pin risk, gamma explosion)
- OR: Exit 50% when peak profit > 50% entry cost

---

### 2. TREND UP (VOL COMPRESSION) ⚠ (CAUTION)

**Performance:** 39 trades, 48.7% win rate, -$1,993 PnL (-$51/trade)

**Winner Profile (Rare - 19/39):**
- Similar to Event/Catalyst winners
- Exit delta: 0.686, spot +2.70%, vol -2.48%
- Requires: Strong uptrend continuation WITHOUT vol expansion

**Loser Profile (Catastrophic - 20/39):**
- **Exit delta:** 0.362 (position barely ITM/OTM)
- **Spot move:** +0.14% (trend STALLED - no gamma profit)
- **Vol change:** +2.64% (vol EXPANDED - vega realized badly)
- **Max drawdown:** -336% average (worst case: -1000%+)
- **Death scenario:** Uptrend looks established → vol spike during trend → calls crushed

**Fatal Flaw:** Thesis breaks when vol expands during uptrend
- 2022 exemplar: Fed rates rising + bear market = vol expansion mid-rally
- Stop loss -30% entry cost (tighter than Event/Catalyst)
- Position size: 50% of Event/Catalyst

**Exit Signal:** IMMEDIATE if vol rises
- Monitor RV5: if spikes > 1.5x entry RV5, exit all
- If trend stalls (slope flattens) + no positive spot move in first 5 days, exit

---

### 3. VOL COMPRESSION / PINNED

**Performance:** 0 trades (no data)

---

### 4. VOL EXPANSION

**Performance:** 0 trades (no data)

---

### 5. CHOPPY / MEAN-REVERTING ✗ (AVOID)

**Performance:** 4 trades, 25% win rate, -$2,110 PnL (-$527/trade)

**Issue:** Theta decay kills unmoving positions
- Sideways chop removes gamma profit (no directional move)
- Time decay crushes long call
- This regime is hostile to directional gamma strategies

**Exit Signal:** Don't enter when RV20 is 0.25-0.35 and slope near zero

---

## The Counterintuitive Truth

**Your "VANNA" strategy is actually DIRECTIONAL GAMMA:**

1. **Entry:** Long 1 ATM call (delta ~0.55, vega ~76)
2. **Supposed edge:** Profit from vol-spot correlation (VANNA)
3. **Actual edge:** Spot moves up → delta increases to 0.687 → gamma profit
4. **Vol is secondary:** Winners have NEGATIVE vol changes yet still win
5. **Exit mechanism:** Hold 13-14 days → collect intrinsic value as delta increases
6. **Time decay:** Works against you if spot doesn't move enough (loser profile)

**Why Event/Catalyst wins:**
- Post-events, spot MOVES (creates gamma P&L)
- Vol NORMALIZES (returns to mean after spike)
- Both factors align: gamma + vol compression

**Why Trend Up fails 51% of time:**
- Requires vol to stay compressed throughout uptrend
- If vol expands (regime shift), vega gets crushed
- Spot gains become irrelevant (-336% max DD possible)

---

## Year-by-Year Analysis

| Year | Trades | Win % | PnL | Notes |
|------|--------|-------|-----|-------|
| 2020 | 24 | 70.8% | +$3,940 | Post-COVID bounce, good conditions |
| 2021 | 32 | 53.1% | +$2,391 | Baseline performance |
| **2022** | **15** | **13.3%** | **-$7,841** | **CRISIS: Bear market + vol expansion** |
| 2023 | 27 | 55.6% | +$2,547 | Recovery, post-crisis |
| 2024 | 36 | 69.4% | +$5,294 | Strong, similar to 2020 |
| 2025 | 17 | 70.6% | +$7,177 | YTD strong performance |

### 2022 Crisis Deep Dive

**Context:**
- Fed rate hikes (4.25% → 4.75%)
- Aggressive monetary tightening after inflation spike
- Market repricing: Growth → Bonds
- Volatility regime shift: LOW → HIGH

**What Happened:**
- Entered Event/Catalyst trades after negative events (CPI misses, Twitter, earnings)
- Expected post-event bounce (historical pattern)
- But 2022 events were all NEGATIVE with persistent selling
- Vol expanded instead of normalizing
- Short vega realized badly (-336% max DD)

**Prevention:**
- Skip Event/Catalyst entries when RV20 > 0.35 (already high vol)
- Avoid trading after major NEGATIVE events in bear markets
- Add regime check: if yield curve inverted or DXY strong, reduce position size
- Tighten stops in bear market conditions

---

## Exit Strategy Framework

### Three-Layer Decision Tree

**LAYER 1: PROFIT TAKING** (Most important)
```
IF: Peak profit > 50% of entry cost
    THEN: Exit 50% immediately (lock profits)

IF: Days held > 10 AND spot still up
    THEN: Trail stop at -20% from peak
    ELSE IF: Days held > 10 AND no spot move
    THEN: Exit all (theta dominates)
```

**LAYER 2: VOL REGIME SHIFT** (Most dangerous)
```
IF: RV5 spikes > 1.5x entry RV5
    THEN: Exit all (vol expansion = vega realized)

IF: Slope flattens AND spot stalls (< 0.5% move in 5 days)
    THEN: Exit all (gamma profit unlikely)

FOR TREND UP ONLY:
    IF: Vol starts rising at any point
    THEN: Exit IMMEDIATELY (fatal to this regime)
```

**LAYER 3: TIME DECAY**
```
IF: Days held > 14 AND not at peak profit
    THEN: Exit (theta accelerates, gamma decays)

IF: DTE drops below 38
    THEN: Exit remaining (pin risk + gamma explosion imminent)
```

### Regime-Specific Exit Rules

**EVENT/CATALYST** (63% win rate):
- Stop loss: -50% entry cost
- Time exit: 8-14 days
- Profit exit: 50% when peak > 50% cost
- Vol trigger: Exit if RV5 > 1.5x entry (rare but matters)

**TREND UP** (48.7% win rate):
- Stop loss: -30% entry cost (tighter)
- Vol exit: IMMEDIATELY if RV20 starts rising
- Position size: 50% of Event/Catalyst
- Spot requirement: Needs > 1.5% move in first 5 days to justify hold

**CHOPPY** (25% win rate):
- **Don't enter.** Regime is hostile to this strategy.

---

## Actionable Implementation

### Entry Filters
```python
# Only enter Event/Catalyst if:
if (regime == "Event/Catalyst" and
    RV20 < 0.35 and  # Not already high vol
    market_condition != "bear_market_downturn"):

    # Scale down size if:
    if RV20 > 0.25:
        position_size = base_size * 0.5

    # Don't enter after major negative events (corporate actions, losses)

# Only enter Trend Up if:
if (regime == "Trend Up" and
    slope > 0.05 and
    RV20 < 0.25 and
    RV20 < (RV20_avg - 1std)):  # Vol compressed vs recent history

    position_size = base_size * 0.5  # Half size vs Event/Catalyst
```

### Exit Automation
```python
# Daily check:
if peak_profit_so_far > 50% * entry_cost:
    exit_50_percent()  # Lock profits
    trail_stop_20pct_from_peak()  # Trail remaining

if days_held > 10 and spot_move < 1%:
    exit_all()  # Theta winning, no gamma

if regime == "Trend Up" and RV20 > entry_RV20 + 0.02:
    exit_all_immediately()  # Vol expansion death signal

if days_held > 14 or DTE < 38:
    exit_all()  # Time decay dominant
```

---

## Key Metrics to Monitor

**Daily:**
- Realized vol (RV5, RV20)
- Spot movement % (< 0.5%/day = danger)
- Days held (>14 = exit zone)
- Days to expiration (< 38 = exit zone)
- Peak profit % from entry

**Before Entry:**
- Is this truly Event/Catalyst or forced categorization?
- RV20 current vs historical (avoid > 0.35)
- Is market in bear regime? (If yes, reduce size or skip)
- What was the "event"? (Earnings? Fed? Bad macro?)

**During Hold:**
- Vol term structure (is it inverting? = regime shift)
- Spot velocity (slowing? = exit soon)
- Peak realized since entry (trail stop updated?)

---

## Summary: Where to Allocate Capital

**PRIORITIZE: Event/Catalyst (63% win, +$163/trade)**
- This is your real edge
- Focus entries here
- Full position sizing allowed
- Exit timers: 8-14 days

**REDUCE: Trend Up (48.7% win, -$51/trade)**
- Too risky for regular trading
- Only when vol compression is EXTREME
- Half position sizing
- Exit if vol rises immediately

**AVOID: Choppy regimes (25% win, -$527/trade)**
- Don't trade
- Theta decay kills unmoving positions

**2022 GUARD RAILS:**
- Skip trading after major negative events in bear markets
- Don't enter Event/Catalyst if RV20 > 0.35
- Tighten stops and reduce sizing in inverted yield curve / DXY strength

---

## Files Referenced

- **Backtest data:** `/Users/zstoc/rotation-engine/data/backtest_results/full_tracking_results.json`
- **Memory entities:** Profile_4_VANNA_regime_analysis (and related)
- **Session state:** Should track 2022 prevention guardrails in SESSION_STATE.md

---

**Next Steps:**

1. ✓ Rename Profile_4 internally from "VANNA" to "Directional Gamma (Upside Calls)"
2. ✓ Implement three-layer exit framework in backtest code
3. ✓ Add 2022 prevention guardrails (bear market check, high RV20 filter)
4. ✓ Test exit timing: profit-taking at 50%, vs. hard time-based at 14 days
5. ⏳ Re-run backtest with refined exits (expect higher capture % and Sharpe)
