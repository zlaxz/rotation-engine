# GROUNDED ANALYSIS - Real System Parameters

**Source:** SESSION_STATE.md + backtest results

## ACTUAL SYSTEM CONFIGURATION

**Period:** 2020-2024 (5 years)
**Total Trades:** 604 trades (after filtering)
**Position Size:** 1 contract per leg (quantity=1)
**Typical Trade Cost:** ~$3-5K in premium per straddle
**Peak Concurrent Capital:** Unknown (need to calculate from trade tracking)

## ACTUAL RESULTS (Post-Bug-Fixes, With Dumb 14-Day Exits)

**Current Realized P&L:** -$6,323
**Peak Potential (Perfect Exits):** $342,579

**Profile Breakdown:**
| Profile | Trades | Peak $ | Current P&L |
|---------|--------|---------|-------------|
| 1 (LDG) | 140 | $43,951 | -$2,863 |
| 2 (SDG) | 42 | $16,330 | -$148 |
| 3 (CHARM) | 69 | $121,553 | -$1,051 |
| 4 (VANNA) | 151 | $79,238 | +$13,507 |
| 5 (SKEW) | 30 | $11,784 | -$3,337 |
| 6 (VOV) | 172 | $76,041 | -$5,077 |
| **TOTAL** | **604** | **$348,897** | **-$6,323** |

**Capture Rate:** 0.3% (only capturing $1K of $348K potential)

## THE CRITICAL QUESTION RE-FRAMED

**NOT:** "Is $342K total return good?"
**BUT:** "Are the PEAKS real or bug-inflated?"

If peaks are real:
- Entry logic is finding edge
- Exit logic is destroying value (0.3% capture)
- Fix exits → capture 60-80% = $209K-$279K over 5 years
- = **$42K-$56K annual** on deployed capital

If peaks are bug-inflated (agents suggest 50-70% fake):
- Real peaks: $105K-$174K (30-50% of $348K)
- With 60% capture: $63K-$104K over 5 years
- = **$13K-$21K annual** on deployed capital

## AGENT FINDINGS APPLIED TO REAL SYSTEM

**Agent #9 (Metrics):** Sharpe calculation broken
- Explains why Sharpe = 0.0026 (noise)
- Can't validate if peaks are real using current metrics
- **FIX THIS FIRST** - need working metrics to measure anything

**Agent #3 (Profiles):** Profile 4 +1094% OOS, Profile 3 sign flip
- If true → peaks are inflated by bias
- Profile 3 peak ($121K) especially suspect
- Profile 4 peak ($79K) might be phantom

**Agent #10 (Integration):** Data alignment mismatch
- Could be double-counting positions
- Peaks might be counting same trade twice

## NEXT STEP

Fix Sharpe calculation, re-run metrics on existing results, THEN we'll know if peaks are real.
