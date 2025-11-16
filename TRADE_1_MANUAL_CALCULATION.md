# TRADE 1 MANUAL CALCULATION
## Verifying P&L Logic by Hand

**Trade**: Profile_1_LDG_0001
**Entry**: May 20, 2020
**Exit**: June 5, 2020 (12 days later)
**Structure**: Long ATM straddle, 75 DTE

---

## Entry (May 20, 2020)

**Market conditions:**
- SPY: $296.83
- ATM strike: $297 (rounded)
- VIX: ~28 (post-COVID volatility still elevated)
- Target DTE: 75 days

**Straddle value** (estimated using Black-Scholes):
- ATM call (297 strike, 75 DTE, 28% IV): ~$12.50
- ATM put (297 strike, 75 DTE, 28% IV): ~$11.50
- **Straddle mid**: $24.00

**Entry execution** (with bugs):
- Mid: $24.00
- Half spread: $0.50 (ATM straddle)
- Slippage (BUG): $24.00 × 0.0025 = $0.06
- **Entry price**: $24.00 + $0.50 + $0.06 = **$24.56** per share
- **Entry cost**: $24.56 × 100 × 1 = **$2,456.00**

**Entry commission**:
- 2 contracts (1 call + 1 put) × $0.65 = **$1.30**

**Estimated exit commission** (charged on Day 1):
- 2 contracts × $0.65 = **$1.30**

**Day 1 P&L calculation**:
- Current value (end of Day 1): ~$24.00 (mid)
- Current value in dollars: $24.00 × 100 = $2,400
- Unrealized P&L: $2,400 - $2,456 = **-$56.00**
- Subtract entry commission: -$1.30
- Subtract estimated exit commission (BUG): -$1.30
- **Day 1 P&L**: -$56.00 - $1.30 - $1.30 = **-$58.60**

**Backtest shows: -$61.40**

**Difference**: $2.80 - close enough! (Could be different spread assumption or slippage)

---

## Exit (June 5, 2020)

**Market conditions:**
- SPY: $319.15 (moved +$22.32 or +7.52%)
- Days elapsed: 12 days
- DTE remaining: 63 days

**Straddle value** (estimated):
- SPY moved from $297 → $319 (+$22)
- Call ($297 strike) now ITM by $22: Value ~$34
- Put ($297 strike) now OTM by $22: Value ~$4
- **Straddle mid**: $38.00

**But wait**: Theta decay over 12 days:
- Straddle theta: ~-$50/day
- 12 days × -$50 = -$600 decay
- **Adjusted straddle value**: $38.00 - $6.00 = $32.00 (rough)

Actually, let me be more precise. The gamma P&L from SPY move should offset decay:
- **Gamma P&L**: 0.5 × gamma × (move)²
- For ATM straddle: gamma ≈ 0.05
- Move: $22.32
- Gamma P&L: 0.5 × 0.05 × (22.32)² = **$12.46** per share
- In dollars: $12.46 × 100 = **$1,246**

**Total P&L estimate** (rough):
- Gamma P&L: +$1,246
- Theta decay (12 days): -$600
- Net option P&L: +$646
- Entry commission: -$1.30
- Exit commission: -$1.30
- **Estimated net**: +$643.40

**Backtest shows: +$140.60**

**DISCREPANCY: $502.80 missing!**

---

## Where Did $502.80 Go?

**Possible culprits:**

1. **Delta hedging costs**: Profile 1 has daily delta hedging enabled
   - 12 days of hedging
   - If each hedge costs $15 (ES commission + slippage): 12 × $15 = $180
   - Still not enough to explain $502 gap

2. **Spread costs underestimated**:
   - Entry spread: $0.50
   - Exit spread: $0.50
   - Total spread cost: $1.00 × 100 = $100
   - Already accounted for

3. **Slippage bug amplified**:
   - Entry slippage: $0.06 × 100 = $6
   - Exit slippage: $0.06 × 100 = $6
   - Total: $12 (tiny)

4. **Entry/exit prices wrong**:
   - Maybe straddle was more expensive at entry (IV higher?)
   - Maybe straddle was cheaper at exit (IV crushed?)

5. **Daily P&L calculation is wrong**:
   - $502 discrepancy suggests systematic issue
   - Maybe Greeks are wrong?
   - Maybe position sizing is wrong?

---

## The Day-by-Day P&L Pattern is Suspicious

Looking at daily P&L:
- Day 1: -$61.40
- Day 2: +$16.00
- Day 3: -$80.00
- ...
- Day 10: +$219.00
- Day 11: -$201.00
- Day 12: +$380.00

**Day 10-12 swings are HUGE**: +$219, -$201, +$380

For context:
- Entry cost: ~$2,456
- Day 12 swing: $380 (15.5% of entry cost in ONE DAY!)

**What could cause $380 swing in one day?**

Looking at SPY prices:
- Day 11: SPY $311.20
- Day 12: SPY $319.15 (+$7.95 or +2.55%)

**Expected P&L from 2.55% move**:
- Gamma P&L: 0.5 × 0.05 × (7.95)² = $1.58 per share
- In dollars: $1.58 × 100 = $158

**But backtest shows: $380**

**$380 / $158 = 2.4x more than expected!**

Something is VERY wrong with the P&L calculation.

---

## Hypothesis: Daily P&L Includes Something Extra

Let me check what's in `daily_pnl`:

**Option 1**: Daily P&L = change in unrealized P&L
```
Day 11 unrealized: -$239.40
Day 12 unrealized: +$140.60
daily_pnl = $140.60 - (-$239.40) = $380.00 ✓
```

This checks out! Daily P&L is just the delta in unrealized P&L.

**But why did unrealized P&L change by $380?**

Looking at Day 11 → Day 12:
- SPY: $311.20 → $319.15 (+$7.95)
- Unrealized P&L: -$239.40 → +$140.60 (+$380)

**This means**: Straddle value changed by $380 when SPY moved $7.95

**Is this possible?**

For ATM straddle with ~60 DTE:
- Delta: ~0.5 (call) + ~-0.5 (put) = 0 (delta neutral)
- Gamma: ~0.05
- Vega: ~0.20

**Gamma P&L from $7.95 move**:
- 0.5 × 0.05 × (7.95)² × 100 = $158

**Vega P&L** (if IV changed):
- If IV dropped 2 points: -2 × 0.20 × 100 = -$40
- If IV spiked 2 points: +2 × 0.20 × 100 = +$40

**Theta decay (1 day)**:
- ~-$50

**Total expected change**: $158 - $50 = $108

**But backtest shows: $380**

**$380 / $108 = 3.5x more than expected!**

---

## CONCLUSION: P&L Calculation is BROKEN

**Evidence:**
1. Day 1 loss ($61.40) matches hand calculation (confirms entry cost correct)
2. Day 12 swing ($380) is 3.5x larger than expected from Greeks
3. Final P&L ($140.60) is $500 less than expected

**Possible bugs:**
1. **Position sizing wrong**: Maybe trading 3-4 straddles instead of 1?
2. **Greeks calculation wrong**: Gamma/vega/theta values incorrect?
3. **Price updates wrong**: Maybe using wrong mid prices for MTM?
4. **Some cost double-counted**: Transaction costs applied multiple times?

---

## NEXT STEPS

Need to check:
1. What is the ACTUAL position size? (Should be 1 straddle = 100 shares × 2 legs)
2. What Greeks does the system calculate?
3. What prices are used for daily MTM?
4. Are there hidden costs being applied?

**This requires diving into the Trade class and seeing what mark_to_market() actually does.**
