"""
Blackjack Decision Engine - Main package exports.
"""

from .core import (
    Rank, Suit, Action, HandType, DeviationDirection, GameState,
    Card, Hand
)

from .state import StateManager, GameRules as StateGameRules

from .strategy import (
    StrategyEngine, RuleConfig, DataLoader, StrategyLookup,
    DeviationEngine, create_standard_deviation_engine
)

from .betting import (
    BettingEngine, BettingConfig, KellyCalculator, EVEstimator
)

from .config import (
    GameRules, ConfigLoader, VEGAS_STRIP, VEGAS_DOWNTOWN, ATLANTIC_CITY
)

__version__ = "0.1.0"

__all__ = [
    # Core types
    'Rank', 'Suit', 'Action', 'HandType', 'DeviationDirection', 'GameState',
    'Card', 'Hand',
    # State management
    'StateManager',
    # Strategy
    'StrategyEngine', 'RuleConfig', 'DataLoader', 'StrategyLookup',
    'DeviationEngine', 'create_standard_deviation_engine',
    # Betting
    'BettingEngine', 'BettingConfig', 'KellyCalculator', 'EVEstimator',
    # Configuration
    'GameRules', 'ConfigLoader', 'VEGAS_STRIP', 'VEGAS_DOWNTOWN', 'ATLANTIC_CITY'
]
