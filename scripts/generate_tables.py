"""
Script: Strategy Table Generator
Generates baseline strategy tables in JSON format.
"""

import json
from pathlib import Path
from typing import Dict


def generate_s17_das_strategy() -> Dict[str, str]:
    """
    Generate complete S17 DAS (Dealer Stands on Soft 17, Double After Split) 
    baseline strategy table.
    """
    tables = {}
    
    # Hard totals (5-21) vs dealer (2-11)
    hard_strategy = {
        # Total: {dealer: action}
        5: {2: 'HIT', 3: 'HIT', 4: 'HIT', 5: 'HIT', 6: 'HIT', 7: 'HIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        6: {2: 'HIT', 3: 'HIT', 4: 'HIT', 5: 'HIT', 6: 'HIT', 7: 'HIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        7: {2: 'HIT', 3: 'HIT', 4: 'HIT', 5: 'HIT', 6: 'HIT', 7: 'HIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        8: {2: 'HIT', 3: 'HIT', 4: 'HIT', 5: 'HIT', 6: 'HIT', 7: 'HIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        9: {2: 'HIT', 3: 'DOUBLE', 4: 'DOUBLE', 5: 'DOUBLE', 6: 'DOUBLE', 7: 'HIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        10: {2: 'DOUBLE', 3: 'DOUBLE', 4: 'DOUBLE', 5: 'DOUBLE', 6: 'DOUBLE', 7: 'DOUBLE', 8: 'DOUBLE', 9: 'DOUBLE', 10: 'HIT', 11: 'HIT'},
        11: {2: 'DOUBLE', 3: 'DOUBLE', 4: 'DOUBLE', 5: 'DOUBLE', 6: 'DOUBLE', 7: 'DOUBLE', 8: 'DOUBLE', 9: 'DOUBLE', 10: 'DOUBLE', 11: 'DOUBLE'},
        12: {2: 'HIT', 3: 'HIT', 4: 'STAND', 5: 'STAND', 6: 'STAND', 7: 'HIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        13: {2: 'STAND', 3: 'STAND', 4: 'STAND', 5: 'STAND', 6: 'STAND', 7: 'HIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        14: {2: 'STAND', 3: 'STAND', 4: 'STAND', 5: 'STAND', 6: 'STAND', 7: 'HIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        15: {2: 'STAND', 3: 'STAND', 4: 'STAND', 5: 'STAND', 6: 'STAND', 7: 'HIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        16: {2: 'STAND', 3: 'STAND', 4: 'STAND', 5: 'STAND', 6: 'STAND', 7: 'HIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        17: {2: 'STAND', 3: 'STAND', 4: 'STAND', 5: 'STAND', 6: 'STAND', 7: 'STAND', 8: 'STAND', 9: 'STAND', 10: 'STAND', 11: 'STAND'},
        18: {2: 'STAND', 3: 'STAND', 4: 'STAND', 5: 'STAND', 6: 'STAND', 7: 'STAND', 8: 'STAND', 9: 'STAND', 10: 'STAND', 11: 'STAND'},
        19: {2: 'STAND', 3: 'STAND', 4: 'STAND', 5: 'STAND', 6: 'STAND', 7: 'STAND', 8: 'STAND', 9: 'STAND', 10: 'STAND', 11: 'STAND'},
        20: {2: 'STAND', 3: 'STAND', 4: 'STAND', 5: 'STAND', 6: 'STAND', 7: 'STAND', 8: 'STAND', 9: 'STAND', 10: 'STAND', 11: 'STAND'},
        21: {2: 'STAND', 3: 'STAND', 4: 'STAND', 5: 'STAND', 6: 'STAND', 7: 'STAND', 8: 'STAND', 9: 'STAND', 10: 'STAND', 11: 'STAND'},
    }
    
    for total, actions in hard_strategy.items():
        for dealer, action in actions.items():
            tables[f"H_{total}:{dealer:02d}"] = action
    
    # Soft totals (13-21) vs dealer (2-11)
    soft_strategy = {
        13: {2: 'HIT', 3: 'HIT', 4: 'HIT', 5: 'DOUBLE', 6: 'DOUBLE', 7: 'HIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        14: {2: 'HIT', 3: 'HIT', 4: 'HIT', 5: 'DOUBLE', 6: 'DOUBLE', 7: 'HIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        15: {2: 'HIT', 3: 'HIT', 4: 'DOUBLE', 5: 'DOUBLE', 6: 'DOUBLE', 7: 'HIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        16: {2: 'HIT', 3: 'HIT', 4: 'DOUBLE', 5: 'DOUBLE', 6: 'DOUBLE', 7: 'HIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        17: {2: 'HIT', 3: 'DOUBLE', 4: 'DOUBLE', 5: 'DOUBLE', 6: 'DOUBLE', 7: 'HIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        18: {2: 'DOUBLE', 3: 'DOUBLE', 4: 'DOUBLE', 5: 'DOUBLE', 6: 'DOUBLE', 7: 'STAND', 8: 'STAND', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        19: {2: 'STAND', 3: 'STAND', 4: 'STAND', 5: 'STAND', 6: 'DOUBLE', 7: 'STAND', 8: 'STAND', 9: 'STAND', 10: 'STAND', 11: 'STAND'},
        20: {2: 'STAND', 3: 'STAND', 4: 'STAND', 5: 'STAND', 6: 'STAND', 7: 'STAND', 8: 'STAND', 9: 'STAND', 10: 'STAND', 11: 'STAND'},
        21: {2: 'STAND', 3: 'STAND', 4: 'STAND', 5: 'STAND', 6: 'STAND', 7: 'STAND', 8: 'STAND', 9: 'STAND', 10: 'STAND', 11: 'STAND'},
    }
    
    for total, actions in soft_strategy.items():
        for dealer, action in actions.items():
            tables[f"S_{total}:{dealer:02d}"] = action
    
    # Pairs (2-11 where 11=A) vs dealer (2-11)
    pair_strategy = {
        2: {2: 'SPLIT', 3: 'SPLIT', 4: 'SPLIT', 5: 'SPLIT', 6: 'SPLIT', 7: 'SPLIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        3: {2: 'SPLIT', 3: 'SPLIT', 4: 'SPLIT', 5: 'SPLIT', 6: 'SPLIT', 7: 'SPLIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        4: {2: 'HIT', 3: 'HIT', 4: 'HIT', 5: 'SPLIT', 6: 'SPLIT', 7: 'HIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        5: {2: 'DOUBLE', 3: 'DOUBLE', 4: 'DOUBLE', 5: 'DOUBLE', 6: 'DOUBLE', 7: 'DOUBLE', 8: 'DOUBLE', 9: 'DOUBLE', 10: 'HIT', 11: 'HIT'},
        6: {2: 'SPLIT', 3: 'SPLIT', 4: 'SPLIT', 5: 'SPLIT', 6: 'SPLIT', 7: 'HIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        7: {2: 'SPLIT', 3: 'SPLIT', 4: 'SPLIT', 5: 'SPLIT', 6: 'SPLIT', 7: 'SPLIT', 8: 'HIT', 9: 'HIT', 10: 'HIT', 11: 'HIT'},
        8: {2: 'SPLIT', 3: 'SPLIT', 4: 'SPLIT', 5: 'SPLIT', 6: 'SPLIT', 7: 'SPLIT', 8: 'SPLIT', 9: 'SPLIT', 10: 'SPLIT', 11: 'SPLIT'},
        9: {2: 'SPLIT', 3: 'SPLIT', 4: 'SPLIT', 5: 'SPLIT', 6: 'SPLIT', 7: 'STAND', 8: 'SPLIT', 9: 'SPLIT', 10: 'STAND', 11: 'STAND'},
        10: {2: 'STAND', 3: 'STAND', 4: 'STAND', 5: 'STAND', 6: 'STAND', 7: 'STAND', 8: 'STAND', 9: 'STAND', 10: 'STAND', 11: 'STAND'},
        11: {2: 'SPLIT', 3: 'SPLIT', 4: 'SPLIT', 5: 'SPLIT', 6: 'SPLIT', 7: 'SPLIT', 8: 'SPLIT', 9: 'SPLIT', 10: 'SPLIT', 11: 'SPLIT'},  # Aces
    }
    
    for pair_val, actions in pair_strategy.items():
        for dealer, action in actions.items():
            tables[f"P_{pair_val:02d}:{dealer:02d}"] = action
    
    return tables


def main():
    """Generate and save strategy tables."""
    output_dir = Path(__file__).parent.parent / 'data' / 'strategies'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate S17 DAS strategy
    tables = generate_s17_das_strategy()
    
    output = {
        "metadata": {
            "rules": "S17_DAS_6D",
            "description": "6-deck, Dealer Stands on Soft 17, Double After Split allowed",
            "version": "1.0"
        },
        "tables": tables
    }
    
    output_file = output_dir / 's17_das.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Generated strategy table: {output_file}")
    print(f"Total entries: {len(tables)}")


if __name__ == '__main__':
    main()
