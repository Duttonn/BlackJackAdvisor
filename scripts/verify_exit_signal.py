#!/usr/bin/env python3
"""
Verify Exit Signal functionality in LiveSession.

Tests that the LiveDecision returns should_exit=True when:
1. True Count drops below -1.0
2. At least one hand has been played this shoe (cover)

Author: Copilot
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from interfaces.live_api import LiveSession, LiveDecision
from src.core import Rank


def test_exit_signal():
    """Test that exit signal fires correctly."""
    
    print("=" * 60)
    print("EXIT SIGNAL VERIFICATION")
    print("=" * 60)
    
    session = LiveSession()
    session.start_shoe()
    
    # Step 1: Play one hand first (to meet cover requirement)
    print("\n📋 Step 1: Play first hand (establish cover)")
    print("-" * 40)
    
    # Start a hand with any cards
    session.start_hand("8h,7d", "6s")  # Player 15 vs 6
    decision = session.get_decision()
    
    print(f"  Player: 8♥ 7♦ = 15 vs Dealer: 6♠")
    print(f"  Decision: {decision.action.name}")
    print(f"  Should Exit: {decision.should_exit}")
    print(f"  Hands This Shoe: {session._session.hands_played_this_shoe}")
    
    # End the hand
    session.end_hand(result=10.0)
    print(f"  ✓ Hand ended. Hands this shoe: {session._session.hands_played_this_shoe}")
    
    # Step 2: Drop the count by observing high cards (10s)
    print("\n📋 Step 2: Drop the count (observe ten 10-value cards)")
    print("-" * 40)
    
    metrics_before = session.get_metrics()
    print(f"  TC Before: {metrics_before.true_count:+.2f}")
    
    # Observe 10 high cards (10, J, Q, K = -1 each)
    for i in range(10):
        session.input_card(f"{['10', 'J', 'Q', 'K'][i % 4]}h")
    
    metrics_after = session.get_metrics()
    print(f"  TC After:  {metrics_after.true_count:+.2f}")
    
    # Step 3: Start another hand and check for exit signal
    print("\n📋 Step 3: Request decision (expect exit signal)")
    print("-" * 40)
    
    session.start_hand("9h,6d", "5s")  # Player 15 vs 5
    decision = session.get_decision()
    
    print(f"  Player: 9♥ 6♦ = 15 vs Dealer: 5♠")
    print(f"  Decision: {decision.action.name}")
    print(f"  True Count: {metrics_after.true_count:+.2f}")
    print(f"  Should Exit: {decision.should_exit}")
    print(f"  Exit Reason: {decision.exit_reason}")
    
    # Validation
    print("\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)
    
    passed = True
    
    # Check 1: TC should be below -1.0
    if metrics_after.true_count < -1.0:
        print(f"✅ True Count is below -1.0: {metrics_after.true_count:+.2f}")
    else:
        print(f"❌ FAIL: True Count should be below -1.0, got {metrics_after.true_count:+.2f}")
        passed = False
    
    # Check 2: should_exit should be True
    if decision.should_exit:
        print("✅ should_exit is True")
    else:
        print("❌ FAIL: should_exit should be True")
        passed = False
    
    # Check 3: exit_reason should be set
    if decision.exit_reason:
        print(f"✅ exit_reason is set: '{decision.exit_reason}'")
    else:
        print("❌ FAIL: exit_reason should not be empty")
        passed = False
    
    # Check 4: Verify cover requirement (shouldn't exit on first hand)
    print("\n📋 Bonus Check: Cover requirement (no exit on first hand)")
    print("-" * 40)
    
    # Start fresh shoe
    session.start_shoe()
    
    # Drop count immediately
    for i in range(10):
        session.input_card(f"{['10', 'J', 'Q', 'K'][i % 4]}s")
    
    # Request decision on FIRST hand
    session.start_hand("5h,4d", "10c")
    first_decision = session.get_decision()
    
    metrics_fresh = session.get_metrics()
    print(f"  TC: {metrics_fresh.true_count:+.2f}")
    print(f"  Hands This Shoe: {session._session.hands_played_this_shoe}")
    print(f"  Should Exit: {first_decision.should_exit}")
    
    if not first_decision.should_exit:
        print("✅ Correctly NOT exiting on first hand (cover)")
    else:
        print("❌ FAIL: Should NOT exit on first hand (cover requirement)")
        passed = False
    
    print()
    if passed:
        print("🎉 ALL CHECKS PASSED - Exit Signal working correctly!")
    else:
        print("⚠️  SOME CHECKS FAILED - Review implementation")
    
    return passed


if __name__ == "__main__":
    success = test_exit_signal()
    sys.exit(0 if success else 1)
