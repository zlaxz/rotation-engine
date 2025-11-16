import os
import pandas as pd
import pytest
from datetime import datetime
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))
sys.path.append(str(project_root / 'src'))

from src.trading.simulator import TradeSimulator, SimulationConfig
from src.trading.trade import TradeLeg
from src.data.polygon_options import PolygonOptionsLoader
from src.data.loaders import OptionsDataLoader


def _sample_data():
    dates = pd.date_range('2024-01-02', periods=2, freq='D')
    return pd.DataFrame({
        'date': dates.date,
        'open': [470.0, 471.0],
        'high': [472.0, 473.0],
        'low': [469.0, 470.0],
        'close': [471.0, 472.0],
        'volume': [100_000_000, 120_000_000],
        'RV20': [0.20, 0.21],
        'regime': [1, 1]
    })


def test_simulator_requires_real_data_without_toy_flag():
    df = _sample_data()
    with pytest.raises(ValueError):
        TradeSimulator(
            data=df,
            config=SimulationConfig(allow_toy_pricing=False),
            use_real_options_data=False
        )


def test_simulator_raises_when_polygon_missing_and_toy_disabled(tmp_path):
    df = _sample_data()
    config = SimulationConfig(allow_toy_pricing=False)
    simulator = TradeSimulator(
        data=df,
        config=config,
        use_real_options_data=True,
        polygon_data_root=str(tmp_path)
    )

    class DummyLoader:
        def get_option_price(self, *args, **kwargs):
            return None

    simulator.polygon_loader = DummyLoader()

    leg = TradeLeg(
        strike=470.0,
        expiry=datetime(2024, 3, 15),
        option_type='call',
        quantity=1,
        dte=45
    )
    row = df.iloc[0]

    with pytest.raises(RuntimeError, match="Polygon options data missing"):
        simulator._estimate_option_price(leg, row['close'], row, dte=30)


def test_polygon_loader_requires_existing_root(tmp_path):
    missing = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError):
        PolygonOptionsLoader(data_root=str(missing))


def test_options_data_loader_requires_existing_root(tmp_path):
    missing = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError):
        OptionsDataLoader(data_root=str(missing))
