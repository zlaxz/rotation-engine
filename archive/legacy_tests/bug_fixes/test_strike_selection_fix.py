"""
Test suite for Bug 2: ATM Strike Rounding Fix

Verifies that:
1. All profiles round strikes to $1 (not $5)
2. ATM strikes are within $0.50 of spot price
3. OTM strikes are correctly calculated from spot
4. No systematic OTM bias in "ATM" selections
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.trading.profiles.profile_1 import Profile1LongDatedGamma
from src.trading.profiles.profile_2 import Profile2ShortDatedGamma
from src.trading.profiles.profile_3 import Profile3CharmDecay
from src.trading.profiles.profile_4 import Profile4Vanna
from src.trading.profiles.profile_5 import Profile5SkewConvexity
from src.trading.profiles.profile_6 import Profile6VolOfVol


class TestStrikeSelectionFix:
    """Test strike selection rounding fixes."""

    @pytest.fixture
    def market_row(self):
        """Create a test market row with fractional spot price."""
        return pd.Series({
            'date': pd.Timestamp('2023-01-15'),
            'open': 502.00,
            'high': 503.50,
            'low': 501.00,
            'close': 502.37,  # Fractional spot price
            'volume': 1000000,
            'RV20': 0.20,
            'regime': 1,
            'profile_1_score': 0.7,
            'profile_2_score': 0.7,
            'profile_3_score': 0.7,
            'profile_4_score': 0.7,
            'profile_5_score': 0.7,
            'profile_6_score': 0.7,
        })

    def test_profile_1_atm_strike_rounding(self, market_row):
        """Test Profile 1 rounds ATM strikes to $1."""
        profile = Profile1LongDatedGamma()
        trade = profile.trade_constructor(market_row, "TEST_001")

        spot = market_row['close']  # 502.37
        expected_strike = round(spot)  # 502

        # All legs should use same ATM strike
        for leg in trade.legs:
            assert leg.strike == expected_strike, \
                f"Expected strike {expected_strike}, got {leg.strike}"

        # Verify strike is within $0.50 of spot
        assert abs(leg.strike - spot) <= 0.50, \
            f"Strike {leg.strike} is more than $0.50 from spot {spot}"

    def test_profile_2_atm_strike_rounding(self, market_row):
        """Test Profile 2 rounds ATM strikes to $1."""
        profile = Profile2ShortDatedGamma()
        trade = profile.trade_constructor(market_row, "TEST_002")

        spot = market_row['close']  # 502.37
        expected_strike = round(spot)  # 502

        for leg in trade.legs:
            assert leg.strike == expected_strike

        assert abs(leg.strike - spot) <= 0.50

    def test_profile_3_otm_strike_rounding(self, market_row):
        """Test Profile 3 rounds OTM strikes to $1."""
        profile = Profile3CharmDecay()
        trade = profile.trade_constructor(market_row, "TEST_003")

        spot = market_row['close']  # 502.37

        # Call strike: ~7% OTM above spot
        expected_call = round(spot * 1.07)  # round(537.54) = 538
        # Put strike: ~7% OTM below spot
        expected_put = round(spot * 0.93)  # round(467.20) = 467

        # Find call and put legs
        call_leg = next(leg for leg in trade.legs if leg.option_type == 'call')
        put_leg = next(leg for leg in trade.legs if leg.option_type == 'put')

        assert call_leg.strike == expected_call, \
            f"Expected call strike {expected_call}, got {call_leg.strike}"
        assert put_leg.strike == expected_put, \
            f"Expected put strike {expected_put}, got {put_leg.strike}"

    def test_profile_4_strike_rounding(self, market_row):
        """Test Profile 4 rounds strikes to $1."""
        profile = Profile4Vanna()
        trade = profile.trade_constructor(market_row, "TEST_004")

        spot = market_row['close']  # 502.37

        # Long ATM strike
        expected_long = round(spot)  # 502
        # Short OTM strike (~5% above)
        expected_short = round(spot * 1.05)  # round(527.49) = 527

        # Legs are ordered: long, short
        long_leg = trade.legs[0]
        short_leg = trade.legs[1]

        assert long_leg.strike == expected_long
        assert short_leg.strike == expected_short

    def test_profile_5_strike_rounding(self, market_row):
        """Test Profile 5 rounds strikes to $1."""
        market_row['regime'] = 2  # Trend Down for Profile 5
        profile = Profile5SkewConvexity()
        trade = profile.trade_constructor(market_row, "TEST_005")

        spot = market_row['close']  # 502.37

        # Short ATM put
        expected_short = round(spot)  # 502
        # Long OTM put (~7% below)
        expected_long = round(spot * 0.93)  # round(467.20) = 467

        # Legs: short ATM, long OTM
        short_leg = trade.legs[0]
        long_leg = trade.legs[1]

        assert short_leg.strike == expected_short
        assert long_leg.strike == expected_long

    def test_profile_6_atm_strike_rounding(self, market_row):
        """Test Profile 6 rounds ATM strikes to $1."""
        market_row['regime'] = 4  # Breaking Vol for Profile 6
        profile = Profile6VolOfVol()
        trade = profile.trade_constructor(market_row, "TEST_006")

        spot = market_row['close']  # 502.37
        expected_strike = round(spot)  # 502

        for leg in trade.legs:
            assert leg.strike == expected_strike

        assert abs(leg.strike - spot) <= 0.50

    def test_no_systematic_otm_bias(self):
        """Test that ATM selections don't have systematic OTM bias."""
        # Test with multiple spot prices
        test_spots = [
            500.23,  # round to 500
            500.63,  # round to 501
            502.12,  # round to 502
            502.88,  # round to 503
            505.49,  # round to 505
            505.51,  # round to 506
        ]

        for spot in test_spots:
            market_row = pd.Series({
                'date': pd.Timestamp('2023-01-15'),
                'close': spot,
                'RV20': 0.20,
                'regime': 1,
                'profile_1_score': 0.7
            })

            profile = Profile1LongDatedGamma()
            trade = profile.trade_constructor(market_row, f"TEST_{spot}")

            selected_strike = trade.legs[0].strike
            expected_strike = round(spot)

            # Verify correct strike selected
            assert selected_strike == expected_strike, \
                f"Spot {spot}: expected {expected_strike}, got {selected_strike}"

            # Verify it's truly closest
            distance = abs(selected_strike - spot)
            assert distance <= 0.50, \
                f"Spot {spot}: strike {selected_strike} is {distance:.2f} away (>$0.50)"

    def test_edge_case_exactly_halfway(self):
        """Test strike selection when spot is exactly halfway (X.50)."""
        # Python's round() uses banker's rounding (round to even)
        test_cases = [
            (500.50, 500),  # Rounds to even (500)
            (501.50, 502),  # Rounds to even (502)
            (502.50, 502),  # Rounds to even (502)
            (503.50, 504),  # Rounds to even (504)
        ]

        for spot, expected in test_cases:
            market_row = pd.Series({
                'date': pd.Timestamp('2023-01-15'),
                'close': spot,
                'RV20': 0.20,
                'regime': 1,
                'profile_1_score': 0.7
            })

            profile = Profile1LongDatedGamma()
            trade = profile.trade_constructor(market_row, f"TEST_{spot}")

            assert trade.legs[0].strike == expected, \
                f"Spot {spot}: expected {expected}, got {trade.legs[0].strike}"

    def test_old_5_dollar_rounding_is_gone(self):
        """Verify that $5 rounding no longer exists."""
        # With $5 rounding: 502.37 would round to 500 (2.37 points OTM - BAD)
        # With $1 rounding: 502.37 rounds to 502 (0.37 points - GOOD)

        spot = 502.37
        market_row = pd.Series({
            'date': pd.Timestamp('2023-01-15'),
            'close': spot,
            'RV20': 0.20,
            'regime': 1,
            'profile_1_score': 0.7
        })

        profile = Profile1LongDatedGamma()
        trade = profile.trade_constructor(market_row, "TEST_OLD_BUG")

        selected_strike = trade.legs[0].strike

        # OLD BUG: Would select 500 (round(502.37 / 5) * 5 = 100 * 5 = 500)
        old_bug_strike = round(spot / 5) * 5
        assert old_bug_strike == 500.0, "Old bug calculation changed"

        # NEW FIX: Should select 502
        assert selected_strike != old_bug_strike, \
            "Still using old $5 rounding logic!"
        assert selected_strike == 502, \
            f"Expected $1 rounding to 502, got {selected_strike}"

        # Verify improvement: new strike is closer to spot
        old_distance = abs(old_bug_strike - spot)  # 2.37
        new_distance = abs(selected_strike - spot)  # 0.37
        assert new_distance < old_distance, \
            f"New rounding not better: {new_distance:.2f} vs {old_distance:.2f}"

    def test_comparison_5_vs_1_dollar_rounding(self):
        """Compare $5 vs $1 rounding across many spot prices."""
        # Generate 100 random spot prices between 400-600
        np.random.seed(42)
        test_spots = np.random.uniform(400, 600, 100)

        distances_5_dollar = []
        distances_1_dollar = []

        for spot in test_spots:
            # Old method: $5 rounding
            strike_5 = round(spot / 5) * 5
            distance_5 = abs(strike_5 - spot)

            # New method: $1 rounding
            strike_1 = round(spot)
            distance_1 = abs(strike_1 - spot)

            distances_5_dollar.append(distance_5)
            distances_1_dollar.append(distance_1)

        # Statistics
        avg_distance_5 = np.mean(distances_5_dollar)
        avg_distance_1 = np.mean(distances_1_dollar)
        max_distance_5 = np.max(distances_5_dollar)
        max_distance_1 = np.max(distances_1_dollar)

        print(f"\n$5 Rounding - Avg distance: {avg_distance_5:.3f}, Max: {max_distance_5:.3f}")
        print(f"$1 Rounding - Avg distance: {avg_distance_1:.3f}, Max: {max_distance_1:.3f}")
        print(f"Improvement: {avg_distance_5 / avg_distance_1:.1f}x better")

        # Assertions
        assert avg_distance_1 < avg_distance_5, \
            "$1 rounding should have smaller avg distance"
        assert max_distance_1 <= 0.50, \
            "$1 rounding max distance should be ≤ $0.50"
        assert max_distance_5 > 2.0, \
            "$5 rounding had unacceptably large errors"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
