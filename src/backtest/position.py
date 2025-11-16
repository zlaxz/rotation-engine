"""
Position tracking for multi-profile rotation portfolio.

A Position represents a single active trade for a specific convexity profile,
with its allocation percentage and value tracking.
"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, Dict
from src.trading.trade import Trade


@dataclass
class Position:
    """
    Represents an active position in the portfolio.

    Tracks:
    - The underlying Trade object (options spread)
    - Capital allocation percentage
    - Entry value and current value
    - Profile assignment
    """

    profile_id: int  # 1-6
    trade: Trade
    allocation_pct: float  # Percentage of portfolio allocated (0-1)
    entry_value: float  # Capital committed at entry
    entry_date: date

    # Updated daily via mark_to_market
    current_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None

    def __post_init__(self):
        """Initialize current value to entry value."""
        if self.current_value is None:
            self.current_value = self.entry_value
        if self.unrealized_pnl is None:
            self.unrealized_pnl = 0.0

    def mark_to_market(self, option_prices: Dict[int, float]) -> float:
        """
        Update position value based on current option prices.

        Parameters:
        -----------
        option_prices : dict
            Current mid prices for each leg {leg_idx: price}

        Returns:
        --------
        unrealized_pnl : float
            Current unrealized P&L
        """
        # Trade calculates P&L from entry
        trade_pnl = self.trade.mark_to_market(option_prices)

        # Current value = entry capital + P&L
        self.current_value = self.entry_value + trade_pnl
        self.unrealized_pnl = trade_pnl

        return self.unrealized_pnl

    def close(self, exit_date: date, exit_prices: Dict[int, float], exit_reason: str) -> float:
        """
        Close position and return realized P&L.

        Parameters:
        -----------
        exit_date : date
            Exit date
        exit_prices : dict
            Exit execution prices for each leg
        exit_reason : str
            Reason for exit

        Returns:
        --------
        realized_pnl : float
            Final realized P&L including all costs
        """
        # Close trade
        self.trade.close(
            exit_date=exit_date,
            exit_prices=exit_prices,
            reason=exit_reason
        )

        # Final realized P&L
        return self.trade.realized_pnl

    def get_greeks(self) -> Dict[str, float]:
        """Return current Greeks for this position."""
        return {
            'delta': self.trade.net_delta,
            'gamma': self.trade.net_gamma,
            'theta': self.trade.net_theta,
            'vega': self.trade.net_vega
        }
