#!/usr/bin/env python3
"""
Deep Shoe Model Error Study.

Analyzes the divergence between Hi-Lo linear approximation and
Exact EoR-based advantage calculation at different penetration depths.

Hypothesis: Hi-Lo tracks closely at low penetration but diverges 
significantly (>2x error) at deep penetration (>90%).

Output: test_results/model_error_study_{timestamp}.csv
"""

import sys
import csv
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core import Card, Hand, Action, Rank, Suit
from src.state import StateManager
from src.state.manager import GameRules as StateGameRules  # StateManager's rules
from src.betting import BettingConfig
from src.betting.estimator import EVEstimator, ExactCountEstimator
from src.config import GameRules  # Config rules (for estimators)
import random


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class HandObservation:
    """Single observation point for model comparison."""
    hand_num: int
    penetration: float
    hilo_adv: float
    exact_adv: float
    true_count: float
    cards_remaining: int


@dataclass
class PenetrationBin:
    """Aggregated statistics for a penetration range."""
    bin_name: str
    range_start: float
    range_end: float
    observations: int = 0
    sum_hilo: float = 0.0
    sum_exact: float = 0.0
    sum_abs_error: float = 0.0
    max_divergence: float = 0.0
    
    @property
    def mean_hilo(self) -> float:
        return self.sum_hilo / self.observations if self.observations > 0 else 0.0
    
    @property
    def mean_exact(self) -> float:
        return self.sum_exact / self.observations if self.observations > 0 else 0.0
    
    @property
    def mae(self) -> float:
        """Mean Absolute Error between Hi-Lo and Exact."""
        return self.sum_abs_error / self.observations if self.observations > 0 else 0.0


# =============================================================================
# Simulation Engine (Simplified for Speed)
# =============================================================================

class DeepShoeSimulator:
    """
    Simplified simulator for model error analysis.
    
    Focuses on tracking advantage estimates at different penetration levels,
    not on playing out full hands.
    """

    def __init__(
        self,
        rules: GameRules,
        seed: Optional[int] = None
    ):
        self.rules = rules
        self.rng = random.Random(seed)
        
        # Initialize state tracking (use StateManager's GameRules)
        state_rules = StateGameRules(
            num_decks=rules.num_decks,
            penetration=rules.penetration
        )
        self.state_manager = StateManager(rules=state_rules)
        
        # Initialize estimators
        self.hilo_estimator = EVEstimator(rules=rules)
        self.exact_estimator = ExactCountEstimator(rules=rules, num_decks=rules.num_decks)
        
        # Build shoe
        self._build_shoe()

    def _build_shoe(self) -> None:
        """Build and shuffle a fresh shoe."""
        self.shoe: List[Card] = []
        for _ in range(self.rules.num_decks):
            for suit in Suit:
                for rank in Rank:
                    self.shoe.append(Card(rank, suit))
        self.rng.shuffle(self.shoe)
        self.shoe_index = 0

    def _deal_card(self) -> Card:
        """Deal a single card from shoe."""
        card = self.shoe[self.shoe_index]
        self.shoe_index += 1
        return card

    def _reset_shoe(self) -> None:
        """Shuffle and reset."""
        self.rng.shuffle(self.shoe)
        self.shoe_index = 0
        self.state_manager.reset()

    def run(
        self,
        num_hands: int,
        verbose: bool = True
    ) -> List[HandObservation]:
        """
        Run simulation and collect observations.
        
        Args:
            num_hands: Number of hands to simulate.
            verbose: Print progress.
            
        Returns:
            List of HandObservation for analysis.
        """
        observations: List[HandObservation] = []
        
        if verbose:
            print(f"\n🎰 Running Deep Shoe Study...")
            print(f"   Penetration: {self.rules.penetration:.0%}")
            print(f"   Hands: {num_hands:,}")
        
        for hand_num in range(num_hands):
            # Check if shuffle needed
            cards_dealt = self.shoe_index
            total_cards = len(self.shoe)
            current_penetration = cards_dealt / total_cards
            
            if current_penetration >= self.rules.penetration:
                self._reset_shoe()
                continue
            
            # Deal 4 cards (2 player, 2 dealer) and observe
            cards_to_deal = min(4, total_cards - self.shoe_index)
            if cards_to_deal < 4:
                self._reset_shoe()
                continue
            
            dealt_cards = [self._deal_card() for _ in range(4)]
            
            # Observe cards in state manager
            for card in dealt_cards:
                self.state_manager.observe_card(card)
            
            # Get current state
            metrics = self.state_manager.get_metrics()
            remaining_by_rank = self.state_manager.get_remaining_by_rank()
            penetration = self.state_manager.penetration
            
            # Calculate advantages
            hilo_adv = self.hilo_estimator.estimate_advantage(
                metrics.true_count,
                self.rules.num_decks
            )
            
            exact_adv = self.exact_estimator.estimate_advantage(
                remaining_by_rank,
                metrics.cards_remaining
            )
            
            # Record observation
            obs = HandObservation(
                hand_num=hand_num,
                penetration=penetration,
                hilo_adv=hilo_adv,
                exact_adv=exact_adv,
                true_count=metrics.true_count,
                cards_remaining=metrics.cards_remaining
            )
            observations.append(obs)
            
            # Progress
            if verbose and (hand_num + 1) % 25000 == 0:
                print(f"   Processed {hand_num + 1:,} hands...")
        
        if verbose:
            print(f"   ✓ Collected {len(observations):,} observations")
        
        return observations


# =============================================================================
# Analysis Functions
# =============================================================================

def create_penetration_bins() -> List[PenetrationBin]:
    """Create 10 bins for penetration deciles."""
    bins = []
    for i in range(10):
        start = i * 0.1
        end = (i + 1) * 0.1
        name = f"{int(start*100)}-{int(end*100)}%"
        bins.append(PenetrationBin(bin_name=name, range_start=start, range_end=end))
    return bins


def analyze_observations(
    observations: List[HandObservation],
    bins: List[PenetrationBin]
) -> None:
    """Aggregate observations into penetration bins."""
    for obs in observations:
        for bin in bins:
            if bin.range_start <= obs.penetration < bin.range_end:
                bin.observations += 1
                bin.sum_hilo += obs.hilo_adv
                bin.sum_exact += obs.exact_adv
                abs_error = abs(obs.hilo_adv - obs.exact_adv)
                bin.sum_abs_error += abs_error
                bin.max_divergence = max(bin.max_divergence, abs_error)
                break


def print_results(bins: List[PenetrationBin]) -> None:
    """Print formatted results table."""
    print("\n" + "=" * 80)
    print("              DEEP SHOE MODEL ERROR ANALYSIS")
    print("=" * 80)
    print(f"{'Bin':<12} {'Obs':>8} {'Mean Hi-Lo':>12} {'Mean Exact':>12} {'MAE':>10} {'Max Div':>10}")
    print("-" * 80)
    
    for bin in bins:
        if bin.observations > 0:
            print(
                f"{bin.bin_name:<12} "
                f"{bin.observations:>8,} "
                f"{bin.mean_hilo*100:>+11.4f}% "
                f"{bin.mean_exact*100:>+11.4f}% "
                f"{bin.mae*100:>9.4f}% "
                f"{bin.max_divergence*100:>9.4f}%"
            )
    
    print("=" * 80)


def validate_hypothesis(bins: List[PenetrationBin]) -> Tuple[bool, str]:
    """
    Validate hypothesis: Is error at >90% penetration >2x higher than <50%?
    
    Returns:
        (hypothesis_valid, explanation)
    """
    # Get MAE for <50% penetration (bins 0-4)
    early_bins = [b for b in bins if b.range_end <= 0.5 and b.observations > 0]
    early_mae = sum(b.mae for b in early_bins) / len(early_bins) if early_bins else 0
    
    # Get MAE for >90% penetration (bin 9)
    late_bins = [b for b in bins if b.range_start >= 0.9 and b.observations > 0]
    late_mae = sum(b.mae for b in late_bins) / len(late_bins) if late_bins else 0
    
    if early_mae == 0:
        return False, "Insufficient data in early penetration bins"
    
    ratio = late_mae / early_mae
    hypothesis_valid = ratio >= 2.0
    
    explanation = (
        f"MAE at <50% penetration: {early_mae*100:.4f}%\n"
        f"MAE at >90% penetration: {late_mae*100:.4f}%\n"
        f"Ratio: {ratio:.2f}x"
    )
    
    return hypothesis_valid, explanation


def export_results(
    bins: List[PenetrationBin],
    output_path: Path
) -> None:
    """Export results to CSV."""
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Bin', 'Observations', 'Mean_HiLo', 'Mean_Exact', 'MAE', 'Max_Divergence'
        ])
        
        for bin in bins:
            if bin.observations > 0:
                writer.writerow([
                    bin.bin_name,
                    bin.observations,
                    f'{bin.mean_hilo:.6f}',
                    f'{bin.mean_exact:.6f}',
                    f'{bin.mae:.6f}',
                    f'{bin.max_divergence:.6f}'
                ])


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """Run the deep shoe model error study."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deep Shoe Model Error Study')
    parser.add_argument('-n', '--hands', type=int, default=100000,
                        help='Number of hands to simulate (default: 100,000)')
    parser.add_argument('-p', '--penetration', type=float, default=0.95,
                        help='Shoe penetration (default: 0.95 = 95%%)')
    parser.add_argument('-s', '--seed', type=int, default=42,
                        help='Random seed (default: 42)')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Output CSV path')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Minimal output')
    
    args = parser.parse_args()
    
    # Output directory
    output_dir = PROJECT_ROOT / "test_results"
    output_dir.mkdir(exist_ok=True)
    
    if not args.quiet:
        print("\n" + "=" * 70)
        print("           DEEP SHOE MODEL ERROR STUDY")
        print("=" * 70)
        print(f"   Penetration: {args.penetration:.0%}")
        print(f"   Hands: {args.hands:,}")
        print(f"   Seed: {args.seed}")
        print("=" * 70)
    
    # Configure rules with deep penetration
    rules = GameRules(
        num_decks=6,
        dealer_stands_soft_17=True,
        penetration=args.penetration,
        double_after_split=True,
        surrender_allowed=True
    )
    
    # Run simulation
    simulator = DeepShoeSimulator(rules=rules, seed=args.seed)
    observations = simulator.run(num_hands=args.hands, verbose=not args.quiet)
    
    # Analyze by penetration bin
    bins = create_penetration_bins()
    analyze_observations(observations, bins)
    
    # Print results
    if not args.quiet:
        print_results(bins)
    
    # Validate hypothesis
    hypothesis_valid, explanation = validate_hypothesis(bins)
    
    if not args.quiet:
        print("\n📊 HYPOTHESIS VALIDATION")
        print("-" * 50)
        print(f"   Question: Is error at >90% penetration >2x higher than <50%?")
        print()
        for line in explanation.split('\n'):
            print(f"   {line}")
        print()
        if hypothesis_valid:
            print("   ✓ HYPOTHESIS CONFIRMED: Hi-Lo diverges significantly at deep penetration")
        else:
            print("   ✗ HYPOTHESIS REJECTED: Hi-Lo maintains accuracy at deep penetration")
    
    # Export results
    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"model_error_study_{timestamp}.csv"
    
    export_results(bins, output_path)
    
    if not args.quiet:
        print(f"\n📁 Report exported to: {output_path}")
    
    return bins, hypothesis_valid


if __name__ == '__main__':
    main()
