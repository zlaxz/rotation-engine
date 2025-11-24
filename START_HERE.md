# ROTATION ENGINE - START HERE

**Last Updated:** 2025-11-18 Late Night
**Status:** Exit investigation complete - System loses money even with optimal exits

---

## QUICK START

**Current Session Summary:** `SESSION_SUMMARY_2025-11-18_LATE.md`

**Key Finding:**
- System loses $11,964 with optimal Day 7 exits (best case)
- Only VANNA and SDG profiles are profitable
- Entries validated as structurally sound (7-gate test)
- Exit optimization complete - Day 7 is best

---

## CURRENT RESULTS (2020-2024, 349 trades)

| Profile | Trades | Day 7 P&L | Day 10 P&L | Status |
|---------|--------|-----------|------------|--------|
| VANNA   | 48     | +$2,870   | **+$6,370** | ✓ Profitable |
| SDG     | 27     | **+$1,136** | -$595     | ✓ Profitable |
| SKEW    | 24     | +$2,153   | +$1,527   | ✓ Day 7 profitable |
| CHARM   | 75     | -$2,026   | -$3,438   | Marginal (Day 14: +$1,235) |
| LDG     | 44     | -$3,813   | -$5,254   | ✗ Losing |
| VOV     | 131    | -$12,282  | -$14,827  | ✗ Losing badly |
| **TOTAL** | **349** | **-$11,964** | **-$15,248** | **✗ Unprofitable** |

---

## DIRECTORY STRUCTURE

```
/Users/zstoc/rotation-engine/
├── START_HERE.md                          # ← You are here
├── SESSION_SUMMARY_2025-11-18_LATE.md     # ← Read this for session details
├── SESSION_STATE.md                       # ← Previous session state
│
├── src/                                   # Source code
│   ├── trading/exit_engine_v1.py         # Exit engine (detector-based, experimental)
│   ├── profiles/detectors.py             # Entry detectors (validated)
│   └── ...
│
├── scripts/                               # Analysis scripts (current)
│   ├── analyze_time_to_peak.py           # Peak timing analysis
│   ├── test_profile_specific_exits.py    # Profile-specific exit test
│   ├── exit_sweep_pnl_based_FIXED.py     # Exit rule testing (corrected)
│   └── structural_entry_analysis.py      # Entry failure analysis
│
├── data/backtest_results/
│   └── full_2020-2024/results.json       # Current backtest results (349 trades)
│
├── analysis/                              # Current analysis (cleaned)
│   └── TIME_TO_PEAK_CURRENT_DATA.txt     # Peak timing by profile
│
├── exits/                                 # Exit logic modules
│   └── detector_exit_v0.py               # Decay-aware detector (doesn't help)
│
├── reports/                               # Generated reports
│   └── exit_detector_v0_vs_day7.md       # Detector comparison
│
└── archive/                               # Historical/outdated
    └── session_2025-11-18_exit_investigation/  # Tonight's audit reports
```

---

## NEXT SESSION: CRITICAL QUESTIONS

**System loses $11,964 even with optimal exits. Why?**

**Investigate:**
1. **Execution costs** - Are spreads/slippage 2x too high?
2. **Focus on winners** - Deploy VANNA-only (+$6,370)?
3. **Regime-specific** - Does edge only exist in certain markets?
4. **Strategy thesis** - Is convexity rotation fundamentally flawed?

**Quick wins to test:**
- VANNA-only strategy (proven +$6,370)
- VANNA + SDG combo (combined +$7,506)
- Audit transaction cost model

---

## FILES TO IGNORE

**Archived (outdated):**
- `archive/session_2025-11-18_exit_investigation/` - Audit reports from tonight
- `archive/train_val_test_pollution_2025-11-18/` - Old contaminated results
- Old analysis files from pre-bug-fix era

**Deprecated scripts:**
- Scripts without `_FIXED` suffix may have bugs
- Always use `_FIXED` versions if they exist
