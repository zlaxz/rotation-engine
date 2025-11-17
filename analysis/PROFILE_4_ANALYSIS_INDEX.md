# Profile 4 VANNA Analysis - Complete Index

**Analysis Date:** 2025-11-16
**Data Range:** 2020-2025 (151 trades)
**Status:** Ready for implementation
**Key Finding:** Strategy is mislabeled - NOT VANNA, actually Directional Gamma with decay

---

## Quick Navigation

### Executive Summaries
- **[Regime Dependencies Report](Profile_4_VANNA_regime_dependencies.md)** - Full 8,000-word analysis
  - Regime performance breakdown
  - Year-by-year analysis (2022 crisis deep dive)
  - Exit strategy framework
  - Capital allocation recommendations

- **[Visual Regime Matrix](Profile_4_VANNA_regime_matrix.txt)** - Quick reference tables
  - Regime summary (Event/Catalyst, Trend Up, Choppy)
  - Year-by-year breakdown
  - Winner vs loser profiles
  - Three-layer exit framework diagram

- **[Action Items & Implementation](Profile_4_VANNA_ACTION_ITEMS.md)** - Developer roadmap
  - 4-phase implementation plan (Weeks 1-4)
  - Code snippets for exits, position sizing, guardrails
  - Testing checklist and success criteria
  - Risk mitigation strategies

### Memory Entities (MCP Graph)
- `Profile_4_VANNA_regime_analysis` - Core findings
- `Profile_4_VANNA_event_catalyst_regime` - Primary money-maker regime
- `Profile_4_VANNA_trend_up_regime` - High-risk regime
- `Profile_4_VANNA_exit_strategy` - Exit framework
- `Profile_4_VANNA_2022_crisis` - Crisis analysis and prevention

---

## Key Findings at a Glance

### The Mislabel Problem
- **Named:** "VANNA (Vol-Spot Correlation)"
- **Actually:** Directional Gamma with theta decay
- **Evidence:** Winners have NEGATIVE vol changes (-2.31% to -2.48%) yet still profit $17,609
- **Profit Driver:** Spot movement (+2.5-2.7%), not vega/vol change
- **Implication:** Strategy fundamentally different from intended design

### Performance by Regime

| Regime | Trades | Win % | PnL | Per Trade | Action |
|--------|--------|-------|-----|-----------|--------|
| **Event/Catalyst** | 108 | 63.0% | +$17,609 | +$163 | ✓ PRIORITIZE (70% capital) |
| **Trend Up** | 39 | 48.7% | -$1,993 | -$51 | ⚠ CAUTION (20% capital, half size) |
| **Choppy** | 4 | 25.0% | -$2,110 | -$527 | ✗ SKIP (don't trade this) |

### 2022 Crisis Summary
- **Win Rate Drop:** 70.8% (2020) → 13.3% (2022) = -57.5%
- **Capital Loss:** $7,841 (erased 3 years of profit)
- **Root Cause:** Bear market + vol expansion during "events"
- **Solution:** Guardrails + vol spike detection + position sizing

---

## Critical Metrics for Trading

### Event/Catalyst (63% Win Rate - PRIMARY)
- **Entry:** Vega ~76, Delta ~0.55
- **Winners:** Hold 13.8 days → Exit Delta 0.687, Spot +2.55%, Vol -2.31%
- **Exit Signal:** Time-based (8-14 days) OR profit-taking at 50% peak
- **Stop Loss:** -50% entry cost
- **Max Drawdown:** -41.2% (but exit before hitting it)

### Trend Up (48.7% Win Rate - CAUTION)
- **Winners:** Similar to Event/Catalyst (spot +2.70%)
- **Losers (Catastrophic):** Spot +0.14% (stalled!), Vol +2.64% (EXPANSION!)
- **Fatal Flaw:** Thesis breaks when vol expands during uptrend
- **Exit Signal:** IMMEDIATELY if RV5 > 1.5x entry
- **Position Size:** 50% of Event/Catalyst
- **Stop Loss:** -30% entry cost (tighter)
- **Max Drawdown:** -336% (worst case)

### Choppy (25% Win Rate - AVOID)
- **Issue:** Theta decay dominates, no directional move for gamma profit
- **Action:** Skip when RV20 is 0.25-0.35 and slope near zero

---

## Three-Layer Exit System

**Layer 1: Profit Taking** (MOST IMPORTANT)
```
IF peak profit > 50% entry cost → Exit 50% immediately
IF days > 10 AND spot up → Trail stop -20% from peak
IF days > 10 AND no spot move → Exit all
```

**Layer 2: Vol Regime Shift** (MOST DANGEROUS)
```
IF RV5 > 1.5x entry RV5 → Exit all (vol spike)
IF slope flat AND spot stalled < 0.5%/5 days → Exit all (no gamma)
FOR TREND UP: IF vol rises at ANY point → Exit IMMEDIATELY
```

**Layer 3: Time Decay**
```
IF days > 14 AND not at peak → Exit (theta accelerates)
IF DTE < 38 → Exit (pin risk, gamma explosion)
```

---

## Implementation Roadmap

### Phase 1: Exit Strategy (Week 1)
- [ ] Code three-layer exit system
- [ ] Implement regime-specific position sizing
- [ ] Implement 2022 crisis prevention guardrails

### Phase 2: Data Validation (Week 1-2)
- [ ] Audit 2022 trades - verify guardrails would prevent 70%+ of losses
- [ ] Validate exit layer effectiveness - show 5-10% capture improvement

### Phase 3: Backtesting (Week 2-3)
- [ ] Re-run full backtest with new exits
- [ ] Monte Carlo robustness testing
- [ ] Compare metrics: Win rate (maintain ~58%), Capture (17% → 25%+), Sharpe (+0.15)

### Phase 4: Live Trading (Week 3-4)
- [ ] Add regime detection to live system
- [ ] Implement daily exit checklist
- [ ] Paper trade for validation

### Phase 5: Documentation (Ongoing)
- [ ] Rename Profile_4 from "VANNA" to "Directional Gamma (DG)"
- [ ] Update all code comments and README
- [ ] Update trading rules documentation

---

## Expected Outcomes

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Win Rate | 58.3% | 58% | Maintain (avoid overfitting) |
| Capture Ratio | 17% | 25%+ | +8 points |
| Sharpe Ratio | TBD | +0.15 points | Risk-adjusted improvement |
| Max Drawdown | -830% | -50% | Reduce via better exits |
| 2022 Performance | -$7,841 (13% win) | -$2,000 (35% win) | Prevent crisis via guardrails |
| PnL per Trade | $163 | $200+ | Improved P&L management |

---

## 2022 Prevention Guardrails

**Problem:** Bear market + vol expansion = strategy broke down

**Solution (Implement):**
1. Skip Event/Catalyst if RV20 > 0.35 (vol already high)
2. Avoid trading after major NEGATIVE events in bear markets
3. Reduce position size in bear market regimes (-30% vs -50% stops)
4. Skip Trend Up entries if rates rising + bear market signals

**Expected Improvement:** Win rate in bear markets 13% → 35%+

---

## Files Generated

### Analysis Documents
1. **Profile_4_VANNA_regime_dependencies.md** (8,000+ words)
   - Complete regime analysis
   - Exit strategy framework
   - Capital allocation
   - 2022 crisis prevention

2. **Profile_4_VANNA_regime_matrix.txt**
   - Visual regime matrix
   - Quick reference tables
   - Decision trees

3. **Profile_4_VANNA_ACTION_ITEMS.md**
   - Implementation roadmap
   - Code snippets
   - Testing checklist

4. **PROFILE_4_ANALYSIS_INDEX.md** (this file)
   - Navigation and summary

### Data Files
- **Data source:** `/Users/zstoc/rotation-engine/data/backtest_results/full_tracking_results.json`
- **151 trades** across 2020-2025
- **$13,507 realized PnL**
- **58.3% win rate**
- **17% capture of peak potential**

---

## Next Steps Priority

### IMMEDIATE (This Week)
1. Read all three analysis documents
2. Review code in ACTION_ITEMS.md
3. Assess implementation effort with engineering team
4. Decide: Full refinement now vs. Phase 1 only?

### SHORT TERM (Week 1-2)
1. Implement three-layer exit system
2. Implement position sizing by regime
3. Implement 2022 guardrails
4. Run data validation audit

### MEDIUM TERM (Week 2-4)
1. Backtest refinement
2. Monte Carlo validation
3. Live trading integration
4. Documentation updates

### LONG TERM (Month 2)
1. Monitor live trading performance against refined backtest
2. Track whether 2022-like crises are prevented
3. Measure actual Sharpe improvement vs. predictions
4. Consider extending framework to other profiles

---

## Key Questions to Address

1. **Should we rename Profile_4 to "Directional Gamma"?**
   - Yes - current name misleads about actual edge
   - Affects: Code, docs, trading rules, client communications

2. **How aggressive should 2022 guardrails be?**
   - RV20 > 0.35 filter: Will remove some winning trades
   - Bear market skip: Too conservative?
   - Recommend: Start aggressive, relax if needed

3. **Do we fully replace the current exit logic?**
   - Three-layer system is more complex
   - Recommend: Phase in Layer 1 first, add layers if testing validates

4. **What's the ROI on implementation effort?**
   - Estimated 40-60 hours engineering
   - Expected: Sharpe +0.15, Capture +8 points, Prevent 2022 crisis
   - Justify: Worth if trading this strategy live

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Over-optimization | Backtest success ≠ live trading success | Monte Carlo + OOS testing |
| Implementation bugs | Wrong exits = wrong results | Thorough unit tests + paper trade |
| Guard rails too strict | Filter out winning trades | Calibrate thresholds carefully |
| Strategy regime change | 2022-like crisis recurrence | Continuous monitoring + quick adjustments |

---

## Contact & Questions

For questions about this analysis:
- See analysis documents for detailed reasoning
- Check memory entities (MCP graph) for structured findings
- Review code snippets in ACTION_ITEMS.md for implementation details

---

**Analysis Complete**
**Status:** Ready for implementation decision
**Last Updated:** 2025-11-16
