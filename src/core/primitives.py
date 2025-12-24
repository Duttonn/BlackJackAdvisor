"""
Core immutable primitives for the Blackjack Decision Engine.
Card and Hand are hashable and immutable for use as dictionary keys.
"""

from dataclasses import dataclass
from typing import Tuple, List
from .types import Rank, Suit, HandType


@dataclass(frozen=True)
class Card:
    """
    Immutable card representation.
    Hashable for use in sets and as dictionary keys.
    """
    rank: Rank
    suit: Suit

    @property
    def value(self) -> int:
        """Returns the blackjack value of this card (2-10, face cards=10, Ace=11)."""
        return self.rank.blackjack_value

    @property
    def hilo_tag(self) -> int:
        """Returns the Hi-Lo counting tag for this card."""
        return self.rank.hilo_tag

    @property
    def is_ace(self) -> bool:
        """Returns True if this card is an Ace."""
        return self.rank == Rank.ACE

    @property
    def is_ten(self) -> bool:
        """Returns True if this card is a 10-value card (T, J, Q, K)."""
        return self.rank.blackjack_value == 10

    def __str__(self) -> str:
        return f"{self.rank.symbol}{self.suit.symbol}"

    def __repr__(self) -> str:
        return f"Card({self.rank.name}, {self.suit.name})"

    @classmethod
    def from_string(cls, s: str, suit: Suit = Suit.SPADES) -> 'Card':
        """
        Create a Card from a string like '2', 'T', 'J', 'Q', 'K', 'A'.
        Suit defaults to SPADES if not specified.
        """
        rank_map = {
            '2': Rank.TWO, '3': Rank.THREE, '4': Rank.FOUR,
            '5': Rank.FIVE, '6': Rank.SIX, '7': Rank.SEVEN,
            '8': Rank.EIGHT, '9': Rank.NINE, 'T': Rank.TEN,
            '10': Rank.TEN, 'J': Rank.JACK, 'Q': Rank.QUEEN,
            'K': Rank.KING, 'A': Rank.ACE
        }
        rank = rank_map.get(s.upper())
        if rank is None:
            raise ValueError(f"Invalid card string: {s}")
        return cls(rank=rank, suit=suit)


@dataclass(frozen=True)
class Hand:
    """
    Immutable hand representation.
    Hashable for caching strategy lookups.
    
    Invariant: total is always calculated treating Ace as 11 if possible <= 21
    """
    cards: Tuple[Card, ...]
    is_pair: bool
    is_soft: bool
    total: int

    def __post_init__(self) -> None:
        """Validate hand invariants."""
        if self.total < 2 or self.total > 31:
            raise ValueError(f"Invalid hand total: {self.total}")

    @classmethod
    def from_cards(cls, cards: List[Card]) -> 'Hand':
        """
        Factory method to create a Hand from a list of cards.
        Automatically calculates total, softness, and pair status.
        """
        if not cards:
            raise ValueError("Cannot create hand with no cards")

        cards_tuple = tuple(cards)
        
        # Calculate total and softness
        total = sum(c.value for c in cards)
        num_aces = sum(1 for c in cards if c.is_ace)
        is_soft = False

        # Reduce aces from 11 to 1 as needed
        aces_as_eleven = num_aces
        while total > 21 and aces_as_eleven > 0:
            total -= 10
            aces_as_eleven -= 1

        # Hand is soft if at least one Ace is still counted as 11
        is_soft = aces_as_eleven > 0 and total <= 21

        # Check for pair (exactly 2 cards of same rank)
        is_pair = (
            len(cards) == 2 and
            cards[0].rank == cards[1].rank
        )

        return cls(
            cards=cards_tuple,
            is_pair=is_pair,
            is_soft=is_soft,
            total=total
        )

    @property
    def hand_type(self) -> HandType:
        """Returns the classification of this hand for strategy lookup."""
        if self.is_pair:
            return HandType.PAIR
        elif self.is_soft:
            return HandType.SOFT
        return HandType.HARD

    @property
    def pair_rank(self) -> Rank:
        """Returns the rank of the pair if this is a pair hand."""
        if not self.is_pair:
            raise ValueError("Not a pair hand")
        return self.cards[0].rank

    @property
    def pair_value(self) -> int:
        """Returns the value used for pair lookup (2-10 for regular cards, 10 for faces, 11 for Ace)."""
        if not self.is_pair:
            raise ValueError("Not a pair hand")
        rank = self.cards[0].rank
        if rank == Rank.ACE:
            return 11  # Aces are treated as 11 for pair splits
        return rank.blackjack_value

    @property
    def is_blackjack(self) -> bool:
        """Returns True if this is a natural blackjack."""
        return len(self.cards) == 2 and self.total == 21

    @property
    def is_busted(self) -> bool:
        """Returns True if the hand has busted."""
        return self.total > 21

    def add_card(self, card: Card) -> 'Hand':
        """Returns a new Hand with the card added."""
        new_cards = list(self.cards) + [card]
        return Hand.from_cards(new_cards)

    def lookup_key(self, dealer_up: Card) -> str:
        """
        Generates the lookup key for strategy tables.
        Format: "{HandType}_{Value}:{DealerUp}"
        """
        hand_type = self.hand_type.value
        
        if self.is_pair:
            # For pairs, use the single card value (formatted as two digits)
            value = f"{self.pair_value:02d}"
        else:
            value = self.total
            
        dealer_value = dealer_up.value if not dealer_up.is_ace else 11
        
        return f"{hand_type}_{value}:{dealer_value:02d}"

    def __str__(self) -> str:
        cards_str = ' '.join(str(c) for c in self.cards)
        return f"[{cards_str}] = {self.total}{'(soft)' if self.is_soft else ''}"

    def __repr__(self) -> str:
        return f"Hand({self.cards}, total={self.total}, soft={self.is_soft}, pair={self.is_pair})"


# Module exports
__all__ = ['Card', 'Hand']
