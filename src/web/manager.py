"""
Session Manager for Web API.
Manages in-memory game sessions with UUID keys.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from interfaces.live_api import LiveSession, LiveDecision, parse_card, parse_cards
from interfaces.simulator import Shoe
from src.config import GameRules
from src.betting import BettingConfig
from src.core import Card, Hand, Action


class SessionMode(str, Enum):
    """Game session modes."""
    AUTO = "AUTO"       # Training mode - engine deals from simulated shoe
    MANUAL = "MANUAL"   # Shadowing mode - user inputs cards from real game


@dataclass
class GameSession:
    """
    Wrapper around LiveSession with additional web-specific state.
    """
    session_id: str
    mode: SessionMode
    live_session: LiveSession
    shoe: Optional[Shoe] = None  # Only for AUTO mode
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    # Current hand state (for AUTO mode training)
    current_player_cards: List[Card] = field(default_factory=list)
    current_dealer_up: Optional[Card] = None
    current_dealer_hole: Optional[Card] = None
    hand_in_progress: bool = False
    
    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session has expired due to inactivity."""
        return datetime.now() - self.last_activity > timedelta(minutes=timeout_minutes)


class SessionManager:
    """
    Manages active game sessions.
    
    Thread-safe in-memory storage with UUID keys.
    """
    
    def __init__(self, session_timeout_minutes: int = 30):
        self._sessions: Dict[str, GameSession] = {}
        self._timeout_minutes = session_timeout_minutes
        
        # Research-validated defaults
        self._default_rules = GameRules(
            num_decks=6,
            dealer_stands_soft_17=True,
            double_after_split=True,
            surrender_allowed=True,
            blackjack_pays=1.5,
            penetration=0.75
        )
        
        self._default_betting = BettingConfig(
            table_min=15.0,
            table_max=500.0,
            kelly_fraction=0.5,              # Half-Kelly (research validated)
            max_betting_penetration=0.85     # Hi-Lo degradation limit
        )
    
    def create_session(
        self,
        mode: SessionMode,
        bankroll: float = 10000.0,
        rules: Optional[GameRules] = None
    ) -> GameSession:
        """
        Create a new game session.
        
        Args:
            mode: AUTO (training) or MANUAL (shadowing)
            bankroll: Starting bankroll
            rules: Optional custom rules
            
        Returns:
            New GameSession with unique ID
        """
        session_id = str(uuid.uuid4())
        
        # Use provided rules or defaults
        game_rules = rules or self._default_rules
        
        # Create LiveSession with research defaults
        live_session = LiveSession(
            rules=game_rules,
            bankroll=bankroll,
            betting_config=self._default_betting
        )
        
        # Create game session
        session = GameSession(
            session_id=session_id,
            mode=mode,
            live_session=live_session
        )
        
        # For AUTO mode, create internal shoe
        if mode == SessionMode.AUTO:
            session.shoe = Shoe(num_decks=game_rules.num_decks)
            session.shoe.shuffle()
        
        # Store session
        self._sessions[session_id] = session
        
        # Cleanup expired sessions
        self._cleanup_expired()
        
        return session
    
    def get_session(self, session_id: str) -> Optional[GameSession]:
        """
        Get a session by ID.
        
        Returns None if session doesn't exist or is expired.
        """
        session = self._sessions.get(session_id)
        
        if session is None:
            return None
        
        if session.is_expired(self._timeout_minutes):
            self._sessions.pop(session_id, None)
            return None
        
        session.touch()
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if session existed."""
        return self._sessions.pop(session_id, None) is not None
    
    def _cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count of removed sessions."""
        expired = [
            sid for sid, session in self._sessions.items()
            if session.is_expired(self._timeout_minutes)
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)
    
    # =========================================================================
    # AUTO Mode Operations (Training)
    # =========================================================================
    
    def deal_hand(self, session_id: str) -> Optional[Dict]:
        """
        Deal a new hand from the internal shoe (AUTO mode only).
        
        Returns:
            Dict with player_cards, dealer_card, recommended_bet
        """
        session = self.get_session(session_id)
        if session is None or session.mode != SessionMode.AUTO:
            return None
        
        shoe = session.shoe
        live = session.live_session
        
        # Check for shuffle
        if shoe.needs_shuffle(session.live_session.rules.penetration):
            shoe.shuffle()
            live.start_shoe()
        
        # Deal cards
        player_card1 = shoe.deal()
        dealer_up = shoe.deal()
        player_card2 = shoe.deal()
        dealer_hole = shoe.deal()
        
        # Observe cards (player sees their cards + dealer up card)
        live.state_manager.observe_card(player_card1)
        live.state_manager.observe_card(player_card2)
        live.state_manager.observe_card(dealer_up)
        
        # Store current hand state
        session.current_player_cards = [player_card1, player_card2]
        session.current_dealer_up = dealer_up
        session.current_dealer_hole = dealer_hole
        session.hand_in_progress = True
        
        # Get metrics
        metrics = live.state_manager.get_metrics()
        hand = Hand.from_cards(session.current_player_cards)
        
        # Get recommended bet
        bet = live.get_bet()
        
        return {
            "player_cards": [str(c) for c in session.current_player_cards],
            "player_total": hand.total,
            "dealer_card": str(dealer_up),
            "running_count": metrics.running_count,
            "true_count": round(metrics.true_count, 2),
            "recommended_bet": round(bet, 2),
            "is_blackjack": hand.is_blackjack
        }
    
    def process_action(
        self,
        session_id: str,
        action: str
    ) -> Optional[Dict]:
        """
        Process player action and provide training feedback (AUTO mode).
        
        Returns:
            Dict with result, correct_action, feedback
        """
        session = self.get_session(session_id)
        if session is None or session.mode != SessionMode.AUTO:
            return None
        
        if not session.hand_in_progress:
            return {"error": "No hand in progress"}
        
        live = session.live_session
        shoe = session.shoe
        
        # Get the correct action
        hand = Hand.from_cards(session.current_player_cards)
        metrics = live.state_manager.get_metrics()
        
        # Build game state for decision
        live._session.player_cards = session.current_player_cards
        live._session.dealer_up_card = session.current_dealer_up
        live._session.hand_in_progress = True
        
        decision = live.get_decision()
        correct_action = decision.action
        
        # Parse user action
        try:
            user_action = Action[action.upper()]
        except KeyError:
            return {"error": f"Invalid action: {action}"}
        
        # Check if correct
        is_correct = user_action == correct_action
        
        # Process the action
        result = {
            "action_taken": action.upper(),
            "correct_action": correct_action.name,
            "is_correct": is_correct,
            "player_total": hand.total,
            "should_exit": decision.should_exit,
            "exit_reason": decision.exit_reason if decision.should_exit else None
        }
        
        # Handle HIT action
        if user_action == Action.HIT:
            new_card = shoe.deal()
            live.state_manager.observe_card(new_card)
            session.current_player_cards.append(new_card)
            
            new_hand = Hand.from_cards(session.current_player_cards)
            result["new_card"] = str(new_card)
            result["new_total"] = new_hand.total
            result["is_bust"] = new_hand.total > 21
            
            if new_hand.total > 21:
                session.hand_in_progress = False
                result["outcome"] = "BUST"
        
        # Handle STAND action
        elif user_action == Action.STAND:
            # Play out dealer
            dealer_total = self._play_dealer(session, shoe, live)
            player_total = hand.total
            
            if dealer_total > 21:
                result["outcome"] = "WIN"
            elif player_total > dealer_total:
                result["outcome"] = "WIN"
            elif player_total < dealer_total:
                result["outcome"] = "LOSS"
            else:
                result["outcome"] = "PUSH"
            
            result["dealer_total"] = dealer_total
            session.hand_in_progress = False
        
        # Handle DOUBLE action
        elif user_action == Action.DOUBLE:
            new_card = shoe.deal()
            live.state_manager.observe_card(new_card)
            session.current_player_cards.append(new_card)
            
            new_hand = Hand.from_cards(session.current_player_cards)
            result["new_card"] = str(new_card)
            result["new_total"] = new_hand.total
            
            if new_hand.total > 21:
                result["outcome"] = "BUST"
                session.hand_in_progress = False
            else:
                # Play out dealer
                dealer_total = self._play_dealer(session, shoe, live)
                player_total = new_hand.total
                
                if dealer_total > 21:
                    result["outcome"] = "WIN"
                elif player_total > dealer_total:
                    result["outcome"] = "WIN"
                elif player_total < dealer_total:
                    result["outcome"] = "LOSS"
                else:
                    result["outcome"] = "PUSH"
                
                result["dealer_total"] = dealer_total
                session.hand_in_progress = False
        
        # Handle SURRENDER action
        elif user_action == Action.SURRENDER:
            result["outcome"] = "SURRENDER"
            session.hand_in_progress = False
        
        return result
    
    def _play_dealer(
        self,
        session: GameSession,
        shoe: Shoe,
        live: LiveSession
    ) -> int:
        """Play out dealer hand and return final total."""
        dealer_cards = [session.current_dealer_up, session.current_dealer_hole]
        
        # Observe hole card
        live.state_manager.observe_card(session.current_dealer_hole)
        
        # Calculate dealer total
        def calc_total(cards: List[Card]) -> int:
            total = sum(c.rank.value for c in cards)
            aces = sum(1 for c in cards if c.rank.value == 11)
            while total > 21 and aces:
                total -= 10
                aces -= 1
            return total
        
        def is_soft(cards: List[Card], total: int) -> bool:
            if total > 21:
                return False
            aces = sum(1 for c in cards if c.rank.value == 11)
            return aces > 0 and total <= 21
        
        # Dealer hits on 16 or less, stands on 17+ (S17 rules)
        while True:
            total = calc_total(dealer_cards)
            soft = is_soft(dealer_cards, total)
            
            if total > 21:
                break
            if total >= 17:
                # S17: Stand on all 17s
                if live.rules.dealer_stands_soft_17 or not soft:
                    break
            
            # Hit
            new_card = shoe.deal()
            live.state_manager.observe_card(new_card)
            dealer_cards.append(new_card)
        
        return calc_total(dealer_cards)
    
    # =========================================================================
    # MANUAL Mode Operations (Shadowing)
    # =========================================================================
    
    def input_cards(
        self,
        session_id: str,
        cards: List[str]
    ) -> Optional[Dict]:
        """
        Input observed cards (MANUAL mode).
        
        Args:
            session_id: Session ID
            cards: List of card strings (e.g., ["Ah", "Kd", "5s"])
            
        Returns:
            Dict with count info and recommendations
        """
        session = self.get_session(session_id)
        if session is None or session.mode != SessionMode.MANUAL:
            return None
        
        live = session.live_session
        
        # Parse and observe cards
        parsed_cards = []
        for card_str in cards:
            card = parse_card(card_str)
            if card:
                live.state_manager.observe_card(card)
                parsed_cards.append(card)
        
        if not parsed_cards:
            return {"error": "No valid cards parsed"}
        
        # Get metrics
        metrics = live.state_manager.get_metrics()
        
        return {
            "cards_observed": [str(c) for c in parsed_cards],
            "running_count": metrics.running_count,
            "true_count": round(metrics.true_count, 2),
            "decks_remaining": round(metrics.decks_remaining, 1),
            "penetration": round(metrics.penetration, 2),
            "recommended_bet": round(live.get_bet(), 2)
        }
    
    def get_decision_for_hand(
        self,
        session_id: str,
        player_cards: List[str],
        dealer_card: str
    ) -> Optional[Dict]:
        """
        Get decision for a specific hand (MANUAL mode).
        
        Args:
            session_id: Session ID
            player_cards: Player card strings (e.g., ["Ah", "7d"])
            dealer_card: Dealer up card string (e.g., "10s")
            
        Returns:
            Dict with recommended action and exit signal
        """
        session = self.get_session(session_id)
        if session is None or session.mode != SessionMode.MANUAL:
            return None
        
        live = session.live_session
        
        # Parse cards
        parsed_player = [parse_card(c) for c in player_cards]
        parsed_player = [c for c in parsed_player if c is not None]
        parsed_dealer = parse_card(dealer_card)
        
        if not parsed_player or not parsed_dealer:
            return {"error": "Invalid card format"}
        
        # Setup hand in live session
        live._session.player_cards = parsed_player
        live._session.dealer_up_card = parsed_dealer
        live._session.hand_in_progress = True
        
        # Increment hands counter for exit signal logic (simulates playing a hand)
        live._session.hands_played_this_shoe += 1
        
        # Get decision
        decision = live.get_decision()
        metrics = live.state_manager.get_metrics()
        hand = Hand.from_cards(parsed_player)
        
        return {
            "player_cards": [str(c) for c in parsed_player],
            "player_total": hand.total,
            "dealer_card": str(parsed_dealer),
            "recommended_action": decision.action.name,
            "running_count": metrics.running_count,
            "true_count": round(metrics.true_count, 2),
            "should_exit": decision.should_exit,
            "exit_reason": decision.exit_reason if decision.should_exit else None,
            "recommended_bet": round(live.get_bet(), 2)
        }
    
    def reset_shoe(self, session_id: str) -> Optional[Dict]:
        """Reset the shoe (new shuffle) for any mode."""
        session = self.get_session(session_id)
        if session is None:
            return None
        
        live = session.live_session
        live.start_shoe()
        
        if session.mode == SessionMode.AUTO and session.shoe:
            session.shoe.shuffle()
        
        session.hand_in_progress = False
        session.current_player_cards = []
        session.current_dealer_up = None
        session.current_dealer_hole = None
        
        return {
            "status": "shuffled",
            "running_count": 0,
            "true_count": 0.0
        }
