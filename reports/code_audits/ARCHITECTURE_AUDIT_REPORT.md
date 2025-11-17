# ROTATION ENGINE - ARCHITECTURAL AUDIT REPORT

**Project:** `/Users/zstoc/rotation-engine`
**Date:** November 13, 2025
**Auditor:** Quantitative Architecture Specialist
**Mission:** High-level architectural soundness assessment

---

## EXECUTIVE SUMMARY

**VERDICT: ARCHITECTURE IS FUNDAMENTALLY SOUND BUT INFRASTRUCTURE HAS CRITICAL IMPLEMENTATION BUGS**

**Verdict Type:** Keep architecture, fix implementation bugs

The rotation engine has been designed with **excellent conceptual organization**. The modular separation, data flow, walk-forward structure, and integration patterns are well-thought-out. However, the **infrastructure layer (data handling, calculations, execution modeling)** contains **14 critical implementation bugs** that make current results unreliable.

**Key Finding:** This is NOT a "start from scratch" situation. It's a "fix the bugs you have" situation with an architecture that is ready for production once implementation is corrected.

---

## SECTION 1: ARCHITECTURAL STRENGTHS

### 1.1 Module Separation - EXCELLENT

The codebase is organized into 5 logical modules with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Data Layer                                    │
│  - src/data/loaders.py    : Options + SPY data loading  │
│  - src/data/features.py   : Feature engineering         │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 2: Regime Detection                              │
│  - src/regimes/signals.py      : Walk-forward signals   │
│  - src/regimes/classifier.py   : Priority-based rules   │
│  - src/regimes/validator.py    : Historical validation  │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Profile Detection                             │
│  - src/profiles/features.py    : IV proxies, rankings   │
│  - src/profiles/detectors.py   : 6 profile scorers      │
│  - src/profiles/validator.py   : Score validation       │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 4: Allocation & Trading                          │
│  - src/backtest/rotation.py    : Desirability scoring   │
│  - src/trading/simulator.py    : Trade execution        │
│  - src/trading/trade.py        : Position tracking      │
│  - src/trading/execution.py    : Execution costs        │
│  - src/trading/profiles/*.py   : Profile-specific logic │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 5: Results & Analysis                            │
│  - src/backtest/portfolio.py   : P&L aggregation        │
│  - src/backtest/engine.py      : Orchestration          │
│  - src/analysis/metrics.py     : Performance metrics    │
└─────────────────────────────────────────────────────────┘
```

**Why This Is Good:**
- Each module has ONE responsibility
- Dependencies flow downward only (no circular dependencies detected)
- Easy to test each layer independently
- Easy to swap implementations (e.g., replace IV proxy with real IV)
- Clear data contracts between layers

**Grade: A+**

---

### 1.2 Data Flow Design - EXCELLENT

The orchestration engine (`src/backtest/engine.py`) implements a clean, sequential pipeline:

```
Step 1: Load data
Step 2: Compute profile scores  (features → detectors)
Step 3: Run profile backtests   (simulator.simulate())
Step 4: Calculate allocations   (rotation.allocate_daily())
Step 5: Aggregate portfolio P&L (portfolio.aggregate_pnl())
Step 6: Calculate attribution   (portfolio.calculate_attribution())
Step 7: Generate metrics        (metrics.compute_metrics())
```

**Why This Is Good:**
- No re-computation of earlier steps
- Clear sequence prevents data leakage
- Easy to trace which step produces which data
- Easy to debug (isolate step, run in isolation)

**Code Reference:** `src/backtest/engine.py:89-214`

**Grade: A**

---

### 1.3 Walk-Forward Compliance - SOLID

The codebase **declares** walk-forward intent in docstrings and implements walk-forward calculations in key places:

**Walk-Forward Implementations Found:**
- ✅ `src/regimes/signals.py:99-110`: Walk-forward percentile calculation
- ✅ `src/profiles/features.py:100-120`: Walk-forward percentile for IV ranks
- ✅ All rolling window calculations use `.rolling()` (which is walk-forward by default)

**No obvious look-ahead bias in:**
- Feature calculations (all use past data only)
- Regime classifications (use computed signals, not future data)
- Profile scoring (based on historical percentiles)

**Caveat:** The most recent code review found **BUG-C05 (off-by-one shift error)** in signals.py that partially breaks walk-forward compliance, but the core design supports it.

**Grade: A- (implementation has bugs, design is clean)**

---

### 1.4 Regime Compatibility Matrix - EXCELLENT CONCEPT

The rotation allocator uses a **regime compatibility matrix** (`src/backtest/rotation.py:19-60`) that maps:

```
For each regime (Trend Up, Trend Down, etc.):
  For each profile (LDG, SDG, Charm, Vanna, Skew, VoV):
    Specify: compatibility weight [0, 1]
```

**Example:** In Trend Up:
- LDG: 1.0 (strong) - long gamma thrives with consistent uptrend
- Vanna: 1.0 (strong) - vanna profits from price + vol correlation
- Skew: 0.0 (avoid) - skew strategies lose when vol expands

**Why This Is Good:**
- Transparent, auditable logic
- Can validate against first principles (market microstructure theory)
- Easy to update based on new research
- Prevents allocating to mismatched profiles

**Grade: A+**

---

### 1.5 Trade Lifecycle Design - GOOD

The Trade object (`src/trading/trade.py`) cleanly separates:

- **Entry phase:** legs, entry_prices, entry_cost, underlying price
- **Holding phase:** is_open flag, delta hedging, Greeks tracking
- **Exit phase:** exit_date, exit_prices, exit_reason, realized_pnl

Multi-leg structures are explicitly supported:
- `legs: List[TradeLeg]` - supports any number of legs
- `entry_prices: Dict[int, float]` - per-leg pricing

**Why This Is Good:**
- Scalable (diagonal spreads, iron condors, etc. all supported)
- Clear state transitions
- Auditable (every property is explicit, not hidden in calculations)

**Grade: A-**

---

### 1.6 Profile Abstraction - EXCELLENT

The 6 profiles are implemented as:
1. **Detectors** (`src/profiles/detectors.py`): Score each profile
2. **Feature engine** (`src/profiles/features.py`): Pre-compute needed signals
3. **Portfolio modules** (`src/trading/profiles/profile_*.py`): Entry/exit logic

This separation allows:
- Different profiles can have completely different scoring logic
- Each profile's trading logic is isolated
- Easy to add 7th profile (just add detector + module)

**Why This Is Good:**
- No shared state between profiles
- Easy testing (each profile tested independently)
- Easy modification (change one profile without affecting others)

**Grade: A+**

---

### 1.7 Data Source Integration - PRAGMATIC

The system is designed to load:
- **SPY OHLCV** from any source (currently yfinance, can swap)
- **Options data** from Polygon (real, production-grade data)

The `DataSpine` class (`src/data/loaders.py:254-320`) acts as a facade that:
- Combines SPY + options data
- Caches loaded data
- Provides `.get_day_data()` for point lookups

**Why This Is Good:**
- Decoupled from data source (easy to swap providers)
- Production-ready infrastructure
- Caching prevents repeated network calls

**Issue:** Currently using **RV-based IV proxy** instead of real IV:
- `src/profiles/features.py:81-98`: IV computed as `RV × 1.2`
- This is INTENTIONAL (marked as placeholder)
- Real Polygon options data has implied vol available

**Grade: A (design), B+ (implementation - uses proxy)**

---

## SECTION 2: ARCHITECTURAL WEAKNESSES

### 2.1 Greeks Calculation - MISSING

**Finding:** No Black-Scholes Greeks implementation anywhere in codebase.

**Impact:**
- Position delta is unknown (can't hedge properly)
- Vega exposure is unknown (vol hedging broken)
- Portfolio Greeks undefined
- Risk management incomplete

**Why It Matters:**
- Gamma/theta tradeoffs can't be analyzed
- Delta hedging costs can't be calculated (currently hardcoded $15/day)
- Vanna strategy effectiveness can't be validated

**Current State:** All Greeks fields in Trade object (`src/trading/trade.py:62-66`) are initialized to 0.0 and never updated.

**Architectural Implication:** The architecture **expects** Greeks to be calculated but has no implementation. This is an **implementation gap**, not an architectural flaw.

**Fix Complexity:** Medium (4-6 hours to implement Black-Scholes)

**Grade: D (missing critical feature)**

---

### 2.2 IV Sourcing - PROXY ONLY

**Finding:** The system uses RV as a proxy for IV instead of real implied vol:

```python
df['IV7'] = df['RV5'] * 1.2    # Assumed relationship
df['IV20'] = df['RV10'] * 1.2
df['IV60'] = df['RV20'] * 1.2
```

**Reference:** `src/profiles/features.py:81-98`

**Why This Matters:**
- RV/IV relationship varies (sometimes 0.8x, sometimes 2.0x)
- Profile scores based on wrong IV will be wrong
- Skew strategy (relies on IV surface) effectively broken

**Current State:** Marked as PLACEHOLDER - intentional temporary solution.

**Architectural Assessment:** The architecture **supports real IV** - just swap the feature. The gap is **data integration**, not design.

**Example Fix:**
```python
# Instead of:
df['IV60'] = df['RV20'] * 1.2

# Use real IV from options chain:
df['IV60'] = compute_weighted_iv(options_chain, dte=60)
```

**Grade: C+ (architectural support exists, implementation incomplete)**

---

### 2.3 Position Management - Per-Leg Rolling Limited

**Finding:** The Trade object has a single `is_open` flag for the entire position:

```python
is_open: bool = True  # All-or-nothing flag
```

**Impact:** Can't do selective rolling (e.g., roll short leg while holding long leg in diagonal spread).

**Where It Matters:**
- Profile 3 (charm decay) uses 25/30 put spreads
- Can't roll short 25 while keeping long 30
- Position is all-or-nothing

**Architectural Implication:** Would require per-leg state:
```python
is_open: Dict[int, bool] = {}  # Track each leg
```

**Current Workaround:** Entire position is exited/entered atomically (less flexible than it could be).

**Grade: B- (works but could be more flexible)**

---

### 2.4 Execution Model - SIMPLIFIED

The execution model (`src/trading/execution.py`) makes simplifying assumptions:

**Assumptions:**
1. Bid-ask spread depends on DTE and moneyness (empirical)
2. No market impact (assumes size is small)
3. No liquidity constraints (assumes can execute any size)
4. Mid-price available (no last-sale only)

**References:**
- Spread function: `src/trading/execution.py:75-95`
- DTE adjustment: `src/trading/execution.py:71-74`

**Reality Check:**
- SPY options have excellent liquidity (REASONABLE assumption)
- Size of typical strategy is small (typically 1-10 contracts, REASONABLE)
- Spreads are real and measurable (can verify empirically)

**Most Recent Audit Finding:** Spreads are underestimated by 30-50% for short-dated and OTM options (BUG-H01, BUG-H02).

**Architectural Implication:** The architecture **allows empirical calibration** - just update the spread function with real data. This is not a design flaw.

**Grade: B (simplified but reasonable, execution costs underestimated)**

---

## SECTION 3: WALK-FORWARD COMPLIANCE ASSESSMENT

### 3.1 Walk-Forward Design

The system explicitly declares walk-forward compliance and implements it in critical functions:

**Key Walk-Forward Functions:**
1. `src/regimes/signals.py:99`: `_compute_walk_forward_percentile()`
2. `src/profiles/features.py:100`: `_compute_iv_ranks()` uses percentile
3. All `.rolling()` calculations are walk-forward by default in pandas

### 3.2 Walk-Forward Issues Found

**BUG-C04/C05 (Critical):**
- Duplicate percentile implementations in signals.py
- One implementation is 1 day late (shift error)
- Breaks walk-forward on volatile indicators

**References:** CODE_REVIEW_MASTER_FINDINGS.md lines 74-101

**Assessment:** The **concept** is sound, the **implementation** has bugs.

---

## SECTION 4: POLYGON OPTIONS DATA FIT

### 4.1 Data Available (2014-2025)

✅ **Polygon provides:**
- Full options chain per day (all expirations, strikes)
- Volume, bid-ask quotes
- Implied volatility per option
- Greeks in some cases

**System Support:**
- `OptionsDataLoader` class designed to handle full chains
- Can compute IV surface from individual option IVs
- Can extract Greeks (or calculate via Black-Scholes)

**Grade: A (data source matches architecture)**

### 4.2 Data Not Currently Used

❌ **Not integrated yet:**
- Real IV (instead using RV proxy)
- Greeks from quotes (implementing own)
- Order book depth
- Bid-ask dynamics over time

**Architectural Assessment:** These are **implementation gaps**, not design flaws. The architecture supports them.

---

## SECTION 5: CRITICAL IMPLEMENTATION BUGS (From Previous Audits)

The CODE_REVIEW_MASTER_FINDINGS identified 14 bugs across 4 categories:

### CRITICAL (Backtest Invalid): 8 bugs
1. **BUG-C01** - P&L sign inversion (inverted profits/losses)
2. **BUG-C02** - Greeks never calculated (always 0.0)
3. **BUG-C03** - Delta hedging placeholder ($15/day constant)
4. **BUG-C04** - Duplicate percentile implementations (94% discrepancy)
5. **BUG-C05** - Off-by-one shift error (signals 1 day late)
6. **BUG-C06** - Slope calculation 71× magnitude error
7. **BUG-C07** - DTE calculation broken for multi-leg
8. **BUG-C08** - Missing commissions/fees

### HIGH (Pre-Live): 3 bugs
- Short-dated spreads 30-50% too tight
- OTM spreads 20-30% too tight
- Multi-leg rolling limitations

### MEDIUM: 3 bugs
- Allocation weights don't re-normalize after VIX scaling
- Slope not normalized by price level
- Inconsistent walk-forward implementations

**Total Fix Time Estimate:** 16-21 hours

---

## SECTION 6: FINAL VERDICT

### ARCHITECTURAL ASSESSMENT

| Component | Grade | Status |
|-----------|-------|--------|
| **Module Separation** | A+ | Excellent |
| **Data Flow** | A | Clean pipeline |
| **Walk-Forward Design** | A- | Good design, buggy implementation |
| **Regime System** | A+ | Theoretically sound |
| **Profile System** | A+ | Well-architected |
| **Trade Lifecycle** | A- | Supports multi-leg, some limitations |
| **Greeks Integration** | D | Missing entirely |
| **Data Source Fit** | A | Polygon data matches needs |
| **Execution Model** | B | Simplified but calibratable |
| **IV Integration** | C+ | Proxy-based, can upgrade |
| **Overall Architecture** | **A-** | **KEEP - Fix bugs, not redesign** |

### DEPLOYMENT READINESS

**Current Status:** 🔴 BLOCKED (14 critical/high bugs)

**Path to Production:**
1. Fix Phase 1 critical bugs (8-10 hours)
2. Have new code audited (4 hours)
3. Run validation backtest (1 hour)
4. Fix Phase 2 high-priority (6-8 hours)
5. Final validation (2 hours)

**Estimated Path Time:** 21-25 hours of focused work

### WHAT TO DO

**✅ KEEP THIS ARCHITECTURE**
- Don't start over
- Don't refactor modules
- Don't redesign data pipeline

**✅ FIX THE BUGS**
- Phase 1: 8 critical bugs (highest priority)
- Phase 2: 3 high bugs (before live trading)
- Phase 3: 3 medium bugs (housekeeping)

**✅ INTEGRATE REAL DATA**
- Replace IV proxy with real Polygon IV
- Implement Black-Scholes Greeks
- Calibrate execution costs empirically

**✅ VALIDATE METHODOLOGICALLY**
- Walk-forward validation across multiple periods
- Stress test across market regimes
- Red-team the new results

---

## CONCLUSION

**The rotation engine has a solid architectural foundation.** It demonstrates:

1. **Clean module separation** - each piece can be tested/modified independently
2. **Conceptually sound logic** - regime compatibility matrix, profile scoring, rotation allocation
3. **Production-ready data integration** - can handle Polygon's full options data
4. **Explicit walk-forward intent** - designed for proper backtesting (though implementation has bugs)
5. **Scalable design** - easy to add profiles, change regimes, modify strategies

**The problems are NOT architectural - they are implementation bugs in:**
- Greeks calculation (not implemented)
- P&L sign convention (wrong)
- Execution cost modeling (oversimplified)
- Walk-forward implementation (has bugs)

**This is a REPAIR situation, not a REDESIGN situation.**

A focused 16-21 hour effort to fix the identified bugs will unlock a properly functioning backtest infrastructure that can support serious research and trading.

---

**Report Generated:** November 13, 2025
**Auditor:** Quantitative Architecture Specialist
**Classification:** INTERNAL DESIGN REVIEW
