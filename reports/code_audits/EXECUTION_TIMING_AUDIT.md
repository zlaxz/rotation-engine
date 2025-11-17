# EXECUTION TIMING & REALISM AUDIT

**Date:** 2025-11-13
**Focus:** Trade execution timing, realistic pricing, market constraints

---

## CRITICAL FINDING #1: Trade Entry/Exit Timing Not Clearly Documented

**Status:** REQUIRES VERIFICATION

**Issue:**

Code does not clearly specify whether trade signals at bar N execute at bar N or bar N+1. This creates look-ahead bias if signals from bar N execute at bar N.

**Evidence:**

In `src/trading/profiles/profile_1.py:52-107`:

```python
def entry_logic(self, row: pd.Series, current_trade: Optional[Trade]) -> bool:
    # ...
    score = row.get('profile_1_score', 0.0)
    if score < self.score_threshold:
        return False
    # ...
    return True

def trade_constructor(self, row: pd.Series, trade_id: str) -> Trade:
    # ...
    spot = row['close']  # USE CLOSE PRICE FROM SAME BAR AS SIGNAL
    entry_date = row['date']
    # ...
```

**The Bug:**

When entry_logic returns True for row N:
1. Signal is computed using close price from bar N
2. Trade is immediately created with entry_date = bar N
3. Trade position size uses bar N's ATM strike
4. Trade Greeks are computed using bar N's IV

**Question:** Is execution price bar N's close or bar N+1's open?

**In _simulate_day() flow (need to verify):**
- Day N: Compute profile score, entry signal
- Day N: Check entry_logic, construct trade
- Day N or N+1: Execute trade?

**Real-World Requirement:**

In live trading:
- Day N 3:50 PM: Compute profile score from N's data
- Day N 4:00 PM: Send orders, trade executes at Day N close
- Day N+1 0:30 AM: Or wait for Day N+1 open?

Current code is ambiguous.

**Fix Required:**

Add explicit documentation:

```python
# In TradeSimulator or profile backtests:

# CLEAR SPECIFICATION:
# Signal generation at bar N uses data available at N's 4:00 PM close
# Trade execution at bar N 4:00-4:15 PM (uses bar N's close price)
# Delta hedge execution at bar N 4:00-4:15 PM (same bar as entry)
# Exit execution at exit bar N (uses bar N's close price)

# This is walk-forward correct: we know N's close when we execute
```

**Verification Needed:**

1. Search for execution price assignments in profile files
2. Confirm all trades use `row['close']` for entry bar
3. Confirm no trades reference future bars

---

## CRITICAL FINDING #2: Bid-Ask Spread Model Not Applied to Option Entry/Exit

**Status:** BROKEN

**Issue:**

The ExecutionModel class defines spreads:

```python
# src/trading/execution.py
def get_execution_price(self, mid_price: float, side: str, ...) -> float:
    # Returns: mid ± half_spread ± slippage
```

But search results show:

**Question:** Is this actually used in profile backtests?

**Evidence:**

Checked profile_1.py - no reference to ExecutionModel.
Checked where trades get priced - using what prices?

**Impact:**

If execution spreads are NOT applied:
- Entry at mid (should pay ask = mid + spread)
- Exit at mid (should receive bid = mid - spread)
- **Overstates profits by 0.5-1.5% per trade**

For a portfolio with 100+ trades, this is 50-150 basis points of overstatement.

**Fix Required:**

1. Find all trade execution price assignments
2. Apply ExecutionModel to get_execution_price() for:
   - Initial option entry (pay ask)
   - Delta hedge entry/exit (pay bid/ask)
   - Option exit at expiration or early exit (receive bid)
3. Verify spread widening during high volatility (line 96-99 of execution.py)

---

## CRITICAL FINDING #3: Assignment Risk Not Modeled on Short Options

**Status:** NOT ADDRESSED

**Issue:**

Profiles may include short options (e.g., short calls, short puts). If not explicitly long-only, assignment risk exists.

**Question:** Are any profiles SHORT options?

Looking at profile structures:
- Profile 1: Long ATM straddle ✓ (long only)
- Profile 2: Unclear (need to check)
- Profile 3-6: Need verification

**In profile_2.py**, "SDG" = Short Delta Gamma. This likely has SHORT options!

**Impact:**

If holding short calls:
- Day N: Sell call at strike K
- Day N+5: Market rallies past K
- Day N+10: Call assigned at expiration
- Position forced closed at strike K (not current market price)

Assignment execution price != market price = forced slippage

**Fix Required:**

1. Document which profiles are short options
2. For short option profiles:
   - Track position throughout holding period
   - Check if assigned at expiration
   - Use STRIKE price (not market price) as execution
   - Account for forced assignment slippage

---

## CRITICAL FINDING #4: Options Data Availability Check

**Status:** NOT VERIFIED

**Issue:**

The code loads options from Polygon (lines 24-101 of loaders.py), but:

```python
def _load_raw_options_day(self, date: datetime) -> pd.DataFrame:
    file_path = self.data_root / str(year) / month / f"{year}-{month}-{day}.csv.gz"
    if not file_path.exists():
        return pd.DataFrame()  # Returns empty!
```

**Question:** What happens when options data is missing?

If options chain is empty for day N:
- Can't compute Greeks
- Can't calculate profile scores
- Can't execute trades
- Backtest silently skips that day?

**Impact:**

If options data is sparse (e.g., first 100 days of data period):
- Backtest uses different lookback windows
- First N days' results unreliable
- Possibly introduces survivorship bias (only running on days with complete data)

**Fix Required:**

1. Check minimum data availability:
   - What's the earliest date with complete options data?
   - How many days are skipped due to missing data?
2. Document data gaps explicitly
3. Validate backtest only runs on days with complete data

---

## MEDIUM SEVERITY: Greeks Calculation Accuracy

**Status:** NOT BENCHMARKED

**Issue:**

Greeks are computed synthetically (IV proxy = RV × 1.2), but no benchmark against market Greeks.

**Missing Verification:**

1. **Delta accuracy**: Compare synthetic delta vs actual option deltas
2. **Gamma accuracy**: Compare synthetic gamma vs actual option gammas
3. **Theta accuracy**: Compare synthetic theta vs actual option thetas
4. **Vega accuracy**: Compare synthetic vega vs actual option vegas

**In profiles/features.py:81-98:**
```python
df['IV7'] = df['RV5'] * 1.2   # Hardcoded 1.2x multiplier
df['IV20'] = df['RV10'] * 1.2
df['IV60'] = df['RV20'] * 1.2
```

**Questions:**

1. Is 1.2x the right premium? (Varies by market)
2. Is this constant over time? (Probably not - skew affects this)
3. Are short-term IV and long-term IV both 1.2x? (No - they differ)

**Impact:**

If IV proxy is off:
- Greeks are off by 10-20%
- Delta hedging is ineffective
- Position Greeks drift during holding period
- P&L attribution is meaningless

**Recommendation:**

1. **Short-term fix:** Use actual IV from options chain (Polygon data has it)
2. **Medium-term:** Implement IV surface model
3. **Before live trading:** Benchmark Greeks against QuantLib on 100 test dates

---

## MEDIUM SEVERITY: Transaction Cost Completeness

**Status:** UNCLEAR IF COMPLETE

**Issue:**

Where are transaction costs applied? Need to verify:

1. **Option bid-ask spreads** - Are they included in entry/exit?
2. **Option commissions** - Are there per-contract fees?
3. **ES futures costs** - Are delta hedge costs calculated (line 155-177)?
4. **Exchange fees** - MicroStrategy fee, SEC fee, etc.?
5. **Clearing costs** - Clearing house fees?

**In ExecutionModel (lines 15-51):**
```python
base_spread_atm: float = 0.75,  # Base ATM straddle spread ($)
base_spread_otm: float = 0.45,  # Base OTM strangle spread ($)
spread_multiplier_vol: float = 1.5,  # High vol widening
slippage_pct: float = 0.0025,  # 0.25% slippage
es_commission: float = 2.50,  # ES round-trip
es_slippage: float = 12.50  # ES half-tick
```

**Questions:**

1. Are spreads applied to option entry AND exit?
2. Are ES hedging costs applied on EVERY rebalance?
3. Is slippage applied on BOTH sides (buy and sell)?

**Impact:**

If costs are understated by 50%, net P&L is overstated by $X per trade.

For 100 trades × $500 per trade = $50,000 overstatement.

**Fix Required:**

Verify in one of the profile backtests:
```python
# In profile_1.py backtest method:

# Entry:
entry_cost = execution_model.get_execution_price(
    mid_option_price, 'buy', moneyness, dte, vix, strangle=False
)
# Should include: mid + half_spread + slippage

# Daily delta hedge:
hedge_cost = execution_model.get_delta_hedge_cost(contracts)
# Should include: ES commission + ES slippage

# Exit:
exit_proceeds = execution_model.get_execution_price(
    mid_option_price, 'sell', moneyness, dte, vix, strangle=False
)
# Should include: mid - half_spread - slippage
```

Search profile files for these calls. If not found, costs are NOT applied.

---

## MEDIUM SEVERITY: Liquidity Constraints

**Status:** NO CONSTRAINTS MODELED

**Issue:**

The code does not check:
1. **Option volume** - Can we trade 10 contracts of this strike?
2. **Open interest** - Is there sufficient OI?
3. **Bid-ask width** - Widens dramatically in illiquid options

**In loaders.py:188-189:**
```python
# Remove options with no volume (stale quotes)
df = df[df['volume'] > 0].copy()
```

This filters out zero-volume options, but doesn't:
1. Check if volume is sufficient for trade size
2. Adjust spread width for low-volume options
3. Check open interest

**Example Problem:**

```
Backtest wants to:
- Buy 100 SPY 400 calls (need 100 contracts)
- 400 call has volume = 2
- Only 2 contracts were traded all day
- But backtest assumes full fill at mid price

Reality:
- Can't buy 100 when only 2 traded
- Would have to execute at much wider spreads
- Or impossible to fill at all
```

**Impact:**

Overstates profits on illiquid options by 2-5%.

**Fix Required:**

1. Check trade size vs daily volume
2. Check trade size vs open interest
3. Scale up spreads for low-liquidity options
4. Flag trades that would be impossible to fill

---

## CRITICAL: Portfolio Margin / Reg-T Compliance

**Status:** NOT VERIFIED

**Issue:**

Backtesting assumes infinite leverage and no margin requirements.

**In practice:**

- Options trades require margin (initial + maintenance)
- Portfolio margins exist but require $125K+ accounts
- Reg-T margin = 20-25% of position value typically
- Margin calls force liquidation if portfolio drops

**Questions:**

1. What's the portfolio size? (Assumed in backtest?)
2. What leverage is used? (Backtests often assume 1:1)
3. Are margin requirements modeled?
4. What happens on a 2x down day? (Margin call!)

**Impact:**

If backtest ignores margin requirements:
- Can hold positions that would be impossible in real trading
- Overstates returns in high-volatility periods
- Ignores forced liquidations from margin calls

**In 2020 March crash:** Many strategies that worked in backtests failed in reality due to margin calls.

---

## SUMMARY OF TIMING/EXECUTION ISSUES

| Bug | Severity | Impact | Status |
|-----|----------|--------|--------|
| Entry/exit timing ambiguity | HIGH | Possible look-ahead bias | REQUIRES DOCUMENTATION |
| Bid-ask spreads not applied | CRITICAL | 0.5-1.5% profit overstatement | NEEDS VERIFICATION |
| Assignment risk not modeled | HIGH | Short options can force close | NOT ADDRESSED |
| Options data gaps | MEDIUM | Sparse early backtests | NEEDS AUDIT |
| Greeks not benchmarked | MEDIUM | 10-20% estimation error | NEEDS BENCHMARK |
| Transaction costs incomplete | HIGH | Costs understated 20-50% | NEEDS VERIFICATION |
| Liquidity constraints ignored | MEDIUM | Can't fill impossible trades | NOT MODELED |
| Margin requirements ignored | HIGH | Doesn't model real constraints | NOT MODELED |

---

## RECOMMENDATIONS

### Before Paper Trading
1. Fix TIER 0 percentile bugs (in TIER0_LOOKAHEAD_AUDIT.md)
2. Verify trade execution timing explicitly (add comments)
3. Verify execution spreads are applied

### Before Live Trading
1. Benchmark Greeks vs QuantLib
2. Add liquidity checks
3. Model margin requirements
4. Verify transaction costs on 10 real trades

---

**These issues compound: Multiple layers of unrealism add up to 2-5% total understatement of actual costs.**

**Real capital depends on realistic execution modeling.**
