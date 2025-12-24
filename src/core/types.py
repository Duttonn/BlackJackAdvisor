"""
Core type definitions for the Blackjack Decision Engine.
Contains all enums and type aliases used throughout the system.
"""

from enum import Enum, auto
from typing import NamedTuple


class Rank(Enum):
    """
    Card rank enumeration with unique ordinal values.
    
    Each rank has a unique value for proper enum iteration.
    Use the `blackjack_value` property for the card's value in blackjack scoring.
    """
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11      # Unique value for proper enum iteration
    QUEEN = 12     # Unique value for proper enum iteration
    KING = 13      # Unique value for proper enum iteration
    ACE = 14       # Unique value; blackjack value handled by property

    @property
    def blackjack_value(self) -> int:
        """Returns the card's value for blackjack scoring (2-10, face=10, ace=11)."""
        if self.value <= 10:
            return self.value
        elif self.value in (11, 12, 13):  # JACK, QUEEN, KING
            return 10
        else:  # ACE
            return 11

    @property
    def hilo_tag(self) -> int:
        """Returns Hi-Lo counting tag for this rank."""
        if self.value in (2, 3, 4, 5, 6):
            return 1
        elif self.value >= 10:  # 10-value cards and Aces (values 10-14)
            return -1
        return 0

    @property
    def symbol(self) -> str:
        """Returns display symbol for the rank."""
        symbols = {
            2: '2', 3: '3', 4: '4', 5: '5', 6: '6',
            7: '7', 8: '8', 9: '9', 10: 'T', 
            11: 'J', 12: 'Q', 13: 'K', 14: 'A'
        }
        return symbols.get(self.value, str(self.value))


class Suit(Enum):
    """Card suit enumeration."""
    HEARTS = auto()
    DIAMONDS = auto()
    CLUBS = auto()
    SPADES = auto()

    @property
    def symbol(self) -> str:
        """Returns Unicode symbol for the suit."""
        return {'HEARTS': '♥', 'DIAMONDS': '♦', 'CLUBS': '♣', 'SPADES': '♠'}[self.name]


class Action(Enum):
    """Possible player actions in blackjack."""
    STAND = auto()
    HIT = auto()
    DOUBLE = auto()
    SPLIT = auto()
    SURRENDER = auto()

    def __str__(self) -> str:
        return self.name


class HandType(Enum):
    """Classification of hand types for strategy lookup."""
    HARD = 'H'      # Hard total (no usable Ace)
    SOFT = 'S'      # Soft total (Ace counted as 11)
    PAIR = 'P'      # Splittable pair


class DeviationDirection(Enum):
    """Direction for count-based deviation triggers."""
    ABOVE_OR_EQUAL = auto()  # TC >= threshold
    BELOW = auto()           # TC < threshold


class GameState(NamedTuple):
    """Immutable snapshot of current game state for decision engines."""
    true_count: float
    cards_remaining: int
    running_count: int = 0
    decks_remaining: float = 1.0
    penetration: float = 0.0  # Fraction of shoe dealt (0.0 = fresh, 1.0 = fully dealt)
