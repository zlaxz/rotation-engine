# BUG-TIER0-004: Allocation Constraint Re-Normalization Oscillation - FIX SUMMARY

## Issue

**Location:** `/Users/zstoc/rotation-engine/src/backtest/rotation.py:171-238` (method `apply_constraints()`)

**Bug:** The allocation constraint algorithm attempted to satisfy two constraints through iterative re-normalization:
1. No profile > 40% (max_profile_weight)
2. All weights sum to 1.0

When signals were concentrated (e.g., [0.5, 0.5]), this oscillated and never converged.

### Example of Broken Behavior

```
Initial: [0.5, 0.5]
Cap at 0.4: [0.4, 0.4] (sum=0.8)
Re-normalize: [0.5, 0.5] (violates cap again!)
→ Oscillates indefinitely
```

After 10 iterations, the algorithm would return an invalid state with weights potentially exceeding the cap.

## Root Cause

The algorithm tried to maintain two incompatible invariants:
- **Hard constraint**: No weight > max_cap (40%)
- **Normalization constraint**: All weights sum to 1.0

When both profiles hit the cap, there's no valid state that satisfies both constraints.

The old algorithm also had a subtle bug: it tracked `violations = weights > max_cap` per iteration, but used `~violations` to identify uncapped profiles. This meant that profiles capped in previous iterations could receive redistribution again, pushing them above the cap.

## Fix

### New Algorithm

Replace the oscillating re-normalization loop with a proper iterative cap-and-redistribute algorithm:

1. **Track capped profiles**: Maintain a persistent `capped` array across iterations
2. **Cap and redistribute**:
   - Cap any weight > max_cap
   - Calculate excess weight
   - Redistribute excess to profiles that have NEVER been capped
   - Repeat until converged
3. **Accept cash positions**: If all profiles hit the cap, accept sum < 1.0 (hold cash)
4. **Apply min threshold AFTER capping**: Zero out weights < min threshold
5. **VIX scaling without renormalization**: Scale down all weights, hold cash in high vol

### Correct Order of Operations

```python
# Step 1: Apply hard cap with redistribution
weight_array = self._iterative_cap_and_redistribute(weight_array, max_cap)

# Step 2: Apply minimum threshold (accept sum < 1.0)
weight_array[weight_array < self.min_profile_weight] = 0.0

# Step 3: VIX scaling (reduce exposure, DO NOT renormalize)
if rv20 > self.vix_scale_threshold:
    weight_array = weight_array * self.vix_scale_factor
    # NO renormalization - hold cash in high vol
```

### Key Implementation Details

**Iterative Cap-and-Redistribute:**
```python
def _iterative_cap_and_redistribute(self, weights, max_cap, max_iterations=100):
    weights = weights.copy()
    capped = np.zeros(len(weights), dtype=bool)  # Track capped profiles

    for iteration in range(max_iterations):
        violations = weights > max_cap

        if not violations.any():
            break  # Converged

        excess = (weights[violations] - max_cap).sum()
        weights[violations] = max_cap
        capped[violations] = True  # Mark as permanently capped

        # Redistribute to profiles NOT capped in any iteration
        uncapped = ~capped & (weights > 0)

        if not uncapped.any():
            break  # All capped, hold cash

        uncapped_sum = weights[uncapped].sum()
        if uncapped_sum > 0:
            redistribution = excess * (weights[uncapped] / uncapped_sum)
            weights[uncapped] += redistribution

    return weights
```

## Test Results

### Constraint Fix Tests (9 tests)

All pass:
- ✓ Equal weights both violate cap: [0.5, 0.5] → [0.4, 0.4] (holds 20% cash)
- ✓ Dominant profile redistribution: [0.8, 0.2] → [0.4, 0.4] (both capped)
- ✓ Balanced weights under cap: [0.3, 0.3, 0.2, 0.2] → unchanged
- ✓ Min threshold zeroing: Small weights zeroed AFTER capping
- ✓ VIX scaling: Reduces exposure without violating cap
- ✓ All profiles capped: Holds cash
- ✓ Single profile over cap: Capped at 0.4, holds 60% cash
- ✓ Convergence speed: Fast (1-3 iterations)
- ✓ No oscillation: Deterministic results

### Integration Tests (2 tests)

All pass:
- ✓ Full allocation pipeline: scores → desirability → weights → constraints
- ✓ Daily allocation: Time series processing with multiple regimes

## Verification

### Before Fix (Broken)
```python
# [0.5, 0.5] with 40% cap
Iteration 1: [0.4, 0.4] → renormalize → [0.5, 0.5]  # Violates cap!
Iteration 2: [0.4, 0.4] → renormalize → [0.5, 0.5]  # Still violates!
...
Iteration 10: Give up, return invalid state
```

### After Fix (Correct)
```python
# [0.5, 0.5] with 40% cap
Iteration 1:
  - Cap both to 0.4: [0.4, 0.4]
  - Excess = 0.2
  - Uncapped profiles: none
  - Result: [0.4, 0.4], sum=0.8 (hold 20% cash)
```

### Constraint Guarantees

After fix, the algorithm ALWAYS satisfies:
- ✓ No weight > max_profile_weight (NEVER violated)
- ✓ All weights >= 0
- ✓ Sum(weights) <= 1.0 (may hold cash)
- ✓ Converges in < 100 iterations (typically 1-3)
- ✓ Deterministic (same input → same output)

## Files Modified

1. `/Users/zstoc/rotation-engine/src/backtest/rotation.py`
   - Replaced `apply_constraints()` method (lines 171-228)
   - Added `_iterative_cap_and_redistribute()` helper method (lines 230-301)
   - Updated docstrings to reflect correct behavior

## Files Created

1. `/Users/zstoc/rotation-engine/tests/test_allocation_constraint_fix.py`
   - 9 comprehensive unit tests for constraint algorithm

2. `/Users/zstoc/rotation-engine/tests/test_allocation_integration.py`
   - 2 integration tests for full allocation pipeline

## Impact on Strategy

### Cash Positions

The system now correctly holds cash when:
1. All profiles hit the max cap (concentration risk limit)
2. Profiles are below min threshold (filtered out as noise)
3. High volatility triggers VIX scaling (risk reduction)

### Example Allocation Output

**Concentrated signals (both profiles strong):**
- Before: [0.5, 0.5] (violates cap) or oscillates
- After: [0.4, 0.4] + 20% cash

**High volatility (RV20 > 30%):**
- Before: [0.4, 0.4] → renormalize to [0.5, 0.5] (violates cap!)
- After: [0.4, 0.4] → scale to [0.2, 0.2] + 60% cash

**Dominant profile with redistribution:**
- Before: [0.8, 0.2] → [0.6, 0.4] (profile_1 exceeds cap!)
- After: [0.8, 0.2] → [0.4, 0.4] (both capped correctly)

## Validation Checklist

- [x] Algorithm converges quickly (no oscillation)
- [x] Hard cap constraint NEVER violated
- [x] Handles edge cases (all capped, single profile, etc.)
- [x] Deterministic behavior
- [x] Cash positions accepted when appropriate
- [x] VIX scaling doesn't violate cap
- [x] Min threshold applied correctly
- [x] Integration with full allocation pipeline
- [x] Time series processing works

## Deployment Status

**Infra status: SAFE FOR RESEARCH**

The allocation constraint algorithm now correctly enforces the max weight cap without oscillation. The system accepts cash positions when constraints prevent full allocation, which is the correct behavior for risk management.

No known look-ahead or accounting bugs in this component.

---

**Fixed by:** Claude (quant-infrastructure-engineer agent)
**Date:** 2025-11-14
**Tier:** 0 (TIME & DATA FLOW - allocation happens before trade execution)
**Testing:** 11 tests, all passing
