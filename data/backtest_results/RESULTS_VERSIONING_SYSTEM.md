# Results Versioning System

**Created:** 2025-11-16
**Purpose:** Prevent mixing old/new results, enable clear historical tracking

---

## Directory Structure

```
data/backtest_results/
├── runs/
│   ├── 20251115_1651_post_bug_fixes/        # Each run gets timestamped directory
│   │   ├── config.json                      # What was run (filters, params)
│   │   ├── results.json                     # Raw results
│   │   ├── summary.txt                      # Human-readable summary
│   │   └── METADATA.json                    # Timestamp, git hash, changes
│   ├── 20251115_2301_validation_analysis/   # Analysis runs also timestamped
│   │   ├── statistical_tests.json
│   │   ├── walk_forward_results.json
│   │   └── METADATA.json
│   └── ...
├── current -> runs/20251115_1651_post_bug_fixes/  # Symlink to current
└── archive/                                  # Old runs moved here
```

---

## File Naming Convention

**Backtest Runs:**
`YYYYMMDD_HHMM_description/`

Examples:
- `20251115_1651_post_bug_fixes/` (what we just ran)
- `20251120_0900_intelligent_exits/` (future run)
- `20251201_1400_regime_filtering/` (future run)

**Analysis Runs:**
`YYYYMMDD_HHMM_analysis_name/`

Examples:
- `20251115_2301_statistical_validation/`
- `20251116_0830_walk_forward_test/`

---

## METADATA.json Format

Every run directory MUST contain `METADATA.json`:

```json
{
  "run_id": "20251115_1651_post_bug_fixes",
  "timestamp": "2025-11-15T16:51:00",
  "run_type": "backtest",
  "description": "Post bug fixes: Profile 5 entry timing, Profile 6 IV inversion, RV5 disaster filter",
  "changes_since_last": [
    "Profile 5: Added slope_MA20 > 0.005 requirement",
    "Profile 6: Inverted IV_rank condition (0.5 - IV_rank)",
    "Profile 6: Added RV10 < RV20 compression detection",
    "Added: RV5 > 0.22 disaster filter"
  ],
  "git_hash": "abc123...",
  "parent_run": "20251114_2200_infrastructure_fixes",
  "data_period": "2020-01-02 to 2024-12-31",
  "total_trades": 604,
  "total_pnl": 1030.20,
  "peak_potential": 348896.60
}
```

---

## SESSION_STATE.md Integration

SESSION_STATE.md MUST track current run:

```markdown
## 🔵 CURRENT RESULTS (Updated Every Session)

**Current Run:** `20251115_1651_post_bug_fixes`
**Run Date:** 2025-11-15 4:51 PM
**Status:** Validated (statistical tests completed 2025-11-15 11:01 PM)

**Summary:**
- Total Trades: 604
- Total P&L: $1,030.20
- Peak Potential: $348,896.60
- Win Rate: 45.9%
- Capture Rate: 0.30%

**Validation Status:**
- Statistical Significance: NOT SIGNIFICANT (p=0.485)
- Walk-Forward: FAILED (sign flip between periods)
- Recommendation: DO NOT DEPLOY

**History:**
- Previous: `20251114_2200_infrastructure_fixes` (-$22,878 → current +$1,030)
- Change: +104% improvement from bug fixes
```

---

## Rules

### RULE 1: Never Overwrite Results
- Create new timestamped directory for each run
- NEVER overwrite `results.json` in place
- Archive old runs, don't delete

### RULE 2: Always Include METADATA
- Every run directory MUST have METADATA.json
- Must document: timestamp, changes, parent run
- Machine-readable and human-readable

### RULE 3: Symlink "current"
- `data/backtest_results/current` symlinks to latest
- Code reads from `current/results.json`
- Update symlink when new run completes

### RULE 4: Analysis References Runs
- Validation reports reference run_id
- Don't create orphaned analysis files
- Analysis goes in its own timestamped directory

### RULE 5: SESSION_STATE Tracks Current
- Must state current run_id at top
- Must state when it was run
- Must state validation status

---

## Migration Plan

1. Create directory structure
2. Move existing results to `20251115_1651_post_bug_fixes/`
3. Move validation reports to `20251115_2301_validation_analysis/`
4. Create METADATA.json for both
5. Create `current` symlink
6. Update SESSION_STATE.md with current run_id
7. Archive old mixed files

---

## Benefits

✅ Clear what's current vs historical
✅ No mixing old validation with new results
✅ Can compare runs over time
✅ Can rollback to previous runs
✅ Git-friendly (timestamped dirs don't conflict)
✅ Claude can read METADATA to understand context
✅ User can see history at a glance

---

**Status:** DESIGNED - Ready to implement
