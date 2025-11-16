"""
Test ExecutionModel integration with PolygonOptionsLoader.

Validates:
- Spreads vary by moneyness (ATM vs OTM)
- Spreads vary by DTE (short-dated wider than long-dated)
- Spreads vary by volatility (high vol wider than low vol)
- No flat 2% spreads when spot_price provided
- Backward compatibility (fallback to 2% without spot_price)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import date
from src.data.polygon_options import PolygonOptionsLoader
from src.trading.execution import ExecutionModel


@pytest.fixture
def loader():
    """Polygon options loader with default ExecutionModel."""
    return PolygonOptionsLoader()


@pytest.fixture
def custom_loader():
    """Polygon options loader with custom ExecutionModel for testing."""
    exec_model = ExecutionModel(
        base_spread_atm=1.00,  # Higher base for testing
        base_spread_otm=0.60,
        spread_multiplier_vol=1.5
    )
    return PolygonOptionsLoader(execution_model=exec_model)


def test_spreads_vary_by_moneyness(loader):
    """
    CRITICAL: Verify ATM spreads < OTM spreads.

    Moneyness = abs(strike - spot) / spot
    ATM: moneyness ~0.0
    OTM: moneyness ~0.05-0.10

    ExecutionModel widens spreads linearly with moneyness.
    """
    trade_date = date(2024, 1, 2)
    spot_price = 475.0  # SPY around $475 in Jan 2024
    rv_20 = 0.12  # 12% annualized vol

    # Load chain with realistic spreads
    chain = loader.get_chain(
        trade_date,
        min_dte=30,
        max_dte=60,
        spot_price=spot_price,
        rv_20=rv_20
    )

    assert not chain.empty, "Chain should have data for 2024-01-02"

    # Separate ATM vs OTM options
    chain['moneyness'] = abs(chain['strike'] - spot_price) / spot_price

    atm_options = chain[chain['moneyness'] < 0.01].copy()  # Within 1% of ATM
    otm_options = chain[chain['moneyness'] > 0.05].copy()  # 5%+ OTM

    assert len(atm_options) > 0, "Should have ATM options"
    assert len(otm_options) > 0, "Should have OTM options"

    # Calculate spreads
    atm_options['spread'] = atm_options['ask'] - atm_options['bid']
    otm_options['spread'] = otm_options['ask'] - otm_options['bid']

    atm_median_spread = atm_options['spread'].median()
    otm_median_spread = otm_options['spread'].median()

    # OTM spreads should be wider than ATM spreads
    assert otm_median_spread > atm_median_spread, \
        f"OTM spreads ({otm_median_spread:.3f}) should be wider than ATM spreads ({atm_median_spread:.3f})"

    # Spread should widen at least 10% for OTM (model has minimum spread floor)
    spread_ratio = otm_median_spread / atm_median_spread
    assert spread_ratio > 1.10, \
        f"OTM/ATM spread ratio ({spread_ratio:.2f}) should be >1.10x"

    print(f"✓ ATM median spread: ${atm_median_spread:.3f}")
    print(f"✓ OTM median spread: ${otm_median_spread:.3f}")
    print(f"✓ OTM/ATM ratio: {spread_ratio:.2f}x")


def test_spreads_vary_by_dte(loader):
    """
    CRITICAL: Verify short-dated spreads > long-dated spreads.

    ExecutionModel widens spreads for DTE < 7 days.
    """
    trade_date = date(2024, 1, 2)
    spot_price = 475.0
    rv_20 = 0.12

    # Load chain
    chain = loader.get_chain(
        trade_date,
        spot_price=spot_price,
        rv_20=rv_20
    )

    assert not chain.empty, "Chain should have data"

    # Separate short-dated vs long-dated (filter to near-ATM to isolate DTE effect)
    chain['moneyness'] = abs(chain['strike'] - spot_price) / spot_price
    near_atm = chain[chain['moneyness'] < 0.03].copy()  # Within 3% of ATM

    short_dated = near_atm[near_atm['dte'] <= 7].copy()
    long_dated = near_atm[(near_atm['dte'] >= 45) & (near_atm['dte'] <= 60)].copy()

    if len(short_dated) == 0 or len(long_dated) == 0:
        pytest.skip("Need both short-dated and long-dated options for this test")

    # Calculate spreads
    short_dated['spread'] = short_dated['ask'] - short_dated['bid']
    long_dated['spread'] = long_dated['ask'] - long_dated['bid']

    short_median = short_dated['spread'].median()
    long_median = long_dated['spread'].median()

    # Short-dated spreads should be wider
    assert short_median > long_median, \
        f"Short-dated spreads ({short_median:.3f}) should be wider than long-dated ({long_median:.3f})"

    spread_ratio = short_median / long_median
    assert spread_ratio > 1.1, \
        f"Short/long spread ratio ({spread_ratio:.2f}) should be >1.1x"

    print(f"✓ Short-dated (≤7 DTE) median spread: ${short_median:.3f}")
    print(f"✓ Long-dated (45-60 DTE) median spread: ${long_median:.3f}")
    print(f"✓ Short/long ratio: {spread_ratio:.2f}x")


def test_spreads_vary_by_volatility(loader):
    """
    CRITICAL: Verify high-vol spreads > low-vol spreads.

    ExecutionModel widens spreads when VIX > 30.
    """
    trade_date = date(2024, 1, 2)
    spot_price = 475.0

    # Load chain with low volatility
    chain_low_vol = loader.get_chain(
        trade_date,
        min_dte=30,
        max_dte=60,
        spot_price=spot_price,
        rv_20=0.10  # Low vol (VIX ~12)
    )

    # Load chain with high volatility
    chain_high_vol = loader.get_chain(
        trade_date,
        min_dte=30,
        max_dte=60,
        spot_price=spot_price,
        rv_20=0.30  # High vol (VIX ~36)
    )

    assert not chain_low_vol.empty and not chain_high_vol.empty, "Need data for both vol scenarios"

    # Filter to ATM options (isolate vol effect)
    chain_low_vol['moneyness'] = abs(chain_low_vol['strike'] - spot_price) / spot_price
    chain_high_vol['moneyness'] = abs(chain_high_vol['strike'] - spot_price) / spot_price

    atm_low_vol = chain_low_vol[chain_low_vol['moneyness'] < 0.01].copy()
    atm_high_vol = chain_high_vol[chain_high_vol['moneyness'] < 0.01].copy()

    if len(atm_low_vol) == 0 or len(atm_high_vol) == 0:
        pytest.skip("Need ATM options for both vol scenarios")

    # Calculate spreads
    atm_low_vol['spread'] = atm_low_vol['ask'] - atm_low_vol['bid']
    atm_high_vol['spread'] = atm_high_vol['ask'] - atm_high_vol['bid']

    low_vol_median = atm_low_vol['spread'].median()
    high_vol_median = atm_high_vol['spread'].median()

    # High vol spreads should be wider
    assert high_vol_median > low_vol_median, \
        f"High vol spreads ({high_vol_median:.3f}) should be wider than low vol ({low_vol_median:.3f})"

    spread_ratio = high_vol_median / low_vol_median
    assert spread_ratio > 1.3, \
        f"High/low vol spread ratio ({spread_ratio:.2f}) should be >1.3x"

    print(f"✓ Low vol (RV=10%) median spread: ${low_vol_median:.3f}")
    print(f"✓ High vol (RV=30%) median spread: ${high_vol_median:.3f}")
    print(f"✓ High/low vol ratio: {spread_ratio:.2f}x")


def test_no_flat_percentage_spreads(loader):
    """
    CRITICAL: Verify spreads are NOT flat 2% when spot_price provided.

    Old bug: Every option had exactly 2% spread regardless of moneyness/DTE.
    Fixed: Spreads vary by option characteristics.
    """
    trade_date = date(2024, 1, 2)
    spot_price = 475.0
    rv_20 = 0.12

    chain = loader.get_chain(
        trade_date,
        min_dte=7,
        max_dte=90,
        spot_price=spot_price,
        rv_20=rv_20
    )

    assert not chain.empty, "Need options data"

    # Calculate spread as percentage of mid
    chain['spread_pct'] = (chain['ask'] - chain['bid']) / chain['mid'] * 100

    # Check spread distribution
    spread_std = chain['spread_pct'].std()
    spread_min = chain['spread_pct'].min()
    spread_max = chain['spread_pct'].max()

    # Spreads should vary (std > 0.5%)
    assert spread_std > 0.5, \
        f"Spread std ({spread_std:.2f}%) should be >0.5% (not flat)"

    # Spread range should be wide (not all 2%)
    spread_range = spread_max - spread_min
    assert spread_range > 3.0, \
        f"Spread range ({spread_range:.2f}%) should be >3% (not flat)"

    # Count options with exactly 2% spread (should be near zero)
    flat_2pct = chain[(chain['spread_pct'] > 1.99) & (chain['spread_pct'] < 2.01)]
    flat_pct = len(flat_2pct) / len(chain) * 100

    assert flat_pct < 10.0, \
        f"{flat_pct:.1f}% of options have flat 2% spread (should be <10%)"

    print(f"✓ Spread std: {spread_std:.2f}%")
    print(f"✓ Spread range: {spread_min:.2f}% to {spread_max:.2f}%")
    print(f"✓ Flat 2% spreads: {flat_pct:.1f}% (should be low)")


def test_atm_spread_magnitude(loader):
    """
    CRITICAL: Verify ATM spreads are $0.75-$1.50 as per ExecutionModel.

    ExecutionModel defaults: base_spread_atm = $0.75
    With moneyness/DTE factors, ATM spreads should be ~$0.75-$1.50.
    """
    trade_date = date(2024, 1, 2)
    spot_price = 475.0
    rv_20 = 0.12

    chain = loader.get_chain(
        trade_date,
        min_dte=30,
        max_dte=60,
        spot_price=spot_price,
        rv_20=rv_20
    )

    assert not chain.empty, "Need options data"

    # Filter to ATM options
    chain['moneyness'] = abs(chain['strike'] - spot_price) / spot_price
    atm_options = chain[chain['moneyness'] < 0.01].copy()

    assert len(atm_options) > 0, "Should have ATM options"

    # Calculate spreads
    atm_options['spread'] = atm_options['ask'] - atm_options['bid']

    median_spread = atm_options['spread'].median()
    mean_spread = atm_options['spread'].mean()

    # ATM spreads should be in realistic range
    assert 0.50 <= median_spread <= 2.00, \
        f"ATM median spread (${median_spread:.3f}) should be $0.50-$2.00"

    # Most ATM spreads should be $0.75-$1.50
    in_range = atm_options[(atm_options['spread'] >= 0.75) & (atm_options['spread'] <= 1.50)]
    pct_in_range = len(in_range) / len(atm_options) * 100

    assert pct_in_range > 30.0, \
        f"{pct_in_range:.1f}% of ATM spreads in $0.75-$1.50 range (should be >30%)"

    print(f"✓ ATM median spread: ${median_spread:.3f}")
    print(f"✓ ATM mean spread: ${mean_spread:.3f}")
    print(f"✓ {pct_in_range:.1f}% in $0.75-$1.50 range")


def test_backward_compatibility_without_spot(loader):
    """
    Verify backward compatibility: Falls back to 2% spread if spot_price not provided.

    Should issue warning but not break.
    """
    trade_date = date(2024, 1, 2)

    # Load without spot_price (should trigger warning)
    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        chain = loader.get_chain(trade_date, min_dte=30, max_dte=60)

        # Should have triggered warning
        assert len(w) > 0, "Should warn about missing spot_price"
        assert "spot_price" in str(w[-1].message).lower()

    assert not chain.empty, "Should still return data"

    # Spreads should be close to 2% (fallback behavior)
    chain['spread_pct'] = (chain['ask'] - chain['bid']) / chain['mid'] * 100

    median_spread_pct = chain['spread_pct'].median()

    # Should be near 2% with low variance (flat spread)
    assert 1.8 <= median_spread_pct <= 2.2, \
        f"Fallback spread ({median_spread_pct:.2f}%) should be ~2%"

    print(f"✓ Fallback median spread: {median_spread_pct:.2f}%")
    print(f"✓ Backward compatibility maintained")


def test_custom_execution_model(custom_loader):
    """
    Verify custom ExecutionModel parameters are used.

    Custom model has base_spread_atm = $1.00 (vs default $0.75).
    """
    trade_date = date(2024, 1, 2)
    spot_price = 475.0
    rv_20 = 0.12

    chain = custom_loader.get_chain(
        trade_date,
        min_dte=30,
        max_dte=60,
        spot_price=spot_price,
        rv_20=rv_20
    )

    assert not chain.empty, "Need options data"

    # Filter to ATM options
    chain['moneyness'] = abs(chain['strike'] - spot_price) / spot_price
    atm_options = chain[chain['moneyness'] < 0.01].copy()

    assert len(atm_options) > 0, "Should have ATM options"

    # Calculate spreads
    atm_options['spread'] = atm_options['ask'] - atm_options['bid']
    median_spread = atm_options['spread'].median()

    # Spreads should be higher with custom model (base $1.00 vs default $0.75)
    assert median_spread > 0.90, \
        f"Custom model ATM spread (${median_spread:.3f}) should be >$0.90"

    print(f"✓ Custom model ATM median spread: ${median_spread:.3f}")
    print(f"✓ Custom ExecutionModel parameters working")


def test_spread_stability_across_days(loader):
    """
    Verify spreads are stable for similar market conditions.

    Same spot, same vol → similar spreads.
    """
    spot_price = 475.0
    rv_20 = 0.12

    dates = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)]
    median_spreads = []

    for d in dates:
        chain = loader.get_chain(
            d,
            min_dte=30,
            max_dte=60,
            spot_price=spot_price,
            rv_20=rv_20
        )

        if chain.empty:
            continue

        chain['moneyness'] = abs(chain['strike'] - spot_price) / spot_price
        atm = chain[chain['moneyness'] < 0.01].copy()

        if len(atm) > 0:
            atm['spread'] = atm['ask'] - atm['bid']
            median_spreads.append(atm['spread'].median())

    if len(median_spreads) < 2:
        pytest.skip("Need multiple days of data")

    # Spreads should be similar across days
    spread_std = np.std(median_spreads)

    assert spread_std < 0.30, \
        f"Spread std across days ({spread_std:.3f}) should be <$0.30 (stable)"

    print(f"✓ Median spreads across days: {[f'${s:.3f}' for s in median_spreads]}")
    print(f"✓ Spread stability (std): ${spread_std:.3f}")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
