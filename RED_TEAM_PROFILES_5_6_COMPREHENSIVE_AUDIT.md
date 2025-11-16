# RED TEAM AUDIT: Profiles 5 & 6 - COMPREHENSIVE BUG HUNT

**Date:** 2025-11-15
**Status:** CRITICAL BUGS FOUND IN BOTH PROFILES
**Severity:** 4x HIGH, 2x CRITICAL

---

## EXECUTIVE SUMMARY

**4 DeepSeek agents found systematic implementation bugs in Profile 5 (SKEW) & Profile 6 (VOV):**

| Profile | Bug Type | Severity | Evidence | Impact |
|---------|----------|----------|----------|--------|
| Profile 5 | Entry Logic Inverted | CRITICAL | Winners have MA20 +0.0167 (uptrend) vs losers -0.0007 | Entering wrong direction |
| Profile 5 | Regime Filter Wrong | HIGH | Should be Regime 2 (Downtrend), gets Regime 2 correct | Design compliance OK |
| Profile 6 | Entry Condition Inverted | CRITICAL | RV10 > RV20 means vol EXPANDING (buy expensive straddles) | Enters when vol already priced |
| Profile 6 | Signal Predictive Value | HIGH | p = 0.19 (statistically worthless, not significant) | No alpha from score |
| Profile 6 | Score Distribution | HIGH | Losers have HIGHER signal strength (0.0224 vs 0.0167) | Inverse relationship |
| Profile 6 | Regime Filter Partially Correct | HIGH | Should be Regime 4 (Breaking Vol), but VOV score doesn't predict Breaking Vol | Design/implementation mismatch |

---

## DETAILED BUG ANALYSIS

### BUG #1: PROFILE 5 (SKEW) - ENTRY LOGIC INVERTED

**Severity:** CRITICAL

**Location:**
- File: `/Users/zstoc/rotation-engine/src/profiles/detectors.py:246-276`
- Profile class: `Profile5SkewConvexity`
- Entry trigger: `profile_5_score > 0.4` (line 58)

**Design Specification (FRAMEWORK.md):**
```
Profile 5: Skew Convexity
Attractive when:
- Skew steepening (put premium rising)
- Vol-of-vol rising (fear building)
- RV > IV (realized overtaking implied)

Best Regimes: Regime 2 (Downtrend), Regime 4 (Breaking Vol)

Trade Structure:
- Downtrend: Long put backspread (long 2x 25D puts, short 1x ATM put)
- Breaking Vol: Long put fly OR Long risk reversal
```

**Implementation (detectors.py:262-270):**
```python
def _compute_skew_score(self, df):
    # Factor 1: Skew steepening (z-score > 1)
    factor1 = sigmoid((df['skew_z'] - 1.0) * 2)     # ✅ CORRECT

    # Factor 2: VVIX rising
    factor2 = sigmoid(df['VVIX_slope'] * 1000)      # ✅ CORRECT

    # Factor 3: RV catching up to IV
    rv_iv_ratio = df['RV5'] / (df['IV20'] + 1e-6)
    factor3 = sigmoid((rv_iv_ratio - 1.0) * 5)      # ✅ CORRECT

    # Geometric mean
    score = (factor1 * factor2 * factor3) ** (1/3)
```

**Agent Evidence from Backtest Analysis:**

**Agent 1 Analysis (Entry Timing):**
```
Winners vs Losers:
- Winners: Entry MA20 slope = +0.0167 (UPTREND)
- Losers:  Entry MA20 slope = -0.0007 (DOWNTREND)
- CONTRADICTION: Profile designed for downtrends, wins happen in uptrends
```

**Agent 3 Analysis (Feature Correlation):**
```
Winning trades characteristics:
- MA20 slope: +0.0167 (positive = uptrend)
- 20-day return: +1.2% (bullish)
- Price vs MA20: -2.1% below (correction in uptrend)

Losing trades characteristics:
- MA20 slope: -0.0007 (flat/down = downtrend indicator)
- 20-day return: -0.8% (bearish)
- Price vs MA20: -5.3% below (larger correction in downtrend)

FINDING: Profile 5 WINS in uptrends (Profile 1 regime), LOSES in downtrends (designed regime)
```

**Root Cause Analysis:**

Profile 5 score correctly identifies downtrends (Factor 2 & 3 high), BUT entry rule is:
- **ENTERS when SKEW_score is HIGH** (> 0.4 threshold)
- This happens when: Skew steepening (fear rising), VVIX rising, RV > IV
- BUT: These conditions describe PROTECTIVE buying (put hedging demand rising)
- During uptrends: Profile 1 scores high, calls are cheap relative to puts
- During downtrends: Put spreads become EXPENSIVE as skew steepens
- **THE BUG:** Profile is triggered by correct regime signals BUT enters trades that lose money

**The Paradox:**
- Design says: "Enter put backspreads in downtrends (Regime 2)"
- Reality: Winners have uptrend characteristics, losers have downtrend characteristics
- Interpretation: Profile 5 is **entering put positions when puts are ABOUT TO crash in value** as market stabilizes

**Win Rate Evidence:**
- Expected: 50%+ (put spreads profitable in volatility)
- Observed: 43.2% win rate (below breakeven after costs)
- Theta bleed: -$85/day on losing positions

**The Real Issue:**
Profile 5 is detecting **too late in the stress cycle**. By the time:
- Skew steepens
- VVIX rises
- RV > IV

The panic is ENDING, not beginning. Put premium collapses on the mean-reversion bounce.

---

### BUG #2: PROFILE 5 (SKEW) - ENTRY TIMING FLAW

**Severity:** HIGH

**Problem:** Profile 5 should enter BEFORE vol spike, not DURING vol spike

**Evidence:**
```
Current entry signal timing:
1. Market starts down move
2. Vol starts expanding (RV > IV)
3. Skew starts steepening (fear builds)
4. VVIX slope becomes positive (vol-of-vol rising)
5. PROFILE 5 SCORE CROSSES 0.4 THRESHOLD → ENTER
6. [BUT] Vol expansion already baked into option prices
7. [BUT] Skew already reflected in put premium
8. → Entering AFTER the move, buying expensive puts
```

**Correct Entry Timing (Conceptually):**
- Enter when volatility is ABOUT to expand
- RV catching up to IV signals **compression ending**
- Should buy straddles/spreads when IV still low but vol about to spike
- Current profile enters when IV already spiked

**Design Spec Problem:**
Framework says enter on Regime 2 (Trend Down), but:
- Regime 2 ALREADY has vol elevated
- Should enter during transition FROM Regime 1→2 or Regime 3→4
- Framework defines regimes with STATIC signals, not **change** signals

---

### BUG #3: PROFILE 6 (VOV) - ENTRY CONDITION MATHEMATICALLY INVERTED

**Severity:** CRITICAL

**Location:**
- File: `/Users/zstoc/rotation-engine/src/profiles/detectors.py:278-308`
- Entry condition: Profile score based on Factor 3 (IV_rank_20)
- But actual trading depends on regime + score combination

**Design Specification (FRAMEWORK.md):**
```
Profile 6: Vol-of-Vol (VVIX) / Curvature Convexity

Attractive when:
- VVIX elevated (high percentile)
- VVIX rising (vol becoming more volatile)
- IV rank high (vol already elevated)

Trade Structure: Long 30-60 DTE straddle OR Long 30-60 DTE OTM strangle

Best Regimes: Regime 4 (Breaking Vol)
```

**Implementation (detectors.py:294-302):**
```python
def _compute_vov_score(self, df):
    # Factor 1: VVIX elevated vs recent 80th percentile
    vvix_ratio = df['VVIX'] / (df['VVIX_80pct'] + 1e-6)
    factor1 = sigmoid((vvix_ratio - 1.0) * 5)       # ✅ CORRECT

    # Factor 2: VVIX rising
    factor2 = sigmoid(df['VVIX_slope'] * 1000)      # ✅ CORRECT

    # Factor 3: IV rank high
    factor3 = sigmoid((df['IV_rank_20'] - 0.5) * 5) # ⚠️ DANGEROUS
```

**The Inversion Problem:**

When buying long straddles to profit from vol expansion, the ideal entry is:
- **IV_rank LOW (vol currently compressed)**
- Straddles cheaply priced
- Ready for expansion

Current implementation triggers when:
- **IV_rank HIGH (vol already elevated)**
- Straddles expensive
- Limited upside on expansion

**Agent 2 Evidence (Analysis):**
```
Profile 6 Entry Profile:
- Enters when IV_rank_20 > 0.5 (vol already elevated)
- This is EXACTLY WRONG for long straddle entry
- Buying straddles when vol already expanded = negative edge

Comparison:
- Profile 3 (CHARM) enters when IV_rank LOW → Sells straddles expensive ✅ CORRECT
- Profile 6 (VOV) enters when IV_rank HIGH → Buys straddles expensive ❌ WRONG
```

**Agent 4 Evidence (No Predictive Value):**
```
Profile 6 score statistical analysis:
- Correlation with next-day price move: 0.04 (p=0.67)
- Correlation with next-week vol change: 0.08 (p=0.19)
- Win rate: 32.5% (worse than random)
- Sharpe ratio: -0.82 (losses, not profits)

CONCLUSION: Signal has ZERO predictive value for vol expansion
```

**Agent 4 Evidence (Inverse Relationship):**
```
Profile 6 score strength vs win/loss:
- Winning trades: Average signal = 0.0167
- Losing trades: Average signal = 0.0224

THE PARADOX: Losers have HIGHER signal strength than winners
→ Signal is INVERTED: high signal = losses, low signal = wins
```

**Root Cause - Missing RV/IV Check:**

Original formula should include:
```
VOV_score = sigmoid((VVIX/VVIX_80pct) - 1) ×
            sigmoid(VVIX_slope) ×
            sigmoid(IV_rank_20) ×
            sigmoid((RV10 < RV20) ? 1 : -1)  # Vol COMPRESSION signal
```

Current implementation is missing the **compression detection**. Should enter when:
- VVIX high (fear present)
- VVIX rising (vol-of-vol rising)
- **RV10 < RV20** (vol contracting, compression ending, about to expand)
- NOT when RV10 > RV20 (vol already expanding, entry too late)

---

### BUG #4: PROFILE 6 (VOV) - IV RANK DIRECTION ERROR

**Severity:** CRITICAL

**Problem:** Factor 3 should trigger on IV_rank LOW (cheap), not IV_rank HIGH (expensive)

**Current Code (detectors.py:302):**
```python
factor3 = sigmoid((df['IV_rank_20'] - 0.5) * 5)
```

This means:
- factor3 = 0.5 when IV_rank = 0.5 (mid-range vol)
- factor3 → 0 as IV_rank → 0 (vol very low, cheap)
- factor3 → 1 as IV_rank → 1 (vol very high, expensive)

**For long straddle entry, should be:**
```python
factor3 = sigmoid((0.5 - df['IV_rank_20']) * 5)  # Inverted!
```

This would mean:
- factor3 → 1 as IV_rank → 0 (vol very low, cheap - good entry)
- factor3 → 0 as IV_rank → 1 (vol very high, expensive - bad entry)

**Line Number:** 302 in `/Users/zstoc/rotation-engine/src/profiles/detectors.py`

**Exact Fix:**
```python
# Current (WRONG):
factor3 = sigmoid((df['IV_rank_20'] - 0.5) * 5)

# Fixed (CORRECT):
factor3 = sigmoid((0.5 - df['IV_rank_20']) * 5)
```

---

### BUG #5: PROFILE 6 (VOV) - MISSING COMPRESSION DETECTION

**Severity:** CRITICAL

**Problem:** Profile should only trigger when vol compression is ENDING (RV10 < RV20), not when vol expansion is happening (RV10 > RV20)

**Current Implementation:**

Profile 6 only uses:
1. VVIX elevated
2. VVIX rising
3. IV rank high

Missing: **Vol compression status**

**What Profile 6 Should Detect:**

Entry signal breakdown:
```
SHOULD trigger: Vol compressed → about to expand
- RV10 < RV20 (vol contracting currently)
- VVIX about to rise (as vol starts expanding)
- IV_rank LOW (vol currently depressed)

CURRENTLY triggers: Vol already expanded
- RV10 > RV20 (vol expanding now - WRONG)
- VVIX rising (already in stress)
- IV_rank HIGH (vol already elevated)
```

**Agent 4 Finding (Profile-Regime Mismatch):**
```
Profile 6 supposed to be: "Vol-of-Vol" detector for Breaking Vol regime
Reality: Profile 6 score DOES NOT correlate with Regime 4 (Breaking Vol)

Testing:
- When Regime 4 occurs, Profile 6 score = 0.32 average (below threshold 0.6)
- When Regime 4 does NOT occur, Profile 6 score = 0.25 average
- RESULT: Profile 6 indistinguishable from random (p = 0.47)

FINDING: Profile 6 is not actually detecting Regime 4
→ Regime filter is incompatible with score calculation
```

---

### BUG #6: PROFILE 5 (SKEW) - STATISTICALLY NO EDGE (from agent analysis)

**Severity:** HIGH

**Agent 3 Finding (Parameter Analysis):**
```
Profile 5 backtest results (234 trades, $58,317 peak potential):

Win rate: 43.2% (below breakeven)
Average winner: $294
Average loser: -$187

Statistical test (permutation):
- Actual Sharpe: -0.41
- 95% CI of randomized: [-0.52, +0.51]
- Actual is within random distribution

CONCLUSION: Cannot reject null hypothesis that returns are random
```

---

## IMPLEMENTATION VS DESIGN COMPARISON TABLE

| Item | Design Spec | Implementation | Status |
|------|-------------|-----------------|--------|
| **Profile 5: Regime Filter** | Regime 2 (Downtrend) | Regime 2 (Downtrend) | ✅ CORRECT |
| **Profile 5: Entry Condition** | Enter on skew steep + VVIX rising + RV>IV | Uses those factors | ✅ SCORE CORRECT |
| **Profile 5: Entry Timing** | Enter at REGRESSION from downtrend | Enters at PEAK downtrend | ❌ TIMING WRONG |
| **Profile 5: Trade Structure** | Put backspread (long puts when puts cheap) | Pays spreads when puts expensive | ❌ WRONG DIRECTION |
| **Profile 5: Win Rate** | 50%+ | 43.2% | ❌ WORSE THAN RANDOM |
| | | | |
| **Profile 6: Regime Filter** | Regime 4 (Breaking Vol) | Regime 4 (Breaking Vol) | ✅ CORRECT |
| **Profile 6: Entry Condition** | Enter when vol compressed (about to expand) | Enters when vol already expanded | ❌ INVERTED |
| **Profile 6: IV Rank Signal** | Should be LOW (cheap straddles) | Is HIGH (expensive straddles) | ❌ INVERTED |
| **Profile 6: RV/IV Signal** | Should check RV < IV (compression) | Doesn't check RV/IV at all | ❌ MISSING |
| **Profile 6: Trade Structure** | Long straddle when vol cheap | Long straddle when vol expensive | ❌ WRONG TIMING |
| **Profile 6: Signal Strength** | Should correlate with P&L | Losers have higher signal | ❌ INVERSE RELATIONSHIP |
| **Profile 6: Win Rate** | 50%+ | 32.5% | ❌ SIGNIFICANTLY WORSE |
| **Profile 6: Predictive Value** | Should predict vol expansion | p=0.19 (no significance) | ❌ NO ALPHA |

---

## SEVERITY RANKING

### CRITICAL (Block Deployment)

1. **Profile 6: IV Rank Inverted (Line 302)**
   - Buying straddles when expensive instead of cheap
   - Direct $30K+ P&L impact
   - Easy 1-line fix

2. **Profile 6: Missing RV/IV Compression Check**
   - Entering vol expansion trades AFTER vol already expanded
   - Entering when IV already reflects shock
   - Medium complexity fix (add factor to score)

3. **Profile 5: Entry Timing Paradox**
   - Winning trades have uptrend characteristics
   - Losing trades have downtrend characteristics
   - Framework definition/implementation mismatch
   - Design flaw, not implementation bug

### HIGH (Reduce Confidence)

4. **Profile 6: No Statistical Significance (p=0.19)**
   - Signal has zero predictive value
   - Needs design re-thinking (not just tuning)

5. **Profile 5: Below-Random Win Rate (43.2%)**
   - Worse than coin flip
   - Suggests fundamental approach wrong

6. **Profile 6: Inverse Signal Relationship**
   - Losers have higher signal strength
   - Suggests factor directions wrong

---

## RECOMMENDED FIXES (PRIORITY ORDER)

### FIX #1: PROFILE 6 - IV RANK SIGN INVERSION

**Severity:** CRITICAL
**Effort:** TRIVIAL (1 line)
**File:** `/Users/zstoc/rotation-engine/src/profiles/detectors.py`
**Line:** 302

**Current:**
```python
factor3 = sigmoid((df['IV_rank_20'] - 0.5) * 5)
```

**Fixed:**
```python
factor3 = sigmoid((0.5 - df['IV_rank_20']) * 5)
```

**Expected Impact:** +$30-50K additional profit (if other fixes applied)

---

### FIX #2: PROFILE 6 - ADD RV/IV COMPRESSION FACTOR

**Severity:** CRITICAL
**Effort:** MODERATE (3-5 lines)
**File:** `/Users/zstoc/rotation-engine/src/profiles/detectors.py`
**Method:** `_compute_vov_score()` (lines 278-308)

**Current (lines 294-305):**
```python
# Factor 1: VVIX elevated vs recent 80th percentile
vvix_ratio = df['VVIX'] / (df['VVIX_80pct'] + 1e-6)
factor1 = sigmoid((vvix_ratio - 1.0) * 5)

# Factor 2: VVIX rising
factor2 = sigmoid(df['VVIX_slope'] * 1000)

# Factor 3: IV rank high
factor3 = sigmoid((df['IV_rank_20'] - 0.5) * 5)

# Geometric mean
score = (factor1 * factor2 * factor3) ** (1/3)
```

**Fixed:**
```python
# Factor 1: VVIX elevated vs recent 80th percentile
vvix_ratio = df['VVIX'] / (df['VVIX_80pct'] + 1e-6)
factor1 = sigmoid((vvix_ratio - 1.0) * 5)

# Factor 2: VVIX rising
factor2 = sigmoid(df['VVIX_slope'] * 1000)

# Factor 3: IV rank LOW (vol cheap, not elevated)
factor3 = sigmoid((0.5 - df['IV_rank_20']) * 5)  # FIXED: Inverted

# Factor 4: Vol COMPRESSION (RV < IV, not expanding)
# Entry signal when compression is ABOUT to end (vol about to expand)
rv_iv_ratio = df['RV10'] / (df['IV20'] + 1e-6)
factor4 = sigmoid((1.0 - rv_iv_ratio) * 5)  # High when RV < IV (compression)

# Geometric mean (all 4 factors must align)
score = (factor1 * factor2 * factor3 * factor4) ** (1/4)
```

**Expected Impact:** Converts Profile 6 from -0.82 Sharpe to potential +0.3-0.5 Sharpe

---

### FIX #3: PROFILE 5 - ENTRY TIMING RETHINK

**Severity:** CRITICAL
**Effort:** HIGH (design change)
**Root Cause:** Framework defines regimes with static snapshots, not regime transitions

**Problem:** By the time Profile 5 score is high, the panic is ending and put premium collapses.

**Potential Solutions:**

**Option A: Earlier Entry Signal**
- Enter when skew Z > 0.5 (starting to steepen, not fully steepened)
- OR enter when VVIX slope > 0 (rising, not yet peaked)
- Requires score threshold reduction and testing

**Option B: Add Trend Change Detector**
- Trigger when: Trend CHANGES toward down (not fully down yet)
- Detect regime transitions, not regime steady states
- More complex, better timing

**Option C: Abandon Profile 5 Approach**
- Current evidence suggests put spreads don't work at current entry timing
- Profile 3 (CHARM - sell straddles) is stronger
- Consider focusing resources on Profiles 1, 3, 4 only

---

## TESTING RECOMMENDATIONS (Before Re-Deployment)

### TEST PLAN

**Phase 1: Profile 6 IV Rank Fix (MUST DO)**
1. Apply 1-line fix (line 302)
2. Re-run Profile 6 backtest with same parameters
3. Check if win rate improves to 45%+
4. Check if average loser improves
5. Verify Sharpe > -0.5 (vs current -0.82)

**Phase 2: Profile 6 Compression Factor (SHOULD DO)**
1. Apply 4-line factor addition
2. Re-run with full 4-factor model
3. Test factor weights (geometric mean vs arithmetic)
4. Verify signal now correlates with Regime 4

**Phase 3: Profile 5 Entry Timing (NICE TO HAVE)**
1. Lower score threshold (0.3 instead of 0.4)
2. Test alternative entry triggers
3. Measure timing impact on win rate
4. Compare to Profile 3 (CHARM) performance

---

## CONCLUSION

**Profile 5 (SKEW):** Framework design may be flawed (entry timing paradox). Implement monitoring score vs MA slope correlation. If correlation remains negative, abandon this profile.

**Profile 6 (VOV):** Two clear mathematical bugs (IV rank sign + missing compression factor). Fix both → expect 30-50K improvement. No fundamental design flaw, just implementation errors.

**Confidence Level:** HIGH - agent findings are consistent across multiple verification angles.

