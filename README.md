# Rotation Engine - Convexity Trading System

**Status:** Exit investigation complete - System unprofitable with current implementation
**Last Session:** 2025-11-18 Late Night

---

## START HERE

1. **Read:** `START_HERE.md` - Navigation and current status
2. **Session summary:** `SESSION_SUMMARY_2025-11-18_LATE.md` - What we found tonight

---

## CRITICAL FINDINGS

**System Performance (2020-2024, 349 trades):**
- Best case (Day 7 exits): **Loses $11,964**
- Current (Day 14 exits): Loses $22,313
- Only 2 of 6 profiles profitable (VANNA, SDG)

**Validated:**
- ✅ Entries are structurally sound (7-gate rigorous test)
- ✅ Optimal exit timing found (Day 7 uniform)
- 🔴 System still unprofitable even with perfect execution

---

## NEXT STEPS

**Investigate why system loses money:**
1. Audit execution costs (spreads too conservative?)
2. Focus on VANNA-only (proven +$6,370)
3. Test regime-specific parameters
4. Or accept strategy doesn't have edge

---

## DIRECTORY ORGANIZATION

```
├── START_HERE.md              # ← Navigation
├── SESSION_SUMMARY_*.md       # ← Session notes
├── src/                       # Source code
├── scripts/                   # Analysis scripts (*_FIXED.py = debugged)
├── data/backtest_results/     # Backtest data
├── exits/                     # Exit logic modules
├── reports/                   # Generated reports
└── archive/                   # Old/outdated files
```

**All audit reports from tonight archived in:**
`archive/session_2025-11-18_exit_investigation/`

---

## USEFUL FILES

**Current Analysis:**
- `data/backtest_results/full_2020-2024/results.json` - 349 trades, all profiles
- `scripts/test_profile_specific_exits.py` - Test different exit days
- `scripts/exit_sweep_pnl_based_FIXED.py` - Test exit rules (bugs fixed)

**Archived (Reference Only):**
- `archive/session_2025-11-18_exit_investigation/old_analysis/` - 31 old analysis files
- `archive/session_2025-11-18_exit_investigation/` - Tonight's audit reports

---

**For questions:** Read `START_HERE.md` for navigation
