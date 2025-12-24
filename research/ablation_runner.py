#!/usr/bin/env python3
"""
Ablation Study Runner.

Runs Monte Carlo simulations with different configurations to isolate
the marginal contribution of each component to overall EV.

Configurations:
- B0_S0: Flat Bet + Basic Strategy (Control) - Expected: ~-0.5% EV
- B0_S1: Flat Bet + CDZ Precision (not yet implemented)
- B0_S2: Flat Bet + I18/Fab4 Deviations
- B1_S0: Kelly Bet + Basic Strategy (no deviations)
- B1_S2: Kelly Bet + I18/Fab4 Deviations (Full Engine) - Expected: ~+1.5% EV
- B_K25/50/100: Kelly fraction variants (risk of ruin analysis)

Output: test_results/ablation_report_{timestamp}.csv
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


# =============================================================================
# Ablation Configurations
# =============================================================================

@dataclass
class AblationConfig:
    """Full ablation experiment configuration."""
    config_id: str
    description: str
    simulator_config: SimulatorConfig
    betting_config: BettingConfig
    expected_ev_range: tuple  # (min_ev, max_ev) as percentages


def get_ablation_configs() -> List[AblationConfig]:
    """Define all 6 ablation study configurations."""
    
    configs = []
    
    # B0_S0: Control - Flat Bet + Basic Strategy
    configs.append(AblationConfig(
        config_id="B0_S0",
        description="Control: Flat Bet + Basic Strategy (TDZ)",
        simulator_config=SimulatorConfig(
            config_id="B0_S0",
            use_counting=False,
            use_deviations=False,
            betting_strategy="FLAT",
            log_json=False
        ),
        betting_config=BettingConfig(
            flat_betting=True,
            kelly_fraction=0.5,  # Unused when flat_betting=True, but must be valid
            table_min=10.0,
            max_spread=1.0  # Flat = 1x spread
        ),
        expected_ev_range=(-0.60, -0.35)  # ~-0.5% EV
    ))
    
    # B0_S2: Flat Bet + Deviations
    configs.append(AblationConfig(
        config_id="B0_S2",
        description="Flat Bet + I18/Fab4 Deviations",
        simulator_config=SimulatorConfig(
            config_id="B0_S2",
            use_counting=True,   # Need counting for deviations
            use_deviations=True,
            betting_strategy="FLAT",
            log_json=False
        ),
        betting_config=BettingConfig(
            flat_betting=True,
            kelly_fraction=0.5,  # Unused when flat_betting=True
            table_min=10.0,
            max_spread=1.0
        ),
        expected_ev_range=(-0.55, -0.10)  # Deviations improve edge slightly
    ))
    
    # B1_S0: Kelly Bet + No Deviations
    configs.append(AblationConfig(
        config_id="B1_S0",
        description="Kelly Bet + Basic Strategy (No Deviations)",
        simulator_config=SimulatorConfig(
            config_id="B1_S0",
            use_counting=True,
            use_deviations=False,
            betting_strategy="KELLY",
            log_json=False
        ),
        betting_config=BettingConfig(
            flat_betting=False,
            kelly_fraction=0.5,  # Half-Kelly
            table_min=10.0,
            max_spread=12.0
        ),
        expected_ev_range=(0.3, 1.5)  # +0.3% to +1.5% EV (betting edge only)
    ))
    
    # B1_S2: Full Engine - Kelly Bet + Deviations
    configs.append(AblationConfig(
        config_id="B1_S2",
        description="Full Engine: Kelly Bet + I18/Fab4",
        simulator_config=SimulatorConfig(
            config_id="B1_S2",
            use_counting=True,
            use_deviations=True,
            betting_strategy="KELLY",
            log_json=False
        ),
        betting_config=BettingConfig(
            flat_betting=False,
            kelly_fraction=0.5,  # Half-Kelly
            table_min=10.0,
            max_spread=12.0
        ),
        expected_ev_range=(1.0, 2.0)  # +1% to +2% EV
    ))
    
    # B_K25: Quarter Kelly (Low Risk)
    configs.append(AblationConfig(
        config_id="B_K25",
        description="Quarter Kelly (Low Risk)",
        simulator_config=SimulatorConfig(
            config_id="B_K25",
            use_counting=True,
            use_deviations=True,
            betting_strategy="KELLY",
            log_json=False
        ),
        betting_config=BettingConfig(
            flat_betting=False,
            kelly_fraction=0.25,  # Quarter Kelly
            table_min=10.0,
            max_spread=6.0
        ),
        expected_ev_range=(0.3, 1.0)  # Lower EV, lower risk
    ))
    
    # B_K100: Full Kelly (High Risk)
    configs.append(AblationConfig(
        config_id="B_K100",
        description="Full Kelly (High Risk)",
        simulator_config=SimulatorConfig(
            config_id="B_K100",
            use_counting=True,
            use_deviations=True,
            betting_strategy="KELLY",
            log_json=False
        ),
        betting_config=BettingConfig(
            flat_betting=False,
            kelly_fraction=1.0,  # Full Kelly
            table_min=10.0,
            max_spread=24.0
        ),
        expected_ev_range=(1.5, 3.0)  # Higher EV, higher risk
    ))
    
    return configs


# =============================================================================
# Ablation Runner
# =============================================================================

@dataclass
class AblationResult:
    """Result from a single ablation run."""
    config_id: str
    description: str
    hands_played: int
    ev_percent: float
    win_rate: float
    max_drawdown: float
    final_bankroll: float
    standard_error: float
    expected_ev_range: tuple
    within_expected: bool


def run_ablation_study(
    num_hands: int = 100000,
    starting_bankroll: float = 10000.0,
    seed: Optional[int] = 42,
    configs: Optional[List[AblationConfig]] = None,
    verbose: bool = True
) -> List[AblationResult]:
    """
    Run the full ablation study.
    
    Args:
        num_hands: Number of hands per configuration.
        starting_bankroll: Starting bankroll.
        seed: Random seed for reproducibility.
        configs: List of configs to run. Defaults to all.
        verbose: Print progress.
        
    Returns:
        List of AblationResult for each configuration.
    """
    if configs is None:
        configs = get_ablation_configs()
    
    # Standard game rules
    rules = GameRules(
        num_decks=6,
        dealer_stands_soft_17=True,
        penetration=0.75,
        double_after_split=True,
        surrender_allowed=True
    )
    
    results: List[AblationResult] = []
    
    if verbose:
        print("\n" + "=" * 70)
        print("           ABLATION STUDY: Strategy Component Analysis")
        print("=" * 70)
        print(f"   Hands per config: {num_hands:,}")
        print(f"   Starting bankroll: ${starting_bankroll:,.2f}")
        print(f"   Seed: {seed}")
        print("=" * 70 + "\n")
    
    for i, config in enumerate(configs):
        if verbose:
            print(f"\n[{i+1}/{len(configs)}] Running {config.config_id}: {config.description}")
            print("-" * 50)
        
        # Create simulator with this config
        simulator = BlackjackSimulator(
            rules=rules,
            betting_config=config.betting_config,
            seed=seed,
            config=config.simulator_config
        )
        
        # Run simulation
        sim_result = simulator.run(
            num_hands=num_hands,
            starting_bankroll=starting_bankroll,
            verbose=False
        )
        
        # Check if within expected range
        within_expected = (
            config.expected_ev_range[0] <= sim_result.ev_percent <= config.expected_ev_range[1]
        )
        
        result = AblationResult(
            config_id=config.config_id,
            description=config.description,
            hands_played=sim_result.hands_played,
            ev_percent=sim_result.ev_percent,
            win_rate=sim_result.win_rate,
            max_drawdown=sim_result.max_drawdown,
            final_bankroll=sim_result.final_bankroll,
            standard_error=sim_result.standard_error,
            expected_ev_range=config.expected_ev_range,
            within_expected=within_expected
        )
        results.append(result)
        
        if verbose:
            status = "✓" if within_expected else "✗"
            print(f"   EV: {sim_result.ev_percent:+.4f}% (expected: {config.expected_ev_range[0]:+.2f}% to {config.expected_ev_range[1]:+.2f}%) {status}")
            print(f"   Win Rate: {sim_result.win_rate:.2%}")
            print(f"   Max Drawdown: ${sim_result.max_drawdown:,.2f}")
            print(f"   Final Bankroll: ${sim_result.final_bankroll:,.2f}")
    
    return results


def export_ablation_report(
    results: List[AblationResult],
    output_path: Optional[Path] = None
) -> Path:
    """Export ablation results to CSV."""
    if output_path is None:
        output_dir = PROJECT_ROOT / "test_results"
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"ablation_report_{timestamp}.csv"
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'Configuration',
            'Description', 
            'Hands',
            'EV_Percent',
            'Win_Rate',
            'Max_Drawdown',
            'Final_Bankroll',
            'Std_Error',
            'Expected_Min',
            'Expected_Max',
            'Within_Expected'
        ])
        
        # Data
        for r in results:
            writer.writerow([
                r.config_id,
                r.description,
                r.hands_played,
                f'{r.ev_percent:+.4f}',
                f'{r.win_rate:.4f}',
                f'{r.max_drawdown:.2f}',
                f'{r.final_bankroll:.2f}',
                f'{r.standard_error:.6f}',
                f'{r.expected_ev_range[0]:+.2f}',
                f'{r.expected_ev_range[1]:+.2f}',
                'YES' if r.within_expected else 'NO'
            ])
    
    return output_path


def print_summary_table(results: List[AblationResult]) -> None:
    """Print a formatted summary table."""
    print("\n" + "=" * 90)
    print("                        ABLATION STUDY SUMMARY")
    print("=" * 90)
    print(f"{'Config':<10} {'Description':<35} {'EV %':>10} {'Expected':>15} {'Status':>8}")
    print("-" * 90)
    
    for r in results:
        status = "✓ PASS" if r.within_expected else "✗ FAIL"
        expected = f"[{r.expected_ev_range[0]:+.2f}, {r.expected_ev_range[1]:+.2f}]"
        print(f"{r.config_id:<10} {r.description[:35]:<35} {r.ev_percent:>+9.4f}% {expected:>15} {status:>8}")
    
    print("=" * 90)
    
    # Attribution Analysis
    print("\n📊 EV ATTRIBUTION ANALYSIS")
    print("-" * 50)
    
    # Find control and full engine
    control = next((r for r in results if r.config_id == "B0_S0"), None)
    full = next((r for r in results if r.config_id == "B1_S2"), None)
    kelly_only = next((r for r in results if r.config_id == "B1_S0"), None)
    devs_only = next((r for r in results if r.config_id == "B0_S2"), None)
    
    if control:
        print(f"   Baseline (House Edge):      {control.ev_percent:+.4f}%")
    
    if kelly_only and control:
        kelly_contrib = kelly_only.ev_percent - control.ev_percent
        print(f"   Kelly Betting Contribution: {kelly_contrib:+.4f}%")
    
    if devs_only and control:
        devs_contrib = devs_only.ev_percent - control.ev_percent
        print(f"   Deviations Contribution:    {devs_contrib:+.4f}%")
    
    if full:
        print(f"   Full Engine Total:          {full.ev_percent:+.4f}%")
    
    print()


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """Run ablation study from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Ablation Study')
    parser.add_argument('-n', '--hands', type=int, default=100000,
                        help='Hands per configuration (default: 100,000)')
    parser.add_argument('-b', '--bankroll', type=float, default=10000.0,
                        help='Starting bankroll (default: $10,000)')
    parser.add_argument('-s', '--seed', type=int, default=42,
                        help='Random seed (default: 42)')
    parser.add_argument('--config', type=str, default=None,
                        help='Run single config by ID (e.g., B0_S0)')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Output CSV path')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Minimal output')
    
    args = parser.parse_args()
    
    # Filter configs if specific one requested
    configs = get_ablation_configs()
    if args.config:
        configs = [c for c in configs if c.config_id == args.config]
        if not configs:
            print(f"Error: Unknown config '{args.config}'")
            print("Available: " + ", ".join(c.config_id for c in get_ablation_configs()))
            sys.exit(1)
    
    # Run study
    results = run_ablation_study(
        num_hands=args.hands,
        starting_bankroll=args.bankroll,
        seed=args.seed,
        configs=configs,
        verbose=not args.quiet
    )
    
    # Export report
    output_path = Path(args.output) if args.output else None
    report_path = export_ablation_report(results, output_path)
    
    # Print summary
    if not args.quiet:
        print_summary_table(results)
        print(f"📁 Report exported to: {report_path}")


if __name__ == '__main__':
    main()
