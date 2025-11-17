# ROTATION ENGINE - ARCHITECTURE QUICK REFERENCE

**One-Page Summary for Developers**

---

## SYSTEM OVERVIEW

```
SPY + Options Data
      ↓
   Features (RV, ATR, MA)
      ↓
Regime Signals (percentiles, slopes)
      ↓
Regime Classification (1-6 regimes)
      ↓
Profile Scoring (6 profiles, 0-1 each)
      ↓
Allocation Weights (rotation logic)
      ↓
Trade Execution (per-profile backtests)
      ↓
Portfolio P&L (aggregation)
      ↓
Performance Metrics
```

---

## 5-LAYER ARCHITECTURE

### Layer 1: Data
- **What:** Raw data + feature engineering
- **Files:** `src/data/loaders.py`, `src/data/features.py`
- **Output:** SPY OHLCV + computed features (RV, ATR, MA, slopes)
- **Key Functions:** `load_spy_data()`, `compute_realized_vol()`

### Layer 2: Regimes
- **What:** Market regime detection (walk-forward)
- **Files:** `src/regimes/signals.py`, `src/regimes/classifier.py`
- **Output:** Regime labels (1-6) per day
- **Key Functions:** `compute_all_signals()`, `classify_period()`
- **Regimes:** 1=Trend Up, 2=Trend Down, 3=Compression, 4=Breaking Vol, 5=Choppy, 6=Event

### Layer 3: Profiles
- **What:** Convexity profile detection
- **Files:** `src/profiles/detectors.py`, `src/profiles/features.py`
- **Output:** Profile scores [0, 1] for 6 profiles
- **Key Functions:** `compute_all_profiles()`, `_compute_long_gamma_score()`
- **Profiles:** LDG, SDG, Charm, Vanna, Skew, VoV

### Layer 4: Trading
- **What:** Trade execution + position tracking
- **Files:** `src/trading/simulator.py`, `src/trading/trade.py`, `src/trading/execution.py`
- **Output:** Daily P&L per profile
- **Key Functions:** `TradeSimulator.simulate()`, `ExecutionModel.calculate_costs()`

### Layer 5: Analysis
- **What:** Portfolio aggregation + metrics
- **Files:** `src/backtest/engine.py`, `src/backtest/portfolio.py`
- **Output:** Portfolio P&L, attribution, metrics
- **Key Functions:** `RotationEngine.run()`, `aggregate_pnl()`

---

## KEY CONCEPTS

### Walk-Forward Compliance
- All signals computed using only PAST data
- No `.shift(-1)` (look-ahead)
- All `.rolling()` calls are walk-forward by default
- **Critical:** Percentile calculations must exclude current row

**Where to check:** `src/regimes/signals.py:99-110`

### Regime Compatibility Matrix
Links profiles to regimes through explicit weights:

```python
REGIME_COMPATIBILITY = {
    1: {                    # Trend Up
        'profile_1': 1.0,   # LDG strong
        'profile_2': 0.0,   # SDG avoid
        'profile_3': 0.3,   # Charm weak
        ...
    },
    ...
}
```

**Where to find:** `src/backtest/rotation.py:19-60`

### Allocation Pipeline
```
Profile Scores [0, 1]
    ↓
Multiply by Regime Weights
    ↓
Normalize to [0, 1]
    ↓
Apply Constraints (max 40%, min 5%, VIX scaling)
    ↓
Daily Allocation Weights
```

**Key file:** `src/backtest/rotation.py:63-326`

### Trade Lifecycle
```
ENTRY → HOLDING → EXIT
```

- Entry: Define legs, entry prices, Greeks
- Holding: Track P&L, manage hedge, roll if needed
- Exit: Record exit prices, compute realized P&L

**Key file:** `src/trading/trade.py:31-80`

---

## CRITICAL FILES

| File | Purpose | Status |
|------|---------|--------|
| `src/backtest/engine.py` | Main orchestrator | ✓ Working |
| `src/data/loaders.py` | Data integration | ✓ Working |
| `src/regimes/classifier.py` | Regime detection | ⚠️ Has bugs |
| `src/profiles/detectors.py` | Profile scoring | ✓ Working |
| `src/backtest/rotation.py` | Allocation logic | ⚠️ Has bugs |
| `src/trading/simulator.py` | Trade execution | ⚠️ Has bugs |
| `src/trading/trade.py` | Position tracking | ⚠️ Has bugs |
| `src/trading/execution.py` | Execution costs | ⚠️ Undersimplified |

---

## KNOWN ISSUES

### Critical (Backtest Invalid)
- **BUG-C01:** P&L sign inverted - MUST FIX
- **BUG-C02:** Greeks never calculated - MUST FIX
- **BUG-C04:** Duplicate percentile implementations - MUST FIX
- **BUG-C06:** Slope calculation magnitude error - MUST FIX

**Status:** Details in CODE_REVIEW_MASTER_FINDINGS.md

### High Priority (Before Live Trading)
- **BUG-H01:** Short-dated spreads too tight
- **BUG-H02:** OTM spreads too tight
- **BUG-H03:** Can't roll individual legs

### Medium
- **BUG-M01:** Allocation weights don't re-normalize after VIX scaling
- **BUG-M02:** Slope not normalized by price level
- **BUG-M03:** Inconsistent walk-forward implementations

---

## DATA FLOW (How Data Moves)

```
1. Raw SPY OHLCV
   ↓ (add features)
2. SPY + Features
   ↓ (add signals)
3. SPY + Signals
   ↓ (classify)
4. SPY + Regime
   ↓ (score profiles)
5. SPY + Profile Scores
   ↓ (allocate)
6. Allocations (weights per profile)
   ↓ (backtest each)
7. Profile P&Ls (daily profit/loss)
   ↓ (aggregate)
8. Portfolio P&L (sum weighted P&Ls)
   ↓ (analyze)
9. Metrics (Sharpe, Sortino, etc.)
```

---

## DEPENDENCIES (What Imports What)

```
Layer 1 (Data):
  No internal imports

Layer 2 (Regimes):
  Imports: Layer 1

Layer 3 (Profiles):
  Imports: Layer 1

Layer 4 (Trading):
  Imports: Layer 1, Layer 2, Layer 3

Layer 5 (Analysis):
  Imports: All layers
```

**Key Rule:** No imports go upward (e.g., Layer 1 never imports Layer 2)

---

## HOW TO ADD A NEW FEATURE

**Example: Add Profile 7 (SomeNewStrategy)**

1. **Add detector:** Create `src/profiles/detectors.py._compute_profile_7_score()`
2. **Add feature:** Extend `src/profiles/features.py` with needed pre-calculations
3. **Add trading logic:** Create `src/trading/profiles/profile_7.py` with entry/exit rules
4. **Add regime weights:** Update `src/backtest/rotation.py:REGIME_COMPATIBILITY[regime]['profile_7'] = weight`
5. **Add config:** Update `src/backtest/engine.py` with threshold and regime filter for Profile 7
6. **Test:** Write unit tests for detector + run end-to-end backtest

**No other files changed.** That's the power of modular architecture.

---

## HOW TO CHANGE DATA SOURCE

**Example: Switch from yfinance to custom data**

1. **Modify:** `src/data/loaders.py:OptionsDataLoader.load_spy_ohlcv()`
2. **Change:** Data loading logic from yfinance to your source
3. **Everything else:** Works unchanged

The `DataSpine` interface remains the same, so no downstream changes needed.

---

## HOW TO UPGRADE IV PROXY → REAL IV

1. **In:** `src/profiles/features.py`
2. **Find:** `_compute_iv_proxies()` function (lines 81-98)
3. **Replace:** RV×1.2 with real IV extraction from options chain
4. **No other changes needed.**

---

## KEY THRESHOLDS TO UNDERSTAND

| Threshold | Value | Location | Purpose |
|-----------|-------|----------|---------|
| Profile Score Min | 0.50-0.60 | Config | Entry threshold |
| RV Percentile Low | 30% | `classifier.py:44` | Vol rank low |
| RV Percentile High | 80% | `classifier.py:45` | Vol rank high |
| Compression Range | 3.5% | `classifier.py:43` | Max pinned range |
| Max Weight | 40% | `rotation.py:77` | Per-profile cap |
| Min Weight | 5% | `rotation.py:78` | Allocation floor |
| VIX Threshold | 30% | `engine.py:54` | Vol scaling trigger |
| DTE Target | 60-90 | Profile-specific | Entry timing |
| Roll DTE | 30 | Profile-specific | Roll timing |

---

## TESTING CHECKLIST

**Before running backtest:**
- [ ] Data loads without errors
- [ ] Features computed for all dates
- [ ] No NaNs in critical columns
- [ ] Regime labels are 1-6
- [ ] Profile scores are [0, 1]
- [ ] Allocations sum to 1.0

**After backtest:**
- [ ] P&L values are reasonable (not -999999999)
- [ ] No sudden jumps (signs of data/calculation errors)
- [ ] Attribution sums to total P&L
- [ ] Rotation is happening (not stuck in one profile)

---

## GLOSSARY

| Term | Meaning |
|------|---------|
| **Walk-Forward** | Compute using only PAST data, no future info |
| **RV** | Realized Volatility (historical vol of returns) |
| **IV** | Implied Volatility (market expectation of future vol) |
| **DTE** | Days To Expiration |
| **ATM** | At The Money (strike = spot price) |
| **OTM** | Out The Money (unprofitable without move) |
| **Delta** | Price sensitivity (how much option moves with spot) |
| **Gamma** | Delta sensitivity (convexity) |
| **Theta** | Time decay (daily P&L from time passing) |
| **Vega** | Vol sensitivity (profit from vol changes) |

---

## PRODUCTION CHECKLIST

**Before Trading Real Capital:**

- [ ] All 8 critical bugs fixed
- [ ] All 3 high-priority bugs fixed
- [ ] Greeks calculated correctly
- [ ] Execution costs empirically calibrated
- [ ] Walk-forward compliance validated
- [ ] 5-year backtest complete
- [ ] Red team review passed
- [ ] Risk framework documented
- [ ] Position sizing rules defined
- [ ] Live trading simulation for 1 week

---

## COMMON MISTAKES

❌ **Using mid-price instead of bid/ask**
- Always use `ask` for entries, `bid` for exits

❌ **Including current day in rolling calculations**
- Must exclude current row from percentile/moving average

❌ **Forgetting commission/fees**
- Add spread + commission + exchange fees

❌ **Not normalizing slopes by price level**
- MA slope changes meaning if SPY moves from 300 to 600

❌ **Hardcoding regimes or thresholds**
- Make them parameters

❌ **Testing on full dataset before splitting**
- Train/test split MUST happen before any fitting

---

## RESOURCES

**Detailed Documentation:**
- `ARCHITECTURE_AUDIT_REPORT.md` - Full architecture review
- `ARCHITECTURAL_RECOMMENDATIONS.md` - Specific improvements
- `CODE_REVIEW_MASTER_FINDINGS.md` - Bug details

**Code References:**
- Entry point: `src/backtest/engine.py`
- Main logic: `src/backtest/rotation.py`
- Execution: `src/trading/simulator.py`

---

**Last Updated:** November 13, 2025
**Version:** 1.0 (Architecture Review)
