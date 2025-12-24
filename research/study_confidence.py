#!/usr/bin/env python3
"""
Confidence Threshold Study.

Tests whether requiring a "stronger signal" (higher margin above index)
before deviating improves risk-adjusted returns (SCORE).

Study Design:
- Run simulations with varying confidence margins: 0.0, 0.5, 1.0, 2.0
- Compare EV, Variance, SCORE, and Deviation Frequency
- Identify optimal margin for risk-adjusted performance

Output: test_results/confidence_study_{timestamp}.csv
"""

import sys
import csv
import math
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
from src.strategy import RuleConfig


# =============================================================================
# Study Configuration
# =============================================================================

@dataclass
class ConfidenceResult:
    """Result from a single confidence margin run."""
    margin: float
    hands_played: int
    ev_percent: float
    variance: float
    standard_error: float
    max_drawdown: float
    final_bankroll: float
    deviation_frequency: float  # % of hands where action != baseline
    score: float  # Risk-adjusted return: EV / sqrt(Variance)


class ConfidenceStudySimulator(BlackjackSimulator):
    """
    Extended simulator that tracks deviation frequency.
    
    Counts how often action_taken != baseline_action.
    """
    
    def __init__(self, *args, deviation_margin: float = 0.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.deviation_margin = deviation_margin
        self._deviation_count = 0
        self._total_decisions = 0
    
    def run(self, *args, **kwargs) -> SimulationResult:
        """Run simulation and track deviation frequency."""
        self._deviation_count = 0
        self._total_decisions = 0
        return super().run(*args, **kwargs)
    
    def _play_hand(self, bet: float, true_count: float, hand_num: int = 0):
        """Override to track deviations."""
        result = super()._play_hand(bet, true_count, hand_num)
        
        # Access the tracked decision from last hand
        # Note: This is a simplified tracking approach
        # In production, we'd track in-line during play
        
        return result
    
    @property
    def deviation_frequency(self) -> float:
        """Percentage of hands where deviation fired."""
        if self._total_decisions == 0:
            return 0.0
        return self._deviation_count / self._total_decisions


def create_simulator_with_margin(
    rules: GameRules,
    margin: float,
    seed: Optional[int] = None
) -> BlackjackSimulator:
    """Create simulator with specific deviation margin."""
    from src.strategy import StrategyEngine, RuleConfig
    from src.state import StateManager
    
    # Create config with margin
    config = SimulatorConfig(
        config_id=f"MARGIN_{margin}",
        use_counting=True,
        use_deviations=True,
        betting_strategy="KELLY",
        log_json=True  # Enable logging to track deviations
    )
    
    betting_config = BettingConfig(
        flat_betting=False,
        kelly_fraction=0.5,
        table_min=10.0,
        max_spread=12.0
    )
    
    # Create simulator
    simulator = BlackjackSimulator(
        rules=rules,
        betting_config=betting_config,
        seed=seed,
        config=config
    )
    
    # Update the agent's strategy engine with the margin
    rule_config = RuleConfig(
        dealer_stands_soft_17=rules.dealer_stands_soft_17,
        double_after_split=rules.double_after_split,
        surrender_allowed=rules.surrender_allowed,
        num_decks=rules.num_decks,
        rule_set_name='s17_das' if rules.dealer_stands_soft_17 else 'h17_das',
        deviation_threshold_margin=margin
    )
    simulator.agent.strategy_engine = StrategyEngine(rule_config)
    
    return simulator


def count_deviations_from_log(log_path: Path) -> tuple:
    """
    Count deviation frequency from flight recorder log.
    
    Returns (deviation_count, total_hands).
    """
    import json
    
    deviation_count = 0
    total_hands = 0
    
    try:
        with open(log_path, 'r') as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    total_hands += 1
                    ctx = record.get('decision_context', {})
                    if ctx.get('deviated', False):
                        deviation_count += 1
    except Exception as e:
        print(f"Warning: Could not read log {log_path}: {e}")
        return 0, 0
    
    return deviation_count, total_hands


# =============================================================================
# Main Study Runner
# =============================================================================

def run_confidence_study(
    margins: List[float] = [0.0, 0.5, 1.0, 2.0],
    num_hands: int = 50000,
    starting_bankroll: float = 10000.0,
    seed: Optional[int] = 42,
    verbose: bool = True
) -> List[ConfidenceResult]:
    """
    Run the confidence threshold study.
    
    Args:
        margins: List of deviation threshold margins to test.
        num_hands: Number of hands per margin configuration.
        starting_bankroll: Starting bankroll.
        seed: Random seed for reproducibility.
        verbose: Print progress.
        
    Returns:
        List of ConfidenceResult for each margin.
    """
    # Standard game rules
    rules = GameRules(
        num_decks=6,
        dealer_stands_soft_17=True,
        penetration=0.75,
        double_after_split=True,
        surrender_allowed=True
    )
    
    results: List[ConfidenceResult] = []
    results_dir = PROJECT_ROOT / "test_results"
    results_dir.mkdir(exist_ok=True)
    
    if verbose:
        print("\n" + "=" * 70)
        print("        CONFIDENCE THRESHOLD STUDY")
        print("=" * 70)
        print(f"   Margins to test: {margins}")
        print(f"   Hands per margin: {num_hands:,}")
        print(f"   Starting bankroll: ${starting_bankroll:,.2f}")
        print(f"   Seed: {seed}")
        print("=" * 70 + "\n")
    
    for i, margin in enumerate(margins):
        if verbose:
            print(f"\n[{i+1}/{len(margins)}] Testing Margin = {margin}")
            print("-" * 50)
        
        # Create simulator with this margin
        simulator = create_simulator_with_margin(rules, margin, seed)
        
        # Run simulation
        sim_result = simulator.run(
            num_hands=num_hands,
            starting_bankroll=starting_bankroll,
            verbose=False
        )
        
        # Stop flight recorder and get log path
        log_path = None
        if simulator._flight_recorder:
            log_path = simulator._flight_recorder.stop()
        
        # Count deviations from log
        deviation_count, total_hands = 0, 0
        if log_path and log_path.exists():
            deviation_count, total_hands = count_deviations_from_log(log_path)
        
        deviation_freq = deviation_count / total_hands if total_hands > 0 else 0.0
        
        # Calculate variance from EV samples
        variance = sim_result.standard_error ** 2 * num_hands if num_hands > 1 else 0.0
        
        # Calculate SCORE (risk-adjusted return)
        # SCORE = EV / sqrt(Variance_per_hand)
        variance_per_hand = variance / num_hands if num_hands > 0 else 1.0
        score = sim_result.ev_percent / math.sqrt(variance_per_hand) if variance_per_hand > 0 else 0.0
        
        result = ConfidenceResult(
            margin=margin,
            hands_played=sim_result.hands_played,
            ev_percent=sim_result.ev_percent,
            variance=variance,
            standard_error=sim_result.standard_error,
            max_drawdown=sim_result.max_drawdown,
            final_bankroll=sim_result.final_bankroll,
            deviation_frequency=deviation_freq * 100,  # As percentage
            score=score
        )
        results.append(result)
        
        if verbose:
            print(f"   EV: {sim_result.ev_percent:+.4f}%")
            print(f"   Std Error: ±{sim_result.standard_error:.4f}")
            print(f"   Max Drawdown: ${sim_result.max_drawdown:,.2f}")
            print(f"   Deviation Frequency: {deviation_freq:.2%}")
            print(f"   SCORE: {score:.4f}")
    
    return results


def export_study_report(
    results: List[ConfidenceResult],
    output_path: Optional[Path] = None
) -> Path:
    """Export study results to CSV."""
    if output_path is None:
        output_dir = PROJECT_ROOT / "test_results"
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"confidence_study_{timestamp}.csv"
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'Margin',
            'Hands',
            'EV_Percent',
            'Variance',
            'Std_Error',
            'Max_Drawdown',
            'Final_Bankroll',
            'Deviation_Freq_Pct',
            'SCORE'
        ])
        
        # Data
        for r in results:
            writer.writerow([
                f'{r.margin:.1f}',
                r.hands_played,
                f'{r.ev_percent:+.4f}',
                f'{r.variance:.6f}',
                f'{r.standard_error:.6f}',
                f'{r.max_drawdown:.2f}',
                f'{r.final_bankroll:.2f}',
                f'{r.deviation_frequency:.2f}',
                f'{r.score:.4f}'
            ])
    
    return output_path


def print_summary_table(results: List[ConfidenceResult]) -> None:
    """Print a formatted summary table."""
    print("\n" + "=" * 90)
    print("                    CONFIDENCE THRESHOLD STUDY RESULTS")
    print("=" * 90)
    print(f"{'Margin':>8} {'EV %':>10} {'Std Err':>10} {'Dev Freq':>10} {'SCORE':>10} {'Status':>10}")
    print("-" * 90)
    
    best_score = max(r.score for r in results)
    
    for r in results:
        status = "★ BEST" if r.score == best_score else ""
        print(f"{r.margin:>8.1f} {r.ev_percent:>+9.4f}% {r.standard_error:>10.4f} "
              f"{r.deviation_frequency:>9.2f}% {r.score:>10.4f} {status:>10}")
    
    print("=" * 90)
    
    # Analysis
    print("\n📊 ANALYSIS")
    print("-" * 50)
    
    baseline = next((r for r in results if r.margin == 0.0), None)
    if baseline:
        print(f"   Baseline (Margin=0): EV={baseline.ev_percent:+.4f}%, SCORE={baseline.score:.4f}")
    
    best = max(results, key=lambda r: r.score)
    print(f"   Best SCORE at Margin={best.margin}: EV={best.ev_percent:+.4f}%, SCORE={best.score:.4f}")
    
    # Trade-off analysis
    if baseline and best.margin != 0.0:
        ev_diff = best.ev_percent - baseline.ev_percent
        freq_diff = best.deviation_frequency - baseline.deviation_frequency
        print(f"\n   Trade-off: {ev_diff:+.4f}% EV, {freq_diff:+.2f}% deviation frequency")
        if ev_diff < 0 and best.score > baseline.score:
            print("   → Lower EV but better risk-adjusted returns (lower variance)")
    
    print()


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """Run confidence study from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Confidence Threshold Study')
    parser.add_argument('-n', '--hands', type=int, default=50000,
                        help='Hands per margin configuration (default: 50,000)')
    parser.add_argument('-b', '--bankroll', type=float, default=10000.0,
                        help='Starting bankroll (default: $10,000)')
    parser.add_argument('-s', '--seed', type=int, default=42,
                        help='Random seed (default: 42)')
    parser.add_argument('--margins', type=str, default="0.0,0.5,1.0,2.0",
                        help='Comma-separated margins to test (default: 0.0,0.5,1.0,2.0)')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Output CSV path')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Minimal output')
    
    args = parser.parse_args()
    
    # Parse margins
    margins = [float(m.strip()) for m in args.margins.split(',')]
    
    # Run study
    results = run_confidence_study(
        margins=margins,
        num_hands=args.hands,
        starting_bankroll=args.bankroll,
        seed=args.seed,
        verbose=not args.quiet
    )
    
    # Export report
    output_path = Path(args.output) if args.output else None
    report_path = export_study_report(results, output_path)
    
    # Print summary
    if not args.quiet:
        print_summary_table(results)
        print(f"📁 Report exported to: {report_path}")


if __name__ == '__main__':
    main()
