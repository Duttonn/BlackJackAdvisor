"""
Configuration Loader Module.
Handles loading and injection of game rule configurations.

Responsibility: Load and validate rule configurations from JSON files.
Provides dependency injection for rule-dependent components.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class GameRules:
    """
    Complete game rules configuration.
    Loaded from JSON files in data/rules/.
    """
    # Rule identification
    name: str = "Standard"
    rule_set_id: str = "s17_das_6d"
    
    # Deck configuration
    num_decks: int = 6
    cards_per_deck: int = 52
    penetration: float = 0.75
    
    @property
    def total_cards(self) -> int:
        """Total cards in the shoe."""
        return self.num_decks * self.cards_per_deck

    @property
    def cut_card_position(self) -> int:
        """Number of cards dealt before shuffle."""
        return int(self.total_cards * self.penetration)
    
    # Dealer rules
    dealer_stands_soft_17: bool = True  # S17 vs H17
    dealer_peeks_for_blackjack: bool = True
    
    # Player options
    double_after_split: bool = True  # DAS
    resplit_aces: bool = False
    hit_split_aces: bool = False
    max_splits: int = 3  # Maximum number of times a hand can be split
    
    # Surrender rules
    surrender_allowed: bool = True
    early_surrender: bool = False  # False = Late Surrender
    
    # Doubling restrictions
    double_any_two: bool = True
    double_9_10_11_only: bool = False
    double_10_11_only: bool = False
    
    # Blackjack payouts
    blackjack_pays: float = 1.5  # 3:2 = 1.5, 6:5 = 1.2
    
    # Table limits
    table_min: float = 10.0
    table_max: float = 1000.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert rules to dictionary."""
        return {
            'name': self.name,
            'rule_set_id': self.rule_set_id,
            'num_decks': self.num_decks,
            'cards_per_deck': self.cards_per_deck,
            'penetration': self.penetration,
            'dealer_stands_soft_17': self.dealer_stands_soft_17,
            'dealer_peeks_for_blackjack': self.dealer_peeks_for_blackjack,
            'double_after_split': self.double_after_split,
            'resplit_aces': self.resplit_aces,
            'hit_split_aces': self.hit_split_aces,
            'max_splits': self.max_splits,
            'surrender_allowed': self.surrender_allowed,
            'early_surrender': self.early_surrender,
            'double_any_two': self.double_any_two,
            'double_9_10_11_only': self.double_9_10_11_only,
            'double_10_11_only': self.double_10_11_only,
            'blackjack_pays': self.blackjack_pays,
            'table_min': self.table_min,
            'table_max': self.table_max
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameRules':
        """Create GameRules from dictionary."""
        return cls(
            name=data.get('name', 'Standard'),
            rule_set_id=data.get('rule_set_id', 's17_das_6d'),
            num_decks=data.get('num_decks', 6),
            cards_per_deck=data.get('cards_per_deck', 52),
            penetration=data.get('penetration', 0.75),
            dealer_stands_soft_17=data.get('dealer_stands_soft_17', True),
            dealer_peeks_for_blackjack=data.get('dealer_peeks_for_blackjack', True),
            double_after_split=data.get('double_after_split', True),
            resplit_aces=data.get('resplit_aces', False),
            hit_split_aces=data.get('hit_split_aces', False),
            max_splits=data.get('max_splits', 3),
            surrender_allowed=data.get('surrender_allowed', True),
            early_surrender=data.get('early_surrender', False),
            double_any_two=data.get('double_any_two', True),
            double_9_10_11_only=data.get('double_9_10_11_only', False),
            double_10_11_only=data.get('double_10_11_only', False),
            blackjack_pays=data.get('blackjack_pays', 1.5),
            table_min=data.get('table_min', 10.0),
            table_max=data.get('table_max', 1000.0)
        )

    @property
    def strategy_file(self) -> str:
        """Returns the strategy file name for this rule set."""
        return self.rule_set_id

    @property
    def house_edge_estimate(self) -> float:
        """
        Estimate the base house edge for these rules.
        This is a rough approximation based on rule effects.
        """
        edge = 0.0
        
        # Base edge for 6-deck game
        edge += 0.006  # ~0.6% base
        
        # Deck count adjustment
        if self.num_decks == 1:
            edge -= 0.002
        elif self.num_decks == 2:
            edge -= 0.001
        elif self.num_decks == 8:
            edge += 0.001
        
        # Dealer rules
        if not self.dealer_stands_soft_17:  # H17
            edge += 0.002
        
        # Double restrictions
        if self.double_10_11_only:
            edge += 0.002
        elif self.double_9_10_11_only:
            edge += 0.001
        
        # DAS
        if not self.double_after_split:
            edge += 0.001
        
        # Surrender
        if not self.surrender_allowed:
            edge += 0.001
        
        # Blackjack payout
        if self.blackjack_pays < 1.5:
            edge += 0.014  # 6:5 penalty
        
        return edge

    def __repr__(self) -> str:
        s17 = "S17" if self.dealer_stands_soft_17 else "H17"
        das = "DAS" if self.double_after_split else "NDAS"
        sur = "LS" if self.surrender_allowed else "NS"
        bj = "3:2" if self.blackjack_pays == 1.5 else f"{self.blackjack_pays}"
        return f"GameRules({s17}, {das}, {sur}, {self.num_decks}D, BJ={bj})"


class ConfigLoader:
    """
    Loads rule configurations from JSON files.
    Provides caching and validation.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the configuration loader.
        
        Args:
            data_dir: Path to data directory. Defaults to project data/ folder.
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / 'data'
        self._data_dir = Path(data_dir)
        self._cache: Dict[str, GameRules] = {}

    def load_rules(self, rule_set: str) -> GameRules:
        """
        Load a rule set from JSON file.
        
        Args:
            rule_set: Name of the rule set (e.g., 'vegas_strip', 'downtown').
            
        Returns:
            Loaded GameRules object.
        """
        if rule_set in self._cache:
            return self._cache[rule_set]
        
        file_path = self._data_dir / 'rules' / f'{rule_set}.json'
        
        if not file_path.exists():
            # Return default rules if file not found, but cache it
            default_rules = GameRules(name=rule_set, rule_set_id=rule_set)
            self._cache[rule_set] = default_rules
            return default_rules
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        rules = GameRules.from_dict(data)
        self._cache[rule_set] = rules
        return rules

    def save_rules(self, rules: GameRules, filename: Optional[str] = None) -> Path:
        """
        Save rules to a JSON file.
        
        Args:
            rules: GameRules to save.
            filename: Output filename (without .json). Uses rule_set_id if not provided.
            
        Returns:
            Path to the saved file.
        """
        filename = filename or rules.rule_set_id
        file_path = self._data_dir / 'rules' / f'{filename}.json'
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(rules.to_dict(), f, indent=2)
        
        return file_path

    def list_available_rules(self) -> List[str]:
        """List all available rule set files."""
        rules_dir = self._data_dir / 'rules'
        if not rules_dir.exists():
            return []
        return [f.stem for f in rules_dir.glob('*.json')]

    def clear_cache(self) -> None:
        """Clear the rules cache."""
        self._cache.clear()


# Predefined rule sets
VEGAS_STRIP = GameRules(
    name="Vegas Strip",
    rule_set_id="vegas_strip",
    num_decks=6,
    dealer_stands_soft_17=True,
    double_after_split=True,
    surrender_allowed=True,
    blackjack_pays=1.5
)

VEGAS_DOWNTOWN = GameRules(
    name="Vegas Downtown",
    rule_set_id="vegas_downtown",
    num_decks=2,
    dealer_stands_soft_17=False,  # H17
    double_after_split=True,
    surrender_allowed=False,
    blackjack_pays=1.5
)

ATLANTIC_CITY = GameRules(
    name="Atlantic City",
    rule_set_id="atlantic_city",
    num_decks=8,
    dealer_stands_soft_17=True,
    double_after_split=True,
    surrender_allowed=True,
    blackjack_pays=1.5
)


__all__ = [
    'GameRules',
    'ConfigLoader',
    'VEGAS_STRIP',
    'VEGAS_DOWNTOWN',
    'ATLANTIC_CITY'
]
