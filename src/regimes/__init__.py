"""Regime classification for convexity rotation engine.

This module implements the 6-regime market classification system:
1. Trend Up (directional + vol compression)
2. Trend Down (directional + vol expansion)
3. Vol Compression / Pinned
4. Breaking Vol / Vol Expansion
5. Choppy / Mean-Reverting
6. Event / Catalyst

All regime detection is WALK-FORWARD ONLY to prevent look-ahead bias.
"""

from .signals import RegimeSignals
from .classifier import RegimeClassifier

__all__ = ['RegimeSignals', 'RegimeClassifier']
