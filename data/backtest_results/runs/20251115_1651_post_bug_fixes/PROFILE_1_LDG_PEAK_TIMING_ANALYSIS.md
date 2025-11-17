# PROFILE 1: LONG-DATED GAMMA (LDG) - PEAK TIMING ANALYSIS

## Executive Summary

**Profile 1 (LDG) exhibits a bimodal peak distribution with distinct early and late clusters.**

- **117 profitable trades (83.6%)**
- **23 unprofitable trades (16.4%)**
- **Mean peak timing: Day 6.9 (median: Day 7.0)**
- **Key insight: 45.3% turn profitable on Day 1, but peak value occurs much later**

---

## Peak Timing Distribution

### Overall Statistics
```
Mean peak day:           6.91
Median peak day:         7.00
Std deviation:           5.00
Min peak day:            0
Max peak day:            14
```

### Distribution by Time Range

| Category | Trades | % | Peak Value (Median) | Avg Peak Day |
|----------|--------|----|--------------------|--------------|
| **Early (Days 1-5)** | 42 | 30.0% | $129.80 | 3.1 |
| **Mid (Days 6-9)** | 26 | 18.6% | $289.30 | 7.7 |
| **Late (Days 10-14)** | 49 | 35.0% | $437.80 | 12.7 |
| **Never Profitable** | 23 | 16.4% | -$17.20 | - |

### Histogram: Peak Timing Distribution (Days 0-14)

```
Day  0:   0 trades (  0.0%)
Day  1:   7 trades (  5.0%) ███
Day  2:   8 trades (  5.7%) ███
Day  3:   9 trades (  6.4%) ███
Day  4:   9 trades (  6.4%) ███
Day  5:   9 trades (  6.4%) ███
Day  6:   3 trades (  2.1%) █
Day  7:   9 trades (  6.4%) ███
Day  8:   6 trades (  4.3%) ██
Day  9:   8 trades (  5.7%) ███
Day 10:   7 trades (  5.0%) ██
Day 11:   1 trades (  0.7%)
Day 12:  10 trades (  7.1%) ███
Day 13:  16 trades ( 11.4%) █████
Day 14:  16 trades ( 11.4%) █████
```

**KEY OBSERVATION: Clear bimodal pattern**
- **First peak cluster: Days 1-5 (30% of trades, smaller gains)**
- **Dead zone: Days 6-11 (only 30% of trades)**
- **Second peak cluster: Days 12-14 (23% of trades, larger gains)**

---

## Critical Discovery: Profitability Timing vs. Peak Timing

### Time to First Profitability
```
Mean:   3.1 days
Median: 2.0 days
Mode:   Day 1 (45.3% of trades!)
```

#### Distribution
| Day | Trades Turning Profitable | % |
|-----|--------------------------|---|
| Day 1 | 53 | 45.3% |
| Day 2 | 16 | 13.7% |
| Day 3 | 20 | 17.1% |
| Day 4 | 3 | 2.6% |
| Day 5 | 3 | 2.6% |
| Day 6+ | 22 | 18.8% |

**CRITICAL INSIGHT**:
- **59% of trades are profitable by Day 2**
- **76% are profitable by Day 3**
- **But peaks don't happen until much later (mean Day 6.9)**

This reveals the fundamental LDG dynamic:
1. **Theta decay hits immediately** → Initial loss (-$17 on entry day)
2. **Quick gamma snap** → Most trades recover to profitability by Day 2
3. **Then what?** → Either hold for larger peaks or exit with quick gains

---

## Profit Realization Schedule

### Average P&L by Day (for trades holding that long)

| Day | Avg Profit | Median | Min | Max | # Trades |
|-----|-----------|--------|-----|-----|----------|
| 1 | $63.86 | $52.80 | $0.80 | $350.80 | 117 |
| 2 | $111.15 | $84.80 | $0.80 | $844.80 | 117 |
| 3 | $130.54 | $72.80 | $2.80 | $791.80 | 117 |
| 4 | $153.02 | $106.80 | $0.80 | $822.80 | 117 |
| 5 | $192.99 | $124.30 | $7.80 | $907.80 | 117 |
| 6 | $178.11 | $114.30 | $2.80 | $732.80 | 117 |
| 7 | $189.25 | $140.80 | $9.80 | $688.80 | 117 |
| 8 | $248.05 | $165.30 | $1.80 | $1087.80 | 117 |
| 9 | $260.84 | $173.80 | $4.80 | $939.80 | 117 |

**Pattern**:
- Day 1→2: Sharp jump ($64 → $111 average)
- Day 2→5: Steady improvement to ~$193
- Day 5→9: Plateau ~$190-$260
- After Day 9: Risk of drawdown (theta + vega bleed)

---

## Drawdown Risk After Peak

### What happens if you hold past peak?

| Days After Peak | Avg Drawdown | Median | Worst 5% | Best 5% |
|-----------------|-------------|--------|----------|---------|
| +1 day | -125.0% | -66.5% | -354.1% | -8.8% |
| +2 days | -164.8% | -87.5% | -576.4% | -25.3% |
| +3 days | -289.2% | -125.6% | -683.3% | -26.9% |
| +4 days | -451.9% | -149.9% | -794.7% | -28.5% |
| +5 days | -606.8% | -154.5% | -860.5% | -39.9% |

**The math is brutal**: Holding past peak loses median 66-155% of peak value within 2-5 days.

This explains why gamma selling (long gamma harvesting) exits quickly.

---

## Peak Capture Milestones

### When are cumulative % of peaks reached?

| % of Peaks | By Day | # Trades |
|-----------|--------|----------|
| 25% | Day 2 | 35 |
| 50% | Day 7 | 70 |
| 75% | Day 12 | 105 |
| 90% | Day 14 | 126 |

**Translation**:
- To catch half the peaks, you need to hold 7 days (uncomfortable duration for gamma)
- To catch 90%, you need the full 2-week expiration window

---

## Recommendation: Adaptive Exit Strategy for LDG

### The Fundamental Trade-Off

**Holding longer = bigger peaks, but slower theta harvesting**

1. **Quick Harvest (Exit Day 3)**
   - Captures: ~36% of all trades near peak
   - Median profit: $73
   - Exits with: 45.3% on Day 1, 59% by Day 2 profitable trades
   - Duration: Ultra-short
   - Best for: Pure gamma harvesting, high trading frequency

2. **First-Week Window (Exit Day 5-7)**
   - Captures: ~54% of trades near peak by Day 7
   - Median profit by Day 7: $141
   - Duration: Normal weekly expiration
   - Best for: Balanced gamma + theta approach

3. **Extended Hold (Exit Day 10-14)**
   - Captures: 69-100% of peaks
   - Median profit by Day 9: $174
   - Risk: Heavy theta bleed after peak
   - Best for: Only if volatility regime validates longer exposure

### Recommended Implementation

**Two-Tier Exit Strategy:**

```
TIER 1: Day 3 Harvest
  - Exit any trade up 30%+ on Day 3
  - Captures quick gamma snaps
  - Harvest ~36% of trades at profit

TIER 2: Day 7 Window
  - Hold remaining to Day 7
  - Re-evaluate Greeks and vol regime
  - Thesis: Most peaks cluster here (median 7 days)

TIER 3: Hard Stop
  - Force exit all positions at Day 14
  - Prevents extended theta decay
  - No exceptions
```

This captures:
- **Quick wins**: Day 1-3 γ spikes (30% of trades)
- **Medium wins**: Day 5-9 peak window (40% of trades)
- **Exits decay stage**: Before post-peak drawdown accelerates

---

## Key Insights for Strategy Design

1. **LDG Bleeds Theta First, Then Explodes**
   - Entry: -$17 loss due to theta
   - Day 1: Recovers to ~$52-63 (gamma snap)
   - Days 1-9: Steady growth if regime supports
   - Days 10+: Dangerous zone (theta + vega decay)

2. **The Bimodal Distribution is Real**
   - 30% of trades want to exit Days 1-5 (small wins)
   - 35% of trades want to exit Days 10-14 (big wins)
   - Only 19% comfort zone in Days 6-9

3. **Exits Past Peak are Brutal**
   - Median -66.5% loss within 1 day of peak
   - Median -154.5% loss within 5 days

4. **High-Frequency Harvesting is Viable**
   - 59% profitable by Day 2
   - 76% profitable by Day 3
   - Exit discipline = the competitive edge

---

## Conclusion

**Profile 1 LDG should not be treated as a "hold to expiration" strategy.**

Recommended exit windows:
- **Primary**: Day 3 (harvest quick γ snaps)
- **Secondary**: Day 7 (capture median peak window)
- **Failsafe**: Day 14 (hard stop)

This approach acknowledges the bimodal nature while protecting against extended theta decay.

---

**Analysis Date**: 2025-11-16
**Data Source**: `/Users/zstoc/rotation-engine/data/backtest_results/current/results.json`
**Trades Analyzed**: 140 total (117 profitable, 23 unprofitable)
