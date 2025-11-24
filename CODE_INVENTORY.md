# CODE INVENTORY - Rotation Engine
**Generated:** 2025-11-20
**Purpose:** Comprehensive audit of all Python scripts for cleanup

---

## EXECUTIVE SUMMARY

**Total Python Files:** 116
- **Core Framework (src/):** 37 files
- **Analysis Scripts (scripts/):** 38 files
- **Test Files (tests/):** 39 files
- **Exit Strategies (exits/):** 2 files

**Key Findings:**
1. **Multiple versions exist** (FIXED, _v2, _new suffixes)
2. **Old architecture** (engine.py) vs **New architecture** (engine_new.py) - NEW NOT IN USE
3. **Train/Validation/Test split** implemented but full period also exists
4. **Exit strategy research** in progress (detector_exit_v0, overlay_decay_intraday)

---

## CATEGORY 1: CORE FRAMEWORK (src/) - PRODUCTION CODE

### Status: ✅ READY (Validated via bug fixes)

#### src/backtest/
- ✅ **engine.py** - Main rotation backtest orchestrator (IN USE)
- ⚠️ **engine_new.py** - Multi-position portfolio architecture (NOT IN USE - candidate for deprecation)
- ✅ **portfolio.py** - Portfolio aggregation (IN USE)
- ⚠️ **portfolio_new.py** - Multi-position portfolio (NOT IN USE - paired with engine_new)
- ⚠️ **position.py** - Position tracking (NOT IN USE - for engine_new)
- ✅ **rotation.py** - Capital allocation logic (IN USE)
- ⚠️ **simple_backtest.py** - Simplified backtest (LEGACY? - check usage)

**Recommendation:**
- Archive engine_new.py, portfolio_new.py, position.py to archive/ (not currently used)
- Verify simple_backtest.py usage or deprecate

#### src/data/
- ✅ **loaders.py** - SPY data loading (IN USE)
- ✅ **features.py** - Feature engineering (IN USE)
- ✅ **polygon_options.py** - Options data loading (IN USE)
- ✅ **events.py** - Event calendar (IN USE)

**Status:** All PRODUCTION READY

#### src/pricing/
- ✅ **greeks.py** - Greeks calculations (IN USE, recently fixed bugs)

**Status:** PRODUCTION READY

#### src/profiles/
- ✅ **detectors.py** - Profile scoring functions (IN USE, core logic)
- ✅ **features.py** - Profile-specific features (IN USE)
- ✅ **validator.py** - Profile validation (IN USE)

**Status:** PRODUCTION READY

#### src/regimes/
- ✅ **classifier.py** - Regime detection (IN USE)
- ✅ **signals.py** - Regime signals (IN USE)
- ✅ **validator.py** - Regime validation (IN USE)

**Status:** PRODUCTION READY

#### src/trading/
- ✅ **execution.py** - Execution model with transaction costs (IN USE, recently fixed)
- ✅ **exit_engine.py** - Exit management (IN USE)
- ✅ **simulator.py** - Trade simulation (IN USE, core component)
- ✅ **trade.py** - Trade and TradeLeg classes (IN USE)
- ✅ **utils.py** - Trading utilities (IN USE)

**Status:** PRODUCTION READY

#### src/trading/profiles/
- ✅ **profile_1.py through profile_6.py** - Individual profile implementations (ALL IN USE)

**Status:** PRODUCTION READY

#### src/analysis/
- ✅ **metrics.py** - Performance metrics (IN USE)
- ✅ **trade_tracker.py** - Trade lifecycle tracking (IN USE)
- ✅ **visualization.py** - Plotting utilities (IN USE)

**Status:** PRODUCTION READY

---

## CATEGORY 2: ANALYSIS SCRIPTS (scripts/) - MIXED STATUS

### ✅ PRODUCTION - Train/Validation/Test Methodology
- ✅ **backtest_train.py** - Train period backtest (2020-2021)
- ✅ **backtest_validation.py** - Validation period backtest (2022-2023)
- ✅ **backtest_test.py** - Test period backtest (2024)
- ✅ **backtest_full_period.py** - Full period backtest (2020-2024)
- ✅ **derive_params_from_train.py** - Parameter derivation from train period

**Status:** Core methodology scripts, KEEP

### ⚠️ DUPLICATES - Need Resolution
- ⚠️ **exit_sweep_pnl_based.py** - Original version
- ✅ **exit_sweep_pnl_based_FIXED.py** - Bug-fixed version (USE THIS)

**Recommendation:** Delete exit_sweep_pnl_based.py (superseded by FIXED version)

- ⚠️ **sdg_multidimensional_separation.py** - Original
- ✅ **sdg_multidimensional_separation_FIXED.py** - Fixed version (USE THIS)

**Recommendation:** Delete sdg_multidimensional_separation.py (superseded)

- ⚠️ **test_bugfixes.py** - Original
- ✅ **test_bugfixes_v2.py** - Version 2 (USE THIS)

**Recommendation:** Delete test_bugfixes.py (superseded by v2)

### ✅ ANALYSIS & RESEARCH - Active
- ✅ **analyze_entry_conditions.py** - Entry condition analysis
- ✅ **analyze_time_to_peak.py** - Peak timing analysis
- ✅ **analyze_detector_scores_at_lifecycle.py** - Detector performance
- ✅ **analyze_phase1_exits_from_existing_data.py** - Exit analysis
- ✅ **structural_entry_analysis.py** - Entry filter research
- ✅ **compare_day7_vs_overlay.py** - Exit strategy comparison
- ✅ **compare_sdg_filter_impact.py** - Filter impact analysis

**Status:** Active research scripts, KEEP

### ✅ VALIDATION & AUDITING
- ✅ **PRE_BACKTEST_AUDIT.py** - Pre-backtest audit agent
- ✅ **SIMPLE_PRE_AUDIT.py** - Simple audit check
- ✅ **red_team_audit.py** - Red team audit
- ✅ **overfitting_red_team.py** - Overfitting detection
- ✅ **overfitting_red_team_fast.py** - Fast overfitting check
- ✅ **statistical_validation.py** - Statistical validation

**Status:** Quality gate scripts, KEEP ALL

### ⚠️ UTILITIES - Check Usage
- ⚠️ **example_usage.py** - Example code (check if outdated)
- ⚠️ **demo_day1.py** - Demo script (check relevance)
- ⚠️ **create_plots.py** - Plotting script (check usage)
- ⚠️ **debug_allocations.py** - Debug utility (one-off?)
- ⚠️ **debug_dates.py** - Debug utility (one-off?)

**Recommendation:** Review for deprecation or move to archive/

### ✅ DATA PROCESSING
- ✅ **build_spy_minute_parquet.py** - SPY minute data builder
- ✅ **download_spy_stock_minutes.py** - SPY data downloader
- ✅ **rebuild_intraday_jan2023.py** - Rebuild specific period

**Status:** Data pipeline scripts, KEEP

### ✅ TOOLS
- ✅ **backtest_with_full_tracking.py** - Full tracking backtest
- ✅ **apply_exit_engine_v1.py** - Exit engine application
- ✅ **evaluate_detector.py** - Detector evaluation
- ✅ **test_profile_specific_exits.py** - Profile exit testing
- ✅ **harm_aware_rule_search_7gates.py** - Rule search (7 gates)
- ✅ **harm_aware_structural_rule_search.py** - Structural rule search

**Status:** Active tools, KEEP

---

## CATEGORY 3: EXIT STRATEGIES (exits/) - EXPERIMENTAL

- 🧪 **detector_exit_v0.py** - Detector-based exit logic (EXPERIMENTAL)
- 🧪 **overlay_decay_intraday.py** - Intraday decay overlay (EXPERIMENTAL, uses daily bars)

**Status:** Research/experimental, based on SESSION_STATE.md overlay never triggered

**Recommendation:**
- Keep for research reference
- Document that overlay_decay_intraday requires minute bars to be useful

---

## CATEGORY 4: TESTS (tests/) - EXTENSIVE

### Status: Mostly LEGACY bug verification tests

**Bug Fix Verification Tests (Legacy):**
- ⚠️ **test_bug_fixes.py** - General bug fixes
- ⚠️ **test_infrastructure_fixes.py** - Infrastructure fixes
- ⚠️ **test_validation_agents_fixes.py** - Validation fixes
- ⚠️ **test_allocation_constraint_fix.py** - Allocation fix
- ⚠️ **test_date_normalization_fix.py** - Date normalization
- ⚠️ **test_iv_fix.py** - IV calculation fix
- ⚠️ **test_pnl_commission_fix.py** - P&L commission fix
- ⚠️ **test_pnl_fix.py** - P&L fix
- ⚠️ **test_percentile_fix.py** - Percentile fix
- ⚠️ **test_strike_selection_fix.py** - Strike selection fix
- ⚠️ **test_timing_and_greeks_fixes.py** - Timing/Greeks fixes
- ⚠️ **BUG_VERIFICATION.py** - Bug verification
- ⚠️ **PNL_BUG_DEMO.py** - P&L bug demo
- ⚠️ **verify_bug_fixes.py** - Verification script
- ⚠️ **verify_fix.py** - Fix verification

**Recommendation:** Archive most bug fix tests after confirming fixes are stable. Keep core tests only.

**Component Tests (Keep):**
- ✅ **test_data_spine.py** - Data spine tests
- ✅ **test_greeks.py** - Greeks calculation tests
- ✅ **test_profiles.py** - Profile tests
- ✅ **test_regimes.py** - Regime tests
- ✅ **test_rotation_engine.py** - Engine tests
- ✅ **test_simulator_data_guards.py** - Simulator guards
- ✅ **test_walk_forward_compliance.py** - Walk-forward tests

**Integration Tests (Keep):**
- ✅ **test_integration_phase3.py** - Phase 3 integration
- ✅ **test_execution_model_integration.py** - Execution integration
- ✅ **test_greeks_integration.py** - Greeks integration
- ✅ **test_simulator_polygon_integration.py** - Polygon integration

**Analysis Tests (Review):**
- ⚠️ **analyze_percentile_impact.py** - Analysis (not a test?)

---

## CLEANUP RECOMMENDATIONS

### IMMEDIATE ACTIONS

#### 1. Delete Superseded Versions
```bash
# Delete original versions that have been FIXED
rm scripts/exit_sweep_pnl_based.py
rm scripts/sdg_multidimensional_separation.py
rm scripts/test_bugfixes.py
```

#### 2. Archive Unused Framework Components
```bash
# Create archive directory for unused architectures
mkdir -p archive/unused_architecture/

# Archive engine_new architecture (not currently in use)
mv src/backtest/engine_new.py archive/unused_architecture/
mv src/backtest/portfolio_new.py archive/unused_architecture/
mv src/backtest/position.py archive/unused_architecture/

# Git commit with clear message
git add -u
git commit -m "chore: Archive unused engine_new architecture - current system uses engine.py"
```

#### 3. Archive Legacy Bug Fix Tests
```bash
mkdir -p archive/legacy_tests/bug_fixes/

# Move legacy bug fix verification tests
mv tests/test_bug_fixes.py archive/legacy_tests/bug_fixes/
mv tests/test_infrastructure_fixes.py archive/legacy_tests/bug_fixes/
mv tests/test_validation_agents_fixes.py archive/legacy_tests/bug_fixes/
# ... (move all ⚠️ marked legacy tests)

git add -u
git commit -m "chore: Archive legacy bug fix tests - infrastructure now stable"
```

#### 4. Review and Archive One-Off Scripts
```bash
# Review these for usage, then archive if obsolete:
scripts/example_usage.py
scripts/demo_day1.py
scripts/debug_allocations.py
scripts/debug_dates.py
scripts/create_plots.py
```

### AFTER CLEANUP - EXPECTED STRUCTURE

```
rotation-engine/
├── src/                          # PRODUCTION FRAMEWORK (37 → 34 files)
│   ├── analysis/                 # ✅ Clean
│   ├── backtest/                 # ✅ Clean (5 → 4 files, removed simple_backtest if unused)
│   ├── data/                     # ✅ Clean
│   ├── pricing/                  # ✅ Clean
│   ├── profiles/                 # ✅ Clean
│   ├── regimes/                  # ✅ Clean
│   └── trading/                  # ✅ Clean
│
├── scripts/                      # ANALYSIS & TOOLS (38 → 33 files)
│   ├── backtest_*.py            # Train/Val/Test methodology (5 files)
│   ├── *_audit.py               # Validation scripts (6 files)
│   ├── analyze_*.py             # Analysis tools (7 files)
│   ├── *_FIXED.py               # Fixed versions (3 files)
│   └── [utilities]              # Data processing, tools (12 files)
│
├── exits/                        # EXPERIMENTAL (2 files)
│   ├── detector_exit_v0.py      # Research: detector-based exits
│   └── overlay_decay_intraday.py # Research: intraday decay (needs minute bars)
│
├── tests/                        # UNIT/INTEGRATION TESTS (39 → 15 files)
│   ├── test_*.py                # Core component tests (~10 files)
│   └── test_*_integration.py    # Integration tests (~5 files)
│
└── archive/                      # ARCHIVED CODE
    ├── unused_architecture/
    │   ├── engine_new.py
    │   ├── portfolio_new.py
    │   └── position.py
    ├── legacy_tests/
    │   └── bug_fixes/           # ~24 legacy test files
    └── deprecated_scripts/       # One-off scripts if obsolete
```

### BENEFITS AFTER CLEANUP

✅ **Reduced file count:** 116 → ~84 active files (-28%)
✅ **Clear separation:** Production vs Research vs Archive
✅ **No duplicate versions:** All FIXED versions canonical
✅ **Faster navigation:** Less clutter in active directories
✅ **Clear inventory:** This document + git history = full audit trail

---

## PRODUCTION-READY COMPONENTS (Verified)

Based on SESSION_STATE.md and recent bug fixing:

✅ **src/backtest/engine.py** - Main orchestrator (VALIDATED)
✅ **src/trading/simulator.py** - Trade execution (BUG-FIXED Nov 18-19)
✅ **src/trading/execution.py** - Transaction costs (AUDITED)
✅ **src/pricing/greeks.py** - Greeks calculations (FIXED)
✅ **src/profiles/detectors.py** - Profile scoring (VALIDATED)
✅ **src/regimes/classifier.py** - Regime detection (VALIDATED)
✅ **src/analysis/trade_tracker.py** - Trade tracking with 14-day observation (CURRENT)

**Current Best Exit Strategy:** Day 7 uniform exit (-$11,964 baseline)

---

## NEXT SESSION PRIORITIES

1. **Execute cleanup** using commands above
2. **Verify no broken imports** after archiving engine_new
3. **Run one full backtest** to confirm infrastructure intact
4. **Update START_HERE.md** with new structure
5. **Git commit** with clear messages for audit trail

---

**End of Inventory**
