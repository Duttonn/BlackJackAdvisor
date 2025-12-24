"""
Unit tests for Strategy Engine.
Tests decision pipeline and deviation logic.
"""

import pytest
from src.core import Card, Hand, Action, Rank, Suit, GameState
from src.strategy import StrategyEngine, RuleConfig, DeviationEngine
from src.strategy.deviations import (
    Deviation, DeviationTrigger, DeviationRule,
    ILLUSTRIOUS_18, FAB_4, create_standard_deviation_engine
)
from src.core.types import HandType, DeviationDirection


class TestStrategyEngine:
    """Tests for StrategyEngine class."""

    @pytest.fixture
    def engine(self):
        """Create a strategy engine for testing."""
        config = RuleConfig(
            dealer_stands_soft_17=True,
            double_after_split=True,
            surrender_allowed=True,
            num_decks=6
        )
        return StrategyEngine(config)

    @pytest.fixture
    def neutral_metrics(self):
        """Create neutral count metrics."""
        return GameState(
            true_count=0.0,
            cards_remaining=260,
            running_count=0,
            decks_remaining=5.0
        )

    def test_hard_17_stand(self, engine, neutral_metrics):
        """Test standing on hard 17."""
        hand = Hand.from_cards([
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.SEVEN, Suit.HEARTS)
        ])
        dealer = Card(Rank.TEN, Suit.DIAMONDS)
        
        action = engine.decide(hand, dealer, neutral_metrics)
        assert action == Action.STAND

    def test_hard_16_vs_7_hit(self, engine, neutral_metrics):
        """Test hitting hard 16 vs 7."""
        hand = Hand.from_cards([
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.SIX, Suit.HEARTS)
        ])
        dealer = Card(Rank.SEVEN, Suit.DIAMONDS)
        
        action = engine.decide(hand, dealer, neutral_metrics)
        assert action == Action.HIT

    def test_hard_11_double(self, engine, neutral_metrics):
        """Test doubling on hard 11."""
        hand = Hand.from_cards([
            Card(Rank.SIX, Suit.SPADES),
            Card(Rank.FIVE, Suit.HEARTS)
        ])
        dealer = Card(Rank.SIX, Suit.DIAMONDS)
        
        action = engine.decide(hand, dealer, neutral_metrics)
        assert action == Action.DOUBLE

    def test_pair_8s_split(self, engine, neutral_metrics):
        """Test splitting pair of 8s."""
        hand = Hand.from_cards([
            Card(Rank.EIGHT, Suit.SPADES),
            Card(Rank.EIGHT, Suit.HEARTS)
        ])
        dealer = Card(Rank.TEN, Suit.DIAMONDS)
        
        action = engine.decide(hand, dealer, neutral_metrics)
        assert action == Action.SPLIT

    def test_soft_18_vs_9_hit(self, engine, neutral_metrics):
        """Test hitting soft 18 vs 9."""
        hand = Hand.from_cards([
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.SEVEN, Suit.HEARTS)
        ])
        dealer = Card(Rank.NINE, Suit.DIAMONDS)
        
        action = engine.decide(hand, dealer, neutral_metrics)
        assert action == Action.HIT

    def test_always_returns_action(self, engine, neutral_metrics):
        """Test that engine always returns a valid action."""
        # Test various edge cases
        hands = [
            Hand.from_cards([Card(Rank.TWO, Suit.SPADES), Card(Rank.THREE, Suit.HEARTS)]),
            Hand.from_cards([Card(Rank.ACE, Suit.SPADES), Card(Rank.ACE, Suit.HEARTS)]),
            Hand.from_cards([Card(Rank.TEN, Suit.SPADES), Card(Rank.TEN, Suit.HEARTS)]),
        ]
        
        for hand in hands:
            for dealer_rank in [Rank.TWO, Rank.SEVEN, Rank.TEN, Rank.ACE]:
                dealer = Card(dealer_rank, Suit.DIAMONDS)
                action = engine.decide(hand, dealer, neutral_metrics)
                assert action is not None
                assert isinstance(action, Action)


class TestDeviationEngine:
    """Tests for DeviationEngine class."""

    @pytest.fixture
    def deviation_engine(self):
        """Create a standard deviation engine."""
        return create_standard_deviation_engine()

    def test_16v10_deviation_positive(self, deviation_engine):
        """Test 16 vs 10 stands at TC >= 0."""
        hand = Hand.from_cards([
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.SIX, Suit.HEARTS)
        ])
        dealer = Card(Rank.TEN, Suit.DIAMONDS)
        
        # At TC = 0, should stand
        metrics = GameState(true_count=0.0, cards_remaining=260)
        action = deviation_engine.check_deviation(hand, dealer, metrics)
        assert action == Action.STAND

    def test_16v10_no_deviation_negative(self, deviation_engine):
        """Test 16 vs 10 hits at TC < 0."""
        hand = Hand.from_cards([
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.SIX, Suit.HEARTS)
        ])
        dealer = Card(Rank.TEN, Suit.DIAMONDS)
        
        # At TC = -1, deviation doesn't trigger
        metrics = GameState(true_count=-1.0, cards_remaining=260)
        action = deviation_engine.check_deviation(hand, dealer, metrics)
        assert action is None  # No deviation, use baseline

    def test_12v3_deviation(self, deviation_engine):
        """Test 12 vs 3 stands at TC >= 2."""
        hand = Hand.from_cards([
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.TWO, Suit.HEARTS)
        ])
        dealer = Card(Rank.THREE, Suit.DIAMONDS)
        
        # At TC = 2, should stand
        metrics = GameState(true_count=2.0, cards_remaining=260)
        action = deviation_engine.check_deviation(hand, dealer, metrics)
        assert action == Action.STAND

    def test_fab4_surrender_15v10(self, deviation_engine):
        """Test Fab 4 surrender 15 vs 10 at TC >= 0."""
        hand = Hand.from_cards([
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.FIVE, Suit.HEARTS)
        ])
        dealer = Card(Rank.TEN, Suit.DIAMONDS)
        
        metrics = GameState(true_count=0.0, cards_remaining=260)
        action = deviation_engine.check_surrender_deviation(hand, dealer, metrics)
        assert action == Action.SURRENDER

    def test_fab4_no_surrender_negative(self, deviation_engine):
        """Test no surrender 15 vs 10 at TC < 0."""
        hand = Hand.from_cards([
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.FIVE, Suit.HEARTS)
        ])
        dealer = Card(Rank.TEN, Suit.DIAMONDS)
        
        metrics = GameState(true_count=-1.0, cards_remaining=260)
        action = deviation_engine.check_surrender_deviation(hand, dealer, metrics)
        assert action is None


class TestIntegratedDecisions:
    """Integration tests for strategy with deviations."""

    @pytest.fixture
    def full_engine(self):
        """Create a fully configured strategy engine."""
        config = RuleConfig(
            dealer_stands_soft_17=True,
            double_after_split=True,
            surrender_allowed=True,
            num_decks=6
        )
        return StrategyEngine(config)

    def test_16v10_with_positive_count(self, full_engine):
        """Test 16 vs 10 with positive count triggers deviation."""
        hand = Hand.from_cards([
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.SIX, Suit.HEARTS)
        ])
        dealer = Card(Rank.TEN, Suit.DIAMONDS)
        
        # Positive count - should stand
        metrics = GameState(true_count=1.0, cards_remaining=260)
        action = full_engine.decide(hand, dealer, metrics)
        assert action == Action.STAND

    def test_surrender_priority(self, full_engine):
        """Test that surrender deviations are checked first."""
        hand = Hand.from_cards([
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.FIVE, Suit.HEARTS)
        ])
        dealer = Card(Rank.TEN, Suit.DIAMONDS)
        
        # At TC = 0, should surrender (Fab 4)
        metrics = GameState(true_count=0.0, cards_remaining=260)
        action = full_engine.decide(hand, dealer, metrics)
        assert action == Action.SURRENDER
