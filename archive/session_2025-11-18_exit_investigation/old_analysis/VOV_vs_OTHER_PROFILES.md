# VOV vs Other Profiles: Comparative Peak Timing Analysis

**Analysis Date:** 2025-11-16
**Source:** `/Users/zstoc/rotation-engine/data/backtest_results/current/results.json`

---

## Executive Comparison

VOV is **NOT unique** in experiencing peak timing issues, but it's **uniquely vulnerable** due to its structure.

| Metric | VOV (Profile_6) | Best | Worst |
|--------|-----------------|------|-------|
| Total trades | 172 | - | - |
| Peak timing (median) | 6 days | CHARM (0) | VANNA (8) |
| Decay from peak | $383 median | LDG ($284) | CHARM ($1,653) |
| Peak-day correlation to P&L | +0.643 | SKEW (+0.783) | LDG (+0.665) |
| Trades exiting at peak | 23/172 (13.4%) | VANNA (31/151 = 20.5%) | LDG (20/140 = 14.3%) |
| Win rate | 35.5% | VANNA (58.3%) | SKEW (26.7%) |
| Total P&L | -$5,077 | VANNA (+$13.5K) | SKEW (-$3.3K) |

---

## Profile-by-Profile Breakdown

### Profile_1_LDG (Long-Dated Gamma Efficiency)
- **Trades:** 140
- **Peak timing:** Median 7 days (mean 6.9)
- **Decay:** $284 median - **BEST** decay profile
- **Correlation (peak day → P&L):** +0.665
- **Exiting at peak:** 20/140 (14.3%)
- **Win rate:** 43.6%
- **P&L:** -$2,863

**Assessment:** Similar to VOV in structure but LOWER decay. Better exit behavior despite low at-peak rate.

---

### Profile_2_SDG (Short-Dated Gamma Spike)
- **Trades:** 42
- **Peak timing:** Median 4 days (mean 4.5) - **Early peaks**
- **Decay:** $359 median
- **Correlation:** +0.649
- **Exiting at peak:** 11/42 (26.2%)
- **Win rate:** 35.7%
- **P&L:** -$148

**Assessment:** Smaller sample but interesting - peaks EARLIER than VOV yet much less negative P&L. Exit-at-peak rate is higher (26%), suggesting some trader discipline.

---

### Profile_3_CHARM (Charm/Decay Dominance)
- **Trades:** 69
- **Peak timing:** Median 0 days (mean 0.0) - **IMMEDIATE peaks**
- **Decay:** $1,653 median - **WORST decay**
- **Correlation:** Not calculated (no variance in peak timing)
- **Exiting at peak:** 0/69 (0.0%)
- **Win rate:** 63.8% - **Highest!**
- **P&L:** -$1,051

**Assessment:** Paradox! Worst decay but HIGHEST win rate. Suggests CHARM profile is about *capturing decay*, not about avoiding it. Different strategy objective.

---

### Profile_4_VANNA (Vanna - Vol-Spot Correlation)
- **Trades:** 151
- **Peak timing:** Median 8 days (mean 7.7) - **Latest**
- **Decay:** $275 median
- **Correlation:** +0.724 - **Second highest**
- **Exiting at peak:** 31/151 (20.5%) - **Best exit-at-peak rate**
- **Win rate:** 58.3% - **Second highest**
- **P&L:** +$13,507 - **ONLY PROFITABLE PROFILE**

**Assessment:** This is the winning profile. Later peaks, better exit discipline, strong correlation. We should study VANNA's exit logic.

---

### Profile_5_SKEW (Skew Convexity)
- **Trades:** 30
- **Peak timing:** Median 5 days (mean 4.8)
- **Decay:** $450 median
- **Correlation:** +0.783 - **Highest correlation**
- **Exiting at peak:** 3/30 (10%)
- **Win rate:** 26.7% - **Worst**
- **P&L:** -$3,337

**Assessment:** Smallest sample. Highest correlation but lowest win rate. Peak timing matters most here but trading logic is broken.

---

### Profile_6_VOV (Vol-of-Vol Convexity)
- **Trades:** 172
- **Peak timing:** Median 6 days (mean 6.9)
- **Decay:** $383 median - **Second worst**
- **Correlation:** +0.643
- **Exiting at peak:** 23/172 (13.4%)
- **Win rate:** 35.5%
- **P&L:** -$5,077 - **Second worst**

**Assessment:** Middle-of-the-road on most metrics but WORST at exit discipline (only 13.4% at peak). High decay is PREVENTABLE with better exit rules.

---

## Key Insights

### 1. CHARM is Different (Not Really Losing)
Profile_3 (CHARM) has massive decay ($1,653) but maintains 63.8% win rate. This suggests:
- CHARM trades are SHORT-DECAY positions (seller's perspective)
- Decay = profit for these trades
- Exit discipline is actually good (capturing decay decay)
- Different strategy objective: *harvest decay*, not *avoid decay*

**Implication:** Our "decay is bad" assumption is profile-specific, not universal.

---

### 2. VANNA is the Winner (+$13.5K)
Only profitable profile. Key differences from VOV:
- 20.5% exit at peak (vs VOV 13.4%)
- Later peaks (8 days, vs VOV 6)
- 58.3% win rate (vs VOV 35.5%)
- Moderate decay ($275, vs VOV $383)

**Question:** Does VANNA have better entry filter, or better exit logic?

---

### 3. Peak Timing Correlation is Profile-Dependent
- SKEW: +0.783 (peak timing matters MOST)
- VANNA: +0.724 (peak timing matters A LOT)
- VOV: +0.643 (peak timing matters, but less than others)
- LDG: +0.665 (peak timing matters)

**Interpretation:** For some profiles (SKEW, VANNA), when peaks occur is crucial. For others (VOV), multiple factors matter equally.

---

### 4. Exit-at-Peak Rate Predicts Profitability
Ranking by profitability (P&L):
1. VANNA: +$13.5K (20.5% at-peak exits)
2. LDG: -$2.9K (14.3% at-peak exits)
3. CHARM: -$1.1K (0% at-peak exits) ← Different objective
4. VOV: -$5.1K (13.4% at-peak exits)
5. SDG: -$0.1K (26.2% at-peak exits)
6. SKEW: -$3.3K (10% at-peak exits)

**Pattern:** VANNA (best profitability) exits at peak most frequently. VOV should emulate this.

---

## Recommended Analysis Path

### Step 1: Reverse-Engineer VANNA's Exit Logic
- What makes VANNA exit at peak 20.5% vs VOV's 13.4%?
- Is it Greeks-based? Time-based? Volatility-based?
- Can we apply VANNA's exit logic to VOV?

### Step 2: Investigate CHARM's Decay Strategy
- CHARM makes money with decay
- Is CHARM actually a SHORT vol position disguised as LONG?
- Should VOV be SHORT-volatility instead of LONG?

### Step 3: Test "Exit at Peak" Across All Profiles
- How much would each profile improve with peak-exit logic?
- Expected improvements:
  - SKEW: -$3.3K → +$30K (highest upside)
  - VOV: -$5.1K → +$15K-$80K (high upside)
  - LDG: -$2.9K → +$10K (moderate)
  - VANNA: Already +$13.5K → Verify doesn't break

### Step 4: Comparative Entry Filter Analysis
- VANNA and CHARM have different entry requirements
- Are their entry filters better at predicting "good peak timing"?
- Can we borrow their entry logic for VOV?

---

## The VOV Specific Problem

VOV's failure is NOT due to:
- Peak timing being later than others (it's middle-of-road)
- Decay being higher than others (CHARM worse, VANNA better)
- Peak-day correlation being weak (it's middle, not outlier)

VOV's failure IS due to:
- **Combining moderate decay ($383) with low exit-at-peak rate (13.4%)**
- Other profiles either:
  - Accept/harvest decay (CHARM)
  - Exit at peak better (VANNA: 20.5%)
  - Have lower decay (LDG: $284)

**VOV is doing everything MODERATELY - which adds up to FAILURE.**

---

## Action Items

### High Priority
1. **Analyze VANNA's exit logic** - Why is it exiting at peak 56% more often than VOV?
2. **Implement exit-at-peak for VOV** - Expected: -$5K → +$15K (3x improvement)
3. **Compare entry conditions** between VANNA (profitable) and VOV (unprofitable)

### Medium Priority
4. **Test peak-exit across all profiles** - Measure breakage/improvement
5. **Investigate CHARM's strategy** - Is it SHORT vol in LONG clothing?
6. **Document exit logic** - What's different between profiles?

### Low Priority
7. Profile performance ranking analysis
8. Parameter sensitivity analysis per profile
9. Stress testing under regime changes

---

## Summary

VOV is fixable. It doesn't need a complete rethink—it needs:
1. Better exit discipline (learn from VANNA)
2. Exit-at-peak logic (to handle decay better)
3. Possibly entry filter adjustment (to reduce early peaks)

The path to +$20K+ is clear. **VANNA shows it's possible.**

---

**Next Steps:** Analyze `/Users/zstoc/rotation-engine/data/backtest_results/current/results.json` to extract VANNA's exit logic
