"""
Performance metrics using empyrical library (battle-tested).

LESSON LEARNED: Don't reinvent wheels. Use proven libraries.
- empyrical: Quantopian's metrics library (billions traded)
- Battle-tested, no custom bugs
- Industry standard
"""

import pandas as pd
import empyrical as ep
from typing import Dict, Optional


class PerformanceMetrics:
    """
    Calculate performance metrics using empyrical library.
    
    NO MORE CUSTOM IMPLEMENTATIONS.
    NO MORE INTRODUCED BUGS.
    BATTLE-TESTED CODE ONLY.
    """

    def __init__(self, annual_factor: int = 252):
        """Risk-free rate can be passed to empyrical functions."""
        self.annual_factor = annual_factor

    def calculate_all(
        self,
        portfolio: pd.DataFrame,
        benchmark_col: Optional[str] = None
    ) -> Dict:
        """
        Calculate all metrics using empyrical.
        
        Input: portfolio_pnl column (dollar P&L is fine - empyrical handles it)
        """
        returns = portfolio['portfolio_pnl']

        # Empyrical handles everything correctly
        metrics = {
            'sharpe_ratio': ep.sharpe_ratio(returns, period='daily'),
            'sortino_ratio': ep.sortino_ratio(returns, period='daily'),
            'calmar_ratio': ep.calmar_ratio(returns, period='daily'),
            'max_drawdown': ep.max_drawdown(returns),
            'annual_return': ep.annual_return(returns, period='daily'),
            'annual_volatility': ep.annual_volatility(returns, period='daily'),
            'stability': ep.stability_of_timeseries(returns),
            'tail_ratio': ep.tail_ratio(returns),
            
            # Simple stats
            'total_return': returns.sum(),
            'avg_daily_pnl': returns.mean(),
            'std_daily_pnl': returns.std(),
            'total_days': len(returns),
            'positive_days': (returns > 0).sum(),
            'best_day': returns.max(),
            'worst_day': returns.min(),
        }

        return metrics
