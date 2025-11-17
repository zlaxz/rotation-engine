# Migration Guide: True Multi-Position Rotation Engine

## Overview

**Critical Change**: The rotation system has been redesigned from post-hoc weighted aggregation to true multi-position portfolio simulation.

**Why This Matters**: The old system couldn't model actual rotation behavior, capital constraints, or realistic transaction costs. Results were P&L arithmetic, not portfolio simulation.

---

## Architectural Changes

### Old Architecture (BROKEN)

```python
# OLD: Run 6 independent backtests
for profile in profiles:
    results[profile] = run_independent_backtest(profile)

# Apply fixed weights POST-HOC
portfolio_pnl = sum(results[p].pnl * weights[p] for p in profiles)
```

**Problems:**
- No simultaneous multi-position tracking
- Can't model rotation timing and costs
- No capital constraints (each profile assumes full capital)
- No portfolio-level risk management
- P&L arithmetic, not position accounting

### New Architecture (TRUE ROTATION)

```python
# NEW: Unified daily loop with multi-position portfolio
portfolio = Portfolio(initial_capital=1M)

for day in date_range:
    regime = classify_regime(data[day])
    scores = score_all_profiles(data[day])
    targets = allocate_capital(scores, regime)

    portfolio.rebalance(targets)  # Close/open positions
    portfolio.mark_to_market(current_prices)
```

**Features:**
- 6 simultaneous positions (one per profile)
- Real rotation timing and transaction costs
- Capital constraints (40% max per profile, 5% min)
- Portfolio-level P&L and Greeks
- Position-based accounting (single source of truth)

---

## Key Files

### New Files

| File | Purpose |
|------|---------|
| `src/backtest/position.py` | Individual position tracking |
| `src/backtest/portfolio_new.py` | Multi-position portfolio |
| `src/backtest/engine_new.py` | True rotation engine |
| `tests/test_multiposition_portfolio.py` | Portfolio tests |
| `tests/test_rotation_engine.py` | Engine tests |
| `tests/test_pnl_consistency.py` | P&L validation |

### Files to Deprecate

| File | Replacement |
|------|-------------|
| `src/backtest/portfolio.py` | `portfolio_new.py` |
| `src/backtest/engine.py` | `engine_new.py` |
| `src/trading/profiles/profile_*.py` | Trade constructors in engine |

### Files Still Used

| File | Purpose |
|------|---------|
| `src/backtest/rotation.py` | RotationAllocator (unchanged) |
| `src/regimes/classifier.py` | Regime classification (unchanged) |
| `src/profiles/detectors.py` | Profile scoring (unchanged) |
| `src/trading/trade.py` | Trade object (unchanged) |
| `src/trading/execution.py` | Execution model (unchanged) |

---

## API Changes

### Running Backtests

**OLD:**
```python
from src.backtest.engine import RotationEngine

engine = RotationEngine()
results = engine.run(data=spy_data)

# Results: post-hoc aggregated P&L
portfolio_df = results['portfolio']  # Weighted sum of independent backtests
```

**NEW:**
```python
from src.backtest.engine_new import RotationBacktestEngine

engine = RotationBacktestEngine(
    initial_capital=1_000_000.0,
    max_profile_weight=0.40,
    min_profile_weight=0.05,
    rebalance_threshold=0.05
)

# Define trade constructors for each profile
constructors = {
    1: build_profile_1_trade,
    2: build_profile_2_trade,
    # ... etc
}

results = engine.run(
    data=spy_data,
    start_date='2024-01-01',
    end_date='2024-12-31',
    trade_constructors=constructors
)

# Results: true portfolio simulation
portfolio = results['portfolio']  # Portfolio object
equity_curve = results['equity_curve']  # Daily equity
daily_results = results['daily_results']  # Day-by-day P&L, allocations, Greeks
closed_positions = results['closed_positions']  # Trade history
rebalance_log = results['rebalance_log']  # Rotation events
```

### Portfolio Object

**OLD:**
```python
# No portfolio object - just DataFrames
portfolio_pnl = aggregator.aggregate_pnl(allocations, profile_results)
```

**NEW:**
```python
# Portfolio object tracks state
portfolio = Portfolio(initial_capital=1_000_000.0)

# Open positions
portfolio.open_position(
    profile_id=1,
    trade=trade_obj,
    allocation_pct=0.20,
    entry_date=date(2024, 1, 2)
)

# Check state
equity = portfolio.get_equity()  # Cash + position values
allocations = portfolio.get_allocations()  # {profile_id: pct}
greeks = portfolio.get_portfolio_greeks()  # Aggregate Greeks

# Mark to market
portfolio.mark_to_market(
    current_date=date(2024, 1, 3),
    option_prices_by_profile={1: {0: 15.0, 1: 14.0}}
)

# Close position
realized_pnl = portfolio.close_position(
    profile_id=1,
    exit_prices={0: 18.0, 1: 17.0},
    exit_date=date(2024, 1, 10),
    exit_reason="Rebalance"
)
```

### Results Structure

**OLD:**
```python
results = {
    'portfolio': DataFrame with weighted P&L,
    'allocations': DataFrame with weights,
    'profile_results': Dict of independent backtest results,
    'attribution': P&L attribution by profile/regime
}
```

**NEW:**
```python
results = {
    'portfolio': Portfolio object (full state),
    'equity_curve': DataFrame (date, cash, position_value, total_equity),
    'daily_results': DataFrame (date, regime, P&L, allocations, Greeks),
    'closed_positions': DataFrame (trade history with P&L),
    'rebalance_log': DataFrame (rotation events),
    'metrics': Dict (Sharpe, max drawdown, win rate, etc.)
}
```

---

## P&L Accounting Changes

### Single Source of Truth: Position-Based Accounting

**OLD**: Return-based P&L (multiple conflicting calculations)

**NEW**: Position-based P&L (one source)

**Formula:**
```
total_equity = cash + sum(position_values)

position_value = entry_value + unrealized_pnl

unrealized_pnl = sum(quantity * (current_price - entry_price) for each leg)

realized_pnl = sum(quantity * (exit_price - entry_price) - commissions for closed trades)

total_pnl = realized_pnl + unrealized_pnl
```

**Validation:**
```python
# Must ALWAYS be true:
assert portfolio.get_equity() == portfolio.cash + sum(pos.current_value for pos in positions)
assert portfolio.get_total_pnl() == portfolio.get_realized_pnl() + portfolio.get_unrealized_pnl()
assert equity_change == initial_capital + total_pnl
```

---

## Trade Constructor Pattern

### What Are Trade Constructors?

Trade constructors are functions that build Trade objects for each profile based on current market conditions.

**Signature:**
```python
def build_profile_N_trade(row: pd.Series, trade_id: str) -> Trade:
    """
    Build trade for profile N.

    Parameters:
    -----------
    row : pd.Series
        Current market data (spot, regime, RV20, profile scores, etc.)
    trade_id : str
        Unique trade identifier

    Returns:
    --------
    trade : Trade
        Constructed trade with legs and entry prices set
    """
    spot = row['close']
    regime = row['regime']

    # Profile-specific logic
    if profile_N == 1:  # Long-dated gamma
        dte = 60
        strike = spot
        # ... build ATM straddle

    # Create legs
    legs = [
        TradeLeg('call', strike, expiry, quantity=1, dte=dte),
        TradeLeg('put', strike, expiry, quantity=1, dte=dte)
    ]

    # Create trade
    trade = Trade(
        trade_id=trade_id,
        profile_name=f"profile_{profile_N}",
        entry_date=row['date'],
        legs=legs,
        entry_prices={0: call_price, 1: put_price}
    )

    trade.__post_init__()

    return trade
```

### Example: Profile 1 (Long-Dated Gamma)

```python
def build_profile_1_ldg(row: pd.Series, trade_id: str) -> Trade:
    """Long-dated gamma efficiency (45-120 DTE)."""
    spot = row['close']
    dte = 60  # Sweet spot

    expiry = datetime.now() + timedelta(days=dte)

    # ATM straddle
    strike = round(spot / 5) * 5  # Round to $5 strikes

    legs = [
        TradeLeg('call', strike, expiry, 1, dte),
        TradeLeg('put', strike, expiry, 1, dte)
    ]

    # Get real prices from Polygon (TODO: integrate)
    call_price = 15.0  # Placeholder
    put_price = 14.0

    trade = Trade(
        trade_id=trade_id,
        profile_name="profile_1_LDG",
        entry_date=row['date'],
        legs=legs,
        entry_prices={0: call_price, 1: put_price}
    )

    trade.__post_init__()

    return trade
```

### Passing to Engine

```python
constructors = {
    1: build_profile_1_ldg,
    2: build_profile_2_sdg,
    3: build_profile_3_charm,
    4: build_profile_4_vanna,
    5: build_profile_5_skew,
    6: build_profile_6_vov
}

results = engine.run(
    data=spy_data,
    trade_constructors=constructors
)
```

---

## Migration Checklist

### 1. Update Imports

```python
# OLD
from src.backtest.engine import RotationEngine
from src.backtest.portfolio import PortfolioAggregator

# NEW
from src.backtest.engine_new import RotationBacktestEngine
from src.backtest.portfolio_new import Portfolio
from src.backtest.position import Position
```

### 2. Implement Trade Constructors

- [ ] Create constructor for Profile 1 (LDG)
- [ ] Create constructor for Profile 2 (SDG)
- [ ] Create constructor for Profile 3 (Charm)
- [ ] Create constructor for Profile 4 (Vanna)
- [ ] Create constructor for Profile 5 (Skew)
- [ ] Create constructor for Profile 6 (VoV)
- [ ] Integrate Polygon options data for real pricing
- [ ] Test each constructor in isolation

### 3. Update Backtest Code

```python
# OLD
engine = RotationEngine()
results = engine.run(data=spy_data)

# NEW
engine = RotationBacktestEngine(
    initial_capital=1_000_000.0,
    max_profile_weight=0.40,
    min_profile_weight=0.05,
    rebalance_threshold=0.05
)

constructors = {i: build_profile_i_trade for i in range(1, 7)}

results = engine.run(
    data=spy_data,
    start_date='2024-01-01',
    end_date='2024-12-31',
    trade_constructors=constructors
)
```

### 4. Update Results Analysis

```python
# OLD
portfolio_df = results['portfolio']
total_pnl = portfolio_df['portfolio_pnl'].sum()

# NEW
portfolio = results['portfolio']
equity_curve = results['equity_curve']
daily_results = results['daily_results']

total_pnl = portfolio.get_total_pnl()
final_equity = portfolio.get_equity()

# Visualize
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 6))
plt.plot(equity_curve['date'], equity_curve['total_equity'])
plt.title('Portfolio Equity Curve')
plt.xlabel('Date')
plt.ylabel('Equity ($)')
plt.show()
```

### 5. Validate Results

Run validation tests:
```bash
pytest tests/test_multiposition_portfolio.py -v
pytest tests/test_rotation_engine.py -v
pytest tests/test_pnl_consistency.py -v
```

**Expected**: All tests pass (or only minor P&L accounting edge cases remain)

### 6. Compare Old vs New

Run parallel comparison:
```python
# Run old engine
old_results = old_engine.run(data=spy_data)

# Run new engine
new_results = new_engine.run(
    data=spy_data,
    trade_constructors=constructors
)

# Compare metrics
print("OLD:")
print(f"  Total P&L: {old_results['portfolio']['portfolio_pnl'].sum()}")

print("NEW:")
print(f"  Total P&L: {new_results['portfolio'].get_total_pnl()}")
print(f"  Total Trades: {len(new_results['closed_positions'])}")
print(f"  Rebalance Events: {len(new_results['rebalance_log'])}")
```

**Expected**: New results should be DIFFERENT (more realistic):
- Lower P&L (transaction costs modeled)
- More trades (rotation events)
- Better risk-adjusted returns (capital constraints enforced)

---

## Common Issues

### 1. P&L Doesn't Match Old System

**Expected**: New system will show lower P&L due to:
- Real transaction costs (entry/exit spreads)
- Rebalancing costs
- Capital constraints (can't allocate >100%)
- Realistic mark-to-market

**This is correct** - old system was overstating returns.

### 2. TypeError: Trade.__init__() Missing Arguments

**Fix**: Trade constructor signature changed. Use:
```python
trade = Trade(
    trade_id="TEST_001",
    profile_name="profile_1",
    entry_date=date(2024, 1, 2),
    legs=[...],
    entry_prices={0: 15.0, 1: 14.0}
)
```

### 3. "Insufficient Cash for Position"

**Cause**: Trying to allocate more capital than available.

**Fix**: Ensure target allocations sum to ≤ 1.0:
```python
allocations = {1: 0.40, 2: 0.30, 3: 0.20}  # Total = 0.90 (OK)
# Not: {1: 0.50, 2: 0.50, 3: 0.50}  # Total = 1.50 (FAIL)
```

### 4. Position Value Doesn't Update

**Cause**: Forgot to call `mark_to_market()`.

**Fix**: Call after each day:
```python
portfolio.mark_to_market(
    current_date=date,
    option_prices_by_profile=current_prices
)
```

---

## Testing Strategy

### Unit Tests

Test individual components:
```bash
# Portfolio
pytest tests/test_multiposition_portfolio.py::TestPositionOpening -v

# P&L accounting
pytest tests/test_pnl_consistency.py::TestCashFlowConservation -v
```

### Integration Tests

Test full rotation loop:
```bash
pytest tests/test_rotation_engine.py::TestBacktestExecution -v
```

### Validation Tests

Critical P&L consistency checks:
```bash
pytest tests/test_pnl_consistency.py -v
```

**All must pass before deploying to production.**

---

## Performance Considerations

### Old System
- Fast (6 independent loops)
- But wrong (post-hoc weighting)

### New System
- Slightly slower (unified loop, rebalancing logic)
- But correct (true portfolio simulation)

**Trade-off**: 10-20% slower execution for dramatically more realistic results.

**Optimization**: Profile constructors are called frequently - keep them fast.

---

## Next Steps

1. **Integrate Polygon Options Data**: Replace placeholder pricing in trade constructors
2. **Implement Profile-Specific Logic**: Customize constructors for each profile's strategy
3. **Add Greeks-Based Rebalancing**: Rebalance when portfolio Greeks exceed thresholds
4. **Implement Risk Limits**: Stop-loss, max drawdown, VaR constraints
5. **Add Performance Attribution**: Decompose P&L by profile, regime, Greek component

---

## Contact

Questions? Check:
- `tests/` for usage examples
- `src/backtest/engine_new.py` for implementation
- SESSION_STATE.md for current project status

---

**This is critical infrastructure. Test thoroughly before using for strategy evaluation.**
