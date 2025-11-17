# FIXES REQUIRED FOR CRITICAL BUGS

## FIX-001: DTE Calculation (1-2 hours)

**File:** `src/trading/simulator.py`
**Current Location:** Line 132
**Current Code:**
```python
# Line 131-136
days_in_trade = (date - current_trade.entry_date).days
avg_dte = int(np.mean([leg.dte for leg in current_trade.legs])) - days_in_trade

if avg_dte <= self.config.roll_dte_threshold:
    should_exit = True
    exit_reason = f"DTE threshold ({avg_dte} DTE)"
```

**Replacement Code:**
```python
# Line 131-150 (CORRECTED)
days_in_trade = (date - current_trade.entry_date).days

# Calculate current DTE for each leg from expiry date
current_dtes = []
for leg in current_trade.legs:
    dte = (leg.expiry - date).days
    dte = max(0, dte)  # Floor at 0 (prevent negative)
    current_dtes.append(dte)

# For rolling decisions, check MINIMUM DTE (most urgent leg)
min_dte = min(current_dtes) if current_dtes else 0
avg_dte = int(np.mean(current_dtes))

if min_dte <= self.config.roll_dte_threshold:
    # At least one leg needs to be rolled/closed
    should_exit = True
    exit_reason = f"DTE threshold (min={min_dte}, avg={avg_dte} DTE)"
```

**Why This Works:**
- Calculates current DTE from actual expiry dates
- Uses `max(0, dte)` to prevent negative DTE for expired legs
- Checks MINIMUM DTE for rolling decisions (catches expired legs)
- Maintains backward compatibility with avg_dte for logging

**Testing:**
```python
# Test case: Diagonal spread
entry_date = datetime(2024, 11, 1)
current_date = datetime(2024, 11, 13)
long_expiry = datetime(2024, 11, 30)  # 60 DTE
short_expiry = datetime(2024, 11, 8)  # 7 DTE

long_dte = (long_expiry - current_date).days  # = 17
short_dte = (short_expiry - current_date).days  # = -5 -> 0
min_dte = min([long_dte, short_dte])  # = 0 (TRIGGER ROLL)
avg_dte = mean([long_dte, short_dte])  # = 8.5

# Should exit = True (min_dte=0 <= threshold=3)
```

---

## FIX-002: Multi-Leg State Tracking (4-6 hours)

**File 1:** `src/trading/trade.py`
**Location:** Class Trade definition

**Current Code:**
```python
@dataclass
class Trade:
    # ... existing fields ...
    is_open: bool = True
    # ... rest of fields ...
```

**Replacement Code:**
```python
@dataclass
class Trade:
    # ... existing fields ...
    is_open: bool = True
    # NEW: Per-leg state tracking
    leg_status: List[bool] = None  # True = open, False = rolled/expired

    def __post_init__(self):
        """Initialize leg_status."""
        if self.entry_prices:
            self.entry_cost = sum(
                -self.legs[i].quantity * price
                for i, price in self.entry_prices.items()
            )
        # NEW: Initialize leg_status
        if self.leg_status is None:
            self.leg_status = [True] * len(self.legs)

    def get_active_legs(self, current_date: datetime) -> List[Tuple[int, TradeLeg]]:
        """Get list of (index, leg) tuples for non-expired, non-rolled legs."""
        active = []
        for i, leg in enumerate(self.legs):
            if self.leg_status[i] and leg.expiry > current_date:
                active.append((i, leg))
        return active

    def mark_leg_rolled(self, leg_index: int):
        """Mark a specific leg as rolled."""
        self.leg_status[leg_index] = False

    def has_expired_legs(self, current_date: datetime) -> bool:
        """Check if any legs are expired."""
        for i, leg in enumerate(self.legs):
            if self.leg_status[i] and leg.expiry <= current_date:
                return True
        return False

    def get_expired_leg_indices(self, current_date: datetime) -> List[int]:
        """Return indices of expired legs."""
        expired = []
        for i, leg in enumerate(self.legs):
            if self.leg_status[i] and leg.expiry <= current_date:
                expired.append(i)
        return expired
```

**File 2:** `src/trading/simulator.py`
**Location:** Lines 121-157 (exit logic)

**Current Code:**
```python
# Check if we should exit current trade
if current_trade is not None and current_trade.is_open:
    should_exit = False
    exit_reason = None

    # Custom exit logic
    if exit_logic is not None and exit_logic(row, current_trade):
        should_exit = True
        exit_reason = "Custom exit logic"

    # Default exit: DTE threshold
    # ... (use corrected DTE code from FIX-001) ...

    # ... rest of exit checks ...

    # Execute exit
    if should_exit:
        exit_prices = self._get_exit_prices(current_trade, row)
        current_trade.close(date, exit_prices, exit_reason or "Unknown")
        pnl_today = current_trade.realized_pnl
        self.trades.append(current_trade)
        current_trade = None
```

**Replacement Code:**
```python
# Check if we should exit current trade
if current_trade is not None and current_trade.is_open:
    should_exit = False
    exit_reason = None

    # NEW: Check for expired legs and handle rolling
    expired_indices = current_trade.get_expired_leg_indices(date)
    if expired_indices:
        # For multi-leg positions, determine rolling vs closing
        active_legs = current_trade.get_active_legs(date)

        if len(active_legs) > 0 and len(expired_indices) == 1:
            # Single leg expired, others still active -> mark as rolled
            for idx in expired_indices:
                current_trade.mark_leg_rolled(idx)
            # Don't trigger full exit, position continues with remaining legs
        else:
            # All legs expired or complex multi-leg case -> close position
            should_exit = True
            exit_reason = f"Expired legs: {expired_indices}"

    # Custom exit logic
    if exit_logic is not None and exit_logic(row, current_trade):
        should_exit = True
        exit_reason = "Custom exit logic"

    # Default exit: DTE threshold (use FIX-001 corrected code)
    if not should_exit:
        days_in_trade = (date - current_trade.entry_date).days
        current_dtes = []
        for leg in current_trade.legs:
            dte = (leg.expiry - date).days
            dte = max(0, dte)
            current_dtes.append(dte)
        min_dte = min(current_dtes) if current_dtes else 0

        if min_dte <= self.config.roll_dte_threshold:
            should_exit = True
            exit_reason = f"DTE threshold ({min_dte} DTE)"

    # ... rest of exit checks ...

    # Execute exit
    if should_exit:
        # Only exit legs that are still open
        exit_prices = self._get_exit_prices(current_trade, row)
        current_trade.close(date, exit_prices, exit_reason or "Unknown")
        pnl_today = current_trade.realized_pnl
        self.trades.append(current_trade)
        current_trade = None
```

**Note:** Full rolling implementation (replacing individual legs) requires:
1. New trade constructor function that creates replacement legs
2. Logic to pair new legs with strategy intent
3. Tracking of rolled legs in Trade history

This is more complex and should be implemented after basic per-leg state tracking works.

**Testing:**
```python
# Test case: Diagonal spread
from datetime import datetime, timedelta
from src.trading.trade import Trade, TradeLeg

# Create diagonal
legs = [
    TradeLeg(strike=500, expiry=datetime(2024, 11, 30),
             option_type='call', quantity=1, dte=60),
    TradeLeg(strike=505, expiry=datetime(2024, 11, 8),
             option_type='call', quantity=-1, dte=7)
]

trade = Trade(
    trade_id="TEST_001",
    profile_name="Test",
    entry_date=datetime(2024, 11, 1),
    legs=legs,
    entry_prices={0: 5.0, 1: 2.0}
)

current_date = datetime(2024, 11, 13)

# Check expired
expired = trade.get_expired_leg_indices(current_date)
assert 1 in expired, "Short leg should be expired"

# Check active
active = trade.get_active_legs(current_date)
assert len(active) == 1, "Only long leg should be active"
assert active[0][0] == 0, "Active leg should be index 0"

# Mark as rolled
trade.mark_leg_rolled(1)
assert trade.leg_status[1] == False, "Rolled leg should be marked False"
assert trade.is_open == True, "Position should stay open"
```

---

## FIX-003: Allocation Weight Re-Normalization (30 minutes)

**File:** `src/backtest/rotation.py`
**Location:** Lines 219-224

**Current Code:**
```python
# Step 5: Apply VIX scaling (reduce exposure in high vol)
if rv20 > self.vix_scale_threshold:
    scale = self.vix_scale_factor
    constrained = {k: v * scale for k, v in constrained.items()}

return constrained
```

**Replacement Code:**
```python
# Step 5: Apply VIX scaling (reduce exposure in high vol)
if rv20 > self.vix_scale_threshold:
    scale = self.vix_scale_factor
    constrained = {k: v * scale for k, v in constrained.items()}

    # RE-NORMALIZE after scaling to maintain sum = 1.0
    total = sum(constrained.values())
    if total > 0:
        constrained = {k: v / total for k, v in constrained.items()}

return constrained
```

**Why This Works:**
- Maintains weights sum to 1.0 after VIX scaling
- Preserves relative weights (high weight stays highest)
- Reduces absolute exposure uniformly

**Example:**
```
Before: {P1: 0.40, P2: 0.40, P3: 0.20} sum=1.0
VIX scale (0.5): {P1: 0.20, P2: 0.20, P3: 0.10} sum=0.50
Re-normalize: {P1: 0.40, P2: 0.40, P3: 0.20} sum=1.0

Wait... that's the same! Is this right?
```

Actually, I think the VIX scaling intent is different. Let me check:

**Option A: Reduce absolute exposure to 50%**
```
After scaling: {P1: 0.20, P2: 0.20, P3: 0.10}
Don't re-normalize (weights sum to 0.50)
= Portfolio only 50% allocated, 50% in cash
```

**Option B: Reduce relative weights proportionally but keep fully allocated**
```
After scaling: {P1: 0.20, P2: 0.20, P3: 0.10}
Re-normalize: {P1: 0.40, P2: 0.40, P3: 0.20}
= Same weights as before (scaling had no effect!)
```

**Correct interpretation:** VIX scaling should reduce OVERALL exposure, not individual weights.

**CORRECT Fix:**
```python
# Step 5: Apply VIX scaling (reduce exposure in high vol)
if rv20 > self.vix_scale_threshold:
    # When volatility is high, scale overall portfolio size down
    # by applying scale to final allocation before returning
    scale = self.vix_scale_factor
    constrained = {k: v * scale for k, v in constrained.items()}
    # Do NOT re-normalize - this reduces total allocation to scale
    # e.g., 50% of portfolio allocated, 50% in cash

    # However, if the intent is to maintain full allocation but reduce weights:
    # total = sum(constrained.values())
    # if total > 0:
    #     constrained = {k: v / total for k, v in constrained.items()}
    # This would give original weights with no actual risk reduction

return constrained
```

**Decision:** Based on the config parameter `vix_scale_factor = 0.5`, the intent is to:
- Reduce overall portfolio exposure to 50% when volatility is high
- This is correct ONLY if your portfolio aggregation code handles partial allocation

**Verification needed in `portfolio.py:76`:**
```python
portfolio[pnl_col] = portfolio[weight_col] * portfolio[f'{profile_name}_daily']
```

If weights sum to 0.50, then total portfolio weight is 0.50. Is this handled correctly downstream?

**Recommendation:**
1. Clarify intent: Does scaling reduce absolute exposure or relative weights?
2. If reducing absolute exposure: Keep current code (don't re-normalize)
3. If maintaining full allocation: Add re-normalization
4. Add comments to explain the intent
5. Add unit test to verify weights behavior

**Conservative fix (re-normalize to be safe):**
```python
# Step 5: Apply VIX scaling (reduce exposure in high vol)
if rv20 > self.vix_scale_threshold:
    scale = self.vix_scale_factor
    constrained = {k: v * scale for k, v in constrained.items()}

    # Clarification: This reduces overall portfolio exposure
    # Weights sum to less than 1.0, leaving scale*(100%)% in cash
    # If you want to maintain full allocation, re-normalize here:
    # total = sum(constrained.values())
    # if total > 0:
    #     constrained = {k: v / total for k, v in constrained.items()}

return constrained
```

---

## IMPLEMENTATION ORDER

1. **First:** Implement FIX-001 (DTE calculation)
   - Relatively simple, no breaking changes
   - Enables accurate rolling decision

2. **Second:** Implement FIX-003 (Allocation weights)
   - Quick fix, critical for correctness
   - Add clarifying comments about VIX scaling intent

3. **Third:** Implement FIX-002 (Multi-leg state tracking)
   - More complex, requires testing
   - Builds on FIX-001 for correct DTE

---

## TESTING CHECKLIST

After each fix:

```python
# FIX-001 Test
def test_dte_calculation():
    """Verify DTE calculation for multi-leg positions."""
    # Create diagonal spread
    # Check current DTE calculation
    # Verify min_dte identifies expired legs
    # Test rolling logic

# FIX-002 Test
def test_leg_state_tracking():
    """Verify per-leg state tracking."""
    # Create multi-leg position
    # Simulate leg expiration
    # Check leg_status reflects current state
    # Test active_legs list

# FIX-003 Test
def test_allocation_weights():
    """Verify allocation weights sum to 1.0."""
    # Create allocation with high RV20
    # Check weights before/after VIX scaling
    # Verify sum = 1.0 (or 0.5 if partial allocation intended)
    # Test with different RV20 levels
```

---

## VALIDATION AFTER FIXES

Run these to validate fixes:

```bash
# 1. Run BUG_VERIFICATION.py to see bugs are fixed
python BUG_VERIFICATION.py

# 2. Run existing unit tests
pytest tests/ -v

# 3. Run backtest on sample profile
python example_usage.py

# 4. Verify P&L calculations manually
python validate_day1.py
python validate_day2.py
# ... etc
```

