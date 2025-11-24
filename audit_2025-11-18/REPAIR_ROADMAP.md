# Repair Roadmap - Infrastructure Fixes

**Created:** 2025-11-18
**Status:** 🔴 In Progress
**Target Completion:** 2 weeks

---

## Phase 1: Critical Foundation Fixes (Days 1-3)

### Day 1: Regime Classifier
- [ ] **BUG-CRIT-001:** Fix `_compute_walk_forward_percentile` look-ahead bias
  - File: `src/regimes/signals.py:99-130`
  - Branch: `fix/regime-lookahead-bias`
  - Test: `tests/test_regime_signals.py`
  - Validate: Re-run regime detection, verify results change

### Day 2: Profile Detectors
- [ ] **BUG-CRIT-002:** Fix Profile 3, 4, 6 look-ahead bias
  - File: `src/profiles/detectors.py`
  - Branch: `fix/profile-lookahead-bias`
  - Test: `tests/test_profile_detectors.py`
  - Validate: Profile 4 OOS performance becomes realistic

- [ ] **BUG-CRIT-002b:** Add NaN handling to all 6 profiles
  - Add `fillna(0)` to all return statements
  - Test: Run with corrupt data, verify no crashes

### Day 3: Data Pipeline
- [ ] **BUG-CRIT-003:** Fix data pipeline bugs
  - Hardcoded 2% spreads → ExecutionModel
  - Add corporate action adjustments
  - Improve garbage filtering
  - Fix VIX loading with fallback
  - Test: `tests/test_data_pipeline.py`

---

## Phase 2: High Priority Fixes (Days 4-5)

### Day 4: Position Tracking
- [ ] **BUG-CRIT-004:** Fix memory leak in Greeks history
  - File: `src/trading/trade.py:206-216`
  - Add history size limit (MAX_GREEKS_HISTORY = 1000)
  - Test: Run 5-year backtest, verify memory stable

- [ ] **BUG-HIGH-001:** Fix state transition race conditions
  - Add state validation in close() method
  - Test: Multiple close() calls don't crash

### Day 5: Validation & Re-test
- [ ] Re-run full backtest with all fixes
- [ ] Verify results are significantly different (proves fixes worked)
- [ ] Statistical validation: significance, walk-forward
- [ ] Check for remaining overfitting symptoms

---

## Phase 3: Complete Audit (Days 6-10)

### Day 6-7: Re-run Failed Agents
- [ ] Re-run Agent #4: Trade Simulator Execution
- [ ] Re-run Agent #5: P&L Accounting
- [ ] Re-run Agent #6: Delta Hedging
- [ ] Re-run Agent #8: Risk Management
- [ ] Re-run Agent #9: Metrics Calculation
- [ ] Re-run Agent #10: Integration Test

### Day 8-9: Fix Additional Issues
- [ ] Address any new bugs found by agents #4-10
- [ ] Prioritize and fix remaining HIGH/MEDIUM issues
- [ ] Add comprehensive unit test coverage

### Day 10: Final Validation
- [ ] Full end-to-end integration test
- [ ] Multi-year backtest validation
- [ ] Statistical significance tests
- [ ] Out-of-sample validation
- [ ] Document all fixes and validation results

---

## Quality Gates

Each fix must pass:
1. ✅ Unit tests pass
2. ✅ Backtest results change (proves fix worked)
3. ✅ No new bugs introduced
4. ✅ Code review complete
5. ✅ Documentation updated

---

## Branch Strategy

```
main
├── fix/regime-lookahead-bias (Day 1)
├── fix/profile-lookahead-bias (Day 2)
├── fix/data-pipeline-bugs (Day 3)
├── fix/position-tracking-memory (Day 4)
└── fix/final-integration (Day 10)
```

Merge strategy:
- Each fix in separate branch
- Test independently before merging
- Merge to `dev` branch first
- Final merge to `main` after Phase 3 complete

---

## Success Criteria

Before declaring "READY FOR DEPLOYMENT":
- [ ] ALL CRITICAL bugs fixed and validated
- [ ] ALL agents (#1-10) run successfully
- [ ] Full backtest produces statistically significant results
- [ ] Walk-forward test shows realistic degradation
- [ ] Out-of-sample performance is reasonable
- [ ] System runs 5+ year backtest without crashes
- [ ] Code coverage >80% for critical paths
- [ ] Independent review complete

---

## Risk Assessment

**Current Risk Level:** 🔴 EXTREME - Do not deploy capital

**After Phase 1:** 🟡 HIGH - Foundation fixed but incomplete
**After Phase 2:** 🟡 MODERATE - Core issues resolved
**After Phase 3:** 🟢 LOW - Ready for paper trading

**Timeline to Paper Trading:** 10-14 days
**Timeline to Live Capital:** +30 days paper trading validation
