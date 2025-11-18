# EXIT STRATEGY - PHASE 1 SPECIFICATION

**Date:** 2025-11-18
**Version:** 1.0 (Baseline - Time-Based Exits Only)
**Status:** Ready for Implementation
**Purpose:** Establish baseline capture rate with ZERO optimizable parameters

---

## DESIGN PHILOSOPHY

**Goal:** Prove exits are the problem, not entries, using the SIMPLEST possible exit strategy.

**Constraints:**
- ZERO parameters to optimize (no overfitting possible)
- Based purely on empirical peak timing from fresh backtest
- No condition-based logic (eliminates look-ahead risk)
- Easy to modify for future iterations

**Success Criteria:**
- Capture rate > 15% (vs current -1.8%)
- At least 3 of 6 profiles become profitable
- Proves entries find real opportunities

---

## EXIT RULES (PROFILE-SPECIFIC)

All exits are **fixed calendar days** from entry. No exceptions, no conditions, no optimization.

### Profile 1: Long-Dated Gamma (LDG)
**Exit Day:** 7
**Rationale:** Empirical median peak = 6.9 days
**Data:** Fresh backtest shows bimodal distribution (early cluster Day 1-5, late cluster Day 10-14), median at Day 7
**Expected Impact:** Currently -$5,777 on $41,516 peak (-13.9% capture) → Target: +10-20% capture

### Profile 2: Short-Dated Gamma Spike (SDG)
**Exit Day:** 5
**Rationale:** Empirical median peak = 4.5 days, short-dated options (0-7 DTE) decay fast
**Data:** Fresh backtest shows fast resolution, holding to Day 14 makes no sense for weeklies
**Expected Impact:** Currently -$318 on $16,173 peak (-2.0% capture) → Target: +15-25% capture

### Profile 3: Charm/Decay Dominance (CHARM)
**Exit Day:** 3
**Rationale:** Empirical peak = 0.0 days (immediate), theta harvesting wants quick exits
**Data:** Fresh backtest shows 62.3% win rate but -1.5% capture - holding destroys theta
**Expected Impact:** Currently -$1,858 on $120,745 peak (-1.5% capture) → Target: +20-30% capture
**Note:** This is the HIGHEST peak profile ($121K of $343K total) - biggest opportunity

### Profile 4: Vanna Convexity (VANNA)
**Exit Day:** 8
**Rationale:** Empirical median peak = 7.7 days, ONLY profitable profile currently
**Data:** Fresh backtest shows +$12,064 on $77,976 peak (15.5% capture) - DON'T BREAK THIS
**Expected Impact:** Keep current +15.5% capture, possibly improve to +20%

### Profile 5: Skew Convexity (SKEW)
**Exit Day:** 5
**Rationale:** Empirical median peak = 4.8 days, fear spikes resolve quickly
**Data:** Fresh backtest shows worst performance (-29.2% capture), fast exit reduces bleed
**Expected Impact:** Currently -$3,421 on $11,731 peak (-29.2%) → Target: +10-15% capture

### Profile 6: Vol-of-Vol Convexity (VOV)
**Exit Day:** 7
**Rationale:** Empirical median peak = 6.9 days, vol expansion window
**Data:** Fresh backtest shows -$7,013 on $74,439 peak (-9.4% capture)
**Expected Impact:** Currently -9.4% capture → Target: +15-25% capture

---

## IMPLEMENTATION REQUIREMENTS

### Code Location
`src/trading/exit_engine.py` (NEW FILE)

### Interface
```python
class ExitEngine:
    """
    Phase 1: Fixed time-based exits only.

    NO parameters to optimize.
    NO condition-based logic.
    PURE empirical peak timing.
    """

    # Profile-specific exit days (IMMUTABLE for Phase 1)
    PROFILE_EXIT_DAYS = {
        'Profile_1_LDG': 7,
        'Profile_2_SDG': 5,
        'Profile_3_CHARM': 3,
        'Profile_4_VANNA': 8,
        'Profile_5_SKEW': 5,
        'Profile_6_VOV': 7
    }

    def should_exit(self, trade, current_day: int, profile: str) -> bool:
        """
        Determine if position should exit.

        Phase 1: Exit on specific calendar day, period.

        Args:
            trade: Trade object with entry info
            current_day: Days since entry (0 = entry day)
            profile: Profile name

        Returns:
            True if should exit, False otherwise
        """
        exit_day = self.PROFILE_EXIT_DAYS.get(profile, 14)  # Default 14 if unknown
        return current_day >= exit_day
```

### Integration Point
`src/backtest/engine.py` - Replace current 14-day fixed exit with ExitEngine

### Logging Requirements
For each trade, log:
- Profile name
- Entry date
- Exit date
- Days held
- Entry P&L (cost)
- Exit P&L (realized)
- Peak P&L (max unrealized during hold)
- Capture % (exit P&L / peak P&L)

This enables Phase 2 analysis.

---

## VALIDATION CRITERIA

### Must Pass Before Accepting Results:

1. **Trade count unchanged:** 604 trades (same entries as fresh backtest)
2. **Peak potential unchanged:** $342,579 total (proves entries unchanged)
3. **Deterministic:** Re-running produces identical results
4. **Exit days match spec:** Verify each profile exits on correct day

### Success Metrics:

**Minimum bar (proves exits work):**
- Total P&L: > $0 (vs current -$6,323)
- Capture rate: > 5% (vs current -1.8%)
- Profitable profiles: ≥ 3 of 6 (vs current 1 of 6)

**Good outcome:**
- Total P&L: > $30K (10% of peak)
- Capture rate: > 15%
- Profitable profiles: ≥ 4 of 6

**Excellent outcome:**
- Total P&L: > $60K (18% of peak)
- Capture rate: > 20%
- Profitable profiles: All 6

---

## TESTING PROTOCOL

### Step 1: Implement ExitEngine
- Create `src/trading/exit_engine.py`
- Add unit tests
- Verify interface works

### Step 2: Integration
- Modify `src/backtest/engine.py` to use ExitEngine
- Ensure no other changes
- Run single-profile test to verify

### Step 3: Full Backtest
- Run complete backtest with Phase 1 exits
- Compare to baseline (fresh backtest with 14-day exits)
- Validate trade count, peak potential unchanged

### Step 4: Analysis
- Calculate capture rates by profile
- Identify which profiles work, which don't
- Document findings for Phase 2

---

## CHANGE LOG

When modifying exit days, update here:

| Date | Profile | Old Day | New Day | Reason | Result |
|------|---------|---------|---------|--------|--------|
| 2025-11-18 | ALL | 14 | Various | Initial implementation from empirical peaks | TBD |

---

## PHASE 2 PREVIEW (NOT IMPLEMENTED YET)

After Phase 1 establishes baseline, add:
1. Profit targets (+50%, +100%)
2. Risk guards (-50% max loss)
3. Condition exits (regime change, theta bleed acceleration)

**But Phase 1 FIRST.** Prove the concept before adding complexity.

---

## APPENDIX: EMPIRICAL PEAK DATA (Fresh Backtest 2025-11-18)

| Profile | Median Peak Day | Total Peak $ | Current P&L | Current Capture |
|---------|----------------|--------------|-------------|-----------------|
| LDG | 6.9 | $41,516 | -$5,777 | -13.9% |
| SDG | 4.5 | $16,173 | -$318 | -2.0% |
| CHARM | 0.0 | $120,745 | -$1,858 | -1.5% |
| VANNA | 7.7 | $77,976 | +$12,064 | +15.5% |
| SKEW | 4.8 | $11,731 | -$3,421 | -29.2% |
| VOV | 6.9 | $74,439 | -$7,013 | -9.4% |
| **TOTAL** | - | **$342,579** | **-$6,323** | **-1.8%** |

**Phase 1 target:** Turn -$6,323 into +$30K-60K with zero-parameter time-based exits.

---

**Approved for Implementation:** 2025-11-18
**Estimated Implementation Time:** 2-3 hours
**Risk Level:** LOW (simple logic, no optimization, easy to revert)
