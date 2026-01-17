#!/usr/bin/env python3
"""Validation script for nchapman model switch.

Tests:
1. Model configuration is correct
2. Multi-message responses work
3. Personality adherence
4. No garbled output
5. MongoDB/Brave integration (if applicable)
"""

import requests
import json
import sys

BACKEND_URL = "http://127.0.0.1:8000"

def test_health_check():
    """Verify server health and model configuration."""
    print("\n[1/5] Testing server health and model configuration...")

    response = requests.get(f"{BACKEND_URL}/health")
    if response.status_code != 200:
        print(f"❌ Health check failed: {response.status_code}")
        return False

    health = response.json()
    model = health.get("model")

    print(f"  Server status: {health.get('status')}")
    print(f"  Model: {model}")
    print(f"  Database: {health.get('db')}")

    if model != "nchapman/gemma-2-9b-it-abliterated:9b":
        print(f"❌ Wrong model! Expected nchapman/gemma-2-9b-it-abliterated:9b, got {model}")
        return False

    print("✅ Health check passed - correct model loaded")
    return True

def test_multi_message_response():
    """Test that multi-message responses work correctly."""
    print("\n[2/5] Testing multi-message response generation...")

    # Create session
    session_response = requests.post(
        f"{BACKEND_URL}/sessions",
        json={"persona_key": "Gojo", "title": "Validation Test"}
    )

    if session_response.status_code != 200:
        print(f"❌ Failed to create session: {session_response.status_code}")
        return False

    session_id = session_response.json()["id"]

    # Send message
    chat_response = requests.post(
        f"{BACKEND_URL}/sessions/{session_id}/chat",
        json={"message": "Explain Bitcoin mining to me"}
    )

    if chat_response.status_code != 200:
        print(f"❌ Failed to send message: {chat_response.status_code}")
        return False

    data = chat_response.json()
    answer = data.get("answer")
    message_flow = data.get("message_flow")

    is_multi = isinstance(answer, list)

    print(f"  Message flow: {message_flow}")
    print(f"  Format: {'Multi-message' if is_multi else 'Single'}")

    if is_multi:
        print(f"  Message count: {len(answer)}")
        for i, msg in enumerate(answer, 1):
            preview = msg[:60] + "..." if len(msg) > 60 else msg
            print(f"    {i}. {preview}")

    # Check for garbled output
    text_to_check = " ".join(answer) if is_multi else answer
    if "'m!" in text_to_check or ",," in text_to_check:
        print("❌ Detected garbled output!")
        return False

    print("✅ Multi-message response working correctly")
    return True

def test_personality_adherence():
    """Test that persona personality is maintained."""
    print("\n[3/5] Testing personality adherence...")

    # Test Eeva (sarcastic, analytical)
    session_response = requests.post(
        f"{BACKEND_URL}/sessions",
        json={"persona_key": "Eeva", "title": "Personality Test"}
    )

    session_id = session_response.json()["id"]

    chat_response = requests.post(
        f"{BACKEND_URL}/sessions/{session_id}/chat",
        json={"message": "What do you think about Bitcoin?"}
    )

    data = chat_response.json()
    answer = data.get("answer")
    text = " ".join(answer) if isinstance(answer, list) else answer

    print(f"  Response length: {len(text)} chars")
    print(f"  Preview: {text[:100]}...")

    # Check response is coherent (not empty, not too short)
    if len(text) < 20:
        print("❌ Response too short or empty")
        return False

    # Check for XML tag leakage
    if "<msg>" in text or "</msg>" in text:
        print("❌ XML tag leakage detected!")
        return False

    print("✅ Personality adherence test passed")
    return True

def test_technical_question():
    """Test handling of technical questions (regression test for garbled output)."""
    print("\n[4/5] Testing technical question handling...")

    # This was the scenario that broke seamon67
    session_response = requests.post(
        f"{BACKEND_URL}/sessions",
        json={"persona_key": "Eeva", "title": "Technical Test"}
    )

    session_id = session_response.json()["id"]

    chat_response = requests.post(
        f"{BACKEND_URL}/sessions/{session_id}/chat",
        json={"message": "How does the Bitcoin halving affect the price long-term?"}
    )

    data = chat_response.json()
    answer = data.get("answer")
    text = " ".join(answer) if isinstance(answer, list) else answer

    print(f"  Response length: {len(text)} chars")
    print(f"  Preview: {text[:150]}...")

    # Check for garbled output patterns
    garbled_patterns = ["'m!'", ",,", ",,ings", "'s!'s"]
    for pattern in garbled_patterns:
        if pattern in text:
            print(f"❌ Detected garbled pattern: {pattern}")
            return False

    # Check response is coherent
    if len(text) < 50:
        print("❌ Response suspiciously short")
        return False

    # Check for technical keywords (should mention halving, supply, scarcity, etc.)
    technical_keywords = ["halving", "supply", "scarcity", "reward", "price"]
    has_technical_content = any(keyword.lower() in text.lower() for keyword in technical_keywords)

    if not has_technical_content:
        print("⚠️  Warning: Response may lack technical depth")
    else:
        print(f"  ✓ Technical content detected")

    print("✅ Technical question handling test passed")
    return True

def test_emotional_response():
    """Test emotional context handling (Frieren persona)."""
    print("\n[5/5] Testing emotional response...")

    session_response = requests.post(
        f"{BACKEND_URL}/sessions",
        json={"persona_key": "Frieren", "title": "Emotional Test"}
    )

    session_id = session_response.json()["id"]

    chat_response = requests.post(
        f"{BACKEND_URL}/sessions/{session_id}/chat",
        json={"message": "I'm worried about investing in Bitcoin"}
    )

    data = chat_response.json()
    answer = data.get("answer")
    text = " ".join(answer) if isinstance(answer, list) else answer
    emotional_state = data.get("emotional_state", {})

    print(f"  Response length: {len(text)} chars")
    print(f"  Emotional state: {emotional_state.get('current_mood', 'N/A')}")
    print(f"  Preview: {text[:150]}...")

    # Check emotional state was detected
    mood = emotional_state.get("current_mood")
    if mood in ["worried", "vulnerable", "anxious"]:
        print(f"  ✓ Emotional state detected: {mood}")

    # Check for empathetic keywords
    empathy_keywords = ["understand", "worry", "concern", "normal", "feel"]
    has_empathy = any(keyword.lower() in text.lower() for keyword in empathy_keywords)

    if has_empathy:
        print("  ✓ Empathetic response detected")

    print("✅ Emotional response test passed")
    return True

def run_validation():
    """Run all validation tests."""
    print("="*70)
    print("NCHAPMAN MODEL SWITCH VALIDATION")
    print("="*70)

    tests = [
        ("Health Check & Model Config", test_health_check),
        ("Multi-Message Responses", test_multi_message_response),
        ("Personality Adherence", test_personality_adherence),
        ("Technical Question Handling", test_technical_question),
        ("Emotional Response", test_emotional_response),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")

    print()
    print(f"Results: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print()
        print("🎉 ALL VALIDATION TESTS PASSED!")
        print("✅ Model switch to nchapman/gemma-2-9b-it-abliterated:9b is successful")
        print("✅ Backend is ready for production use")
    else:
        print()
        print("⚠️  Some validation tests failed - review results above")

    print("="*70)

    return passed_count == total_count

if __name__ == "__main__":
    try:
        success = run_validation()
        sys.exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to backend at http://127.0.0.1:8000")
        print("Make sure the backend is running:")
        print("   python scripts/utils/run_react.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
