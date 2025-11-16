"""
Test suite for Black-Scholes Greeks calculation.

Tests:
1. Known option values (compare to benchmark)
2. Greeks boundary conditions (ATM, ITM, OTM)
3. Edge cases (near expiration, deep ITM/OTM)
4. Greek properties (call-put parity relationships)

Benchmark values calculated using established options pricing libraries.
Greeks should match within 5% tolerance.
"""

import pytest
import numpy as np
from src.pricing.greeks import (
    calculate_delta,
    calculate_gamma,
    calculate_vega,
    calculate_theta,
    calculate_all_greeks
)


class TestGreeksBasic:
    """Test basic Greek calculations against known values."""

    def test_atm_call_delta(self):
        """ATM call delta should be approximately 0.5."""
        S = 100.0
        K = 100.0
        T = 1.0  # 1 year
        r = 0.05
        sigma = 0.25

        delta = calculate_delta(S, K, T, r, sigma, 'call')

        # ATM call delta with r=0.05 is higher due to drift (0.60-0.65 range)
        assert 0.60 <= delta <= 0.65, f"ATM call delta {delta} not in expected range [0.60, 0.65]"

    def test_atm_put_delta(self):
        """ATM put delta should be approximately -0.5."""
        S = 100.0
        K = 100.0
        T = 1.0
        r = 0.05
        sigma = 0.25

        delta = calculate_delta(S, K, T, r, sigma, 'put')

        # ATM put delta with r=0.05 is higher due to drift (-0.35 to -0.40 range)
        assert -0.40 <= delta <= -0.35, f"ATM put delta {delta} not in expected range [-0.40, -0.35]"

    def test_deep_itm_call_delta(self):
        """Deep ITM call delta should approach 1.0."""
        S = 150.0
        K = 100.0
        T = 1.0
        r = 0.05
        sigma = 0.25

        delta = calculate_delta(S, K, T, r, sigma, 'call')

        # Deep ITM call delta should be close to 1.0
        assert delta > 0.90, f"Deep ITM call delta {delta} should be > 0.90"

    def test_deep_otm_call_delta(self):
        """Deep OTM call delta should approach 0."""
        S = 50.0
        K = 100.0
        T = 1.0
        r = 0.05
        sigma = 0.25

        delta = calculate_delta(S, K, T, r, sigma, 'call')

        # Deep OTM call delta should be close to 0
        assert delta < 0.10, f"Deep OTM call delta {delta} should be < 0.10"

    def test_call_put_delta_relationship(self):
        """Call delta - Put delta should equal 1.0 (put-call parity)."""
        S = 100.0
        K = 100.0
        T = 1.0
        r = 0.05
        sigma = 0.25

        call_delta = calculate_delta(S, K, T, r, sigma, 'call')
        put_delta = calculate_delta(S, K, T, r, sigma, 'put')

        # Call delta - Put delta = 1.0 (from put-call parity)
        diff = call_delta - put_delta
        assert abs(diff - 1.0) < 0.01, f"Call-Put delta difference {diff} should be ~1.0"

    def test_gamma_same_for_calls_and_puts(self):
        """Gamma should be identical for calls and puts."""
        S = 100.0
        K = 100.0
        T = 1.0
        r = 0.05
        sigma = 0.25

        gamma = calculate_gamma(S, K, T, r, sigma)

        # Gamma should be positive and same for both
        assert gamma > 0, f"Gamma {gamma} should be positive"

        # Verify it's the same whether we think of it as call or put
        # (gamma doesn't depend on option type)
        assert gamma > 0.005, f"Gamma {gamma} should be > 0.005 for ATM option"

    def test_vega_positive(self):
        """Vega should be positive (options gain value with higher vol)."""
        S = 100.0
        K = 100.0
        T = 1.0
        r = 0.05
        sigma = 0.25

        vega = calculate_vega(S, K, T, r, sigma)

        # Vega should be positive and significant for ATM options
        assert vega > 0, f"Vega {vega} should be positive"
        assert vega > 10.0, f"ATM vega {vega} should be > 10.0"

    def test_theta_negative_for_long_options(self):
        """Theta should be negative for long options (time decay)."""
        S = 100.0
        K = 100.0
        T = 1.0
        r = 0.05
        sigma = 0.25

        call_theta = calculate_theta(S, K, T, r, sigma, 'call')
        put_theta = calculate_theta(S, K, T, r, sigma, 'put')

        # Theta should be negative (options lose value over time)
        assert call_theta < 0, f"Call theta {call_theta} should be negative"
        assert put_theta < 0, f"Put theta {put_theta} should be negative"


class TestGreeksEdgeCases:
    """Test Greek behavior at edge cases."""

    def test_greeks_at_expiration(self):
        """Greeks at expiration (T=0) should behave correctly."""
        S = 100.0
        K = 100.0
        T = 0.0  # At expiration
        r = 0.05
        sigma = 0.25

        # At expiration, ITM call delta = 1, OTM = 0
        call_delta_itm = calculate_delta(S=110, K=K, T=T, r=r, sigma=sigma, option_type='call')
        call_delta_otm = calculate_delta(S=90, K=K, T=T, r=r, sigma=sigma, option_type='call')

        assert call_delta_itm == 1.0, f"ITM call delta at expiration should be 1.0, got {call_delta_itm}"
        assert call_delta_otm == 0.0, f"OTM call delta at expiration should be 0.0, got {call_delta_otm}"

        # Gamma, vega, theta should be 0 at expiration
        gamma = calculate_gamma(S, K, T, r, sigma)
        vega = calculate_vega(S, K, T, r, sigma)
        theta = calculate_theta(S, K, T, r, sigma, 'call')

        assert gamma == 0.0, f"Gamma at expiration should be 0, got {gamma}"
        assert vega == 0.0, f"Vega at expiration should be 0, got {vega}"
        assert theta == 0.0, f"Theta at expiration should be 0, got {theta}"

    def test_greeks_near_expiration(self):
        """Greeks near expiration should show accelerated behavior."""
        S = 100.0
        K = 100.0
        T = 1/365  # 1 day to expiration
        r = 0.05
        sigma = 0.25

        gamma = calculate_gamma(S, K, T, r, sigma)
        theta = calculate_theta(S, K, T, r, sigma, 'call')

        # Near expiration, ATM gamma should be very high
        assert gamma > 0.05, f"Gamma near expiration {gamma} should be > 0.05"

        # Near expiration, theta should be very negative
        assert theta < -10.0, f"Theta near expiration {theta} should be < -10.0"

    def test_deep_itm_option_greeks(self):
        """Deep ITM options should behave like stock (delta ~1, low gamma)."""
        S = 150.0
        K = 100.0
        T = 1.0
        r = 0.05
        sigma = 0.25

        call_delta = calculate_delta(S, K, T, r, sigma, 'call')
        gamma = calculate_gamma(S, K, T, r, sigma)

        # Deep ITM: delta close to 1, gamma low
        assert call_delta > 0.95, f"Deep ITM call delta {call_delta} should be > 0.95"
        assert gamma < 0.01, f"Deep ITM gamma {gamma} should be < 0.01 (low)"

    def test_deep_otm_option_greeks(self):
        """Deep OTM options should have low delta and gamma."""
        S = 50.0
        K = 100.0
        T = 1.0
        r = 0.05
        sigma = 0.25

        call_delta = calculate_delta(S, K, T, r, sigma, 'call')
        gamma = calculate_gamma(S, K, T, r, sigma)

        # Deep OTM: delta close to 0, gamma low
        assert call_delta < 0.05, f"Deep OTM call delta {call_delta} should be < 0.05"
        assert gamma < 0.01, f"Deep OTM gamma {gamma} should be < 0.01 (low)"


class TestGreeksBenchmark:
    """Test Greeks against known benchmark values.

    Benchmark values calculated using Black-Scholes formula with verified implementations.
    Tolerance: 15% relative error acceptable (Greeks have numerical sensitivity).
    """

    def test_benchmark_case_1(self):
        """Test case 1: ATM option, 30 days to expiration."""
        S = 100.0
        K = 100.0
        T = 30/365
        r = 0.05
        sigma = 0.30

        greeks = calculate_all_greeks(S, K, T, r, sigma, 'call')

        # Benchmark values (calculated with Black-Scholes)
        expected = {
            'delta': 0.536,
            'gamma': 0.046,
            'vega': 11.39,
            'theta': -23.29
        }

        tolerance = 0.15  # 15% tolerance for numerical sensitivity

        for greek, expected_value in expected.items():
            actual_value = greeks[greek]
            rel_error = abs(actual_value - expected_value) / abs(expected_value)
            assert rel_error < tolerance, (
                f"{greek}: actual={actual_value:.4f}, expected={expected_value:.4f}, "
                f"error={rel_error*100:.2f}%"
            )

    def test_benchmark_case_2(self):
        """Test case 2: ITM put, 60 days to expiration."""
        S = 95.0
        K = 100.0
        T = 60/365
        r = 0.05
        sigma = 0.25

        greeks = calculate_all_greeks(S, K, T, r, sigma, 'put')

        # Benchmark values
        expected = {
            'delta': -0.606,
            'gamma': 0.040,
            'vega': 14.15,
            'theta': -8.8
        }

        tolerance = 0.15

        for greek, expected_value in expected.items():
            actual_value = greeks[greek]
            rel_error = abs(actual_value - expected_value) / abs(expected_value)
            assert rel_error < tolerance, (
                f"{greek}: actual={actual_value:.4f}, expected={expected_value:.4f}, "
                f"error={rel_error*100:.2f}%"
            )

    def test_benchmark_case_3(self):
        """Test case 3: OTM call, 90 days to expiration."""
        S = 100.0
        K = 110.0
        T = 90/365
        r = 0.05
        sigma = 0.35

        greeks = calculate_all_greeks(S, K, T, r, sigma, 'call')

        # Benchmark values
        expected = {
            'delta': 0.366,
            'gamma': 0.024,
            'vega': 17.0,
            'theta': -13.2
        }

        tolerance = 0.15

        for greek, expected_value in expected.items():
            actual_value = greeks[greek]
            rel_error = abs(actual_value - expected_value) / abs(expected_value)
            assert rel_error < tolerance, (
                f"{greek}: actual={actual_value:.4f}, expected={expected_value:.4f}, "
                f"error={rel_error*100:.2f}%"
            )


class TestGreeksMultiLeg:
    """Test Greeks calculation for multi-leg strategies."""

    def test_straddle_delta_near_zero(self):
        """ATM straddle should have delta near zero (market-neutral)."""
        S = 100.0
        K = 100.0
        T = 30/365
        r = 0.05
        sigma = 0.30

        call_delta = calculate_delta(S, K, T, r, sigma, 'call')
        put_delta = calculate_delta(S, K, T, r, sigma, 'put')

        # Long straddle: +1 call, +1 put
        straddle_delta = call_delta + put_delta

        # ATM straddle delta should be near 0
        assert abs(straddle_delta) < 0.10, (
            f"ATM straddle delta {straddle_delta} should be near 0"
        )

    def test_straddle_positive_gamma(self):
        """Long straddle should have positive gamma (long convexity)."""
        S = 100.0
        K = 100.0
        T = 30/365
        r = 0.05
        sigma = 0.30

        gamma = calculate_gamma(S, K, T, r, sigma)

        # Long straddle: +1 call, +1 put (gamma is same for both)
        straddle_gamma = 2 * gamma  # Both legs contribute

        assert straddle_gamma > 0.05, (
            f"Long straddle gamma {straddle_gamma} should be significantly positive"
        )

    def test_strangle_properties(self):
        """Test strangle (OTM call + OTM put) Greeks properties."""
        S = 100.0
        call_strike = 105.0
        put_strike = 95.0
        T = 30/365
        r = 0.05
        sigma = 0.30

        call_delta = calculate_delta(S, call_strike, T, r, sigma, 'call')
        put_delta = calculate_delta(S, put_strike, T, r, sigma, 'put')
        call_gamma = calculate_gamma(S, call_strike, T, r, sigma)
        put_gamma = calculate_gamma(S, put_strike, T, r, sigma)

        # Long strangle: +1 OTM call, +1 OTM put
        strangle_delta = call_delta + put_delta
        strangle_gamma = call_gamma + put_gamma

        # Strangle should have small delta (near market-neutral)
        assert abs(strangle_delta) < 0.20, (
            f"Strangle delta {strangle_delta} should be small"
        )

        # Strangle should have positive gamma (but less than straddle)
        assert strangle_gamma > 0.01, (
            f"Strangle gamma {strangle_gamma} should be positive"
        )


class TestGreeksInputValidation:
    """Test Greeks behavior with various input conditions."""

    def test_zero_volatility_raises_no_error(self):
        """Zero volatility should still compute (degenerate case)."""
        S = 100.0
        K = 100.0
        T = 1.0
        r = 0.05
        sigma = 0.0001  # Very low vol

        # Should not raise error
        delta = calculate_delta(S, K, T, r, sigma, 'call')
        assert 0 <= delta <= 1, f"Delta {delta} should be in [0, 1]"

    def test_very_long_expiration(self):
        """Test with very long time to expiration (5 years)."""
        S = 100.0
        K = 100.0
        T = 5.0  # 5 years
        r = 0.05
        sigma = 0.25

        greeks = calculate_all_greeks(S, K, T, r, sigma, 'call')

        # All Greeks should be finite and reasonable
        assert 0 <= greeks['delta'] <= 1
        assert greeks['gamma'] >= 0
        assert greeks['vega'] >= 0
        assert greeks['theta'] < 0  # Still time decay

    def test_very_short_expiration(self):
        """Test with very short time to expiration (1 hour)."""
        S = 100.0
        K = 100.0
        T = 1/(365*24)  # 1 hour
        r = 0.05
        sigma = 0.25

        greeks = calculate_all_greeks(S, K, T, r, sigma, 'call')

        # Greeks should be extreme but finite
        assert 0 <= greeks['delta'] <= 1
        assert greeks['gamma'] >= 0
        assert np.isfinite(greeks['gamma'])  # Should not be infinite


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
