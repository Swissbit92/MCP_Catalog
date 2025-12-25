#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Live test for Phase 2 multi-message conversational behavior.

Tests:
1. Multi-message response parsing
2. Message flow detection
3. Question distribution across messages
4. Staggered rendering metadata
"""

import sys
import io
import requests
import json
import time
from datetime import datetime

# Fix Windows encoding issues
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BACKEND_URL = "http://127.0.0.1:8000"

def test_multi_message_behavior():
    """Test multi-message responses with Gojo (now common rarity)."""
    print("\n" + "="*70)
    print("Phase 2 Multi-Message Live Test")
    print("="*70)

    # 1. Create a new session with Gojo
    print("\n[1/4] Creating new session with Gojo...")
    session_response = requests.post(
        f"{BACKEND_URL}/sessions",
        json={"persona_key": "Gojo", "title": "Phase 2 Live Test"}
    )

    if session_response.status_code != 200:
        print(f"❌ Failed to create session: {session_response.status_code}")
        print(session_response.text)
        return False

    session = session_response.json()
    session_id = session["id"]
    print(f"✅ Session created: {session_id}")

    # 2. Send a message that should trigger multi-message response
    print("\n[2/4] Sending message to trigger multi-message response...")
    test_message = "I'm new to Bitcoin. Can you help me understand the basics?"

    chat_response = requests.post(
        f"{BACKEND_URL}/sessions/{session_id}/chat",
        json={"message": test_message}
    )

    if chat_response.status_code != 200:
        print(f"❌ Failed to send message: {chat_response.status_code}")
        print(chat_response.text)
        return False

    response_data = chat_response.json()
    print(f"✅ Received response")

    # 3. Analyze response structure
    print("\n[3/4] Analyzing response structure...")
    print(f"\nResponse keys: {list(response_data.keys())}")

    # Check message_flow
    message_flow = response_data.get("message_flow", "single")
    print(f"\n📊 Message Flow: {message_flow}")

    # Check answer format
    answer = response_data.get("answer")
    is_multi = isinstance(answer, list)

    print(f"\n📝 Answer Format:")
    print(f"   - Type: {'List (multi-message)' if is_multi else 'String (single message)'}")

    if is_multi:
        print(f"   - Message count: {len(answer)}")
        print(f"\n   Messages:")
        for i, msg in enumerate(answer, 1):
            preview = msg[:60] + "..." if len(msg) > 60 else msg
            print(f"      {i}. {preview}")
    else:
        preview = answer[:100] + "..." if len(answer) > 100 else answer
        print(f"   - Content: {preview}")

    # Check metadata
    metadata = response_data.get("metadata", {})
    print(f"\n🔍 Metadata:")
    print(f"   - is_multi_message: {metadata.get('is_multi_message', False)}")
    print(f"   - message_count: {metadata.get('message_count', 1)}")

    # 4. Validation
    print("\n[4/4] Validation...")

    validations = []

    # Test 1: message_flow matches answer type
    flow_matches = (message_flow == "multi" and is_multi) or (message_flow == "single" and not is_multi)
    validations.append(("message_flow matches answer type", flow_matches))

    # Test 2: metadata matches answer type
    metadata_matches = metadata.get("is_multi_message", False) == is_multi
    validations.append(("metadata is_multi_message matches", metadata_matches))

    # Test 3: message_count is correct
    expected_count = len(answer) if is_multi else 1
    count_correct = metadata.get("message_count", 1) == expected_count
    validations.append(("message_count is correct", count_correct))

    # Test 4: Messages are concise if multi-message
    if is_multi:
        avg_length = sum(len(msg) for msg in answer) / len(answer)
        concise = avg_length < 300  # Target is ~150-200 chars
        validations.append(("messages are concise (avg < 300 chars)", concise))
        print(f"   - Average message length: {avg_length:.0f} chars")

    # Test 5: Contains questions (conversational engagement)
    has_questions = any("?" in (msg if isinstance(msg, str) else str(msg)) for msg in ([answer] if not is_multi else answer))
    validations.append(("response contains questions", has_questions))

    # Print results
    print("\n" + "="*70)
    print("VALIDATION RESULTS")
    print("="*70)

    for test_name, passed in validations:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    # Summary
    passed_count = sum(1 for _, p in validations if p)
    total_count = len(validations)

    print(f"\n{'='*70}")
    print(f"SUMMARY: {passed_count}/{total_count} tests passed")
    print("="*70)

    # Display full response if multi-message
    if is_multi and message_flow == "multi":
        print(f"\n{'='*70}")
        print("FULL MULTI-MESSAGE RESPONSE")
        print("="*70)
        for i, msg in enumerate(answer, 1):
            print(f"\n[Message {i}/{len(answer)}]")
            print(msg)

    return passed_count == total_count

if __name__ == "__main__":
    try:
        success = test_multi_message_behavior()
        exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to backend at http://127.0.0.1:8000")
        print("Make sure the backend is running:")
        print("   python run_react.py")
        print("   OR")
        print("   uvicorn src.coordinator.server:app --reload --port 8000")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
