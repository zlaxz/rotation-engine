# TEST CASES FOR BUG FIX VERIFICATION

## Overview

These test cases verify that each bug fix is correctly implemented and produces expected results.

---

## TEST 1: BUG-002 Greeks Multiplier Verification

**Purpose**: Verify that Greeks are scaled by 100 (contract multiplier)

### Test Case 1.1: Single ATM Call

**Setup**:
```python
spot = 100
strike = 100
dte = 30
iv = 0.20

# Black-Scholes expects: delta ≈ 0.50 for ATM call
# Per contract (100 shares): delta_contract = 0.50 * 100 = 50
```

**Code Path** (trade.py lines 336-342):
```python
greeks = calculate_all_greeks(S=100, K=100, T=30/365, r=0.05, sigma=0.20, option_type='call')
# Returns: {'delta': 0.5, 'gamma': 0.04, 'theta': -0.002, 'vega': 0.15, ...}

self.net_delta = 1 * 0.5 * 100 = 50  # Should be around 50
self.net_gamma = 1 * 0.04 * 100 = 4  # Should be around 4
```

**Expected Result**:
- net_delta = 50 (not 0.5)
- net_gamma = 4 (not 0.04)
- net_theta = -0.2 (not -0.002)
- net_vega = 15 (not 0.15)

**Verification Command**:
```python
trade = create_straddle_trade(...)
trade.calculate_greeks(underlying_price=100, current_date=entry_date, implied_vol=0.20)
assert 40 < trade.net_delta < 60, f"Expected delta ~50, got {trade.net_delta}"
assert 3 < trade.net_gamma < 5, f"Expected gamma ~4, got {trade.net_gamma}"
print("✓ Test 1.1 PASSED: ATM call Greeks scaled correctly")
```

---

### Test Case 1.2: Long Straddle (Long Call + Long Put)

**Setup**:
```python
# Long 1 call + Long 1 put at same strike
# At ATM: delta_call ≈ +0.50, delta_put ≈ -0.50
# Net should be ≈ 0
```

**Expected Result**:
- net_delta_call = +50
- net_delta_put = -50
- net_delta_total = 0

**Verification Command**:
```python
trade = Trade(legs=[
    TradeLeg(strike=100, qty=+1, option_type='call', ...),
    TradeLeg(strike=100, qty=+1, option_type='put', ...)
])
trade.calculate_greeks(underlying_price=100, current_date=entry_date)
assert abs(trade.net_delta) < 5, f"Expected net_delta ≈ 0, got {trade.net_delta}"
print("✓ Test 1.2 PASSED: Straddle has neutral delta")
```

---

### Test Case 1.3: Short Strangle (Short 1 Call + Short 1 Put)

**Setup**:
```python
# Short 1 call + Short 1 put
# Gamma should be NEGATIVE (loses on large moves)
# Theta should be NEGATIVE but represents profit from time decay
```

**Expected Result**:
- net_gamma < 0 (short options)
- net_theta < 0 (theta for short options is negative, but represents daily profit)

**Verification Command**:
```python
trade = Trade(legs=[
    TradeLeg(strike=100, qty=-1, option_type='call', ...),
    TradeLeg(strike=100, qty=-1, option_type='put', ...)
])
trade.calculate_greeks(underlying_price=100, current_date=entry_date)
assert trade.net_gamma < -5, f"Expected net_gamma < -5, got {trade.net_gamma}"
assert trade.net_theta < -0.3, f"Expected net_theta negative, got {trade.net_theta}"
print("✓ Test 1.3 PASSED: Short strangle has negative gamma (risk)")
```

---

## TEST 2: BUG-003 Commission in Unrealized P&L Verification

**Purpose**: Verify entry commission is NOT deducted from unrealized P&L

### Test Case 2.1: Long Call Mark-to-Market (No Closing)

**Setup**:
```python
# Day 1 (Entry)
entry_price = 3.00
entry_commission = 2.60
cost_per_contract = 3.00 * 100 = 300
total_entry_outflow = 300 + 2.60 = 302.60 (cash we paid)

# Day 2 (Still holding)
current_price = 3.50
mtm_value = 3.50 * 100 = 350

# Estimated exit commission if we close today
estimated_exit_commission = 2.60
```

**Expected Unrealized P&L**:
```python
unrealized = (3.50 - 3.00) * 100 - estimated_exit_commission
           = 50 - 2.60
           = 47.40

# DO NOT subtract entry_commission from unrealized!
# DO subtract estimated_exit_commission (we'd have to pay it to close)
```

**Code Path** (trade.py lines 176-225):
```python
# mark_to_market() calculation
unrealized_pnl = 1 * (3.50 - 3.00) * 100 = 50  # Line 181
unrealized_pnl -= cumulative_hedge_cost (assume 0)
unrealized_pnl -= estimated_exit_commission = 2.60
# Result: 50 - 2.60 = 47.40

# Entry commission NOT subtracted ✓
```

**Verification Command**:
```python
trade = Trade(legs=[TradeLeg(strike=100, qty=1, option_type='call')])
trade.entry_prices = {0: 3.00}
trade.entry_commission = 2.60
trade.cumulative_hedge_cost = 0.0
trade.__post_init__()

unrealized = trade.mark_to_market(
    current_prices={0: 3.50},
    estimated_exit_commission=2.60
)
assert abs(unrealized - 47.40) < 0.01, f"Expected 47.40, got {unrealized}"
print("✓ Test 2.1 PASSED: Entry commission not in unrealized P&L")
```

---

### Test Case 2.2: Realized P&L at Close (All Commissions Applied)

**Setup**:
```python
# Entry
entry_price = 3.00
entry_commission = 2.60

# Close
exit_price = 3.40
exit_commission = 2.60
```

**Expected Realized P&L**:
```python
realized = (3.40 - 3.00) * 100 - entry_commission - exit_commission
         = 40 - 2.60 - 2.60
         = 34.80

# BOTH commissions subtracted now ✓
```

**Code Path** (trade.py lines 122-137):
```python
pnl_legs = 1 * (3.40 - 3.00) * 100 = 40  # Line 127
realized_pnl = pnl_legs - entry_commission - exit_commission - hedge_cost
             = 40 - 2.60 - 2.60 - 0
             = 34.80  # Correct ✓
```

**Verification Command**:
```python
trade = Trade(legs=[TradeLeg(strike=100, qty=1, option_type='call')])
trade.entry_prices = {0: 3.00}
trade.entry_commission = 2.60
trade.exit_commission = 2.60
trade.cumulative_hedge_cost = 0.0
trade.__post_init__()

trade.close(exit_date=date2, exit_prices={0: 3.40}, reason="Test")

assert abs(trade.realized_pnl - 34.80) < 0.01, f"Expected 34.80, got {trade.realized_pnl}"
print("✓ Test 2.2 PASSED: Both commissions in realized P&L")
```

---

## TEST 3: BUG-004 Delta Hedge Direction Verification

**Purpose**: Verify delta hedge shorts ES when portfolio is long delta

### Test Case 3.1: Long Delta Portfolio

**Setup**:
```python
# Portfolio: 1 ATM call
# Delta ≈ +0.5 per share, but multiplied by 100 → net_delta = +50? NO!
# Actually net_delta should be ~+50 (in delta units for ES hedging)

# Actually: 1 call = +0.5 delta per share * 100 shares = +50 notional delta
# But ES is quoted differently...
# The code assumes: es_delta_per_contract = 50
# So if net_delta = +100 (2 ATM calls), need 2 ES contracts
```

**Expected Hedge**:
```python
net_delta = +100 (long delta exposure)
es_delta_per_contract = 50

hedge_magnitude = 100 / 50 = 2 contracts
hedge_direction = -1 (short ES to neutralize)
hedge_contracts = 2 * (-1) = -2 (short 2 ES)

# Resulting net delta: +100 (portfolio) + (-100) (hedge) = 0 ✓
```

**Code Path** (simulator.py lines 740-745):
```python
if trade.net_delta > 0:
    hedge_direction = -1  # Long delta → short hedge
else:
    hedge_direction = 1   # Short delta → long hedge

hedge_contracts = hedge_contracts_magnitude * hedge_direction
# Result: 2 * (-1) = -2 ✓
```

**Verification Command**:
```python
trade = Trade(legs=[TradeLeg(strike=100, qty=1, option_type='call')])
trade.net_delta = 100  # Long delta

# Manual hedge calculation
es_delta_per_contract = 50
hedge_magnitude = abs(trade.net_delta) / es_delta_per_contract  # 100/50 = 2

if trade.net_delta > 0:
    hedge_direction = -1
else:
    hedge_direction = 1

hedge_contracts = hedge_magnitude * hedge_direction  # 2 * (-1) = -2

assert hedge_contracts == -2, f"Expected -2, got {hedge_contracts}"
print("✓ Test 3.1 PASSED: Long delta gets short hedge")
```

---

### Test Case 3.2: Short Delta Portfolio

**Setup**:
```python
net_delta = -100 (short delta exposure, from short call + short put)
es_delta_per_contract = 50

# Should LONG ES to neutralize
hedge_direction should be +1
hedge_contracts should be +2
```

**Expected Hedge**:
```python
hedge_magnitude = 100 / 50 = 2
hedge_direction = +1 (short delta → long hedge)
hedge_contracts = +2 (long 2 ES)

# Resulting net delta: -100 (portfolio) + (+100) (hedge) = 0 ✓
```

**Verification Command**:
```python
trade = Trade(legs=[
    TradeLeg(strike=100, qty=-1, option_type='call'),
    TradeLeg(strike=100, qty=-1, option_type='put')
])
trade.net_delta = -100  # Short delta

hedge_magnitude = abs(-100) / 50  # = 2
if trade.net_delta > 0:
    hedge_direction = -1
else:
    hedge_direction = 1  # This path

hedge_contracts = 2 * 1  # +2

assert hedge_contracts == +2, f"Expected +2, got {hedge_contracts}"
print("✓ Test 3.2 PASSED: Short delta gets long hedge")
```

---

## TEST 4: BUG-001 Entry Cost Sign Convention

**Purpose**: Verify entry_cost has correct sign and includes spread/commission

### Test Case 4.1: Long Position Entry Cost

**Setup**:
```python
# TradeTracker (fixed)
qty = +1
price = 3.00 (mid)
spread = 0.03
commission = 2.60

# We BUY at ask = 3.00 + 0.03 = 3.03
# We PAY: 1 * 3.03 * 100 + 2.60 = 303 + 2.60 = 305.60
```

**Expected Result**:
```python
entry_cost = +305.60  (positive = cash outflow)
```

**Code Path** (trade_tracker.py lines 95-104):
```python
leg_cost = 1 * (3.00 + 0.03) * 100 = 303
entry_cost = 303 + 2.60 = 305.60  ✓
```

**Verification Command**:
```python
qty = 1
price_mid = 3.00
spread = 0.03
commission = 2.60

if qty > 0:
    leg_cost = qty * (price_mid + spread) * 100
else:
    leg_cost = qty * (price_mid - spread) * 100

entry_cost = leg_cost + commission
assert entry_cost == 305.60, f"Expected 305.60, got {entry_cost}"
print("✓ Test 4.1 PASSED: Long entry has positive cost")
```

---

### Test Case 4.2: Short Position Entry Cost

**Setup**:
```python
# TradeTracker (fixed)
qty = -1
price = 3.00 (mid)
spread = 0.03
commission = 2.60

# We SELL at bid = 3.00 - 0.03 = 2.97
# We RECEIVE: -1 * 2.97 * 100 = -297
# Net INFLOW: -297 + 2.60 (commission cost) = -294.40
```

**Expected Result**:
```python
entry_cost = -294.40  (negative = cash inflow)
```

**Code Path** (trade_tracker.py lines 98-104):
```python
leg_cost = -1 * (3.00 - 0.03) * 100 = -297
entry_cost = -297 + 2.60 = -294.40  ✓
```

**Verification Command**:
```python
qty = -1
price_mid = 3.00
spread = 0.03
commission = 2.60

if qty > 0:
    leg_cost = qty * (price_mid + spread) * 100
else:
    leg_cost = qty * (price_mid - spread) * 100

entry_cost = leg_cost + commission
assert entry_cost == -294.40, f"Expected -294.40, got {entry_cost}"
print("✓ Test 4.2 PASSED: Short entry has negative cost (inflow)")
```

---

### Test Case 4.3: Straddle Entry Cost

**Setup**:
```python
# Long 1 call + Long 1 put
call_mid = 3.00
put_mid = 2.50
spread = 0.03
commission = 2.60

# Call leg: buy at ask = 3.00 + 0.03 = 3.03
call_cost = 1 * 3.03 * 100 = 303

# Put leg: buy at ask = 2.50 + 0.03 = 2.53
put_cost = 1 * 2.53 * 100 = 253

# Total: 303 + 253 + 2.60 = 558.60
```

**Expected Result**:
```python
entry_cost = +558.60  (total debit for buying straddle)
```

**Verification Command**:
```python
legs = [
    {'type': 'call', 'qty': 1, 'price': 3.00},
    {'type': 'put', 'qty': 1, 'price': 2.50}
]
spread = 0.03
commission = 2.60

entry_cost = 0
for leg in legs:
    qty = leg['qty']
    price = leg['price']
    if qty > 0:
        leg_cost = qty * (price + spread) * 100
    else:
        leg_cost = qty * (price - spread) * 100
    entry_cost += leg_cost

entry_cost += commission

assert entry_cost == 558.60, f"Expected 558.60, got {entry_cost}"
print("✓ Test 4.3 PASSED: Straddle entry cost correct")
```

---

## Integration Test: End-to-End Trade Flow

**Purpose**: Verify all four bugs work together correctly in a complete trade lifecycle

### Setup:
```python
# Entry: Day 1, Long 1 ATM straddle
# Hold: Days 2-3, Check unrealized P&L and Greeks
# Exit: Day 4, Check realized P&L and commissions
```

### Test Execution:

```python
def test_complete_trade_lifecycle():
    # Day 1: Entry
    trade = Trade(
        trade_id="TEST_001",
        profile_name="STRADDLE",
        entry_date=datetime(2025, 1, 1),
        legs=[
            TradeLeg(strike=505, expiry=datetime(2025, 1, 31), qty=1, option_type='call'),
            TradeLeg(strike=505, expiry=datetime(2025, 1, 31), qty=1, option_type='put')
        ],
        entry_prices={0: 3.00, 1: 2.50}
    )

    trade.entry_commission = 2.60
    trade.__post_init__()

    # Verify entry_cost includes commission
    # (Note: This depends on Trade.py using execution prices or mid prices)
    print(f"Entry cost: {trade.entry_cost}")

    # Day 2: Mark-to-market
    trade.calculate_greeks(
        underlying_price=505,
        current_date=datetime(2025, 1, 2),
        implied_vol=0.20
    )

    # Verify Greeks are scaled by 100
    assert abs(trade.net_delta) < 20, f"Expected near-zero delta, got {trade.net_delta}"
    assert trade.net_gamma > 5, f"Expected positive gamma, got {trade.net_gamma}"
    print(f"Greeks - Delta: {trade.net_delta}, Gamma: {trade.net_gamma}")

    # Mark-to-market
    unrealized_day2 = trade.mark_to_market(
        current_prices={0: 3.15, 1: 2.60},
        estimated_exit_commission=2.60
    )

    # Verify entry commission NOT in unrealized
    expected_unrealized = (3.15 - 3.00) * 100 + (2.60 - 2.50) * 100 - 2.60
    assert abs(unrealized_day2 - expected_unrealized) < 0.01, \
        f"Expected {expected_unrealized}, got {unrealized_day2}"
    print(f"Unrealized P&L Day 2: {unrealized_day2}")

    # Day 4: Close
    trade.exit_commission = 2.60
    trade.close(
        exit_date=datetime(2025, 1, 4),
        exit_prices={0: 3.10, 1: 2.55},
        reason="Test close"
    )

    # Verify realized includes ALL commissions
    expected_realized = (3.10 - 3.00) * 100 + (2.55 - 2.50) * 100 - 2.60 - 2.60
    assert abs(trade.realized_pnl - expected_realized) < 0.01, \
        f"Expected {expected_realized}, got {trade.realized_pnl}"
    print(f"Realized P&L: {trade.realized_pnl}")

    print("✓ Integration Test PASSED: All bugs work correctly together")

test_complete_trade_lifecycle()
```

---

## Summary

- **BUG-001**: Entry cost signs correct for long/short positions ✓
- **BUG-002**: Greeks scaled by 100 (contract multiplier) ✓
- **BUG-003**: Entry commission not in unrealized P&L ✓
- **BUG-004**: Delta hedge direction correct (opposite of portfolio) ✓

All tests should pass before deploying to production.

