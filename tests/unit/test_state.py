"""
Unit tests for State Manager.
Tests Hi-Lo counting and game state tracking.
"""

import pytest
from src.core import Card, Rank, Suit, GameState
from src.state import StateManager, GameRules


class TestStateManager:
    """Tests for StateManager class."""

    def test_initial_state(self):
        """Test initial state after creation."""
        manager = StateManager()
        metrics = manager.get_metrics()
        
        assert metrics.running_count == 0
        assert metrics.true_count == 0.0
        assert metrics.cards_remaining == 312  # 6 decks

    def test_observe_single_card(self):
        """Test observing a single card."""
        manager = StateManager()
        
        # Observe a low card (+1)
        card = Card(Rank.FIVE, Suit.SPADES)
        manager.observe_card(card)
        
        assert manager.running_count == 1
        assert manager.cards_seen == 1

    def test_observe_multiple_cards(self):
        """Test observing multiple cards."""
        manager = StateManager()
        
        cards = [
            Card(Rank.TWO, Suit.SPADES),   # +1
            Card(Rank.TEN, Suit.HEARTS),   # -1
            Card(Rank.ACE, Suit.DIAMONDS), # -1
            Card(Rank.FIVE, Suit.CLUBS),   # +1
        ]
        manager.observe(cards)
        
        assert manager.running_count == 0  # +1 -1 -1 +1 = 0
        assert manager.cards_seen == 4

    def test_true_count_calculation(self):
        """Test true count calculation."""
        manager = StateManager()
        
        # Observe 52 cards to consume 1 deck
        # 10 low cards (+10) and 10 high cards (-10) = 0
        low_cards = [Card(Rank.TWO, Suit.SPADES) for _ in range(10)]
        high_cards = [Card(Rank.TEN, Suit.HEARTS) for _ in range(10)]
        neutral_cards = [Card(Rank.SEVEN, Suit.DIAMONDS) for _ in range(32)]
        
        manager.observe(low_cards + high_cards + neutral_cards)
        
        # 52 cards dealt, 5 decks remaining
        # Running count = 0, True count = 0
        metrics = manager.get_metrics()
        assert metrics.running_count == 0
        assert abs(metrics.true_count) < 0.01

    def test_positive_true_count(self):
        """Test positive true count calculation."""
        rules = GameRules(num_decks=6)
        manager = StateManager(rules)
        
        # Observe only low cards (+1 each)
        low_cards = [Card(Rank.THREE, Suit.SPADES) for _ in range(20)]
        manager.observe(low_cards)
        
        # RC = +20, approximately 5.6 decks remaining
        # TC ≈ 20 / 5.6 ≈ +3.5
        metrics = manager.get_metrics()
        assert metrics.running_count == 20
        assert metrics.true_count > 3.0

    def test_negative_true_count(self):
        """Test negative true count calculation."""
        manager = StateManager()
        
        # Observe only high cards (-1 each)
        high_cards = [Card(Rank.ACE, Suit.SPADES) for _ in range(12)]
        manager.observe(high_cards)
        
        metrics = manager.get_metrics()
        assert metrics.running_count == -12
        assert metrics.true_count < -2.0

    def test_reset(self):
        """Test reset functionality."""
        manager = StateManager()
        
        # Build up some count
        cards = [Card(Rank.FIVE, Suit.SPADES) for _ in range(10)]
        manager.observe(cards)
        
        assert manager.running_count == 10
        
        # Reset
        manager.reset()
        
        assert manager.running_count == 0
        assert manager.cards_seen == 0

    def test_reset_with_new_rules(self):
        """Test reset with new rules."""
        manager = StateManager(GameRules(num_decks=6))
        
        # Reset with 8-deck rules
        new_rules = GameRules(num_decks=8)
        manager.reset(new_rules)
        
        metrics = manager.get_metrics()
        assert metrics.cards_remaining == 416  # 8 * 52

    def test_decks_remaining_minimum(self):
        """Test that decks remaining doesn't go below 0.5."""
        rules = GameRules(num_decks=1)
        manager = StateManager(rules)
        
        # Observe almost all cards
        cards = [Card(Rank.SEVEN, Suit.SPADES) for _ in range(50)]
        manager.observe(cards)
        
        # Should clamp to 0.5 minimum
        metrics = manager.get_metrics()
        assert metrics.decks_remaining >= 0.5

    def test_shuffle_due(self):
        """Test shuffle detection."""
        rules = GameRules(num_decks=1, penetration=0.75)
        manager = StateManager(rules)
        
        # Deal 75% of deck
        cards = [Card(Rank.SEVEN, Suit.SPADES) for _ in range(39)]
        manager.observe(cards)
        
        assert manager.is_shuffle_due

    def test_game_state_immutability(self):
        """Test that GameState is immutable."""
        manager = StateManager()
        metrics = manager.get_metrics()
        
        # GameState is a NamedTuple - should be immutable
        with pytest.raises(AttributeError):
            metrics.true_count = 5.0


class TestGameRules:
    """Tests for GameRules configuration."""

    def test_default_rules(self):
        """Test default rule configuration."""
        rules = GameRules()
        
        assert rules.num_decks == 6
        assert rules.cards_per_deck == 52
        assert rules.total_cards == 312

    def test_custom_rules(self):
        """Test custom rule configuration."""
        rules = GameRules(num_decks=8, penetration=0.80)
        
        assert rules.num_decks == 8
        assert rules.total_cards == 416
        assert rules.cut_card_position == 332  # 80% of 416

    def test_penetration_calculation(self):
        """Test cut card position calculation."""
        rules = GameRules(num_decks=6, penetration=0.75)
        
        # 75% of 312 = 234
        assert rules.cut_card_position == 234
