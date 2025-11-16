# Strategy Context: Convexity Rotation Engine

**Last Updated:** 2025-11-15
**Status:** Framework Validated | Phase 2 (Exit Intelligence)
**Current Phase:** Building intelligent exit system for Profile 3 (CHARM)

---

## 🎯 OPERATING HYPOTHESIS

**Core Thesis:**
Markets systematically misprice specific types of options convexity based on market regime. By detecting which convexity profile is underpriced relative to realized market behavior, we can harvest structural edge independent of directional bets.

**Theoretical Basis:**
Options market makers price convexity based on IMPLIED volatility and historical patterns, but actual REALIZED convexity varies by regime. When market transitions between regimes (trending → mean-reverting, low vol → high vol), specific convexity types become structurally mispriced for a window of time. This creates arbitrage-like opportunities.

**Edge Concept:**
The edge exists at regime transitions and within specific market microstructures:
1. **Regime Transition Alpha** - When market moves from low-vol to high-vol, long gamma is underpriced
2. **Theta Harvest in Carry Regimes** - When vol mean-reverts, short gamma + charm capture premium decay
3. **Vanna Exploitation** - When vol and spot correlate (crashes), vanna positions profit from convexity interaction
4. **Skew Arbitrage** - When realized skew > implied skew, tail convexity is mispriced

**Key Insight (Validated):**
Profiles self-select favorable regimes through entry logic. Entry conditions naturally encode regime detection, so explicit regime filtering ON TOP reduces opportunity. Let the profile's entry logic be the regime detector.

---

## 🏗️ STRATEGY ARCHITECTURE

**High-Level Logic:**
1. Calculate 6 continuous [0,1] scores for each convexity profile daily
2. Profiles enter trades when their score > threshold (0.7) AND favorable conditions exist
3. Each profile targets specific convexity type (long gamma, charm, vanna, etc.)
4. Hold for fixed period OR exit on intelligent signal (building this now)
5. Measure performance = Σ(all profile P&L) across time

**Key Components:**

1. **Data Spine** - SPY OHLCV + options chains + derived features (RV, ATR, MAs)
2. **Regime Classifier** (De-emphasized) - 5-regime detection, but profiles don't require it
3. **Profile Scoring** - 6 continuous sigmoid scores, EMA-smoothed for stability
4. **Trade Simulator** - Event-driven backtest with realistic execution (bid-ask, slippage)
5. **Profile Implementations** - 6 distinct convexity profiles with entry/exit logic
6. **Rotation Engine** (Future) - Dynamically allocate capital based on desirability scores

**Component Interactions:**
Data → Profile Scoring → Trade Entry (when score > 0.7) → Hold → Exit (intelligent system building) → Measure P&L

**What Makes This Different:**
- Not directional (delta-hedged or delta-neutral positions)
- Not volatility arbitrage (not betting on vol direction)
- **Convexity arbitrage** - Betting on specific shapes of P&L curves being mispriced
- 6 distinct profiles cover different market microstructures
- Self-selecting regime logic (no complex filtering needed)

---

## 🔬 KEY RESEARCH QUESTIONS

**Currently Investigating:**
1. **Exit intelligence impact** - Can we capture 40-50% of peaks vs 30%? (HIGH PRIORITY)
2. **Vol filter effectiveness** - Does RV > 15% improve win rate from 36% to 50%+?
3. **Profile 3 (CHARM) optimization** - Can this alone drive $30K+/year?

**Answered Questions:**
1. ~~Does framework have edge?~~ → YES: $83K baseline validated (2025-11-14)
2. ~~Are transaction costs correct?~~ → YES: $0.03 spread confirmed (2025-11-14)
3. ~~Do all 6 profiles work?~~ → YES: Each finds $10K-20K opportunity (2025-11-14)
4. ~~Does regime filtering improve results?~~ → NO: Reduces opportunity by 50% (2025-11-14)
5. ~~Are profiles self-selecting regimes?~~ → YES: Entry logic IS regime detection (2025-11-14)

---

## 🎲 CRITICAL DECISIONS & RATIONALE

### Decision 1: 6 Convexity Profiles (Not 3)
**Date:** 2025-11-13
**Decision:** Implement 6 distinct profiles covering full convexity spectrum
**Alternatives Considered:** 3 profiles (long gamma, short gamma, vanna) - simpler
**Rationale:** Markets have 6+ distinct microstructures. Missing any means missing edge. Each profile captures different market behavior:
- Profile 1 (LDG): Long-dated gamma - Big moves
- Profile 2 (SDG): Short-dated gamma - Scalping
- Profile 3 (CHARM): Theta decay - Carry regimes
- Profile 4 (VANNA): Vol-spot correlation - Crashes
- Profile 5 (SKEW): Tail convexity - Skew misprice
- Profile 6 (VOLVOL): Volatility of volatility - Regime instability

**Implications:** More code, but covers full opportunity set. Validated: Each finds $10K-20K (2025-11-14).

### Decision 2: Sigmoid Scoring (Not Binary)
**Date:** 2025-11-13
**Decision:** Continuous [0,1] scores with sigmoid functions, not binary regime flags
**Alternatives Considered:** Binary on/off signals (simpler but noisier)
**Rationale:** Markets aren't binary. Convexity edge exists on continuum. Sigmoid provides:
- Smooth transitions (no whipsaw)
- Confidence levels (0.7 = high confidence, 0.5 = uncertain)
- Natural threshold for entry (>0.7)
- EMA smoothing removes noise while preserving signal

**Implications:** More nuanced, but dramatically reduces false signals. Works well in practice.

### Decision 3: Walk-Forward Regime Detection
**Date:** 2025-11-13
**Decision:** Use walk-forward methodology for regime classification (no look-ahead)
**Alternatives Considered:** Full-sample regime detection (would be look-ahead bias)
**Rationale:** Prevents overfitting and look-ahead bias. Regimes detected using only past data. Critical for backtest integrity.
**Implications:** More complex implementation, but necessary for valid results.

### Decision 4: Abandon Complex Regime Filtering
**Date:** 2025-11-14
**Decision:** De-emphasize 6-regime rotation, let profiles self-select
**Alternatives Considered:** Full rotation engine with regime-based allocation
**Rationale:** Testing showed regime filtering REDUCES opportunity by 50%. Profiles' entry conditions naturally select favorable regimes. Don't over-constrain.
**Implications:** Simpler system, better performance. Focus on exits, not regime filtering.

### Decision 5: Transaction Costs = $0.03 Spread
**Date:** 2025-11-14
**Decision:** Use $0.03 bid-ask spread (3x penny-wide for safety), not $0.75
**Alternatives Considered:** $0.75 spread (old assumption), $0.01 (too optimistic)
**Rationale:**
- WebSearch: SPY options are most liquid, penny-wide spreads standard
- User's Schwab trades: 0.02-0.04% total costs
- $0.03 = conservative 3x for safety
**Implications:** GAME CHANGER - Turned "losing strategy" into $83K+ validated edge. All prior validation was WRONG due to bad cost assumption.

### Decision 6: Daily Bars Insufficient - Build Intelligent Exits
**Date:** 2025-11-14
**Decision:** Prioritize building intelligent exit system with minute bars
**Alternatives Considered:** Keep simple 7-day holds, optimize entry instead
**Rationale:** Analysis showed $8,772 left on table PER PROFILE due to:
- Theta decay giving back gains
- Can't respond to intraday moves
- Trailing stops trigger on noise with daily bars
**Implications:** Need minute-bar data (have 1,500 files ready) + exit manager logic from option-machine. High-priority build.

---

## ❌ FAILED APPROACHES (What Didn't Work)

### Failed Approach 1: $0.75 Bid-Ask Spread Assumption
**Tried:** 2025-11-13 (initial testing)
**Hypothesis:** SPY options have wide spreads like other underlyings
**Result:** Made EVERYTHING look unprofitable. Framework appeared to have no edge.
**Why It Failed:** Completely wrong assumption. SPY is most liquid options market, penny-wide spreads.
**Lesson Learned:** NEVER assume market data. WebSearch or verify with real trades first.
**Don't Retry Because:** Now validated correct spread ($0.03), this was 25x error.

### Failed Approach 2: Simplified Regime Classifiers
**Tried:** Multiple times during build (2025-11-13)
**Hypothesis:** Can shortcut regime detection with simplified logic for testing
**Result:** Every simplified version failed. Created more debugging work than using real code.
**Why It Failed:** Regime detection is complex. Simplifications remove critical nuance that makes it work.
**Lesson Learned:** Use actual code or don't test. No simplified versions.
**Don't Retry Because:** Have production regime classifier. Just use it.

### Failed Approach 3: Explicit 6-Regime Filtering
**Tried:** 2025-11-14
**Hypothesis:** Filter profile entries by aligned regimes to improve edge
**Result:** Reduced opportunity from $83K to $46K (50% loss)
**Why It Failed:** Profiles' entry conditions ALREADY encode regime detection. Filtering on top = double-filtering = over-constraining.
**Lesson Learned:** Entry logic IS regime detection. Don't add explicit filtering.
**Don't Retry Because:** Validated empirically. More filtering = worse results.

### Failed Approach 4: Skip DeepSeek Verification Before Tests
**Tried:** Multiple times (2025-11-14)
**Hypothesis:** Can run tests directly, debug if they fail
**Result:** Wasted 50K tokens debugging broken tests. DeepSeek would have caught bugs before execution.
**Why It Failed:** Debugging costs 25x more tokens than pre-validation. False economy.
**Lesson Learned:** Use DeepSeek swarm BEFORE running tests to validate approach.
**Don't Retry Because:** Proven pattern - invest 2K tokens to save 50K tokens.

---

## 📊 CURRENT STATE OF RESEARCH

**Where We Started (2025-11-13):**
Initial hypothesis: "Regime-based convexity rotation can harvest structural edge"
Built: Data spine → Regime classifier → Profile scoring → Trade simulator

**Key Pivots:**
1. (2025-11-14) Discovered transaction cost assumption was 25x wrong → Revalidated everything
2. (2025-11-14) Found regime filtering HURTS performance → De-emphasized rotation, focus on exits
3. (2025-11-14) Validated framework has $83K edge → Confidence to proceed

**Where We Are Now (2025-11-15):**
Framework validated. $83K baseline confirmed. Ready to build intelligent exit system to improve from 30% capture to 40-50% capture. Focusing on Profile 3 (CHARM) as strongest candidate ($65K peak potential).

**Progress Metrics:**
- Hypothesis confidence: **HIGH** (validated with clean data)
- Implementation: **70% complete** (data, regimes, profiles, simulator done; exits pending)
- Validation status: **Framework validated** | Exit system pending

---

## 🔮 WHAT'S NEXT

**Immediate Next Steps (Priority Order):**

1. **Test Simple Vol Filter** (Quick Win - 1-2 hours)
   - Add RV > 15% OR VIX > 18 to Profile 1
   - Measure win rate improvement (expecting 36% → 50%+)
   - If works: Apply to all profiles

2. **Build Intelligent Exit System** (High Priority - 1 week)
   - Implement DynamicExitManager from option-machine
   - Runner trail stop (keep 50-65% of max profit)
   - Quick win detection (+$200 in <3 days)
   - Momentum stall detection (flat >6 hours)
   - Stop loss (-8% hard stop)
   - Test on Profile 3 (CHARM) with minute bars

3. **Profile 3 (CHARM) Deep Dive** (After exits work)
   - Isolated backtest (no other profiles)
   - CARRY regime filter (low vol) - showed +$5K
   - Different DTE options (30 vs 45 vs 60)
   - Target: $19K → $30K+ with optimization

**Open Questions to Resolve:**
- Can intelligent exits capture 40-50% instead of 30%?
- Does vol filter improve win rate to 50%+?
- Is Profile 3 (CHARM) viable as standalone strategy?

**If X, Then Y:**
- If vol filter works → Apply to all 6 profiles, expect $100K+ baseline
- If exit system works → $83K → $110K+ (50% capture)
- If Profile 3 strong standalone → Focus entirely on CHARM, scale that first

---

## 📚 KEY REFERENCES

**Papers/Research:**
- (Add relevant papers as research progresses)

**Code Files (Critical):**
- `src/profiles/detectors.py` - 6 profile scoring functions (PRODUCTION)
- `src/trading/simulator.py` - Event-driven backtest engine (PRODUCTION)
- `src/trading/profiles/profile_3.py` - CHARM implementation (strongest profile)
- `test_all_6_profiles.py` - Validation script that proved $83K edge

**Notebooks:**
- (None yet - consider creating analysis notebooks)

**External Resources:**
- `/Volumes/VelocityData/` - SPY minute bars (1,500 files ready for exit testing)
- option-machine repo - DynamicExitManager logic to port

**Data Sources:**
- Polygon API (options data 2014-2025)
- Massive.com (streaming data subscription)

---

## 🧠 MENTAL MODEL SUMMARY

**In 3 sentences, what is this strategy?**

This strategy exploits systematic convexity mispricings in SPY options by rotating capital across 6 distinct convexity profiles based on market microstructure. Each profile targets a specific type of Greek exposure (long gamma, charm, vanna, skew, vol-of-vol) that becomes underpriced during particular market conditions. Edge comes from capturing convexity arbitrage, not directional bets or vol arbitrage.

**When should I use this vs standard approaches?**

Use this when you want:
- Non-directional exposure (market-neutral or delta-hedged)
- Structural edge from convexity mispricing (not betting on direction)
- High Sharpe ratio from multiple uncorrelated profile types
- Systematic, rules-based approach (no discretion)

Avoid if:
- You need high win rate (this is 35-50%, big wins small losses)
- You can't handle 7-day+ hold periods
- You need intraday liquidity (exits require time)
- You want simple buy-and-hold (this requires active monitoring)

---

**This document is the BRAIN of the strategy. Update after every major discovery.**

**Last Major Updates:**
- 2025-11-14: Framework validated ($83K baseline), transaction costs corrected, regime filtering de-emphasized
- 2025-11-15: Created this document, prioritized exit intelligence, identified Profile 3 as strongest
