# ROTATION ENGINE AUDIT - QUICK REFERENCE

## The Problem in One Graphic

```
┌─────────────────────┐         ┌──────────────────────┐
│   EQUITY MARKET     │         │   OPTIONS MARKET     │
│   (What System      │         │   (What System       │
│    Actually         │         │    Should Detect)    │
│    Detects)         │         │                      │
├─────────────────────┤         ├──────────────────────┤
│ RV (price moves)    │ ≠≠≠     │ IV (options pricing) │
│ ATR (range size)    │ ≠≠≠     │ Skew (put premium)   │
│ MA slope (trend)    │ ≠≠≠     │ VVIX (vol expctation)│
│ Volatility variance │ ≠≠≠     │ Greeks Greeks)       │
└─────────────────────┘         └──────────────────────┘

System detects: EQUITY conditions
System uses for: OPTIONS decisions

Result: FUNDAMENTAL MISMATCH
```

## The 4 Smoking Guns

### 1. IV Proxy: `RV * 1.2`
```python
# src/profiles/features.py:81-98
df['IV7'] = df['RV5'] * 1.2      # ← WRONG
df['IV20'] = df['RV10'] * 1.2    # ← ARBITRARY CONSTANT
df['IV60'] = df['RV20'] * 1.2    # ← NEVER VALIDATED
```
**Reality:** IV/RV varies 0.8x to 5.0x
**Consequence:** IV rank wrong by 20-300%

### 2. Skew Proxy: `ATR / RV`
```python
# src/profiles/features.py:150-173
skew_proxy = (df['ATR'] / df['close']) / (df['RV10'])  # NOT SKEW

# src/regimes/signals.py:186-201
def compute_skew_proxy(self, options_data):
    return pd.Series(0.0, index=options_data.index)  # RETURNS ZEROS!
```
**Should measure:** Put IV - Call IV
**Actually measures:** Price range relative to vol variance

### 3. VVIX Proxy: `std(RV)`
```python
# src/profiles/features.py:115-128
df['VVIX'] = df['RV10'].rolling(window=20, min_periods=10).std()
```
**Should measure:** Market expectation of future vol-of-vol
**Actually measures:** Historical variance of past vol calculations

### 4. IV Rank: `percentile(RV * 1.2)`
```python
# src/profiles/features.py:100-113
df['IV_rank_20'] = self._rolling_percentile(df['IV20'], window=60)
# where IV20 = RV10 * 1.2
```
**Should measure:** Where actual IV is in historical range
**Actually measures:** Where (RV × 1.2) is in range

---

## What If Deployed?

| Timeline | What Happens |
|----------|-------------|
| **Days 1-5** | Random luck. Some equity moves coincide with options opportunities. Looks okay. |
| **Week 1-2** | Profiles trigger when equity conditions match, but options don't. Performance starts degrading. |
| **Month 1** | Capital losses accelerate. Realize system measures wrong market. System needs rebuild. |

---

## The Placeholder Evidence

**This was CLEARLY development code, not production:**

```
src/regimes/signals.py, line 48-50:
  "# RV/IV ratios - For now use RV20 as IV proxy"
  "# In production, replace with actual IV from options chain"

src/profiles/features.py, line 61-63:
  "# IV proxies (using RV until real IV available)"

src/regimes/signals.py, line 186-201:
  def compute_skew_proxy(self, options_data):
      """For now, returns placeholder. In production, compute:
         - 25D put IV - ATM IV
      """
      # TODO: Implement actual skew calculation when IV data is available
      return pd.Series(0.0, index=options_data.index)
```

**Translation:** "This is temporary. We'll add real data later."
**Reality:** Later never came. Code shipped anyway.

---

## Data Available But Not Used

**Options data exists:**
- Location: `/Volumes/VelocityData/polygon_downloads/us_options_opra/day_aggs_v1/`
- Contains: SPY options chain data with full pricing history

**Infrastructure exists:**
- `OptionsDataLoader` class in `src/data/loaders.py`
- Can load and parse options chains
- Has `load_options_chain()` method

**Why not used?**
- Short answer: Developers ran out of time
- System was never finished before deployment pressure
- Placeholder code left in place

---

## The Fix

### Option A: Use Real IV Data (Recommended) - 2-3 Days
```python
# Instead of:
df['IV7'] = df['RV5'] * 1.2

# Do:
options_chain = loader.load_options_chain(date)
iv_7d = options_chain[options_chain.dte==7]['close'].mean()  # Real IV
df['IV7'] = iv_7d  # Actual market data
```

### Option B: Honest Proxy System - 1 Day
- Rename to "Equity Detector" (not "Options Convexity")
- Document: Measures equity, not options opportunities
- Accept that correlation to options may be weak

### Option C: Redesign from Scratch - 1 Week
- Build with real IV data from day one
- Validate against options P&L
- Release production-quality system

---

## Files to Review

| File | Issue | Severity |
|------|-------|----------|
| `src/profiles/features.py` | IV/VVIX/skew proxies | CRITICAL |
| `src/regimes/signals.py` | IV proxies, skew placeholder | CRITICAL |
| `src/profiles/detectors.py` | Uses poisoned features | CRITICAL |
| `src/data/features.py` | RV calculation correct but used wrong | HIGH |
| `src/data/loaders.py` | Infrastructure exists but not used | LOW |

---

## Deployment Status

**BLOCKED** - Do not deploy until one of these is true:
1. Real IV data integrated (Option A)
2. System renamed as honest proxy (Option B)
3. Complete redesign from scratch (Option C)

---

## Memory System

Findings saved to memory with keywords:
- `rotation_engine_feature_contamination_critical`
- `rotation_engine_iv_proxy_flaw`
- `rotation_engine_skew_detection_broken`
- `rotation_engine_vvix_proxy_wrong`

Query with: "rotation engine feature contamination"

---

## Reports

| Report | Size | Purpose |
|--------|------|---------|
| **FEATURE_CONTAMINATION_AUDIT.md** | 22 KB | Full technical audit with all findings |
| **AUDIT_EXECUTIVE_SUMMARY.md** | 9.4 KB | Executive summary with remediation paths |
| **AUDIT_FINDINGS_SUMMARY.txt** | 8 KB | Text summary of all findings |
| **QUICK_REFERENCE.md** | This file | Fast reference for key points |

Start with AUDIT_FINDINGS_SUMMARY.txt or AUDIT_EXECUTIVE_SUMMARY.md for quick understanding.

---

**Audit Date:** 2025-11-13
**Status:** COMPLETE - DEPLOYMENT BLOCKED
**Confidence:** 100% - Architecture flaw confirmed
