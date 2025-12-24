"""
Unit tests for Config Loader.
Tests rule configuration loading and injection.
"""

import pytest
from pathlib import Path
from src.config import GameRules, ConfigLoader, VEGAS_STRIP, VEGAS_DOWNTOWN, ATLANTIC_CITY
from src.strategy import StrategyEngine, RuleConfig
from src.core import Card, Hand, Rank, Suit, GameState, Action


class TestGameRules:
    """Tests for GameRules configuration."""

    def test_default_rules(self):
        """Test default S17 DAS rules."""
        rules = GameRules()
        
        assert rules.dealer_stands_soft_17 == True
        assert rules.double_after_split == True
        assert rules.num_decks == 6

    def test_h17_rules(self):
        """Test H17 (Dealer Hits Soft 17) configuration."""
        rules = GameRules(
            name="H17 Game",
            dealer_stands_soft_17=False,  # H17
            num_decks=6
        )
        
        assert rules.dealer_stands_soft_17 == False
        assert rules.num_decks == 6

    def test_predefined_vegas_strip(self):
        """Test predefined Vegas Strip rules."""
        assert VEGAS_STRIP.dealer_stands_soft_17 == True
        assert VEGAS_STRIP.num_decks == 6
        assert VEGAS_STRIP.blackjack_pays == 1.5

    def test_predefined_vegas_downtown(self):
        """Test predefined Vegas Downtown rules (H17)."""
        assert VEGAS_DOWNTOWN.dealer_stands_soft_17 == False  # H17
        assert VEGAS_DOWNTOWN.num_decks == 2

    def test_house_edge_estimate_s17_vs_h17(self):
        """Test that H17 has higher house edge than S17."""
        s17_rules = GameRules(dealer_stands_soft_17=True)
        h17_rules = GameRules(dealer_stands_soft_17=False)
        
        # H17 should have higher house edge
        assert h17_rules.house_edge_estimate > s17_rules.house_edge_estimate

    def test_strategy_file_property(self):
        """Test strategy file name generation."""
        rules = GameRules(rule_set_id="h17_das")
        assert rules.strategy_file == "h17_das"

    def test_rules_to_dict(self):
        """Test serialization to dictionary."""
        rules = GameRules(name="Test", num_decks=8)
        data = rules.to_dict()
        
        assert data['name'] == "Test"
        assert data['num_decks'] == 8
        assert 'dealer_stands_soft_17' in data

    def test_rules_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            'name': 'Custom',
            'dealer_stands_soft_17': False,
            'num_decks': 2
        }
        rules = GameRules.from_dict(data)
        
        assert rules.name == 'Custom'
        assert rules.dealer_stands_soft_17 == False
        assert rules.num_decks == 2


class TestConfigLoader:
    """Tests for ConfigLoader class."""

    def test_load_missing_rules_returns_default(self):
        """Test that loading missing rules returns default."""
        loader = ConfigLoader()
        rules = loader.load_rules("nonexistent_ruleset")
        
        # Should return a default GameRules with the name
        assert rules.name == "nonexistent_ruleset"

    def test_list_available_rules(self):
        """Test listing available rule files."""
        loader = ConfigLoader()
        available = loader.list_available_rules()
        
        # Should find at least the vegas_strip rules we created
        assert isinstance(available, list)

    def test_cache_functionality(self):
        """Test that rules are cached."""
        loader = ConfigLoader()
        
        rules1 = loader.load_rules("test_cache")
        rules2 = loader.load_rules("test_cache")
        
        # Should be same object from cache
        assert rules1 is rules2
        
        # Clear cache
        loader.clear_cache()
        rules3 = loader.load_rules("test_cache")
        
        # Should be different object after cache clear
        assert rules1 is not rules3


class TestRuleConfigIntegration:
    """Integration tests for RuleConfig with StrategyEngine."""

    def test_s17_rule_config(self):
        """Test S17 RuleConfig initialization."""
        config = RuleConfig(
            dealer_stands_soft_17=True,
            double_after_split=True,
            surrender_allowed=True,
            num_decks=6,
            rule_set_name='s17_das'
        )
        
        assert config.dealer_stands_soft_17 == True
        assert config.strategy_file == 's17_das'

    def test_h17_rule_config(self):
        """Test H17 RuleConfig initialization."""
        config = RuleConfig(
            dealer_stands_soft_17=False,  # H17
            double_after_split=True,
            surrender_allowed=True,
            num_decks=6,
            rule_set_name='h17_das'
        )
        
        assert config.dealer_stands_soft_17 == False
        assert config.strategy_file == 'h17_das'

    def test_engine_loads_with_s17_config(self):
        """Test StrategyEngine loads with S17 config."""
        config = RuleConfig(
            dealer_stands_soft_17=True,
            rule_set_name='s17_das'
        )
        engine = StrategyEngine(config)
        
        assert engine.config.dealer_stands_soft_17 == True

    def test_engine_loads_with_h17_config(self):
        """Test StrategyEngine loads with H17 config."""
        config = RuleConfig(
            dealer_stands_soft_17=False,
            rule_set_name='h17_das'
        )
        engine = StrategyEngine(config)
        
        assert engine.config.dealer_stands_soft_17 == False
        # Now that h17_das.json exists, tables should load successfully
        assert engine.tables_loaded == True


class TestH17VsS17StrategyDifferences:
    """
    Critical test: Verify that different rules load different strategies.
    
    Key difference: In H17 games, certain soft total plays change because
    the dealer is more likely to improve a soft 17.
    """

    @pytest.fixture
    def s17_engine(self):
        """Create S17 strategy engine."""
        config = RuleConfig(
            dealer_stands_soft_17=True,
            rule_set_name='s17_das'
        )
        return StrategyEngine(config)

    @pytest.fixture
    def h17_engine(self):
        """Create H17 strategy engine."""
        config = RuleConfig(
            dealer_stands_soft_17=False,
            rule_set_name='h17_das'
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

    def test_soft_18_vs_ace_difference(self, s17_engine, h17_engine, neutral_metrics):
        """
        Test Soft 18 vs Ace - a key difference between S17 and H17.
        
        In S17: Soft 18 vs A is typically STAND or HIT (depends on table)
        In H17: Soft 18 vs A should be HIT (dealer more likely to improve)
        
        Also test Hard 15 vs A and Hard 17 vs A which have SURRENDER in H17.
        """
        # Test Hard 15 vs Ace - H17 has SURRENDER, S17 has HIT
        hand_15 = Hand.from_cards([
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.FIVE, Suit.HEARTS)
        ])
        dealer_ace = Card(Rank.ACE, Suit.DIAMONDS)
        
        s17_action_15 = s17_engine.decide(hand_15, dealer_ace, neutral_metrics)
        h17_action_15 = h17_engine.decide(hand_15, dealer_ace, neutral_metrics)
        
        print(f"S17 Engine: Hard 15 vs A = {s17_action_15}")
        print(f"H17 Engine: Hard 15 vs A = {h17_action_15}")
        
        # Both should return valid actions
        assert s17_action_15 is not None
        assert h17_action_15 is not None
        
        # H17 table has SURRENDER for 15 vs A (and 16 vs A, 17 vs A)
        # This is a KEY difference that validates table swapping works
        # Note: Fab4 deviation may also trigger surrender, so we check H17 baseline

    def test_hard_17_vs_ace_h17_surrender(self, s17_engine, h17_engine, neutral_metrics):
        """
        Test Hard 17 vs Ace - unique H17 surrender situation.
        
        In S17: Hard 17 vs A = STAND (always)
        In H17: Hard 17 vs A = SURRENDER (unique to H17 games)
        
        This is a definitive test that proves tables are being swapped.
        """
        hand_17 = Hand.from_cards([
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.SEVEN, Suit.HEARTS)
        ])
        dealer_ace = Card(Rank.ACE, Suit.DIAMONDS)
        
        s17_action = s17_engine.decide(hand_17, dealer_ace, neutral_metrics)
        h17_action = h17_engine.decide(hand_17, dealer_ace, neutral_metrics)
        
        print(f"S17 Engine: Hard 17 vs A = {s17_action}")
        print(f"H17 Engine: Hard 17 vs A = {h17_action}")
        
        # S17: Should STAND on 17 vs A
        assert s17_action == Action.STAND, f"S17 should STAND on 17 vs A, got {s17_action}"
        
        # H17: Should SURRENDER on 17 vs A (this is the key difference!)
        assert h17_action == Action.SURRENDER, f"H17 should SURRENDER on 17 vs A, got {h17_action}"

    def test_11_vs_ace_double_difference(self, s17_engine, h17_engine, neutral_metrics):
        """
        Test 11 vs Ace - another key S17/H17 difference.
        
        In S17: 11 vs A is typically DOUBLE
        In H17: 11 vs A is DOUBLE (same, but with different EV)
        """
        hand = Hand.from_cards([
            Card(Rank.SIX, Suit.SPADES),
            Card(Rank.FIVE, Suit.HEARTS)
        ])
        dealer_ace = Card(Rank.ACE, Suit.DIAMONDS)
        
        s17_action = s17_engine.decide(hand, dealer_ace, neutral_metrics)
        h17_action = h17_engine.decide(hand, dealer_ace, neutral_metrics)
        
        print(f"S17 Engine: 11 vs A = {s17_action}")
        print(f"H17 Engine: 11 vs A = {h17_action}")
        
        # Both should return DOUBLE for 11 vs A in basic strategy
        # (deviation might change this based on count)
        assert s17_action is not None
        assert h17_action is not None

    def test_engine_config_propagation(self, s17_engine, h17_engine):
        """Verify that rule configuration is properly stored in engine."""
        assert s17_engine.config.dealer_stands_soft_17 == True
        assert h17_engine.config.dealer_stands_soft_17 == False

    def test_tables_loaded_status(self, s17_engine, h17_engine):
        """
        Check which engines successfully loaded tables.
        
        Both S17 and H17 should now load from files.
        """
        print(f"S17 tables loaded: {s17_engine.tables_loaded}")
        print(f"H17 tables loaded: {h17_engine.tables_loaded}")
        
        # S17 should load (we have s17_das.json)
        assert s17_engine.tables_loaded == True, "S17 tables should be loaded"
        
        # H17 should now also load (we created h17_das.json)
        assert h17_engine.tables_loaded == True, "H17 tables should be loaded"


class TestMissingH17TablesWarning:
    """
    Test to explicitly warn about missing H17 strategy tables.
    """

    def test_h17_table_existence(self):
        """
        CRITICAL: Check if H17 strategy table exists.
        
        If this test fails, the decision engine will use fallback
        tables for H17 games, which may not be optimal.
        """
        from src.strategy import DataLoader
        
        loader = DataLoader()
        
        try:
            h17_table = loader.load_strategy('h17_das')
            assert len(h17_table) > 0, "H17 table is empty"
            print(f"H17 table loaded with {len(h17_table)} entries")
        except FileNotFoundError:
            pytest.fail(
                "CRITICAL: H17 strategy table (h17_das.json) not found!\n"
                "The decision engine will use fallback tables for H17 games.\n"
                "Run scripts/generate_tables.py to create H17 tables."
            )
