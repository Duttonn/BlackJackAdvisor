"""
Integration tests for the full decision pipeline.
Tests end-to-end workflow from cards to actions.
"""

import pytest
from src.core import Card, Hand, Action, Rank, Suit, GameState
from src.state import StateManager, GameRules
from src.strategy import StrategyEngine, RuleConfig
from src.betting import BettingEngine, BettingConfig
from src.betting.kelly import KellyCalculator


class TestFullPipeline:
    """Integration tests for the complete decision pipeline."""

    @pytest.fixture
    def setup_engines(self):
        """Set up all engines for testing."""
        rules = GameRules(num_decks=6, penetration=0.75)
        state_manager = StateManager(rules)
        
        rule_config = RuleConfig(
            dealer_stands_soft_17=True,
            double_after_split=True,
            surrender_allowed=True,
            num_decks=6
        )
        strategy_engine = StrategyEngine(rule_config)
        
        betting_config = BettingConfig(
            kelly_fraction=0.5,
            table_min=10.0,
            table_max=500.0,
            max_spread=12.0
        )
        betting_engine = BettingEngine(betting_config)
        
        return state_manager, strategy_engine, betting_engine

    def test_fresh_shoe_neutral_count(self, setup_engines):
        """Test decisions at start of fresh shoe."""
        state, strategy, betting = setup_engines
        
        # Fresh shoe - should have neutral count
        metrics = state.get_metrics()
        assert abs(metrics.true_count) < 0.01
        
        # Basic hand decision
        hand = Hand.from_cards([
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.SIX, Suit.HEARTS)
        ])
        dealer = Card(Rank.SEVEN, Suit.DIAMONDS)
        
        action = strategy.decide(hand, dealer, metrics)
        assert action == Action.HIT  # 16 vs 7 = Hit at neutral

    def test_positive_count_affects_decision(self, setup_engines):
        """Test that positive count affects decisions."""
        state, strategy, betting = setup_engines
        
        # Observe many low cards to build positive count
        low_cards = [Card(Rank.FIVE, Suit.SPADES) for _ in range(30)]
        state.observe(low_cards)
        
        metrics = state.get_metrics()
        assert metrics.true_count > 4.0  # Should be significantly positive
        
        # 16 vs 10 should STAND at TC >= 0
        hand = Hand.from_cards([
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.SIX, Suit.HEARTS)
        ])
        dealer = Card(Rank.TEN, Suit.DIAMONDS)
        
        action = strategy.decide(hand, dealer, metrics)
        assert action == Action.STAND

    def test_betting_increases_with_count(self, setup_engines):
        """Test that betting increases with positive count."""
        state, strategy, betting = setup_engines
        
        bankroll = 5000.0
        
        # Bet at neutral count
        neutral_metrics = state.get_metrics()
        neutral_bet = betting.compute_bet(
            neutral_metrics.true_count, 
            bankroll,
            penetration=neutral_metrics.penetration
        )
        
        # Build positive count
        low_cards = [Card(Rank.THREE, Suit.SPADES) for _ in range(30)]
        state.observe(low_cards)
        
        positive_metrics = state.get_metrics()
        positive_bet = betting.compute_bet(
            positive_metrics.true_count, 
            bankroll,
            penetration=positive_metrics.penetration
        )
        
        # Bet should be higher with positive count
        assert positive_bet > neutral_bet

    def test_reset_shoe_resets_count(self, setup_engines):
        """Test that shoe reset clears the count."""
        state, strategy, betting = setup_engines
        
        # Build up count
        cards = [Card(Rank.FIVE, Suit.SPADES) for _ in range(20)]
        state.observe(cards)
        
        assert state.running_count != 0
        
        # Reset
        state.reset()
        
        assert state.running_count == 0
        assert state.cards_seen == 0

    def test_complete_hand_workflow(self, setup_engines):
        """Test a complete hand from deal to decision."""
        state, strategy, betting = setup_engines
        
        # Pre-existing count from previous hands
        previous_cards = [
            Card(Rank.FOUR, Suit.SPADES),
            Card(Rank.FIVE, Suit.HEARTS),
            Card(Rank.SIX, Suit.DIAMONDS)
        ]
        state.observe(previous_cards)  # +3 RC
        
        # New hand dealt
        player_cards = [
            Card(Rank.TEN, Suit.CLUBS),
            Card(Rank.EIGHT, Suit.SPADES)
        ]
        dealer_up = Card(Rank.SIX, Suit.HEARTS)
        
        # Observe dealt cards
        state.observe(player_cards)
        state.observe_card(dealer_up)
        
        # Get current metrics
        metrics = state.get_metrics()
        
        # Make decision
        hand = Hand.from_cards(player_cards)
        action = strategy.decide(hand, dealer_up, metrics)
        
        # 18 vs 6 should stand
        assert action == Action.STAND
        
        # Calculate bet for next hand
        bet = betting.compute_bet(
            metrics.true_count, 
            1000,
            penetration=metrics.penetration
        )
        assert bet >= 10.0  # At least minimum


class TestBoundaryEnforcement:
    """Tests for architectural boundary rules."""

    def test_strategy_is_deterministic(self):
        """Test that strategy gives same output for same input."""
        config = RuleConfig()
        engine = StrategyEngine(config)
        
        hand = Hand.from_cards([
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.SIX, Suit.HEARTS)
        ])
        dealer = Card(Rank.SEVEN, Suit.DIAMONDS)
        metrics = GameState(true_count=0.0, cards_remaining=260)
        
        # Same inputs should give same output
        action1 = engine.decide(hand, dealer, metrics)
        action2 = engine.decide(hand, dealer, metrics)
        action3 = engine.decide(hand, dealer, metrics)
        
        assert action1 == action2 == action3

    def test_betting_only_uses_counts(self):
        """Test that betting engine only needs count information."""
        engine = BettingEngine()
        
        # Should work with just count and bankroll
        bet = engine.compute_bet(true_count=2.0, bankroll=1000)
        assert bet > 0
        
        # No card information needed
        advantage = engine.get_advantage(2.0)
        assert advantage is not None

    def test_state_only_observes(self):
        """Test that state manager only observes, doesn't strategize."""
        state = StateManager()
        
        # Can observe cards
        cards = [Card(Rank.TEN, Suit.SPADES)]
        state.observe(cards)
        
        # Returns metrics, not decisions
        metrics = state.get_metrics()
        assert hasattr(metrics, 'true_count')
        assert hasattr(metrics, 'cards_remaining')
        # No 'action' or 'decision' attribute


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_hand_rejected(self):
        """Test that empty hand creation raises error."""
        with pytest.raises(ValueError):
            Hand.from_cards([])

    def test_invalid_kelly_fraction_rejected(self):
        """Test that invalid Kelly fraction raises error."""
        with pytest.raises(ValueError):
            KellyCalculator(kelly_fraction=1.5)
        
        with pytest.raises(ValueError):
            KellyCalculator(kelly_fraction=0.0)

    def test_hand_immutability_preserved(self):
        """Test that hand operations don't mutate original."""
        original_cards = [
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.FIVE, Suit.HEARTS)
        ]
        hand = Hand.from_cards(original_cards)
        original_total = hand.total
        
        # Add card
        new_hand = hand.add_card(Card(Rank.THREE, Suit.DIAMONDS))
        
        # Original unchanged
        assert hand.total == original_total
        assert len(hand.cards) == 2
        
        # New hand different
        assert new_hand.total != hand.total
        assert len(new_hand.cards) == 3
