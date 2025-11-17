# Worst Losers Analysis - How to Use These Files

**Analysis Date**: 2025-11-15
**Working Directory**: `/Users/zstoc/rotation-engine/`

## Files Generated

### 1. **RISK_AVOIDANCE_STRATEGY.md** ← START HERE
**The main report**. Read this first. Contains:
- Executive summary of findings
- What went wrong (entry conditions of worst losers)
- The risk signals that predict disasters
- Implementation roadmap (Tier 1 vs Tier 2 filters)
- Specific trades that would be filtered

**Time to read**: 15-20 minutes
**What to do next**: Follow implementation checklist

---

### 2. **DISASTER_FILTER_SUMMARY.txt**
**Quick reference cheat sheet**. One-page summary:
- Key statistics in table format
- Single strongest filter (RV5 > 0.22)
- What each condition means
- Specific recommendations
- Next steps

**Time to read**: 5 minutes
**Good for**: Sharing with others, quick reference

---

### 3. **DISASTER_FILTER_ANALYSIS.md**
**Deep technical analysis**. Contains:
- Per-signal discrimination analysis
- Profile vulnerability breakdown
- Threshold optimization
- Performance by market condition
- Detailed explanation of worst trades

**Time to read**: 30 minutes
**Good for**: Understanding the "why" behind each recommendation

---

### 4. **worst_losers_bottom_10pct.csv**
**Raw data on all 66 worst trades**. Columns:
- `profile` - Which strategy (Profile_1_LDG, etc)
- `trade_id` - Unique identifier for trade
- `entry_date` - When trade entered
- `exit_date` - When trade exited
- `days_held` - How long trade was open
- `final_pnl` - P&L in dollars
- `entry_spot`, `strike`, `dte_at_entry` - Position parameters
- `RV5`, `RV10`, `RV20` - Realized volatility metrics
- `slope`, `return_5d`, `return_10d` - Trend/momentum metrics
- `delta_at_entry`, `gamma_at_entry`, `theta_at_entry`, `vega_at_entry` - Greeks

**Use for**: Detailed analysis of specific trades, validating patterns

---

## Quick Start: The Recommendation

### If you have 5 minutes:

Read DISASTER_FILTER_SUMMARY.txt

**Key takeaway**: Skip trades when RV5 > 0.22. This single filter turns your -$22.9K portfolio into +$0.9K.

---

### If you have 30 minutes:

1. Read RISK_AVOIDANCE_STRATEGY.md (main report)
2. Skim DISASTER_FILTER_ANALYSIS.md (tables section)

**Key takeaway**: Implement Tier 1 filter (RV5 only) immediately. Measurable +$23.8K improvement.

---

### If you have 1-2 hours:

1. Read RISK_AVOIDANCE_STRATEGY.md (full)
2. Read DISASTER_FILTER_ANALYSIS.md (full)
3. Explore worst_losers_bottom_10pct.csv in Excel/Jupyter

**Key takeaway**: Understand all the nuances, plan multi-phase implementation, identify edge cases.

---

## Implementation Workflow

### Step 1: Verify RV5 Calculation (Today)

```bash
# Check that your backtest calculates RV5 correctly
# Compare against worst_losers_bottom_10pct.csv rows
```

Specific trades to spot-check:
- Trade ID: `Profile_3_CHARM_2025-04-25_551` → RV5 should be 0.3090
- Trade ID: `Profile_2_SDG_2022-10-04_377` → RV5 should be 0.3531
- Trade ID: `Profile_4_VANNA_2022-06-07_415` → RV5 should be 0.2702

If values match, RV5 calculation is correct.

---

### Step 2: Implement Filter (Tomorrow)

Add to your backtest engine:

```python
def should_trade(entry_conditions):
    # Tier 1: RV5 filter only (RECOMMENDED)
    if entry_conditions['RV5'] > 0.22:
        return False  # Skip this trade
    return True

# OR for Tier 2 (conservative):
def should_trade(entry_conditions):
    if entry_conditions['RV5'] > 0.22 and entry_conditions['slope'] < 0.005:
        return False  # Skip this trade
    return True
```

---

### Step 3: Re-run Backtest (Tomorrow)

```bash
python backtest.py --filter RV5_ONLY --date-range 2020-2025
```

Expected output:
- Total trades: ~551 (was 668)
- Total P&L: ~+$900 (was -$22,877)
- Win rate: ~46% (was 44%)

---

### Step 4: Compare Metrics (Next Day)

Create comparison table:

| Metric | No Filter | RV5 Filter | Improvement |
|--------|-----------|-----------|------------|
| P&L | -$22,877 | +$899 | +$23,776 |
| Win Rate | 44.2% | 46.1% | +1.9% |
| Sharpe | [baseline] | [expected: +20%] | ? |
| Max DD | [baseline] | [expected: lower] | ? |

---

### Step 5: Deep Analysis (Next Week)

1. Check Sharpe/Sortino/Calmar ratios
2. Verify maximum drawdown decreased
3. Identify any regressions per profile
4. Study high-RV winners (15.2% of winners) - what made them work?

---

## Key Numbers to Remember

### The Filter
- **Threshold**: RV5 > 0.22
- **Trigger rate**: 17.5% of trades
- **Impact**: +$23,776 (103.9%)
- **Complexity**: 1 number, 1 comparison

### The Payoff
- **Baseline portfolio**: -$22,877
- **Filtered portfolio**: +$899
- **Per-skipped-trade saved**: $210

### The Risk
- **Worst trades eliminated**: 31.8% of bottom 10%
- **False positive rate**: 15.2% (winners in high-RV)
- **Opportunity cost**: 17.5% fewer trades

### Profile Sensitivity
- **Worst hit**: CHARM (short straddles, loses -$1,692 avg in disasters)
- **Most frequent**: VANNA/VOV (22-21 appearances in worst 10%)
- **Most resilient**: Still lose, but lower severity

---

## Validation Checklist

Before deploying filter live:

- [ ] RV5 calculation verified against CSV
- [ ] Filter logic implemented correctly
- [ ] Backtest runs without errors
- [ ] P&L improvement matches expectations (~$23.8K)
- [ ] Win rate improves (~46% vs 44%)
- [ ] No data leakage (filter uses only past RV5, not future)
- [ ] Per-profile impact analyzed (CHARM benefit confirmed?)
- [ ] Walk-forward validation performed (doesn't overfit 2020-2025)
- [ ] Transaction cost impact estimated
- [ ] Live trading readiness: Is 46% win rate acceptable for your capital?

---

## Q&A

### Q: Will RV5 > 0.22 still work in 2026?
**A**: Unknown. The threshold is based on 5 years of data. It should generalize if:
- Volatility regimes remain similar
- Greeks calculations consistent
- Trade holding periods similar (14 days)

Test on new data as it comes in.

### Q: What about the absolute worst trades (CHARM at RV5 < 0.15)?
**A**: Different problem (decay scenarios, not vol spikes). Can't filter them with RV5. Requires:
- Profile-specific guards (maybe don't short straddles during vol compression?)
- IV crush detection (entry vol vs forward forecasts)
- Time-decay monitoring (adjust when theta accelerates)

This is Phase 2 work, after RV5 filter is confirmed.

### Q: Should I use Tier 1 (RV5 only) or Tier 2 (RV5 + slope)?
**A**: Start with Tier 1. If you still want to reduce disasters, add Tier 2. But don't use both.

Expected improvement:
- Tier 1 alone: +$23.8K
- Tier 2 alone (if no Tier 1): +$12.1K
- Both together: Only +$24-25K (diminishing returns)

### Q: What if I'm willing to miss winners to avoid losers?
**A**: You already are. 15.2% of winners are in high-RV periods. But 31.8% of losers are there. Net discrimination is +16.7% in your favor. Worth it.

### Q: Can I use different RV5 thresholds per profile?
**A**: Good idea for future work. For now, use 0.22 globally. If you find CHARM needs stricter (0.18) and VANNA needs looser (0.24), split later.

---

## Technical Details

### RV5 Calculation
RV5 = 5-day realized volatility. Calculated from daily returns:
```
RV5 = sqrt(mean(return[0:5]^2))
```

### Slope Calculation
Slope = linear regression slope of last 20 closes on last 20 days:
```
slope = linear_regression(price[0:20])
```

Both should be in your entry_conditions dict already. Verify by checking worst_losers_bottom_10pct.csv.

### Data Source
All analysis from: `/data/backtest_results/full_tracking_results.json`

---

## Next Analysis

After implementing RV5 filter, consider:

1. **Regime classification audit**: Does regime classification predict disasters better than RV5?
2. **CHARM profile deep dive**: Why are they hit hardest? Can we add protective collar?
3. **Transaction cost modeling**: How much of the +$23.8K improvement survives realistic slippage/commissions?
4. **Walk-forward validation**: Does 0.22 threshold hold up in out-of-sample periods?
5. **Live trading simulation**: Monte Carlo on filtered strategy with realistic execution

---

**Questions?** See specific sections in RISK_AVOIDANCE_STRATEGY.md or DISASTER_FILTER_ANALYSIS.md.

**Ready to implement?** Start with Step 2 of Implementation Workflow above.

