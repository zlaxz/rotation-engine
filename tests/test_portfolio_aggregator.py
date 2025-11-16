import pandas as pd
from datetime import date
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))
sys.path.append(str(project_root / 'src'))

from src.backtest.portfolio import PortfolioAggregator


def test_aggregate_pnl_uses_returns_and_capital():
    allocations = pd.DataFrame({
        'date': [date(2024, 1, 2), date(2024, 1, 3)],
        'regime': [1, 1],
        'profile_1_weight': [0.5, 0.5],
        'profile_2_weight': [0.5, 0.5]
    })

    profile_1 = pd.DataFrame({
        'date': allocations['date'],
        'daily_pnl': [100.0, -50.0],
        'daily_return': [0.01, -0.005]
    })

    profile_2 = pd.DataFrame({
        'date': allocations['date'],
        'daily_pnl': [50.0, 50.0],
        'daily_return': [0.005, 0.005]
    })

    aggregator = PortfolioAggregator(starting_capital=1000.0)
    portfolio = aggregator.aggregate_pnl(
        allocations,
        {
            'profile_1': profile_1,
            'profile_2': profile_2
        }
    )

    # Day 1 expected return = 0.5*0.01 + 0.5*0.005 = 0.0075
    expected_day1_return = 0.0075
    assert abs(portfolio.loc[0, 'portfolio_return'] - expected_day1_return) < 1e-9
    # Day 1 pnl = 1000 * 0.0075
    assert abs(portfolio.loc[0, 'portfolio_pnl'] - 7.5) < 1e-9

    # Day 2 prev value = 1007.5, expected return = 0.5*-0.005 + 0.5*0.005 = 0
    assert abs(portfolio.loc[1, 'portfolio_return']) < 1e-9
    assert abs(portfolio.loc[1, 'portfolio_pnl']) < 1e-9
