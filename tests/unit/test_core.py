"""
Unit tests for core primitives.
Tests Card and Hand immutability and correctness.
"""

import pytest
from src.core import Card, Hand, Rank, Suit, Action, HandType


class TestCard:
    """Tests for Card class."""

    def test_card_creation(self):
        """Test basic card creation."""
        card = Card(Rank.ACE, Suit.SPADES)
        assert card.rank == Rank.ACE
        assert card.suit == Suit.SPADES
        assert card.value == 11

    def test_card_immutability(self):
        """Test that cards are immutable."""
        card = Card(Rank.KING, Suit.HEARTS)
        with pytest.raises(AttributeError):
            card.rank = Rank.QUEEN

    def test_card_hashable(self):
        """Test that cards can be used as dict keys."""
        card1 = Card(Rank.TEN, Suit.DIAMONDS)
        card2 = Card(Rank.TEN, Suit.DIAMONDS)
        
        card_dict = {card1: "value"}
        assert card_dict[card2] == "value"

    def test_card_hilo_tags(self):
        """Test Hi-Lo counting tags."""
        # Low cards (+1)
        assert Card(Rank.TWO, Suit.SPADES).hilo_tag == 1
        assert Card(Rank.SIX, Suit.SPADES).hilo_tag == 1
        
        # Neutral cards (0)
        assert Card(Rank.SEVEN, Suit.SPADES).hilo_tag == 0
        assert Card(Rank.NINE, Suit.SPADES).hilo_tag == 0
        
        # High cards (-1)
        assert Card(Rank.TEN, Suit.SPADES).hilo_tag == -1
        assert Card(Rank.ACE, Suit.SPADES).hilo_tag == -1

    def test_card_from_string(self):
        """Test creating cards from strings."""
        card = Card.from_string('A')
        assert card.rank == Rank.ACE
        
        card = Card.from_string('T')
        assert card.rank == Rank.TEN
        
        card = Card.from_string('2')
        assert card.rank == Rank.TWO


class TestHand:
    """Tests for Hand class."""

    def test_hand_hard_total(self):
        """Test hard hand total calculation."""
        cards = [
            Card(Rank.KING, Suit.SPADES),
            Card(Rank.SEVEN, Suit.HEARTS)
        ]
        hand = Hand.from_cards(cards)
        
        assert hand.total == 17
        assert not hand.is_soft
        assert not hand.is_pair

    def test_hand_soft_total(self):
        """Test soft hand total calculation."""
        cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.SIX, Suit.HEARTS)
        ]
        hand = Hand.from_cards(cards)
        
        assert hand.total == 17
        assert hand.is_soft

    def test_hand_ace_adjustment(self):
        """Test ace adjustment when over 21."""
        cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.SEVEN, Suit.HEARTS),
            Card(Rank.NINE, Suit.DIAMONDS)
        ]
        hand = Hand.from_cards(cards)
        
        # Should be 17 (1 + 7 + 9), not 27
        assert hand.total == 17
        assert not hand.is_soft  # Ace is now hard

    def test_hand_pair_detection(self):
        """Test pair detection."""
        cards = [
            Card(Rank.EIGHT, Suit.SPADES),
            Card(Rank.EIGHT, Suit.HEARTS)
        ]
        hand = Hand.from_cards(cards)
        
        assert hand.is_pair
        assert hand.pair_value == 8
        assert hand.hand_type == HandType.PAIR

    def test_hand_blackjack(self):
        """Test blackjack detection."""
        cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS)
        ]
        hand = Hand.from_cards(cards)
        
        assert hand.is_blackjack
        assert hand.total == 21
        assert hand.is_soft

    def test_hand_bust(self):
        """Test bust detection."""
        cards = [
            Card(Rank.KING, Suit.SPADES),
            Card(Rank.QUEEN, Suit.HEARTS),
            Card(Rank.FIVE, Suit.DIAMONDS)
        ]
        hand = Hand.from_cards(cards)
        
        assert hand.is_busted
        assert hand.total == 25

    def test_hand_immutability(self):
        """Test that hands are immutable."""
        cards = [
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.FIVE, Suit.HEARTS)
        ]
        hand = Hand.from_cards(cards)
        
        with pytest.raises(AttributeError):
            hand.total = 20

    def test_hand_add_card(self):
        """Test adding a card returns new hand."""
        cards = [
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.FIVE, Suit.HEARTS)
        ]
        hand = Hand.from_cards(cards)
        
        new_card = Card(Rank.THREE, Suit.DIAMONDS)
        new_hand = hand.add_card(new_card)
        
        # Original unchanged
        assert hand.total == 15
        assert len(hand.cards) == 2
        
        # New hand updated
        assert new_hand.total == 18
        assert len(new_hand.cards) == 3

    def test_hand_lookup_key(self):
        """Test strategy lookup key generation."""
        # Hard hand
        cards = [Card(Rank.TEN, Suit.SPADES), Card(Rank.SIX, Suit.HEARTS)]
        hand = Hand.from_cards(cards)
        dealer = Card(Rank.TEN, Suit.DIAMONDS)
        
        key = hand.lookup_key(dealer)
        assert key.startswith("H_16:")

    def test_hand_hashable(self):
        """Test that hands can be used as dict keys."""
        cards = [Card(Rank.TEN, Suit.SPADES), Card(Rank.SIX, Suit.HEARTS)]
        hand1 = Hand.from_cards(cards)
        hand2 = Hand.from_cards(cards)
        
        hand_dict = {hand1: "strategy"}
        assert hand_dict[hand2] == "strategy"
