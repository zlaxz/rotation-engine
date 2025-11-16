"""Convexity profile detection system.

Build 6 profile detectors that output continuous scores (0-1) indicating
how strongly each convexity profile is expressed.
"""

from .features import ProfileFeatures
from .detectors import ProfileDetectors

__all__ = ['ProfileFeatures', 'ProfileDetectors']
