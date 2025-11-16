# Regime Analysis: Quick Reference

**Question:** Do market regimes at entry predict success?
**Answer:** YES - Strongly, with profile-specific patterns

---

## THE BOTTOM LINE

| Metric | Low RV | Med RV | High RV |
|--------|--------|--------|---------|
| Win Rate | **48.1%** ✅ | 41.3% | 35.1% ⚠️ |
| Avg P&L | +$6.32 | -$43.63 | -$171 |
| Total P&L | +$2.3K | -$9.1K | -$16.1K |
| Trades | 366 | 208 | 94 |

**Trend Effect:**
- **Choppy (|slope|<0.05):** 43.9% WR, -$35 avg ← Baseline
- **Medium (0.05-0.1):** 49.3% WR, **+$16 avg** ← Best
- **Trending (>0.1):** 24.1% WR, **-$263 avg** ← Toxic

---

## WINNERS BY REGIME

### Low RV + Choppy (Safest)
- Profile 4 (VANNA): **67% WR, $170 avg P&L** (81 trades)
- Profile 3 (CHARM): **63% WR, $44 avg P&L** (46 trades)
- Profile 1 (LDG): 47% WR, -$10 avg P&L (315 trades)

### Med RV + Choppy (Charm's Sweet Spot)
- **Profile 3 (CHARM): 72% WR, $133 avg P&L** (25 trades) ⭐ BEST COMBO

### Med RV + Medium (Gentle Trend)
- Profile 1 (LDG): **53% WR, $140 avg P&L** (15 trades)
- Profile 4 (VANNA): 55% WR, $56 avg P&L (18 trades)

---

## LOSERS BY REGIME

### Trending Markets (Toxic for all)
- Profile 1 (LDG): 20% WR, **-$322 avg**
- Profile 4 (VANNA): 25% WR, **-$230 avg**
- Profile 3 (CHARM): 0% (doesn't enter)
- Profile 5 (SKEW): 0% (doesn't enter)

### High RV (Destroys Position Size)
- When Profile 3 loses: -$1,146 avg (vs -$412 Low RV)
- When Profile 4 loses: -$646 avg (vs -$438 Low RV)

### Low RV Disasters
- **Profile 5 (SKEW): 5% WR, -$276 avg** (hostile to safe environment!)
- **Profile 6 (VOV): 37% WR, -$77 avg** (never strong anywhere)

---

## PROFILE STRENGTH BY REGIME

```
              LOW RV    MED RV    HIGH RV   CHOPPY   TRENDING
VANNA         64.6% ⭐   48.9%    50.0%    61.4% ⭐   25.0%
CHARM         63.0% ⭐   72.0% ⭐  40.0%    63.0% ⭐   N/A
LDG           48.4%     37.2%    31.2%    43.0%    20.0%
SDG           26.7%     40.0%    41.2%    27.3%    50.0% ⭐
SKEW          4.8% ⚠️    38.7%    7.1% ⚠️   17.4%    N/A
VOV           36.2%     22.7%    36.8%    30.0%    20.0%
```

---

## WHAT THIS MEANS

### DO: Trade in These Regimes
1. **Low RV + Choppy** (Profile 4): 67% WR, +$14.8K total
2. **Med RV + Choppy** (Profile 3): 72% WR, +$3.3K total
3. **Low RV + Medium slope** (Profile 4): 56% WR, +$1.1K total

### DON'T: Trade in These Regimes
1. **Any + Trending slope** (All profiles): 24% WR, -$7.6K total
2. **High RV + Any trend** (All profiles): 35% WR, -$16.1K total
3. **Low RV + Choppy for Profile 5** (SKEW): 5% WR, -$276 avg

### REMOVE: These Profiles
1. **Profile 5 (SKEW):** 21% overall WR, -$14K, only 50% in best regime
2. **Profile 6 (VOV):** 32% overall WR, -$17K, never strong

---

## FILTERING RECOMMENDATION

**Current:** No regime filtering, trade all combinations

**Proposed:** Only enter if:
```
RV20 < 25%   AND   |slope| < 0.1
```

**Impact:**
- Removes: 100% High RV trades, 90% Trending trades
- Keeps: ~300 trades (45% of total)
- Expected win rate: 50-55% (up from 44%)

**By Profile:**
- Profile 4 (VANNA): Keep 99/162 trades, 65% WR → **Keep**
- Profile 3 (CHARM): Keep 71/81 trades, 67% WR → **Keep**
- Profile 1 (LDG): Keep 92/150 trades, 48% WR → **Keep**
- Profile 5 (SKEW): Keep 52/66 trades, still 22% WR → **Remove**
- Profile 6 (VOV): Keep 138/157 trades, still 33% WR → **Remove**
- Profile 2 (SDG): Keep 22/52 trades, but loses trend strategy → **Questionable**

---

## STATISTICAL CONFIDENCE

- **Low RV vs High RV difference:** p < 0.001 (highly significant)
- **Choppy vs Trending difference:** p < 0.01 (highly significant)
- **Regime effects are real, not luck**

---

## ACTIONABLE NEXT STEPS

### Phase 1 (Immediate): Implement Filtering
- [ ] Add regime checks to entry logic
- [ ] Filter: Only enter if RV20 < 25% AND |slope| < 0.1
- [ ] Remove Profiles 5 & 6 from trading
- [ ] Re-run backtest with filtering

### Phase 2 (Medium-term): Profile-Specific Optimization
- [ ] Concentrate Profile 4 capital in Low RV
- [ ] Concentrate Profile 3 capital in Med RV + Choppy
- [ ] Analyze Profile 2 as Trending-only specialist
- [ ] Adjust position sizing by regime (bigger in low vol, smaller in high vol)

### Phase 3 (Long-term): Deep Dives
- [ ] Why does Profile 5 fail universally?
- [ ] Why does Profile 6 never exceed 43%?
- [ ] Can hedging reduce High RV losses?
- [ ] What about events/earnings? (Profile 6 might work with events)

---

## FILES GENERATED

- **REGIME_ANALYSIS_REPORT.md** - Full 15-section analysis with statistics
- **regime_analysis_heatmaps.png** - 6-panel heatmap of win rates by regime
- **regime_analysis_summary.png** - Summary charts
- **REGIME_ANALYSIS_QUICK_REFERENCE.md** - This file

