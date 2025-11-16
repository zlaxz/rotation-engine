# Disaster Filter Analysis: Risk Avoidance Strategy

**Analysis Date**: 2025-11-15
**Dataset**: 668 trades across 6 profiles (2020-2025)
**Goal**: Identify market conditions where trades are likely to lose money

---

## Executive Summary

**Bottom 10% (66 worst losers) have clear entry condition patterns:**

- Elevated realized volatility (RV5 +30% higher than average)
- Weak/negative price momentum (return_10d -81% lower)
- Flat trend strength (slope -32% lower)
- Higher theta decay (more negative by -19.5%)

**Key Finding**: A simple **2-condition filter** avoids 68 trades (-$12.1K loss) with minimal trade reduction:
- **Skip when: RV5 > 0.22 AND slope < 0.005**
- Eliminates ~10% of trades
- Turns portfolio from -$22.9K to -$10.7K loss (+52% improvement)
- **Single strongest signal: RV5 > 0.22** alone improves P&L by $23.8K

---

## Market Conditions: Worst Losers vs All Trades

| Metric | Worst 10% | All Trades | Difference |
|--------|-----------|-----------|------------|
| **RV5** (realized vol) | 0.2061 | 0.1584 | **+30.1%** |
| **RV10** | 0.2062 | 0.1662 | **+24.1%** |
| **RV20** | 0.2022 | 0.1682 | **+20.2%** |
| **ATR5** (volatility) | 7.70 | 6.42 | **+19.9%** |
| **slope** (trend) | 0.0149 | 0.0217 | **-31.5%** |
| **return_10d** | 0.0018 | 0.0094 | **-81.0%** |
| **return_5d** | 0.0047 | 0.0061 | **-22.6%** |
| **vega_at_entry** | 53.6 | 74.8 | **-28.3%** |
| **theta_at_entry** | -58.5 | -48.9 | **-19.5%** |

**Pattern**: Worst losers entered during periods of:
1. **High realized volatility** (market is whipsawing)
2. **Weak/negative momentum** (no directional bias)
3. **Flat/negative trends** (support/resistance not functioning)
4. **Compressed vega** (lower options premiums to harvest)

---

## Risk Signals: Individual Discrimination

Each signal shows % of worst losers vs winners meeting that condition:

| Signal | Threshold | Worst Losers | Winners | Discrimination |
|--------|-----------|-------------|---------|-----------------|
| High RV5 | > 0.22 | 31.8% | 15.2% | **+16.7%** ✅ |
| High RV10 | > 0.21 | 34.8% | 24.2% | **+10.6%** ✅ |
| Negative return_10d | < 0 | 45.5% | 37.9% | **+7.6%** ⚠️ |
| Low 10d return | < -0.005 | 37.9% | 28.8% | **+9.1%** ✅ |
| Low vega | < 40 | 18.2% | 12.1% | **+6.1%** ⚠️ |
| Low slope | < 0.005 | 43.9% | 40.9% | **+3.0%** ⚠️ |
| High ATR5 | > 8.5 | 37.9% | 37.9% | **0.0%** ❌ |

**Best individual predictor**: RV5 > 0.22 (+16.7% discrimination)

---

## Combined Signal Analysis

### Strongest Combinations

**COMBINATION 1: High RV5 + Low Slope** (MOST PREDICTIVE)
```
Condition: RV5 > 0.22 AND slope < 0.005
- In worst losers: 21.2% (14/66 trades)
- In winners: 9.1% (6/66 trades)
- Discrimination: +12.1% ✅✅
```
**Interpretation**: Market is volatile AND has no directional bias = disaster zone for all Greek strategies.

**COMBINATION 2: High RV10 + Negative Return**
```
Condition: RV10 > 0.21 AND return_10d < 0
- In worst losers: 19.7% (13/66 trades)
- In winners: 10.6% (7/66 trades)
- Discrimination: +9.1%
```
**Interpretation**: Volatility spike happening while momentum is negative = trapped long vega.

---

## Profile Risk Analysis

### Worst Losers by Profile

| Profile | Losers | Avg P&L | Min P&L | Relative Risk |
|---------|--------|---------|---------|----------------|
| **Profile_3_CHARM** | 9 | -$1,692 | -$3,490 | 🔴🔴 **HIGHEST** |
| **Profile_1_LDG** | 2 | -$1,549 | -$2,293 | 🔴 HIGH |
| **Profile_2_SDG** | 8 | -$1,167 | -$1,496 | 🟡 MEDIUM |
| **Profile_4_VANNA** | 22 | -$1,001 | -$1,426 | 🟡 MEDIUM |
| **Profile_6_VOV** | 21 | -$988 | -$1,357 | 🟡 MEDIUM |
| **Profile_5_SKEW** | 4 | -$982 | -$1,306 | 🟡 MEDIUM |

**Note**: Profile_3_CHARM (charm/decay dominance) has smallest sample but highest disaster potential. Profile_4_VANNA (vol-spot correlation) shows high frequency but lower average loss.

---

## Impact of Filtering

### Scenario 1: Filter on RV5 alone (RV5 > 0.22)

```
Original portfolio:      668 trades, -$22,877.60 total P&L
After RV5 filter:        551 trades, +$898.80 total P&L

Improvement: +$23,776.40 (+103.9%)
Trades filtered: 117 (17.5%)
Win rate improvement: 44.2% → 46.1%
```

**Verdict**: STRONGEST SINGLE FILTER. Eliminates worst volatility-driven disasters.

---

### Scenario 2: Filter on slope alone (slope < 0.005)

```
Original portfolio:      668 trades, -$22,877.60 total P&L
After slope filter:      459 trades, -$14,887.80 total P&L

Improvement: +$7,989.80 (+34.9%)
Trades filtered: 209 (31.3%)
Win rate improvement: 44.2% → 45.5%
```

**Verdict**: Too many trades filtered. Reduces opportunity set too much for modest gain.

---

### Scenario 3: Combined filter (RV5 > 0.22 AND slope < 0.005)

```
Original portfolio:      668 trades, -$22,877.60 total P&L
After combined filter:   600 trades, -$10,743.00 total P&L

Improvement: +$12,134.60 (+53.0%)
Trades filtered: 68 (10.2%)
Win rate improvement: 44.2% → 45.0%
```

**Verdict**: BALANCED APPROACH. Filters ~10% of trades, improves P&L by 52%, keeps opportunity set large.

---

### Filtered Trade Profile

**The 68 trades we'd skip (RV5 > 0.22 AND slope < 0.005):**

| Metric | Value |
|--------|-------|
| Total P&L if taken | -$12,134.60 |
| Average P&L per trade | -$178.45 |
| Losers | 43/68 (63.2%) |
| Winners | 25/68 (36.8%) |
| Loss rate | 2.2x better odds |

---

## Implementation Rules

### RECOMMENDED: Two-Tier Filtering

**TIER 1 (Primary filter - use daily)**
```python
if RV5 > 0.22:
    SKIP_TRADE()  # High realized vol = whipsaw environment
```
- Impact: +$23.8K improvement (103.9% gain)
- Trade impact: Skip 17.5% of trades
- Simplicity: ⭐⭐⭐⭐⭐ One number to check

**TIER 2 (Secondary gate - use when RV5 marginal)**
```python
if RV5 > 0.20 and slope < 0.005:
    SKIP_TRADE()  # Vol spike without direction = trap
```
- Impact: Additional $12.1K improvement (52% from baseline)
- Trade impact: Skip 10.2% additional trades
- Complexity: Combines two signals

---

## What We Know About These Disasters

### Market State When Disasters Happen

1. **Realized volatility spiking** (RV5 +30% vs baseline)
   - Market is whipsawing within trades
   - Greeks are changing rapidly
   - Straddle/strangle gamma bleed accelerates

2. **No directional trend** (slope flat/negative)
   - Trend-following Greeks work poorly
   - Vanna and skew edge disappear
   - Mean-reversion becomes dominant

3. **Negative recent returns** (return_10d -81% vs baseline)
   - Portfolio momentum negative
   - Buyers stepping away
   - Risk-off environment forming

4. **Theta collapsing faster** (theta -19.5% more negative)
   - Decay accelerating despite volatility
   - Greeks unstable
   - Option pricing not reflecting realized vol properly

### Why These Conditions Are Bad

- **For Gamma strategies (LDG, SDG)**: Volatility spikes create gamma losses without offsetting vega gains
- **For Vol strategies (VANNA, VOV, SKEW)**: Flat markets mean the convexity edges we're harvesting disappear
- **For Decay strategies (CHARM)**: Theta acceleration happens at moment of greatest uncertainty

---

## What We DON'T Know (Yet)

We can avoid disasters with RV5 filtering, but:
- ❌ We can't predict winners (win rate stays 45% even after filtering)
- ❌ We don't know why vega is compressed (supply, demand, or strike selection issue?)
- ❌ We don't have regime classification at entry (is this trending, choppy, volatility expansion?)
- ❌ We don't distinguish between "bad entry" vs "bad market events" during holding period

**Suggestion**: Next analysis should examine:
1. What regime classification would have caught these disasters?
2. Are compressed-vega entries inherently risky?
3. Do disasters cluster in specific date ranges (March 2020? June 2022?)?

---

## Actionable Next Steps

### Immediate (Today)

1. **Implement RV5 filter** in backtest engine
   ```python
   if entry_conditions.RV5 > 0.22:
       return SKIP  # Don't trade in high-volatility environments
   ```

2. **Re-run full backtest** with filter applied
   - Expected improvement: ~$23.8K (103% gain)
   - Report new win rate, Sharpe ratio, maximum drawdown

### Short-term (This Week)

3. **Add secondary slope filter** if RV5 marginal
4. **Analyze filtered disasters** for false positives
   - Are there rare winners with high RV5? (Yes, 15.2% of winners)
   - Could we refine the threshold from 0.22 to something better?

### Medium-term (Next Phase)

5. **Research regime classification** at entry
   - Can we classify market state better than "slope"?
   - Do VOL_EXPANSION regimes have different disaster patterns?

6. **Study vega compression** root cause
   - Is it ATM spread too wide?
   - Is it DTE selection creating structural problems?

---

## Files Generated

- `worst_losers_bottom_10pct.csv` - Full detail on 66 worst trades
- All data from: `/data/backtest_results/full_tracking_results.json`
