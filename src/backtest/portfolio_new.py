"""
Multi-position portfolio for true rotation backtesting.

Tracks 6 simultaneous positions (one per convexity profile),
manages cash, calculates portfolio-level P&L and Greeks.
"""

from typing import Dict, Optional, List, Tuple
from datetime import date
from dataclasses import dataclass
import pandas as pd

from .position import Position
from src.trading.trade import Trade


@dataclass
class ClosedPosition:
    """Record of a closed position for analysis."""
    profile_id: int
    entry_date: date
    exit_date: date
    entry_value: float
    exit_value: float
    realized_pnl: float
    allocation_pct: float
    exit_reason: str
    trade_id: str
    days_held: int


class Portfolio:
    """
    Multi-position portfolio for rotation backtesting.

    Manages:
    - Cash balance
    - Up to 6 simultaneous positions (one per profile)
    - Portfolio-level P&L tracking
    - Rebalancing and rotation logic
    - Aggregate Greeks exposure
    """

    def __init__(self, initial_capital: float = 1_000_000.0):
        """
        Initialize portfolio.

        Parameters:
        -----------
        initial_capital : float
            Starting capital (default $1M)
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital

        # Active positions: {profile_id: Position}
        self.positions: Dict[int, Position] = {}

        # History tracking
        self.closed_positions: List[ClosedPosition] = []
        self.equity_history: List[Dict] = []

    def get_equity(self) -> float:
        """
        Calculate total portfolio equity.

        Returns:
        --------
        equity : float
            Cash + sum of position values
        """
        position_values = sum(pos.current_value for pos in self.positions.values())
        return self.cash + position_values

    def get_allocations(self) -> Dict[int, float]:
        """
        Get current allocation percentages.

        Returns:
        --------
        allocations : dict
            {profile_id: allocation_pct}
        """
        return {
            profile_id: pos.allocation_pct
            for profile_id, pos in self.positions.items()
        }

    def get_position_value(self, profile_id: int) -> Optional[float]:
        """Get current value of a specific position."""
        if profile_id in self.positions:
            return self.positions[profile_id].current_value
        return None

    def has_position(self, profile_id: int) -> bool:
        """Check if position exists for profile."""
        return profile_id in self.positions

    def open_position(
        self,
        profile_id: int,
        trade: Trade,
        allocation_pct: float,
        entry_date: date
    ) -> Position:
        """
        Open new position for a profile.

        Parameters:
        -----------
        profile_id : int
            Profile ID (1-6)
        trade : Trade
            Trade object with constructed options spread
        allocation_pct : float
            Percentage of portfolio to allocate (0-1)
        entry_date : date
            Entry date

        Returns:
        --------
        position : Position
            Created position object
        """
        # Calculate capital to allocate
        current_equity = self.get_equity()
        entry_value = current_equity * allocation_pct

        # Check sufficient cash
        if entry_value > self.cash:
            raise ValueError(
                f"Insufficient cash for position. "
                f"Required: ${entry_value:,.2f}, Available: ${self.cash:,.2f}"
            )

        # Create position
        position = Position(
            profile_id=profile_id,
            trade=trade,
            allocation_pct=allocation_pct,
            entry_value=entry_value,
            entry_date=entry_date,
            current_value=entry_value,
            unrealized_pnl=0.0
        )

        # Deduct from cash (pay entry cost)
        self.cash -= abs(trade.entry_cost)

        # Add to active positions
        self.positions[profile_id] = position

        return position

    def close_position(
        self,
        profile_id: int,
        exit_prices: Dict[int, float],
        exit_date: date,
        exit_reason: str
    ) -> float:
        """
        Close position and realize P&L.

        Parameters:
        -----------
        profile_id : int
            Profile ID to close
        exit_prices : dict
            Exit execution prices {leg_idx: price}
        exit_date : date
            Exit date
        exit_reason : str
            Reason for closing

        Returns:
        --------
        realized_pnl : float
            Realized P&L from closing
        """
        if profile_id not in self.positions:
            raise ValueError(f"No active position for profile {profile_id}")

        position = self.positions[profile_id]

        # Close trade
        realized_pnl = position.close(exit_date, exit_prices, exit_reason)

        # Return cash (exit proceeds)
        self.cash += position.trade.exit_proceeds

        # Record closed position
        days_held = (exit_date - position.entry_date).days
        self.closed_positions.append(
            ClosedPosition(
                profile_id=profile_id,
                entry_date=position.entry_date,
                exit_date=exit_date,
                entry_value=position.entry_value,
                exit_value=position.current_value,
                realized_pnl=realized_pnl,
                allocation_pct=position.allocation_pct,
                exit_reason=exit_reason,
                trade_id=position.trade.trade_id,
                days_held=days_held
            )
        )

        # Remove from active positions
        del self.positions[profile_id]

        return realized_pnl

    def mark_to_market(
        self,
        current_date: date,
        option_prices_by_profile: Dict[int, Dict[int, float]]
    ) -> float:
        """
        Update all position values and calculate total equity.

        Parameters:
        -----------
        current_date : date
            Current date
        option_prices_by_profile : dict
            {profile_id: {leg_idx: price}} - mid prices for all active positions

        Returns:
        --------
        total_equity : float
            Current total portfolio equity
        """
        # Mark each position to market
        for profile_id, position in self.positions.items():
            if profile_id in option_prices_by_profile:
                option_prices = option_prices_by_profile[profile_id]
                position.mark_to_market(option_prices)

        # Calculate total equity
        total_equity = self.get_equity()

        # Record equity snapshot
        equity_record = {
            'date': current_date,
            'cash': self.cash,
            'position_value': sum(pos.current_value for pos in self.positions.values()),
            'total_equity': total_equity,
            'num_positions': len(self.positions)
        }

        # Add per-profile values
        for profile_id in range(1, 7):
            if profile_id in self.positions:
                pos = self.positions[profile_id]
                equity_record[f'profile_{profile_id}_value'] = pos.current_value
                equity_record[f'profile_{profile_id}_pnl'] = pos.unrealized_pnl
            else:
                equity_record[f'profile_{profile_id}_value'] = 0.0
                equity_record[f'profile_{profile_id}_pnl'] = 0.0

        self.equity_history.append(equity_record)

        return total_equity

    def get_portfolio_greeks(self) -> Dict[str, float]:
        """
        Calculate aggregate Greeks across all positions.

        Returns:
        --------
        greeks : dict
            {'delta': X, 'gamma': Y, 'theta': Z, 'vega': W}
        """
        total_delta = 0.0
        total_gamma = 0.0
        total_theta = 0.0
        total_vega = 0.0

        for position in self.positions.values():
            greeks = position.get_greeks()
            total_delta += greeks['delta']
            total_gamma += greeks['gamma']
            total_theta += greeks['theta']
            total_vega += greeks['vega']

        return {
            'delta': total_delta,
            'gamma': total_gamma,
            'theta': total_theta,
            'vega': total_vega
        }

    def get_unrealized_pnl(self) -> float:
        """Get total unrealized P&L across all positions."""
        return sum(pos.unrealized_pnl for pos in self.positions.values())

    def get_realized_pnl(self) -> float:
        """Get total realized P&L from closed positions."""
        return sum(cp.realized_pnl for cp in self.closed_positions)

    def get_total_pnl(self) -> float:
        """Get total P&L (realized + unrealized)."""
        return self.get_realized_pnl() + self.get_unrealized_pnl()

    def get_equity_curve(self) -> pd.DataFrame:
        """
        Get equity curve as DataFrame.

        Returns:
        --------
        equity_curve : pd.DataFrame
            Columns: date, cash, position_value, total_equity, num_positions, profile values
        """
        if not self.equity_history:
            return pd.DataFrame()

        return pd.DataFrame(self.equity_history)

    def get_closed_positions_summary(self) -> pd.DataFrame:
        """
        Get summary of all closed positions.

        Returns:
        --------
        summary : pd.DataFrame
            Closed positions with P&L details
        """
        if not self.closed_positions:
            return pd.DataFrame()

        records = []
        for cp in self.closed_positions:
            records.append({
                'profile_id': cp.profile_id,
                'trade_id': cp.trade_id,
                'entry_date': cp.entry_date,
                'exit_date': cp.exit_date,
                'days_held': cp.days_held,
                'entry_value': cp.entry_value,
                'exit_value': cp.exit_value,
                'realized_pnl': cp.realized_pnl,
                'return_pct': (cp.realized_pnl / cp.entry_value * 100) if cp.entry_value != 0 else 0,
                'allocation_pct': cp.allocation_pct * 100,
                'exit_reason': cp.exit_reason
            })

        return pd.DataFrame(records)

    def rebalance(
        self,
        target_allocations: Dict[int, float],
        current_date: date,
        trade_constructor,
        option_chains: Dict[int, any],
        market_data: pd.Series,
        rebalance_threshold: float = 0.05
    ) -> List[Tuple[str, int, float]]:
        """
        Rebalance portfolio to match target allocations.

        Parameters:
        -----------
        target_allocations : dict
            {profile_id: allocation_pct} - target weights (0-1)
        current_date : date
            Current date
        trade_constructor : callable
            Function(profile_id, market_data, options_chain) -> Trade
        option_chains : dict
            {profile_id: options_chain} - available options per profile
        market_data : pd.Series
            Current market data row
        rebalance_threshold : float
            Minimum allocation change to trigger rebalance (default 5%)

        Returns:
        --------
        actions : list
            List of (action_type, profile_id, allocation_pct) tuples
            action_type: 'close', 'open', 'hold'
        """
        actions = []
        current_allocations = self.get_allocations()

        # Process each profile (1-6)
        for profile_id in range(1, 7):
            target_pct = target_allocations.get(profile_id, 0.0)
            current_pct = current_allocations.get(profile_id, 0.0)

            # Calculate allocation change
            allocation_change = abs(target_pct - current_pct)

            # Decision logic
            if allocation_change < rebalance_threshold:
                # No material change - hold
                if profile_id in self.positions:
                    actions.append(('hold', profile_id, current_pct))
                continue

            # Close existing position if present
            if profile_id in self.positions:
                position = self.positions[profile_id]
                exit_prices = {}  # Will be filled by engine
                self.close_position(
                    profile_id=profile_id,
                    exit_prices=exit_prices,
                    exit_date=current_date,
                    exit_reason="Rebalance"
                )
                actions.append(('close', profile_id, current_pct))

            # Open new position if target > min threshold
            if target_pct >= 0.05:  # Min 5%
                # Construct trade
                trade = trade_constructor(profile_id, market_data, option_chains.get(profile_id))

                # Open position
                self.open_position(
                    profile_id=profile_id,
                    trade=trade,
                    allocation_pct=target_pct,
                    entry_date=current_date
                )
                actions.append(('open', profile_id, target_pct))

        return actions
