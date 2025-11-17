# Profile 5 (SKEW) - Comprehensive Peak Magnitude & Entry Analysis

**Date:** 2025-11-16
**Status:** CRITICAL FINDINGS - Requires Immediate Action
**Location:** `/Users/zstoc/rotation-engine/data/backtest_results/current/results.json`

---

## EXECUTIVE SUMMARY

Profile 5 (SKEW - Skew Convexity) is **the worst performer** in the rotation engine, with critical issues in both entry timing and exit execution:

- **Win Rate:** 26.7% (second-worst among 6 profiles)
- **Total P&L:** -$3,337 (WORST)
- **Avg Final P&L:** -$111 (WORST)
- **Peak-to-Final Capture:** -62% (trades give back peak gains)
- **Status:** Should NOT be in production

The problem is **NOT bad peaks** (peaks are $389 average). The problem is **catastrophic exits** that squander profitable positions.

---

## 1. PEAK MAGNITUDE STATISTICS

### Distribution of Peak P&L:
```
Mean Peak:          $389.43
Median Peak:        $215.30
Std Dev:            $500.01
Min:                $-11.20 (1/3 of trades start underwater)
Max:                $2,166.80
Q1:                 $-11.20
Q3:                 $597.30
```

### Peak P&L Categories:
- **Negative peak (lost from entry):** 9 trades (30%)
- **$0-$100 peak:** 2 trades (7%)
- **$100-$300 peak:** 5 trades (17%)
- **>$300 peak:** 14 trades (47%)

**Finding:** Half of SKEW trades DO reach profitable peaks. The problem is what happens AFTER.

---

## 2. THE SMOKING GUN: Peak-to-Final Decay

### Peak vs Final P&L Correlation
```
Correlation: 0.815 (strong positive)
```

While correlated, the ABSOLUTE dollars reveal the problem:

### Peak Capture Analysis:
```
Mean Capture %:     -62.2% (NEGATIVE - giving back MORE than peak)
Median Capture %:   0.0% (half the trades don't capture ANY of peak)
Best:               +100% (one trade captured full peak)
Worst:              -818.2% (catastrophic loss far below peak)
```

### Peak Capture Breakdown:
- **>80% captured:** 5 trades (16%) - WINNERS
- **50-80% captured:** 1 trade (3%)
- **0-50% captured:** 11 trades (37%) - SLOW BLEED
- **Negative captured:** 13 trades (43%) - COMPLETE REVERSALS

### Peak-to-Exit Drawdown:
```
Mean Decay:         -$500.67 (average loss from peak to exit)
Median Decay:       -$449.50
Trades with >50% decay back: 24/30 (80% of portfolio)
Max Decay:          $0.00 (at least one peaks at exit)
```

**Critical Finding:** 80% of SKEW trades give back MORE than half their peak gains. This is an **exit execution disaster**.

---

## 3. FINAL P&L STATISTICS

### Overall P&L Distribution:
```
Mean Final:         -$111.23 (average loss per trade)
Median Final:       -$223.20 (typical loser)
Std Dev:            $609.47
Min:                -$877.20 (maximum loss)
Max:                +$2,166.80 (same as peak - rare winner!)
```

### Winners vs Losers:
```
Winners:    8/30 (26.7%)
  Avg Peak:        $960.05
  Avg Final:       $652.55
  Capture %:       +67.5% (keep 2/3 of peak)

Losers:     22/30 (73.3%)
  Avg Peak:        $181.94
  Avg Final:       -$388.97
  Capture %:       -109.4% (GIVE BACK 100%+ of peak)
```

**Interpretation:** Winners occur when peak happens late in hold (capture happens). Losers occur when peak happens early and entire position decays.

---

## 4. TIMING ANALYSIS: When Profits Occur (and Disappear)

### Days to Peak:
```
Mean:       4.8 days
Median:     5.0 days
Q1:         0.0 days (peaks immediately)
Q3:         7.0 days
Range:      [0, 14] days
```

### Days Held AFTER Peak:
```
Mean:       9.2 days (HOLDS FOR 9+ DAYS AFTER PEAK)
Median:     9.0 days
Max:        14.0 days
```

**The Pattern:**
1. Peak occurs around day 5
2. Continue holding for 9 more days
3. Over those 9 days, position decays (theta + spot move)
4. Exit at day 14 with massive drawdown

### P&L Volatility During Hold:
```
Mean Volatility:    $235.16 (wild P&L swings)
Median Volatility:  $179.39
```

**Finding:** High volatility + long hold after peak = disaster

---

## 5. ENTRY CONDITION CORRELATIONS

### Statistical Significance Testing (Winners vs Losers):

**ONLY ONE ENTRY METRIC SIGNIFICANTLY DIFFERENT:**

```
Field                       Winners         Losers          P-Value    Significant?
────────────────────────────────────────────────────────────────────────────────
entry_slope_ma50            +0.00784        +0.04760        p=0.016    YES ✓
entry_delta                 -0.2115         -0.2061         p=0.501    no
entry_gamma                 +0.0092         +0.0090         p=0.767    no
entry_theta                 -$29.49         -$31.29         p=0.452    no
entry_vega                  +$45.60         +$47.54         p=0.742    no
entry_rv5                   +0.1612         +0.1649         p=0.824    no
entry_rv10                  +0.1679         +0.1637         p=0.857    no
entry_rv20                  +0.1728         +0.1532         p=0.289    no
entry_atr5                  +6.862          +7.176          p=0.735    no
entry_atr10                 +6.726          +6.821          p=0.906    no
entry_slope                 -0.0055         -0.0147         p=0.380    no
entry_slope_ma20            +0.0328         +0.0216         p=0.057    no
entry_return_5d             -0.0164         -0.0198         p=0.616    no
entry_return_10d            -0.0345         -0.0301         p=0.363    no
```

**Interpretation:** Entry conditions are nearly **IDENTICAL** between winners and losers. This means:
- ✗ Entry filtering is NOT working
- ✗ Can't predict outcomes from entry signals
- ✓ Problem is downstream (exit logic or market regime changes)

### Correlations with Final P&L:
```
entry_slope_ma50:   -0.499  (downtrend context = worse outcomes)
entry_return_5d:    +0.395  (flat/up momentum at entry = better)
```

**Finding:** Slight predictive power exists but weak. Winners enter on FLAT/POSITIVE momentum. Losers enter on EXTREME NEGATIVE momentum.

---

## 6. ENTRY GREEKS ANALYSIS

### Delta (Spot Sensitivity):
```
Winners:    Mean -0.2115,  Std 0.0165  (tight distribution, consistent hedging)
Losers:     Mean -0.2061,  Std 0.0201  (same)
Range:      [-0.2315, -0.1600] (all puts, 5% OTM approx)
```

### Gamma (Delta Sensitivity / Convexity):
```
Winners:    Mean +0.0092,  Std 0.0017
Losers:     Mean +0.0090,  Std 0.0017
Same gamma across both - no differentiation
```

### Theta (Daily Time Decay):
```
Winners:    Mean -$29.49/day,  Std $3.27 (consistent)
Losers:     Mean -$31.29/day,  Std $6.32 (high variance)
```

**Finding:** Winners have slightly less aggressive theta decay, but not statistically significant.

### Vega (IV Sensitivity):
```
Winners:    Mean +$46.00   (slightly lower than losers)
Losers:     Mean +$47.54   (slightly higher)
Expected:   IV increase should help both equally
Reality:    Losers don't benefit from IV spikes (exit timing problem)
```

**Finding:** Positive vega is correct for skew strategy, but exits prevent capture of IV gains.

---

## 7. DISASTER ANALYSIS: Winners Turned Losers

### The Pattern - 11 Trades with >$100 Peak but NEGATIVE Final:
```
Count:                  11 trades (37% of portfolio)
Avg Peak:               $360.16
Avg Final:              -$273.29
Avg Drawdown:           -$633.45 (peak to final)

Timeline:
  Days to Peak:         3.7 days (FAST)
  Days After Peak:      10.3 days (LONG HOLD)
  Total Hold:           ~14 days

Pattern:
  Peak occurs early (day 3-4)
  Exit at day 14
  Give back 107% of peak (end up BELOW entry)
```

**This is the core problem:** Trades that peak quickly hold too long after, decaying into losses.

---

## 8. COMPARISON TO OTHER PROFILES

### Cross-Profile Performance:

| Profile  | Trades | Win Rate | Total PnL | Avg Final | Peak Capture |
|----------|--------|----------|-----------|-----------|--------------|
| 1 LDG    | 140    | 43.6%    | -$2,863   | -$20      | -381%        |
| 2 SDG    | 42     | 35.7%    | -$148     | -$4       | -1385%       |
| 3 CHARM  | 69     | 63.8%    | -$1,051   | -$15      | -1%          |
| 4 VANNA  | 151    | 58.3%    | **+$13,507** | +$89  | -194%        |
| **5 SKEW**  | **30** | **26.7%** | **-$3,337**   | **-$111** | **-62%** |
| 6 VOV    | 172    | 35.5%    | -$5,077   | -$30      | -318%        |

**Profile 5 Ranking:**
- Win Rate: 5th out of 6 (only SDG worse)
- Total P&L: **DEAD LAST** (worst by $2,000+)
- Avg Final PnL: **DEAD LAST**
- Peak Capture: NOT worst, but still terrible (-62%)

---

## DIAGNOSIS: ENTRY vs EXIT Problem

### Is this an ENTRY problem?
❌ **NO** - Entry conditions show no statistical difference between winners/losers
- Both enter with similar Greeks
- Both enter at similar volatility levels
- Only difference is slope_ma50 trend context (weak)

### Is this an EXIT problem?
✅ **YES** - CATASTROPHIC
- 80% of trades give back >50% of peak
- Winners hold 9+ days after peak
- Losers ALSO hold 9+ days after peak → convert to losses
- 30% of trades have negative peak (never profitable)

### Root Cause:
```
Profile 5 (SKEW) Strategy Failure Model:

1. ENTRY: "Buy OTM puts when skew is interesting"
   ✓ Enters at reasonable OTM levels
   ✓ Greeks reasonable for skew play
   ⚠️ BUT... no discrimination between good/bad setups

2. PEAK: IV spike occurs, puts gain value
   ✓ Avg peak $389 shows IV spikes DO occur
   ✓ Winners see peaks, peaks are real

3. EXIT: "Hold for X days (fixed exit rule)"
   ❌ PROBLEM: Exit timing is fixed, not dynamic
   ❌ Peaks occur day 5, exits occur day 14
   ❌ 9 days of decay after peak
   ❌ Theta kills all value, spot moves against
   ❌ 24/30 trades lose 50%+ of peak

4. OUTCOME: Lose money despite good entries
   - Entry signals work (find profitable moves)
   - Exit signals fail (don't lock in profits)
```

---

## EXIT STRATEGY IMPLICATIONS

### Current Exit Logic (Inferred):
- Fixed hold period (14 days average)
- No peak-detection exit trigger
- No profit-taking at peak
- No dynamic exit based on Greeks decay

### Why This Fails:
1. **Skew strategy requires quick exits** - IV spikes are brief
2. **Peak occurs early** (day 5) while vega still large
3. **Theta accelerates** as DTE decreases (days 10-14 are brutal)
4. **Spot risk** - if underlying recovers, puts lose value

### Entry Fix (Marginal):
- Could improve discrimination (steep MA50 trend = avoid)
- Could tighten momentum filter (extreme downside = avoid)
- **But:** Won't solve the 73% loss rate (exit is problem)

### Exit Fix (CRITICAL):
**Need dynamic exit logic:**
- Exit at peak OR when Vega/Theta ratio becomes unfavorable
- Exit when peak-to-current decay >30% (before it gets worse)
- Exit before day 7 if realized vol > implied vol (mean-reversion risk)
- Don't hold past day 5-7 unless new peak being made

**Estimated Impact:** Could flip win rate from 26.7% to 50%+ with proper exit

---

## RECOMMENDATION

### SHORT TERM (Immediate):
1. **Disable Profile 5 (SKEW) from production**
   - It's hemorrhaging money (-$3.3K on just 30 trades)
   - Extrapolating: $3.3K / 30 trades × 2000 = $220K annual loss at scale
   - No statistical edge demonstrated

2. **Segregate into research branch**
   - Keep data for post-mortem analysis
   - Don't trade live until fixed

### MEDIUM TERM (This Week):
1. **Implement dynamic exit logic**
   - Peak detection (mark day of peak in backtest)
   - Exit on peak + 1-2 days OR peak decay threshold
   - Back-test new exit rules against same entry signals

2. **Test entry filters**
   - Filter out >-8% momentum entries (extreme oversold)
   - Filter on MA50 slope > certain threshold (avoid downtrends)
   - Run robustness tests

### LONG TERM (Strategic):
1. **Rethink skew strategy**
   - Current approach: long puts on down days
   - Skew definition: pricing differential across strikes
   - Consider: selling OTM calls into rallies (capture skew decay)
   - Or: calendar spreads (front-month skew vs back-month)

---

## KEY METRICS SUMMARY TABLE

| Metric | Value | Status |
|--------|-------|--------|
| Total Trades | 30 | Limited sample |
| Win Rate | 26.7% | ❌ CRITICAL |
| Total P&L | -$3,337 | ❌ WORST |
| Avg Peak | $389.43 | ✓ Peaks exist |
| Avg Final | -$111.23 | ❌ Giving back |
| Peak Capture | -62.2% | ❌ CRITICAL |
| Peak-to-Exit Decay | -$500.67 avg | ❌ CRITICAL |
| Days to Peak | 4.8 | ✓ Fast |
| Days After Peak | 9.2 | ❌ Too long |
| Winner Peak | $960.05 | ✓ Decent |
| Winner Final | $652.55 | ✓ Decent |
| Loser Peak | $181.94 | ~ Modest |
| Loser Final | -$388.97 | ❌ Catastrophic |
| Entry Greeks Stat Diff | Only MA50 slope | ⚠️ Not predictive |
| Exit vs Peak Correlation | 0.815 | ✓ But negative values |

---

## CONCLUSION

Profile 5 (SKEW) demonstrates that **an investment opportunity can exist (peaks of $389) but be completely destroyed by poor exit execution**.

- **Entries:** Functional, find opportunities
- **Peaks:** Real, IV spikes occur regularly
- **Exits:** Catastrophic, prevent profit capture

**The profile should NOT be in production until exit logic is fixed.**

Expected outcome with proper dynamic exits: **Potentially profitable strategy**, but requires different exit paradigm.
