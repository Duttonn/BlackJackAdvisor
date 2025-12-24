"""
Unit tests for Betting Engine.
Tests Kelly criterion and EV estimation.
"""

import pytest
from src.betting import (
    BettingEngine, BettingConfig,
    KellyCalculator, BetLimits,
    EVEstimator, AdvantageModel
)


class TestKellyCalculator:
    """Tests for KellyCalculator class."""

    def test_full_kelly_calculation(self):
        """Test full Kelly bet fraction calculation."""
        kelly = KellyCalculator(kelly_fraction=1.0)
        
        # 1% advantage with variance 1.26
        # Kelly = 0.01 / 1.26 ≈ 0.0079
        fraction = kelly.calculate_bet_fraction(0.01)
        assert abs(fraction - 0.01 / 1.26) < 0.001

    def test_half_kelly_calculation(self):
        """Test half Kelly bet fraction calculation."""
        kelly = KellyCalculator(kelly_fraction=0.5)
        
        # Half of full Kelly
        fraction = kelly.calculate_bet_fraction(0.01)
        expected = (0.01 / 1.26) * 0.5
        assert abs(fraction - expected) < 0.001

    def test_no_bet_with_no_advantage(self):
        """Test zero bet with zero or negative advantage."""
        kelly = KellyCalculator()
        
        assert kelly.calculate_bet_fraction(0.0) == 0.0
        assert kelly.calculate_bet_fraction(-0.01) == 0.0

    def test_bet_amount_clamping(self):
        """Test bet amount is clamped to limits."""
        kelly = KellyCalculator(kelly_fraction=1.0)
        limits = BetLimits(table_min=10, table_max=100)
        
        # With huge advantage, should cap at max
        bet = kelly.calculate_bet_amount(0.5, 10000, limits)
        assert bet == 100

    def test_bet_never_exceeds_bankroll(self):
        """Test bet never exceeds bankroll."""
        kelly = KellyCalculator(kelly_fraction=1.0)
        limits = BetLimits(table_min=10, table_max=1000)
        
        bet = kelly.calculate_bet_amount(0.1, 50, limits)
        assert bet <= 50


class TestEVEstimator:
    """Tests for EVEstimator class."""

    def test_breakeven_count(self):
        """Test breakeven count calculation."""
        model = AdvantageModel(slope=0.005, baseline_edge=0.005)
        estimator = EVEstimator(model)
        
        # Breakeven: 0 = TC * 0.005 - 0.005
        # TC = 1
        assert abs(estimator.breakeven_count() - 1.0) < 0.01

    def test_positive_advantage(self):
        """Test positive advantage at high count."""
        estimator = EVEstimator()
        
        # At TC = +3: advantage = 3 * 0.005 - 0.005 = 0.01 (1%)
        advantage = estimator.estimate_advantage(3.0)
        assert advantage > 0
        assert abs(advantage - 0.01) < 0.002

    def test_negative_advantage(self):
        """Test negative advantage at low count."""
        estimator = EVEstimator()
        
        # At TC = -2: advantage = -2 * 0.005 - 0.005 = -0.015 (-1.5%)
        advantage = estimator.estimate_advantage(-2.0)
        assert advantage < 0

    def test_ev_per_hand(self):
        """Test EV calculation per hand."""
        estimator = EVEstimator()
        
        # At TC = +3 with 1% advantage and $100 bet
        ev = estimator.estimate_ev_per_hand(3.0, 100)
        assert ev > 0

    def test_wong_out_threshold(self):
        """Test wong out threshold calculation."""
        estimator = EVEstimator()
        
        # Threshold for 0% advantage = breakeven
        threshold = estimator.wong_out_threshold(0.0)
        assert abs(threshold - estimator.breakeven_count()) < 0.01


class TestBettingEngine:
    """Tests for BettingEngine class."""

    @pytest.fixture
    def engine(self):
        """Create a betting engine for testing."""
        config = BettingConfig(
            kelly_fraction=0.5,
            table_min=10.0,
            table_max=500.0,
            max_spread=12.0
        )
        return BettingEngine(config)

    def test_minimum_bet_negative_count(self, engine):
        """Test minimum bet at negative counts."""
        bet = engine.compute_bet(-2.0, 1000)
        
        # Should be table minimum (or close to it)
        assert bet >= 10.0
        assert bet <= 20.0  # Not much more than minimum

    def test_increased_bet_positive_count(self, engine):
        """Test increased bet at positive counts."""
        bet = engine.compute_bet(4.0, 10000)
        
        # With advantage, should bet more than minimum
        assert bet > 10.0

    def test_bet_spread_limit(self, engine):
        """Test bet doesn't exceed spread limit."""
        bet = engine.compute_bet(10.0, 100000)
        
        # Max spread is 12x minimum = $120
        assert bet <= 12 * 10.0

    def test_bankroll_constraint(self, engine):
        """Test bet doesn't exceed bankroll."""
        bet = engine.compute_bet(5.0, 50)
        
        # Even with advantage, can't bet more than bankroll
        assert bet <= 50

    def test_insufficient_bankroll(self, engine):
        """Test zero bet with insufficient bankroll."""
        bet = engine.compute_bet(5.0, 5)
        
        # Can't afford table minimum
        assert bet == 0.0

    def test_compute_bet_units(self, engine):
        """Test bet units calculation."""
        # At breakeven, should be 1 unit
        units = engine.compute_bet_units(1.0)  # Approximately breakeven
        assert units >= 1.0
        
        # At high count, should be more units
        high_units = engine.compute_bet_units(5.0)
        assert high_units > units

    def test_should_bet_positive(self, engine):
        """Test should_bet returns True with advantage."""
        assert engine.should_bet(3.0)

    def test_should_bet_negative(self, engine):
        """Test should_bet returns False without advantage."""
        assert not engine.should_bet(-1.0)

    def test_wong_out(self, engine):
        """Test wong out recommendation."""
        # At very negative count, should wong out
        assert engine.should_wong_out(-2.0)
        
        # At positive count, should stay
        assert not engine.should_wong_out(2.0)

    def test_get_advantage(self, engine):
        """Test getting advantage for a count."""
        advantage = engine.get_advantage(3.0)
        assert advantage > 0

    def test_get_expected_value(self, engine):
        """Test EV calculation."""
        ev = engine.get_expected_value(3.0, 100)
        
        # With positive count and $100 bet, EV should be positive
        assert ev > 0

    def test_defensive_cutoff_forces_minimum_bet(self):
        """Test that defensive cutoff forces table minimum at deep penetration."""
        config = BettingConfig(
            table_min=25.0,
            max_spread=8.0,
            max_betting_penetration=0.85  # Cutoff at 85%
        )
        engine = BettingEngine(config=config)
        
        # High true count should normally produce large bet
        normal_bet = engine.compute_bet(
            true_count=5.0, 
            bankroll=10000,
            penetration=0.50  # Safe penetration
        )
        assert normal_bet > config.table_min  # Should scale up
        
        # Same count but beyond cutoff should force minimum
        cutoff_bet = engine.compute_bet(
            true_count=5.0,
            bankroll=10000,
            penetration=0.90  # Beyond cutoff
        )
        assert cutoff_bet == config.table_min  # Defensive minimum
        
    def test_defensive_cutoff_boundary(self):
        """Test defensive cutoff at exactly the boundary."""
        config = BettingConfig(
            table_min=10.0,
            max_betting_penetration=0.85
        )
        engine = BettingEngine(config=config)
        
        # At exactly 0.85 - should still scale (boundary is >)
        at_boundary = engine.compute_bet(true_count=4.0, bankroll=5000, penetration=0.85)
        # Just above 0.85 - should cutoff
        above_boundary = engine.compute_bet(true_count=4.0, bankroll=5000, penetration=0.851)
        
        assert at_boundary > config.table_min  # Still scaling
        assert above_boundary == config.table_min  # Cutoff active
