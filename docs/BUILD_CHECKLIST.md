# Build Checklist - Convexity Rotation Engine

**Implementation order for backtesting harness**
**Source:** ChatGPT day-by-day build plan
**Date:** 2025-11-13

---

## Overview

This is the canonical build sequence. Follow it exactly. Don't skip ahead.

**Timeline:** 7 focused work sessions (days/weekends)
**Approach:** Build → Validate → Move to next layer

---

## Day 1: Data Spine Only

**Goal:** Clean, queryable SPY + options dataset. No trading logic yet.

### 1.1 Core Tasks

* [ ] Load SPY OHLCV into clean table/dataframe
* [ ] Load options data (quotes + Greeks if available)
* [ ] Normalize columns:
  * [ ] `date`, `expiry`, `strike`, `type`
  * [ ] `bid`, `ask`, `mid`
  * [ ] `iv`, `delta`, `gamma`
* [ ] Filter out garbage quotes:
  * [ ] bid < 0
  * [ ] ask < bid
  * [ ] spread > 20% of mid (except Breaking Vol)
  * [ ] extrinsic value < 0

### 1.2 Derived Features

* [ ] Compute `RV5`, `RV10`, `RV20` from SPY returns
* [ ] Compute `ATR5`, `ATR10`
* [ ] Compute `MA20`, `MA50`, `slope_MA20`

### 1.3 Definition of Done

**Test query:**
"Give me SPY + full options chain for 2022-06-15 with RV/IV/MA features computed."

**Success criteria:**
- ✅ No NaN explosions
- ✅ No weird gaps
- ✅ Data structure clean and queryable

---

## Day 2: Regime Labeler (NO TRADES)

**Goal:** Daily regime labels 1-6, walk-forward only.

### 2.1 Signals to Compute

* [ ] **Trend indicators:**
  * [ ] 20-day return
  * [ ] MA20, MA50 slopes
  * [ ] Price relative to MAs
* [ ] **RV/IV ratios:**
  * [ ] RV5 / IV20
  * [ ] RV10 / IV20
* [ ] **IV rank:**
  * [ ] 20D or 30D IV percentile
* [ ] **Skew:**
  * [ ] IV_25D_put - IV_ATM
  * [ ] Skew Z-score vs 6-12 months
* [ ] **Range compression:**
  * [ ] 10-day high/low range in %
* [ ] **Term structure:**
  * [ ] Short IV vs longer IV proxy
* [ ] **Vol-of-vol:**
  * [ ] Stdev of IV30 over last 20 days
* [ ] **Event flags:**
  * [ ] CPI/FOMC windows

### 2.2 Classification Logic

Implement the 6-regime rule set:

* [ ] **Regime 1:** Trend Up
  * [ ] 20-day return > +2%
  * [ ] Price above MA20 and MA50
  * [ ] slope(MA20) > 0
  * [ ] RV < IV
  * [ ] IV percentile < 40%

* [ ] **Regime 2:** Trend Down
  * [ ] 20-day return < -2%
  * [ ] Price below MA20 and MA50
  * [ ] slope(MA20) < 0
  * [ ] RV > IV
  * [ ] Skew steepening

* [ ] **Regime 3:** Vol Compression / Pinned
  * [ ] Price in 3-5% range for 10+ days
  * [ ] RV/IV < 0.6
  * [ ] IV rank < 30%
  * [ ] VIX downtrending

* [ ] **Regime 4:** Breaking Vol
  * [ ] VVIX rising > 10% week over week
  * [ ] VVIX > 80th percentile
  * [ ] Skew steepening aggressively
  * [ ] RV > IV

* [ ] **Regime 5:** Choppy
  * [ ] MA20 slope ≈ 0
  * [ ] RSI oscillating 40-60
  * [ ] RV ≈ IV (0.9 < RV/IV < 1.1)

* [ ] **Regime 6:** Event
  * [ ] Within 3 days of CPI/FOMC/NFP
  * [ ] 0DTE/1DTE IV > 2 std above 60-day mean

**CRITICAL:** Walk-forward only - at date t, use only data up to t

### 2.3 Validation

* [ ] Plot time series: SPY price + colored regime bands (1-6)
* [ ] Sanity-check specific periods:
  * [ ] 2020 crash → Downtrend / Breaking Vol
  * [ ] 2021 grind → Trend Up + Pinned
  * [ ] 2022 bear → Downtrend + Breaking Vol

### 2.4 Definition of Done

**Success criteria:**
- ✅ Every date 2020-2024 has regime label
- ✅ Regime labels look reasonable (visual inspection)
- ✅ No look-ahead bias (walk-forward verified)

---

## Day 3: Convexity Profile Scores (Still No Trades)

**Goal:** For each day, compute six profile scores in [0,1]

### 3.1 Implement Detectors

Each detector outputs `score ∈ [0,1]`:

* [ ] **Profile 1:** Long-dated gamma efficiency (LDG)
  ```
  LDG_score = sigmoid((RV10/IV60) - 0.9) ×
              sigmoid((IV_rank_60 - 0.4) × -1) ×
              sigmoid(slope_MA20)
  ```

* [ ] **Profile 2:** Short-dated gamma spike (SDG)
  ```
  SDG_score = sigmoid((RV5/IV7) - 0.8) ×
              sigmoid(abs(ret_1d)/ATR5) ×
              sigmoid(VVIX_slope)
  ```

* [ ] **Profile 3:** Charm/decay
  ```
  CHARM_score = sigmoid((IV20/RV10) - 1.4) ×
                sigmoid(range_10d < 0.03) ×
                sigmoid(-VVIX_slope)
  ```

* [ ] **Profile 4:** Vanna
  ```
  VANNA_score = sigmoid(-IV_rank_20) ×
                sigmoid(slope_MA20) ×
                sigmoid(-VVIX_slope)
  ```

* [ ] **Profile 5:** Skew convexity
  ```
  SKEW_score = sigmoid(skew_z - 1.0) ×
               sigmoid(VVIX_slope) ×
               sigmoid((RV5/IV20) - 1)
  ```

* [ ] **Profile 6:** Vol-of-vol convexity
  ```
  VOV_score = sigmoid((VVIX/VVIX_80pct) - 1) ×
              sigmoid(VVIX_slope) ×
              sigmoid(IV_rank_20)
  ```

### 3.2 Smoothness Check

* [ ] Plot each profile score over time for sample year (2022)
* [ ] Verify smooth-ish behavior (not insane spikes)

### 3.3 Regime Alignment Check

* [ ] For each regime, compute average of each profile score
* [ ] Verify intuitive alignment:
  * [ ] Regime 3 → high Profile 3 (charm), high Profile 4 (vanna)
  * [ ] Regime 2/4 → high Profile 2, 5, 6
  * [ ] Regime 1 → high Profile 1, 4

### 3.4 Definition of Done

**Success criteria:**
- ✅ Every day 2020-2024 has all 6 profile scores
- ✅ Average profile score by regime makes intuitive sense
- ✅ Scores are smooth (not noisy)

---

## Day 4: Single-Profile Backtest Harness

**Goal:** Build generic trade simulator (reusable for all profiles)

### 4.1 Generic Trade Object

Define trade structure that knows:

* [ ] Entry date/time
* [ ] Entry options (legs, strikes, expiries, quantities)
* [ ] Hedging rule (if any)
* [ ] Close/roll rules
* [ ] Slippage/fee model

### 4.2 Core Engine Loop

For each day:

* [ ] Decide whether profile wants to open/hold/close trades
* [ ] Price legs using bid/ask logic:
  * [ ] Entry: pay ask (or mid + slippage)
  * [ ] Exit: receive bid (or mid - slippage)
* [ ] Apply delta hedge if required
* [ ] Update P&L

### 4.3 Implement ONE Profile Fully First

**Recommended:** Start with Profile 3 (short strangle) or Profile 2 (short-dated gamma)

**Profile 3 implementation:**
* [ ] Trade structure: Short 7-14 DTE 25D strangle
* [ ] Entry logic: When in Regime 3 or profile score > 0.6
* [ ] Delta hedging: Daily
* [ ] Roll logic: When <5 DTE or regime changes
* [ ] Exit logic: On regime transition or roll
* [ ] P&L tracking: Daily mark-to-market

### 4.4 Definition of Done

**Test run:**
"Simulate Profile 3 from 2020-2024, no regime filter, show P&L."

**Success criteria:**
- ✅ Doesn't crash
- ✅ P&L looks vaguely believable
- ✅ Can trace specific trades (entry/exit prices, dates)

---

## Day 5: Full Set of Profile-Level Backtests

**Goal:** Every profile has isolated P&L series

### 5.1 Wire Each Profile to Canonical Trade

* [ ] **P1:** 60-90 DTE long ATM straddle
  * [ ] Delta-hedge daily
  * [ ] Roll 30 days before expiration

* [ ] **P2:** 1-3 DTE ATM straddle
  * [ ] Long in Regime 2 (downtrend)
  * [ ] Short in Regime 5 (choppy, delta-hedged)

* [ ] **P3:** 7-14 DTE short 25D strangle
  * [ ] Delta-hedge daily
  * [ ] Roll when <5 DTE

* [ ] **P4:** Call diagonal (60D long, 7D short) or call fly
  * [ ] Track vanna attribution

* [ ] **P5:** Put backspread
  * [ ] Long 2x 25D puts, short 1x ATM put

* [ ] **P6:** 30-60 DTE long straddle or VIX calls
  * [ ] Only deploy in Regime 4 or 6

### 5.2 Run Each Profile on Full Sample

**First:** Without regime conditioning (always on)
* [ ] Profile 1 always-on P&L
* [ ] Profile 2 always-on P&L
* [ ] Profile 3 always-on P&L
* [ ] Profile 4 always-on P&L
* [ ] Profile 5 always-on P&L
* [ ] Profile 6 always-on P&L

**Then:** With regime filtering (only trade when score > threshold)
* [ ] Profile 1 with filtering
* [ ] Profile 2 with filtering
* [ ] Profile 3 with filtering
* [ ] Profile 4 with filtering
* [ ] Profile 5 with filtering
* [ ] Profile 6 with filtering

### 5.3 Analyze Per-Regime P&L

For each profile, group P&L by `regime_t`:

* [ ] Compute mean daily P&L per regime
* [ ] Compute std, Sharpe per regime
* [ ] Compute hit rate per regime

**Create table:** Profile vs Regime performance matrix

### 5.4 Definition of Done

**Validation check:**
"Does each profile make money where we think it should?"

**Success criteria:**
- ✅ Profile 3 (charm) wins in Regime 3 (pinned)
- ✅ Profile 3 has major drawdowns in Regime 4 (breaking vol)
- ✅ Profile 2 (short gamma) performs well in Regime 2 (downtrend)
- ✅ No total inversions of expected behavior

---

## Day 6: Rotation Engine Layer

**Goal:** Combine profiles with dynamic capital allocation

### 6.1 Desirability Scores

For each day:

* [ ] Start from profile scores (0-1)
* [ ] Apply regime compatibility weights:
  ```python
  # Example for Regime 2 (Downtrend)
  compatibility = {
      'profile_1': 0.0,
      'profile_2': 1.0,
      'profile_3': 0.2,
      'profile_4': 0.0,
      'profile_5': 1.0,
      'profile_6': 0.6
  }
  ```
* [ ] Calculate: `desire_i(t) = profile_score_i(t) × compatibility_i(regime_t)`

### 6.2 Normalize and Risk Adjust

* [ ] Normalize so weights sum to 1.0:
  ```python
  weight_i = desire_i / sum(desire_j)
  ```

* [ ] Apply constraints:
  * [ ] Max per-profile cap: 40%
  * [ ] Min allocation threshold: 5% (ignore below this)
  * [ ] VIX > 35 → scale down all positions
  * [ ] Reduce short-vol in event windows

### 6.3 Capital Mapping

For each day:

* [ ] Use `weight_i(t)` as notional allocation to profile i's trade simulator
* [ ] Aggregate all profile P&Ls into single portfolio P&L:
  ```python
  portfolio_pnl(t) = sum(weight_i(t) × profile_pnl_i(t))
  ```

### 6.4 Definition of Done

**Test run:**
"Full convexity rotation engine P&L 2020-2024"

**Can break down by:**
- ✅ P&L by profile
- ✅ P&L by regime
- ✅ Drawdown curve
- ✅ Allocation heatmap over time

---

## Day 7: Validation & Stress Testing

**Goal:** Try to break it. If it survives, it's real.

### 7.1 Stress Tests

* [ ] **2× transaction costs**
  * [ ] Bid-ask spreads doubled
  * [ ] Does edge survive?

* [ ] **Add execution slippage**
  * [ ] Random ±20-50 bps on fills
  * [ ] Performance degradation acceptable?

* [ ] **Delay hedges**
  * [ ] Delta hedge 1 hour late instead of instant
  * [ ] Impact on P&L?

* [ ] **Remove top 10 best days**
  * [ ] Is strategy dependent on outliers?

### 7.2 Sub-Period Analysis

* [ ] 2020 only (crash + recovery)
* [ ] 2021 only (melt-up low vol)
* [ ] 2022 only (bear market)
* [ ] 2023-2024 (choppy low vol)

**Question:** Does it work in ALL periods or just specific ones?

### 7.3 Sanity Questions

* [ ] Does engine shift away from dangerous profiles in crashes?
* [ ] Does short charm get reduced when regime → Breaking Vol?
* [ ] Fewer blowups than naive "always short gamma"?
* [ ] Do regime transitions generate P&L or whipsaw losses?

### 7.4 Cross-Validation (Optional)

Test on alternative underlyings:

* [ ] QQQ (tech-heavy)
* [ ] IWM (small cap)
* [ ] XLK (sector)

**Not expecting identical performance - testing stability of approach**

### 7.5 Definition of Done

**Success criteria:**
- ✅ Survives stress tests without collapsing
- ✅ Positive Sharpe in at least 3/4 sub-periods
- ✅ Max drawdown < 50%
- ✅ Strategy behavior matches intuition (reduces risk in crashes, harvests edge in stable periods)

---

## Implementation Notes

### Code Organization

```
src/
├── data/
│   ├── loaders.py          # Load SPY OHLCV and options data
│   ├── features.py         # Compute RV, ATR, MAs, etc.
│   └── validation.py       # Data quality checks
├── regimes/
│   ├── signals.py          # Regime signal calculations
│   ├── classifier.py       # 6-regime classification logic
│   └── validator.py        # Regime sanity checks
├── profiles/
│   ├── detectors.py        # 6 profile scoring functions
│   └── validator.py        # Profile score sanity checks
├── trading/
│   ├── trade.py            # Generic trade object
│   ├── simulator.py        # Trade execution simulator
│   ├── profiles/
│   │   ├── profile_1.py    # Long-dated gamma implementation
│   │   ├── profile_2.py    # Short-dated gamma implementation
│   │   ├── profile_3.py    # Charm decay implementation
│   │   ├── profile_4.py    # Vanna implementation
│   │   ├── profile_5.py    # Skew convexity implementation
│   │   └── profile_6.py    # Vol-of-vol implementation
│   └── execution.py        # Bid-ask logic, slippage
├── backtest/
│   ├── engine.py           # Main backtest orchestrator
│   ├── rotation.py         # Capital allocation logic
│   └── portfolio.py        # Portfolio P&L aggregation
├── risk/
│   ├── constraints.py      # Position limits, risk caps
│   └── hedging.py          # Delta hedging logic
└── analysis/
    ├── metrics.py          # Sharpe, drawdown, attribution
    ├── attribution.py      # Greek P&L breakdown
    └── visualization.py    # Plots and reports
```

### Testing Strategy

**After each day:**
1. Write unit tests for new functionality
2. Validate against known examples
3. Visual inspection of outputs
4. Don't proceed until current layer works

**Progressive validation:**
- Day 1: Data integrity tests
- Day 2: Regime classification visual validation
- Day 3: Profile score correlation checks
- Day 4: Single-trade P&L verification
- Day 5: Per-profile performance validation
- Day 6: Portfolio allocation logic tests
- Day 7: Full system stress testing

### Common Pitfalls to Avoid

**Look-ahead bias:**
- ❌ Using future data in regime classification
- ❌ Optimizing parameters on full dataset
- ✅ Always walk-forward

**Implementation bugs:**
- ❌ Off-by-one errors in indexing
- ❌ Using wrong side of bid-ask (paying bid when should pay ask)
- ✅ Manual verification of random trades

**Overfitting:**
- ❌ Optimizing every threshold
- ❌ Adding parameters until backtest looks perfect
- ✅ Use ChatGPT's default values, only change if clearly broken

**Transaction costs:**
- ❌ Using mid-price
- ❌ Ignoring delta hedge costs
- ✅ Realistic bid-ask spreads from actual SPY options data

---

## Success Gates

**Don't proceed to next day until:**

**Day 1 → Day 2:**
- ✅ Can query any date and get clean data
- ✅ Zero NaN values in critical columns
- ✅ RV/ATR/MA calculations verified correct

**Day 2 → Day 3:**
- ✅ Every date has regime label
- ✅ Visual inspection looks sane (crash = downtrend/breaking vol)
- ✅ No look-ahead bias (verified walk-forward)

**Day 3 → Day 4:**
- ✅ All 6 profile scores calculated
- ✅ Regime alignment makes sense
- ✅ Scores are smooth

**Day 4 → Day 5:**
- ✅ Can run single profile backtest without crashes
- ✅ Can trace individual trades
- ✅ P&L calculation verified on sample trades

**Day 5 → Day 6:**
- ✅ All 6 profiles have P&L series
- ✅ Per-regime performance matches expectations
- ✅ No total inversions

**Day 6 → Day 7:**
- ✅ Rotation engine runs full 2020-2024
- ✅ Can break down P&L by profile and regime
- ✅ Allocation weights look reasonable

**Day 7 → Production:**
- ✅ Survives all stress tests
- ✅ Sharpe > 1.0 after costs
- ✅ Max DD < 50%
- ✅ Ready for RED TEAM GAUNTLET

---

**Last Updated:** 2025-11-13
**Source:** ChatGPT day-by-day build plan
**Status:** READY FOR IMPLEMENTATION
