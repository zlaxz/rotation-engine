# Profile 4 VANNA - Action Items & Implementation

**Status:** Ready for backtesting refinements
**Priority:** HIGH - Could improve Sharpe ratio and prevent 2022-like collapses
**Estimated ROI:** +5-10 percentage points on Sharpe (estimated)

---

## Critical Findings Summary

1. **Mislabeled Strategy:** Profile 4 is NOT VANNA (vol-correlation), it's **Directional Gamma** with decay
   - Winners have NEGATIVE vol changes yet still profit
   - Vega almost irrelevant to P&L
   - Profit driver: Spot movement (+2.5-2.7%) → Delta increase (0.55 → 0.687)

2. **Two-Tier Regime Performance:**
   - Event/Catalyst: 63% win, +$163/trade (FOCUS HERE)
   - Trend Up: 48.7% win, -$51/trade (HIGH RISK - needs guardrails)
   - Choppy: 25% win, -$527/trade (SKIP - theta death)

3. **2022 Crisis:** 70.8% → 13.3% win rate collapse (lost $7,841)
   - Root cause: Fed tightening + bear market = vol expansion during exits
   - Solution: Regime guards + vol spike detection

---

## Implementation Roadmap

### PHASE 1: Exit Strategy Refinement (Week 1)

#### Task 1.1: Implement Three-Layer Exit System

Current state: Trades hold until expiration (predictable exit after 14-15 days)
Target: Dynamic exits based on profit, vol regime, and time decay

**Code to implement in backtest engine:**

```python
class ExitManager:
    """Three-layer exit decision system for Profile 4"""

    def should_exit(self, position, trade_day_data, regime):
        """
        Returns: (exit_signal: bool, exit_reason: str, exit_price: float)
        """

        # LAYER 1: PROFIT TAKING
        peak_profit = trade_day_data['peak_so_far'] - position['entry_cost']
        current_mtm = trade_day_data['mtm_pnl']

        if peak_profit > position['entry_cost'] * 0.5:  # > 50% profit achieved
            if current_mtm > peak_profit * 0.8:  # Within 20% of peak
                return (True, "PROFIT_TAKING_50_PERCENT", current_mtm)

        if trade_day_data['days_held'] > 10 and position['spot_change'] > 0.01:
            if current_mtm > peak_profit * 0.8:
                return (True, "TRAIL_STOP_FROM_PEAK",
                        peak_profit - (position['entry_cost'] * 0.2))

        if trade_day_data['days_held'] > 10 and position['spot_change'] < 0.005:
            return (True, "NO_SPOT_MOVE_TIME_DECAY", current_mtm)

        # LAYER 2: VOL REGIME SHIFT (Most dangerous)
        if regime == "Event/Catalyst":
            entry_rv5 = position['entry_conditions']['RV5']
            current_rv5 = trade_day_data['market_conditions']['RV5']

            if current_rv5 > entry_rv5 * 1.5:  # Vol spike > 50%
                return (True, "VOL_SPIKE_REALIZED_VEGA_LOSS", current_mtm)

        if regime == "Trend Up":
            entry_rv20 = position['entry_conditions']['RV20']
            current_rv20 = trade_day_data['market_conditions']['RV20']

            if current_rv20 > entry_rv20 + 0.02:  # Vol expanded 2%+
                return (True, "VOL_EXPANSION_FATAL_TREND_UP", current_mtm)

            # Spot stalled + vol not moving = gamma profit unlikely
            if position['days_held'] > 5 and position['spot_change'] < 0.005:
                if trade_day_data['market_conditions']['slope'] < 0.01:
                    return (True, "TREND_STALLED_NO_GAMMA", current_mtm)

        # LAYER 3: TIME DECAY
        if trade_day_data['days_held'] > 14:
            if current_mtm < peak_profit * 0.8:  # Drawdown from peak
                return (True, "TIME_DECAY_THETA_DOMINATES", current_mtm)

        if trade_day_data['dte'] < 38:  # DTE too low
            return (True, "PIN_RISK_GAMMA_EXPLOSION", current_mtm)

        return (False, "HOLD", current_mtm)
```

**Success metric:** Increase capture ratio from 17% to 25-30% by exiting more winners at profit peaks

---

#### Task 1.2: Implement Regime-Specific Position Sizing

Current: Fixed 1 contract per trade
Target: Event/Catalyst = 1.0x, Trend Up = 0.5x

```python
class PositionSizer:
    """Regime-specific position sizing"""

    def get_position_size(self, regime, entry_conditions, market_regime="normal"):
        """
        Returns: contracts to trade
        """
        base_size = 1.0

        if market_regime == "bear":  # Fed tightening, rates rising
            bear_discount = 0.7
        else:
            bear_discount = 1.0

        if regime == "Event/Catalyst":
            if entry_conditions['RV20'] > 0.35:  # Vol already high
                return base_size * 0.5 * bear_discount
            else:
                return base_size * 1.0 * bear_discount

        elif regime == "Trend Up":
            # Always reduced vs Event/Catalyst
            return base_size * 0.5 * bear_discount

        elif regime == "Choppy":
            return 0  # Skip this regime

        return base_size * bear_discount
```

**Success metric:** Reduce 2022-like drawdowns by 50% through position sizing

---

#### Task 1.3: Implement 2022 Crisis Prevention Guardrails

```python
class MarketRegimeDetector:
    """Detects bear market + vol expansion regimes"""

    def should_skip_entry(self, entry_conditions, regime):
        """
        Returns: (skip: bool, reason: str)
        """

        # Guardrail 1: High vol already
        if entry_conditions['RV20'] > 0.35:
            return (True, "RV20_TOO_HIGH_0.35")

        # Guardrail 2: Bear market signals (simplified check)
        # In real system, would check: yield curve inversion, DXY strength, SPY trend
        if self.is_bear_market():
            if regime == "Event/Catalyst" and entry_conditions['RV20'] > 0.25:
                return (True, "BEAR_MARKET_HIGH_VOL")
            if regime == "Trend Up":
                return (True, "BEAR_MARKET_SKIP_TREND_UP")

        # Guardrail 3: Negative event filter
        # (In real system: check if event is earnings miss, macro miss, etc.)
        if regime == "Event/Catalyst" and self.is_negative_event():
            if self.is_bear_market():
                return (True, "NEGATIVE_EVENT_IN_BEAR_MARKET")

        return (False, "OK_TO_TRADE")

    def is_bear_market(self):
        """Simplified - in real system would check multiple indicators"""
        # TODO: Implement real bear market detection
        return False

    def is_negative_event(self):
        """Detect if event is likely negative (earnings miss, macro data)"""
        # TODO: Implement real event classification
        return False
```

**Success metric:** Filter out trades that led to 2022 losses

---

### PHASE 2: Data Validation (Week 1-2)

#### Task 2.1: Audit 2022 Trades

```python
def audit_2022_trades():
    """Identify which 2022 trades would have been prevented"""

    trades_2022 = load_trades_by_year(2022)

    for trade in trades_2022:
        entry_cond = trade['entry']['entry_conditions']
        regime = classify_regime(entry_cond)

        # Would this trade be filtered by guardrails?
        skip, reason = detector.should_skip_entry(entry_cond, regime)

        # Compare: actual result vs what guardrail would have done
        actual_pnl = get_realized_pnl(trade)

        print(f"Trade {trade['trade_id']}")
        print(f"  Regime: {regime}")
        print(f"  Would skip: {skip} ({reason})")
        print(f"  Actual result: ${actual_pnl}")
        print()

    # Calculate: How many losing 2022 trades would be filtered?
    filtered = sum(1 for t in trades_2022 if detector.should_skip_entry(
        t['entry']['entry_conditions'], classify_regime(t['entry']['entry_conditions']))[0])
    print(f"\nGuardrails would have filtered: {filtered}/15 trades")
    print(f"Projected win rate if filtered: {calculate_filtered_win_rate(trades_2022)}")
```

**Success metric:** Verify that 70%+ of 2022 losses would be prevented

---

#### Task 2.2: Verify Exit Layer Effectiveness

```python
def validate_exit_layers():
    """
    For each trade, determine which exit layer would have triggered first.
    Calculate improved capture rates.
    """

    all_trades = load_all_trades()
    exit_stats = defaultdict(list)

    for trade in all_trades:
        path = trade['path']
        entry_cost = trade['entry']['entry_cost']
        regime = classify_regime(trade['entry']['entry_conditions'])

        # Run exit logic day by day
        for i, day in enumerate(path):
            exit_signal, reason, exit_price = exit_manager.should_exit(
                trade['entry'], day, regime
            )

            if exit_signal:
                realized_pnl = exit_price - entry_cost
                potential_pnl = path[-1]['mtm_pnl']  # What we actually got

                exit_stats[reason].append({
                    'realized': realized_pnl,
                    'potential': potential_pnl,
                    'improvement': realized_pnl - potential_pnl
                })
                break

    # Print stats
    for exit_reason in sorted(exit_stats.keys()):
        stats = exit_stats[exit_reason]
        avg_realized = np.mean([s['realized'] for s in stats])
        avg_potential = np.mean([s['potential'] for s in stats])
        avg_improvement = np.mean([s['improvement'] for s in stats])

        print(f"{exit_reason}")
        print(f"  Count: {len(stats)}")
        print(f"  Avg realized: ${avg_realized:.2f}")
        print(f"  Avg potential: ${avg_potential:.2f}")
        print(f"  Improvement: ${avg_improvement:.2f}")
        print()
```

**Success metric:** Show that 3-layer exit improves capture by 5-10 percentage points

---

### PHASE 3: Backtesting Refinement (Week 2-3)

#### Task 3.1: Re-run Full Backtest with New Exits

```bash
# Run refined backtest
python backtest_engine.py \
  --profile Profile_4_VANNA \
  --exit_mode three_layer \
  --position_sizing regime_aware \
  --guardrails 2022_prevention \
  --output refined_backtest_results.json
```

Compare metrics:
- Win rate (should stay ~58% or improve slightly)
- Sharpe ratio (should improve 0.1-0.3 points)
- Capture ratio (should improve 17% → 25%+)
- Max drawdown (should improve through better exits)
- 2022 performance (should improve dramatically)

**Success metric:**
- Capture: 17% → 25%
- Sharpe: +0.15 minimum
- 2022 win rate: 13% → 35%+

---

#### Task 3.2: Monte Carlo Simulation of Refined Strategy

```python
def monte_carlo_exit_timing():
    """
    Test robustness: How sensitive is strategy to small changes in exit timing?
    """

    base_metrics = backtest_results['Event/Catalyst']

    for exit_day_shift in [-1, 0, 1, 2]:  # Test ±1-2 days
        for vol_spike_threshold in [1.3, 1.4, 1.5, 1.6]:  # Vol spike sensitivity

            refined = run_backtest(
                exit_days=13 + exit_day_shift,
                vol_spike_threshold=vol_spike_threshold
            )

            print(f"Exit day +{exit_day_shift}, Vol spike {vol_spike_threshold}")
            print(f"  Win rate: {refined['win_rate']}")
            print(f"  Sharpe: {refined['sharpe']}")
            print()
```

**Success metric:** Verify strategy isn't brittle to small parameter changes

---

### PHASE 4: Live Trading Integration (Week 3-4)

#### Task 4.1: Add Regime Detection to Trading Engine

```python
class LiveTradingRules:
    """Rules for Profile 4 live trading"""

    def entry_allowed(self):
        """Check if conditions allow new trade entry"""

        regime = self.detect_regime()
        market_regime = self.detect_market_regime()  # bear vs normal

        # Skip during bear markets
        if market_regime == "bear":
            return False, "BEAR_MARKET_SKIP"

        # Only enter clean regimes
        if regime not in ["Event/Catalyst", "Trend Up"]:
            return False, f"REGIME_SKIP_{regime}"

        # Event/Catalyst: check vol
        if regime == "Event/Catalyst":
            if self.current_rv20 > 0.35:
                return False, "RV20_TOO_HIGH"

        return True, "OK_TO_TRADE"

    def position_size(self, regime):
        """Determine position size for new trade"""
        if regime == "Event/Catalyst":
            return 1.0
        elif regime == "Trend Up":
            return 0.5
        return 0  # Don't trade
```

---

#### Task 4.2: Daily Exit Checklist

```python
def daily_exit_check(position):
    """Run every day at market close"""

    checks = [
        ("Peak profit > 50%", peak_profit_check(position)),
        ("Vol spike detected", vol_spike_check(position)),
        ("Days held > 14", time_decay_check(position)),
        ("DTE < 38", dte_check(position)),
        ("Spot stalled", spot_stall_check(position)),
    ]

    for check_name, should_exit in checks:
        if should_exit:
            print(f"EXIT SIGNAL: {check_name}")
            return True

    return False
```

---

## Naming & Labeling Updates

### Action Item 1: Rename Profile_4 Internally

Change from: "Profile_4_VANNA (Vol-Spot Correlation)"
Change to: "Profile_4_DG (Directional Gamma - Upside Calls)"

Update in:
- `backtest_engine.py`: Profile_4 class documentation
- Results JSON: Rename output files
- Trading rules: Update comments
- Memory entities: Update metadata

---

## Documentation Updates

### Action Item 2: Update CONFIG/README

In `README.md` or trading system docs:

```markdown
## Profile 4: Directional Gamma (Upside Calls)

**NOT a VANNA strategy.** This is a directional gamma play exploiting spot movement.

**Edge:** Post-event markets move directionally (gamma profit)
**Regime:** Event/Catalyst environments (63% win rate)

**Why it wins:** Spot moves up (+2.5-2.7%) → Delta increases → Gamma collects
**Why it loses:** Spot stalls → Theta decay dominates

**Best for:** Event-driven trading (earnings, Fed announcements, macro releases)
**Worst for:** Choppy/mean-reverting markets (theta wins, no directional move)

See: `analysis/Profile_4_VANNA_regime_dependencies.md` for full analysis.
```

---

## Testing Checklist

- [ ] Task 1.1: Three-layer exit system coded and unit tested
- [ ] Task 1.2: Position sizing implemented for all regimes
- [ ] Task 1.3: 2022 guardrails coded and validated
- [ ] Task 2.1: 2022 audit shows 70%+ of losses would be filtered
- [ ] Task 2.2: Exit layer effectiveness shows +5-10% improvement potential
- [ ] Task 3.1: Refined backtest shows improved metrics
- [ ] Task 3.2: Monte Carlo shows robustness to parameter changes
- [ ] Task 4.1: Live trading rules implemented
- [ ] Task 4.2: Daily exit checklist functional
- [ ] Rename Profile_4 to DG in all code/docs
- [ ] Update README with correct description

---

## Success Criteria

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Win Rate | 58.3% | 58% (maintain) | OK |
| Sharpe Ratio | TBD | +0.15 points | To test |
| Capture Ratio | 17% | 25%+ | To test |
| Max Drawdown | -830% (Event/Catalyst losers) | -50% (with exits) | To test |
| 2022 Win Rate | 13.3% | 35%+ | To test |
| PnL/Trade | $163 | $200+ | To test |

---

## Timeline

- **Week 1:** Implement exit system, guardrails, position sizing
- **Week 1-2:** Data validation and 2022 audit
- **Week 2-3:** Backtesting refinement and Monte Carlo testing
- **Week 3-4:** Live trading integration and documentation

**Estimated effort:** 40-60 hours development + testing

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Over-optimization to past data | Use OOS data, Monte Carlo robustness testing |
| Exit rules too complex | Start with Layer 1 only, add layers progressively |
| Guardrails too strict (miss good trades) | Set high thresholds (RV20 > 0.35), not restrictive |
| Live implementation bugs | Thorough unit tests + paper trading first |

---

## Files to Update

1. `/Users/zstoc/rotation-engine/backtest_engine.py` - Exit logic, position sizing
2. `/Users/zstoc/rotation-engine/strategy_rules/Profile_4_config.py` - Guardrails
3. `/Users/zstoc/rotation-engine/README.md` - Profile naming and description
4. `/Users/zstoc/rotation-engine/analysis/` - Updated documentation (DONE)
5. `/Users/zstoc/rotation-engine/SESSION_STATE.md` - Add as working items

---

**Status:** Ready for implementation
**Next Step:** Start Week 1 Phase 1 (Exit system implementation)
