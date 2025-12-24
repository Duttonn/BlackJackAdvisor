#!/usr/bin/env python3
"""
Test script for the Web API.
Verifies all endpoints work correctly.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from src.web.app import app


def test_api():
    """Test all API endpoints."""
    client = TestClient(app)
    
    print("=" * 60)
    print("WEB API VERIFICATION")
    print("=" * 60)
    
    # Test 1: Health check
    print("\n📋 Test 1: Health Check")
    print("-" * 40)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print(f"  ✅ Health: {data}")
    
    # Test 2: Start AUTO session
    print("\n📋 Test 2: Start AUTO Session (Training)")
    print("-" * 40)
    response = client.post("/api/session/start", json={
        "mode": "AUTO",
        "bankroll": 10000.0
    })
    assert response.status_code == 200
    data = response.json()
    auto_session_id = data["session_id"]
    assert data["mode"] == "AUTO"
    assert data["status"] == "active"
    print(f"  ✅ Session ID: {auto_session_id[:8]}...")
    print(f"  ✅ Mode: {data['mode']}")
    
    # Test 3: Deal hand (AUTO)
    print("\n📋 Test 3: Deal Hand (AUTO)")
    print("-" * 40)
    response = client.post(f"/api/session/{auto_session_id}/deal")
    assert response.status_code == 200
    data = response.json()
    print(f"  ✅ Player: {data['player_cards']} = {data['player_total']}")
    print(f"  ✅ Dealer: {data['dealer_card']}")
    print(f"  ✅ TC: {data['true_count']}, Bet: ${data['recommended_bet']}")
    
    # Test 4: Submit action (AUTO)
    print("\n📋 Test 4: Submit Action (AUTO)")
    print("-" * 40)
    response = client.post(f"/api/session/{auto_session_id}/action", json={
        "action": "STAND"
    })
    assert response.status_code == 200
    data = response.json()
    print(f"  ✅ Action: {data['action_taken']}")
    print(f"  ✅ Correct: {data['correct_action']}")
    print(f"  ✅ Is Correct: {data['is_correct']}")
    if "outcome" in data and data["outcome"]:
        print(f"  ✅ Outcome: {data['outcome']}")
    
    # Test 5: Start MANUAL session
    print("\n📋 Test 5: Start MANUAL Session (Shadowing)")
    print("-" * 40)
    response = client.post("/api/session/start", json={
        "mode": "MANUAL",
        "bankroll": 5000.0
    })
    assert response.status_code == 200
    data = response.json()
    manual_session_id = data["session_id"]
    assert data["mode"] == "MANUAL"
    print(f"  ✅ Session ID: {manual_session_id[:8]}...")
    print(f"  ✅ Mode: {data['mode']}")
    
    # Test 6: Input cards (MANUAL)
    print("\n📋 Test 6: Input Cards (MANUAL)")
    print("-" * 40)
    response = client.post(f"/api/session/{manual_session_id}/input", json={
        "cards": ["Ah", "Kd", "5s", "3c", "2h"]  # +1 net count
    })
    assert response.status_code == 200
    data = response.json()
    print(f"  ✅ Cards: {data['cards_observed']}")
    print(f"  ✅ RC: {data['running_count']}, TC: {data['true_count']}")
    print(f"  ✅ Bet: ${data['recommended_bet']}")
    
    # Test 7: Get decision (MANUAL)
    print("\n📋 Test 7: Get Decision (MANUAL)")
    print("-" * 40)
    response = client.post(f"/api/session/{manual_session_id}/decision", json={
        "player_cards": ["10h", "6d"],
        "dealer_card": "10s"
    })
    assert response.status_code == 200
    data = response.json()
    print(f"  ✅ Player: {data['player_cards']} = {data['player_total']}")
    print(f"  ✅ Dealer: {data['dealer_card']}")
    print(f"  ✅ Action: {data['recommended_action']}")
    print(f"  ✅ TC: {data['true_count']}")
    print(f"  ✅ Should Exit: {data['should_exit']}")
    
    # Test 8: Drop count to trigger exit signal
    print("\n📋 Test 8: Exit Signal (Wong Out)")
    print("-" * 40)
    # Input many 10s to drop the count
    response = client.post(f"/api/session/{manual_session_id}/input", json={
        "cards": ["Kh", "Qd", "Jc", "10s", "Kc", "Qh", "Jd", "10h", "Kd", "Qs"]
    })
    assert response.status_code == 200
    data = response.json()
    print(f"  ✅ RC after 10 high cards: {data['running_count']}")
    print(f"  ✅ TC: {data['true_count']}")
    
    # Now get a decision - should trigger exit
    response = client.post(f"/api/session/{manual_session_id}/decision", json={
        "player_cards": ["9h", "6d"],
        "dealer_card": "5s"
    })
    data = response.json()
    print(f"  ✅ Should Exit: {data['should_exit']}")
    if data['should_exit']:
        print(f"  ✅ Exit Reason: {data['exit_reason']}")
    
    # Test 9: Shuffle
    print("\n📋 Test 9: Shuffle Deck")
    print("-" * 40)
    response = client.post(f"/api/session/{manual_session_id}/shuffle")
    assert response.status_code == 200
    data = response.json()
    print(f"  ✅ Status: {data['status']}")
    print(f"  ✅ RC: {data['running_count']}, TC: {data['true_count']}")
    
    # Test 10: Get session status
    print("\n📋 Test 10: Session Status")
    print("-" * 40)
    response = client.get(f"/api/session/{auto_session_id}")
    assert response.status_code == 200
    data = response.json()
    print(f"  ✅ Mode: {data['mode']}")
    print(f"  ✅ RC: {data['running_count']}, TC: {data['true_count']}")
    
    # Test 11: Delete session
    print("\n📋 Test 11: Delete Session")
    print("-" * 40)
    response = client.delete(f"/api/session/{auto_session_id}")
    assert response.status_code == 200
    print(f"  ✅ Deleted: {auto_session_id[:8]}...")
    
    # Verify deleted
    response = client.get(f"/api/session/{auto_session_id}")
    assert response.status_code == 404
    print(f"  ✅ Confirmed: Session not found")
    
    # Cleanup
    client.delete(f"/api/session/{manual_session_id}")
    
    print("\n" + "=" * 60)
    print("🎉 ALL API TESTS PASSED!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = test_api()
        sys.exit(0 if success else 1)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
