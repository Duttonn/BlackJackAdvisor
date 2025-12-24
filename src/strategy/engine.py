"""
Strategy Engine Module.
Main decision pipeline for blackjack play decisions.

Responsibility: Route input state to the correct Action.
Invariant: Must always return a valid Action (never None).

FORBIDDEN: EV calculation, random number generation, bankroll access.
Must be purely deterministic f(State) -> Action.
"""

from typing import Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

from ..core import Action, Hand, Card, GameState
from .lookup import DataLoader, StrategyLookup
from .deviations import DeviationEngine, create_standard_deviation_engine


@dataclass
class DecisionResult:
    """
    Result of a strategy decision with counterfactual information.
    
    Allows ablation studies to compare deviation performance vs baseline.
    """
    action: Action              # The action to take
    baseline_action: Action     # What baseline (CDZ) strategy would do
    deviation_id: Optional[str] # ID of deviation that triggered, or None
    true_count: float           # TC at decision time
    
    @property
    def deviated(self) -> bool:
        """True if action differs from baseline."""
        return self.action != self.baseline_action


class RuleConfig:
    """Configuration for game rules affecting strategy."""
    
    def __init__(
        self,
        dealer_stands_soft_17: bool = True,
        double_after_split: bool = True,
        surrender_allowed: bool = True,
        num_decks: int = 6,
        rule_set_name: str = 's17_das',
        deviation_threshold_margin: float = 0.0
    ):
        """
        Initialize rule configuration.
        
        Args:
            dealer_stands_soft_17: True if dealer stands on soft 17 (S17).
            double_after_split: True if doubling after split is allowed (DAS).
            surrender_allowed: True if late surrender is available.
            num_decks: Number of decks in the shoe.
            rule_set_name: Name of the strategy file to load.
            deviation_threshold_margin: Extra TC margin required to trigger deviations.
                                        E.g., if Index is +3 and margin is +1.0,
                                        deviation only fires at TC >= +4.
        """
        self.dealer_stands_soft_17 = dealer_stands_soft_17
        self.double_after_split = double_after_split
        self.surrender_allowed = surrender_allowed
        self.num_decks = num_decks
        self.rule_set_name = rule_set_name
        self.deviation_threshold_margin = deviation_threshold_margin

    @property
    def strategy_file(self) -> str:
        """Returns the strategy file name for this rule set."""
        return self.rule_set_name

    def __repr__(self) -> str:
        s17 = "S17" if self.dealer_stands_soft_17 else "H17"
        das = "DAS" if self.double_after_split else "NDAS"
        sur = "LS" if self.surrender_allowed else "NS"
        return f"RuleConfig({s17}_{das}_{sur}_{self.num_decks}D)"


class StrategyEngine:
    """
    Main decision engine for blackjack strategy.
    
    Routes input state through the decision pipeline:
    1. Check Surrender (Fab 4)
    2. Check Split (if hand.is_pair)
    3. Check Deviations (Ill18) -> if triggers, return Deviation
    4. Return Baseline (CDZ/TDZ lookup)
    
    Invariant: Must always return a valid Action (never None).
    """

    def __init__(
        self,
        rule_config: RuleConfig,
        data_loader: Optional[DataLoader] = None,
        deviation_engine: Optional[DeviationEngine] = None
    ):
        """
        Initialize the strategy engine.
        
        Preloads exact tables for the active rule set.
        
        Args:
            rule_config: Configuration for game rules.
            data_loader: Data loader for strategy files. Created if not provided.
            deviation_engine: Engine for count deviations. Created if not provided.
        """
        self._config = rule_config
        self._data_loader = data_loader or DataLoader()
        self._deviation_engine = deviation_engine or create_standard_deviation_engine()
        
        # Preload strategy tables
        try:
            strategy_table = self._data_loader.load_strategy(rule_config.strategy_file)
            self._lookup = StrategyLookup(strategy_table)
            self._tables_loaded = True
        except FileNotFoundError:
            # Use fallback in-memory tables
            self._lookup = StrategyLookup(self._get_fallback_strategy())
            self._tables_loaded = False

    def decide(
        self,
        hand: Hand,
        dealer_up: Card,
        metrics: GameState,
        use_deviations: bool = True
    ) -> Action:
        """
        Main decision method. Returns the optimal action for the given state.
        
        For counterfactual analysis, use decide_with_context() instead.
        
        Args:
            hand: The player's current hand.
            dealer_up: The dealer's face-up card.
            metrics: Current game state (true count, etc.)
            use_deviations: If False, skip I18/Fab4 and use baseline only.
            
        Returns:
            The recommended Action. Never returns None.
        """
        result = self.decide_with_context(hand, dealer_up, metrics, use_deviations)
        return result.action

    def decide_with_context(
        self,
        hand: Hand,
        dealer_up: Card,
        metrics: GameState,
        use_deviations: bool = True
    ) -> DecisionResult:
        """
        Decision method with full counterfactual context.
        
        Returns both the chosen action AND what baseline strategy would do,
        enabling ablation studies and deviation performance analysis.
        
        Decision Pipeline:
        1. ALWAYS compute Baseline Strategy first
        2. Check Surrender (Fab 4 deviations) - if use_deviations
        3. Check Split (if pair, check for split deviations)
        4. Check Playing Deviations (Ill18) - if use_deviations
        5. Return DecisionResult with both actions
        
        Args:
            hand: The player's current hand.
            dealer_up: The dealer's face-up card.
            metrics: Current game state (true count, etc.)
            use_deviations: If False, skip I18/Fab4 and use baseline only.
            
        Returns:
            DecisionResult with action, baseline_action, and deviation_id.
        """
        true_count = metrics.true_count
        margin = self._config.deviation_threshold_margin
        
        # ALWAYS compute baseline first (for counterfactual logging)
        baseline_action = self._get_baseline_action(hand, dealer_up)
        
        # If deviations disabled, return baseline
        if not use_deviations:
            return DecisionResult(
                action=baseline_action,
                baseline_action=baseline_action,
                deviation_id=None,
                true_count=true_count
            )
        
        # Track which deviation triggered (if any)
        deviation_id: Optional[str] = None
        chosen_action = baseline_action
        
        # Step 1: Check Surrender Deviations (Fab 4)
        if self._config.surrender_allowed and len(hand.cards) == 2:
            surrender_result = self._check_deviation_with_margin(
                hand, dealer_up, metrics, margin, surrender_only=True
            )
            if surrender_result:
                deviation_id, chosen_action = surrender_result
                return DecisionResult(
                    action=chosen_action,
                    baseline_action=baseline_action,
                    deviation_id=deviation_id,
                    true_count=true_count
                )

        # Step 2: Check Split
        if hand.is_pair:
            split_result = self._decide_split_with_context(
                hand, dealer_up, metrics, margin
            )
            if split_result:
                deviation_id, chosen_action = split_result
                if chosen_action == Action.SPLIT:
                    return DecisionResult(
                        action=chosen_action,
                        baseline_action=baseline_action,
                        deviation_id=deviation_id,
                        true_count=true_count
                    )
            # Check if baseline says split
            if baseline_action == Action.SPLIT:
                return DecisionResult(
                    action=Action.SPLIT,
                    baseline_action=baseline_action,
                    deviation_id=None,
                    true_count=true_count
                )

        # Step 3: Check Playing Deviations (Illustrious 18)
        deviation_result = self._check_deviation_with_margin(
            hand, dealer_up, metrics, margin, surrender_only=False
        )
        if deviation_result:
            deviation_id, chosen_action = deviation_result
            if chosen_action != Action.SURRENDER:  # Surrender handled above
                return DecisionResult(
                    action=chosen_action,
                    baseline_action=baseline_action,
                    deviation_id=deviation_id,
                    true_count=true_count
                )
        
        # Step 4: Return baseline
        return DecisionResult(
            action=baseline_action,
            baseline_action=baseline_action,
            deviation_id=None,
            true_count=true_count
        )

    def _get_baseline_action(self, hand: Hand, dealer_up: Card) -> Action:
        """Get the baseline (CDZ) strategy action, ignoring deviations."""
        baseline_action = self._lookup.lookup(hand, dealer_up)
        if baseline_action:
            return self._validate_action(baseline_action, hand)
        return self._calculate_fallback_action(hand, dealer_up)

    def _check_deviation_with_margin(
        self,
        hand: Hand,
        dealer_up: Card,
        metrics: GameState,
        margin: float,
        surrender_only: bool = False
    ) -> Optional[Tuple[str, Action]]:
        """
        Check for deviation with confidence margin applied.
        
        Returns (deviation_id, action) if triggered, None otherwise.
        """
        # Use the deviation engine's internal check with adjusted TC
        # Create adjusted GameState with TC reduced by margin (requiring higher TC to trigger)
        adjusted_metrics = GameState(
            true_count=metrics.true_count - margin,  # Require higher TC
            cards_remaining=metrics.cards_remaining,
            running_count=metrics.running_count,
            decks_remaining=metrics.decks_remaining
        )
        
        if surrender_only:
            action = self._deviation_engine.check_surrender_deviation(
                hand, dealer_up, adjusted_metrics
            )
            if action:
                deviation_id = self._get_triggered_deviation_id(hand, dealer_up, metrics)
                return (deviation_id, action)
        else:
            action = self._deviation_engine.check_deviation(
                hand, dealer_up, adjusted_metrics
            )
            if action and action != Action.SURRENDER:
                deviation_id = self._get_triggered_deviation_id(hand, dealer_up, metrics)
                return (deviation_id, action)
        
        return None

    def _get_triggered_deviation_id(
        self,
        hand: Hand,
        dealer_up: Card,
        metrics: GameState
    ) -> str:
        """Get the ID of the deviation that would trigger for this situation."""
        # This is a simplified lookup - in production, DeviationEngine would expose this
        # For now, construct a descriptive ID
        if hand.is_pair:
            hand_desc = f"P{hand.pair_value}"
        elif hand.is_soft:
            hand_desc = f"S{hand.total}"
        else:
            hand_desc = f"H{hand.total}"
        
        dealer_val = dealer_up.value if not dealer_up.is_ace else 11
        return f"DEV_{hand_desc}v{dealer_val}"

    def _decide_split_with_context(
        self,
        hand: Hand,
        dealer_up: Card,
        metrics: GameState,
        margin: float
    ) -> Optional[Tuple[str, Action]]:
        """Check for split deviation with margin. Returns (dev_id, action) or None."""
        result = self._check_deviation_with_margin(
            hand, dealer_up, metrics, margin, surrender_only=False
        )
        if result and result[1] == Action.SPLIT:
            return result
        return None

    def _decide_split(
        self,
        hand: Hand,
        dealer_up: Card,
        metrics: GameState,
        use_deviations: bool = True
    ) -> Optional[Action]:
        """
        Decide whether to split a pair.
        
        Checks for split deviations first (if enabled), then baseline.
        """
        # Check for split deviation only if deviations enabled
        if use_deviations:
            deviation_action = self._deviation_engine.check_deviation(
                hand, dealer_up, metrics
            )
            if deviation_action == Action.SPLIT:
                return Action.SPLIT

        # Baseline split lookup
        baseline_action = self._lookup.lookup(hand, dealer_up)
        if baseline_action == Action.SPLIT:
            return Action.SPLIT
            
        return None

    def _validate_action(self, action: Action, hand: Hand) -> Action:
        """
        Validate that an action is legal for the current hand.
        
        Handles cases like:
        - Can't double with more than 2 cards
        - Can't split non-pairs
        - Can't surrender after hitting
        """
        if action == Action.DOUBLE and len(hand.cards) > 2:
            return Action.HIT
        if action == Action.SPLIT and not hand.is_pair:
            return Action.HIT
        if action == Action.SURRENDER and len(hand.cards) > 2:
            return Action.HIT
        return action

    def _calculate_fallback_action(self, hand: Hand, dealer_up: Card) -> Action:
        """
        Calculate basic strategy when table lookup fails.
        This is a simplified fallback for essential coverage.
        """
        total = hand.total
        dealer_value = dealer_up.value if not dealer_up.is_ace else 11
        
        # Hard totals fallback
        if not hand.is_soft:
            if total >= 17:
                return Action.STAND
            elif total >= 13 and dealer_value <= 6:
                return Action.STAND
            elif total == 12 and 4 <= dealer_value <= 6:
                return Action.STAND
            elif total == 11:
                return Action.DOUBLE if len(hand.cards) == 2 else Action.HIT
            elif total == 10 and dealer_value <= 9:
                return Action.DOUBLE if len(hand.cards) == 2 else Action.HIT
            elif total == 9 and 3 <= dealer_value <= 6:
                return Action.DOUBLE if len(hand.cards) == 2 else Action.HIT
            else:
                return Action.HIT
        
        # Soft totals fallback
        else:
            if total >= 19:
                return Action.STAND
            elif total == 18:
                if dealer_value >= 9:
                    return Action.HIT
                return Action.STAND
            else:
                return Action.HIT

    def _get_fallback_strategy(self) -> dict:
        """
        Returns a minimal in-memory strategy table.
        Used when JSON files are not available.
        """
        return {
            # Common hard totals
            "H_17:02": "STAND", "H_17:07": "STAND", "H_17:10": "STAND",
            "H_16:02": "STAND", "H_16:07": "HIT", "H_16:10": "HIT",
            "H_15:02": "STAND", "H_15:07": "HIT", "H_15:10": "HIT",
            "H_14:02": "STAND", "H_14:07": "HIT", "H_14:10": "HIT",
            "H_13:02": "STAND", "H_13:07": "HIT", "H_13:10": "HIT",
            "H_12:02": "HIT", "H_12:04": "STAND", "H_12:07": "HIT",
            "H_11:02": "DOUBLE", "H_11:10": "DOUBLE", "H_11:11": "HIT",
            "H_10:02": "DOUBLE", "H_10:10": "HIT", "H_10:11": "HIT",
            "H_9:02": "HIT", "H_9:03": "DOUBLE", "H_9:07": "HIT",
            # Common soft totals
            "S_20:02": "STAND", "S_20:10": "STAND",
            "S_19:02": "STAND", "S_19:06": "DOUBLE", "S_19:10": "STAND",
            "S_18:02": "STAND", "S_18:09": "HIT", "S_18:10": "HIT",
            "S_17:02": "HIT", "S_17:03": "DOUBLE", "S_17:07": "HIT",
            # Common pairs
            "P_11:02": "SPLIT", "P_11:10": "SPLIT",  # Aces
            "P_10:02": "STAND", "P_10:10": "STAND",  # Tens
            "P_08:02": "SPLIT", "P_08:10": "SPLIT",  # Eights
        }

    @property
    def tables_loaded(self) -> bool:
        """Returns True if strategy tables were loaded from files."""
        return self._tables_loaded

    @property
    def config(self) -> RuleConfig:
        """Returns the current rule configuration."""
        return self._config

    def __repr__(self) -> str:
        status = "loaded" if self._tables_loaded else "fallback"
        return f"StrategyEngine({self._config}, tables={status})"


__all__ = ['StrategyEngine', 'RuleConfig', 'DecisionResult']
