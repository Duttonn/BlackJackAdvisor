"""
State Manager Module.
Maintains the "World View" - Running Count, True Count, and Shoe tracking.

Responsibility: Observe cards and maintain counting state.
FORBIDDEN: Strategy logic - only observes and counts.
"""

from typing import List, Optional, Dict
from dataclasses import dataclass, field
from collections import Counter

from ..core import Card, GameState


@dataclass
class GameRules:
    """Configuration for game rules affecting state management."""
    num_decks: int = 6
    cards_per_deck: int = 52
    penetration: float = 0.75  # Percentage of shoe dealt before shuffle

    @property
    def total_cards(self) -> int:
        """Total cards in the shoe."""
        return self.num_decks * self.cards_per_deck

    @property
    def cut_card_position(self) -> int:
        """Number of cards dealt before shuffle."""
        return int(self.total_cards * self.penetration)


class StateManager:
    """
    Maintains running count and shoe state using Hi-Lo counting system.
    
    Invariant: decks_remaining must never be <= 0 (clamp to 0.5 minimum).
    """

    def __init__(self, rules: Optional[GameRules] = None):
        """Initialize with default 6-deck shoe."""
        self._rules = rules or GameRules()
        self._running_count: int = 0
        self._cards_seen: int = 0
        self._observed_cards: List[Card] = []

    def observe(self, cards: List[Card]) -> None:
        """
        Updates Running Count based on Hi-Lo tags.
        
        Hi-Lo System:
        - 2-6: +1
        - 7-9: 0
        - 10-A: -1
        
        Args:
            cards: List of cards to observe and count.
        """
        for card in cards:
            self._running_count += card.hilo_tag
            self._cards_seen += 1
            self._observed_cards.append(card)

    def observe_card(self, card: Card) -> None:
        """Convenience method to observe a single card."""
        self.observe([card])

    def get_metrics(self) -> GameState:
        """
        Returns snapshot for Decision/Betting engines.
        
        Output: GameState with true_count, cards_remaining, running_count, decks_remaining, penetration
        """
        cards_remaining = self._rules.total_cards - self._cards_seen
        decks_remaining = self._calculate_decks_remaining()
        true_count = self._calculate_true_count(decks_remaining)
        penetration = self._cards_seen / self._rules.total_cards if self._rules.total_cards > 0 else 0.0

        return GameState(
            true_count=true_count,
            cards_remaining=cards_remaining,
            running_count=self._running_count,
            decks_remaining=decks_remaining,
            penetration=penetration
        )

    def reset(self, rules: Optional[GameRules] = None, burn_count: int = 0) -> None:
        """
        Resets running count and total cards based on rule config.
        
        Supports "late entry" simulation where player sits down mid-shoe
        without having observed the burned cards.
        
        Args:
            rules: New game rules to apply. If None, uses existing rules.
            burn_count: Number of cards already dealt before we sat down.
                        These cards are "burned" from our perspective - we
                        haven't seen them, so RC stays at 0, but cards_seen
                        reflects true penetration for TC calculation.
        """
        if rules is not None:
            self._rules = rules
        self._running_count = 0  # Always start at 0 (we haven't seen any cards)
        self._cards_seen = burn_count  # But shoe may already be partially dealt
        self._observed_cards.clear()

    def _calculate_decks_remaining(self) -> float:
        """
        Calculate decks remaining in the shoe.
        
        Invariant: Never returns less than 0.5 to prevent division issues.
        """
        cards_remaining = self._rules.total_cards - self._cards_seen
        decks = cards_remaining / self._rules.cards_per_deck
        return max(0.5, decks)  # Clamp to minimum of 0.5

    def _calculate_true_count(self, decks_remaining: float) -> float:
        """
        Calculate true count from running count.
        
        True Count = Running Count / Decks Remaining
        """
        return self._running_count / decks_remaining

    @property
    def running_count(self) -> int:
        """Current running count."""
        return self._running_count

    @property
    def cards_seen(self) -> int:
        """Number of cards observed."""
        return self._cards_seen

    @property
    def cards_remaining(self) -> int:
        """Number of cards remaining in shoe."""
        return self._rules.total_cards - self._cards_seen

    @property
    def is_shuffle_due(self) -> bool:
        """Returns True if we've passed the cut card."""
        return self._cards_seen >= self._rules.cut_card_position

    @property
    def true_count(self) -> float:
        """Current true count."""
        return self._calculate_true_count(self._calculate_decks_remaining())

    def get_remaining_by_rank(self) -> Dict[int, int]:
        """
        Get the count of remaining cards for each blackjack value.
        
        Used by ExactCountEstimator to calculate precise EoR-based advantage.
        
        Returns:
            Dict mapping blackjack value (2-11) to count remaining.
            Note: 10 includes all ten-value cards (T, J, Q, K).
                  11 represents Aces.
        """
        # Count observed cards by blackjack value
        observed_counts: Counter = Counter()
        for card in self._observed_cards:
            observed_counts[card.value] += 1
        
        # Calculate remaining for each value
        # Fresh shoe has 4 * num_decks of each rank
        cards_per_rank = 4 * self._rules.num_decks
        ten_value_cards = 16 * self._rules.num_decks  # 4 ranks * 4 suits * num_decks
        
        remaining: Dict[int, int] = {}
        for value in range(2, 10):
            remaining[value] = cards_per_rank - observed_counts.get(value, 0)
        
        # Ten-value cards (10, J, Q, K all have value 10)
        remaining[10] = ten_value_cards - observed_counts.get(10, 0)
        
        # Aces (value 11 in our system)
        remaining[11] = cards_per_rank - observed_counts.get(11, 0)
        
        return remaining

    @property
    def penetration(self) -> float:
        """Current penetration (% of shoe dealt)."""
        if self._rules.total_cards == 0:
            return 0.0
        return self._cards_seen / self._rules.total_cards

    def __repr__(self) -> str:
        return (
            f"StateManager(RC={self._running_count}, "
            f"TC={self.true_count:.2f}, "
            f"seen={self._cards_seen}/{self._rules.total_cards})"
        )


__all__ = ['StateManager', 'GameRules']
