"""
Integration test for allocation constraint fix.

Tests the full allocation pipeline with the corrected constraint algorithm.
"""

import pandas as pd
import numpy as np
from src.backtest.rotation import RotationAllocator


def test_full_allocation_pipeline():
    """
    Test full allocation pipeline: scores → desirability → weights → constraints.

    Verifies that the oscillation bug is fixed and constraints are properly applied.
    """
    allocator = RotationAllocator(
        max_profile_weight=0.40,
        min_profile_weight=0.05,
        vix_scale_threshold=0.30,
        vix_scale_factor=0.5
    )

    # Scenario 1: Two profiles with equal high scores in Trend Up regime
    # Should result in [0.4, 0.4] holding 20% cash (both hit cap)
    profile_scores = {
        'profile_1': 0.9,  # Long-dated gamma - strong in Trend Up
        'profile_4': 0.9   # Vanna - strong in Trend Up
    }
    regime = 1  # Trend Up
    rv20 = 0.15  # Low vol

    result = allocator.allocate(profile_scores, regime, rv20)

    # Both should be capped at 0.4
    assert result['profile_1'] <= 0.40 + 1e-9, f"Profile 1 exceeds cap: {result['profile_1']}"
    assert result['profile_4'] <= 0.40 + 1e-9, f"Profile 4 exceeds cap: {result['profile_4']}"

    # Sum should be <= 1.0 (may hold cash)
    total = sum(result.values())
    assert total <= 1.0 + 1e-9, f"Sum exceeds 1.0: {total}"

    print(f"Scenario 1 - Equal high scores: {result}, sum={total:.3f}")


    # Scenario 2: Dominant profile in Breaking Vol regime
    # Skew and vol-of-vol are strong, others weak
    profile_scores = {
        'profile_1': 0.8,
        'profile_2': 0.6,
        'profile_3': 0.5,
        'profile_4': 0.4,
        'profile_5': 0.95,  # Skew - strong
        'profile_6': 0.9    # Vol-of-vol - strong
    }
    regime = 4  # Breaking Vol
    rv20 = 0.15

    result = allocator.allocate(profile_scores, regime, rv20)

    # No weight should exceed cap
    for weight in result.values():
        assert weight <= 0.40 + 1e-9, f"Weight {weight} exceeds cap"

    # Sum should be reasonable
    total = sum(result.values())
    assert 0 <= total <= 1.0 + 1e-9, f"Sum out of range: {total}"

    print(f"Scenario 2 - Dominant profiles: {result}, sum={total:.3f}")


    # Scenario 3: High volatility triggers VIX scaling
    profile_scores = {
        'profile_1': 0.7,
        'profile_2': 0.6
    }
    regime = 1
    rv20 = 0.35  # Above threshold (0.30)

    result = allocator.allocate(profile_scores, regime, rv20)

    # After VIX scaling, should scale down and hold cash (NOT renormalize)
    total = sum(result.values())
    assert total < 1.0, f"VIX scaling should reduce exposure (hold cash), got {total}"

    # No weight should exceed cap
    for weight in result.values():
        assert weight <= 0.40 + 1e-9, f"Weight {weight} exceeds cap"

    print(f"Scenario 3 - VIX scaling: {result}, sum={total:.3f}")


    # Scenario 4: Multiple iterations with redistribution
    # This would have oscillated with the old algorithm
    profile_scores = {
        'profile_1': 1.0,
        'profile_2': 0.5,
        'profile_3': 0.3,
        'profile_4': 0.2
    }
    regime = 1
    rv20 = 0.15

    result = allocator.allocate(profile_scores, regime, rv20)

    # No weight should exceed cap
    for weight in result.values():
        assert weight <= 0.40 + 1e-9, f"Weight {weight} exceeds cap"

    # Should be deterministic (run 10 times, get same result)
    for _ in range(10):
        result_check = allocator.allocate(profile_scores, regime, rv20)
        for profile in profile_scores.keys():
            assert abs(result[profile] - result_check[profile]) < 1e-9, \
                "Non-deterministic behavior (oscillation)"

    print(f"Scenario 4 - No oscillation: {result}, sum={sum(result.values()):.3f}")

    print("\n✓ Full allocation pipeline integration test PASSED")


def test_daily_allocation():
    """
    Test allocate_daily() method with time series data.
    """
    allocator = RotationAllocator(max_profile_weight=0.40, min_profile_weight=0.05)

    # Create simple time series
    dates = pd.date_range('2024-01-01', periods=5, freq='D')
    data = pd.DataFrame({
        'date': dates,
        'regime': [1, 1, 2, 3, 4],
        'RV20': [0.15, 0.18, 0.25, 0.32, 0.40],
        'profile_1_score': [0.8, 0.7, 0.5, 0.6, 0.3],
        'profile_2_score': [0.5, 0.6, 0.8, 0.4, 0.5]
    })

    result = allocator.allocate_daily(data)

    # Check structure
    assert len(result) == 5, "Should have 5 rows"
    assert 'date' in result.columns
    assert 'regime' in result.columns
    assert 'profile_1_weight' in result.columns
    assert 'profile_2_weight' in result.columns

    # Check constraints for each day
    for idx, row in result.iterrows():
        w1 = row['profile_1_weight']
        w2 = row['profile_2_weight']

        # No weight exceeds cap
        assert w1 <= 0.40 + 1e-9, f"Day {idx}: profile_1 exceeds cap: {w1}"
        assert w2 <= 0.40 + 1e-9, f"Day {idx}: profile_2 exceeds cap: {w2}"

        # Sum is reasonable
        total = w1 + w2
        assert 0 <= total <= 1.0 + 1e-9, f"Day {idx}: sum out of range: {total}"

    print(f"\n✓ Daily allocation test PASSED")
    print(result)


if __name__ == '__main__':
    test_full_allocation_pipeline()
    test_daily_allocation()
