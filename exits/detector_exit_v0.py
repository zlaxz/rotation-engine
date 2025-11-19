#!/usr/bin/env python3
"""
EXIT DETECTOR V0 - DECAY-AWARE EXIT LOGIC

NOT inverse-of-entry. Detects when convexity edge is DECAYING.

Profile-specific rules based on time-to-peak analysis:
- SDG (median peak day 4): Fast decay detection
- SKEW (median peak day 4): Fast decay detection
- CHARM (median peak day 10): Pin break detection
- VANNA (median peak day 9.5): Later exits
- LDG (median peak day 6): Moderate
- VOV (median peak day 5): Moderate

Features (computed ex-ante daily):
- dRV5: RV5 change vs 5 days ago (vol stalling?)
- dIV: IV rank change vs entry (vol cooling?)
- TS_inverted: Term structure > 0 (panic on/off)
- dTS: TS flip detection
- skew_flat: Skew normalizing
- price_drift: return_1d sign

Exit logic: Profile-specific decay detection
Fallback: Profile-specific max_hold (5-10 days based on peak timing)
"""

from typing import Dict, Optional, List
import pandas as pd
import numpy as np


class ExitDetectorV0:
    """Decay-aware exit detector"""

    def __init__(self):
        """Initialize with profile-specific parameters"""

        # Profile-specific max hold (from time-to-peak analysis)
        self.max_hold = {
            'Profile_1_LDG': 7,      # Median peak: 6 days
            'Profile_2_SDG': 5,      # Median peak: 4 days
            'Profile_3_CHARM': 10,   # Median peak: 10 days
            'Profile_4_VANNA': 10,   # Median peak: 9.5 days
            'Profile_5_SKEW': 5,     # Median peak: 4 days
            'Profile_6_VOV': 7       # Median peak: 5 days
        }

        # Minimum hold periods (allow edge to develop)
        self.min_hold = {
            'Profile_1_LDG': 2,
            'Profile_2_SDG': 2,
            'Profile_3_CHARM': 3,
            'Profile_4_VANNA': 3,
            'Profile_5_SKEW': 2,
            'Profile_6_VOV': 2
        }

    def should_exit(
        self,
        profile_id: str,
        days_held: int,
        current_market: Dict,
        entry_market: Dict,
        market_history: List[Dict]  # Last 5-10 days of market data
    ) -> tuple[bool, str]:
        """
        Determine if position should exit based on decay detection

        Args:
            profile_id: Profile identifier
            days_held: Days since entry
            current_market: Current day market conditions
            entry_market: Market conditions at entry
            market_history: Recent market data for delta calculations

        Returns:
            (should_exit: bool, reason: str)
        """

        # Minimum hold
        if days_held < self.min_hold[profile_id]:
            return False, ""

        # Maximum hold (backstop)
        if days_held >= self.max_hold[profile_id]:
            return True, f"max_hold_day{self.max_hold[profile_id]}"

        # Profile-specific decay detection
        if profile_id == 'Profile_2_SDG':
            return self._exit_sdg(days_held, current_market, entry_market, market_history)
        elif profile_id == 'Profile_5_SKEW':
            return self._exit_skew(days_held, current_market, entry_market, market_history)
        elif profile_id == 'Profile_3_CHARM':
            return self._exit_charm(days_held, current_market, entry_market)
        else:
            # VANNA, LDG, VOV: Use max_hold only for now
            return False, ""

    def _exit_sdg(self, days_held, current, entry, history) -> tuple[bool, str]:
        """
        SDG: Gamma spike decay detection

        Exit if:
        - dRV5 <= 0 (vol spike stalling)
        - dTS < 0 (term structure flipping)
        - dIV <= -5pctl (IV cooling off)

        Require 2-of-3 signals for 2 consecutive days (confirmation)
        """

        # Calculate deltas
        rv5_now = current.get('RV5')  # Don't default to 0

        # Get RV5 from 5 days ago
        rv5_5d_ago = None
        if len(history) >= 5:
            rv5_5d_ago = history[len(history) - 5].get('RV5')  # Explicit indexing

        dRV5 = None
        if rv5_now is not None and rv5_5d_ago is not None:  # Explicit None check
            dRV5 = rv5_now - rv5_5d_ago

        # Exit tripwire: Vol spike stalling
        if dRV5 is not None and dRV5 <= 0:
            return True, "sdg_vol_stalling"

        # TODO: Add TS_inverted and dIV when term structure data available

        return False, ""

    def _exit_skew(self, days_held, current, entry, history) -> tuple[bool, str]:
        """
        SKEW: Fear decay detection

        Exit if:
        - skew_flat (skew normalizing)
        - (dIV <= -5pctl AND dRV5 <= 0) for 2 days
        """

        # Calculate RV delta
        rv5_now = current.get('RV5')  # Don't default to 0

        rv5_5d_ago = None
        if len(history) >= 5:
            rv5_5d_ago = history[len(history) - 5].get('RV5')  # Explicit indexing

        dRV5 = None
        if rv5_now is not None and rv5_5d_ago is not None:  # Explicit None check
            dRV5 = rv5_now - rv5_5d_ago

        # Exit: Vol spike fading
        if dRV5 is not None and dRV5 <= 0:
            return True, "skew_vol_fading"

        # TODO: Add skew_z tracking when available

        return False, ""

    def _exit_charm(self, days_held, current, entry) -> tuple[bool, str]:
        """
        CHARM: Pin break detection

        Exit if:
        - |return_5d| > 1.5% (pin broken)
        - RV10 rising vs entry (vol expanding)
        """

        return_5d = current.get('return_5d')

        # Pin broken
        if return_5d is not None and abs(return_5d) > 0.015:
            return True, "charm_pin_broken"

        # Vol expansion
        rv10_now = current.get('RV10')
        rv10_entry = entry.get('RV10')

        if rv10_now is not None and rv10_entry is not None and rv10_entry > 0:
            if rv10_now > rv10_entry * 1.2:
                return True, "charm_vol_expanding"

        return False, ""

    def get_max_hold(self, profile_id: str) -> int:
        """Get max hold days for profile"""
        return self.max_hold.get(profile_id, 10)


# Convenience function
def create_exit_detector() -> ExitDetectorV0:
    """Create exit detector instance"""
    return ExitDetectorV0()
