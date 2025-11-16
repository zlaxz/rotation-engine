import datetime as dt
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))
sys.path.append(str(project_root / 'src'))

from src.trading.trade import Trade, TradeLeg, CONTRACT_MULTIPLIER


def _build_trade(entry_price: float, quantity: int = 1):
    entry_date = dt.datetime(2024, 1, 2)
    expiry = dt.datetime(2024, 3, 15)
    legs = [
        TradeLeg(
            strike=470.0,
            expiry=expiry,
            option_type='call',
            quantity=quantity,
            dte=60
        )
    ]
    trade = Trade(
        trade_id='TEST',
        profile_name='TEST',
        entry_date=entry_date,
        legs=legs,
        entry_prices={0: entry_price}
    )
    return trade


def test_entry_cost_scales_by_contract_multiplier():
    trade = _build_trade(entry_price=2.50)
    assert trade.entry_cost == 2.50 * CONTRACT_MULTIPLIER


def test_close_realized_pnl_uses_multiplier_and_signs():
    trade = _build_trade(entry_price=2.0)
    exit_date = trade.entry_date + dt.timedelta(days=10)
    trade.close(exit_date, {0: 3.5}, reason='test')
    expected = (3.5 - 2.0) * CONTRACT_MULTIPLIER
    assert trade.realized_pnl == expected
