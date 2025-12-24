"""
Strategy Lookup Module.
Efficient O(1) table reader for baseline strategy lookups.

Responsibility: Load and query strategy tables from JSON data files.
FORBIDDEN: EV calculation, random number generation, bankroll access.
"""

import json
from pathlib import Path
from typing import Dict, Optional, Any

from ..core import Action, Hand, Card, HandType


class DataLoader:
    """
    Loads and caches strategy data from JSON files.
    Provides O(1) hash-based lookups for strategy decisions.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the data loader.
        
        Args:
            data_dir: Path to the data directory. Defaults to project data/ folder.
        """
        if data_dir is None:
            # Default to project data directory
            data_dir = Path(__file__).parent.parent.parent / 'data'
        self._data_dir = Path(data_dir)
        self._strategy_cache: Dict[str, Dict[str, Any]] = {}
        self._deviation_cache: Dict[str, list] = {}

    def load_strategy(self, rule_set: str) -> Dict[str, str]:
        """
        Load a baseline strategy table for a specific rule set.
        
        Args:
            rule_set: Rule set identifier (e.g., 's17_das')
            
        Returns:
            Dictionary mapping lookup keys to action strings.
        """
        if rule_set in self._strategy_cache:
            return self._strategy_cache[rule_set]['tables']

        file_path = self._data_dir / 'strategies' / f'{rule_set}.json'
        
        if not file_path.exists():
            raise FileNotFoundError(f"Strategy file not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self._strategy_cache[rule_set] = data
        return data['tables']

    def load_deviations(self, deviation_set: str = 'standard') -> list:
        """
        Load deviation rules (Illustrious 18, Fab 4, etc.)
        
        Args:
            deviation_set: Name of the deviation set to load.
            
        Returns:
            List of deviation rule dictionaries.
        """
        if deviation_set in self._deviation_cache:
            return self._deviation_cache[deviation_set]

        file_path = self._data_dir / 'deviations' / f'{deviation_set}.json'
        
        if not file_path.exists():
            raise FileNotFoundError(f"Deviation file not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self._deviation_cache[deviation_set] = data
        return data

    def get_metadata(self, rule_set: str) -> Dict[str, Any]:
        """Get metadata for a loaded strategy."""
        if rule_set not in self._strategy_cache:
            self.load_strategy(rule_set)
        return self._strategy_cache[rule_set].get('metadata', {})

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._strategy_cache.clear()
        self._deviation_cache.clear()


class StrategyLookup:
    """
    Provides O(1) strategy lookups from loaded tables.
    Translates Hand + Dealer card to Actions.
    """

    def __init__(self, strategy_table: Dict[str, str]):
        """
        Initialize with a loaded strategy table.
        
        Args:
            strategy_table: Dictionary mapping keys to action strings.
        """
        self._table = strategy_table
        self._action_map = {
            'STAND': Action.STAND,
            'HIT': Action.HIT,
            'DOUBLE': Action.DOUBLE,
            'SPLIT': Action.SPLIT,
            'SURRENDER': Action.SURRENDER,
            'Ds': Action.DOUBLE,  # Double if allowed, else Stand
            'Dh': Action.DOUBLE,  # Double if allowed, else Hit
            'Rh': Action.SURRENDER,  # Surrender if allowed, else Hit
            'Rs': Action.SURRENDER,  # Surrender if allowed, else Stand
            'Rp': Action.SURRENDER,  # Surrender if allowed, else Split
            'Ph': Action.SPLIT,  # Split if DAS, else Hit
            'Pd': Action.SPLIT,  # Split if DAS, else Double
        }

    def lookup(self, hand: Hand, dealer_up: Card) -> Optional[Action]:
        """
        Look up the baseline strategy action for a hand vs dealer.
        
        Args:
            hand: The player's hand.
            dealer_up: The dealer's up card.
            
        Returns:
            The recommended Action, or None if not found.
        """
        key = self._generate_key(hand, dealer_up)
        action_str = self._table.get(key)
        
        if action_str is None:
            # Try alternative key formats
            alt_key = self._generate_alt_key(hand, dealer_up)
            action_str = self._table.get(alt_key)
        
        if action_str is None:
            return None
            
        return self._action_map.get(action_str.upper(), None)

    def _generate_key(self, hand: Hand, dealer_up: Card) -> str:
        """
        Generate the primary lookup key.
        Format: "{HandType}_{Value}:{DealerUp:02d}"
        
        Note: Dealer value is zero-padded, hand value is NOT (matches JSON format).
        Pairs use zero-padded values like P_08:10.
        """
        hand_type = hand.hand_type.value
        dealer_value = dealer_up.value if not dealer_up.is_ace else 11
        
        if hand.is_pair:
            # For pairs, use zero-padded pair value to match "P_08:10" format
            value = hand.pair_value
            return f"{hand_type}_{value:02d}:{dealer_value:02d}"
        else:
            # For hard/soft totals, don't zero-pad to match "H_5:02" format
            value = hand.total
            return f"{hand_type}_{value}:{dealer_value:02d}"

    def _generate_alt_key(self, hand: Hand, dealer_up: Card) -> str:
        """
        Generate alternative key format for compatibility.
        Format without zero-padding: "{HandType}_{Value}:{DealerUp}"
        """
        hand_type = hand.hand_type.value
        dealer_value = dealer_up.value if not dealer_up.is_ace else 11
        
        if hand.is_pair:
            value = hand.pair_value
        else:
            value = hand.total
            
        return f"{hand_type}_{value}:{dealer_value}"

    def has_key(self, key: str) -> bool:
        """Check if a key exists in the table."""
        return key in self._table


__all__ = ['DataLoader', 'StrategyLookup']
