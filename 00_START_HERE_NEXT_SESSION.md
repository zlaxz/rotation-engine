# START HERE - Next Session

**Date:** 2025-11-18 Evening Session End
**Status:** METHODOLOGY CONTAMINATION DISCOVERED

---

## CRITICAL: ALL PREVIOUS RESULTS ARE INVALID

**What happened:**
- Fixed 22 bugs using full dataset (2020-2024)
- Derived exit timing from full dataset
- ZERO train/validation/test splitting
- Perfect overfitting crime

**Consequence:**
ALL metrics, parameters, and results are contaminated. Cannot be used for live trading.

---

## NEXT SESSION: START FRESH WITH PROPER METHODOLOGY

### Step 1: Read Documentation (5 minutes)
1. `docs/SESSION_2025-11-18_EVENING_HANDOFF.md` - Full context
2. `docs/TRAIN_VALIDATION_TEST_SPEC.md` - Methodology to implement
3. `SESSION_STATE.md` - Current status

### Step 2: Archive Contamination (5 minutes)
```bash
mkdir -p archive/contaminated_2025-11-18
mv data/backtest_results/full_tracking_results.json archive/contaminated_2025-11-18/
echo "IN-SAMPLE CONTAMINATED - DO NOT USE FOR LIVE TRADING" > archive/contaminated_2025-11-18/WARNING.txt
```

### Step 3: Implement Train/Val/Test Scripts (2 hours)
Create three scripts with ENFORCED date boundaries:
- `scripts/backtest_train.py` (2020-2021 ONLY)
- `scripts/backtest_validation.py` (2022-2023 ONLY)
- `scripts/backtest_test.py` (2024 ONLY)

### Step 4: Run Train Period (30 minutes)
```bash
python scripts/backtest_train.py
```
- Derive median peak timing from 2020-2021 ONLY
- Save parameters: `config/train_derived_2020-2021.json`
- Use `statistical-validator` agent after completion

### Step 5: Run Validation Period (30 minutes)
```bash
python scripts/backtest_validation.py --params config/train_derived_2020-2021.json
```
- Apply train parameters to 2022-2023
- Expect 20-40% degradation (acceptable)
- If >50% degradation or sign flip → Strategy doesn't work

---

## WHAT NOT TO DO

- ❌ Don't trust current results (contaminated)
- ❌ Don't test on full dataset
- ❌ Don't derive parameters without train/test split
- ❌ Don't skip statistical validation agents

---

## DATA SPLITS

**Train:** 2020-01-01 to 2021-12-31 (2 years, ~500 days)
**Validation:** 2022-01-01 to 2023-12-31 (2 years, ~500 days)
**Test:** 2024-01-01 to 2024-12-31 (1 year, ~250 days)

---

**Philosophy:** Better to have zero results than contaminated results.

**Next Session Goal:** Proper out-of-sample validation using industrial-grade methodology.
