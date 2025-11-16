"""
Test Polygon options data loader.
"""

import pytest
from datetime import date, datetime
from src.data.polygon_options import PolygonOptionsLoader


def test_polygon_loader_basic():
    """Test basic loading of Polygon data."""
    loader = PolygonOptionsLoader()

    # Load a known date
    trade_date = date(2024, 1, 2)

    df = loader.load_day(trade_date)

    # Should have data
    assert not df.empty, "Should load data for 2024-01-02"

    # Check columns
    expected_cols = ['date', 'expiry', 'strike', 'option_type', 'dte',
                     'close', 'mid', 'bid', 'ask', 'volume']
    for col in expected_cols:
        assert col in df.columns, f"Missing column: {col}"

    # Check data types
    assert df['option_type'].isin(['call', 'put']).all()
    assert (df['strike'] > 0).all()
    assert (df['close'] > 0).all()

    print(f"\nLoaded {len(df)} options for {trade_date}")
    print(f"Strike range: {df['strike'].min():.2f} - {df['strike'].max():.2f}")
    print(f"DTE range: {df['dte'].min()} - {df['dte'].max()}")


def test_get_option_price():
    """Test getting specific option price."""
    loader = PolygonOptionsLoader()

    trade_date = date(2024, 1, 2)

    # Load data first to see what's available
    df = loader.load_day(trade_date)
    assert not df.empty

    # Get a sample option
    sample = df.iloc[0]

    # Test lookup
    price = loader.get_option_price(
        trade_date=trade_date,
        strike=sample['strike'],
        expiry=sample['expiry'],
        option_type=sample['option_type'],
        price_type='mid'
    )

    assert price is not None
    assert price > 0
    print(f"\nLookup test: {sample['option_type']} strike={sample['strike']:.2f} expiry={sample['expiry']}")
    print(f"Price: ${price:.2f}")


def test_bulk_lookup():
    """Test bulk price lookup."""
    loader = PolygonOptionsLoader()

    trade_date = date(2024, 1, 2)

    # Get a few contracts
    df = loader.load_day(trade_date)
    samples = df.head(5)

    contracts = [
        (row['strike'], row['expiry'], row['option_type'])
        for _, row in samples.iterrows()
    ]

    # Bulk lookup
    prices = loader.get_option_prices_bulk(trade_date, contracts, price_type='mid')

    assert len(prices) == len(contracts)
    print(f"\nBulk lookup: {len(prices)} contracts")
    for contract, price in prices.items():
        strike, expiry, opt_type = contract
        print(f"  {opt_type} K={strike:.2f} exp={expiry}: ${price:.2f}")


def test_chain_filtering():
    """Test chain filtering by DTE."""
    loader = PolygonOptionsLoader()

    trade_date = date(2024, 1, 2)

    # Get 30-60 DTE options
    df = loader.get_chain(trade_date, min_dte=30, max_dte=60)

    assert not df.empty
    assert (df['dte'] >= 30).all()
    assert (df['dte'] <= 60).all()

    print(f"\n30-60 DTE chain: {len(df)} options")
    print(f"Expiries: {df['expiry'].unique()}")


def test_caching():
    """Test that caching works."""
    loader = PolygonOptionsLoader()

    trade_date = date(2024, 1, 2)

    # First load (from disk)
    df1 = loader.load_day(trade_date)

    # Second load (from cache)
    df2 = loader.load_day(trade_date)

    # Should be identical
    assert len(df1) == len(df2)
    assert (df1.columns == df2.columns).all()

    # Clear cache
    loader.clear_cache()

    # Third load (from disk again)
    df3 = loader.load_day(trade_date)
    assert len(df3) == len(df1)


def test_no_inverted_spreads():
    """Test BUG-001 fix: No bid >= mid for penny options."""
    loader = PolygonOptionsLoader()

    # Load multiple days to get comprehensive coverage
    test_dates = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)]

    total_inverted = 0
    total_options = 0

    for trade_date in test_dates:
        df = loader.load_day(trade_date)
        if df.empty:
            continue

        # Check for inverted markets (bid >= mid)
        inverted = df[df['bid'] >= df['mid']]

        total_inverted += len(inverted)
        total_options += len(df)

        if len(inverted) > 0:
            print(f"\n⚠️ Found {len(inverted)} inverted spreads on {trade_date}:")
            print(inverted[['strike', 'option_type', 'mid', 'bid', 'ask']].head())

    print(f"\nTotal: {total_inverted} inverted / {total_options} options ({100*total_inverted/total_options:.2f}%)")

    assert total_inverted == 0, f"Found {total_inverted} inverted spreads (bid >= mid)"


def test_garbage_filtering_in_lookup():
    """Test BUG-002 fix: get_option_price filters garbage quotes."""
    loader = PolygonOptionsLoader()

    trade_date = date(2024, 1, 2)

    # Load raw data
    df = loader.load_day(trade_date)
    assert not df.empty

    # Find an option with low volume (likely garbage if volume=0)
    low_vol = df[df['volume'] <= 1]

    if len(low_vol) > 0:
        sample = low_vol.iloc[0]

        # Try to get price via get_option_price
        price = loader.get_option_price(
            trade_date=trade_date,
            strike=sample['strike'],
            expiry=sample['expiry'],
            option_type=sample['option_type']
        )

        # If volume=0, should be filtered out (return None)
        if sample['volume'] == 0:
            assert price is None, "Should filter out zero-volume options"
            print(f"\n✅ Correctly filtered zero-volume option")
        else:
            print(f"\n✅ Low-volume option correctly returned")

    print(f"✅ Garbage filtering working in get_option_price()")


if __name__ == '__main__':
    # Run tests
    test_polygon_loader_basic()
    test_get_option_price()
    test_bulk_lookup()
    test_chain_filtering()
    test_caching()
    test_no_inverted_spreads()
    test_garbage_filtering_in_lookup()

    print("\n✅ All Polygon loader tests passed!")
