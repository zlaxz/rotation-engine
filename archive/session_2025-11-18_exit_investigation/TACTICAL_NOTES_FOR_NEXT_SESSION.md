# TACTICAL NOTES - Immediate Next Session

**For:** Zach starting fresh session immediately after 2025-11-18 evening
**Created:** 2025-11-18 end of session

---

## BRANCH CONFUSION - RESOLVE FIRST

**Git shows:** `fix/sharpe-calculation-bug`
**I've been calling it:** `bugfix/critical-4-bugs`

**Action needed:**
```bash
git branch  # Check actual branch name
# Rename if needed for clarity
```

**Recommendation:** Create NEW clean branch for train/val/test work:
```bash
git checkout -b feature/train-validation-test-methodology
```

---

## BACKGROUND PROCESSES RUNNING

**I left ~30 DeepSeek audit agents running in background.**

**Clean them up:**
```bash
# List all background bash processes
/bashes

# Kill them all (optional, or let them finish)
# They were just audit agents, not critical
```

**Note:** Background bash 171923 was running the contaminated backtest script. Ignore its output.

---

## VALUABLE WORK DESPITE CONTAMINATION

### Bug Fixes That Are Probably Real:

**These fixes are likely valid (mathematical corrections):**
1. Sharpe/Sortino/Calmar P&L→returns conversion (metrics.py:110-180)
2. Greeks 100x multiplier (trade.py:339-342)
3. Theta daily→annual conversion (trade.py - theta bug)
4. Delta hedge direction (simulator.py:740-745)
5. DatetimeIndex→position index (metrics.py:330)

**These fixes might be overfit (data-driven):**
1. Execution model moneyness/VIX parameters (execution.py:100-114)
2. Profile entry conditions (detectors.py - various)
3. Any thresholds derived from data

**Verification needed on train period:**
- Run backtest on 2020-2021 ONLY
- See if bugs still appear
- Re-fix on train data if needed

### Code Architecture That's Sound:

**ExitEngine design** (`src/trading/exit_engine.py`):
- Class structure is good
- `should_exit()` interface is clean
- Just needs clean parameters from train period

**TradeTracker** (`src/analysis/trade_tracker.py`):
- 14-day tracking window approach is correct
- Daily path recording works
- Peak detection logic sound

---

## KEY INSIGHT: ENTRIES WORK, EXITS DESTROY VALUE

**From contaminated backtest (for context only):**
- Peak potential: $343K (entries finding real opportunities)
- Actual P&L: -$6K (14-day hold kills everything)
- Capture rate: -1.8% (exits are the problem)

**This suggests:**
- Entry signals are finding SOMETHING real
- Exit timing is critical (currently terrible)
- Phase 1 time-based exits might work

**BUT:** Must verify on train period, then validate out-of-sample.

---

## WHAT TO SALVAGE VS REBUILD

### Salvage (Keep and Verify):
- Infrastructure code (loaders, metrics, trade.py, simulator.py)
- ExitEngine class design
- TradeTracker architecture
- Bug fixes that are mathematical corrections

### Rebuild from Scratch:
- ALL parameter derivation (on train data)
- ALL backtest results
- Exit timing (re-calculate on train period)
- Disaster filter threshold (RV5 > 0.22 - was from full data)

### Delete Immediately:
- `scripts/analyze_phase1_exits_from_existing_data.py` (overfitting tool)
- `data/backtest_results/full_tracking_results.json` (contaminated)
- Any analysis based on full 2020-2024 dataset

---

## STATISTICAL VALIDATION REQUIREMENTS

**After Train Period (2020-2021):**
1. Use `statistical-validator` skill IMMEDIATELY
2. Bootstrap confidence intervals for all metrics
3. Permutation tests for entry signals
4. Document ALL derived parameters with train-period source

**After Validation Period (2022-2023):**
1. Use `overfitting-detector` skill to check degradation
2. Multiple testing correction: α = 0.05/22 = 0.0023 (22 bug fixes)
3. Regime analysis (2022 had bear market - good test)
4. Decision: Proceed to test or iterate?

**Critical Thresholds:**
- Validation Sharpe < 50% of train → Severe overfitting, abandon
- Validation flips sign → Strategy doesn't work, abandon
- Validation 60-80% of train → Expected, acceptable
- Validation > train → Lucky, suspicious

---

## FILE ORGANIZATION NOTES

**Root directory getting messy again (before cleanup):**
```
PROFILE_DETAILED_BREAKDOWN.md
QUICK_FIX_REFERENCE.md
ROUND4_AUDIT_SUMMARY.txt
STATISTICAL_AUDIT.json
... etc (many audit files)
```

**After session cleanup:**
- Move all audit files to `audit_2025-11-18/`
- Archive root-level analysis files
- Keep only: SESSION_STATE.md, 00_START_HERE_NEXT_SESSION.md

---

## AGENT UTILIZATION LESSON

**I underutilized expert agents this session.**

**Next time, call IMMEDIATELY:**
- `statistical-validator` - After ANY backtest completes
- `overfitting-detector` - When deriving ANY parameters
- `backtest-bias-auditor` - Before trusting ANY results

**Don't wait for user to point out overfitting - catch it myself.**

---

## TIMING ESTIMATES (For Planning)

**Train period implementation:**
- Create train/val/test scripts: 2 hours
- Run train period backtest: 30 minutes
- Statistical validation: 1 hour
- Total: ~3.5 hours

**Validation period:**
- Run validation backtest: 30 minutes
- Analysis and comparison: 1 hour
- Decision on iteration: 30 minutes
- Total: ~2 hours

**Test period (if reached):**
- Lock methodology: 30 minutes
- Run test backtest: 30 minutes
- Final analysis: 1 hour
- Total: ~2 hours

**Total for complete train/val/test cycle:** ~8 hours (if everything goes smoothly)

---

## WHAT WORKED THIS SESSION

1. **DeepSeek swarm audits** - Found real bugs efficiently ($0.30 for 30 agents)
2. **Iterative bug fixing** - 22 bugs across 4 rounds, systematic
3. **Comprehensive documentation** - Handoff doc is thorough
4. **Caught overfitting** - Before deploying capital (expensive lesson but valuable)

## WHAT FAILED THIS SESSION

1. **Methodology first** - Should have implemented train/val/test BEFORE fixing bugs
2. **Agent utilization** - Didn't use statistical experts until too late
3. **Implementation bug** - max_days parameter error showed I didn't understand peak vs exit
4. **Time waste** - 2 hours on contaminated exit testing

---

## QUICK WINS FOR NEXT SESSION

**If you want to see progress fast:**

1. **Use existing infrastructure code** - Don't rebuild from scratch
2. **Just add date filters** - Modify backtest script to take start_date/end_date params
3. **Run train period** - 2020-2021 only, derive new exit timing
4. **Quick validation test** - Apply to 2022-2023, see if it works

**This could give you train/validation results in ~2 hours** if infrastructure code is sound.

---

## THE ONE THING THAT MATTERS

**Research methodology > Everything else.**

Could have perfect code, zero bugs, beautiful architecture...

...but if I test on data used for development = worthless.

Train/validation/test splits are the FOUNDATION. Everything builds on top.

---

## FILES TO DELETE NEXT SESSION (Cleanup)

Root directory files created this session (contaminated analysis):
```
PROFILE_DETAILED_BREAKDOWN.md
QUICK_FIX_REFERENCE.md
ROUND4_AUDIT_SUMMARY.txt
ROUND4_BIAS_AUDIT_REPORT.md
STATISTICAL_AUDIT.json
STATISTICAL_AUDIT_DETAILED.md
TRANSACTION_COST_AUDIT_ROUND4.json
TRANSACTION_COST_REALITY_CHECK_ROUND4.md
PRE_BACKTEST_AUDIT_REPORT.md
validate_execution_costs.py
```

**Action:**
```bash
mkdir -p archive/session_2025-11-18_analysis
mv PROFILE_DETAILED_BREAKDOWN.md QUICK_FIX_REFERENCE.md ROUND4_*.* STATISTICAL_*.* TRANSACTION_*.* PRE_BACKTEST_*.* validate_execution_costs.py archive/session_2025-11-18_analysis/
```

---

**Priority 1 for next session:** Implement train/val/test scripts with enforced date boundaries.

**Don't get distracted** by fixing more bugs until methodology is proper.

**Good luck.**
