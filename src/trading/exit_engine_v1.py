"""
Exit Engine V1 - Intelligent Multi-Factor Exits

Designed by PrimeGPT for convexity rotation strategy.

Exit Decision Order (MANDATORY):
1. RISK: Max loss stop (protect capital)
2. TP2: Full profit target (lock in big wins)
3. TP1: Partial profit target (reduce risk, let winners run)
4. CONDITION: Profile-specific regime/indicator exits
5. TIME: Max hold backstop (prevent eternal losers)

Each profile has:
- Risk parameters (max_loss_pct, max_hold_days)
- Profit targets (tp1_pct, tp1_fraction, tp2_pct)
- Condition exit logic (trend breaks, vol changes, etc.)

Uses daily bars with T+1 open execution.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Callable
from datetime import date


@dataclass
class ExitConfig:
    """Exit configuration for a single profile"""

    # Risk management
    max_loss_pct: float          # Max loss before forced exit (e.g., -0.50 = -50%)
    max_hold_days: int           # Max days to hold (backstop)

    # Profit targets
    tp1_pct: Optional[float]     # First profit target (partial exit)
    tp1_fraction: Optional[float] # Fraction to close at TP1 (e.g., 0.50 = half)
    tp2_pct: Optional[float]     # Second profit target (full exit)

    # Condition exit function
    condition_exit_fn: Callable[[Dict], bool]  # Function that checks market conditions


class ExitEngineV1:
    """
    Intelligent exit engine using risk management, profit targets, and conditions.

    Decision order:
    1. Risk (max loss)
    2. TP2 (full exit on big profit)
    3. TP1 (partial exit on moderate profit)
    4. Condition (regime/indicator based)
    5. Time (max hold backstop)
    """

    def __init__(self):
        """Initialize Exit Engine V1 with profile configurations"""
        self.configs = self._get_profile_configs()
        self.tp1_hit = {}  # Track if TP1 already hit for each trade

    def _get_profile_configs(self) -> Dict[str, ExitConfig]:
        """
        Define exit configurations for all 6 profiles.

        Based on PrimeGPT's Exit Engine V1 specification.
        """

        configs = {
            'Profile_1_LDG': ExitConfig(
                max_loss_pct=-0.50,      # -50% stop loss
                tp1_pct=0.50,            # Take half off at +50%
                tp1_fraction=0.50,       # Close 50% of position
                tp2_pct=1.00,            # Full exit at +100%
                max_hold_days=14,        # Max 14 days
                condition_exit_fn=self._condition_exit_profile_1
            ),

            'Profile_2_SDG': ExitConfig(
                max_loss_pct=-0.40,      # -40% stop (tighter for short-dated)
                tp1_pct=None,            # No partial exit (all or nothing)
                tp1_fraction=None,
                tp2_pct=0.75,            # Full exit at +75%
                max_hold_days=5,         # Max 5 days (short-dated gamma)
                condition_exit_fn=self._condition_exit_profile_2
            ),

            'Profile_3_CHARM': ExitConfig(
                max_loss_pct=-1.50,      # -150% (1.5x premium for short straddle)
                tp1_pct=0.60,            # Exit at 60% premium collected
                tp1_fraction=1.00,       # Full exit (not partial for shorts)
                tp2_pct=None,            # No TP2 (TP1 is full exit)
                max_hold_days=14,        # Max 14 days
                condition_exit_fn=self._condition_exit_profile_3
            ),

            'Profile_4_VANNA': ExitConfig(
                max_loss_pct=-0.50,      # -50% stop
                tp1_pct=0.50,            # Take half at +50%
                tp1_fraction=0.50,
                tp2_pct=1.25,            # Full exit at +125%
                max_hold_days=14,
                condition_exit_fn=self._condition_exit_profile_4
            ),

            'Profile_5_SKEW': ExitConfig(
                max_loss_pct=-0.50,      # -50% stop
                tp1_pct=None,            # No partial (OTM put is binary)
                tp1_fraction=None,
                tp2_pct=1.00,            # Full exit at +100%
                max_hold_days=5,         # Max 5 days (fear spike is fast)
                condition_exit_fn=self._condition_exit_profile_5
            ),

            'Profile_6_VOV': ExitConfig(
                max_loss_pct=-0.50,      # -50% stop
                tp1_pct=0.50,            # Take half at +50%
                tp1_fraction=0.50,
                tp2_pct=1.00,            # Full exit at +100%
                max_hold_days=14,
                condition_exit_fn=self._condition_exit_profile_6
            ),
        }

        return configs

    def should_exit(
        self,
        profile_id: str,
        trade_id: str,
        days_held: int,
        pnl_pct: float,
        market_conditions: Dict,
        position_greeks: Dict
    ) -> tuple[bool, float, str]:
        """
        Determine if position should exit and how much.

        Args:
            profile_id: Profile identifier (e.g., 'Profile_1_LDG')
            trade_id: Unique trade identifier (for tracking TP1 status)
            days_held: Days since entry
            pnl_pct: Current P&L as percentage of entry cost
            market_conditions: Dict with market indicators (slope_MA20, RV5, etc.)
            position_greeks: Dict with current Greeks (delta, gamma, etc.)

        Returns:
            (should_exit: bool, fraction_to_close: float, reason: str)
            - fraction_to_close: 0.0-1.0 (1.0 = close all)
        """
        cfg = self.configs.get(profile_id)
        if not cfg:
            # Unknown profile - use time backstop
            return (days_held >= 14, 1.0, "unknown_profile_time_stop")

        # Track TP1 status per trade
        tp1_key = f"{profile_id}_{trade_id}"
        if tp1_key not in self.tp1_hit:
            self.tp1_hit[tp1_key] = False

        # DECISION ORDER (MANDATORY - DO NOT CHANGE):

        # 1. RISK: Max loss stop (highest priority)
        if pnl_pct <= cfg.max_loss_pct:
            return (True, 1.0, f"max_loss_{cfg.max_loss_pct:.0%}")

        # 2. TP2: Full profit target
        if cfg.tp2_pct is not None and pnl_pct >= cfg.tp2_pct:
            return (True, 1.0, f"tp2_{cfg.tp2_pct:.0%}")

        # 3. TP1: Partial profit target (if not already hit)
        if cfg.tp1_pct is not None and pnl_pct >= cfg.tp1_pct:
            if not self.tp1_hit[tp1_key]:
                self.tp1_hit[tp1_key] = True
                return (True, cfg.tp1_fraction, f"tp1_{cfg.tp1_pct:.0%}")

        # 4. CONDITION: Profile-specific exit conditions
        if cfg.condition_exit_fn(market_conditions, position_greeks):
            return (True, 1.0, "condition_exit")

        # 5. TIME: Max hold backstop
        if days_held >= cfg.max_hold_days:
            return (True, 1.0, f"time_stop_day{cfg.max_hold_days}")

        # No exit triggered
        return (False, 0.0, "")

    def _condition_exit_profile_1(self, market: Dict, greeks: Dict) -> bool:
        """
        Profile 1 (LDG) - Long-Dated Gamma condition exit

        Exit if:
        - Trend broken (slope_MA20 <= 0)
        - Price under MA20 (close < MA20)
        - Cheap vol thesis invalid (RV10/IV60 < 0.90)
        """
        # FIXED: Validate data exists and is not None
        slope_ma20 = market.get('slope_MA20')
        if slope_ma20 is not None and slope_ma20 <= 0:
            return True

        # Price below MA20
        close = market.get('close')
        ma20 = market.get('MA20')
        if close is not None and ma20 is not None and close > 0 and ma20 > 0 and close < ma20:
            return True

        # Cheap vol thesis broken (would need IV60 - not currently tracked)
        # For now, skip this condition
        # TODO: Add IV tracking to market_conditions

        return False

    def _condition_exit_profile_2(self, market: Dict, greeks: Dict) -> bool:
        """
        Profile 2 (SDG) - Short-Dated Gamma Spike condition exit

        Exit if:
        - Fear fading (VVIX_slope < 0) - NOT TRACKED YET
        - Spike receding (move_size < 1.0) - NOT TRACKED YET
        - RV spike failed (RV5/IV7 <= 0.80) - NOT TRACKED YET
        """
        # TODO: Add VVIX, move_size, IV7 tracking
        # For now, rely on time/profit targets only
        return False

    def _condition_exit_profile_3(self, market: Dict, greeks: Dict) -> bool:
        """
        Profile 3 (CHARM) - Theta/Decay condition exit

        Exit if:
        - Pin broken (range_10d > 0.04) - NOT TRACKED YET
        - Vol-of-vol rising (VVIX_slope > 0) - NOT TRACKED YET
        - Rich vol edge gone (IV20/RV10 < 1.20) - NOT TRACKED YET
        """
        # TODO: Add range_10d, VVIX, IV20 tracking
        # For now, rely on profit targets
        return False

    def _condition_exit_profile_4(self, market: Dict, greeks: Dict) -> bool:
        """
        Profile 4 (VANNA) - Vol-Spot Correlation condition exit

        Exit if:
        - Trend weakening (slope_MA20 <= 0)
        - Vol no longer cheap (IV_rank_20 > 0.70) - NOT TRACKED YET
        - Vol-of-vol instability (VVIX_slope > 0) - NOT TRACKED YET
        """
        # FIXED: Validate data exists
        slope_ma20 = market.get('slope_MA20')
        if slope_ma20 is not None and slope_ma20 <= 0:
            return True

        # TODO: Add IV_rank_20, VVIX tracking
        return False

    def _condition_exit_profile_5(self, market: Dict, greeks: Dict) -> bool:
        """
        Profile 5 (SKEW) - Fear/Skew Convexity condition exit

        Exit if:
        - Skew normalized (skew_z < 1.0) - NOT TRACKED YET
        - Fear receding (VVIX_slope <= 0) - NOT TRACKED YET
        - Catch-up done (RV5/IV20 <= 1.0) - NOT TRACKED YET
        """
        # TODO: Add skew_z, VVIX, IV20 tracking
        # For now, rely on profit targets
        return False

    def _condition_exit_profile_6(self, market: Dict, greeks: Dict) -> bool:
        """
        Profile 6 (VOV) - Vol-of-Vol Convexity condition exit

        Exit if:
        - VVIX not elevated (VVIX/VVIX_80pct <= 1.0) - NOT TRACKED YET
        - Vol-of-vol stopped rising (VVIX_slope <= 0) - NOT TRACKED YET
        - Compression resolved (RV10/IV20 >= 1.0) - NOT TRACKED YET
        """
        # TODO: Add VVIX tracking
        # For now, rely on RV ratios we DO track

        # Use RV10/RV20 as proxy for volatility compression state
        # FIXED: Validate data exists
        rv10 = market.get('RV10')
        rv20 = market.get('RV20')

        # If RV normalized (RV10 >= RV20), compression resolved
        if rv10 is not None and rv20 is not None and rv10 > 0 and rv20 > 0 and rv10 >= rv20:
            return True

        return False

    def get_config(self, profile_id: str) -> Optional[ExitConfig]:
        """Get exit configuration for a profile"""
        return self.configs.get(profile_id)

    def reset_tp1_tracking(self):
        """Reset TP1 tracking (call at start of backtest)"""
        self.tp1_hit = {}

    def apply_to_tracked_trade(
        self,
        profile_id: str,
        trade_data: Dict
    ) -> Dict:
        """
        Apply Exit Engine V1 logic to a tracked trade.

        Takes complete 14-day tracked trade and determines when exit would
        have triggered based on Exit Engine V1 rules.

        Args:
            profile_id: Profile identifier
            trade_data: Complete trade data from TradeTracker with 'path' and 'entry'

        Returns:
            Dict with exit info:
                - exit_day: Day exit triggered (0-14)
                - exit_reason: Why exit triggered
                - exit_pnl: P&L at exit
                - exit_fraction: Fraction closed (for TP1 partials)
        """
        # FIXED: Don't use abs() - preserves sign for short positions
        # Short positions have negative entry_cost (premium collected)
        entry_cost = trade_data['entry']['entry_cost']
        daily_path = trade_data['path']

        # Generate unique trade ID for TP1 tracking
        trade_id = trade_data['entry']['entry_date']

        # Check each day for exit trigger
        for day in daily_path:
            day_idx = day['day']
            mtm_pnl = day['mtm_pnl']

            # Calculate P&L percentage (FIXED: handle zero and preserve signs)
            if abs(entry_cost) < 0.01:  # Near-zero entry cost (break-even)
                pnl_pct = 0
            else:
                pnl_pct = mtm_pnl / entry_cost

            # Check if exit triggered
            should_exit, fraction, reason = self.should_exit(
                profile_id=profile_id,
                trade_id=trade_id,
                days_held=day_idx,
                pnl_pct=pnl_pct,
                market_conditions=day.get('market_conditions', {}),
                position_greeks=day.get('greeks', {})
            )

            if should_exit:
                return {
                    'exit_day': day_idx,
                    'exit_reason': reason,
                    'exit_pnl': mtm_pnl,
                    'exit_fraction': fraction,
                    'entry_cost': entry_cost,
                    'pnl_pct': pnl_pct
                }

        # No exit triggered - use last day (14-day backstop)
        last_day = daily_path[-1]

        # FIXED: Handle division by zero
        if abs(entry_cost) < 0.01:
            final_pnl_pct = 0
        else:
            final_pnl_pct = last_day['mtm_pnl'] / entry_cost

        return {
            'exit_day': last_day['day'],
            'exit_reason': 'max_tracking_days',
            'exit_pnl': last_day['mtm_pnl'],
            'exit_fraction': 1.0,
            'entry_cost': entry_cost,
            'pnl_pct': final_pnl_pct
        }
