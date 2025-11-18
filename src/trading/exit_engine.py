"""
Exit Engine - Phase 1: Fixed Time-Based Exits

DESIGN: Zero-parameter baseline using empirical peak timing.
NO optimization, NO conditions, PURE time-based exits.

See: docs/EXIT_STRATEGY_PHASE1_SPEC.md for full specification.

CHANGE LOG:
- 2025-11-18: Initial implementation (Phase 1)
"""

from typing import Dict
from datetime import date


class ExitEngine:
    """
    Manage trade exits using profile-specific strategies.

    Phase 1: Fixed time windows based on empirical peak timing.
    Future phases will add profit targets, risk guards, condition exits.
    """

    # Phase 1: Profile-specific exit days (DEFAULT - will be overridden by train-derived)
    # FIXED Round 8: Use 14 days as neutral baseline (safer for longer-DTE profiles)
    # Train period will derive actual median peak timing from 2020-2021 data
    # 14 days gives 75 DTE and 60 DTE profiles time to develop gamma/vanna edge
    PROFILE_EXIT_DAYS = {
        'Profile_1_LDG': 14,   # Neutral default (75 DTE needs time) - re-derived on train
        'Profile_2_SDG': 14,   # Neutral default - re-derived on train
        'Profile_3_CHARM': 14, # Neutral default - re-derived on train
        'Profile_4_VANNA': 14, # Neutral default (60 DTE needs time) - re-derived on train
        'Profile_5_SKEW': 14,  # Neutral default - re-derived on train
        'Profile_6_VOV': 14    # Neutral default - re-derived on train
    }

    def __init__(self, phase: int = 1, custom_exit_days: Dict[str, int] = None):
        """
        Initialize exit engine.

        Args:
            phase: Exit strategy phase (1 = time-based only)
            custom_exit_days: Optional dict to override default exit days
                             (used for validation/test periods with train-derived parameters)
        """
        self.phase = phase

        # Create mutable instance copy that can be overridden
        self.exit_days = self.PROFILE_EXIT_DAYS.copy()

        # Override with custom exit days if provided
        if custom_exit_days:
            self.exit_days.update(custom_exit_days)

        if phase != 1:
            raise NotImplementedError(f"Phase {phase} not implemented yet. Only Phase 1 available.")

    def should_exit(
        self,
        trade,
        current_date: date,
        profile: str
    ) -> tuple[bool, str]:
        """
        Determine if trade should exit.

        Phase 1: Exit on fixed calendar day based on profile.

        Args:
            trade: Trade object with entry_date
            current_date: Current date
            profile: Profile name (e.g., 'Profile_1_LDG')

        Returns:
            (should_exit: bool, reason: str)
        """
        # Calculate days since entry
        days_held = (current_date - trade.entry_date).days

        # Get profile-specific exit day (from instance, not class)
        exit_day = self.exit_days.get(profile, 14)

        # Phase 1: Simple time-based exit
        if days_held >= exit_day:
            return (True, f"Phase1_Time_Day{exit_day}")

        return (False, "")

    def get_exit_day(self, profile: str) -> int:
        """Get the exit day for a given profile."""
        return self.exit_days.get(profile, 14)

    def get_all_exit_days(self) -> Dict[str, int]:
        """Get all profile exit days (for logging/validation)."""
        return self.exit_days.copy()
