#!/usr/bin/env python3
"""
Debug script to verify wonging (table hopping) logic is working correctly.

Expected behavior:
1. When TC drops below threshold, player "hops" to fresh table
2. After hop: TC = 0.0, shoe = full deck
3. EV should be POSITIVE (> +0.5%) with proper wonging

Author: Copilot
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from interfaces.simulator import BlackjackSimulator, SimulatorConfig


def run_wonging_verification():
    """Verify wonging produces expected behavior."""
    
    print("=" * 60)
    print("WONGING DEBUG VERIFICATION")
    print("=" * 60)
    
    # Test 1: Baseline (no wonging)
    print("\n📊 TEST 1: Baseline (No Wonging)")
    print("-" * 40)
    
    baseline_config = SimulatorConfig(
        use_counting=True,
        betting_strategy="KELLY",
        use_deviations=True,
        wong_out_threshold=None,  # No wonging
    )
    
    sim_baseline = BlackjackSimulator(config=baseline_config)
    result_baseline = sim_baseline.run(num_hands=50000)
    
    ev_baseline = result_baseline.ev_percent
    print(f"  Hands Played: {result_baseline.hands_played:,}")
    print(f"  Hands Skipped: {result_baseline.hands_skipped:,}")
    print(f"  EV: {ev_baseline:+.3f}%")
    
    # Test 2: Wonging enabled (wong out at TC < +1)
    print("\n📊 TEST 2: Wonging Enabled (Wong Out at TC < +1)")
    print("-" * 40)
    
    wong_config = SimulatorConfig(
        use_counting=True,
        betting_strategy="KELLY",
        use_deviations=True,
        wong_out_threshold=1.0,  # Exit when TC drops below +1
        min_hands_per_shoe=5,    # Play at least 5 hands before exiting
    )
    
    sim_wong = BlackjackSimulator(config=wong_config)
    result_wong = sim_wong.run(num_hands=50000)
    
    ev_wong = result_wong.ev_percent
    print(f"  Hands Played: {result_wong.hands_played:,}")
    print(f"  Table Hops: {result_wong.hands_skipped:,}")
    print(f"  EV: {ev_wong:+.3f}%")
    
    # Test 3: Aggressive wonging (wong out at TC < +2)
    print("\n📊 TEST 3: Aggressive Wonging (Wong Out at TC < +2)")
    print("-" * 40)
    
    aggressive_config = SimulatorConfig(
        use_counting=True,
        betting_strategy="KELLY",
        use_deviations=True,
        wong_out_threshold=2.0,  # Exit when TC drops below +2
        min_hands_per_shoe=3,    # Play fewer hands before exiting
    )
    
    sim_aggressive = BlackjackSimulator(config=aggressive_config)
    result_aggressive = sim_aggressive.run(num_hands=50000)
    
    ev_aggressive = result_aggressive.ev_percent
    print(f"  Hands Played: {result_aggressive.hands_played:,}")
    print(f"  Table Hops: {result_aggressive.hands_skipped:,}")
    print(f"  EV: {ev_aggressive:+.3f}%")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Configuration':<30} {'EV':>10} {'Table Hops':>12}")
    print("-" * 60)
    print(f"{'Baseline (No Wonging)':<30} {ev_baseline:>+9.3f}% {result_baseline.hands_skipped:>12,}")
    print(f"{'Wonging TC<+1':<30} {ev_wong:>+9.3f}% {result_wong.hands_skipped:>12,}")
    print(f"{'Aggressive TC<+2':<30} {ev_aggressive:>+9.3f}% {result_aggressive.hands_skipped:>12,}")
    
    # Validation
    print("\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)
    
    passed = True
    
    # Check 1: Wonging should improve EV over baseline
    if ev_wong > ev_baseline:
        print("✅ Wonging TC<+1 improves EV over baseline")
    else:
        print(f"❌ FAIL: Wonging EV ({ev_wong:+.3f}%) should exceed baseline ({ev_baseline:+.3f}%)")
        passed = False
    
    # Check 2: Aggressive wonging should improve EV even more
    if ev_aggressive > ev_wong:
        print("✅ Aggressive wonging (TC<+2) improves EV over standard wonging")
    else:
        # This is OK - more aggressive isn't always better due to variance
        print(f"⚠️  Aggressive wonging ({ev_aggressive:+.3f}%) not better than standard ({ev_wong:+.3f}%)")
    
    # Check 3: Table hops should be positive
    if result_wong.hands_skipped > 0:
        print(f"✅ Table hops recorded: {result_wong.hands_skipped:,}")
    else:
        print("❌ FAIL: No table hops recorded")
        passed = False
    
    # Check 4: Wonging EV should be positive
    if ev_wong > 0:
        print(f"✅ Wonging EV is positive: {ev_wong:+.3f}%")
    else:
        print(f"❌ FAIL: Wonging EV should be positive, got {ev_wong:+.3f}%")
        passed = False
    
    print()
    if passed:
        print("🎉 ALL CRITICAL CHECKS PASSED - Wonging logic is working!")
    else:
        print("⚠️  SOME CHECKS FAILED - Review wonging implementation")
    
    return passed


if __name__ == "__main__":
    success = run_wonging_verification()
    sys.exit(0 if success else 1)
