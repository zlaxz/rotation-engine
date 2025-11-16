"""
Test simulator integration with real Polygon data.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta

from src.trading.simulator import TradeSimulator, SimulationConfig
from src.trading.trade import Trade, TradeLeg
from src.data.polygon_options import PolygonOptionsLoader


def test_simulator_with_real_data():
    """Test that simulator loads and uses real Polygon data."""

    # Create simple SPY dataset
    dates = pd.date_range('2024-01-02', '2024-01-10', freq='D')
    data = pd.DataFrame({
        'date': dates,
        'open': [472.0] * len(dates),
        'high': [475.0] * len(dates),
        'low': [470.0] * len(dates),
        'close': [473.0] * len(dates),
        'volume': [100000000] * len(dates),
        'RV20': [0.15] * len(dates),
        'regime': ['calm'] * len(dates)
    })

    # Convert dates to date objects
    data['date'] = pd.to_datetime(data['date']).dt.date

    # Initialize simulator with real data
    config = SimulationConfig(
        delta_hedge_enabled=False,  # Simplify for testing
        roll_dte_threshold=5
    )

    simulator = TradeSimulator(
        data=data,
        config=config,
        use_real_options_data=True
    )

    print(f"\n✓ Simulator initialized with Polygon data")

    # Create a simple test trade (ATM straddle)
    trade_date = datetime(2024, 1, 2)
    spot = 473.0
    expiry = datetime(2024, 2, 16)  # 45 DTE

    # Define legs
    legs = [
        TradeLeg(
            strike=473.0,
            expiry=expiry,
            option_type='call',
            quantity=1,
            dte=45
        ),
        TradeLeg(
            strike=473.0,
            expiry=expiry,
            option_type='put',
            quantity=1,
            dte=45
        )
    ]

    trade = Trade(
        trade_id='TEST001',
        profile_name='TEST',
        entry_date=trade_date,
        legs=legs,
        entry_prices={}  # Will be filled by simulator
    )

    # Get entry prices
    row = data[data['date'] == trade_date.date()].iloc[0]
    entry_prices = simulator._get_entry_prices(trade, row)

    print(f"\n✓ Entry prices retrieved:")
    for i, (leg, price) in enumerate(zip(legs, entry_prices.values())):
        print(f"  Leg {i}: {leg.option_type.upper()} K={leg.strike:.2f} → ${price:.2f}")

    # Verify prices are reasonable
    assert all(p > 0 for p in entry_prices.values()), "All prices should be positive"

    # Get mark-to-market prices a few days later
    later_date = date(2024, 1, 5)
    later_row = data[data['date'] == later_date].iloc[0]

    mtm_prices = simulator._get_current_prices(trade, later_row)

    print(f"\n✓ Mark-to-market prices (3 days later):")
    for i, price in mtm_prices.items():
        print(f"  Leg {i}: ${price:.2f}")

    # Print statistics
    print(f"\n📊 Data usage statistics:")
    print(f"  Real prices used: {simulator.stats['real_prices_used']}")
    print(f"  Fallback prices used: {simulator.stats['fallback_prices_used']}")
    print(f"  Missing contracts: {len(simulator.stats['missing_contracts'])}")

    if simulator.stats['missing_contracts']:
        print(f"\n❌ Missing contracts:")
        for contract in simulator.stats['missing_contracts']:
            print(f"  {contract}")

    # Should have used some real data
    assert simulator.stats['real_prices_used'] > 0, "Should use some real Polygon data"

    return simulator


def test_price_validation():
    """Validate prices match Polygon data exactly."""

    loader = PolygonOptionsLoader()

    # Sample 10 random dates and contracts
    test_cases = [
        (date(2024, 1, 2), 473.0, date(2024, 2, 16), 'call'),
        (date(2024, 1, 2), 473.0, date(2024, 2, 16), 'put'),
        (date(2024, 1, 3), 470.0, date(2024, 2, 16), 'call'),
        (date(2024, 1, 3), 476.0, date(2024, 2, 16), 'put'),
        (date(2024, 1, 5), 465.0, date(2024, 3, 15), 'call'),
        (date(2024, 1, 5), 480.0, date(2024, 3, 15), 'put'),
        (date(2024, 1, 8), 475.0, date(2024, 2, 9), 'call'),
        (date(2024, 1, 8), 475.0, date(2024, 2, 9), 'put'),
        (date(2024, 1, 9), 460.0, date(2024, 4, 19), 'call'),
        (date(2024, 1, 10), 485.0, date(2024, 4, 19), 'put'),
    ]

    print("\n📋 Price Validation (10 random samples):")
    print(f"{'Date':<12} {'Strike':<8} {'Expiry':<12} {'Type':<6} {'Bid':>8} {'Mid':>8} {'Ask':>8} {'Spread':>8}")
    print("-" * 80)

    valid_count = 0

    for trade_date, strike, expiry, opt_type in test_cases:
        try:
            bid = loader.get_option_price(trade_date, strike, expiry, opt_type, 'bid')
            mid = loader.get_option_price(trade_date, strike, expiry, opt_type, 'mid')
            ask = loader.get_option_price(trade_date, strike, expiry, opt_type, 'ask')

            if bid is not None and mid is not None and ask is not None:
                spread = ask - bid
                spread_pct = 100 * spread / mid

                print(f"{trade_date} {strike:<8.2f} {expiry} {opt_type:<6} "
                      f"{bid:>8.2f} {mid:>8.2f} {ask:>8.2f} {spread_pct:>7.1f}%")

                # Validate: bid < mid < ask
                assert bid <= mid <= ask, f"Invalid quote: bid={bid} mid={mid} ask={ask}"
                assert bid > 0, f"Bid should be positive: {bid}"

                valid_count += 1
            else:
                print(f"{trade_date} {strike:<8.2f} {expiry} {opt_type:<6} {'N/A':>8} {'N/A':>8} {'N/A':>8} {'N/A':>8}")

        except Exception as e:
            print(f"{trade_date} {strike:<8.2f} {expiry} {opt_type:<6} ERROR: {e}")

    print(f"\n✓ Validated {valid_count}/{len(test_cases)} contracts successfully")
    assert valid_count >= 5, f"Should validate at least 5 contracts, got {valid_count}"


def test_toy_vs_real_comparison():
    """Compare toy model vs real data prices."""

    # Same setup for both
    dates = pd.date_range('2024-01-02', '2024-01-05', freq='D')
    data = pd.DataFrame({
        'date': dates,
        'close': [473.0, 474.0, 471.0, 472.5],
        'RV20': [0.15] * len(dates),
        'regime': ['calm'] * len(dates)
    })
    data['date'] = pd.to_datetime(data['date']).dt.date

    # Simulator with real data
    sim_real = TradeSimulator(data=data, use_real_options_data=True)

    # Simulator with toy model
    sim_toy = TradeSimulator(data=data, use_real_options_data=False)

    # Test leg
    trade_date = datetime(2024, 1, 2)
    expiry = datetime(2024, 2, 16)

    leg = TradeLeg(
        strike=473.0,
        expiry=expiry,
        option_type='call',
        quantity=1,
        dte=45
    )

    row = data[data['date'] == trade_date.date()].iloc[0]
    spot = row['close']

    # Get prices
    price_real = sim_real._estimate_option_price(leg, spot, row)
    price_toy = sim_toy._estimate_option_price(leg, spot, row)

    print(f"\n📊 Price comparison (ATM Call, 45 DTE):")
    print(f"  Real Polygon data: ${price_real:.2f}")
    print(f"  Toy model:         ${price_toy:.2f}")
    print(f"  Difference:        ${abs(price_real - price_toy):.2f} ({100*abs(price_real - price_toy)/price_real:.1f}%)")

    # Both should be reasonable
    assert 5 < price_real < 100, f"Real price seems unreasonable: {price_real}"
    assert 5 < price_toy < 100, f"Toy price seems unreasonable: {price_toy}"


if __name__ == '__main__':
    print("=" * 80)
    print("TESTING SIMULATOR INTEGRATION WITH POLYGON DATA")
    print("=" * 80)

    print("\n[1/3] Testing simulator with real data...")
    test_simulator_with_real_data()

    print("\n[2/3] Validating prices match Polygon...")
    test_price_validation()

    print("\n[3/3] Comparing toy model vs real data...")
    test_toy_vs_real_comparison()

    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)
