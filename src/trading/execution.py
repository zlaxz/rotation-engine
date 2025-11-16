"""
Execution model for realistic bid-ask spreads, slippage, and transaction costs.

Models:
- Bid-ask spreads as function of moneyness, DTE, volatility
- Execution slippage
- Delta hedging costs (ES futures)
"""

import numpy as np
import pandas as pd
from typing import Tuple


class ExecutionModel:
    """Realistic execution cost model for SPY options."""

    def __init__(
        self,
        base_spread_atm: float = 0.03,  # Base ATM spread ($) - SPY penny-wide spreads, 3x for safety
        base_spread_otm: float = 0.05,  # Base OTM spread ($) - slightly wider
        spread_multiplier_vol: float = 2.0,  # Spread widening in high vol (2-3x)
        slippage_pct: float = 0.0,  # NO slippage for retail size (user's real trades confirm)
        es_commission: float = 2.50,  # ES futures commission per round-trip
        es_slippage: float = 0.0,  # NO ES slippage for liquid futures (simulate in fill price if needed)
        option_commission: float = 0.65,  # Options commission per contract
        sec_fee_rate: float = 0.00182  # SEC fee per contract (for short sales)
    ):
        """
        Initialize execution model.

        Parameters:
        -----------
        base_spread_atm : float
            Base bid-ask spread for ATM straddles (dollars)
        base_spread_otm : float
            Base bid-ask spread for OTM options (dollars)
        spread_multiplier_vol : float
            Spread widening multiplier during high volatility
        slippage_pct : float
            Additional slippage as percentage of mid price
        es_commission : float
            ES futures commission per round-trip (dollars)
        es_slippage : float
            ES futures slippage per contract (dollars)
        option_commission : float
            Commission per option contract (dollars)
        sec_fee_rate : float
            SEC fee per contract for short sales (dollars)
        """
        self.base_spread_atm = base_spread_atm
        self.base_spread_otm = base_spread_otm
        self.spread_multiplier_vol = spread_multiplier_vol
        self.slippage_pct = slippage_pct
        self.es_commission = es_commission
        self.es_slippage = es_slippage
        self.option_commission = option_commission
        self.sec_fee_rate = sec_fee_rate

    def get_spread(
        self,
        mid_price: float,
        moneyness: float,
        dte: int,
        vix_level: float = 20.0,
        is_strangle: bool = False
    ) -> float:
        """
        Calculate bid-ask spread for an option.

        Parameters:
        -----------
        mid_price : float
            Mid price of the option
        moneyness : float
            Abs(strike - spot) / spot (0 = ATM, higher = OTM)
        dte : int
            Days to expiration
        vix_level : float
            Current VIX level (for spread widening)
        is_strangle : bool
            Whether this is a strangle (tighter spread than straddle)

        Returns:
        --------
        spread : float
            Bid-ask spread in dollars
        """
        # Base spread depends on structure
        base = self.base_spread_otm if is_strangle else self.base_spread_atm

        # Adjust for moneyness (wider spreads for OTM)
        moneyness_factor = 1.0 + moneyness * 2.0  # Spread widens linearly with OTM

        # Adjust for DTE (wider spreads for short DTE)
        dte_factor = 1.0
        if dte < 7:
            dte_factor = 1.3  # 30% wider for weekly options
        elif dte < 14:
            dte_factor = 1.15  # 15% wider for 2-week options

        # Adjust for volatility (spreads widen when VIX > 30)
        vol_factor = 1.0
        if vix_level > 30:
            vol_factor = self.spread_multiplier_vol
        elif vix_level > 25:
            vol_factor = 1.2

        # Final spread
        spread = base * moneyness_factor * dte_factor * vol_factor

        # Ensure spread is at least some % of mid price (for very cheap options)
        min_spread = mid_price * 0.05  # At least 5% of mid
        return max(spread, min_spread)

    def get_execution_price(
        self,
        mid_price: float,
        side: str,  # 'buy' or 'sell'
        moneyness: float,
        dte: int,
        vix_level: float = 20.0,
        is_strangle: bool = False
    ) -> float:
        """
        Get realistic execution price including bid-ask spread and slippage.

        Parameters:
        -----------
        mid_price : float
            Mid price of the option
        side : str
            'buy' or 'sell'
        moneyness : float
            Abs(strike - spot) / spot
        dte : int
            Days to expiration
        vix_level : float
            Current VIX level
        is_strangle : bool
            Whether this is a strangle

        Returns:
        --------
        exec_price : float
            Execution price (mid ± half spread ± slippage)
        """
        spread = self.get_spread(mid_price, moneyness, dte, vix_level, is_strangle)
        half_spread = spread / 2.0

        # Additional slippage
        slippage = mid_price * self.slippage_pct

        if side == 'buy':
            # Pay ask + slippage
            return mid_price + half_spread + slippage
        elif side == 'sell':
            # Receive bid - slippage
            return max(0.01, mid_price - half_spread - slippage)
        else:
            raise ValueError(f"Invalid side: {side}. Must be 'buy' or 'sell'")

    def get_delta_hedge_cost(self, contracts: int) -> float:
        """
        Calculate cost of delta hedging with ES futures.

        Parameters:
        -----------
        contracts : int
            Number of ES futures contracts (can be fractional, will round)

        Returns:
        --------
        cost : float
            Total cost of hedging (commission + slippage)
        """
        # Round to nearest contract
        actual_contracts = abs(round(contracts))

        if actual_contracts == 0:
            return 0.0

        # Cost = commission + slippage per contract
        cost_per_contract = self.es_commission + self.es_slippage
        return actual_contracts * cost_per_contract

    def apply_spread_to_price(
        self,
        mid_price: float,
        quantity: int,  # Positive = long, negative = short
        moneyness: float,
        dte: int,
        vix_level: float = 20.0,
        is_strangle: bool = False
    ) -> float:
        """
        Apply bid-ask spread to get execution price based on quantity sign.

        Parameters:
        -----------
        mid_price : float
            Mid price
        quantity : int
            Quantity (sign determines buy/sell)
        moneyness : float
            Moneyness
        dte : int
            Days to expiration
        vix_level : float
            VIX level
        is_strangle : bool
            Whether strangle

        Returns:
        --------
        exec_price : float
            Execution price
        """
        side = 'buy' if quantity > 0 else 'sell'
        return self.get_execution_price(
            mid_price, side, moneyness, dte, vix_level, is_strangle
        )

    def get_commission_cost(self, num_contracts: int, is_short: bool = False) -> float:
        """
        Calculate total commission and fees for options trade.

        Parameters:
        -----------
        num_contracts : int
            Number of contracts traded (absolute value)
        is_short : bool
            Whether this is a short sale (incurs SEC fees)

        Returns:
        --------
        total_cost : float
            Total commission + fees (always positive)
        """
        num_contracts = abs(num_contracts)

        # Base commission
        commission = num_contracts * self.option_commission

        # SEC fees for short sales
        sec_fees = 0.0
        if is_short:
            sec_fees = num_contracts * self.sec_fee_rate

        return commission + sec_fees


def calculate_moneyness(strike: float, spot: float) -> float:
    """Calculate moneyness as abs(strike - spot) / spot."""
    return abs(strike - spot) / spot


def get_vix_proxy(rv_20: float) -> float:
    """
    Simple VIX proxy from 20-day realized vol.

    Typical relationship: VIX ≈ RV * sqrt(252) * 100 * 1.2 (IV premium)

    Parameters:
    -----------
    rv_20 : float
        20-day realized volatility (annualized, as decimal)

    Returns:
    --------
    vix_proxy : float
        VIX proxy (e.g., 20.0 for 20% implied vol)
    """
    return rv_20 * 100 * 1.2  # RV to IV with 20% premium
