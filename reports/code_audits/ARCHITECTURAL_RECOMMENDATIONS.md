# ROTATION ENGINE - ARCHITECTURAL RECOMMENDATIONS

**Date:** November 13, 2025
**From:** Quantitative Code Auditor
**To:** Development Team

---

## EXECUTIVE SUMMARY FOR DECISION-MAKERS

**Question:** Should we keep this architecture or start over?

**Answer:** **KEEP IT. Fix the bugs.**

**Rationale:**
- The architecture is well-designed (A- grade)
- The bugs are in implementation, not design
- Starting over costs 4-8 weeks
- Fixing bugs costs 16-21 hours
- The existing design makes fixes straightforward

**Cost Comparison:**
| Option | Time | Risk | Outcome |
|--------|------|------|---------|
| **Keep & Fix** | 16-21 hrs | Low | Working production system |
| **Redesign** | 4-8 weeks | High | Might have new bugs |
| **Use as-is** | 0 hrs | CRITICAL | Invalid results |

---

## PART 1: STRENGTHS TO PRESERVE

### 1. Module Architecture (Keep 100%)

**Current Design:** 5-layer pipeline with clean separation

```
Data Layer → Regime Layer → Profile Layer → Trading Layer → Analysis Layer
```

**Why Keep It:**
- Easy to test each layer independently
- Easy to swap implementations (e.g., IV proxy → real IV)
- No circular dependencies
- Production teams understand it immediately

**What NOT to Change:**
- Don't merge modules
- Don't move code between layers
- Don't add cross-layer dependencies

---

### 2. Regime Compatibility Matrix (Keep 100%)

**Current Approach:** Explicit weighting of profiles in each regime

```python
REGIME_COMPATIBILITY = {
    1: {'profile_1': 1.0, 'profile_2': 0.0, ...},  # Trend Up
    2: {'profile_1': 0.0, 'profile_2': 1.0, ...},  # Trend Down
    ...
}
```

**Why Keep It:**
- Transparent and auditable
- Can validate against theory
- Easy to update as research evolves
- Prevents bad allocations

**Enhancement:** Add documentation for each entry:
```python
{
    'profile_1': {
        'weight': 1.0,
        'rationale': 'LDG thrives in consistent uptrends due to gamma compounding',
        'research': 'See market_microstructure_paper_v2.pdf page 15'
    }
}
```

---

### 3. Trade Lifecycle (Keep 95%)

**Current Design:** Entry → Holding → Exit with explicit state tracking

**Strengths:**
- Multi-leg support built in
- Clear state transitions
- Auditable P&L
- Greeks tracking placeholder (good foresight)

**One Enhancement Needed:**
- Per-leg state tracking for diagonal spreads
- Change `is_open: bool` → `is_open: Dict[int, bool]`
- Enables selective rolling

**Estimated effort:** 4-6 hours, low risk

---

## PART 2: GAPS TO FILL

### Gap 1: Greeks Calculation (MUST IMPLEMENT)

**Current State:** Greeks fields exist but are never calculated

**What's Needed:** Black-Scholes implementation

**Recommended Approach:**

```python
# New file: src/pricing/black_scholes.py

class BlackScholesGreeks:
    """Calculate option Greeks using Black-Scholes model."""

    @staticmethod
    def call_delta(S, K, T, r, sigma):
        """Call option delta (0 to 1)"""
        ...

    @staticmethod
    def put_delta(S, K, T, r, sigma):
        """Put option delta (-1 to 0)"""
        ...

    @staticmethod
    def gamma(S, K, T, r, sigma):
        """Gamma for both call and put (same)"""
        ...

    @staticmethod
    def theta(S, K, T, r, sigma, option_type):
        """Theta per day"""
        ...

    @staticmethod
    def vega(S, K, T, r, sigma):
        """Vega per 1% vol move"""
        ...
```

**Integration Point:** `src/trading/simulator.py` when marking to market

**Effort:** 4-6 hours
**Priority:** CRITICAL (blocks risk management)

---

### Gap 2: Real IV Integration (SHOULD IMPLEMENT)

**Current State:** Using `RV × 1.2` as IV proxy

**What's Needed:** Extract IV from Polygon options data

**Recommended Approach:**

```python
# In src/profiles/features.py, replace:
df['IV7'] = df['RV5'] * 1.2

# With:
df['IV7'] = compute_atm_iv_from_options(options_chain, dte=7)

def compute_atm_iv_from_options(options_chain, dte=7):
    """Extract IV from ATM options for given DTE."""
    # Filter options with specified DTE
    # Find ATM calls and puts
    # Extract implied_vol field from Polygon data
    # Average call IV and put IV
    return iv
```

**Data Available:** Polygon API includes `implied_vol` field per option

**Integration Point:** `src/data/loaders.py` → `DataSpine` class

**Effort:** 6-8 hours (mainly data wrangling)
**Priority:** HIGH (improves profile accuracy)

---

### Gap 3: Execution Cost Calibration (MUST IMPROVE)

**Current State:** Simplified spread model, underestimates 30-50%

**Issues Found:**
- Short-dated spreads too tight (BUG-H01)
- OTM spreads too tight (BUG-H02)
- Missing commissions (BUG-C08)

**Recommended Approach:**

```python
# In src/trading/execution.py

class ExecutionCostsCalibrated:
    """Empirically calibrated execution costs."""

    # Commission per contract ($0.65-1.00 depending on broker)
    COMMISSION_PER_CONTRACT = 0.70

    # Exchange fees per contract
    EXCHANGE_FEE = 0.00182

    # FINRA regulatory fee
    FINRA_FEE = 0.000095

    def get_spread_pct(self, dte, moneyness, side):
        """Get bid-ask spread as % of mid price.

        Empirically calibrated using Polygon data:
        - For DTE < 7: Add 30% to spread width
        - For abs(log_moneyness) > 0.05: Add 20% to spread width
        """
        base_spread = self.spread_for_dte_moneyness[dte][moneyness]
        # Apply empirical adjustments...
        return adjusted_spread
```

**Data Source for Calibration:** Polygon's bid-ask quotes on sample dates

**Effort:** 3-4 hours (empirical analysis + coding)
**Priority:** HIGH (affects all P&L)

---

### Gap 4: Per-Leg Rolling (SHOULD IMPROVE)

**Current State:** Position is all-or-nothing (single `is_open` flag)

**Limitation:** Can't do diagonal spreads properly (roll short leg while holding long leg)

**Recommended Change:**

```python
# Before (current):
@dataclass
class Trade:
    is_open: bool = True

# After (improved):
@dataclass
class Trade:
    is_open: Dict[int, bool] = field(default_factory=dict)  # Per-leg state
    exit_dates: Dict[int, datetime] = field(default_factory=dict)
    exit_prices: Dict[int, float] = field(default_factory=dict)
```

**Impact:** Enables Profile 3 (charm + diagonal spreads) to work properly

**Effort:** 4-6 hours
**Priority:** MEDIUM (nice-to-have, Profile 3 works with all-or-nothing)

---

## PART 3: BUG FIX ROADMAP

### Phase 1: CRITICAL BUGS (16-20 hours)
These **must** be fixed before any backtest is valid:

| Bug | File | Time | Fix |
|-----|------|------|-----|
| C01 | trade.py | 2 hrs | Fix P&L sign convention |
| C02 | trade.py | 4 hrs | Implement Black-Scholes |
| C03 | simulator.py | 1 hr | Replace hardcoded hedge cost |
| C04 | signals.py | 0.25 hrs | Delete broken percentile method |
| C05 | signals.py | (with C04) | Removed by fixing C04 |
| C06 | features.py | 3 hrs | Standardize slope calculation |
| C07 | simulator.py | 1.5 hrs | Track per-leg DTE |
| C08 | execution.py | 1 hr | Add commissions |

**Total Phase 1:** 16-20 hours

### Phase 2: HIGH PRIORITY (6-8 hours)
Must complete before live trading:

| Bug | File | Time | Fix |
|-----|------|------|-----|
| H01 | execution.py | 3 hrs | Calibrate short-dated spreads |
| H02 | execution.py | 2 hrs | Calibrate OTM spreads |
| H03 | trade.py, simulator.py | 4-6 hrs | Per-leg rolling |

**Total Phase 2:** 6-8 hours

### Phase 3: MEDIUM (2-3 hours)
Housekeeping and optimization:

| Bug | File | Time | Fix |
|-----|------|------|-----|
| M01 | rotation.py | 0.5 hrs | Re-normalize after VIX scaling |
| M02 | features.py | 1 hr | Normalize slope by price |
| M03 | signals.py | 1 hr | Consolidate percentile code |

**Total Phase 3:** 2-3 hours

---

## PART 4: DATA QUALITY RECOMMENDATIONS

### Recommendation 1: Add Data Validation Layer

**Current State:** Data assumed correct

**Recommended Addition:** Pre-backtest validation

```python
# New file: src/data/validator.py

class DataValidator:
    """Validate data quality before backtesting."""

    @staticmethod
    def validate_spy_ohlcv(df):
        """Check OHLCV data quality."""
        assert df['high'] >= df['low'], "High < Low invalid"
        assert df['open'] > 0, "Prices must be positive"
        # ... more checks

    @staticmethod
    def validate_features(df):
        """Check computed features are in valid ranges."""
        assert (df['RV20'] >= 0) & (df['RV20'] <= 1.0), "RV20 out of range"
        assert (df['IV_rank'] >= 0) & (df['IV_rank'] <= 1.0), "IV rank out of range"
        # ... more checks

    @staticmethod
    def validate_options_chain(df):
        """Check options data quality."""
        assert df['bid'] <= df['mid'] <= df['ask'], "Bid-mid-ask order wrong"
        assert df['bid'] > 0, "Prices must be positive"
        # ... more checks
```

**Effort:** 2-3 hours
**Value:** Catches data issues early

---

### Recommendation 2: Add Data Quality Reporting

**Current State:** No visibility into data issues

**Recommended Addition:** Pre-backtest report

```python
# In engine.py, after loading data:

report = {
    'dates_covered': f"{df['date'].min()} to {df['date'].max()}",
    'trading_days': len(df),
    'weekends_removed': ...
    'data_gaps': check_for_gaps(df),
    'features_computed': [col for col in df.columns if col in expected],
    'features_missing': [col for col in expected if col not in df.columns],
    'options_coverage': options_data_available_dates,
    'data_quality_score': 0.95,  # Percentage of data passing all checks
}
print(report)
```

**Effort:** 1-2 hours
**Value:** Transparency into backtest inputs

---

## PART 5: WALK-FORWARD COMPLIANCE

### Current State Assessment

**Good:**
- Architecture designed for walk-forward
- Key functions use `.rolling()` (walk-forward by default)
- No `.shift(-1)` or obvious future indexing

**Issues:**
- Duplicate implementations (BUG-C04, BUG-C05)
- Off-by-one error in one implementation
- Inconsistent approaches across modules

### Recommended Fix

**Consolidate percentile calculations:**

```python
# Create single canonical function in src/utils/walk_forward.py

def compute_walk_forward_percentile(series, window=60):
    """
    Compute percentile rank walk-forward (no look-ahead).

    For each row t:
        Percentile = rank of value[t] in window [t-window:t]

    CRITICAL: Does NOT include row t in window.
    """
    result = pd.Series(np.nan, index=series.index)

    for i in range(window, len(series)):
        past_window = series.iloc[i-window:i]
        current_value = series.iloc[i]
        percentile = (past_window < current_value).sum() / len(past_window)
        result.iloc[i] = percentile

    return result

# Use everywhere:
# regimes/signals.py: iv_rank = compute_walk_forward_percentile(...)
# profiles/features.py: iv_rank = compute_walk_forward_percentile(...)
```

**Benefit:** Single canonical implementation, zero confusion

---

## PART 6: TESTING IMPROVEMENTS

### Recommended Unit Tests

```python
# tests/test_architecture.py

class TestWalkForwardCompliance:
    """Ensure no look-ahead bias."""

    def test_no_shift_minus_one(self):
        """Grep codebase for '.shift(-1)' - should find nothing."""
        ...

    def test_features_not_use_future_data(self):
        """Verify features only use data up to current row."""
        ...

    def test_percentile_not_include_current_row(self):
        """Verify percentile excludes current row."""
        ...

class TestDataIntegrity:
    """Ensure data is consistent across layers."""

    def test_no_nan_propagation(self):
        """Check NaNs don't cascade through calculations."""
        ...

    def test_features_match_raw_data(self):
        """Spot-check features against manual calculations."""
        ...
```

**Effort:** 4-6 hours to write and integrate
**Value:** Prevents regression of fixed bugs

---

## PART 7: DOCUMENTATION IMPROVEMENTS

### Current State
- Code has docstrings (good)
- No architectural documentation (bad)
- No explanation of design choices (bad)

### Recommended Additions

**File: ARCHITECTURE.md (new)**
```markdown
# Rotation Engine Architecture

## Overview
[5-layer pipeline description]

## Module Responsibilities
- Layer 1: Data loading and feature computation
- Layer 2: Regime detection
- ...

## Key Design Decisions
1. Why walk-forward? [explanation]
2. Why compatibility matrix? [explanation]
3. Why multi-profile rotation? [explanation]

## Data Flow Diagram
[ASCII diagram]

## Integration Points
[How to add new profiles, regimes, etc.]
```

**File: DESIGN_DECISIONS.md (new)**
```markdown
# Design Decisions Log

## Decision 1: 5-Layer Architecture
**Date:** [when]
**Rationale:** Clean separation of concerns, testability
**Alternatives Considered:** Monolithic, MVC, other
**Status:** ACTIVE

## Decision 2: Regime Compatibility Matrix
**Date:** [when]
**Rationale:** Transparent, auditable, theory-grounded
**Alternatives Considered:** ML classifier, heuristics
**Status:** ACTIVE
```

**Effort:** 2-3 hours
**Value:** Onboarding new team members, maintaining institutional knowledge

---

## PART 8: DEPLOYMENT CHECKLIST

### Before Running First Proper Backtest

- [ ] Phase 1 critical bugs fixed (8 bugs)
- [ ] Code review of fixes
- [ ] Unit tests pass
- [ ] Walk-forward compliance verified
- [ ] Data validation passes
- [ ] Test backtest on 1 week of data
- [ ] Spot-check P&L matches manual calculations
- [ ] Review allocation output (does it make sense?)
- [ ] Check for NaN propagation

### Before Live Trading

- [ ] Phase 2 high-priority bugs fixed (3 bugs)
- [ ] Execution costs empirically calibrated
- [ ] Greeks Greeks validation
- [ ] Full backtest on 5 years data
- [ ] Red team the results
- [ ] Risk framework documented
- [ ] Live trading simulation for 1 week
- [ ] Capital allocation decided
- [ ] Position sizing rules finalized

---

## PART 9: FUTURE-PROOFING

### Architecture Already Supports

✅ Adding new profiles (just add detector + module)
✅ Changing regime definitions (update classifier)
✅ New data sources (swap loader)
✅ New execution models (swap execution.py)
✅ Walk-forward → online learning (just need different engine)

### Architecture Should Support (Consider Adding)

1. **Historical regime backtests** - run backtest assuming perfect regime forecast
2. **Parameter sensitivity analysis** - sweep DTE targets, thresholds, weights
3. **Stress testing** - replay extreme market events
4. **Attribution decomposition** - how much P&L from which decisions?
5. **Live trading integration** - real capital deployment

---

## SUMMARY TABLE

| Item | Current | Recommendation | Priority |
|------|---------|-----------------|----------|
| **Architecture** | A- grade | Keep 100% | N/A |
| **Module Separation** | Excellent | No changes | N/A |
| **Walk-Forward Design** | Good concept, buggy | Fix bugs | CRITICAL |
| **Greeks** | Missing | Implement | CRITICAL |
| **IV Integration** | Proxy-based | Use real IV | HIGH |
| **Execution Costs** | Oversimplified | Calibrate | HIGH |
| **Per-Leg Rolling** | All-or-nothing | Add flexibility | MEDIUM |
| **Testing** | Minimal | Add unit tests | MEDIUM |
| **Documentation** | Code only | Add architecture docs | LOW |

---

## FINAL RECOMMENDATION

**KEEP THE ARCHITECTURE AND FIX THE BUGS.**

This is a well-designed system with implementation problems, not a fundamentally broken design. A focused 16-21 hour effort will unlock a properly functioning backtest infrastructure.

**Do not:**
- Start over
- Rewrite modules
- Change the pipeline
- Merge layers

**Do:**
- Fix the 14 identified bugs
- Integrate real IV
- Implement Greeks
- Calibrate execution costs
- Add tests and documentation

**Estimated Timeline to Production:**
- Phase 1 (critical): 16-20 hours
- Phase 2 (high): 6-8 hours
- Phase 3 (medium): 2-3 hours
- Review & validation: 4-6 hours
- **Total: 28-37 hours focused work = 3-4 focused days**

Then you have a production-ready quantitative trading system.

---

**Prepared by:** Quantitative Code Auditor
**Date:** November 13, 2025
**Classification:** INTERNAL ARCHITECTURAL REVIEW
