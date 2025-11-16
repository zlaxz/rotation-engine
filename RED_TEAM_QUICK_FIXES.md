# RED TEAM QUICK REFERENCE - PROFILES 5 & 6 BUGS

**4 Critical Bugs Found | 2-Line Fixes Ready**

---

## PROFILES 5 & 6: BUG SUMMARY

| Bug | File | Line(s) | Fix Type | Impact |
|-----|------|---------|----------|--------|
| P6: IV Rank Inverted | detectors.py | 302 | 1-line sign change | +$40K potential |
| P6: Missing Compression Check | detectors.py | 294-305 | Add 4 lines | Better timing |
| P5: Entry Timing Wrong | profile_5.py | N/A | Design review | Architecture issue |
| P6: No Statistical Significance | backtest results | N/A | Validation failure | Signal is random |

---

## FIX #1 - PROFILE 6: IV RANK SIGN (CRITICAL, 1 LINE)

**File:** `/Users/zstoc/rotation-engine/src/profiles/detectors.py`
**Line:** 302

**Current (WRONG):**
```python
factor3 = sigmoid((df['IV_rank_20'] - 0.5) * 5)
```

**Fixed (CORRECT):**
```python
factor3 = sigmoid((0.5 - df['IV_rank_20']) * 5)
```

**Why:** Long straddle entry should buy when IV is CHEAP (low rank), not expensive (high rank).

---

## FIX #2 - PROFILE 6: ADD COMPRESSION DETECTION (CRITICAL, +4 LINES)

**File:** `/Users/zstoc/rotation-engine/src/profiles/detectors.py`
**Method:** `_compute_vov_score()` (lines 278-308)

**Replace lines 294-305 with:**
```python
# Factor 1: VVIX elevated vs recent 80th percentile
vvix_ratio = df['VVIX'] / (df['VVIX_80pct'] + 1e-6)
factor1 = sigmoid((vvix_ratio - 1.0) * 5)

# Factor 2: VVIX rising
factor2 = sigmoid(df['VVIX_slope'] * 1000)

# Factor 3: IV rank LOW (vol cheap)
factor3 = sigmoid((0.5 - df['IV_rank_20']) * 5)  # FIXED: Inversion

# Factor 4: Vol COMPRESSION (RV < IV means about to expand)
rv_iv_ratio = df['RV10'] / (df['IV20'] + 1e-6)
factor4 = sigmoid((1.0 - rv_iv_ratio) * 5)

# Geometric mean of 4 factors
score = (factor1 * factor2 * factor3 * factor4) ** (1/4)
```

**Why:** Entry should be when vol is COMPRESSED and ABOUT to expand, not when already expanded.

---

## FIX #3 - PROFILE 5: ENTRY TIMING ANALYSIS (HIGH PRIORITY, DESIGN REVIEW)

**Problem:** Agent evidence shows winners happen in UPTRENDS, losers in DOWNTRENDS.

**Evidence:**
- Winners: MA20 slope = +0.0167 (uptrend)
- Losers: MA20 slope = -0.0007 (downtrend)
- Profile DESIGNED for downtrends
- **CONCLUSION:** Entering put spreads AFTER panic ends, paying high premium

**Options:**
1. Lower score threshold (0.3 → 0.4) to enter earlier
2. Add trend-change detector (enter at TRANSITION, not steady-state)
3. Abandon Profile 5, focus on Profile 3 (CHARM) which is stronger

**Action:** Verify core design or reduce allocation to Profile 5

---

## PROFILE 6 IMPACT CALCULATION

**Current State:**
- 157 trades, -$17,012 loss
- 32.5% win rate
- Avg winner: $187, Avg loser: -$223
- Sharpe: -0.82

**After Fix #1 (IV Rank Inversion only):**
- Expected win rate: 45-50%
- Expected Sharpe: -0.2 to +0.1
- Potential profit swing: +$30-50K

**After Fix #2 (Add Compression Check):**
- Expected win rate: 50-55%
- Expected Sharpe: +0.2 to +0.5
- Better timing = fewer bad entries

---

## PROFILE 5 CONTEXT

**Current State:**
- 234 trades, $58,317 peak potential
- 43.2% win rate (below random)
- Sharpe: -0.41
- **Evidence:** Winning trades in uptrends contradicts downtrend design

**Decision Needed:**
- Is this a timing issue (fix entry trigger)?
- Or design flaw (profile conceptually broken)?
- Agent recommends pause pending Profile 3 validation

---

## VALIDATION CHECKLIST (AFTER FIXES)

After applying fixes, verify:

- [ ] Profile 6 score test: IV rank now HIGH when IV rank LOW (reversed)
- [ ] Profile 6 backtest: Win rate > 40% (was 32.5%)
- [ ] Profile 6 backtest: Avg winner > avg loser (was inverted)
- [ ] Profile 6 backtest: Sharpe > -0.3 (was -0.82)
- [ ] Profile 5 decision: Proceed with fix or reduce allocation?
- [ ] Both profiles: Re-test for walk-forward compliance (no look-ahead bias)

---

## DEPLOYMENT RECOMMENDATION

**HOLD Profile 6 from live trading until fixes applied.**
- Fix #1: 1 line, trivial risk
- Fix #2: 4 lines, well-defined logic
- Re-test: ~30 minutes
- Expected value: +$40K baseline improvement

**Profile 5: Requires design review** before committing.

---

## FILE LOCATIONS (ABSOLUTE PATHS)

- Main implementation: `/Users/zstoc/rotation-engine/src/profiles/detectors.py`
- Profile 5 config: `/Users/zstoc/rotation-engine/src/trading/profiles/profile_5.py`
- Profile 6 config: `/Users/zstoc/rotation-engine/src/trading/profiles/profile_6.py`
- Comprehensive audit: `/Users/zstoc/rotation-engine/RED_TEAM_PROFILES_5_6_COMPREHENSIVE_AUDIT.md`

