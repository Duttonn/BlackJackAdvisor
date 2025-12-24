"""
Kelly Criterion Module.
Implements Kelly and fractional Kelly betting for bankroll management.

Responsibility: Calculate optimal bet size based on advantage and variance.
FORBIDDEN: Knowledge of specific cards - only works with counts and EV.
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class BetLimits:
    """Table betting limits and constraints."""
    table_min: float = 10.0
    table_max: float = 1000.0
    max_bet_spread: float = 12.0  # Maximum bet spread (e.g., 1-12)

    def clamp(self, bet: float) -> float:
        """Clamp bet to table limits."""
        return max(self.table_min, min(self.table_max, bet))


class KellyCalculator:
    """
    Kelly Criterion calculator for blackjack betting.
    
    Kelly Formula: f* = (bp - q) / b
    Where:
        f* = fraction of bankroll to bet
        b = odds received (1 for even money)
        p = probability of winning
        q = probability of losing (1 - p)
    
    For blackjack with advantage A:
        f* = A / variance
    
    Typical blackjack variance ≈ 1.26 per hand
    """

    # Standard blackjack variance (per unit bet)
    BLACKJACK_VARIANCE = 1.26

    def __init__(
        self,
        kelly_fraction: float = 0.5,
        variance: float = BLACKJACK_VARIANCE
    ):
        """
        Initialize Kelly calculator.
        
        Args:
            kelly_fraction: Fraction of Kelly to use (0.5 = Half Kelly).
                           Full Kelly is aggressive; Half Kelly is common.
            variance: Variance per unit bet. Default is standard BJ variance.
        """
        if not 0 < kelly_fraction <= 1.0:
            raise ValueError("Kelly fraction must be between 0 and 1")
        
        self._kelly_fraction = kelly_fraction
        self._variance = variance

    def calculate_bet_fraction(self, advantage: float) -> float:
        """
        Calculate the fraction of bankroll to bet.
        
        Args:
            advantage: Player advantage as a decimal (e.g., 0.01 = 1% edge).
            
        Returns:
            Fraction of bankroll to bet (0 if advantage <= 0).
        """
        if advantage <= 0:
            return 0.0
        
        # Kelly fraction = advantage / variance
        full_kelly = advantage / self._variance
        
        # Apply fractional Kelly
        return full_kelly * self._kelly_fraction

    def calculate_bet_amount(
        self,
        advantage: float,
        bankroll: float,
        limits: Optional[BetLimits] = None
    ) -> float:
        """
        Calculate the actual bet amount.
        
        Args:
            advantage: Player advantage as a decimal.
            bankroll: Current bankroll.
            limits: Optional bet limits.
            
        Returns:
            Bet amount clamped to limits.
        """
        if bankroll <= 0:
            return 0.0
            
        limits = limits or BetLimits()
        
        # Calculate Kelly bet
        fraction = self.calculate_bet_fraction(advantage)
        bet = bankroll * fraction
        
        # Clamp to limits
        bet = limits.clamp(bet)
        
        # Never bet more than bankroll
        bet = min(bet, bankroll)
        
        return bet

    @property
    def kelly_fraction(self) -> float:
        """Current Kelly fraction."""
        return self._kelly_fraction

    @property
    def variance(self) -> float:
        """Current variance setting."""
        return self._variance


class RiskOfRuin:
    """
    Calculate risk of ruin for different betting strategies.
    """

    @staticmethod
    def calculate(
        advantage: float,
        bet_fraction: float,
        variance: float = KellyCalculator.BLACKJACK_VARIANCE
    ) -> float:
        """
        Calculate approximate risk of ruin.
        
        For full Kelly, RoR approaches 0 over time.
        For over-betting, RoR approaches 1.
        
        Args:
            advantage: Player advantage (decimal).
            bet_fraction: Fraction of bankroll being bet.
            variance: Game variance.
            
        Returns:
            Approximate risk of ruin (0-1).
        """
        if advantage <= 0:
            return 1.0  # Certain ruin with no edge
            
        if bet_fraction <= 0:
            return 0.0  # No betting, no risk
        
        # Optimal fraction (full Kelly)
        optimal = advantage / variance
        
        if bet_fraction <= optimal:
            # Under-betting: lower risk but slower growth
            # Approximate RoR decreases exponentially
            return (1 - advantage) ** (1 / bet_fraction) if bet_fraction > 0 else 0
        else:
            # Over-betting: increased risk
            ratio = bet_fraction / optimal
            return min(1.0, ratio - 1)  # Simplified approximation


__all__ = ['KellyCalculator', 'BetLimits', 'RiskOfRuin']
