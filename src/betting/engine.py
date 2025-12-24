"""
Betting Engine Module.
Main interface for computing optimal bet sizes.

Responsibility: Map True Count to Bet Size.
Invariant: Bet > Bankroll is impossible.

FORBIDDEN: Knowledge of specific cards - only works with counts/EV.

CRITICAL: The baseline house edge depends on table rules!
- H17 (dealer hits soft 17): +0.22% edge to house
- 6:5 blackjack payout: +1.39% edge to house
Always inject GameRules to avoid overbetting on unfavorable tables.
"""

from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass

from .kelly import KellyCalculator, BetLimits
from .estimator import EVEstimator, AdvantageModel

if TYPE_CHECKING:
    from ..config.loader import GameRules


@dataclass
class BettingConfig:
    """Configuration for the betting engine."""
    kelly_fraction: float = 0.5  # Half-Kelly by default (SAFETY CONSTRAINT)
    table_min: float = 10.0
    table_max: float = 1000.0
    max_spread: float = 12.0  # 1-12 spread
    num_decks: int = 6
    flat_betting: bool = False  # If True, always bet table_min (ignore count)
    max_betting_penetration: float = 0.85  # Defensive cutoff: assume no edge beyond this


class BettingEngine:
    """
    Main betting engine for blackjack.
    
    Maps True Count to optimal bet size using:
    1. Linear EV approximation: Advantage = (TC × Slope) - Baseline_Edge
    2. Fractional Kelly Criterion: Bet = Kelly_Fraction × (Advantage / Variance)
    3. Clamping to table limits and bankroll constraints
    
    SAFETY: Uses Half-Kelly (fraction=0.5) by default to reduce risk of ruin.
    Full Kelly assumes perfect knowledge which we don't have with linear approximation.
    
    Invariant: Bet > Bankroll is impossible.
    """

    def __init__(
        self,
        config: Optional[BettingConfig] = None,
        rules: Optional["GameRules"] = None
    ):
        """
        Initialize the betting engine.
        
        Args:
            config: Betting configuration. Uses defaults if not provided.
            rules: Game rules for calculating accurate baseline edge.
                   STRONGLY RECOMMENDED to avoid overbetting on H17/6:5 tables.
        """
        self._config = config or BettingConfig()
        self._rules = rules
        
        # Initialize components
        self._limits = BetLimits(
            table_min=self._config.table_min,
            table_max=self._config.table_max,
            max_bet_spread=self._config.max_spread
        )
        
        self._kelly = KellyCalculator(
            kelly_fraction=self._config.kelly_fraction
        )
        
        # Use rule-adjusted model if rules provided
        if rules is not None:
            self._estimator = EVEstimator(rules=rules)
        else:
            # Default S17 baseline - WARNING: may overbet on H17 tables!
            self._estimator = EVEstimator()

    def compute_bet(
        self, 
        true_count: float, 
        bankroll: float,
        penetration: float = 0.0
    ) -> float:
        """
        Compute optimal bet size for given true count and bankroll.
        
        Applies:
        1. DEFENSIVE CUTOFF: If penetration > max_betting_penetration, assume no edge
        2. (TC × Slope) - Baseline_Edge → Advantage
        3. Half-Kelly(Advantage, Variance=1.26) → Bet Fraction
        4. Clamp between TableMin and min(TableMax, Bankroll)
        
        If flat_betting is enabled, always returns table minimum.
        
        Args:
            true_count: Current true count.
            bankroll: Current bankroll amount.
            penetration: Fraction of shoe dealt (0.0 to 1.0).
            
        Returns:
            Clamped bet amount between table limits.
            Returns 0 if bankroll is insufficient.
        """
        if bankroll < self._limits.table_min:
            return 0.0  # Can't afford minimum bet
        
        # FLAT BETTING: Always bet table minimum (ignore count)
        if self._config.flat_betting:
            return self._limits.table_min
        
        # DEFENSIVE CUTOFF: In deep shoes, the linear model is unreliable
        # Force table minimum bet when beyond the safe penetration threshold
        if penetration > self._config.max_betting_penetration:
            return self._limits.table_min
        
        # Step 1: Estimate advantage
        advantage = self._estimator.estimate_advantage(
            true_count, 
            self._config.num_decks
        )
        
        # Step 2: Calculate Kelly bet
        bet = self._kelly.calculate_bet_amount(
            advantage=advantage,
            bankroll=bankroll,
            limits=self._limits
        )
        
        # Step 3: Apply spread limits
        max_bet = self._limits.table_min * self._config.max_spread
        bet = min(bet, max_bet)
        
        # Step 4: Ensure bet doesn't exceed bankroll
        bet = min(bet, bankroll)
        
        # Step 5: Final clamping
        if bet < self._limits.table_min:
            # If can't afford min bet after calculations, bet minimum
            if advantage > 0 and bankroll >= self._limits.table_min:
                return self._limits.table_min
            return self._limits.table_min if bankroll >= self._limits.table_min else 0.0
        
        return round(bet, 2)

    def compute_bet_units(self, true_count: float) -> float:
        """
        Compute bet in units relative to table minimum.
        
        Useful for bet spreading without knowing exact bankroll.
        
        Args:
            true_count: Current true count.
            
        Returns:
            Number of units to bet (1.0 = table minimum).
        """
        if true_count <= self.breakeven_count:
            return 1.0  # Minimum bet below breakeven
        
        # Linear spread based on count
        # Each TC above breakeven = additional unit
        units = 1.0 + (true_count - self.breakeven_count)
        
        # Cap at max spread
        return min(units, self._config.max_spread)

    def should_bet(self, true_count: float) -> bool:
        """
        Determine if conditions are favorable for betting.
        
        Args:
            true_count: Current true count.
            
        Returns:
            True if player has an edge, False otherwise.
        """
        advantage = self._estimator.estimate_advantage(
            true_count,
            self._config.num_decks
        )
        return advantage > 0

    def should_wong_out(self, true_count: float, threshold: float = -1.0) -> bool:
        """
        Determine if player should leave the table (wong out).
        
        Args:
            true_count: Current true count.
            threshold: TC threshold for leaving (default -1).
            
        Returns:
            True if player should leave, False otherwise.
        """
        return true_count < threshold

    @property
    def breakeven_count(self) -> float:
        """True count at which player breaks even."""
        return self._estimator.breakeven_count()

    @property
    def config(self) -> BettingConfig:
        """Current betting configuration."""
        return self._config

    def get_advantage(self, true_count: float) -> float:
        """
        Get the estimated player advantage for a true count.
        
        Args:
            true_count: Current true count.
            
        Returns:
            Advantage as a decimal (negative = house edge).
        """
        return self._estimator.estimate_advantage(
            true_count,
            self._config.num_decks
        )

    def get_expected_value(self, true_count: float, bet: float) -> float:
        """
        Get expected value for a specific bet at given count.
        
        Args:
            true_count: Current true count.
            bet: Bet amount.
            
        Returns:
            Expected value in currency units.
        """
        return self._estimator.estimate_ev_per_hand(
            true_count,
            bet,
            self._config.num_decks
        )

    def __repr__(self) -> str:
        return (
            f"BettingEngine(kelly={self._config.kelly_fraction}, "
            f"spread=1-{self._config.max_spread}, "
            f"limits=${self._limits.table_min}-${self._limits.table_max})"
        )


__all__ = ['BettingEngine', 'BettingConfig']
