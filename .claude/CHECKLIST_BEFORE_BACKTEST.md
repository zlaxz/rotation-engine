# MANDATORY CHECKLIST - Before Running ANY Backtest Code

Before executing ANY code that produces P&L, metrics, or trade results:

## 1. Execution Model ✅
- [ ] Uses ExecutionModel.get_execution_price() (not midpoint)
- [ ] Applies bid/ask spreads
- [ ] Applies slippage

## 2. Transaction Costs ✅
- [ ] Deducts option commissions ($0.65/contract)
- [ ] Deducts SEC fees for shorts
- [ ] Deducts ES hedge costs if applicable
- [ ] Uses ExecutionModel.get_commission_cost()

## 3. P&L Calculation ✅
- [ ] Uses Trade.calculate_realized_pnl() (not direct math)
- [ ] Sign convention correct (positive = long)
- [ ] Multiplier applied (100x for standard options)

## 4. Walk-Forward Compliance ✅
- [ ] No look-ahead bias
- [ ] Greeks use current date only
- [ ] Entry/exit use available data only

## 5. Code Quality ✅
- [ ] Reuses validated framework components
- [ ] NOT a "quick test" or "simplified version"
- [ ] Production-grade, not prototype

**If ANY checkbox is unchecked:**
🛑 DO NOT RUN. Results will be invalid.

**No such thing as "quick test" - build it right or don't build it.**
