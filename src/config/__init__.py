"""
Config module exports.
Rule configuration loading and injection.
"""

from .loader import (
    GameRules,
    ConfigLoader,
    VEGAS_STRIP,
    VEGAS_DOWNTOWN,
    ATLANTIC_CITY
)

__all__ = [
    'GameRules',
    'ConfigLoader',
    'VEGAS_STRIP',
    'VEGAS_DOWNTOWN',
    'ATLANTIC_CITY'
]
