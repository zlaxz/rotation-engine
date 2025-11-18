# DETAILED PROFILE BREAKDOWN - ALL 6 PROFILES

**Source:** data/backtest_results/runs/20251115_1651_post_bug_fixes/
**Period:** 2020-01-02 to 2024-12-31 (5 years)
**Total System:** 604 trades, $348,897 peak potential, $1,030 actual P&L (0.3% capture)

---

## PROFILE 1: LONG-DATED GAMMA (LDG)

**Strategy:** Buy long-dated options (45-120 DTE) when vol is cheap relative to realized, in uptrending markets

**Detection Logic** (src/profiles/detectors.py:112-145):
```python
# Factor 1: RV catching up to IV (cheap long vol)
factor1 = sigmoid((RV10/IV60 - 0.9) * 5)

# Factor 2: IV rank low (vol cheap in absolute terms)
factor2 = sigmoid((0.4 - IV_rank_60) * 5)

# Factor 3: Upward trend (positive slope)
factor3 = sigmoid(slope_MA20 * 100)

score = (factor1 * factor2 * factor3) ^ (1/3)  # Geometric mean
```

### Performance

| Metric | Value |
|--------|-------|
| **Trades** | 140 |
| **Winners** | 61 (43.6%) |
| **Total P&L** | **-$2,863** |
| **Peak Potential** | **$43,951** |
| **Capture Rate** | **-6.5%** |
| **Avg P&L/Trade** | -$20.45 |
| **Best Trade** | $2,268 |
| **Worst Trade** | -$744 |
| **Max Drawdown** | -$2,734 |
| **Avg Days to Peak** | 6.9 days |

### Peak Timing Pattern (from detailed analysis)

**Bimodal distribution:**
- **Early cluster (Days 1-5):** 30% of trades, median $130 peak
- **Mid period (Days 6-9):** 19% of trades, median $289 peak
- **Late cluster (Days 10-14):** 35% of trades, median $438 peak
- **Never profitable:** 16% of trades

**Critical insight:** 59% profitable by Day 2, but mean peak at Day 6.9

**Profitability vs Peak Timing:**
- Day 1: 45% of trades turn profitable
- Day 2: 59% profitable (quick gamma snap)
- Day 3: 76% profitable
- But peaks occur much later (median Day 7)

**Drawdown After Peak:** Brutal
- +1 day after peak: -66.5% median drawdown
- +2 days: -87.5%
- +5 days: -154.5%

### Key Finding

**Problem:** Fixed 14-day exit destroys value
- Positions turn profitable early (Day 1-2 gamma snap)
- Peaks occur mid-period (Day 7 median)
- Holding to Day 14 bleeds theta (-66% to -155% from peak)

**Solution needed:** Adaptive exit (harvest Day 3 quick wins, hold winners to Day 7 peak window)

---

## PROFILE 2: SHORT-DATED GAMMA SPIKE (SDG)

**Strategy:** Buy short-dated options (0-7 DTE) when short-term RV spikes faster than IV reprices

**Detection Logic** (src/profiles/detectors.py:147-179):
```python
# Factor 1: RV spiking vs short IV
factor1 = sigmoid((RV5/IV7 - 0.8) * 5)

# Factor 2: Large daily moves
move_size = abs(ret_1d) / (ATR5/close + 1e-6)
factor2 = sigmoid((move_size - 1.0) * 3)

# Factor 3: VVIX rising (vol-of-vol increasing)
factor3 = sigmoid(VVIX_slope * 1000)

score = (factor1 * factor2 * factor3) ^ (1/3)
# Then EMA smoothed (span=7) to reduce noise
```

### Performance

| Metric | Value |
|--------|-------|
| **Trades** | 42 |
| **Winners** | 15 (35.7%) |
| **Total P&L** | **-$148** |
| **Peak Potential** | **$16,330** |
| **Capture Rate** | **-0.9%** |
| **Avg P&L/Trade** | -$3.53 |
| **Best Trade** | $2,046 |
| **Worst Trade** | -$1,258 |
| **Max Drawdown** | -$1,365 |
| **Avg Days to Peak** | 4.5 days |

### Key Finding

**Observation:** Lowest trade count (42 trades in 5 years = 8/year)
- Detection is very selective (high threshold for short-term spike)
- Win rate only 35.7% (worst of all profiles)
- Peak timing fast (4.5 days avg) - appropriate for 0-7 DTE
- But exits still destroying value (-0.9% capture)

**Profile behavior:** Designed for violent moves (RV spike + VVIX rising)
- Rare but explosive opportunities
- Should exit quickly (0-7 DTE options decay fast)
- Current 14-day exit makes no sense for short-dated options

---

## PROFILE 3: CHARM/DECAY DOMINANCE (CHARM)

**Strategy:** Sell premium when IV elevated vs RV, market pinned, vol-of-vol declining

**Detection Logic** (src/profiles/detectors.py:181-212):
```python
# Factor 1: IV rich vs RV (vol overpriced)
factor1 = sigmoid((IV20/RV10 - 1.4) * 5)

# Factor 2: Market pinned (tight range <3%)
factor2 = sigmoid((0.035 - range_10d) * 100)

# Factor 3: VVIX declining (stable vol)
factor3 = sigmoid(-VVIX_slope * 1000)

score = (factor1 * factor2 * factor3) ^ (1/3)
```

### Performance

| Metric | Value |
|--------|-------|
| **Trades** | 69 |
| **Winners** | 44 (63.8%) |
| **Total P&L** | **-$1,051** |
| **Peak Potential** | **$121,553** |
| **Capture Rate** | **-0.9%** |
| **Avg P&L/Trade** | -$15.23 |
| **Best Trade** | $1,404 |
| **Worst Trade** | -$3,490 |
| **Max Drawdown** | -$5,361 |
| **Avg Days to Peak** | 0.0 days (?) |

### Key Finding

**CATASTROPHIC EXIT MISMATCH:**
- **HIGHEST peak potential** ($121K - 35% of total!)
- **WORST capture** (-0.9% - essentially zero)
- High win rate (63.8%) suggests entries work
- But exits are destroying ALL value

**Avg days to peak = 0.0?** This suggests immediate profitability (charm theta harvesting)
- Peak might occur on entry (selling overpriced premium)
- Then decays from there
- 14-day hold bleeds all the theta back

**Profile behavior:** Theta harvesting
- Should exit when IV normalizes or range expands
- Not time-based exits
- Needs regime-aware exit (exit when vol compression ends)

---

## PROFILE 4: VANNA CONVEXITY (VANNA)

**Strategy:** Buy when low IV, uptrend, stable vol-of-vol (benefit from vol-spot correlation)

**Detection Logic** (src/profiles/detectors.py:214-248):
```python
# Factor 1: Low IV rank (cheap vol)
factor1 = sigmoid((0.3 - IV_rank_20) * 5)  # Fixed bug (was inverted)

# Factor 2: Upward trend
factor2 = sigmoid(slope_MA20 * 100)

# Factor 3: VVIX stable/declining
factor3 = sigmoid(-VVIX_slope * 1000)

score = (factor1 * factor2 * factor3) ^ (1/3)
```

### Performance

| Metric | Value |
|--------|-------|
| **Trades** | 151 |
| **Winners** | 88 (58.3%) |
| **Total P&L** | **+$13,507** ✅ |
| **Peak Potential** | **$79,238** |
| **Capture Rate** | **+17.0%** ✅ |
| **Avg P&L/Trade** | +$89.45 |
| **Best Trade** | $1,924 |
| **Worst Trade** | -$1,283 |
| **Max Drawdown** | -$1,706 |
| **Avg Days to Peak** | 7.7 days |

### Key Finding

**ONLY PROFITABLE PROFILE**
- 17% capture rate (vs 0.3% overall)
- Most trades (151 in 5 years = 30/year)
- Best win rate (58.3%)
- Peak timing 7.7 days (similar to LDG)

**Why does VANNA work when others don't?**
- Hypothesis: Uptrend filter (factor2) creates directional bias
- Vanna benefits from spot moving up while vol stays stable
- 14-day exit might align better with trend duration
- Or: Vanna positions naturally converge to peak faster?

**This is the benchmark** - 17% capture is what "working exits" look like

---

## PROFILE 5: SKEW CONVEXITY (SKEW)

**Strategy:** Buy when skew steepening, vol-of-vol rising, RV catching up to IV

**Detection Logic** (src/profiles/detectors.py:250-280):
```python
# Factor 1: Skew steepening (z-score > 1)
factor1 = sigmoid((skew_z - 1.0) * 2)

# Factor 2: VVIX rising
factor2 = sigmoid(VVIX_slope * 1000)

# Factor 3: RV catching up to IV
factor3 = sigmoid((RV5/IV20 - 1.0) * 5)

score = (factor1 * factor2 * factor3) ^ (1/3)
# Then EMA smoothed (span=7)
```

### Performance

| Metric | Value |
|--------|-------|
| **Trades** | 30 |
| **Winners** | 8 (26.7%) |
| **Total P&L** | **-$3,337** |
| **Peak Potential** | **$11,784** |
| **Capture Rate** | **-28.3%** |
| **Avg P&L/Trade** | -$111.23 |
| **Best Trade** | $2,167 |
| **Worst Trade** | -$877 |
| **Max Drawdown** | -$1,349 |
| **Avg Days to Peak** | 4.8 days |

### Key Finding

**WORST PERFORMANCE:**
- Lowest trade count (30 trades = 6/year - very selective)
- Lowest win rate (26.7%)
- Worst capture rate (-28.3% - exits DESTROY value)
- Fast peak timing (4.8 days)

**Profile behavior:** Designed for fear events
- Skew steepening = put premium rising
- VVIX rising = vol becoming volatile
- These are "sell the rip" opportunities
- Fast peak (4.8 days) suggests quick resolution
- Holding 14 days makes zero sense

**Issue:** Either detection is wrong OR exits are catastrophically bad
- 26.7% win rate is concerning (suggests detection noise)
- But $11K peak shows SOME opportunities found
- -28% capture means exits are timed exactly wrong

---

## PROFILE 6: VOL-OF-VOL CONVEXITY (VOV)

**Strategy:** Buy straddles when VVIX elevated, rising, and IV is cheap (vol about to expand)

**Detection Logic** (src/profiles/detectors.py:282-318):
```python
# Factor 1: VVIX elevated vs 80th percentile
factor1 = sigmoid((VVIX/VVIX_80pct - 1.0) * 5)

# Factor 2: VVIX rising
factor2 = sigmoid(VVIX_slope * 1000)

# Factor 3: IV rank LOW (buy cheap vol)
factor3 = sigmoid((0.5 - IV_rank_20) * 5)  # Fixed bug (was inverted)

# Factor 4: RV/IV compression (vol about to expand)
factor4 = sigmoid((1.0 - RV10/IV20) * 5)  # Added compression detection

score = (factor1 * factor2 * factor3 * factor4) ^ (1/4)
```

### Performance

| Metric | Value |
|--------|-------|
| **Trades** | 172 |
| **Winners** | 61 (35.5%) |
| **Total P&L** | **-$5,077** |
| **Peak Potential** | **$76,041** |
| **Capture Rate** | **-6.7%** |
| **Avg P&L/Trade** | -$29.52 |
| **Best Trade** | $3,456 |
| **Worst Trade** | -$1,335 |
| **Max Drawdown** | -$5,498 |
| **Avg Days to Peak** | 6.9 days |

### Key Finding

**Most active profile (172 trades = 34/year)**
- Detects vol expansion opportunities frequently
- But low win rate (35.5%)
- Peak potential solid ($76K - 22% of total)
- Exits destroying value (-6.7% capture)

**Profile behavior:** Vol expansion plays
- VVIX elevated + rising = vol becoming more volatile
- IV cheap + compressed = about to expand
- Correct thesis: Buy cheap vol before expansion
- Peak timing 6.9 days (same as LDG)

**Recent fixes** (from METADATA):
- Inverted IV_rank condition (was buying expensive vol!)
- Added compression detection factor
- These fixes may not be validated yet

---

## COMPARATIVE SUMMARY

### Peak Potential (Entry Quality)

| Profile | Peak $ | % of Total | Trades | $/Trade Peak |
|---------|--------|-----------|--------|--------------|
| **Profile 3 (CHARM)** | $121,553 | 34.9% | 69 | $1,762 |
| **Profile 4 (VANNA)** | $79,238 | 22.7% | 151 | $525 |
| **Profile 6 (VOV)** | $76,041 | 21.8% | 172 | $442 |
| **Profile 1 (LDG)** | $43,951 | 12.6% | 140 | $314 |
| **Profile 2 (SDG)** | $16,330 | 4.7% | 42 | $389 |
| **Profile 5 (SKEW)** | $11,784 | 3.4% | 30 | $393 |
| **TOTAL** | **$348,897** | 100% | 604 | $578 |

**Key insight:** CHARM has highest peak potential despite worst capture

### Actual P&L (Exit Quality)

| Profile | Actual P&L | Capture % | Status |
|---------|-----------|-----------|--------|
| **Profile 4 (VANNA)** | +$13,507 | +17.0% | ✅ ONLY WINNER |
| **Profile 2 (SDG)** | -$148 | -0.9% | ❌ |
| **Profile 3 (CHARM)** | -$1,051 | -0.9% | ❌ WORST CAPTURE |
| **Profile 1 (LDG)** | -$2,863 | -6.5% | ❌ |
| **Profile 5 (SKEW)** | -$3,337 | -28.3% | ❌ DESTROYS VALUE |
| **Profile 6 (VOV)** | -$5,077 | -6.7% | ❌ |
| **TOTAL** | **+$1,030** | **+0.3%** | ❌ |

### Trade Frequency

| Profile | Trades (5yr) | Avg/Year | Activity |
|---------|-------------|----------|----------|
| Profile 6 (VOV) | 172 | 34 | Most active |
| Profile 4 (VANNA) | 151 | 30 | Very active |
| Profile 1 (LDG) | 140 | 28 | Active |
| Profile 3 (CHARM) | 69 | 14 | Moderate |
| Profile 2 (SDG) | 42 | 8 | Selective |
| Profile 5 (SKEW) | 30 | 6 | Very selective |

### Win Rates

| Profile | Win Rate | Assessment |
|---------|----------|------------|
| Profile 3 (CHARM) | 63.8% | Best (theta harvesting) |
| Profile 4 (VANNA) | 58.3% | Good |
| Profile 1 (LDG) | 43.6% | Acceptable |
| Profile 2 (SDG) | 35.7% | Poor |
| Profile 6 (VOV) | 35.5% | Poor |
| Profile 5 (SKEW) | 26.7% | Worst (detection noise?) |

### Peak Timing

| Profile | Avg Days to Peak | Implication |
|---------|-----------------|-------------|
| Profile 3 (CHARM) | 0.0 | Immediate (theta harvesting) |
| Profile 2 (SDG) | 4.5 | Fast (short-dated) |
| Profile 5 (SKEW) | 4.8 | Fast (fear spike) |
| Profile 1 (LDG) | 6.9 | Medium (gamma evolution) |
| Profile 6 (VOV) | 6.9 | Medium (vol expansion) |
| Profile 4 (VANNA) | 7.7 | Slow (trend + vol correlation) |

---

## CRITICAL INSIGHTS

### 1. Entry Detection Works (All 6 Profiles)

**Evidence:**
- Total $348K peak potential across all profiles
- Distributed across different market conditions
- Each profile finds specific opportunities

### 2. Exit Logic is Catastrophically Broken

**Evidence:**
- 5 of 6 profiles have NEGATIVE or near-zero capture
- Profile 3: $121K peak → -$1K actual (worst mismatch)
- Profile 5: -28% capture (exits timed exactly wrong)
- **Only Profile 4 works at 17% capture**

### 3. One-Size-Fits-All Exits Don't Work

**Current:** 14-day fixed exit for ALL profiles

**Problem:**
- CHARM peaks at Day 0 (immediate theta)
- SDG/SKEW peak at ~5 days (short-dated, fear spikes)
- LDG/VOV peak at ~7 days (gamma evolution)
- VANNA peaks at 7.7 days (trend development)

**14-day exit:**
- Too long for CHARM (bleeds theta back)
- Too long for SDG/SKEW (short-dated decay)
- Slightly too long for LDG/VOV
- Approximately correct for VANNA (why it works?)

### 4. Profile-Specific Exit Strategies Needed

**Profile 1 (LDG):** Two-tier (Day 3 harvest + Day 7 peak window)
**Profile 2 (SDG):** Quick exit (Day 3-5, short-dated options)
**Profile 3 (CHARM):** Regime-based (exit when compression ends, not time-based)
**Profile 4 (VANNA):** Current ~7-10 day window seems to work
**Profile 5 (SKEW):** Fast exit (Day 3-5, fear spikes resolve quickly)
**Profile 6 (VOV):** Medium (Day 5-7, vol expansion window)

---

## NEXT STEPS

**IMMEDIATE:**
1. Fix empyrical bugs (can't trust metrics until this is done)
2. Document current exit logic (where is "14-day" exit coming from?)

**HIGH PRIORITY:**
3. Build adaptive exit system:
   - Profile-specific peak windows
   - Regime-aware exits (not just time-based)
   - Use Greeks evolution to detect peak passage

**RESEARCH:**
4. Why does Profile 4 work when others don't?
   - Is it the uptrend filter?
   - Is peak timing more stable?
   - Are Greeks evolution patterns different?

**VALIDATION:**
5. Test if $348K peak holds across walk-forward periods
   - If stable → Entry detection works, focus on exits
   - If collapses → Entry detection overfit, bigger problem

---

**Analysis Date:** 2025-11-18
**Data:** data/backtest_results/runs/20251115_1651_post_bug_fixes/
**Status:** Infrastructure clean, entries finding opportunities, exits destroying 99.7% of value
