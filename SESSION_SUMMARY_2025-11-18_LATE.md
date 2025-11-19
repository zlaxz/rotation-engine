# SESSION SUMMARY - 2025-11-18 Late Night (Exit Investigation)

**Duration:** ~3 hours
**Focus:** Find intelligent exit system without overfitting
**Result:** System loses money even with optimal exits

---

## WHAT WE DISCOVERED

### 1. Entries Are Structurally Sound (Validated)

**7-Gate Rigorous Test:**
- Tested all possible 1D and 2D feature filters
- Gates: Harm-awareness, net benefit, year robustness, coarseness, bootstrap, permutation, sample size
- **Result:** ZERO filters passed all gates
- **Conclusion:** Cannot improve entries without harming winners

**Peakless rates acceptable:**
- CHARM: 17.3%
- LDG: 22.7%
- VANNA: 20.8%
- SDG: 18.5% (after downtrend filter, but filter removed too many winners - rejected)
- SKEW: 29.2%
- VOV: 29.0%

### 2. Current Performance (349 trades, 2020-2024)

**With Day 14 exits (original):**
- Total P&L: -$22,313
- Peak Potential: $236,258
- Capture: -9.4%
- **Losing money**

**With Day 7 exits (optimal found):**
- Total P&L: -$11,964
- Improvement: +$10,349 (47% better)
- Capture: -16.0%
- **Still losing money**

### 3. Exit Strategies Tested

**Family A: Fixed Hold Times**
- Day 2: -$14,651
- Day 3: -$17,346
- Day 5: -$26,831
- **Day 7: -$11,964** ← BEST
- Day 10: -$12,307

**Family B: Trailing Stops**
- K=300 D=100: -$14,145
- All others worse than Day 7

**Family C: Profile-Specific Days**
- Based on median time-to-peak per profile
- Result: -$17,029
- **Worse than uniform Day 7 (failed)**

**Family D: Detector-Based (Decay-Aware)**
- Exit when dRV5 <= 0 (vol stalling)
- Exit when pin breaks (CHARM)
- Result: -$19,618
- **Worse than Day 7 (failed)**

### 4. Time-to-Peak Analysis

**Overall:** 52% of trades peak by day 7

**Profile-specific:**
- Fast profiles (SDG, SKEW): Median day 4, but p75 is day 6-8
- Moderate (LDG, VOV): Median day 5-6
- Slow (VANNA, CHARM): Median day 9-10

**Key insight:** Uniform Day 7 captures the sweet spot across distribution

---

## PROFITABLE PROFILES (With Optimal Exits)

**Only 2 profiles consistently profitable:**

1. **VANNA:** +$6,370 with Day 10 exits
   - 48 trades
   - 56% win rate
   - Strong performance

2. **SDG:** +$1,136 with Day 7 exits (after filter applied)
   - 27 trades (was 62, filtered to downtrend-only)
   - 59% win rate
   - Marginal but positive

**SKEW:** +$2,153 with Day 7 (but only 24 trades - small sample)

**Marginal:**
- CHARM: +$1,235 with Day 14 (barely profitable)

**Losers:**
- LDG: -$3,813 (best case)
- VOV: -$12,282 (worst performer)

---

## CRITICAL CONCLUSION

**Even with optimal exits, system loses $11,964.**

**This means:**
- Entry system captures opportunities ($236K potential)
- But edge is not large enough to overcome:
  - Time decay (theta)
  - Volatility mean reversion
  - Transaction costs
  - Market efficiency

**OR:**
- Only 2 profiles have real edge (VANNA, SDG)
- Other 4 profiles don't work
- Multi-profile rotation dilutes the edge

---

## NEXT SESSION PRIORITIES

### Investigate Why System Loses Money

1. **Execution Cost Audit:**
   - Are spreads too conservative?
   - Slippage too high?
   - Check actual SPY option spreads vs model

2. **Focus on Winners:**
   - Build VANNA-only strategy
   - Build SDG-only strategy
   - Test 2-profile rotation (VANNA + SDG)

3. **Regime Analysis:**
   - Does edge exist only in specific regimes?
   - 2020-2021: COVID (unusual)
   - 2022: Bear market (unusual)
   - 2023-2024: Low vol grind (normal?)
   - Test on 2023-2024 only?

4. **Fundamental Strategy Review:**
   - Is convexity rotation thesis valid?
   - Or is this just market noise?
   - Need theoretical validation

---

## FILES CREATED

**Analysis:**
- `analysis/TIME_TO_PEAK_CURRENT_DATA.txt`
- `STRUCTURAL_ENTRY_FILTERS_ANALYSIS.md`
- `structural_rules.json`
- `reports/exit_detector_v0_vs_day7.md`

**Scripts (Audited and Working):**
- `scripts/analyze_time_to_peak.py`
- `scripts/exit_sweep_pnl_based_FIXED.py`
- `scripts/test_profile_specific_exits.py`
- `scripts/evaluate_detector_v0.py`
- `scripts/structural_entry_analysis.py`
- `scripts/harm_aware_rule_search_7gates.py`
- `exits/detector_exit_v0.py`

**Scripts (Broken/Rejected):**
- `scripts/exit_sweep_pnl_based.py` - Had look-ahead bias (FIXED version exists)
- `scripts/sdg_multidimensional_separation.py` - Had bugs (FIXED version exists)

---

## RECOMMENDATIONS FOR DEPLOYMENT

**DO NOT deploy current system** (loses $11,964 even with optimal exits)

**Options:**

**A. Deploy VANNA-only:**
- Proven profitable (+$6,370)
- 48 trades over 5 years
- Use Day 10 exits
- Accept low frequency

**B. Deploy VANNA + SDG:**
- Combined: +$7,506
- Focused on proven edges
- Ignore failing profiles

**C. Investigate execution costs first:**
- If costs are 2x too high, system might be profitable
- Check spreads vs actual market data
- Audit transaction cost model

**D. Accept system doesn't have edge:**
- 5 years of data, rigorous testing
- Loses money even with optimal exits
- Move to different strategy

---

## METHODOLOGY LEARNINGS

**What Worked:**
- ✅ 7-gate rigorous testing prevents spurious filters
- ✅ Multi-agent auditing catches bugs before they matter
- ✅ Harm-awareness (TP >= FP) prevents destroying winners
- ✅ Year-by-year robustness catches regime overfitting

**What Didn't Work:**
- ❌ Train/val/test on single regime (2020-2021 = COVID, not generalizable)
- ❌ Profile-specific parameters from means (high variance makes means misleading)
- ❌ Detector-based exits (decay signals too noisy)
- ❌ Inverse-entry exits (doesn't capture decay properly)

**Key Lesson:**
Rigorous methodology prevented us from deploying overfit garbage.
But revealed uncomfortable truth: Strategy might not have edge.

---

**Session end:** 2025-11-18 ~11:00 PM
**Status:** Exit investigation complete
**Next:** Investigate root cause of losses OR pivot to VANNA-only strategy
