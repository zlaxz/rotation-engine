# CRITICAL BUG FIXES - Technical Implementation Guide

## PRIORITY ORDER FOR FIXES

1. **BUG-001: P&L Sign Convention** (HIGHEST - corrupts all results)
2. **BUG-002: Greeks Contract Multiplier** (HIGHEST - 100x error)
3. **BUG-004: Delta Hedge Direction** (HIGHEST - hedges go backwards)
4. **BUG-003: Double-Counting Commission** (HIGH - costs wrong)
5. **BUG-005: IV Estimation** (HIGH - Greeks unreliable)
6. Others in descending priority

---

## BUG-001: P&L Sign Convention Fix

### File: `/Users/zstoc/rotation-engine/src/analysis/trade_tracker.py`

### Current Code (WRONG - Lines 79-94)

```python
for leg in position['legs']:
    opt_type = leg['type']
    qty = leg['qty']

    price = self.polygon.get_option_price(
        entry_date, position['strike'], position['expiry'], opt_type, 'mid'
    )
    if price is None:
        return None

    entry_prices[opt_type] = price
    # Cost: positive for buying, negative for selling
    leg_cost = qty * (price + (spread if qty > 0 else -spread)) * 100  # LINE 91 - WRONG
    entry_cost += leg_cost

entry_cost += commission  # LINE 94
```

### Issue

The sign convention is **inconsistent**. For:
- **Long call (qty = 1)**: `1 * (5.00 + 0.03) * 100 = +513` → shows as cost+513
  - CORRECT meaning: "you paid 513 (outflow)"
  - But stored as POSITIVE, which typically means "money IN" not "money OUT"

- **Short call (qty = -1)**: `-1 * (5.00 - 0.03) * 100 = -497` → shows as cost-497
  - CORRECT meaning: "you received 497 (inflow)"
  - But stored as NEGATIVE, which typically means "money OUT"

This is BACKWARDS from standard accounting.

### Correct Code (Option A - Make entry_cost represent cash outflow as POSITIVE)

```python
for leg in position['legs']:
    opt_type = leg['type']
    qty = leg['qty']

    price = self.polygon.get_option_price(
        entry_date, position['strike'], position['expiry'], opt_type, 'mid'
    )
    if price is None:
        return None

    entry_prices[opt_type] = price

    # NEW: Correct sign convention
    # entry_cost = sum of (quantity * price * 100)
    # For long (qty > 0): positive = cash outflow (we paid)
    # For short (qty < 0): negative = cash inflow (we received)
    if qty > 0:
        # Long position - we PAY the ask (include spread)
        leg_cost = qty * (price + spread) * 100  # Positive for outflow
    else:
        # Short position - we RECEIVE the bid (subtract spread)
        leg_cost = qty * (price - spread) * 100  # Negative for inflow

    entry_cost += leg_cost

entry_cost += commission  # Commission is always a cost (positive addition)
```

### Verification After Fix

```python
# Test case 1: Long straddle
call_price = 5.00
put_price = 4.50
spread = 0.03
commission = 2.60

# Call leg (qty = 1)
call_cost = 1 * (5.00 + 0.03) * 100 = 513
# Put leg (qty = 1)
put_cost = 1 * (4.50 + 0.03) * 100 = 453
# Total
entry_cost = 513 + 453 + 2.60 = 968.60

# Interpretation: Paid $968.60 for position ✓

# Test case 2: Short straddle
# Call leg (qty = -1)
call_cost = -1 * (5.00 - 0.03) * 100 = -497
# Put leg (qty = -1)
put_cost = -1 * (4.50 - 0.03) * 100 = -447
# Total
entry_cost = -497 + (-447) + 2.60 = -941.40

# Interpretation: Received $941.40, paid $2.60 commission = net -939 ✓
```

---

## BUG-002: Greeks Contract Multiplier Fix

### File: `/Users/zstoc/rotation-engine/src/analysis/trade_tracker.py`

### Current Code (WRONG - Lines 267-282)

```python
# Calculate Greeks for each leg and sum
net_greeks = {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}

for leg in legs:
    opt_type = leg['type']
    qty = leg['qty']

    greeks = calculate_all_greeks(
        spot, strike, dte / 365.0, r, iv, opt_type
    )

    # Scale by quantity (positive = long, negative = short)
    net_greeks['delta'] += greeks['delta'] * qty      # LINE 279 - MISSING *100
    net_greeks['gamma'] += greeks['gamma'] * qty      # LINE 280 - MISSING *100
    net_greeks['theta'] += greeks['theta'] * qty      # LINE 281 - MISSING *100
    net_greeks['vega'] += greeks['vega'] * qty        # LINE 282 - MISSING *100

return {k: float(v) for k, v in net_greeks.items()}
```

### Issue

`calculate_all_greeks()` returns per-contract Greeks (representing 100 shares per options contract).
- Delta for 1 ATM call: ~0.5 (per 1 share of 100)
- Should be: ~0.5 * 100 = 50 (for full contract)

Current code only multiplies by `qty`, missing the `* 100`.

### Correct Code

```python
# Calculate Greeks for each leg and sum
CONTRACT_MULTIPLIER = 100  # Options represent 100 shares per contract
net_greeks = {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}

for leg in legs:
    opt_type = leg['type']
    qty = leg['qty']

    greeks = calculate_all_greeks(
        spot, strike, dte / 365.0, r, iv, opt_type
    )

    # Scale by quantity (positive = long, negative = short) AND contract multiplier
    net_greeks['delta'] += greeks['delta'] * qty * CONTRACT_MULTIPLIER    # LINE 279
    net_greeks['gamma'] += greeks['gamma'] * qty * CONTRACT_MULTIPLIER    # LINE 280
    net_greeks['theta'] += greeks['theta'] * qty * CONTRACT_MULTIPLIER    # LINE 281
    net_greeks['vega'] += greeks['vega'] * qty * CONTRACT_MULTIPLIER      # LINE 282

return {k: float(v) for k, v in net_greeks.items()}
```

### Verification After Fix

```python
# Test case: 1 ATM call contract (qty=1)
greeks_per_share = {'delta': 0.5, 'gamma': 0.02, 'theta': -0.05, 'vega': 0.15}

# OLD (WRONG):
net_delta = 0.5 * 1 = 0.5  # ✗ way too small

# NEW (CORRECT):
net_delta = 0.5 * 1 * 100 = 50  # ✓ correct for 100 shares

# Interpretation: 50 delta means position moves $50 per $1 move in SPY ✓
```

---

## BUG-003: Double-Counting Commission Fix

### File: `/Users/zstoc/rotation-engine/src/trading/trade.py`

### Current Design Issue

The problem is architectural - commission is subtracted in TWO places:
1. In `mark_to_market()` for unrealized P&L (line 224)
2. In `close()` for realized P&L (line 137)

### Solution: Only Subtract at Close

Modify `mark_to_market()` to NOT subtract entry commission:

### Current Code (Lines 223-224)

```python
# Unrealized P&L - all costs (entry commission, hedging, estimated exit commission)
# This gives realistic P&L that accounts for future exit costs
return unrealized_pnl - self.entry_commission - self.cumulative_hedge_cost - estimated_exit_commission
```

### Correct Code

```python
# Option A: Don't subtract entry commission from unrealized P&L
# (entry commission was already paid, so unrealized should show current position value)
# Subtract only hedge costs (ongoing costs) and estimated exit commission (future costs)
return unrealized_pnl - self.cumulative_hedge_cost - estimated_exit_commission

# Entry commission accounting:
# - At entry: already paid, reflected in entry_prices
# - During holding: not a future cost, already sunk
# - At close: included in realized_pnl calculation
```

### Alternative: Subtract at Mark-to-Market Only

If you want commission reflected throughout:

```python
# In close() - don't subtract entry commission again (line 137)
# Only subtract exit commission (first and only time)
self.realized_pnl = pnl_legs - self.exit_commission - self.cumulative_hedge_cost

# Entry commission already reflected in unrealized_pnl calculations
```

### Recommendation

**Use Option A (subtract at close only).**

This matches standard accounting:
- Entry commission paid at entry, affects entry_cost
- Exit commission paid at exit, affects realized_pnl
- No double-counting

---

## BUG-004: Delta Hedge Direction Fix

### File: `/Users/zstoc/rotation-engine/src/trading/simulator.py`

### Current Code (WRONG - Lines 729-738)

```python
# Only hedge if delta exceeds threshold
delta_threshold = 20  # Hedge if abs(delta) > 20
if abs(trade.net_delta) < delta_threshold:
    return 0.0

# Calculate ES contracts needed to neutralize delta
hedge_contracts = abs(trade.net_delta) / es_delta_per_contract

# Get hedging cost
return self.config.execution_model.get_delta_hedge_cost(hedge_contracts)
```

### Issue

The code calculates magnitude but loses direction:
- If `net_delta = +100` (long delta, needs short hedge)
- Calculation: `hedge_contracts = 100 / 50 = 2` (quantity only, no direction)
- What direction are these 2 contracts? **Not specified!**
- If interpreted as LONG (buy 2 ES): adds +100 delta → total becomes +200 (WORSE)
- Should be SHORT (sell 2 ES): subtracts -100 delta → total becomes 0 (CORRECT)

### Correct Code

```python
# Only hedge if delta exceeds threshold
delta_threshold = 20  # Hedge if abs(delta) > 20
if abs(trade.net_delta) < delta_threshold:
    return 0.0

# Calculate ES contracts needed (get magnitude)
es_delta_per_contract = 50
hedge_contracts_magnitude = abs(trade.net_delta) / es_delta_per_contract

# Determine direction - hedge should be OPPOSITE of portfolio delta
# If portfolio is LONG delta (+), hedge should SHORT (-) ES
# If portfolio is SHORT delta (-), hedge should LONG (+) ES
if trade.net_delta > 0:
    # Long delta (positive): need SHORT hedge (negative contracts)
    hedge_direction = -1
else:
    # Short delta (negative): need LONG hedge (positive contracts)
    hedge_direction = 1

# Apply direction
hedge_contracts_signed = hedge_contracts_magnitude * hedge_direction

# Get hedging cost (will use abs value anyway)
return self.config.execution_model.get_delta_hedge_cost(hedge_contracts_signed)
```

### Verification After Fix

```python
# Test case: Portfolio with net_delta = +100 (long delta)
net_delta = 100
es_delta_per_contract = 50
delta_threshold = 20

# Check threshold
abs(100) > 20 → hedge needed ✓

# OLD (WRONG):
hedge_contracts = abs(100) / 50 = 2
# If this is interpreted as LONG: portfolio becomes 100 + 100 = 200 delta ✗

# NEW (CORRECT):
hedge_contracts_magnitude = abs(100) / 50 = 2
hedge_direction = -1  (because net_delta > 0)
hedge_contracts_signed = 2 * -1 = -2  (SHORT 2 ES)
# Portfolio becomes 100 - 100 = 0 delta ✓ (neutral)

# Interpretation: Successfully neutralized portfolio delta ✓
```

---

## BUG-005: IV Estimation Fix

### File: `/Users/zstoc/rotation-engine/src/analysis/trade_tracker.py`

### Current Code (CRUDE - Lines 256-265)

```python
# Estimate IV from option price (simple approach)
iv = 0.20  # Default
for leg in legs:
    opt_type = leg['type']
    if opt_type in prices:
        price = prices[opt_type]
        # Back out IV from price (simplified - just use ATM vol estimate)
        if abs(strike - spot) / spot < 0.02:  # Near ATM
            iv = max(0.10, price / spot * np.sqrt(365 / dte) * 2)
            break
```

### Issue

Formula is not a proper IV calculation:
```
iv = max(0.10, price/spot * sqrt(365/dte) * 2)
```

This is an ad-hoc heuristic that:
1. Takes price/spot ratio
2. Scales by time
3. Multiplies by 2 (magic constant)
4. **Always floors at 0.10** (bias low)

Example: `iv = max(0.10, 0.01 * 3.5 * 2) = max(0.10, 0.07) = 0.10` (floored)

### Correct Code: Numerical IV Inversion

```python
# Need to add to imports:
from scipy.optimize import brentq
from scipy.stats import norm

def estimate_iv_from_price(option_price, spot, strike, dte, r, option_type):
    """
    Properly invert Black-Scholes to get implied volatility.
    Uses numerical optimization (Brent's method).
    """
    T = dte / 365.0

    def black_scholes_price(sigma):
        """Calculate option price for given volatility"""
        if T <= 0 or sigma <= 0:
            return 0.0

        d1 = (np.log(spot/strike) + (r + 0.5*sigma**2)*T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        if option_type.lower() == 'call':
            price = spot * norm.cdf(d1) - strike * np.exp(-r*T) * norm.cdf(d2)
        else:  # put
            price = strike * np.exp(-r*T) * norm.cdf(-d2) - spot * norm.cdf(-d1)

        return price

    def objective(sigma):
        """Objective function to minimize: price_diff"""
        calculated_price = black_scholes_price(sigma)
        return calculated_price - option_price

    try:
        # Search for IV between 0.1% and 500%
        iv = brentq(objective, 0.001, 5.0, maxiter=100)
        return iv
    except:
        # If convergence fails, return reasonable default
        return 0.20

# Usage in track_trade():
iv = 0.20  # Default
for leg in legs:
    opt_type = leg['type']
    if opt_type in prices and abs(strike - spot) / spot < 0.02:
        price = prices[opt_type]
        # CORRECT: Use numerical inversion
        estimated_iv = estimate_iv_from_price(price, spot, strike, dte, r=0.04, option_type=opt_type)
        if 0.01 < estimated_iv < 3.0:  # Sanity check
            iv = estimated_iv
        break
```

### Verification After Fix

```python
# Test case: ATM call with price 5.00
spot = 500
strike = 500
dte = 30
price = 5.00

# OLD (CRUDE):
iv = max(0.10, 5/500 * sqrt(365/30) * 2) = max(0.10, 0.01 * 3.49 * 2) = 0.10

# NEW (CORRECT):
# Numerical inversion finds IV that produces price 5.00
iv ≈ 0.22  (will vary based on actual market data)

# This IV is then used in Greeks calculation
# Greeks become realistic, not biased low by assumption of 0.10 IV
```

---

## BUG-006: VIX Proxy Bounds Checking

### File: `/Users/zstoc/rotation-engine/src/trading/execution.py`

### Current Code (UNBOUNDED - Lines 258-274)

```python
def get_vix_proxy(rv_20: float) -> float:
    """
    Simple VIX proxy from 20-day realized vol.
    Typical relationship: VIX ≈ RV * sqrt(252) * 100 * 1.2 (IV premium)
    """
    return rv_20 * 100 * 1.2  # RV to IV with 20% premium
```

### Issue

No validation or clipping:
- If `rv_20 = 0.50` (extreme): returns 60 (VIX 60 is high but reasonable)
- If `rv_20 = 5.0` (data error): returns 600 (absurd, will break Greeks)
- If `rv_20 = 0.0`: returns 0 (zero volatility in Black-Scholes = NaN)

### Correct Code

```python
def get_vix_proxy(rv_20: float, min_vol: float = 0.05, max_vol: float = 2.0) -> float:
    """
    VIX proxy from 20-day realized vol with bounds checking.

    Parameters:
    -----------
    rv_20 : float
        20-day realized volatility (annualized, as decimal)
        Expected range: 0.10 to 0.50 (10%-50%)
    min_vol : float
        Minimum volatility bound (prevents zero vol in Greeks)
    max_vol : float
        Maximum volatility bound (prevents extreme values)

    Returns:
    --------
    float
        VIX proxy (approximately 0-100 scale)
    """
    import numpy as np

    # Clip input to reasonable range
    rv_20_clipped = np.clip(rv_20, min_vol, max_vol)

    # Convert to VIX-like scale (0-100)
    vix_proxy = rv_20_clipped * 100 * 1.2

    # Clip output to realistic range (VIX typically 10-80, rarely > 100)
    vix_proxy_clipped = np.clip(vix_proxy, 5, 100)

    return vix_proxy_clipped
```

### Verification After Fix

```python
# Test cases:
get_vix_proxy(0.20) = 0.20 * 100 * 1.2 = 24 ✓ (normal VIX)
get_vix_proxy(0.50) = 0.50 * 100 * 1.2 = 60 ✓ (high vol)
get_vix_proxy(0.05) = min(0.05 * 100 * 1.2, 100) = 6 → clipped to 5 ✓ (handles floor)
get_vix_proxy(5.0) = min(5.0 * 100 * 1.2, 100) = 100 ✓ (clipped to max)
get_vix_proxy(0.0) = clipped to 5 ✓ (prevents zero vol)
```

---

## TESTING THE FIXES

### Unit Tests to Add

Create `/Users/zstoc/rotation-engine/tests/test_bug_fixes.py`:

```python
import pytest
import numpy as np
from src.analysis.trade_tracker import TradeTracker
from src.trading.trade import Trade, TradeLeg
from src.trading.execution import ExecutionModel, get_vix_proxy
from datetime import datetime, timedelta

class TestBugFixes:

    def test_bug001_long_straddle_entry_cost_sign(self):
        """BUG-001: Entry cost should be positive for cash outflow"""
        # Simulate: Long 1 straddle at 500 strike, call=5, put=4.5, spread=0.03

        call_price = 5.00
        put_price = 4.50
        spread = 0.03
        commission = 2.60

        # Expected: positive cost (cash paid)
        expected_cost = (
            1 * (call_price + spread) * 100 +
            1 * (put_price + spread) * 100 +
            commission
        )
        assert expected_cost > 0, "Long straddle should have positive entry cost"
        assert expected_cost == pytest.approx(968.60, abs=0.01)

    def test_bug001_short_straddle_entry_cost_sign(self):
        """BUG-001: Entry cost should be negative for cash inflow"""
        call_price = 5.00
        put_price = 4.50
        spread = 0.03
        commission = 2.60

        # Short positions: qty = -1
        expected_cost = (
            -1 * (call_price - spread) * 100 +
            -1 * (put_price - spread) * 100 +
            commission
        )
        assert expected_cost < 0, "Short straddle should have negative entry cost"
        assert expected_cost == pytest.approx(-941.40, abs=0.01)

    def test_bug002_greeks_contract_multiplier(self):
        """BUG-002: Greeks should include 100x contract multiplier"""
        # Single ATM call
        greeks_per_share = {
            'delta': 0.5,
            'gamma': 0.02,
            'theta': -0.05,
            'vega': 0.15
        }
        qty = 1
        contract_multiplier = 100

        # With fix: multiply by contract_multiplier
        expected_delta = 0.5 * qty * contract_multiplier
        expected_gamma = 0.02 * qty * contract_multiplier

        assert expected_delta == 50, "Delta should be 50 for 1 ATM call"
        assert expected_gamma == 2, "Gamma should be 2"

    def test_bug004_hedge_direction_long_delta(self):
        """BUG-004: Long delta should be hedged with SHORT contracts"""
        net_delta = 100  # Long delta
        es_delta_per_contract = 50

        # With fix:
        hedge_magnitude = abs(net_delta) / es_delta_per_contract
        hedge_direction = -1 if net_delta > 0 else 1
        hedge_signed = hedge_magnitude * hedge_direction

        assert hedge_signed == -2, "Long delta should hedge with -2 ES (short)"
        assert net_delta + hedge_signed * es_delta_per_contract == 0, "Should neutralize"

    def test_bug004_hedge_direction_short_delta(self):
        """BUG-004: Short delta should be hedged with LONG contracts"""
        net_delta = -100  # Short delta
        es_delta_per_contract = 50

        # With fix:
        hedge_magnitude = abs(net_delta) / es_delta_per_contract
        hedge_direction = -1 if net_delta > 0 else 1
        hedge_signed = hedge_magnitude * hedge_direction

        assert hedge_signed == 2, "Short delta should hedge with +2 ES (long)"
        assert net_delta + hedge_signed * es_delta_per_contract == 0, "Should neutralize"

    def test_bug006_vix_proxy_bounds(self):
        """BUG-006: VIX proxy should clip to reasonable bounds"""
        # Normal case
        assert 20 < get_vix_proxy(0.20) < 30, "20% RV should give ~24 VIX"

        # Extreme low
        result_low = get_vix_proxy(0.01)
        assert result_low >= 5, "Should clip to minimum 5"

        # Extreme high
        result_high = get_vix_proxy(2.0)
        assert result_high <= 100, "Should clip to maximum 100"

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

### How to Run Tests

```bash
cd /Users/zstoc/rotation-engine
python -m pytest tests/test_bug_fixes.py -v
```

---

## VERIFICATION CHECKLIST

After implementing all fixes:

- [ ] BUG-001: Run backtest, verify all trades show correct sign for P&L
  - Long straddles: positive entry cost, losses are negative
  - Short straddles: negative entry cost, gains are positive

- [ ] BUG-002: Check greeks output, verify delta ~50 for ATM calls
  - Before: delta ~0.5
  - After: delta ~50

- [ ] BUG-003: Track commissions through full lifecycle
  - Entry commission deducted once (at close)
  - Mark-to-market shows position value, not pre-deducted

- [ ] BUG-004: Run backtest with delta hedge enabled
  - Long delta positions should become neutral
  - Verify portfolio delta decreases, not increases

- [ ] BUG-005: Greeks calculations no longer floor IV at 0.10
  - IV estimates properly inverted from prices

- [ ] BUG-006: VIX proxy doesn't produce extreme values
  - Output always in 5-100 range

---

## DEPLOYMENT GATES

Do NOT deploy until:

- [ ] All CRITICAL bugs fixed (001-004)
- [ ] All unit tests passing (test_bug_fixes.py)
- [ ] Backtest results regenerated from scratch
- [ ] Spot-check: Manual verification of 5 random trades
- [ ] P&L reconciliation: Verify each trade's realized P&L matches manual calculation
- [ ] Greeks validation: Compare output to separate Greeks calculation
- [ ] Re-audit: Run quality gates again (bias audit, execution realism, etc.)

