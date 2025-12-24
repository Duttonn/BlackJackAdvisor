"""
Live API Interface Module.
Clean interface for real-time manual entry (or future OCR integration).

This is a Port in the Hexagonal Architecture, providing an interface
for live casino play via manual card input.

Features:
- Session management with persistent StateManager and StrategyEngine
- Simple card input methods (input_card, start_shoe, etc.)
- Decision and bet queries
- CLI mode for live terminal play
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum, auto
import re
import sys

from src.core import Card, Hand, Action, GameState, Rank, Suit
from src.state import StateManager
from src.strategy import StrategyEngine, RuleConfig
from src.betting import BettingEngine, BettingConfig
from src.config import GameRules


# =============================================================================
# Card Parsing Utilities
# =============================================================================

# Mapping for card string parsing
RANK_MAP = {
    'A': Rank.ACE, '1': Rank.ACE,
    '2': Rank.TWO,
    '3': Rank.THREE,
    '4': Rank.FOUR,
    '5': Rank.FIVE,
    '6': Rank.SIX,
    '7': Rank.SEVEN,
    '8': Rank.EIGHT,
    '9': Rank.NINE,
    '10': Rank.TEN, 'T': Rank.TEN,
    'J': Rank.JACK,
    'Q': Rank.QUEEN,
    'K': Rank.KING,
}

SUIT_MAP = {
    'H': Suit.HEARTS, '♥': Suit.HEARTS, 'h': Suit.HEARTS,
    'D': Suit.DIAMONDS, '♦': Suit.DIAMONDS, 'd': Suit.DIAMONDS,
    'C': Suit.CLUBS, '♣': Suit.CLUBS, 'c': Suit.CLUBS,
    'S': Suit.SPADES, '♠': Suit.SPADES, 's': Suit.SPADES,
}


def parse_card(card_str: str) -> Optional[Card]:
    """
    Parse a card string like "Ah", "10s", "5d", "Kc".
    
    Supported formats:
    - "Ah" = Ace of Hearts
    - "10s" = Ten of Spades  
    - "5d" = Five of Diamonds
    - "Kc" = King of Clubs
    - "Th" = Ten of Hearts (T = 10)
    
    Args:
        card_str: Card string to parse.
        
    Returns:
        Card object or None if parsing fails.
    """
    card_str = card_str.strip()
    if not card_str:
        return None
    
    # Handle 10 specially
    if card_str.startswith('10'):
        rank_str = '10'
        suit_str = card_str[2:].upper()
    else:
        rank_str = card_str[:-1].upper()
        suit_str = card_str[-1].upper()
    
    rank = RANK_MAP.get(rank_str)
    suit = SUIT_MAP.get(suit_str)
    
    if rank is None or suit is None:
        return None
    
    return Card(rank, suit)


def parse_cards(cards_str: str) -> List[Card]:
    """
    Parse multiple cards from a string.
    
    Supports formats:
    - "Ah Kd" (space-separated)
    - "Ah,Kd" (comma-separated)
    - "AhKd" (no separator for single-char ranks)
    
    Args:
        cards_str: String containing multiple cards.
        
    Returns:
        List of parsed Card objects.
    """
    # Try comma-separated first
    if ',' in cards_str:
        parts = [p.strip() for p in cards_str.split(',')]
    # Then space-separated
    elif ' ' in cards_str:
        parts = cards_str.split()
    else:
        # Try to parse as concatenated (only works for non-10 cards)
        parts = []
        i = 0
        while i < len(cards_str):
            # Check for 10
            if cards_str[i:i+2] == '10' and i + 3 <= len(cards_str):
                parts.append(cards_str[i:i+3])
                i += 3
            elif i + 2 <= len(cards_str):
                parts.append(cards_str[i:i+2])
                i += 2
            else:
                break
    
    cards = []
    for part in parts:
        card = parse_card(part)
        if card:
            cards.append(card)
    
    return cards


# =============================================================================
# Live Session
# =============================================================================

@dataclass
class LiveDecision:
    """Decision result with exit signal support."""
    action: Action
    should_exit: bool = False
    exit_reason: str = ""


@dataclass
class SessionState:
    """Current state of the live session."""
    player_cards: List[Card] = field(default_factory=list)
    dealer_up_card: Optional[Card] = None
    hand_in_progress: bool = False
    cards_observed_this_shoe: int = 0
    hands_played: int = 0
    hands_played_this_shoe: int = 0  # For wonging cover
    session_profit: float = 0.0


class LiveSession:
    """
    Live blackjack session manager.
    
    Provides a clean interface for real-time play:
    - start_shoe(): Initialize a new shoe
    - input_card(): Input observed cards
    - get_decision(): Get recommended action
    - get_bet(): Get recommended bet size
    
    All decisions are queried from the src/ modules.
    """

    def __init__(
        self,
        rules: Optional[GameRules] = None,
        bankroll: float = 10000.0,
        betting_config: Optional[BettingConfig] = None
    ):
        """
        Initialize a live session.
        
        Args:
            rules: Game rules configuration.
            bankroll: Current bankroll for bet sizing.
            betting_config: Betting configuration.
        """
        self.rules = rules or GameRules()
        self.bankroll = bankroll
        self.betting_config = betting_config or BettingConfig()
        
        # Initialize engines
        self.state_manager = StateManager(self.rules)
        
        rule_config = RuleConfig(
            dealer_stands_soft_17=self.rules.dealer_stands_soft_17,
            double_after_split=self.rules.double_after_split,
            surrender_allowed=self.rules.surrender_allowed,
            num_decks=self.rules.num_decks,
            rule_set_name='s17_das' if self.rules.dealer_stands_soft_17 else 'h17_das'
        )
        self.strategy_engine = StrategyEngine(rule_config)
        self.betting_engine = BettingEngine(
            config=self.betting_config,
            rules=self.rules
        )
        
        # Session state
        self._session = SessionState()

    def start_shoe(self, rules: Optional[GameRules] = None) -> None:
        """
        Start a new shoe (shuffle).
        
        Args:
            rules: Optional new rules to apply.
        """
        if rules:
            self.rules = rules
            self.state_manager = StateManager(rules)
            
            rule_config = RuleConfig(
                dealer_stands_soft_17=rules.dealer_stands_soft_17,
                double_after_split=rules.double_after_split,
                surrender_allowed=rules.surrender_allowed,
                num_decks=rules.num_decks,
                rule_set_name='s17_das' if rules.dealer_stands_soft_17 else 'h17_das'
            )
            self.strategy_engine = StrategyEngine(rule_config)
            self.betting_engine = BettingEngine(
                config=self.betting_config,
                rules=rules
            )
        else:
            self.state_manager.reset()
        
        self._session.cards_observed_this_shoe = 0
        self._session.hands_played_this_shoe = 0  # Reset per-shoe counter
        print(f"🔄 New shoe started. Rules: {'S17' if self.rules.dealer_stands_soft_17 else 'H17'}, {self.rules.num_decks} decks")

    def input_card(self, card_str: str) -> Optional[Card]:
        """
        Input a single observed card.
        
        Args:
            card_str: Card string (e.g., "Ah", "10s", "5d").
            
        Returns:
            Parsed Card object or None if parsing failed.
        """
        card = parse_card(card_str)
        if card:
            self.state_manager.observe_card(card)
            self._session.cards_observed_this_shoe += 1
            return card
        else:
            print(f"⚠️ Could not parse card: '{card_str}'")
            return None

    def input_cards(self, cards_str: str) -> List[Card]:
        """
        Input multiple observed cards.
        
        Args:
            cards_str: Cards string (e.g., "Ah Kd" or "Ah,Kd").
            
        Returns:
            List of parsed Card objects.
        """
        cards = parse_cards(cards_str)
        for card in cards:
            self.state_manager.observe_card(card)
            self._session.cards_observed_this_shoe += 1
        return cards

    def start_hand(self, player_cards: str, dealer_up: str) -> None:
        """
        Start a new hand with given cards.
        
        Args:
            player_cards: Player's cards (e.g., "Ah Kd").
            dealer_up: Dealer's up card (e.g., "10s").
        """
        # Parse and observe cards
        p_cards = parse_cards(player_cards)
        d_card = parse_card(dealer_up)
        
        if not p_cards:
            print("⚠️ Could not parse player cards")
            return
        if not d_card:
            print("⚠️ Could not parse dealer card")
            return
        
        # Observe cards
        for card in p_cards:
            self.state_manager.observe_card(card)
            self._session.cards_observed_this_shoe += 1
        
        self.state_manager.observe_card(d_card)
        self._session.cards_observed_this_shoe += 1
        
        # Set session state
        self._session.player_cards = p_cards
        self._session.dealer_up_card = d_card
        self._session.hand_in_progress = True

    def add_player_card(self, card_str: str) -> Optional[Card]:
        """Add a card to player's hand (after hit/split)."""
        card = parse_card(card_str)
        if card:
            self.state_manager.observe_card(card)
            self._session.cards_observed_this_shoe += 1
            self._session.player_cards.append(card)
            return card
        return None

    def end_hand(self, result: float = 0.0) -> None:
        """
        End the current hand.
        
        Args:
            result: Net profit/loss from the hand.
        """
        self._session.hand_in_progress = False
        self._session.player_cards = []
        self._session.dealer_up_card = None
        self._session.hands_played += 1
        self._session.hands_played_this_shoe += 1  # Track per-shoe for wonging
        self._session.session_profit += result
        self.bankroll += result

    def get_decision(self) -> LiveDecision:
        """
        Get the recommended action for current hand.
        
        Returns:
            LiveDecision with action and exit signal.
        """
        if not self._session.player_cards or not self._session.dealer_up_card:
            print("⚠️ No hand in progress. Use start_hand() first.")
            return LiveDecision(action=Action.STAND)
        
        hand = Hand.from_cards(self._session.player_cards)
        metrics = self.state_manager.get_metrics()
        
        action = self.strategy_engine.decide(
            hand, 
            self._session.dealer_up_card, 
            metrics
        )
        
        # Build decision with exit signal
        decision = LiveDecision(action=action)
        
        # EXIT SIGNAL: Check if we should leave the table
        # Wong out at TC < -1.0, but only after playing at least one hand (cover)
        if metrics.true_count < -1.0 and self._session.hands_played_this_shoe > 0:
            decision.should_exit = True
            decision.exit_reason = f"True Count {metrics.true_count:+.1f} < -1.0 (Wong Out)"
        
        return decision

    def get_bet(self) -> float:
        """
        Get the recommended bet size.
        
        Returns:
            Recommended bet amount.
        """
        metrics = self.state_manager.get_metrics()
        return self.betting_engine.compute_bet(
            metrics.true_count, 
            self.bankroll,
            penetration=metrics.penetration
        )

    def get_metrics(self) -> GameState:
        """Get current game state metrics."""
        return self.state_manager.get_metrics()

    def get_status(self) -> Dict[str, Any]:
        """
        Get current session status.
        
        Returns:
            Dictionary with session information.
        """
        metrics = self.state_manager.get_metrics()
        
        return {
            'running_count': metrics.running_count,
            'true_count': metrics.true_count,
            'cards_remaining': metrics.cards_remaining,
            'decks_remaining': metrics.decks_remaining,
            'cards_observed_this_shoe': self._session.cards_observed_this_shoe,
            'hands_played': self._session.hands_played,
            'session_profit': self._session.session_profit,
            'bankroll': self.bankroll,
            'hand_in_progress': self._session.hand_in_progress,
            'recommended_bet': self.get_bet(),
        }

    def display_status(self) -> None:
        """Print current session status to console."""
        status = self.get_status()
        metrics = self.get_metrics()
        
        print("\n" + "─" * 50)
        print("📊 SESSION STATUS")
        print("─" * 50)
        print(f"   Running Count:   {status['running_count']:+d}")
        print(f"   True Count:      {status['true_count']:+.2f}")
        print(f"   Cards Remaining: {status['cards_remaining']}")
        print(f"   Decks Remaining: {status['decks_remaining']:.1f}")
        print(f"   Recommended Bet: ${status['recommended_bet']:.2f}")
        print("─" * 50)
        print(f"   Hands Played:    {status['hands_played']}")
        print(f"   Session Profit:  ${status['session_profit']:+.2f}")
        print(f"   Bankroll:        ${status['bankroll']:.2f}")
        print("─" * 50)

        # Show current hand if in progress
        if self._session.hand_in_progress:
            hand = Hand.from_cards(self._session.player_cards)
            print(f"\n🃏 CURRENT HAND")
            print(f"   Player: {' '.join(str(c) for c in self._session.player_cards)} = {hand.total}")
            print(f"   Dealer: {self._session.dealer_up_card}")
            
            action = self.get_decision()
            print(f"   ➡️  Recommended: {action.name}")


# =============================================================================
# CLI Mode
# =============================================================================

def print_help():
    """Print CLI help message."""
    print("""
╔════════════════════════════════════════════════════════════╗
║              BLACKJACK DECISION ENGINE - CLI               ║
╠════════════════════════════════════════════════════════════╣
║  COMMANDS:                                                 ║
║                                                            ║
║  SHOE MANAGEMENT:                                          ║
║    new / shuffle    - Start a new shoe                     ║
║    status / s       - Show current count and status        ║
║                                                            ║
║  CARD INPUT:                                               ║
║    c <cards>        - Observe cards (e.g., "c Ah Kd 5s")   ║
║    hand <p> <d>     - Start hand (e.g., "hand Ah,Kd 10s")  ║
║    hit <card>       - Add card after hit (e.g., "hit 5d")  ║
║                                                            ║
║  DECISIONS:                                                ║
║    d / decide       - Get decision for current hand        ║
║    bet / b          - Get recommended bet size             ║
║                                                            ║
║  SESSION:                                                  ║
║    bankroll <amt>   - Set bankroll (e.g., "bankroll 5000") ║
║    win <amt>        - Record win and end hand              ║
║    lose <amt>       - Record loss and end hand             ║
║    push             - Record push and end hand             ║
║                                                            ║
║  OTHER:                                                    ║
║    help / h / ?     - Show this help                       ║
║    quit / q / exit  - Exit the program                     ║
╚════════════════════════════════════════════════════════════╝
    """)


def cli_main():
    """Run the CLI interface for live play."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Blackjack Live Decision Engine')
    parser.add_argument('-d', '--decks', type=int, default=6,
                        help='Number of decks (default: 6)')
    parser.add_argument('--h17', action='store_true',
                        help='Use H17 rules (dealer hits soft 17)')
    parser.add_argument('-b', '--bankroll', type=float, default=10000.0,
                        help='Starting bankroll (default: $10,000)')
    
    args = parser.parse_args()
    
    # Create rules and session
    rules = GameRules(
        num_decks=args.decks,
        dealer_stands_soft_17=not args.h17,
        penetration=0.75
    )
    
    session = LiveSession(rules=rules, bankroll=args.bankroll)
    
    print("\n" + "=" * 60)
    print("     🎰 BLACKJACK DECISION ENGINE - LIVE MODE 🎰")
    print("=" * 60)
    print(f"   Rules: {'H17' if args.h17 else 'S17'}, {args.decks} decks")
    print(f"   Bankroll: ${args.bankroll:,.2f}")
    print("   Type 'help' for commands")
    print("=" * 60)
    
    # Main loop
    while True:
        try:
            # Show count inline
            metrics = session.get_metrics()
            tc = metrics.true_count
            rc = metrics.running_count
            
            prompt = f"\n[RC:{rc:+d} TC:{tc:+.1f}] > "
            user_input = input(prompt).strip()
            
            if not user_input:
                continue
            
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            args_str = parts[1] if len(parts) > 1 else ""
            
            # === QUIT ===
            if cmd in ('quit', 'q', 'exit'):
                print("\n👋 Goodbye! Final session profit: ${:.2f}".format(
                    session._session.session_profit))
                break
            
            # === HELP ===
            elif cmd in ('help', 'h', '?'):
                print_help()
            
            # === NEW SHOE ===
            elif cmd in ('new', 'shuffle'):
                session.start_shoe()
            
            # === STATUS ===
            elif cmd in ('status', 's'):
                session.display_status()
            
            # === OBSERVE CARDS ===
            elif cmd == 'c':
                if not args_str:
                    print("Usage: c <cards> (e.g., 'c Ah Kd 5s')")
                    continue
                cards = session.input_cards(args_str)
                if cards:
                    print(f"✓ Observed: {', '.join(str(c) for c in cards)}")
                    metrics = session.get_metrics()
                    print(f"  RC: {metrics.running_count:+d}, TC: {metrics.true_count:+.2f}")
            
            # === START HAND ===
            elif cmd == 'hand':
                # Parse "hand Ah,Kd 10s" -> player="Ah,Kd", dealer="10s"
                hand_parts = args_str.split()
                if len(hand_parts) < 2:
                    print("Usage: hand <player_cards> <dealer_up>")
                    print("  Example: hand Ah,Kd 10s")
                    continue
                
                player_str = hand_parts[0]
                dealer_str = hand_parts[1]
                session.start_hand(player_str, dealer_str)
                
                # Show hand and decision
                if session._session.hand_in_progress:
                    hand = Hand.from_cards(session._session.player_cards)
                    print(f"\n🃏 Player: {player_str} = {hand.total}")
                    print(f"   Dealer: {dealer_str}")
                    
                    decision = session.get_decision()
                    print(f"\n   ➡️  {decision.action.name}")
                    
                    # EXIT SIGNAL WARNING
                    if decision.should_exit:
                        print(f"\n   ⚠️  STRATEGY ALERT: LEAVE TABLE")
                        print(f"       {decision.exit_reason}")
            
            # === HIT (add card) ===
            elif cmd == 'hit':
                if not args_str:
                    print("Usage: hit <card> (e.g., 'hit 5d')")
                    continue
                card = session.add_player_card(args_str)
                if card and session._session.hand_in_progress:
                    hand = Hand.from_cards(session._session.player_cards)
                    print(f"✓ Added: {card}, Total: {hand.total}")
                    
                    if hand.total > 21:
                        print("💥 BUST!")
                    else:
                        decision = session.get_decision()
                        print(f"   ➡️  {decision.action.name}")
                        
                        # EXIT SIGNAL WARNING
                        if decision.should_exit:
                            print(f"\n   ⚠️  STRATEGY ALERT: LEAVE TABLE")
                            print(f"       {decision.exit_reason}")
            
            # === GET DECISION ===
            elif cmd in ('d', 'decide'):
                if not session._session.hand_in_progress:
                    print("⚠️ No hand in progress. Use 'hand' command first.")
                    continue
                decision = session.get_decision()
                print(f"\n   ➡️  {decision.action.name}")
                
                # EXIT SIGNAL WARNING
                if decision.should_exit:
                    print(f"\n   ⚠️  STRATEGY ALERT: LEAVE TABLE")
                    print(f"       {decision.exit_reason}")
            
            # === GET BET ===
            elif cmd in ('bet', 'b'):
                bet = session.get_bet()
                print(f"\n   💰 Recommended bet: ${bet:.2f}")
            
            # === SET BANKROLL ===
            elif cmd == 'bankroll':
                try:
                    new_bankroll = float(args_str.replace('$', '').replace(',', ''))
                    session.bankroll = new_bankroll
                    print(f"✓ Bankroll set to ${new_bankroll:,.2f}")
                except ValueError:
                    print("Usage: bankroll <amount> (e.g., 'bankroll 5000')")
            
            # === RECORD WIN ===
            elif cmd == 'win':
                try:
                    amount = float(args_str.replace('$', '').replace(',', '')) if args_str else 0
                    session.end_hand(amount)
                    print(f"✓ Win recorded: +${amount:.2f}")
                except ValueError:
                    print("Usage: win <amount>")
            
            # === RECORD LOSS ===
            elif cmd == 'lose':
                try:
                    amount = float(args_str.replace('$', '').replace(',', '')) if args_str else 0
                    session.end_hand(-amount)
                    print(f"✓ Loss recorded: -${amount:.2f}")
                except ValueError:
                    print("Usage: lose <amount>")
            
            # === RECORD PUSH ===
            elif cmd == 'push':
                session.end_hand(0)
                print("✓ Push recorded")
            
            # === UNKNOWN COMMAND ===
            else:
                # Try to parse as card observation
                cards = parse_cards(user_input)
                if cards:
                    for card in cards:
                        session.state_manager.observe_card(card)
                        session._session.cards_observed_this_shoe += 1
                    print(f"✓ Observed: {', '.join(str(c) for c in cards)}")
                    metrics = session.get_metrics()
                    print(f"  RC: {metrics.running_count:+d}, TC: {metrics.true_count:+.2f}")
                else:
                    print(f"Unknown command: '{cmd}'. Type 'help' for commands.")
        
        except KeyboardInterrupt:
            print("\n\n👋 Session interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"⚠️ Error: {e}")




if __name__ == '__main__':
    cli_main()


__all__ = [
    'LiveSession',
    'LiveDecision',
    'parse_card',
    'parse_cards',
    'SessionState'
]
