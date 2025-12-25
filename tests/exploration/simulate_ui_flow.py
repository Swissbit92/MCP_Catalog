#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simulate the UI flow for multi-message testing.

This script mimics what the React frontend does:
1. Create a session
2. Send a message
3. Parse the response
4. Display messages with staggered delays (simulated)
"""

import sys
import io
import requests
import json
import time
from datetime import datetime

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BACKEND_URL = "http://127.0.0.1:8000"

def simulate_typing_indicator(duration=1.2):
    """Simulate the typing indicator shown in UI."""
    print("   [Typing...]", end="", flush=True)
    time.sleep(duration)
    print("\r" + " " * 20 + "\r", end="", flush=True)

def display_message(content, index, total, is_user=False):
    """Display a message bubble like the UI does."""
    role = "YOU" if is_user else "PERSONA"
    prefix = "🙋" if is_user else "🤖"

    print(f"\n{prefix} {role}:")
    print(f"   {content}")

    if not is_user and index < total:
        print(f"   [{index}/{total}]")

def test_ui_flow():
    """Simulate complete UI interaction flow."""

    print("="*70)
    print("SIMULATING UI MULTI-MESSAGE FLOW")
    print("="*70)

    # Step 1: Create session (like PersonaContext.createNewSession)
    print("\n[1/5] Creating session...")
    session_resp = requests.post(
        f"{BACKEND_URL}/sessions",
        json={"persona_key": "Eeva", "title": "UI Flow Test"}
    )

    if session_resp.status_code != 200:
        print(f"❌ Failed to create session: {session_resp.status_code}")
        return False

    session = session_resp.json()
    session_id = session["id"]
    print(f"✅ Session created: {session_id}")

    # Step 2: User types and sends message (like PersonaContext.sendMessage)
    test_message = "I just bought my first Bitcoin! I'm excited but nervous. What should I do next?"

    print(f"\n[2/5] Sending message...")
    display_message(test_message, 1, 1, is_user=True)

    # Step 3: Show search/typing indicator while waiting
    print(f"\n[3/5] Waiting for response...")
    simulate_typing_indicator(1.5)

    # Step 4: Send request (API call)
    start_time = time.time()
    chat_resp = requests.post(
        f"{BACKEND_URL}/sessions/{session_id}/chat",
        json={"message": test_message}
    )
    response_time = time.time() - start_time

    if chat_resp.status_code != 200:
        print(f"❌ Failed to send message: {chat_resp.status_code}")
        return False

    data = chat_resp.json()

    # Step 5: Parse response (like PersonaContext processes response)
    print(f"\n[4/5] Received response ({response_time:.2f}s)")

    message_flow = data.get("message_flow", "single")
    answer = data.get("answer")
    is_multi = isinstance(answer, list)
    metadata = data.get("metadata", {})

    print(f"\n📊 Response Analysis:")
    print(f"   - Flow type: {message_flow}")
    print(f"   - Is multi-message: {is_multi}")
    print(f"   - Message count: {metadata.get('message_count', 1)}")

    # Step 6: Render messages with staggered delays (like UI does)
    print(f"\n[5/5] Rendering messages with UI-like delays...")
    print("\n" + "="*70)

    if is_multi:
        print(f"MULTI-MESSAGE RESPONSE ({len(answer)} messages)")
        print("="*70)

        # Render each message with delay (PersonaContext.tsx lines 246-269)
        for i, message_content in enumerate(answer):
            # Show typing indicator before each message (except first)
            if i > 0:
                time.sleep(0.3)  # Small delay
                simulate_typing_indicator(1.2)  # Thinking time

            # Display the message
            display_message(message_content, i + 1, len(answer))

            # Auto-scroll simulation
            if i < len(answer) - 1:
                print("   [Auto-scrolling...]")

        print("\n" + "="*70)
        print(f"✅ All {len(answer)} messages displayed")
        print("="*70)

    else:
        print("SINGLE MESSAGE RESPONSE")
        print("="*70)
        display_message(answer, 1, 1)
        print("\n" + "="*70)
        print("✅ Message displayed")
        print("="*70)

    # Show metadata details
    print(f"\n📋 Response Metadata:")
    print(f"   - Source type: {metadata.get('source_type', 'llm')}")
    print(f"   - Is multi-message: {metadata.get('is_multi_message', False)}")
    print(f"   - Message count: {metadata.get('message_count', 1)}")
    print(f"   - Used search: {data.get('used_search', False)}")

    if "emotional_state" in data:
        emo = data["emotional_state"]
        print(f"\n😊 Emotional State Updated:")
        print(f"   - Trust level: {emo['trust_level']:.2f}")
        print(f"   - Rapport: {emo['rapport']:.2f}")
        print(f"   - Mood: {emo['current_mood']}")

    # Validation
    print(f"\n{'='*70}")
    print("VALIDATION")
    print("="*70)

    validations = []

    # Check flow type matches answer format
    flow_correct = (message_flow == "multi" and is_multi) or (message_flow == "single" and not is_multi)
    validations.append(("message_flow matches answer type", flow_correct))

    # Check metadata
    meta_correct = metadata.get("is_multi_message", False) == is_multi
    validations.append(("metadata is_multi_message correct", meta_correct))

    # Check message count
    expected_count = len(answer) if is_multi else 1
    count_correct = metadata.get("message_count", 1) == expected_count
    validations.append(("message_count correct", count_correct))

    # Check messages not empty
    if is_multi:
        all_non_empty = all(msg.strip() for msg in answer)
        validations.append(("all messages non-empty", all_non_empty))

    # Print validation results
    for test_name, passed in validations:
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}")

    passed_count = sum(1 for _, p in validations if p)
    total_count = len(validations)

    print(f"\n{'='*70}")
    print(f"RESULT: {passed_count}/{total_count} validations passed")
    print("="*70)

    return passed_count == total_count

if __name__ == "__main__":
    try:
        print("\n⏳ Simulating UI multi-message flow...\n")
        time.sleep(1)

        success = test_ui_flow()

        print("\n" + "="*70)
        if success:
            print("🎉 UI FLOW SIMULATION SUCCESSFUL")
            print("\nThe multi-message feature is working correctly!")
            print("You can now test in the actual UI at: http://localhost:3000")
        else:
            print("⚠️ VALIDATION ISSUES DETECTED")
            print("Check the output above for details.")
        print("="*70 + "\n")

        exit(0 if success else 1)

    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to backend")
        print("Make sure backend is running at http://localhost:8000")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
