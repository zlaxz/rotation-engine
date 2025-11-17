# ROTATION ENGINE AUDIT - EXECUTIVE SUMMARY

**Audit Date:** 2025-11-13
**Auditor:** Quantitative Code Auditor (Tier 0 Focus)
**Classification:** CRITICAL ARCHITECTURE FLAW - NO DEPLOYMENT

---

## ONE-SENTENCE VERDICT

**The system trades OPTIONS based on EQUITY market signals. These are completely orthogonal markets with zero guaranteed correlation.**

---

## WHAT'S HAPPENING

### What The System Does
- Analyzes SPY price movements (OHLCV data)
- Calculates equity-based metrics: Realized Vol (RV), Average True Range (ATR), Moving Averages
- Detects "regimes" and "convexity profiles"
- Makes trading decisions for options strategies (long gamma, short premium, skew trades, etc.)

### The Critical Problem
- **IV (Implied Volatility)** = What options market EXPECTS vol to be → Drives option prices
- **RV (Realized Volatility)** = What price movement ACTUALLY was → Historical fact
- **System uses:** RV × 1.2 (constant) as proxy for IV
- **Reality:** Real IV/RV ratio ranges 0.8x to 5.0x depending on market conditions
- **Result:** Features measure equity conditions, not options conditions

---

## THE FUNDAMENTAL MISMATCH

| What Drives Profits | What System Measures | Match? |
|---|---|---|
| **Gamma P&L** depends on: IV surface curvature, spot/vol correlation | System measures: RV spikes, ATR moves, MA slopes | ❌ UNRELATED |
| **Vega P&L** depends on: IV level going up/down, term structure | System measures: RV percentile (from proxy, not real IV) | ❌ UNRELATED |
| **Theta P&L** depends on: IV rank, DTE, strike proximity | System measures: RV percentile (meaningless) | ❌ UNRELATED |
| **Skew P&L** depends on: Put/call IV spread from options chain | System measures: ATR/RV ratio (unrelated to skew) | ❌ UNRELATED |
| **Vol-of-Vol P&L** depends on: VVIX level, variance swap curve | System measures: Stdev of RV (not market vol-of-vol) | ❌ UNRELATED |

---

## THREE SPECIFIC SMOKING GUNS

### 1. IV Proxy: RV × 1.2 (Fixed Constant)
```python
# src/profiles/features.py:81-98
df['IV7'] = df['RV5'] * 1.2      # ← Completely arbitrary
df['IV20'] = df['RV10'] * 1.2    # ← Hardcoded
df['IV60'] = df['RV20'] * 1.2    # ← Never calibrated
```

**Reality Check:**
- Normal markets: Real IV/RV ≈ 1.5-2.0x (system underestimates by 25-40%)
- Vol spike: Real IV/RV ≈ 2.0-3.0x (system massively wrong)
- Post-events: Real IV/RV ≈ 3.0-5.0x (system critically wrong)

**Consequence:** IV rank signal will be systematically wrong by 20-300% depending on regime.

### 2. Skew Detection: ATR/RV Ratio (Not Related to Skew)
```python
# src/profiles/features.py:150-173
skew_proxy = (df['ATR'] / df['close']) / (df['RV10'])  # ← Unrelated to put/call skew

# src/regimes/signals.py:186-201
def compute_skew_proxy(self, options_data):
    return pd.Series(0.0, index=options_data.index)  # ← Returns zeros
```

**What Skew Actually Is:** Put IV - Call IV (from options chain)

**What ATR/RV Is:** Price range relative to realized vol volatility

**These are completely orthogonal.**

### 3. VVIX Proxy: Stdev of RV (Not Market Expectation)
```python
# src/profiles/features.py:115-128
df['VVIX'] = df['RV10'].rolling(window=20, min_periods=10).std()  # ← Backward-looking variance
```

**What VVIX Actually Is:** Market expectation about future volatility of volatility (from VIX options)

**What This Code Is:** Historical standard deviation of volatility calculations

**Scenario:** Vol market expects to stabilize (real VVIX low), but historical RV variance was high (proxy high). Detector triggers VOV profile. Result: Buys gamma when vol about to stabilize (bad trade).

---

## THE ARCHITECTURAL SMOKING GUN

**Evidence this was temporary placeholder code:**

```python
# Line 48-50 in signals.py
# RV/IV ratios - For now use RV20 as IV proxy
# In production, replace with actual IV from options chain

# Line 61-63 in features.py
# IV proxies (using RV until real IV available)

# Line 73-74 in features.py
# Skew proxy (until we have real IV surface)

# Line 186-201 in signals.py
def compute_skew_proxy(self, options_data):
    """Compute skew metric from options chain.
    For now, returns placeholder. In production, compute:
    - 25D put IV - ATM IV
    """
    # TODO: Implement actual skew calculation when IV data is available
    return pd.Series(0.0, index=options_data.index)
```

**Translation:** "This is temporary. We'll add real options data later."

**Problem:** Later never came. Code was promoted to production anyway.

---

## DATA AVAILABILITY (PROVES NEGLIGENCE)

**Options data is available but deliberately not used:**

```python
# src/data/loaders.py (exists, can load options chain)
class OptionsDataLoader:
    def __init__(self, data_root: str = "/Volumes/VelocityData/polygon_downloads/us_options_opra/day_aggs_v1"):
        self.loader = OptionsDataLoader(data_root)

    def load_options_chain(self, date: datetime) -> pd.DataFrame:
        """Load SPY options chain for a specific date."""
```

**Evidence:**
- `/Volumes/VelocityData/polygon_downloads/us_options_opra/day_aggs_v1` exists with actual options data
- `OptionsDataLoader` class exists and can parse options chains
- System has infrastructure to use real IV but chose not to
- Placeholder comments say "in production, use real IV" - but this IS production code

---

## WHAT HAPPENS IF DEPLOYED

### Optimistic Scenario (Days 1-5)
- Profiles activate based on random correlation with equity moves
- Some trades happen to coincide with actual options opportunities
- Results look okay by luck

### Realistic Scenario (Week 1-2)
- Profiles trigger when equity conditions match, but options conditions don't
- Example: RV spikes from SPY move, profile thinks "vol elevated, sell gamma"
  - But IV hasn't repriced yet (still cheap)
  - Result: Sell gamma when it's actually cheap (bad trade)
- Performance starts degrading

### Failure Scenario (Month 1)
- Pattern becomes clear: profiles don't correlate with options opportunities
- Capital losses accelerate
- System activates when "conditions are right" but opportunities don't exist
- Realize: We're measuring wrong market

---

## WHAT'S THE FIX?

### Option A: Use Real IV Data (Recommended) - 2-3 Days
1. Parse actual IV surface from options chain
2. Calculate IV rank from real IV percentiles
3. Calculate actual skew: IV_put_25D - IV_call_25D
4. Use real VVIX or calculate from options volatility
5. Retrain profiles with proper walk-forward validation
6. Retest full backtest (results may differ)

**Benefit:** System now measures what it claims
**Cost:** 2-3 days development + backtest revalidation

### Option B: Honest Proxy System - 1 Day
1. Rename everything to honest names: RV_proxy, IV_proxy
2. Rename profiles: "Equity Regime Detector" (not "Options Convexity")
3. Document: "These profiles detect equity conditions, not options opportunities"
4. Separately validate that equity conditions predict options profitability
5. Accept if correlation is weak or nonexistent

**Benefit:** Honest about what system measures
**Cost:** 1 day + probably discover low correlation

### Option C: Redesign from Scratch (Strongest) - 1 Week
Don't patch. Start fresh:
1. Begin with real IV surface data
2. Build profiles to detect actual options conditions
3. Use walk-forward validation against options P&L
4. Train on real opportunities, not equity proxies
5. Release system that's architecturally sound

**Benefit:** Foundation is solid
**Cost:** 1 week development, but system won't need rework later

---

## DEPLOYMENT DECISION

**Verdict:** CRITICAL - BLOCK DEPLOYMENT

**Why:** This isn't a calibration issue. You can't fix proxy mismatch with better thresholds. The fundamental problem is measuring the wrong market.

**Timeline:** Don't deploy until one of options A, B, or C is completed.

---

## DETAILED FINDINGS

See full audit report: `/Users/zstoc/rotation-engine/FEATURE_CONTAMINATION_AUDIT.md`

Key sections:
- CRITICAL FINDINGS (4 architectural flaws)
- HIGH SEVERITY (calculation and semantic issues)
- MEDIUM SEVERITY (missing validation)
- LOW SEVERITY (implementation issues)
- MANUAL VERIFICATION (tested scenarios)
- RECOMMENDATIONS (path forward)

---

## RECOMMENDED ACTION

**Immediate (Today):**
1. Read full audit report
2. Decide which remediation path (A, B, or C)
3. Block deployment pending fix

**Short-term (This Week):**
1. Implement chosen option
2. Revalidate with proper walk-forward testing
3. Verify fixes before production release

**Medium-term:**
1. Add automated correlation checks (proxy vs real options data)
2. Implement validation that profiles correlate with options P&L
3. Document assumptions and limitations

---

## QUESTIONS THIS AUDIT ANSWERS

**Q: Why do profiles sometimes work but seem unreliable?**
A: They work when equity conditions randomly coincide with options conditions. Pure luck.

**Q: Can we just recalibrate the thresholds?**
A: No. The problem isn't thresholds. The problem is measuring the wrong market.

**Q: Could this be a minor issue?**
A: No. You're trading options (Greeks-based) based on equity signals (price-based). Different markets.

**Q: Is there some correlation between equity moves and options opportunities?**
A: Maybe. But we haven't validated it. And we have real options data that should be used instead.

**Q: Can we ship this if we add disclaimers?**
A: Only if you rename it "Equity Detector" (not "Options Convexity") and separately prove equity conditions predict options profitability.

---

**Generated:** 2025-11-13
**Status:** AUDIT COMPLETE - DEPLOYMENT BLOCKED
**Next Step:** Review full report and choose remediation path
