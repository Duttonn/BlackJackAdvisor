#!/usr/bin/env python3
"""
Defense Validation Experiment.

Compares betting performance with and without the defensive penetration cutoff.

HYPOTHESIS:
The "Safe" configuration (max_betting_penetration=0.85) should preserve
most of the EV while significantly reducing drawdown and standard error
by avoiding aggressive bets in deep-shoe high-error states.

Configurations:
1. UNSAFE: max_betting_penetration = 1.0 (current risky behavior)
2. SAFE:   max_betting_penetration = 0.85 (defensive cutoff)

Metrics:
- Total EV (normalized to units per 100 hands)
- Standard Error of Returns
- Maximum Drawdown
- Bets made at >85% penetration
"""

import sys
import random
import math
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core import Card, Hand, Action, Rank, Suit, GameState
from src.state import StateManager
from src.state.manager import GameRules as StateGameRules
from src.betting import BettingEngine, BettingConfig
from src.config import GameRules


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class HandResult:
    """Result of a single hand."""
    bet: float
    outcome: float  # +bet for win, -bet for loss, 0 for push
    true_count: float
    penetration: float


@dataclass
class SimulationResult:
    """Aggregated simulation statistics."""
    config_name: str
    total_hands: int
    total_wagered: float
    total_outcome: float
    ev_per_hand: float
    standard_error: float
    max_drawdown: float
    deep_shoe_bets: int  # Bets at >85% penetration
    deep_shoe_wagered: float
    
    @property
    def ev_percent(self) -> float:
        """EV as percentage of wager."""
        if self.total_wagered == 0:
            return 0.0
        return (self.total_outcome / self.total_wagered) * 100


# =============================================================================
# Simulator
# =============================================================================

class DefenseSimulator:
    """
    Simplified simulator for defense validation.
    
    Plays blackjack hands with configurable penetration cutoff.
    """

    def __init__(
        self,
        rules: GameRules,
        betting_config: BettingConfig,
        seed: Optional[int] = None
    ):
        self.rules = rules
        self.betting_config = betting_config
        self.rng = random.Random(seed)
        
        # Initialize state tracking
        state_rules = StateGameRules(
            num_decks=rules.num_decks,
            penetration=rules.penetration
        )
        self.state_manager = StateManager(rules=state_rules)
        
        # Initialize betting engine
        self.betting_engine = BettingEngine(
            config=betting_config,
            rules=rules
        )
        
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

    def _play_hand(self, bankroll: float) -> HandResult:
        """
        Play a single hand with simplified rules.
        
        Uses a simplified outcome model based on:
        - Win rate ≈ 42.5% + advantage
        - Push rate ≈ 8.5%
        - Lose rate = remainder
        """
        metrics = self.state_manager.get_metrics()
        
        # Get bet amount
        bet = self.betting_engine.compute_bet(
            metrics.true_count,
            bankroll,
            penetration=metrics.penetration
        )
        
        if bet == 0:
            bet = self.betting_config.table_min
        
        # Deal cards (4 cards per hand on average)
        cards_to_deal = self.rng.randint(4, 7)
        for _ in range(cards_to_deal):
            if self.shoe_index >= len(self.shoe) * self.rules.penetration:
                break
            card = self._deal_card()
            self.state_manager.observe_card(card)
        
        # Simplified outcome model
        # Advantage modifies base 42.5% win rate
        advantage = self.betting_engine.get_advantage(metrics.true_count)
        win_prob = 0.425 + advantage
        push_prob = 0.085
        
        roll = self.rng.random()
        if roll < win_prob:
            outcome = bet  # Win
        elif roll < win_prob + push_prob:
            outcome = 0.0  # Push
        else:
            outcome = -bet  # Lose
        
        return HandResult(
            bet=bet,
            outcome=outcome,
            true_count=metrics.true_count,
            penetration=metrics.penetration
        )

    def run(
        self,
        num_hands: int,
        initial_bankroll: float = 10000.0
    ) -> List[HandResult]:
        """Run simulation for specified number of hands."""
        results: List[HandResult] = []
        bankroll = initial_bankroll
        
        for i in range(num_hands):
            # Check if need to reshuffle
            if self.shoe_index >= len(self.shoe) * self.rules.penetration:
                self._reset_shoe()
            
            result = self._play_hand(bankroll)
            results.append(result)
            bankroll += result.outcome
            
            # Prevent bankruptcy
            if bankroll < self.betting_config.table_min:
                bankroll = initial_bankroll  # Reset for study purposes
            
            if (i + 1) % 10000 == 0:
                print(f"   Processed {i + 1:,} hands...")
        
        return results


def analyze_results(
    config_name: str,
    results: List[HandResult]
) -> SimulationResult:
    """Analyze simulation results."""
    total_wagered = sum(r.bet for r in results)
    total_outcome = sum(r.outcome for r in results)
    
    # Calculate running bankroll for drawdown
    bankroll = 10000.0
    peak = bankroll
    max_drawdown = 0.0
    
    for r in results:
        bankroll += r.outcome
        peak = max(peak, bankroll)
        drawdown = (peak - bankroll) / peak if peak > 0 else 0
        max_drawdown = max(max_drawdown, drawdown)
    
    # Standard error of outcomes
    mean_outcome = total_outcome / len(results) if results else 0
    variance = sum((r.outcome - mean_outcome) ** 2 for r in results) / len(results) if results else 0
    std_dev = math.sqrt(variance)
    standard_error = std_dev / math.sqrt(len(results)) if results else 0
    
    # Deep shoe stats
    deep_results = [r for r in results if r.penetration > 0.85]
    deep_shoe_bets = len(deep_results)
    deep_shoe_wagered = sum(r.bet for r in deep_results)
    
    return SimulationResult(
        config_name=config_name,
        total_hands=len(results),
        total_wagered=total_wagered,
        total_outcome=total_outcome,
        ev_per_hand=mean_outcome,
        standard_error=standard_error,
        max_drawdown=max_drawdown * 100,  # As percentage
        deep_shoe_bets=deep_shoe_bets,
        deep_shoe_wagered=deep_shoe_wagered
    )


def run_experiment(num_hands: int = 50000, seed: int = 42):
    """Run the defense validation experiment."""
    print("=" * 70)
    print("     DEFENSIVE CUTOFF VALIDATION EXPERIMENT")
    print("=" * 70)
    print(f"   Hands: {num_hands:,}")
    print(f"   Penetration: 95%")
    print(f"   Seed: {seed}")
    print("=" * 70)
    print()
    
    # Common rules
    rules = GameRules(
        num_decks=6,
        penetration=0.95  # Deep shoe
    )
    
    # Configuration 1: UNSAFE (no cutoff)
    unsafe_config = BettingConfig(
        table_min=25.0,
        table_max=500.0,
        kelly_fraction=0.5,
        max_spread=8.0,
        max_betting_penetration=1.0  # No cutoff - RISKY
    )
    
    # Configuration 2: SAFE (defensive cutoff)
    safe_config = BettingConfig(
        table_min=25.0,
        table_max=500.0,
        kelly_fraction=0.5,
        max_spread=8.0,
        max_betting_penetration=0.85  # Cutoff at 85%
    )
    
    print("🎰 Running UNSAFE Configuration (no cutoff)...")
    unsafe_sim = DefenseSimulator(rules=rules, betting_config=unsafe_config, seed=seed)
    unsafe_results = unsafe_sim.run(num_hands)
    unsafe_stats = analyze_results("UNSAFE (pen_limit=1.0)", unsafe_results)
    
    print()
    print("🛡️ Running SAFE Configuration (85% cutoff)...")
    safe_sim = DefenseSimulator(rules=rules, betting_config=safe_config, seed=seed)
    safe_results = safe_sim.run(num_hands)
    safe_stats = analyze_results("SAFE (pen_limit=0.85)", safe_results)
    
    # Report
    print()
    print("=" * 70)
    print("                    RESULTS COMPARISON")
    print("=" * 70)
    print()
    print(f"{'Metric':<30} {'UNSAFE':>15} {'SAFE':>15} {'Diff':>12}")
    print("-" * 70)
    
    print(f"{'Total Wagered':.<30} ${unsafe_stats.total_wagered:>13,.0f} ${safe_stats.total_wagered:>13,.0f} {(safe_stats.total_wagered - unsafe_stats.total_wagered):>+12,.0f}")
    print(f"{'Total Outcome':.<30} ${unsafe_stats.total_outcome:>13,.2f} ${safe_stats.total_outcome:>13,.2f} {(safe_stats.total_outcome - unsafe_stats.total_outcome):>+12,.2f}")
    print(f"{'EV (% of wager)':.<30} {unsafe_stats.ev_percent:>14.3f}% {safe_stats.ev_percent:>14.3f}% {(safe_stats.ev_percent - unsafe_stats.ev_percent):>+11.3f}%")
    print(f"{'EV per Hand':.<30} ${unsafe_stats.ev_per_hand:>13.4f} ${safe_stats.ev_per_hand:>13.4f} ${(safe_stats.ev_per_hand - unsafe_stats.ev_per_hand):>+11.4f}")
    print(f"{'Standard Error':.<30} ${unsafe_stats.standard_error:>13.4f} ${safe_stats.standard_error:>13.4f} {(safe_stats.standard_error - unsafe_stats.standard_error):>+12.4f}")
    print(f"{'Max Drawdown':.<30} {unsafe_stats.max_drawdown:>14.2f}% {safe_stats.max_drawdown:>14.2f}% {(safe_stats.max_drawdown - unsafe_stats.max_drawdown):>+11.2f}%")
    print(f"{'Deep Shoe Bets (>85%)':.<30} {unsafe_stats.deep_shoe_bets:>15,} {safe_stats.deep_shoe_bets:>15,} {(safe_stats.deep_shoe_bets - unsafe_stats.deep_shoe_bets):>+12,}")
    print(f"{'Deep Shoe Wagered':.<30} ${unsafe_stats.deep_shoe_wagered:>13,.0f} ${safe_stats.deep_shoe_wagered:>13,.0f} ${(safe_stats.deep_shoe_wagered - unsafe_stats.deep_shoe_wagered):>+11,.0f}")
    
    print()
    print("=" * 70)
    print("                    HYPOTHESIS VALIDATION")
    print("=" * 70)
    print()
    
    # Check hypothesis
    drawdown_improvement = unsafe_stats.max_drawdown - safe_stats.max_drawdown
    se_improvement = unsafe_stats.standard_error - safe_stats.standard_error
    ev_retention = (safe_stats.total_outcome / unsafe_stats.total_outcome * 100) if unsafe_stats.total_outcome != 0 else 100
    
    print(f"   Drawdown Reduction: {drawdown_improvement:+.2f}%")
    print(f"   Standard Error Reduction: {se_improvement:+.4f}")
    print(f"   EV Retained: {ev_retention:.1f}%")
    print()
    
    if drawdown_improvement > 0 and ev_retention > 80:
        print("   ✓ HYPOTHESIS CONFIRMED: Defensive cutoff reduces risk while preserving most EV")
    elif drawdown_improvement > 0:
        print("   ~ PARTIAL: Drawdown reduced, but EV loss may be significant")
    else:
        print("   ✗ HYPOTHESIS NOT CONFIRMED: Defensive cutoff did not improve risk profile")
    
    # Export results
    results_dir = PROJECT_ROOT / "test_results"
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = results_dir / f"defense_validation_{timestamp}.csv"
    
    with open(output_file, 'w') as f:
        f.write("config,total_hands,total_wagered,total_outcome,ev_percent,ev_per_hand,standard_error,max_drawdown,deep_shoe_bets,deep_shoe_wagered\n")
        for stats in [unsafe_stats, safe_stats]:
            f.write(f"{stats.config_name},{stats.total_hands},{stats.total_wagered:.2f},{stats.total_outcome:.2f},{stats.ev_percent:.4f},{stats.ev_per_hand:.4f},{stats.standard_error:.4f},{stats.max_drawdown:.2f},{stats.deep_shoe_bets},{stats.deep_shoe_wagered:.2f}\n")
    
    print()
    print(f"📁 Results exported to: {output_file}")
    
    return unsafe_stats, safe_stats


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Defensive Cutoff Validation")
    parser.add_argument("--hands", type=int, default=50000, help="Number of hands")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()
    
    run_experiment(num_hands=args.hands, seed=args.seed)


if __name__ == "__main__":
    main()
