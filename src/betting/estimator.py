"""
EV Estimator Module.
Linear approximation of player advantage based on True Count.

Responsibility: Map True Count to estimated player advantage.
FORBIDDEN: Knowledge of specific cards - only works with counts.

IMPORTANT: The baseline house edge is NOT static - it depends on table rules.
This module adjusts for:
    - H17 vs S17: Dealer hitting soft 17 adds ~0.22% to house edge
    - Blackjack payout: 6:5 vs 3:2 adds ~1.39% to house edge
    - Other rule variations affect the intercept, not the slope
"""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..config.loader import GameRules


@dataclass
class AdvantageModel:
    """
    Linear advantage model parameters.
    
    Advantage = (TC * slope) - baseline_edge
    
    Where:
        TC = True Count
        slope = advantage gain per true count (~0.5% per TC)
        baseline_edge = house edge at TC=0 (varies by rules)
        
    Rule Adjustments to baseline_edge:
        - Base S17 with good rules: ~0.40-0.50%
        - H17 (dealer hits soft 17): +0.22%
        - 6:5 blackjack payout: +1.39%
        - No DAS: +0.14%
        - No surrender: +0.08%
    """
    slope: float = 0.005  # 0.5% per true count (EoR-based, relatively stable)
    baseline_edge: float = 0.005  # 0.5% house edge at TC=0 (S17 DAS baseline)

    def calculate_advantage(self, true_count: float) -> float:
        """
        Calculate player advantage for a given true count.
        
        Args:
            true_count: Current true count.
            
        Returns:
            Player advantage as a decimal (negative = house edge).
        """
        return (true_count * self.slope) - self.baseline_edge

    @classmethod
    def from_rules(cls, rules: "GameRules") -> "AdvantageModel":
        """
        Create an advantage model adjusted for specific game rules.
        
        This is CRITICAL for accurate betting - using hardcoded values
        on an H17 table will cause the engine to overbet because it
        thinks it has an edge when it doesn't.
        
        Args:
            rules: Game rules configuration.
            
        Returns:
            AdvantageModel with rule-adjusted baseline edge.
        """
        # Start with base S17 DAS edge (~0.40%)
        baseline = 0.004
        
        # H17 adjustment: Dealer hitting soft 17 is bad for player
        if not rules.dealer_stands_soft_17:
            baseline += 0.0022  # +0.22%
        
        # Blackjack payout: 6:5 is catastrophic
        if rules.blackjack_pays < 1.4:  # 6:5 = 1.2
            baseline += 0.0139  # +1.39%
        
        # No DAS adjustment
        if not rules.double_after_split:
            baseline += 0.0014  # +0.14%
        
        # No surrender adjustment
        if not rules.surrender_allowed:
            baseline += 0.0008  # +0.08%
        
        # Double restrictions
        if rules.double_10_11_only:
            baseline += 0.0018  # +0.18%
        elif rules.double_9_10_11_only:
            baseline += 0.0009  # +0.09%
        
        return cls(slope=0.005, baseline_edge=baseline)


class EVEstimator:
    """
    Expected Value estimator using linear approximation.
    
    Uses Effect of Removal (EoR) based linear model.
    The relationship between True Count and advantage is approximately linear:
    
        Advantage ≈ 0.5% × True Count - House Edge
    
    CRITICAL: The house edge is NOT static! It depends on table rules.
    
    For a typical 6-deck S17 DAS game:
        House Edge ≈ 0.4%
        Slope ≈ 0.5% per True Count
        
    For an H17 game (dealer hits soft 17):
        House Edge ≈ 0.62%  (+0.22%)
        
    For a 6:5 payout game (AVOID THESE!):
        House Edge ≈ 1.79%  (+1.39%)
        
    Therefore with S17:
        TC = +1 → Advantage ≈ 0.1% (near breakeven)
        TC = +2 → Advantage ≈ 0.6% (player edge)
        TC = +5 → Advantage ≈ 2.1% (strong player edge)
        
    With H17:
        TC = +1 → Advantage ≈ -0.12% (STILL LOSING!)
        TC = +2 → Advantage ≈ 0.38% (barely positive)
    """

    def __init__(
        self,
        model: Optional[AdvantageModel] = None,
        rules: Optional["GameRules"] = None,
        deck_adjustment: bool = True
    ):
        """
        Initialize the EV estimator.
        
        Args:
            model: Advantage model parameters. If not provided, will be
                   derived from rules or use defaults.
            rules: Game rules for calculating baseline edge. Strongly
                   recommended to provide this for accurate betting.
            deck_adjustment: Whether to adjust for number of decks.
            
        WARNING: Using default model without rules will use S17 baseline.
        On an H17 table, this will overestimate your edge and cause overbetting!
        """
        if model is not None:
            self._model = model
        elif rules is not None:
            self._model = AdvantageModel.from_rules(rules)
        else:
            self._model = AdvantageModel()  # Default S17 baseline
            
        self._rules = rules
        self._deck_adjustment = deck_adjustment

    def estimate_advantage(
        self,
        true_count: float,
        num_decks: int = 6
    ) -> float:
        """
        Estimate player advantage from true count.
        
        Args:
            true_count: Current true count.
            num_decks: Number of decks in the shoe.
            
        Returns:
            Estimated player advantage as a decimal.
        """
        base_advantage = self._model.calculate_advantage(true_count)
        
        if self._deck_adjustment:
            # Slight adjustment for deck count
            # More decks = slightly lower slope effectiveness
            deck_factor = 6 / num_decks  # Normalized to 6 decks
            adjustment = 1 + (deck_factor - 1) * 0.1
            base_advantage *= adjustment
        
        return base_advantage

    def estimate_ev_per_hand(
        self,
        true_count: float,
        bet_size: float,
        num_decks: int = 6
    ) -> float:
        """
        Estimate expected value for a given bet.
        
        Args:
            true_count: Current true count.
            bet_size: Size of the bet.
            num_decks: Number of decks.
            
        Returns:
            Expected value in currency units.
        """
        advantage = self.estimate_advantage(true_count, num_decks)
        return bet_size * advantage

    def breakeven_count(self) -> float:
        """
        Calculate the true count at which player breaks even.
        
        Returns:
            True count for 0% advantage.
        """
        # Solve: 0 = (TC * slope) - baseline_edge
        # TC = baseline_edge / slope
        return self._model.baseline_edge / self._model.slope

    def wong_out_threshold(self, min_advantage: float = 0.0) -> float:
        """
        Calculate the true count below which to leave the table.
        
        Args:
            min_advantage: Minimum acceptable advantage (default 0 = breakeven).
            
        Returns:
            True count threshold for wonging out.
        """
        # Solve: min_advantage = (TC * slope) - baseline_edge
        # TC = (min_advantage + baseline_edge) / slope
        return (min_advantage + self._model.baseline_edge) / self._model.slope

    @property
    def model(self) -> AdvantageModel:
        """Current advantage model."""
        return self._model


class EffectOfRemoval:
    """
    Effect of Removal (EoR) values for card counting accuracy.
    
    These values represent the change in player advantage when
    each card is removed from the deck.
    """

    # EoR values (approximate, in percentage points)
    # Positive = removal helps player, Negative = removal hurts player
    EOR_VALUES = {
        2: 0.38,
        3: 0.44,
        4: 0.55,
        5: 0.69,
        6: 0.46,
        7: 0.28,
        8: 0.00,
        9: -0.18,
        10: -0.51,  # 10, J, Q, K
        11: -0.61,  # Ace
    }

    @classmethod
    def get_eor(cls, card_value: int) -> float:
        """
        Get the Effect of Removal for a card value.
        
        Args:
            card_value: The blackjack value of the card (2-11, where 11=Ace).
            
        Returns:
            EoR value in percentage points.
        """
        return cls.EOR_VALUES.get(card_value, 0.0)

    @classmethod
    def hi_lo_correlation(cls) -> float:
        """
        Calculate the betting correlation of the Hi-Lo system.
        
        Hi-Lo has approximately 0.97 betting correlation with EoR.
        """
        return 0.97


class ExactCountEstimator:
    """
    Exact advantage estimator using Effect of Removal (EoR) values.
    
    Unlike the linear Hi-Lo approximation, this calculates the precise
    advantage based on the actual composition of remaining cards in the shoe.
    
    This serves as "Ground Truth" for benchmarking Hi-Lo accuracy.
    
    Formula:
        Exact_Advantage = Σ (EoR[rank] × (cards_remaining[rank] - expected[rank]))
                          ÷ total_cards_remaining
    
    Where expected[rank] is the neutral shoe composition.
    """

    def __init__(
        self,
        rules: Optional["GameRules"] = None,
        num_decks: int = 6
    ):
        """
        Initialize the exact count estimator.
        
        Args:
            rules: Game rules for baseline edge calculation.
            num_decks: Number of decks in the shoe.
        """
        self._num_decks = num_decks
        self._rules = rules
        
        # Calculate baseline edge from rules (same logic as linear model)
        if rules is not None:
            self._baseline_edge = self._calculate_baseline_edge(rules)
        else:
            self._baseline_edge = 0.004  # Default S17 DAS baseline (~0.4%)
        
        # Expected cards per rank in a fresh shoe
        self._expected_per_rank = 4 * num_decks  # 4 suits × num_decks
        self._expected_tens = 16 * num_decks     # 4 ten-values × 4 suits × num_decks
        self._total_cards = 52 * num_decks

    def _calculate_baseline_edge(self, rules: "GameRules") -> float:
        """Calculate baseline house edge from game rules."""
        baseline = 0.004  # Base S17 DAS edge (~0.40%)
        
        if not rules.dealer_stands_soft_17:
            baseline += 0.0022  # H17 adds +0.22%
        
        if rules.blackjack_pays < 1.4:
            baseline += 0.0139  # 6:5 payout adds +1.39%
        
        if not rules.double_after_split:
            baseline += 0.0014  # No DAS adds +0.14%
        
        if not rules.surrender_allowed:
            baseline += 0.0008  # No surrender adds +0.08%
        
        return baseline

    def estimate_advantage(
        self,
        remaining_by_rank: dict,
        total_remaining: int
    ) -> float:
        """
        Calculate exact advantage from shoe composition.
        
        Args:
            remaining_by_rank: Dict mapping card value (2-11) to count remaining.
            total_remaining: Total cards remaining in shoe.
            
        Returns:
            Player advantage as a decimal (negative = house edge).
        """
        if total_remaining <= 0:
            return -self._baseline_edge
        
        # Calculate the EoR-weighted deviation from neutral
        # For each rank, compare actual remaining to expected remaining
        eor_sum = 0.0
        
        for value in range(2, 10):
            actual = remaining_by_rank.get(value, 0)
            # Expected proportion = original count / original total
            expected = self._expected_per_rank * (total_remaining / self._total_cards)
            deviation = expected - actual  # Cards removed vs expected
            eor_sum += EffectOfRemoval.get_eor(value) * deviation
        
        # Ten-value cards
        actual_tens = remaining_by_rank.get(10, 0)
        expected_tens = self._expected_tens * (total_remaining / self._total_cards)
        eor_sum += EffectOfRemoval.get_eor(10) * (expected_tens - actual_tens)
        
        # Aces
        actual_aces = remaining_by_rank.get(11, 0)
        expected_aces = self._expected_per_rank * (total_remaining / self._total_cards)
        eor_sum += EffectOfRemoval.get_eor(11) * (expected_aces - actual_aces)
        
        # Convert to percentage and subtract baseline edge
        # EoR values are in percentage points, so divide by 100
        exact_advantage = (eor_sum / total_remaining) / 100 - self._baseline_edge
        
        return exact_advantage

    def compare_to_hilo(
        self,
        remaining_by_rank: dict,
        total_remaining: int,
        hilo_true_count: float,
        hilo_slope: float = 0.005
    ) -> dict:
        """
        Compare exact advantage to Hi-Lo linear approximation.
        
        Args:
            remaining_by_rank: Shoe composition.
            total_remaining: Cards remaining.
            hilo_true_count: True count from Hi-Lo system.
            hilo_slope: Slope used in linear model (default 0.5% per TC).
            
        Returns:
            Dict with exact_adv, hilo_adv, error, and percent_error.
        """
        exact_adv = self.estimate_advantage(remaining_by_rank, total_remaining)
        hilo_adv = (hilo_true_count * hilo_slope) - self._baseline_edge
        error = hilo_adv - exact_adv
        
        return {
            "exact_adv": exact_adv,
            "hilo_adv": hilo_adv,
            "error": error,
            "abs_error": abs(error),
            "percent_error": abs(error / exact_adv) * 100 if exact_adv != 0 else 0
        }


__all__ = ['EVEstimator', 'AdvantageModel', 'EffectOfRemoval', 'ExactCountEstimator']
