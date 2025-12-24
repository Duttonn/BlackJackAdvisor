"""
Deviation Logic Module.
Handles Illustrious 18 and Fab 4 count-based strategy deviations.

Responsibility: Determine when True Count triggers deviation from baseline.
FORBIDDEN: EV calculation, random number generation, bankroll access.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

from ..core import Action, Hand, Card, GameState, HandType, DeviationDirection


@dataclass(frozen=True)
class DeviationTrigger:
    """Defines when a deviation applies based on hand/dealer combination."""
    hand_type: HandType
    value: int
    dealer_up: int


@dataclass(frozen=True)
class DeviationRule:
    """Defines the count threshold and resulting action for a deviation."""
    threshold: float
    direction: DeviationDirection
    action: Action


@dataclass(frozen=True)
class Deviation:
    """Complete deviation specification."""
    id: str
    trigger: DeviationTrigger
    rule: DeviationRule
    priority: int = 0  # Higher priority deviations are checked first

    def matches_hand(self, hand: Hand, dealer_up: Card) -> bool:
        """Check if this deviation applies to the given hand situation."""
        dealer_value = dealer_up.value if not dealer_up.is_ace else 11
        
        if dealer_value != self.trigger.dealer_up:
            return False
            
        # Check hand type and value
        if self.trigger.hand_type == HandType.HARD:
            return not hand.is_soft and not hand.is_pair and hand.total == self.trigger.value
        elif self.trigger.hand_type == HandType.SOFT:
            return hand.is_soft and hand.total == self.trigger.value
        elif self.trigger.hand_type == HandType.PAIR:
            return hand.is_pair and hand.pair_value == self.trigger.value
        return False

    def is_triggered(self, true_count: float) -> bool:
        """Check if the true count triggers this deviation."""
        if self.rule.direction == DeviationDirection.ABOVE_OR_EQUAL:
            return true_count >= self.rule.threshold
        else:  # BELOW
            return true_count < self.rule.threshold

    def get_action(self) -> Action:
        """Get the action to take when this deviation triggers."""
        return self.rule.action


class DeviationEngine:
    """
    Manages and applies count-based strategy deviations.
    
    Supports:
    - Illustrious 18 (playing deviations)
    - Fab 4 (surrender deviations)
    - Custom deviation sets
    """

    def __init__(self, deviations: Optional[List[Deviation]] = None):
        """
        Initialize the deviation engine.
        
        Args:
            deviations: List of Deviation objects. Can be loaded later.
        """
        self._deviations: List[Deviation] = deviations or []
        self._index: Dict[str, List[Deviation]] = {}
        self._rebuild_index()

    def load_from_data(self, deviation_data: List[Dict[str, Any]]) -> None:
        """
        Load deviations from parsed JSON data.
        
        Args:
            deviation_data: List of deviation dictionaries from JSON.
        """
        self._deviations.clear()
        
        for i, item in enumerate(deviation_data):
            try:
                deviation = self._parse_deviation(item, i)
                self._deviations.append(deviation)
            except (KeyError, ValueError) as e:
                # Log and skip malformed deviations
                print(f"Warning: Skipping malformed deviation {item.get('id', 'unknown')}: {e}")
        
        self._rebuild_index()

    def _parse_deviation(self, data: Dict[str, Any], index: int) -> Deviation:
        """Parse a deviation from JSON dictionary."""
        trigger_data = data['trigger']
        rule_data = data['rule']
        
        # Parse hand type
        hand_type_map = {
            'HARD': HandType.HARD,
            'SOFT': HandType.SOFT,
            'PAIR': HandType.PAIR
        }
        hand_type = hand_type_map[trigger_data['type'].upper()]
        
        # Parse direction
        direction_map = {
            'ABOVE_OR_EQUAL': DeviationDirection.ABOVE_OR_EQUAL,
            'BELOW': DeviationDirection.BELOW
        }
        direction = direction_map[rule_data['direction'].upper()]
        
        # Parse action
        action_map = {
            'STAND': Action.STAND,
            'HIT': Action.HIT,
            'DOUBLE': Action.DOUBLE,
            'SPLIT': Action.SPLIT,
            'SURRENDER': Action.SURRENDER
        }
        action = action_map[rule_data['action'].upper()]
        
        trigger = DeviationTrigger(
            hand_type=hand_type,
            value=trigger_data['value'],
            dealer_up=trigger_data['dealer']
        )
        
        rule = DeviationRule(
            threshold=float(rule_data['threshold']),
            direction=direction,
            action=action
        )
        
        return Deviation(
            id=data['id'],
            trigger=trigger,
            rule=rule,
            priority=data.get('priority', index)
        )

    def _rebuild_index(self) -> None:
        """Build index for fast deviation lookup."""
        self._index.clear()
        for dev in self._deviations:
            key = f"{dev.trigger.hand_type.value}_{dev.trigger.value}_{dev.trigger.dealer_up}"
            if key not in self._index:
                self._index[key] = []
            self._index[key].append(dev)
        
        # Sort each list by priority (higher first)
        for key in self._index:
            self._index[key].sort(key=lambda d: d.priority, reverse=True)

    def check_deviation(
        self,
        hand: Hand,
        dealer_up: Card,
        metrics: GameState
    ) -> Optional[Action]:
        """
        Check if any deviation applies and return the action if so.
        
        Args:
            hand: The player's hand.
            dealer_up: The dealer's up card.
            metrics: Current game state with true count.
            
        Returns:
            The deviation action if triggered, None otherwise.
        """
        # Build lookup key
        if hand.is_pair:
            hand_type = HandType.PAIR
            value = hand.pair_value
        elif hand.is_soft:
            hand_type = HandType.SOFT
            value = hand.total
        else:
            hand_type = HandType.HARD
            value = hand.total
            
        dealer_value = dealer_up.value if not dealer_up.is_ace else 11
        key = f"{hand_type.value}_{value}_{dealer_value}"
        
        candidates = self._index.get(key, [])
        
        for deviation in candidates:
            if deviation.is_triggered(metrics.true_count):
                return deviation.get_action()
        
        return None

    def check_surrender_deviation(
        self,
        hand: Hand,
        dealer_up: Card,
        metrics: GameState
    ) -> Optional[Action]:
        """
        Check specifically for surrender deviations (Fab 4).
        
        Returns SURRENDER action if a surrender deviation triggers.
        """
        action = self.check_deviation(hand, dealer_up, metrics)
        if action == Action.SURRENDER:
            return action
        return None

    @property
    def deviation_count(self) -> int:
        """Number of loaded deviations."""
        return len(self._deviations)

    def get_deviation_ids(self) -> List[str]:
        """Get list of all loaded deviation IDs."""
        return [d.id for d in self._deviations]


# Standard Illustrious 18 deviations
ILLUSTRIOUS_18 = [
    Deviation("ILL_16v10", DeviationTrigger(HandType.HARD, 16, 10), 
              DeviationRule(0, DeviationDirection.ABOVE_OR_EQUAL, Action.STAND), 1),
    Deviation("ILL_15v10", DeviationTrigger(HandType.HARD, 15, 10),
              DeviationRule(4, DeviationDirection.ABOVE_OR_EQUAL, Action.STAND), 2),
    Deviation("ILL_20vA", DeviationTrigger(HandType.PAIR, 10, 11),
              DeviationRule(6, DeviationDirection.ABOVE_OR_EQUAL, Action.SPLIT), 3),
    Deviation("ILL_10v10", DeviationTrigger(HandType.HARD, 10, 10),
              DeviationRule(4, DeviationDirection.ABOVE_OR_EQUAL, Action.DOUBLE), 4),
    Deviation("ILL_12v3", DeviationTrigger(HandType.HARD, 12, 3),
              DeviationRule(2, DeviationDirection.ABOVE_OR_EQUAL, Action.STAND), 5),
    Deviation("ILL_12v2", DeviationTrigger(HandType.HARD, 12, 2),
              DeviationRule(3, DeviationDirection.ABOVE_OR_EQUAL, Action.STAND), 6),
    Deviation("ILL_11vA", DeviationTrigger(HandType.HARD, 11, 11),
              DeviationRule(1, DeviationDirection.ABOVE_OR_EQUAL, Action.DOUBLE), 7),
    Deviation("ILL_9v2", DeviationTrigger(HandType.HARD, 9, 2),
              DeviationRule(1, DeviationDirection.ABOVE_OR_EQUAL, Action.DOUBLE), 8),
    Deviation("ILL_10vA", DeviationTrigger(HandType.HARD, 10, 11),
              DeviationRule(4, DeviationDirection.ABOVE_OR_EQUAL, Action.DOUBLE), 9),
    Deviation("ILL_9v7", DeviationTrigger(HandType.HARD, 9, 7),
              DeviationRule(3, DeviationDirection.ABOVE_OR_EQUAL, Action.DOUBLE), 10),
    Deviation("ILL_16v9", DeviationTrigger(HandType.HARD, 16, 9),
              DeviationRule(5, DeviationDirection.ABOVE_OR_EQUAL, Action.STAND), 11),
    Deviation("ILL_13v2", DeviationTrigger(HandType.HARD, 13, 2),
              DeviationRule(-1, DeviationDirection.BELOW, Action.HIT), 12),
    Deviation("ILL_12v4", DeviationTrigger(HandType.HARD, 12, 4),
              DeviationRule(0, DeviationDirection.BELOW, Action.HIT), 13),
    Deviation("ILL_12v5", DeviationTrigger(HandType.HARD, 12, 5),
              DeviationRule(-2, DeviationDirection.BELOW, Action.HIT), 14),
    Deviation("ILL_12v6", DeviationTrigger(HandType.HARD, 12, 6),
              DeviationRule(-1, DeviationDirection.BELOW, Action.HIT), 15),
    Deviation("ILL_13v3", DeviationTrigger(HandType.HARD, 13, 3),
              DeviationRule(-2, DeviationDirection.BELOW, Action.HIT), 16),
]

# Fab 4 surrender deviations
FAB_4 = [
    Deviation("FAB_15v10", DeviationTrigger(HandType.HARD, 15, 10),
              DeviationRule(0, DeviationDirection.ABOVE_OR_EQUAL, Action.SURRENDER), 100),
    Deviation("FAB_15vA", DeviationTrigger(HandType.HARD, 15, 11),
              DeviationRule(1, DeviationDirection.ABOVE_OR_EQUAL, Action.SURRENDER), 101),
    Deviation("FAB_14v10", DeviationTrigger(HandType.HARD, 14, 10),
              DeviationRule(3, DeviationDirection.ABOVE_OR_EQUAL, Action.SURRENDER), 102),
    Deviation("FAB_15v9", DeviationTrigger(HandType.HARD, 15, 9),
              DeviationRule(2, DeviationDirection.ABOVE_OR_EQUAL, Action.SURRENDER), 103),
]


def create_standard_deviation_engine() -> DeviationEngine:
    """Create a deviation engine with standard Illustrious 18 + Fab 4."""
    return DeviationEngine(ILLUSTRIOUS_18 + FAB_4)


__all__ = [
    'Deviation',
    'DeviationTrigger', 
    'DeviationRule',
    'DeviationEngine',
    'ILLUSTRIOUS_18',
    'FAB_4',
    'create_standard_deviation_engine'
]
