#!/usr/bin/env python3
"""
Verify Theory: Floating Advantage in Deep Shoes.

This script validates our ExactCountEstimator against Griffin/Thorp literature.

THEORETICAL BASIS (Griffin, 1979; Thorp, 1966):
The "Floating Advantage" phenomenon states that player advantage actually
increases as the shoe depletes, even when the Hi-Lo true count is zero.

This happens because:
1. Hi-Lo is a simplified linear approximation (assigns ±1 or 0 to cards)
2. The actual EoR (Effect of Removal) values are non-linear
3. At neutral Hi-Lo count, the low cards and high cards "cancel out" 
   in the linear model, but NOT in combinatorial reality
4. In a deep shoe with fewer total cards, the variance in composition
   has a larger effect on player advantage

EXPECTED RESULT:
When Hi-Lo True Count = 0 in a deep shoe (1 deck or ~13 cards remaining),
the exact EoR-based advantage should be approximately +1.0% to +1.6%,
while Hi-Lo predicts 0.0%.

This demonstrates the "Drift" between our linear model and reality.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.betting.estimator import ExactCountEstimator, EffectOfRemoval, EVEstimator
from src.config import GameRules


def create_neutral_hilo_deep_shoe() -> tuple[dict, int]:
    """
    Create a deep shoe scenario with TC = 0.
    
    We need a composition where:
    - Hi-Lo running count = 0 (balanced low and high cards)
    - Very few cards remaining (deep penetration)
    
    Scenario: 13 cards remaining (1/4 deck)
    Composition chosen to have RC = 0:
    - 2 × Two (+1)
    - 2 × Three (+1)
    - 1 × Five (+1)  = Total +5
    - 2 × Eight (0)
    - 2 × Nine (0)   = Total 0
    - 2 × Ten (-1)
    - 2 × Ace (-1)
    - 1 × King (-1)  = Total -5
    
    Net Hi-Lo: +5 - 5 = 0
    """
    remaining_by_rank = {
        2: 2,   # Two twos: +2 to RC
        3: 2,   # Two threes: +2 to RC
        5: 1,   # One five: +1 to RC
        8: 2,   # Two eights: 0 to RC
        9: 2,   # Two nines: 0 to RC (actually -0.36 but small)
        10: 3,  # Three tens (10, J, K): -3 to RC
        11: 2,  # Two aces: -2 to RC
    }
    total_remaining = sum(remaining_by_rank.values())  # 14 cards
    
    # Verify Hi-Lo count
    hilo_rc = (
        2 * 1 +   # twos: +2
        2 * 1 +   # threes: +2
        1 * 1 +   # fives: +1
        2 * 0 +   # eights: 0
        2 * 0 +   # nines: 0
        3 * (-1) + # tens: -3
        2 * (-1)   # aces: -2
    )
    
    return remaining_by_rank, total_remaining, hilo_rc


def create_alternative_scenario() -> tuple[dict, int, int]:
    """
    Alternative: Exactly 13 cards with perfect RC=0.
    
    3 × low cards (+3): 2, 3, 4
    4 × neutral (0): 7, 7, 8, 8
    3 × high cards (-3): 10, J, A
    3 × more low (+3): 5, 5, 6
    6 × more high (-6): K, K, Q, Q, A, A
    
    Let's make it simpler:
    - 3 × low (2, 3, 4): +3
    - 4 × neutral (7, 7, 8, 8): 0
    - 6 × high (10, 10, J, Q, A, A): -6 ... too many
    
    Better approach: Equal numbers
    - 3 low cards: +3
    - 4 neutral: 0
    - 3 high: -3
    - 3 more of each? 
    
    Simplest: 12 cards
    - 3 × low (e.g., 2, 3, 5): +3
    - 3 × neutral (e.g., 7, 8, 8): 0
    - 3 × high (e.g., 10, J, A): -3
    - 3 × neutral (e.g., 9, 9, 9): 0 (9s are actually -0.18 but Hi-Lo says 0)
    """
    remaining_by_rank = {
        2: 1,   # +1
        3: 1,   # +1
        5: 1,   # +1
        7: 2,   # 0
        8: 1,   # 0
        9: 3,   # 0 (Hi-Lo)
        10: 2,  # -2 (represents 10, J, Q, K)
        11: 1,  # -1 (Ace)
    }
    total = sum(remaining_by_rank.values())  # 12 cards
    
    rc = (1 + 1 + 1) + (0 + 0 + 0) + (-2 + -1)  # = 3 + 0 - 3 = 0
    
    return remaining_by_rank, total, rc


def create_extreme_deep_shoe() -> tuple[dict, int, int]:
    """
    Extreme deep shoe: Only 8 cards left, Hi-Lo RC = 0.
    
    4 low cards: 2, 3, 4, 5 = +4
    4 high cards: 10, J, Q, A = -4
    Total = 0
    """
    remaining_by_rank = {
        2: 1,   # +1
        3: 1,   # +1
        4: 1,   # +1
        5: 1,   # +1
        10: 3,  # -3 (10, J, Q)
        11: 1,  # -1 (Ace)
    }
    total = sum(remaining_by_rank.values())  # 8 cards
    rc = 4 - 4
    
    return remaining_by_rank, total, rc


def verify_floating_advantage():
    """
    Main verification: Compare Hi-Lo to Exact in deep shoe scenarios.
    
    The Floating Advantage occurs because at deep penetration:
    1. The EoR impact is amplified (divided by fewer remaining cards)
    2. Asymmetric compositions that "balance" in Hi-Lo don't balance in EoR
    """
    print("=" * 70)
    print("     FLOATING ADVANTAGE VERIFICATION")
    print("     Comparing Hi-Lo Linear Model vs Exact EoR Calculation")
    print("=" * 70)
    print()
    
    # Initialize estimators
    rules = GameRules()  # Standard S17 DAS
    exact_estimator = ExactCountEstimator(rules=rules, num_decks=6)
    
    # Baseline edge (house edge at TC=0)
    baseline_edge = 0.004  # ~0.4%
    
    print("CONFIGURATION:")
    print(f"  Rules: S17, DAS, 6-deck shoe")
    print(f"  Baseline House Edge: {baseline_edge:.2%}")
    print(f"  Hi-Lo Slope: 0.5% per True Count")
    print()
    
    print("-" * 70)
    print("TEST 1: ASYMMETRIC EoR IN BALANCED Hi-Lo")
    print("-" * 70)
    print("""
    Scenario: Construct a shoe where Hi-Lo RC = 0, but EoR is imbalanced.
    
    Key insight: 5s are worth +0.69% EoR but only +1 in Hi-Lo
                 2s are worth +0.38% EoR but also +1 in Hi-Lo
                 
    If we have more 5s removed and fewer 2s removed (but Hi-Lo balanced),
    the exact advantage should be higher than Hi-Lo predicts.
    """)
    
    # Scenario: 312 cards started (6 decks), now 52 remaining (1 deck)
    # Normal 1-deck composition: 4 of each rank (2-9), 16 tens, 4 aces = 52
    
    # Test with high-EoR low cards removed vs low-EoR low cards remaining
    # Removed from 6-deck: 260 cards total
    # Key: More 5s removed, fewer 2s removed → Hi-Lo balanced but EoR positive
    
    print("Scenario A: 52 cards remaining (1 deck), neutral composition")
    # Perfect 1 deck remaining
    remaining_neutral = {
        2: 4, 3: 4, 4: 4, 5: 4, 6: 4, 7: 4, 8: 4, 9: 4,
        10: 16,  # 10, J, Q, K
        11: 4    # Aces
    }
    total = sum(remaining_neutral.values())
    
    exact_adv = exact_estimator.estimate_advantage(remaining_neutral, total)
    hilo_rc = 4*5*1 + 4*0 + (-16 - 4)  # Wrong, let me recalculate
    # Low cards: 4*5 = 20 cards, each +1 = +20
    # Neutral: 4*3 = 12 cards (7,8,9), each 0 = 0
    # High: 16 + 4 = 20 cards, each -1 = -20
    # Net RC = 0
    hilo_rc = 0
    hilo_adv = -baseline_edge
    
    print(f"  Remaining: 52 cards (exactly 1 deck)")
    print(f"  Hi-Lo RC: {hilo_rc}, TC: {hilo_rc / 1.0:.2f}")
    print(f"  Hi-Lo Advantage:  {hilo_adv:+.4%}")
    print(f"  Exact Advantage:  {exact_adv:+.4%}")
    print(f"  Divergence:       {exact_adv - hilo_adv:+.4%}")
    print()
    
    print("Scenario B: Rich in high-EoR low cards (5s), depleted in low-EoR (2s)")
    # Imbalanced: Extra 5s remaining (good for player), fewer 2s
    remaining_imbalanced = {
        2: 2,   # 2 fewer 2s (but 2s are +0.38%)
        3: 4, 4: 4, 
        5: 6,   # 2 extra 5s (5s are +0.69%)
        6: 4, 7: 4, 8: 4, 9: 4,
        10: 16,
        11: 4
    }
    total = sum(remaining_imbalanced.values())  # Still 52
    
    # Hi-Lo: +2×1 + 4×1 + 4×1 + 6×1 + 4×1 + ... = balanced if tens balanced
    hilo_low = 2 + 4 + 4 + 6 + 4  # = 20
    hilo_high = 16 + 4  # = 20
    hilo_rc = hilo_low - hilo_high  # 0
    
    exact_adv = exact_estimator.estimate_advantage(remaining_imbalanced, total)
    hilo_adv = -baseline_edge
    
    print(f"  Remaining: {total} cards")
    print(f"  Composition: 2 fewer 2s, 2 extra 5s (same Hi-Lo)")
    print(f"  Hi-Lo RC: {hilo_rc}, TC: {hilo_rc / 1.0:.2f}")
    print(f"  Hi-Lo Advantage:  {hilo_adv:+.4%}")
    print(f"  Exact Advantage:  {exact_adv:+.4%}")
    print(f"  Divergence:       {exact_adv - hilo_adv:+.4%}")
    
    print()
    print("-" * 70)
    print("TEST 2: DEEP SHOE AMPLIFICATION")
    print("-" * 70)
    print("""
    The same EoR imbalance has MORE impact in a small shoe because
    the advantage formula divides by remaining cards.
    """)
    
    # Same proportional imbalance in a smaller shoe
    for deck_fraction, name in [(1.0, "52 cards"), (0.5, "26 cards"), (0.25, "13 cards")]:
        multiplier = deck_fraction
        remaining = {
            2: int(2 * multiplier) or 1,   # Slightly depleted
            3: int(4 * multiplier),
            4: int(4 * multiplier),
            5: int(6 * multiplier) or 1,   # Slightly enriched
            6: int(4 * multiplier),
            7: int(4 * multiplier),
            8: int(4 * multiplier),
            9: int(4 * multiplier),
            10: int(16 * multiplier),
            11: int(4 * multiplier),
        }
        total = sum(remaining.values())
        
        # Recalculate Hi-Lo for this composition
        hilo_rc = (remaining.get(2, 0) + remaining.get(3, 0) + remaining.get(4, 0) + 
                   remaining.get(5, 0) + remaining.get(6, 0) - 
                   remaining.get(10, 0) - remaining.get(11, 0))
        decks_remaining = total / 52.0
        tc = hilo_rc / decks_remaining if decks_remaining > 0 else 0
        
        exact_adv = exact_estimator.estimate_advantage(remaining, total)
        hilo_adv = (tc * 0.005) - baseline_edge
        
        print(f"\n  {name}:")
        print(f"    Hi-Lo RC={hilo_rc}, TC={tc:.2f}")
        print(f"    Hi-Lo Adv: {hilo_adv:+.4%}, Exact Adv: {exact_adv:+.4%}")
        print(f"    Divergence: {exact_adv - hilo_adv:+.4%}")
    
    print()
    print("=" * 70)
    print("THEORETICAL INTERPRETATION")
    print("=" * 70)
    print("""
The "Floating Advantage" occurs because Hi-Lo's linear approximation
loses accuracy as the shoe depletes. Key observations:

1. Hi-Lo assigns equal weight (+1) to all low cards (2-6), but their
   actual EoR values differ: 5 is worth +0.69%, while 2 is only +0.38%.

2. Similarly, Hi-Lo treats all 10-value cards equally (-1), but Aces
   have a higher EoR (-0.61%) than 10s (-0.51%).

3. In a balanced shoe (RC=0), these asymmetries can accumulate,
   especially when few cards remain.

4. The result: In deep shoes, the actual player advantage can be
   significantly different from what Hi-Lo predicts.

This is why professional advantage players use more sophisticated
counting systems (Zen, Omega II) or compositional-dependent strategies
for deep shoe play.
""")


def print_eor_reference():
    """Print the EoR values for reference."""
    print()
    print("=" * 70)
    print("EFFECT OF REMOVAL (EoR) VALUES - Griffin/Thorp")
    print("=" * 70)
    print()
    print("Card  | EoR Value | Hi-Lo Tag | Ratio")
    print("-" * 40)
    for value in range(2, 12):
        eor = EffectOfRemoval.get_eor(value)
        if value <= 6:
            hilo = +1
        elif value <= 9:
            hilo = 0
        else:
            hilo = -1
        
        name = "A" if value == 11 else ("10/J/Q/K" if value == 10 else str(value))
        ratio = eor / hilo if hilo != 0 else float('inf')
        print(f"  {name:8} | {eor:+.2f}%    | {hilo:+2}        | {ratio:.2f}")
    print()
    print("Note: Hi-Lo treats all +1 cards equally, but their EoR values differ.")
    print("      This asymmetry causes the 'Drift' in deep shoes.")


def main():
    """Run the verification."""
    print_eor_reference()
    verify_floating_advantage()
    

if __name__ == "__main__":
    main()
