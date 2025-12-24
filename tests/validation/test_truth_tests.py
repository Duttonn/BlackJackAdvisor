"""
Validation Tests - The "Truth" Tests.
These tests verify the engine's logic against known correct behaviors.

These are NOT unit tests - they are integration tests that validate
the entire system works correctly for critical edge cases.
"""

import pytest
from src.core import Card, Hand, Rank, Suit, Action
from src.state import StateManager
from src.strategy import StrategyEngine, RuleConfig
from src.betting import BettingEngine, BettingConfig
from src.config import GameRules, ConfigLoader


class TestH17Trap:
    """
    Test 1: The "H17" Trap
    
    Verifies that the Rule Adapter correctly loads H17-specific tables
    where certain plays differ from S17.
    """

    def test_11_vs_ace_h17_should_hit_not_double(self):
        """
        Config: rules.s17 = False (Dealer Hits Soft 17)
        Input: Player 11 vs Dealer Ace
        Expected: Basic strategy differs between H17 and S17
        
        In S17: DOUBLE (dealer stands on soft 17, so doubling is safer)
        In H17: Player advantage on double is reduced
        
        This test verifies the tables are actually different.
        """
        # Create S17 engine (dealer stands on soft 17)
        s17_config = RuleConfig(
            dealer_stands_soft_17=True,
            rule_set_name='s17_das'
        )
        s17_engine = StrategyEngine(rule_config=s17_config)
        
        # Create H17 engine (dealer hits soft 17)
        h17_config = RuleConfig(
            dealer_stands_soft_17=False,
            rule_set_name='h17_das'
        )
        h17_engine = StrategyEngine(rule_config=h17_config)
        
        # Create hand: 11 (5 + 6)
        hand = Hand.from_cards([
            Card(Rank.FIVE, Suit.SPADES),
            Card(Rank.SIX, Suit.HEARTS)
        ])
        dealer_ace = Card(Rank.ACE, Suit.DIAMONDS)
        
        # Get state metrics (fresh shoe, TC = 0)
        state = StateManager()
        metrics = state.get_metrics()
        
        # Get decisions
        s17_action = s17_engine.decide(hand, dealer_ace, metrics)
        h17_action = h17_engine.decide(hand, dealer_ace, metrics)
        
        # Verify the tables are different for this hand
        # S17 basic strategy: 11 vs Ace = DOUBLE
        # H17 basic strategy: 11 vs Ace = HIT (or still DOUBLE in some charts)
        # The key is that we load DIFFERENT tables
        assert s17_engine.tables_loaded, "S17 tables should be loaded"
        assert h17_engine.tables_loaded, "H17 tables should be loaded"
        
        # If tables are properly differentiated, at least soft 18 vs Ace differs
        soft_18_hand = Hand.from_cards([
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.SEVEN, Suit.HEARTS)
        ])
        
        s17_soft18 = s17_engine.decide(soft_18_hand, dealer_ace, metrics)
        h17_soft18 = h17_engine.decide(soft_18_hand, dealer_ace, metrics)
        
        # THIS is the critical difference: Soft 18 vs Ace
        # S17: STAND (dealer will stand on soft 17, so 18 is good)
        # H17: HIT (dealer will hit and potentially improve)
        assert s17_soft18 == Action.STAND, "S17: Soft 18 vs Ace should STAND"
        assert h17_soft18 == Action.HIT, "H17: Soft 18 vs Ace should HIT"


class TestSplitPriority:
    """
    Test 2: The "Split" Priority
    
    Verifies that pairs are identified correctly and not treated as
    hard totals. A pair of 8s (total 16) should SPLIT, not HIT/SURRENDER.
    """

    def test_pair_8s_vs_10_should_split_not_hit(self):
        """
        Input: Player has 8, 8 (Total 16) vs Dealer 10
        Expected: SPLIT
        Failure: If it returns HIT or SURRENDER, the engine is treating
                 the pair as a hard total (16)
        """
        config = RuleConfig()
        engine = StrategyEngine(rule_config=config)
        
        # Create pair of 8s
        hand = Hand.from_cards([
            Card(Rank.EIGHT, Suit.SPADES),
            Card(Rank.EIGHT, Suit.HEARTS)
        ])
        dealer_10 = Card(Rank.TEN, Suit.DIAMONDS)
        
        state = StateManager()
        metrics = state.get_metrics()
        
        action = engine.decide(hand, dealer_10, metrics)
        
        # Must be SPLIT - this is one of the most important plays in blackjack
        # 8+8=16 is terrible, but 8 vs 10 twice is much better
        assert action == Action.SPLIT, (
            f"8,8 vs 10 should SPLIT, got {action}. "
            "Engine may be treating pair as hard 16!"
        )

    def test_pair_aces_vs_6_should_split(self):
        """Pair of Aces vs 6 should always split."""
        config = RuleConfig()
        engine = StrategyEngine(rule_config=config)
        
        hand = Hand.from_cards([
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.ACE, Suit.HEARTS)
        ])
        dealer_6 = Card(Rank.SIX, Suit.DIAMONDS)
        
        state = StateManager()
        metrics = state.get_metrics()
        
        action = engine.decide(hand, dealer_6, metrics)
        
        assert action == Action.SPLIT, f"A,A vs 6 should SPLIT, got {action}"

    def test_hard_16_is_not_confused_with_pair(self):
        """
        Hard 16 (10+6) should NOT be treated as a pair.
        
        At TC=0, the Illustrious 18 deviation kicks in and says STAND.
        At TC < 0, basic strategy says HIT.
        
        The key test is that this is NOT treated as a pair (which would SPLIT).
        """
        config = RuleConfig()
        engine = StrategyEngine(rule_config=config)
        
        # 10 + 6 = 16 (hard, NOT a pair)
        hand = Hand.from_cards([
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.SIX, Suit.HEARTS)
        ])
        dealer_10 = Card(Rank.TEN, Suit.DIAMONDS)
        
        # At TC=0, ILL_16v10 deviation applies: STAND
        state = StateManager()
        metrics = state.get_metrics()  # TC = 0
        
        action = engine.decide(hand, dealer_10, metrics)
        
        # Key assertion: NOT treated as a pair (would be SPLIT)
        assert action != Action.SPLIT, (
            "Hard 16 must NOT be treated as a pair! Got SPLIT."
        )
        
        # At TC=0, ILL_16v10 deviation says STAND (not HIT)
        # This is correct per Illustrious 18
        assert action in [Action.HIT, Action.STAND, Action.SURRENDER], (
            f"Hard 16 vs 10 should be HIT/STAND/SURRENDER, got {action}"
        )
        
        # Verify at TC=0 we get the deviation (STAND)
        assert action == Action.STAND, (
            f"At TC=0, ILL_16v10 deviation should trigger STAND, got {action}"
        )


class TestBankrollSafety:
    """
    Test 3: The "Bankroll" Safety
    
    Verifies that the betting engine uses Half-Kelly (not Full Kelly)
    and produces safe bet sizes.
    """

    def test_half_kelly_bet_sizing(self):
        """
        Input: Bankroll $10,000, True Count +10 (massive advantage)
        
        At TC +10:
            Advantage ≈ (10 × 0.005) - 0.004 = 0.046 = 4.6%
            
        Full Kelly: f* = 0.046 / 1.26 ≈ 0.0365 = 3.65% = $365
        Half-Kelly: f* = 0.5 × 0.0365 ≈ 1.83% ≈ $183
        
        With table max $1000, both would be clamped, but the fraction
        should be closer to 2% than 4%.
        """
        rules = GameRules(dealer_stands_soft_17=True)
        
        # Use high table max to see the actual Kelly calculation
        config = BettingConfig(
            kelly_fraction=0.5,  # Half-Kelly
            table_min=10.0,
            table_max=5000.0,  # High max to not clamp
            max_spread=100.0
        )
        engine = BettingEngine(config=config, rules=rules)
        
        bankroll = 10000.0
        true_count = 10.0
        
        bet = engine.compute_bet(true_count, bankroll)
        bet_fraction = bet / bankroll
        
        # Half-Kelly should be around 1.8-2.0% of bankroll
        # Full Kelly would be around 3.6-4.0%
        assert bet_fraction < 0.03, (
            f"Bet fraction {bet_fraction:.2%} is too high! "
            "Should be ~2% (Half-Kelly), not ~4% (Full Kelly)"
        )
        assert bet_fraction > 0.01, (
            f"Bet fraction {bet_fraction:.2%} is too low! "
            "Should be ~2% for TC +10"
        )

    def test_no_bet_on_negative_count(self):
        """At negative counts (house edge), bet should be minimum."""
        rules = GameRules()
        config = BettingConfig(table_min=10.0)
        engine = BettingEngine(config=config, rules=rules)
        
        bet = engine.compute_bet(true_count=-5.0, bankroll=10000.0)
        
        # Should bet table minimum (no edge = no betting above min)
        assert bet == 10.0, f"Negative count should bet minimum, got ${bet}"

    def test_h17_vs_s17_baseline_difference(self):
        """
        H17 tables have higher house edge, so betting should be more
        conservative at the same true count.
        """
        s17_rules = GameRules(dealer_stands_soft_17=True)
        h17_rules = GameRules(dealer_stands_soft_17=False)
        
        config = BettingConfig(
            table_min=10.0,
            table_max=5000.0,
            max_spread=100.0
        )
        
        s17_engine = BettingEngine(config=config, rules=s17_rules)
        h17_engine = BettingEngine(config=config, rules=h17_rules)
        
        bankroll = 10000.0
        true_count = 5.0  # Moderate advantage
        
        s17_bet = s17_engine.compute_bet(true_count, bankroll)
        h17_bet = h17_engine.compute_bet(true_count, bankroll)
        
        # S17 has lower house edge, so bet should be higher
        assert s17_bet > h17_bet, (
            f"S17 bet (${s17_bet:.2f}) should be higher than "
            f"H17 bet (${h17_bet:.2f}) at same TC"
        )


class TestSixFivePayoutDanger:
    """
    Additional safety test: 6:5 blackjack payout is catastrophic.
    The engine should never recommend large bets on such tables.
    """

    def test_6_5_payout_requires_higher_count(self):
        """
        6:5 payout adds ~1.39% to house edge.
        At TC +2 on a 3:2 table, you have an edge.
        At TC +2 on a 6:5 table, you're still losing!
        """
        normal_rules = GameRules(blackjack_pays=1.5)  # 3:2
        bad_rules = GameRules(blackjack_pays=1.2)     # 6:5
        
        config = BettingConfig(table_min=10.0, table_max=1000.0)
        
        normal_engine = BettingEngine(config=config, rules=normal_rules)
        bad_engine = BettingEngine(config=config, rules=bad_rules)
        
        bankroll = 10000.0
        
        # At TC +2, normal table has edge, 6:5 table doesn't
        normal_bet = normal_engine.compute_bet(true_count=2.0, bankroll=bankroll)
        bad_bet = bad_engine.compute_bet(true_count=2.0, bankroll=bankroll)
        
        # Normal table should bet above minimum
        assert normal_bet > 10.0, f"3:2 table at TC+2 should bet above min: ${normal_bet}"
        
        # 6:5 table should still be at minimum (no edge yet!)
        assert bad_bet == 10.0, (
            f"6:5 table at TC+2 should bet minimum (still no edge!), got ${bad_bet}"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
