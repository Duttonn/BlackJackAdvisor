#!/usr/bin/env python3
"""
Live Interface Verification Script.

Programmatically validates the Live API by running the "Dry Run" scenario:
1. Low card counting: 2,3,4,5,6 -> TC should rise
2. High card counting: T,J,Q,K,A -> TC should return to 0
3. Decision test: 8,8 vs 10 -> SPLIT
4. I18 Deviation: 16 vs 10 at TC >= 0 -> STAND

This script proves the Live Interface is feature-complete and ready
for integration with OCR or manual tablet entry at the table.

Usage:
    python scripts/verify_live.py
    python -m scripts.verify_live
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from interfaces.live_api import LiveSession, parse_card, parse_cards
from src.core import Action


class TestResult:
    """Tracks test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def record(self, name: str, passed: bool, details: str = ""):
        self.tests.append((name, passed, details))
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def print_summary(self):
        print("\n" + "=" * 70)
        print("                    VERIFICATION RESULTS")
        print("=" * 70)
        
        for name, passed, details in self.tests:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"\n  {status}  {name}")
            if details:
                print(f"         {details}")
        
        print("\n" + "-" * 70)
        total = self.passed + self.failed
        print(f"  TOTAL: {self.passed}/{total} tests passed")
        
        if self.failed == 0:
            print("\n  🎉 ALL TESTS PASSED - SYSTEM FEATURE COMPLETE 🎉")
        else:
            print(f"\n  ⚠️  {self.failed} TESTS FAILED - REVIEW REQUIRED")
        
        print("=" * 70)
        return self.failed == 0


def test_card_parsing(results: TestResult):
    """Test card parsing utilities."""
    print("\n[TEST] Card Parsing")
    print("-" * 40)
    
    # Test single card parsing
    test_cases = [
        ("Ah", "A♥"),
        ("10s", "T♠"),
        ("5d", "5♦"),
        ("Kc", "K♣"),
        ("Th", "T♥"),
        ("Jd", "J♦"),
        ("Qs", "Q♠"),
    ]
    
    all_passed = True
    for input_str, expected_str in test_cases:
        card = parse_card(input_str)
        if card is None:
            print(f"  ❌ parse_card('{input_str}') returned None")
            all_passed = False
        elif str(card) != expected_str:
            print(f"  ❌ parse_card('{input_str}') = '{card}', expected '{expected_str}'")
            all_passed = False
        else:
            print(f"  ✓ parse_card('{input_str}') = '{card}'")
    
    results.record("Card Parsing", all_passed, 
                   f"{len(test_cases)} card formats tested")


def test_low_card_counting(results: TestResult):
    """Test that low cards (2-6) increase the count."""
    print("\n[TEST] Low Card Counting")
    print("-" * 40)
    
    session = LiveSession()
    low_cards = ['2h', '3d', '4c', '5s', '6h']
    
    print(f"  Initial: RC=0, TC=0.00")
    
    for card_str in low_cards:
        session.input_card(card_str)
    
    metrics = session.get_metrics()
    rc = metrics.running_count
    tc = metrics.true_count
    
    print(f"  After {', '.join(low_cards)}: RC={rc}, TC={tc:+.2f}")
    
    # Low cards are +1 each, so RC should be +5
    passed = rc == 5 and tc > 0
    
    results.record("Low Card Counting", passed,
                   f"RC={rc} (expected 5), TC={tc:+.2f} (expected > 0)")


def test_high_card_counting(results: TestResult):
    """Test that high cards (T-A) decrease the count."""
    print("\n[TEST] High Card Counting")
    print("-" * 40)
    
    session = LiveSession()
    
    # First add low cards
    low_cards = ['2h', '3d', '4c', '5s', '6h']
    for card_str in low_cards:
        session.input_card(card_str)
    
    metrics = session.get_metrics()
    print(f"  After low cards: RC={metrics.running_count}, TC={metrics.true_count:+.2f}")
    
    # Then add high cards (should cancel out)
    high_cards = ['Th', 'Jd', 'Qc', 'Ks', 'Ah']
    for card_str in high_cards:
        session.input_card(card_str)
    
    metrics = session.get_metrics()
    rc = metrics.running_count
    tc = metrics.true_count
    
    print(f"  After high cards: RC={rc}, TC={tc:+.2f}")
    
    # 5 low (+5) + 5 high (-5) = 0
    passed = rc == 0 and abs(tc) < 0.01
    
    results.record("High Card Counting", passed,
                   f"RC={rc} (expected 0), TC={tc:+.2f} (expected 0)")


def test_pair_split_decision(results: TestResult):
    """Test that 8,8 vs 10 returns SPLIT."""
    print("\n[TEST] Pair Split Decision (8,8 vs 10)")
    print("-" * 40)
    
    session = LiveSession()
    session.start_hand('8s 8h', 'Td')
    
    decision = session.get_decision()
    print(f"  Player: 8,8 vs Dealer: 10")
    print(f"  Decision: {decision.name}")
    
    passed = decision == Action.SPLIT
    
    results.record("Pair Split Decision", passed,
                   f"Got {decision.name}, expected SPLIT")


def test_basic_strategy_hit(results: TestResult):
    """Test basic strategy: 16 vs 10 at negative count should HIT."""
    print("\n[TEST] Basic Strategy (16 vs 10 at TC < 0)")
    print("-" * 40)
    
    session = LiveSession()
    
    # Pre-load negative count
    for card_str in ['Th', 'Jd', 'Qc']:
        session.input_card(card_str)
    
    metrics = session.get_metrics()
    print(f"  Pre-loaded negative count: TC={metrics.true_count:+.2f}")
    
    session.start_hand('9s 7h', 'Td')
    
    metrics = session.get_metrics()
    decision = session.get_decision()
    
    print(f"  Player: 9+7=16 vs Dealer: 10")
    print(f"  TC after deal: {metrics.true_count:+.2f}")
    print(f"  Decision: {decision.name}")
    
    # At negative TC, basic strategy says HIT on 16 vs 10
    passed = decision == Action.HIT
    
    results.record("Basic Strategy (HIT 16v10)", passed,
                   f"TC={metrics.true_count:+.2f}, Got {decision.name}, expected HIT")


def test_i18_deviation_stand(results: TestResult):
    """Test I18 deviation: 16 vs 10 at TC >= 0 should STAND."""
    print("\n[TEST] Illustrious 18 Deviation (16 vs 10 at TC >= 0)")
    print("-" * 40)
    
    session = LiveSession()
    
    # Pre-load positive count to ensure TC >= 0 after dealing
    for card_str in ['2h', '3d', '4c']:
        session.input_card(card_str)
    
    metrics = session.get_metrics()
    print(f"  Pre-loaded positive count: TC={metrics.true_count:+.2f}")
    
    session.start_hand('Ts 6h', 'Td')
    
    metrics = session.get_metrics()
    decision = session.get_decision()
    
    print(f"  Player: T+6=16 vs Dealer: 10")
    print(f"  TC after deal: {metrics.true_count:+.2f}")
    print(f"  Decision: {decision.name}")
    
    # At TC >= 0, I18 says STAND on 16 vs 10
    passed = decision == Action.STAND
    
    results.record("I18 Deviation (STAND 16v10)", passed,
                   f"TC={metrics.true_count:+.2f}, Got {decision.name}, expected STAND")


def test_bet_sizing(results: TestResult):
    """Test that bet sizing increases with positive count."""
    print("\n[TEST] Bet Sizing")
    print("-" * 40)
    
    session = LiveSession(bankroll=10000.0)
    
    # Get bet at neutral count
    bet_neutral = session.get_bet()
    print(f"  At TC=0: Recommended bet = ${bet_neutral:.2f}")
    
    # Add low cards to increase count
    for card_str in ['2h', '3d', '4c', '5s', '6h', '2d', '3h', '4s']:
        session.input_card(card_str)
    
    metrics = session.get_metrics()
    bet_positive = session.get_bet()
    
    print(f"  At TC={metrics.true_count:+.2f}: Recommended bet = ${bet_positive:.2f}")
    
    passed = bet_positive > bet_neutral
    
    results.record("Bet Sizing", passed,
                   f"Neutral=${bet_neutral:.0f}, Positive=${bet_positive:.0f}")


def test_session_status(results: TestResult):
    """Test that session status returns all expected fields."""
    print("\n[TEST] Session Status")
    print("-" * 40)
    
    session = LiveSession()
    session.input_card('5h')
    session.start_hand('Ah Kd', 'Ts')
    
    status = session.get_status()
    
    required_fields = [
        'running_count', 'true_count', 'cards_remaining', 'decks_remaining',
        'cards_observed_this_shoe', 'hands_played', 'session_profit',
        'bankroll', 'hand_in_progress', 'recommended_bet'
    ]
    
    missing = [f for f in required_fields if f not in status]
    
    print(f"  Status fields present: {len(status)}")
    for field in required_fields:
        value = status.get(field, "MISSING")
        print(f"    {field}: {value}")
    
    passed = len(missing) == 0
    
    results.record("Session Status", passed,
                   f"All {len(required_fields)} required fields present" if passed 
                   else f"Missing: {missing}")


def test_shoe_reset(results: TestResult):
    """Test that shoe reset clears the count."""
    print("\n[TEST] Shoe Reset")
    print("-" * 40)
    
    session = LiveSession()
    
    # Add some cards
    for card_str in ['2h', '3d', '4c', '5s', '6h']:
        session.input_card(card_str)
    
    metrics = session.get_metrics()
    print(f"  Before reset: RC={metrics.running_count}, TC={metrics.true_count:+.2f}")
    
    # Reset shoe
    session.start_shoe()
    
    metrics = session.get_metrics()
    print(f"  After reset: RC={metrics.running_count}, TC={metrics.true_count:+.2f}")
    
    passed = metrics.running_count == 0 and metrics.true_count == 0
    
    results.record("Shoe Reset", passed,
                   f"RC={metrics.running_count}, TC={metrics.true_count:.2f}")


def main():
    """Run all verification tests."""
    print("\n" + "=" * 70)
    print("     BLACKJACK LIVE INTERFACE VERIFICATION SCRIPT")
    print("=" * 70)
    print("\n  Running automated dry-run tests to verify system functionality...")
    
    results = TestResult()
    
    # Run all tests
    test_card_parsing(results)
    test_low_card_counting(results)
    test_high_card_counting(results)
    test_pair_split_decision(results)
    test_basic_strategy_hit(results)
    test_i18_deviation_stand(results)
    test_bet_sizing(results)
    test_session_status(results)
    test_shoe_reset(results)
    
    # Print summary
    success = results.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
