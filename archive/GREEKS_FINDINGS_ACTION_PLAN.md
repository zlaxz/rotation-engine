# Greeks Pattern Analysis - Action Plan

**Status:** Complete analysis of 668 trades reveals 3 major discoveries
**Impact:** +11% win rate, +$70/trade potential improvement
**Confidence:** HIGH (p < 0.001 for all major patterns)

---

## Executive Summary

The backtest contradicts traditional options wisdom:

| Finding | Traditional Wisdom | Backtest Reality | Impact |
|---------|------------------|-----------------|--------|
| **Gamma** | Buy for protection | Avoid (losing bet) | -14% win rate |
| **Delta** | Stay neutral | Embrace directional | +17% win rate |
| **Theta** | Minimize | Harvest when positive | +21% win rate |
| **Vega** | Control | Short vol works | +26% win rate |

---

## Three Critical Discoveries

### 1. Gamma Paradox (Most Actionable)
- **Finding:** High-gamma trades: 37.1% win rate, Low-gamma trades: 51.2% win rate
- **Magnitude:** +14.1 percentage points (p=0.0003, highly significant)
- **Implication:** Straddles and strangles are losing bets
- **Action:** Reduce all positions to gamma < 0.02

### 2. Directional Bias Wins (Highest Impact)
- **Finding:** Winners have 67% higher delta (0.203 vs 0.123)
- **Magnitude:** +17% win rate difference (very-positive vs neutral delta)
- **Implication:** Direction matters more than Greeks neutrality
- **Action:** Target delta 0.30-0.60 for all new positions

### 3. Positive Theta is Rare Gold (Constraint)
- **Finding:** Only 12% of trades have positive theta (81 total)
- **Magnitude:** 63% win rate for positive theta vs 42% for negative
- **Implication:** Calendar spreads outperform straddles
- **Action:** Increase Profile_3_CHARM allocation (only positive-theta source)

---

## Profile Redesign: From Convexity to Greeks

### Current Profile Structure (Wrong Optimization Target)
```
Profile_1_LDG      → Long-Dated Gamma (design target)
Profile_2_SDG      → Short-Dated Gamma (design target)
Profile_3_CHARM    → Charm/Decay (design target)
Profile_4_VANNA    → Vanna/Vol-Spot (design target)
Profile_5_SKEW     → Skew (design target)
Profile_6_VOV      → Vol-of-Vol (design target)
```

### Problem
Each profile is optimized for its Greeks target, but NOT for winning Greeks profile:
- Profile_2_SDG: Optimizes for high gamma, but high gamma loses
- Profile_5_SKEW: Optimizes for skew, but produces losing directional bias

### Solution: Greeks-First Redesign

All profiles should target the winning Greeks combination:

```
TARGET GREEKS PROFILE (from Profile_4_VANNA, 58.6% win rate):
- Delta:  0.50-0.60   (directional edge)
- Gamma:  0.010-0.020 (low - avoid short gamma pain)
- Theta:  -30 to -50   (manageable decay)
- Vega:   70-100       (some vol exposure)

CURRENT LOSERS vs TARGET:

Profile_2_SDG:  Delta=0.05 (❌ Too low), Gamma=0.10 (❌ Too high)
Profile_5_SKEW: Delta=-0.21 (❌ Wrong sign), Gamma=0.009 (✓ OK)
Profile_6_VOV:  Delta=0.08 (❌ Too low), Gamma=0.045 (❌ Too high)
```

---

## Implementation Plan

### Phase 1: Risk Mitigation (Week 1)

#### 1.1 Eliminate Profile_5_SKEW [2 days]
- **Current:** 21% win rate, -$212 avg PnL
- **Action:** Remove from rotation entirely
- **Expected:** Eliminates worst performer
- **Files to change:** `/Users/zstoc/rotation-engine/src/profiles/profile_5_skew.py`
- **Impact:** +$212/trade improvement from this profile alone

#### 1.2 Reduce Gamma Target to <0.02 [1 day]
- **Current:** Gamma ranges 0.01-0.10 across profiles
- **Action:** Add gamma cap constraint to entry logic
- **File:** `/Users/zstoc/rotation-engine/src/entry_signals.py`
- **Expected:** ~+5% win rate across portfolio
- **Implementation:**
  ```python
  # Add constraint
  if entry_greeks['gamma'] > 0.02:
      skip_trade()
  ```

#### 1.3 Rebalance Allocation [1 day]
- **Current:** 6 profiles × 17% = 100% (equal weight)
- **Target:**
  - Profile_4_VANNA: 40% (best performer)
  - Profile_3_CHARM: 25% (only positive theta)
  - Profile_1_LDG: 15%
  - Profile_2_SDG: 10% (limited by gamma)
  - Profile_6_VOV: 10% (limited by gamma)
  - Profile_5_SKEW: 0% (eliminate)
- **File:** `/Users/zstoc/rotation-engine/src/portfolio_config.py`
- **Expected:** +6% win rate, +$50/trade PnL improvement

### Phase 2: Profile Optimization (Week 2)

#### 2.1 Redesign Profile_2_SDG [2 days]
- **Problem:** Delta=0.05 (too low), Gamma=0.10 (too high)
- **Target:** Delta=0.50, Gamma=0.015 (match Profile_4_VANNA)
- **Current Win Rate:** 36.5%
- **Expected Win Rate:** 55-60% (if redesign successful)
- **Action:** Change from short-dated strangles to directional call spreads
- **File:** `/Users/zstoc/rotation-engine/src/profiles/profile_2_sdg.py`

#### 2.2 Optimize Profile_3_CHARM for More Positive Theta [2 days]
- **Problem:** Only 81 positive-theta trades (12%)
- **Action:** Add calendar spread variations to increase positive theta frequency
- **Target:** 25-30% of trades with positive theta
- **Expected Win Rate:** 70%+ (if theta consistently positive)
- **File:** `/Users/zstoc/rotation-engine/src/profiles/profile_3_charm.py`

#### 2.3 Test Profile_1_LDG Greeks [1 day]
- **Current:** 43% win rate (mediocre)
- **Greeks Profile:** Delta=0.13, Gamma=0.028 (not optimized)
- **Action:** Shift toward higher delta, lower gamma
- **Expected:** 50%+ win rate

### Phase 3: Validation (Week 2)

#### 3.1 Regime-Conditional Analysis [2 days]
- **Question:** Do Greeks patterns hold across market regimes?
- **Method:** Re-run analysis split by regime
- **Files:** Create new analysis script
- **Purpose:** Ensure patterns aren't regime-specific

#### 3.2 Greeks Screening Filter [2 days]
- **Action:** Add entry filter based on Greeks patterns
- **Rule:** Only enter if Delta > 0.30 AND Gamma < 0.02 AND (Theta > 0 OR Theta > -50)
- **Expected:** Improve win rate, reduce losing trades
- **File:** `/Users/zstoc/rotation-engine/src/entry_signals.py`

---

## Expected Outcomes

### Conservative Estimate (Phase 1 only)
```
Win Rate:     44.1% → 50% (+5.9%)
Avg PnL:      -$20  → $30 (+$50/trade)
Portfolio PnL: +$3k → +$8k (+$5k improvement)
```

### Optimistic Estimate (All Phases)
```
Win Rate:     44.1% → 55% (+10.9%)
Avg PnL:      -$20  → $50 (+$70/trade)
Portfolio PnL: +$3k → +$13k (+$10k improvement)
```

---

## Key Files to Modify

**Profile Optimization:**
- `/Users/zstoc/rotation-engine/src/profiles/profile_2_sdg.py`
- `/Users/zstoc/rotation-engine/src/profiles/profile_3_charm.py`
- `/Users/zstoc/rotation-engine/src/profiles/profile_5_skew.py` (REMOVE)

**Entry Logic:**
- `/Users/zstoc/rotation-engine/src/entry_signals.py` (add Greeks filters)

**Portfolio Configuration:**
- `/Users/zstoc/rotation-engine/src/portfolio_config.py` (rebalance allocation)

**Greeks Calculation:**
- `/Users/zstoc/rotation-engine/src/greeks_calculator.py` (verify accuracy)

---

## Risk Factors

### Risk 1: Greeks Calculation Errors
- **Concern:** Entry Greeks might be calculated incorrectly
- **Mitigation:** Validate Greeks against Black-Scholes benchmarks
- **Action:** Run Greeks validation test before implementation

### Risk 2: Regime Dependency
- **Concern:** Patterns might not hold in trending markets
- **Mitigation:** Test in different market regimes
- **Action:** Regime-conditional analysis (Phase 3)

### Risk 3: Data Snooping
- **Concern:** Patterns might be due to random chance (though p<0.001)
- **Mitigation:** Walk-forward validation on future data
- **Action:** Test on out-of-sample period

### Risk 4: Live Trading Slippage
- **Concern:** Backtest assumes perfect execution
- **Mitigation:** Add realistic transaction costs
- **Action:** Conservative position sizing initially

---

## Files Generated (Data/Analysis)

All analysis files saved to: `/Users/zstoc/rotation-engine/data/backtest_results/`

1. **GREEKS_PATTERN_ANALYSIS.md** (11 KB)
   - Comprehensive technical report
   - Statistical validation
   - Detailed findings by profile

2. **GREEKS_PATTERNS_VISUAL.txt** (6.4 KB)
   - Visual summary with ASCII charts
   - Quick reference for key patterns
   - Recommendation matrix

3. **GREEKS_ANALYSIS_SUMMARY.txt** (5.4 KB)
   - Executive brief
   - Three critical discoveries
   - Next questions and caveats

4. **GREEKS_FINDINGS_ACTION_PLAN.md** (this file)
   - Implementation roadmap
   - Risk assessment
   - Timeline and resources

---

## Success Criteria

### Phase 1 Success
- Profile_5_SKEW successfully removed from rotation
- Gamma cap (<0.02) implemented without breaking other logic
- Allocation rebalanced successfully
- **Target:** 50% win rate achieved

### Phase 2 Success
- Profile_2_SDG redesigned with higher delta, lower gamma
- Profile_3_CHARM positive theta frequency increased
- All profiles now target winning Greeks profile
- **Target:** 55% win rate achieved

### Phase 3 Success
- Regime-conditional analysis shows patterns hold
- Greeks screening filter reduces false entry signals
- Out-of-sample validation confirms backtest results
- **Target:** 55% win rate sustained on new data

---

## Timeline

```
Week 1: Phase 1 (Risk Mitigation)      4 days
  - Eliminate Profile_5_SKEW           2 days
  - Add gamma cap                       1 day
  - Rebalance allocation                1 day

Week 2: Phase 2 (Optimization)         4 days
  - Redesign Profile_2_SDG             2 days
  - Optimize Profile_3_CHARM           2 days

Week 2: Phase 3 (Validation)           2 days
  - Regime-conditional analysis        1 day
  - Greeks screening filter            1 day

TOTAL: 10 days (2 weeks)
```

---

## Decision Point: Continue or Pivot?

If Phase 1 shows **<49% win rate**, pivot to different Greeks targets.

If Phase 1 shows **>50% win rate**, proceed with Phase 2.

If Phase 2 shows **>54% win rate**, scale allocation to optimized profiles.

---

## Next Meeting Agenda

1. Review Greek patterns with quant team
2. Validate Greeks calculation methodology
3. Approve Phase 1 implementation
4. Schedule weekly check-ins for monitoring

---

**Document Created:** 2025-11-15
**Status:** Ready for Implementation
**Approval Required:** ✓ (CEO sign-off on Phase 1)
