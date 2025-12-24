#!/usr/bin/env python3
"""
Wonging Realism Study.

Measures the "EV Decay" caused by realistic table-hopping constraints:
1. Min Hands per Shoe (Cover play - can't instantly leave)
2. Late Entry (Sitting down mid-shoe without seeing burned cards)

Configurations:
1. IDEAL: Exit at TC < -1, Min Hands 0, Fresh Shoes
2. COVERED: Exit at TC < -1, Min Hands 10 (forced cover play)
3. LATE_ENTRY: Exit at TC < -1, Min Hands 0, Random entry 0-50%
4. REALISTIC_PRO: Exit at TC < -1, Min Hands 10, Late Entry

Hypothesis:
- "Min Hands" will reduce EV (forced play in bad counts)
- "Late Entry" will increase Variance (betting on incomplete info)
"""

import sys
import csv
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from interfaces.simulator import (
    BlackjackSimulator, 
    SimulatorConfig, 
    SimulationResult
)
from src.config import GameRules
from src.betting import BettingConfig


@dataclass
class StudyConfig:
    """Configuration for a single wonging scenario."""
    name: str
    wong_threshold: float  # TC to exit table
    min_hands: int         # Minimum hands before leaving
    late_entry: bool       # Simulate late entry
    late_entry_max: float  # Max penetration for late entry


def create_configs() -> List[StudyConfig]:
    """Create the 4 study configurations."""
    return [
        StudyConfig(
            name="IDEAL",
            wong_threshold=-1.0,
            min_hands=0,
            late_entry=False,
            late_entry_max=0.0
        ),
        StudyConfig(
            name="COVERED",
            wong_threshold=-1.0,
            min_hands=10,
            late_entry=False,
            late_entry_max=0.0
        ),
        StudyConfig(
            name="LATE_ENTRY",
            wong_threshold=-1.0,
            min_hands=0,
            late_entry=True,
            late_entry_max=0.5
        ),
        StudyConfig(
            name="REALISTIC_PRO",
            wong_threshold=-1.0,
            min_hands=10,
            late_entry=True,
            late_entry_max=0.5
        ),
    ]


def run_study(num_hands: int = 100000, seed: int = 42):
    """Run the wonging realism study."""
    print("=" * 70)
    print("     WONGING REALISM STUDY")
    print("=" * 70)
    print(f"   Hands per config: {num_hands:,}")
    print(f"   Seed: {seed}")
    print("=" * 70)
    print()
    
    # Common game rules
    rules = GameRules(
        num_decks=6,
        penetration=0.75
    )
    
    # Common betting config
    betting_config = BettingConfig(
        table_min=25.0,
        table_max=500.0,
        kelly_fraction=0.5,
        max_spread=8.0,
        max_betting_penetration=0.85
    )
    
    configs = create_configs()
    results: List[tuple[StudyConfig, SimulationResult]] = []
    
    for cfg in configs:
        print(f"🎰 Running {cfg.name}...")
        print(f"   Wong Threshold: TC < {cfg.wong_threshold}")
        print(f"   Min Hands: {cfg.min_hands}")
        print(f"   Late Entry: {cfg.late_entry} (max {cfg.late_entry_max:.0%})")
        
        sim_config = SimulatorConfig(
            config_id=cfg.name,
            use_counting=True,
            use_deviations=True,
            betting_strategy="KELLY",
            wong_out_threshold=cfg.wong_threshold,
            min_hands_per_shoe=cfg.min_hands,
            simulate_late_entry=cfg.late_entry,
            late_entry_max_pen=cfg.late_entry_max
        )
        
        simulator = BlackjackSimulator(
            rules=rules,
            betting_config=betting_config,
            seed=seed,
            config=sim_config
        )
        
        result = simulator.run(num_hands=num_hands, verbose=False)
        results.append((cfg, result))
        
        print(f"   ✓ EV: {result.ev_percent:+.3f}%, Skipped: {result.hands_skipped:,}")
        print()
    
    # Report
    print("=" * 70)
    print("                    RESULTS COMPARISON")
    print("=" * 70)
    print()
    print(f"{'Config':<20} {'EV %':>10} {'Std Err':>10} {'Hands Played':>14} {'Hands Skipped':>14}")
    print("-" * 70)
    
    for cfg, result in results:
        print(f"{cfg.name:<20} {result.ev_percent:>+10.3f}% {result.standard_error:>10.4f} {result.hands_played:>14,} {result.hands_skipped:>14,}")
    
    # Calculate EV decay
    print()
    print("-" * 70)
    print("EV DECAY ANALYSIS (relative to IDEAL)")
    print("-" * 70)
    
    ideal_ev = results[0][1].ev_percent
    for cfg, result in results[1:]:
        ev_decay = result.ev_percent - ideal_ev
        pct_of_ideal = (result.ev_percent / ideal_ev * 100) if ideal_ev != 0 else 0
        print(f"{cfg.name:<20} EV Decay: {ev_decay:+.3f}%  ({pct_of_ideal:.1f}% of IDEAL)")
    
    # Hypothesis validation
    print()
    print("=" * 70)
    print("                    HYPOTHESIS VALIDATION")
    print("=" * 70)
    print()
    
    ideal_result = results[0][1]
    covered_result = results[1][1]
    late_entry_result = results[2][1]
    realistic_result = results[3][1]
    
    # Hypothesis 1: Min Hands reduces EV
    if covered_result.ev_percent < ideal_result.ev_percent:
        print("✓ CONFIRMED: Min Hands (Cover) reduces EV")
        print(f"  IDEAL: {ideal_result.ev_percent:+.3f}% → COVERED: {covered_result.ev_percent:+.3f}%")
    else:
        print("✗ NOT CONFIRMED: Min Hands did not reduce EV")
    
    print()
    
    # Hypothesis 2: Late Entry increases Variance
    if late_entry_result.standard_error > ideal_result.standard_error:
        print("✓ CONFIRMED: Late Entry increases Variance")
        print(f"  IDEAL SE: {ideal_result.standard_error:.4f} → LATE_ENTRY SE: {late_entry_result.standard_error:.4f}")
    else:
        print("✗ NOT CONFIRMED: Late Entry did not increase Variance")
    
    print()
    print(f"REALISTIC PRO Configuration:")
    print(f"  EV: {realistic_result.ev_percent:+.3f}%")
    print(f"  Standard Error: {realistic_result.standard_error:.4f}")
    print(f"  Hands Skipped: {realistic_result.hands_skipped:,}")
    
    # Export results
    results_dir = PROJECT_ROOT / "test_results"
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = results_dir / f"wonging_realism_{timestamp}.csv"
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "config", "ev_percent", "standard_error", "hands_played", 
            "hands_skipped", "total_wagered", "max_drawdown"
        ])
        for cfg, result in results:
            writer.writerow([
                cfg.name,
                f"{result.ev_percent:.4f}",
                f"{result.standard_error:.4f}",
                result.hands_played,
                result.hands_skipped,
                f"{result.total_wagered:.2f}",
                f"{result.max_drawdown:.2f}"
            ])
    
    print()
    print(f"📁 Results exported to: {output_file}")
    
    return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Wonging Realism Study")
    parser.add_argument("--hands", type=int, default=100000, help="Hands per config")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()
    
    run_study(num_hands=args.hands, seed=args.seed)


if __name__ == "__main__":
    main()
