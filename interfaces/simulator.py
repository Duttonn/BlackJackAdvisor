"""
Simulator Interface Module.
High-speed Monte Carlo simulator to validate the engine's EV and Variance.

This is a Port in the Hexagonal Architecture, providing an interface
for simulation systems to interact with the decision engine.

CONSTRAINT: The Simulator contains NO strategy logic.
            It strictly queries src/ modules for all decisions.
"""

from typing import List, Dict, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict
import random
import csv
import sys
import json
import uuid
from pathlib import Path
from datetime import datetime

from src.core import Card, Hand, Action, GameState, Rank, Suit
from src.state import StateManager
from src.strategy import StrategyEngine, RuleConfig
from src.strategy.engine import DecisionResult
from src.betting import BettingEngine, BettingConfig
from src.config import GameRules


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SimulationResult:
    """Aggregate results from a simulation run."""
    hands_played: int = 0
    total_wagered: float = 0.0
    total_won: float = 0.0
    net_profit: float = 0.0
    ev_percent: float = 0.0  # Expected Value as percentage
    win_rate: float = 0.0
    average_bet: float = 0.0
    max_drawdown: float = 0.0
    final_bankroll: float = 0.0
    standard_error: float = 0.0
    
    # Wonging statistics
    hands_skipped: int = 0  # Hands not played due to wonging out
    
    # Detailed breakdowns
    hands_by_action: Dict[Action, int] = field(default_factory=dict)
    true_count_distribution: Dict[int, int] = field(default_factory=dict)
    ev_by_true_count: Dict[int, Tuple[float, int]] = field(default_factory=dict)  # TC -> (total_ev, count)
    
    # Win/Loss breakdown
    wins: int = 0
    losses: int = 0
    pushes: int = 0
    blackjacks: int = 0
    surrenders: int = 0
    busts: int = 0


@dataclass
class HandResult:
    """Result of a single hand."""
    player_hand: Hand
    dealer_hand: Hand
    final_player_total: int
    final_dealer_total: int
    actions_taken: List[Action]
    bet_size: float
    payout: float
    net_result: float  # payout - bet
    true_count: float
    outcome: str  # 'win', 'loss', 'push', 'blackjack', 'surrender', 'bust'


# =============================================================================
# Simulator Configuration (Ablation Studies)
# =============================================================================

@dataclass
class SimulatorConfig:
    """
    Configuration for ablation study experiments.
    
    Controls which components are active during simulation:
    - use_counting: If False, true count is always reported as 0
    - use_deviations: Passed to StrategyEngine.decide()
    - betting_strategy: "KELLY" (count-based) or "FLAT" (table min)
    - log_json: Enable Flight Recorder for NDJSON output
    
    Wonging/Cover simulation:
    - wong_out_threshold: TC below which to exit table (None = no wonging)
    - min_hands_per_shoe: Minimum hands to play before wonging out (cover)
    - simulate_late_entry: If True, start shoes at random penetration (0-50%)
    - late_entry_max_pen: Maximum penetration for late entry (default 0.5)
    """
    config_id: str = "FULL"           # Experiment identifier
    use_counting: bool = True         # If False, TC is always 0 for decisions
    use_deviations: bool = True       # Passed to StrategyEngine.decide()
    betting_strategy: str = "KELLY"   # "KELLY" or "FLAT"
    log_json: bool = False            # Enable Flight Recorder
    
    # Wonging/Cover parameters
    wong_out_threshold: Optional[float] = None  # TC to exit table (e.g., -1.0)
    min_hands_per_shoe: int = 0                 # Minimum hands before wonging
    simulate_late_entry: bool = False           # Start shoes mid-penetration
    late_entry_max_pen: float = 0.5             # Max penetration for late entry
    
    @classmethod
    def control(cls) -> 'SimulatorConfig':
        """B0_S0: Flat bet + Basic Strategy only (Control)."""
        return cls(
            config_id="B0_S0",
            use_counting=False,
            use_deviations=False,
            betting_strategy="FLAT",
            log_json=False
        )
    
    @classmethod
    def full_engine(cls) -> 'SimulatorConfig':
        """B1_S2: Full counting + Kelly + deviations."""
        return cls(
            config_id="B1_S2",
            use_counting=True,
            use_deviations=True,
            betting_strategy="KELLY",
            log_json=False
        )
    
    @classmethod
    def flat_with_deviations(cls) -> 'SimulatorConfig':
        """B0_S2: Flat betting with I18/Fab4 deviations."""
        return cls(
            config_id="B0_S2",
            use_counting=True,   # Need counting for deviations to work
            use_deviations=True,
            betting_strategy="FLAT",
            log_json=False
        )
    
    @classmethod
    def kelly_no_deviations(cls) -> 'SimulatorConfig':
        """B1_S0: Kelly betting without deviations."""
        return cls(
            config_id="B1_S0",
            use_counting=True,
            use_deviations=False,
            betting_strategy="KELLY",
            log_json=False
        )


# =============================================================================
# Flight Recorder (JSON Hand Trace Logging)
# =============================================================================

class FlightRecorder:
    """
    NDJSON logger for hand-level forensics.
    
    Records every hand with full context for post-hoc analysis:
    - Shoe state at decision time
    - Decision context (player hand, dealer up, action taken)
    - Outcome and P&L
    
    Output: test_results/flight_recorder_{timestamp}.jsonl
    """
    
    def __init__(self, config_id: str):
        """Initialize the flight recorder."""
        self.config_id = config_id
        self.session_id = f"sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        self._records: List[Dict[str, Any]] = []
        self._output_path: Optional[Path] = None
        self._file_handle = None
    
    def start(self, output_dir: Path) -> None:
        """Start recording session, open output file."""
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self._output_path = output_dir / f"flight_recorder_{self.config_id}_{timestamp}.jsonl"
        self._file_handle = open(self._output_path, 'w', encoding='utf-8')
    
    def record_hand(
        self,
        hand_id: str,
        shoe_state: Dict[str, Any],
        decision_context: Dict[str, Any],
        outcome: Dict[str, Any]
    ) -> None:
        """
        Record a single hand to NDJSON.
        
        Args:
            hand_id: Unique identifier for the hand (UUID)
            shoe_state: {cards_remaining, true_count}
            decision_context: {player_total, dealer_up, action_taken, deviation_trigger}
            outcome: {pnl, result}
        """
        record = {
            "session_id": self.session_id,
            "config_id": self.config_id,
            "hand_id": hand_id,
            "shoe_state": shoe_state,
            "decision_context": decision_context,
            "outcome": outcome
        }
        
        if self._file_handle:
            self._file_handle.write(json.dumps(record) + '\n')
            self._file_handle.flush()  # Immediate write for crash safety
        else:
            self._records.append(record)
    
    def stop(self) -> Optional[Path]:
        """Stop recording and close file. Returns output path."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
        return self._output_path
    
    @property
    def output_path(self) -> Optional[Path]:
        """Get the output file path."""
        return self._output_path


# =============================================================================
# Shoe Class
# =============================================================================

class Shoe:
    """
    Simulated shoe of cards.
    Manages a shuffled collection of decks for dealing.
    
    NOTE: This class is local to the simulator and does NOT modify src/core.
    """

    def __init__(self, num_decks: int = 6, seed: Optional[int] = None):
        """
        Initialize the shoe.
        
        Args:
            num_decks: Number of decks in the shoe.
            seed: Random seed for reproducibility.
        """
        self._num_decks = num_decks
        self._rng = random.Random(seed)
        self._cards: List[Card] = []
        self._dealt_index: int = 0
        self.shuffle()

    def shuffle(self) -> None:
        """Shuffle a fresh shoe."""
        self._cards = []
        for _ in range(self._num_decks):
            for suit in Suit:
                for rank in Rank:
                    self._cards.append(Card(rank, suit))
        self._rng.shuffle(self._cards)
        self._dealt_index = 0

    def deal(self) -> Card:
        """Deal a single card from the shoe."""
        if self._dealt_index >= len(self._cards):
            raise RuntimeError("Shoe is empty - needs shuffle")
        card = self._cards[self._dealt_index]
        self._dealt_index += 1
        return card

    def deal_multiple(self, count: int) -> List[Card]:
        """Deal multiple cards at once."""
        return [self.deal() for _ in range(count)]

    @property
    def cards_remaining(self) -> int:
        """Number of cards remaining in shoe."""
        return len(self._cards) - self._dealt_index

    @property
    def penetration(self) -> float:
        """Current penetration (percentage dealt)."""
        if len(self._cards) == 0:
            return 0.0
        return self._dealt_index / len(self._cards)

    def needs_shuffle(self, cut_penetration: float = 0.75) -> bool:
        """Check if shoe needs shuffling based on cut card position."""
        return self.penetration >= cut_penetration

    @property
    def total_cards(self) -> int:
        """Total number of cards in the shoe."""
        return len(self._cards)

    def burn_cards(self, count: int) -> None:
        """
        Burn cards from the shoe without observing them.
        
        Used for late entry simulation - advances the shoe index
        without the player seeing the cards.
        
        Args:
            count: Number of cards to burn.
        """
        self._dealt_index = min(self._dealt_index + count, len(self._cards))


# =============================================================================
# Blackjack Agent (Wraps Decision Engines)
# =============================================================================

class BlackjackAgent:
    """
    Agent that wraps the decision engines.
    Provides a clean interface for the simulator to query decisions.
    
    CONSTRAINT: Agent contains NO strategy logic - it only queries src/ modules.
    """

    def __init__(
        self,
        rules: GameRules,
        betting_config: Optional[BettingConfig] = None,
        seed: Optional[int] = None
    ):
        """
        Initialize the blackjack agent.
        
        Args:
            rules: Game rules configuration.
            betting_config: Betting configuration (optional).
            seed: Random seed (unused, for consistency).
        """
        self.rules = rules
        
        # Initialize State Manager
        self.state_manager = StateManager(rules)
        
        # Initialize Strategy Engine with matching rules
        rule_config = RuleConfig(
            dealer_stands_soft_17=rules.dealer_stands_soft_17,
            double_after_split=rules.double_after_split,
            surrender_allowed=rules.surrender_allowed,
            num_decks=rules.num_decks,
            rule_set_name='s17_das' if rules.dealer_stands_soft_17 else 'h17_das'
        )
        self.strategy_engine = StrategyEngine(rule_config)
        
        # Initialize Betting Engine with rules for proper edge calculation
        self.betting_engine = BettingEngine(
            config=betting_config or BettingConfig(),
            rules=rules
        )

    def observe_card(self, card: Card) -> None:
        """Observe a card being dealt."""
        self.state_manager.observe_card(card)

    def observe_cards(self, cards: List[Card]) -> None:
        """Observe multiple cards being dealt."""
        for card in cards:
            self.observe_card(card)

    def get_decision(
        self, 
        hand: Hand, 
        dealer_up: Card, 
        use_deviations: bool = True
    ) -> Action:
        """
        Query the strategy engine for a decision.
        
        Args:
            hand: Player's hand.
            dealer_up: Dealer's face-up card.
            use_deviations: If False, use baseline strategy only.
        """
        metrics = self.state_manager.get_metrics()
        return self.strategy_engine.decide(hand, dealer_up, metrics, use_deviations)

    def get_decision_with_context(
        self, 
        hand: Hand, 
        dealer_up: Card, 
        use_deviations: bool = True
    ) -> DecisionResult:
        """
        Query the strategy engine for a decision with full counterfactual context.
        
        Returns DecisionResult with both action and baseline_action for logging.
        """
        metrics = self.state_manager.get_metrics()
        return self.strategy_engine.decide_with_context(
            hand, dealer_up, metrics, use_deviations
        )

    def get_bet(self, bankroll: float) -> float:
        """Query the betting engine for bet size."""
        metrics = self.state_manager.get_metrics()
        return self.betting_engine.compute_bet(
            metrics.true_count, 
            bankroll,
            penetration=metrics.penetration
        )

    def get_metrics(self) -> GameState:
        """Get current game state metrics."""
        return self.state_manager.get_metrics()

    def reset(self) -> None:
        """Reset for new shoe."""
        self.state_manager.reset()

    def reset_with_burn(self, burn_count: int) -> None:
        """
        Reset for new shoe with late entry (cards already burned).
        
        Args:
            burn_count: Number of cards already dealt before we sat down.
                        RC stays at 0, but cards_seen reflects the burn
                        for accurate TC calculation.
        """
        self.state_manager.reset(burn_count=burn_count)


# =============================================================================
# Main Simulator
# =============================================================================

class BlackjackSimulator:
    """
    High-speed Monte Carlo simulator for blackjack.
    
    Validates the engine's EV and Variance through simulation.
    
    Features:
    - Full game logic (Hit, Stand, Double, Split, Surrender)
    - S17 vs H17 dealer rules support
    - Blackjack detection with 3:2 payout
    - EV tracking bucketed by True Count
    - Standard Error calculation
    - CSV output support
    - SimulatorConfig for ablation studies
    - Flight Recorder for NDJSON hand traces
    """

    def __init__(
        self,
        rules: Optional[GameRules] = None,
        betting_config: Optional[BettingConfig] = None,
        seed: Optional[int] = None,
        config: Optional[SimulatorConfig] = None
    ):
        """
        Initialize the simulator.
        
        Args:
            rules: Game rules configuration.
            betting_config: Betting configuration.
            seed: Random seed for reproducibility.
            config: SimulatorConfig for ablation studies (optional).
        """
        self.rules = rules or GameRules()
        self.seed = seed
        self.config = config or SimulatorConfig()
        
        # Apply config to betting_config
        if betting_config:
            self.betting_config = betting_config
        else:
            # Configure betting based on SimulatorConfig
            self.betting_config = BettingConfig(
                flat_betting=(self.config.betting_strategy == "FLAT")
            )
        
        # Create agent and shoe
        self.agent = BlackjackAgent(self.rules, self.betting_config, seed)
        self.shoe = Shoe(self.rules.num_decks, seed)
        
        # Flight Recorder (initialized if log_json is enabled)
        self._flight_recorder: Optional[FlightRecorder] = None
        if self.config.log_json:
            self._flight_recorder = FlightRecorder(self.config.config_id)
        
        # Results tracking
        self._hand_results: List[HandResult] = []
        self._ev_samples: List[float] = []  # For standard error calculation

    def run(
        self,
        num_hands: int,
        starting_bankroll: float = 10000.0,
        verbose: bool = False,
        on_hand_complete: Optional[Callable[[HandResult], None]] = None
    ) -> SimulationResult:
        """
        Run the Monte Carlo simulation.
        
        Args:
            num_hands: Number of hands to simulate.
            starting_bankroll: Starting bankroll.
            verbose: Print progress updates.
            on_hand_complete: Optional callback after each hand.
            
        Returns:
            SimulationResult with aggregate statistics.
        """
        result = SimulationResult(final_bankroll=starting_bankroll)
        bankroll = starting_bankroll
        max_bankroll = bankroll
        peak_bankroll = bankroll
        
        self._hand_results.clear()
        self._ev_samples.clear()
        
        # Wonging tracking
        hands_this_shoe = 0
        hands_skipped = 0  # Table hops due to wonging
        
        # Start Flight Recorder if enabled
        if self._flight_recorder:
            results_dir = Path(__file__).parent.parent / "test_results"
            self._flight_recorder.start(results_dir)
        
        for hand_num in range(num_hands):
            # Check for shuffle (new shoe)
            if self.shoe.needs_shuffle(self.rules.penetration):
                self.shoe.shuffle()
                hands_this_shoe = 0
                
                # LATE ENTRY LOGIC: Simulate sitting down mid-shoe
                if self.config.simulate_late_entry:
                    # Random entry point from 0 to late_entry_max_pen
                    max_burn = int(self.shoe.total_cards * self.config.late_entry_max_pen)
                    burn_count = random.randint(0, max_burn)
                    
                    # Burn cards from shoe (advance index without observing)
                    self.shoe.burn_cards(burn_count)
                    
                    # Reset agent with burn count (RC=0, but cards_seen reflects burn)
                    self.agent.reset_with_burn(burn_count)
                else:
                    self.agent.reset()
            
            # Get current metrics BEFORE dealing
            metrics = self.agent.get_metrics()
            
            # WONGING LOGIC: Check if we should exit (table hop)
            if self.config.wong_out_threshold is not None:
                if metrics.true_count < self.config.wong_out_threshold:
                    # Only wong out if we've met minimum hands requirement
                    if hands_this_shoe >= self.config.min_hands_per_shoe:
                        # TABLE HOP: Exit this bad shoe and find a fresh game
                        hands_skipped += 1
                        self.shoe.shuffle()  # New table = fresh shoe
                        hands_this_shoe = 0
                        
                        # Simulate late entry at new table if configured
                        if self.config.simulate_late_entry:
                            max_burn = int(self.shoe.total_cards * self.config.late_entry_max_pen)
                            burn_count = random.randint(0, max_burn)
                            self.shoe.burn_cards(burn_count)
                            self.agent.reset_with_burn(burn_count)
                        else:
                            self.agent.reset()  # Fresh count at new table
                        continue  # Re-evaluate TC at new table
            
            # Apply use_counting config: if False, treat TC as 0 for betting
            true_count = metrics.true_count if self.config.use_counting else 0.0
            tc_bucket = int(round(metrics.true_count))  # Always track real TC for stats
            
            # Track true count distribution
            result.true_count_distribution[tc_bucket] = \
                result.true_count_distribution.get(tc_bucket, 0) + 1
            
            # Determine bet size
            bet = self.agent.get_bet(bankroll)
            if bet <= 0 or bet < self.betting_config.table_min:
                bet = self.betting_config.table_min
            bet = min(bet, bankroll)  # Can't bet more than bankroll
            
            if bet <= 0:
                # Bankrupt
                break
            
            # Simulate the hand (pass config flags)
            hand_result = self._play_hand(bet, true_count, hand_num)
            
            # Update bankroll
            bankroll += hand_result.net_result
            result.total_wagered += hand_result.bet_size
            result.total_won += hand_result.payout
            result.hands_played += 1
            hands_this_shoe += 1  # Track hands for wonging cover
            
            # Track EV by true count
            ev_pct = hand_result.net_result / hand_result.bet_size if hand_result.bet_size > 0 else 0
            self._ev_samples.append(ev_pct)
            
            current_ev, count = result.ev_by_true_count.get(tc_bucket, (0.0, 0))
            result.ev_by_true_count[tc_bucket] = (current_ev + ev_pct, count + 1)
            
            # Track actions
            for action in hand_result.actions_taken:
                result.hands_by_action[action] = result.hands_by_action.get(action, 0) + 1
            
            # Track outcomes
            if hand_result.outcome == 'win':
                result.wins += 1
            elif hand_result.outcome == 'loss':
                result.losses += 1
            elif hand_result.outcome == 'push':
                result.pushes += 1
            elif hand_result.outcome == 'blackjack':
                result.blackjacks += 1
            elif hand_result.outcome == 'surrender':
                result.surrenders += 1
            elif hand_result.outcome == 'bust':
                result.busts += 1
            
            # Track max drawdown
            peak_bankroll = max(peak_bankroll, bankroll)
            drawdown = peak_bankroll - bankroll
            result.max_drawdown = max(result.max_drawdown, drawdown)
            
            max_bankroll = max(max_bankroll, bankroll)
            
            # Store result
            self._hand_results.append(hand_result)
            
            if on_hand_complete:
                on_hand_complete(hand_result)
            
            # Verbose progress
            if verbose and (hand_num + 1) % 10000 == 0:
                ev = result.net_profit / result.total_wagered * 100 if result.total_wagered > 0 else 0
                print(f"  Hand {hand_num + 1:,}: Bankroll ${bankroll:,.2f}, EV {ev:+.3f}%")
        
        # Calculate final statistics
        result.final_bankroll = bankroll
        result.net_profit = bankroll - starting_bankroll
        result.ev_percent = (result.net_profit / result.total_wagered * 100) if result.total_wagered > 0 else 0
        result.win_rate = result.wins / result.hands_played if result.hands_played > 0 else 0
        result.average_bet = result.total_wagered / result.hands_played if result.hands_played > 0 else 0
        result.hands_skipped = hands_skipped  # Hands not played due to wonging
        
        # Calculate standard error
        if len(self._ev_samples) > 1:
            mean_ev = sum(self._ev_samples) / len(self._ev_samples)
            variance = sum((x - mean_ev) ** 2 for x in self._ev_samples) / (len(self._ev_samples) - 1)
            result.standard_error = (variance ** 0.5) / (len(self._ev_samples) ** 0.5)
        
        # Stop Flight Recorder if enabled
        if self._flight_recorder:
            flight_path = self._flight_recorder.stop()
            if flight_path:
                print(f"📝 Flight Recorder: {flight_path}")
        
        return result

    def _play_hand(self, bet: float, true_count: float, hand_num: int = 0) -> HandResult:
        """
        Play out a complete hand of blackjack.
        
        Implements full game logic: Deal, Player Turn, Dealer Turn, Settlement.
        """
        actions_taken: List[Action] = []
        deviation_trigger: Optional[str] = None  # Track if deviation fired
        
        # === DEAL ===
        player_cards = [self.shoe.deal(), self.shoe.deal()]
        dealer_up = self.shoe.deal()
        dealer_hole = self.shoe.deal()
        
        # Observe initial cards (player cards + dealer up card)
        self.agent.observe_cards(player_cards)
        self.agent.observe_card(dealer_up)
        
        player_hand = Hand.from_cards(player_cards)
        dealer_hand_cards = [dealer_up, dealer_hole]
        
        # Check for player blackjack
        if player_hand.is_blackjack:
            self.agent.observe_card(dealer_hole)  # Reveal hole card
            dealer_hand = Hand.from_cards(dealer_hand_cards)
            
            if dealer_hand.is_blackjack:
                # Push on double blackjack
                return HandResult(
                    player_hand=player_hand,
                    dealer_hand=dealer_hand,
                    final_player_total=21,
                    final_dealer_total=21,
                    actions_taken=[Action.STAND],
                    bet_size=bet,
                    payout=bet,  # Return original bet
                    net_result=0.0,
                    true_count=true_count,
                    outcome='push'
                )
            else:
                # Player blackjack wins 3:2
                payout = bet + (bet * self.rules.blackjack_pays)
                return HandResult(
                    player_hand=player_hand,
                    dealer_hand=dealer_hand,
                    final_player_total=21,
                    final_dealer_total=dealer_hand.total,
                    actions_taken=[Action.STAND],
                    bet_size=bet,
                    payout=payout,
                    net_result=payout - bet,
                    true_count=true_count,
                    outcome='blackjack'
                )
        
        # === PLAYER TURN ===
        current_bet = bet
        player_busted = False
        first_decision_result: Optional[DecisionResult] = None  # Track for logging
        
        while True:
            decision_result = self.agent.get_decision_with_context(
                player_hand, 
                dealer_up, 
                use_deviations=self.config.use_deviations
            )
            action = decision_result.action
            actions_taken.append(action)
            
            # Track first decision for flight recorder logging
            if first_decision_result is None:
                first_decision_result = decision_result
                if decision_result.deviation_id:
                    deviation_trigger = decision_result.deviation_id
            
            if action == Action.SURRENDER:
                # Surrender: lose half bet
                self.agent.observe_card(dealer_hole)
                return HandResult(
                    player_hand=player_hand,
                    dealer_hand=Hand.from_cards(dealer_hand_cards),
                    final_player_total=player_hand.total,
                    final_dealer_total=Hand.from_cards(dealer_hand_cards).total,
                    actions_taken=actions_taken,
                    bet_size=bet,
                    payout=bet / 2,  # Return half
                    net_result=-bet / 2,
                    true_count=true_count,
                    outcome='surrender'
                )
            
            elif action == Action.STAND:
                break
            
            elif action == Action.HIT:
                new_card = self.shoe.deal()
                self.agent.observe_card(new_card)
                player_hand = player_hand.add_card(new_card)
                
                if player_hand.total > 21:
                    player_busted = True
                    break
            
            elif action == Action.DOUBLE:
                # Double: one more card, double bet
                current_bet = bet * 2
                new_card = self.shoe.deal()
                self.agent.observe_card(new_card)
                player_hand = player_hand.add_card(new_card)
                
                if player_hand.total > 21:
                    player_busted = True
                break  # Must stand after double
            
            elif action == Action.SPLIT:
                # Simplified split handling: just play one hand
                # (Full split implementation would require recursive handling)
                # For simulation accuracy, treat as hitting
                new_card = self.shoe.deal()
                self.agent.observe_card(new_card)
                player_hand = player_hand.add_card(new_card)
                
                if player_hand.total > 21:
                    player_busted = True
                    break
            
            else:
                # Unknown action, stand
                break
        
        # Player busted
        if player_busted:
            self.agent.observe_card(dealer_hole)
            return HandResult(
                player_hand=player_hand,
                dealer_hand=Hand.from_cards(dealer_hand_cards),
                final_player_total=player_hand.total,
                final_dealer_total=Hand.from_cards(dealer_hand_cards).total,
                actions_taken=actions_taken,
                bet_size=current_bet,
                payout=0.0,
                net_result=-current_bet,
                true_count=true_count,
                outcome='bust'
            )
        
        # === DEALER TURN ===
        # Reveal hole card
        self.agent.observe_card(dealer_hole)
        dealer_hand = Hand.from_cards(dealer_hand_cards)
        
        # Dealer plays according to rules
        while True:
            if dealer_hand.total > 21:
                break  # Dealer busts
            
            if dealer_hand.total >= 17:
                # Check for soft 17 with H17 rules
                if dealer_hand.total == 17 and dealer_hand.is_soft and not self.rules.dealer_stands_soft_17:
                    # H17: Dealer hits soft 17
                    pass
                else:
                    break  # Dealer stands
            
            # Dealer hits
            new_card = self.shoe.deal()
            self.agent.observe_card(new_card)
            dealer_hand = dealer_hand.add_card(new_card)
        
        # === SETTLEMENT ===
        player_total = player_hand.total
        dealer_total = dealer_hand.total
        
        if dealer_total > 21:
            # Dealer busts, player wins
            payout = current_bet * 2
            outcome = 'win'
        elif player_total > dealer_total:
            # Player wins
            payout = current_bet * 2
            outcome = 'win'
        elif player_total == dealer_total:
            # Push
            payout = current_bet
            outcome = 'push'
        else:
            # Dealer wins
            payout = 0.0
            outcome = 'loss'
        
        hand_result = HandResult(
            player_hand=player_hand,
            dealer_hand=dealer_hand,
            final_player_total=player_total,
            final_dealer_total=dealer_total,
            actions_taken=actions_taken,
            bet_size=current_bet,
            payout=payout,
            net_result=payout - current_bet,
            true_count=true_count,
            outcome=outcome
        )
        
        # === FLIGHT RECORDER LOGGING ===
        if self._flight_recorder and first_decision_result:
            hand_id = str(uuid.uuid4())
            shoe_state = {
                "cards_remaining": self.shoe.cards_remaining,
                "true_count": round(first_decision_result.true_count, 2)
            }
            decision_context = {
                "player_total": player_hand.total,  # Total at first decision
                "dealer_up": str(dealer_up),
                "action_taken": first_decision_result.action.name,
                "baseline_action": first_decision_result.baseline_action.name,
                "deviation_trigger": first_decision_result.deviation_id,
                "true_count": round(first_decision_result.true_count, 2),
                "deviated": first_decision_result.deviated
            }
            outcome_record = {
                "pnl": round(payout - current_bet, 2),
                "result": outcome.upper()
            }
            self._flight_recorder.record_hand(
                hand_id=hand_id,
                shoe_state=shoe_state,
                decision_context=decision_context,
                outcome=outcome_record
            )
        
        return hand_result

    def export_results_csv(self, filepath: str, result: SimulationResult) -> None:
        """
        Export simulation results to CSV.
        
        Args:
            filepath: Path to output CSV file.
            result: SimulationResult to export.
        """
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Summary section
            writer.writerow(['=== SIMULATION SUMMARY ==='])
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Hands Played', result.hands_played])
            writer.writerow(['Total Wagered', f'${result.total_wagered:,.2f}'])
            writer.writerow(['Net Profit', f'${result.net_profit:,.2f}'])
            writer.writerow(['EV %', f'{result.ev_percent:+.4f}%'])
            writer.writerow(['Standard Error', f'{result.standard_error:.6f}'])
            writer.writerow(['Final Bankroll', f'${result.final_bankroll:,.2f}'])
            writer.writerow(['Max Drawdown', f'${result.max_drawdown:,.2f}'])
            writer.writerow(['Win Rate', f'{result.win_rate:.2%}'])
            writer.writerow([])
            
            # Outcomes
            writer.writerow(['=== OUTCOMES ==='])
            writer.writerow(['Outcome', 'Count', 'Percentage'])
            total = result.hands_played
            writer.writerow(['Wins', result.wins, f'{result.wins/total:.2%}' if total else '0%'])
            writer.writerow(['Losses', result.losses, f'{result.losses/total:.2%}' if total else '0%'])
            writer.writerow(['Pushes', result.pushes, f'{result.pushes/total:.2%}' if total else '0%'])
            writer.writerow(['Blackjacks', result.blackjacks, f'{result.blackjacks/total:.2%}' if total else '0%'])
            writer.writerow(['Surrenders', result.surrenders, f'{result.surrenders/total:.2%}' if total else '0%'])
            writer.writerow(['Busts', result.busts, f'{result.busts/total:.2%}' if total else '0%'])
            writer.writerow([])
            
            # EV by True Count
            writer.writerow(['=== EV BY TRUE COUNT ==='])
            writer.writerow(['True Count', 'Hands', 'Total EV %', 'Avg EV %'])
            for tc in sorted(result.ev_by_true_count.keys()):
                total_ev, count = result.ev_by_true_count[tc]
                avg_ev = (total_ev / count * 100) if count > 0 else 0
                writer.writerow([tc, count, f'{total_ev*100:.4f}', f'{avg_ev:+.4f}%'])

    def print_results(self, result: SimulationResult) -> None:
        """Print simulation results to console."""
        print("\n" + "=" * 60)
        print("           BLACKJACK SIMULATION RESULTS")
        print("=" * 60)
        
        print(f"\n📊 SUMMARY")
        print(f"   Hands Played:    {result.hands_played:,}")
        print(f"   Total Wagered:   ${result.total_wagered:,.2f}")
        print(f"   Net Profit:      ${result.net_profit:+,.2f}")
        print(f"   EV:              {result.ev_percent:+.4f}%")
        print(f"   Standard Error:  ±{result.standard_error:.4f}")
        print(f"   Final Bankroll:  ${result.final_bankroll:,.2f}")
        print(f"   Max Drawdown:    ${result.max_drawdown:,.2f}")
        
        print(f"\n📈 OUTCOMES")
        total = result.hands_played
        if total > 0:
            print(f"   Wins:       {result.wins:,} ({result.wins/total:.1%})")
            print(f"   Losses:     {result.losses:,} ({result.losses/total:.1%})")
            print(f"   Pushes:     {result.pushes:,} ({result.pushes/total:.1%})")
            print(f"   Blackjacks: {result.blackjacks:,} ({result.blackjacks/total:.1%})")
            print(f"   Surrenders: {result.surrenders:,} ({result.surrenders/total:.1%})")
            print(f"   Busts:      {result.busts:,} ({result.busts/total:.1%})")
        
        print(f"\n📉 EV BY TRUE COUNT")
        print(f"   {'TC':>4} | {'Hands':>8} | {'Avg EV':>10}")
        print(f"   {'-'*4}-+-{'-'*8}-+-{'-'*10}")
        for tc in sorted(result.ev_by_true_count.keys()):
            total_ev, count = result.ev_by_true_count[tc]
            avg_ev = (total_ev / count * 100) if count > 0 else 0
            print(f"   {tc:>+4} | {count:>8,} | {avg_ev:>+9.2f}%")
        
        print("\n" + "=" * 60)


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """Run simulation from command line."""
    import argparse
    from datetime import datetime
    
    # Default output directory
    RESULTS_DIR = Path(__file__).parent.parent / "test_results"
    RESULTS_DIR.mkdir(exist_ok=True)
    
    parser = argparse.ArgumentParser(description='Blackjack Monte Carlo Simulator')
    parser.add_argument('-n', '--hands', type=int, default=100000,
                        help='Number of hands to simulate (default: 100,000)')
    parser.add_argument('-b', '--bankroll', type=float, default=10000.0,
                        help='Starting bankroll (default: $10,000)')
    parser.add_argument('-d', '--decks', type=int, default=6,
                        help='Number of decks (default: 6)')
    parser.add_argument('--h17', action='store_true',
                        help='Use H17 rules (dealer hits soft 17)')
    parser.add_argument('-s', '--seed', type=int, default=None,
                        help='Random seed for reproducibility')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Output CSV file path (default: test_results/sim_TIMESTAMP.csv)')
    parser.add_argument('--no-csv', action='store_true',
                        help='Disable automatic CSV output')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show progress during simulation')
    
    args = parser.parse_args()
    
    # Create rules
    rules = GameRules(
        num_decks=args.decks,
        dealer_stands_soft_17=not args.h17,
        penetration=0.75
    )
    
    print(f"\n🎰 BLACKJACK SIMULATOR")
    print(f"   Rules: {'H17' if args.h17 else 'S17'}, {args.decks} decks")
    print(f"   Hands: {args.hands:,}")
    print(f"   Bankroll: ${args.bankroll:,.2f}")
    if args.seed:
        print(f"   Seed: {args.seed}")
    print()
    
    # Run simulation
    simulator = BlackjackSimulator(rules=rules, seed=args.seed)
    result = simulator.run(
        num_hands=args.hands,
        starting_bankroll=args.bankroll,
        verbose=args.verbose
    )
    
    # Print results
    simulator.print_results(result)
    
    # Export to CSV (automatic unless --no-csv)
    if not args.no_csv:
        if args.output:
            output_path = args.output
        else:
            # Auto-generate timestamped filename in test_results/
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rules_tag = 'h17' if args.h17 else 's17'
            output_path = str(RESULTS_DIR / f"sim_{rules_tag}_{args.hands}h_{timestamp}.csv")
        
        simulator.export_results_csv(output_path, result)
        print(f"\n📁 Results exported to: {output_path}")


if __name__ == '__main__':
    main()


__all__ = [
    'BlackjackSimulator',
    'BlackjackAgent', 
    'Shoe',
    'SimulationResult',
    'HandResult',
    'SimulatorConfig',
    'FlightRecorder'
]
