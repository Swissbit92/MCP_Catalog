#!/usr/bin/env python3
"""
End-to-end test for MongoDB persona flavor implementation.
Tests that Eeva's responses to MongoDB queries include persona flavor.
"""

import requests
import json
import time

BACKEND_URL = "http://127.0.0.1:8000"

def test_mongodb_persona_flavor():
    """Test that MongoDB responses include Eeva's persona flavor."""

    print("=" * 80)
    print("MongoDB Persona Flavor - End-to-End Test")
    print("=" * 80)
    print()

    # Check backend is running
    print("[1/4] Checking backend connectivity...")
    try:
        response = requests.get(f"{BACKEND_URL}/personas", timeout=5)
        if response.status_code != 200:
            print(f"[FAIL] Backend not responding (status: {response.status_code})")
            return False
        print("[PASS] Backend is running")
        print()
    except requests.exceptions.RequestException as e:
        print(f"[FAIL] Cannot connect to backend: {e}")
        print()
        print("Please start the backend:")
        print("  python run_react.py")
        print()
        return False

    # Verify Eeva is available and has Epic/Legendary rarity
    print("[2/4] Checking Eeva persona availability...")
    personas = response.json()
    eeva = next((p for p in personas if p.get("key") == "Eeva"), None)

    if not eeva:
        print("[FAIL] Eeva persona not found")
        return False

    rarity = eeva.get("rarity", "").lower()
    if rarity not in ["epic", "legendary"]:
        print(f"[FAIL] Eeva must be Epic or Legendary for MongoDB access (current: {rarity})")
        return False

    print(f"[PASS] Eeva found (rarity: {rarity})")
    print()

    # Test MongoDB query
    print("[3/4] Sending MongoDB query to Eeva...")
    print("Query: 'What's the current Bitcoin price?'")
    print()

    chat_request = {
        "persona": "Eeva",
        "message": "What's the current Bitcoin price?"
    }

    try:
        start_time = time.time()
        response = requests.post(
            f"{BACKEND_URL}/persona/chat",
            json=chat_request,
            timeout=30
        )
        elapsed = time.time() - start_time

        if response.status_code != 200:
            print(f"[FAIL] Chat request failed (status: {response.status_code})")
            print(f"Response: {response.text}")
            return False

        result = response.json()
        answer = result.get("answer", "")
        metadata = result.get("metadata", {})

        print(f"[PASS] Received response in {elapsed:.2f}s")
        print()

    except requests.exceptions.RequestException as e:
        print(f"[FAIL] Chat request failed: {e}")
        return False

    # Analyze response for persona flavor
    print("[4/4] Analyzing response for persona flavor...")
    print()
    print("-" * 80)
    print("RESPONSE:")
    print("-" * 80)
    print(answer)
    print("-" * 80)
    print()

    # Check metadata
    print("Metadata:")
    print(f"  Source: {metadata.get('source_type')}")
    print(f"  Tools used: {metadata.get('tools_used')}")
    print(f"  Cache status: {metadata.get('cache_status')}")
    print()

    # Persona flavor checks
    print("Persona Flavor Analysis:")
    print()

    checks = {
        "MongoDB source": metadata.get('source_type') == 'mongodb_mcp',
        "Non-empty response": len(answer) > 0,
        "Contains price data": '$' in answer or 'price' in answer.lower(),
        "Not robotic (>50 chars)": len(answer) > 50,
    }

    # Eeva-specific flavor checks
    eeva_indicators = {
        "Casual language": any(word in answer.lower() for word in [
            "sitting at", "right now", "honestly", "pretty", "look",
            "watch for", "I'd", "make"
        ]),
        "Interpretation provided": any(phrase in answer.lower() for phrase in [
            "means", "suggests", "indicates", "territory", "momentum",
            "neutral", "bullish", "bearish", "calm", "shift"
        ]),
        "Personal voice (I/my)": any(word in answer for word in ["I", "my", "I'm", "I'd"]),
        "Not data dump": not answer.startswith("Bitcoin price is $") and "RSI:" not in answer,
    }

    # Combine all checks
    all_checks = {**checks, **eeva_indicators}

    passed_checks = 0
    total_checks = len(all_checks)

    for check_name, check_result in all_checks.items():
        status = "[PASS]" if check_result else "[FAIL]"
        print(f"  {status} {check_name}")
        if check_result:
            passed_checks += 1

    print()

    # Calculate score
    score = (passed_checks / total_checks) * 100

    print("=" * 80)
    print(f"PERSONA FLAVOR SCORE: {passed_checks}/{total_checks} ({score:.0f}%)")
    print("=" * 80)
    print()

    if score >= 75:
        print("[SUCCESS] Response has strong persona flavor!")
        print()
        print("Expected characteristics present:")
        if all_checks.get("Casual language"):
            print("  - Casual, conversational tone")
        if all_checks.get("Interpretation provided"):
            print("  - Technical interpretation, not just raw data")
        if all_checks.get("Personal voice (I/my)"):
            print("  - First-person voice (I/my)")
        if all_checks.get("Not data dump"):
            print("  - Natural synthesis, not robotic data dump")
        print()
        return True

    elif score >= 50:
        print("[PARTIAL] Response has some persona flavor, but could be stronger")
        print()
        print("Missing characteristics:")
        for check_name, check_result in eeva_indicators.items():
            if not check_result:
                print(f"  - {check_name}")
        print()
        print("The synthesis prompt may need tuning or LLM may need higher temperature.")
        return True

    else:
        print("[FAIL] Response lacks persona flavor (emotionless data dump)")
        print()
        print("This suggests the synthesis prompt is not being applied.")
        print("Check backend logs for '[MongoDB Synthesis]' entries.")
        return False


def compare_with_brave():
    """Optional: Compare MongoDB response with Brave search response."""
    print()
    print("=" * 80)
    print("Optional: Comparing MongoDB vs Brave Search Persona Flavor")
    print("=" * 80)
    print()

    print("Testing Brave search query with Eeva...")
    print("Query: 'What happened in the 2024 US election?'")
    print()

    try:
        response = requests.post(
            f"{BACKEND_URL}/persona/chat",
            json={
                "persona": "Eeva",
                "message": "What happened in the 2024 US election?"
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            answer = result.get("answer", "")

            print("-" * 80)
            print("BRAVE SEARCH RESPONSE:")
            print("-" * 80)
            print(answer[:500] + "..." if len(answer) > 500 else answer)
            print("-" * 80)
            print()

            has_citations = "Sources:" in answer or "🔍" in answer
            print(f"Brave response has citations: {has_citations}")
            print(f"Brave response length: {len(answer)} chars")
            print()

            print("Both responses should have similar persona flavor now!")
        else:
            print(f"Brave query failed (status: {response.status_code})")

    except Exception as e:
        print(f"Brave comparison skipped: {e}")


if __name__ == "__main__":
    success = test_mongodb_persona_flavor()

    # Optional comparison
    try:
        compare_with_brave()
    except:
        pass

    print()
    print("=" * 80)
    if success:
        print("[COMPLETE] MongoDB Persona Flavor Test: PASSED")
    else:
        print("[COMPLETE] MongoDB Persona Flavor Test: FAILED")
    print("=" * 80)

    exit(0 if success else 1)
