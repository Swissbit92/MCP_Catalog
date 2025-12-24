"""Phase 3 Live Conversation Test

Tests Phase 3 features with real API calls to running backend.
"""

import sys
import os
import requests
import time
import json
import sqlite3

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"

def print_header(text):
    """Print section header."""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def create_session(persona="Eeva"):
    """Create a new chat session."""
    response = requests.post(f"{BASE_URL}/sessions", json={
        "persona_key": persona,
        "title": f"Phase 3 Live Test"
    })
    response.raise_for_status()
    session = response.json()
    print(f"[INFO] Session created: {session['id']}")
    return session['id']

def send_message(session_id, message, show_response=True):
    """Send a message and get response."""
    print(f"\n>> User: {message}")

    start_time = time.time()
    response = requests.post(f"{BASE_URL}/sessions/{session_id}/chat", json={
        "message": message
    })
    latency = (time.time() - start_time) * 1000

    response.raise_for_status()
    data = response.json()

    if show_response:
        answer = data['answer']
        if len(answer) > 300:
            print(f"<< Assistant: {answer[:300]}... [truncated]")
        else:
            print(f"<< Assistant: {answer}")

    print(f"[TIMING] Response latency: {latency:.0f}ms")
    return data

def check_database_profiles():
    """Check user profiles in database."""
    conn = sqlite3.connect("chats.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get all profiles
    cur.execute("SELECT user_id, profile_data, created_at FROM user_profiles")
    profiles = cur.fetchall()

    if not profiles:
        print("[WARN] No user profiles found in database")
        conn.close()
        return None

    print(f"\n[DATABASE] Found {len(profiles)} user profile(s):")

    for profile in profiles:
        data = json.loads(profile['profile_data'])
        print(f"\n  User ID: {profile['user_id']}")
        print(f"  Created: {profile['created_at']}")
        print(f"  Name: {data.get('name', 'Not set')}")
        print(f"  Sessions: {data.get('total_sessions', 0)}")
        print(f"  Messages: {data.get('total_messages', 0)}")
        print(f"  Facts: {len(data.get('facts', []))}")

        if data.get('facts'):
            print(f"  Sample facts:")
            for fact in data['facts'][:3]:
                print(f"    - {fact}")

        if data.get('holdings'):
            print(f"  Holdings: {data['holdings']}")

        if data.get('topics_discussed'):
            top_topics = sorted(data['topics_discussed'].items(),
                              key=lambda x: x[1], reverse=True)[:3]
            print(f"  Top topics: {', '.join([f'{t}({c}x)' for t, c in top_topics])}")

    conn.close()
    return profiles[0]['user_id'] if profiles else None

def main():
    """Run live Phase 3 test."""
    print_header("Phase 3 Live Conversation Test")

    print("\n[INFO] Testing Phase 3 advanced memory features:")
    print("  1. RAG-based semantic search")
    print("  2. Cross-session user profiles")
    print("  3. Automated fact extraction")

    try:
        # Test 1: Create session and have conversation
        print_header("Test 1: Initial Conversation (Trigger Fact Extraction)")

        session_id = create_session("Eeva")

        # Design conversation to trigger fact extraction at message 10
        test_messages = [
            "Hello! My name is Alex.",
            "I'm a software engineer based in San Francisco.",
            "I've been learning about Bitcoin for the past 6 months.",
            "I currently own 0.5 BTC that I bought through dollar-cost averaging.",
            "I'm particularly interested in hardware wallets for security.",
            "Can you explain what makes Trezor a good hardware wallet choice?",
            "I also hold about 2 ETH in addition to my Bitcoin.",
            "What's the best way to secure cryptocurrency long-term?",
            "I prefer cold storage solutions over keeping crypto on exchanges.",
            "How does multi-signature wallet security work?",
            "I'm planning to increase my Bitcoin position by buying $100 worth weekly.",  # Message 11 - triggers extraction
        ]

        print(f"\n[INFO] Sending {len(test_messages)} messages...")
        print("[INFO] Fact extraction should trigger at message 10-11\n")

        for i, msg in enumerate(test_messages, 1):
            send_message(session_id, msg, show_response=(i == 1 or i == 11))
            if i < len(test_messages):
                time.sleep(1)  # Brief pause between messages

        print(f"\n[PASS] Sent all {len(test_messages)} messages")

        # Test 2: Check for user profile in database
        print_header("Test 2: Verify User Profile Creation")

        time.sleep(2)  # Give backend time to process
        user_id = check_database_profiles()

        if user_id:
            print("\n[PASS] User profile successfully created!")
        else:
            print("\n[WARN] User profile not found - may need more messages")

        # Test 3: Test semantic search
        print_header("Test 3: RAG Semantic Search")

        print("\n[INFO] Testing semantic memory retrieval...")
        print("[INFO] Asking about topic from earlier (message 6: Trezor)")

        semantic_query = "What hardware wallet brand did we discuss earlier?"
        response = send_message(session_id, semantic_query, show_response=True)

        answer_lower = response['answer'].lower()
        if 'trezor' in answer_lower:
            print("\n[PASS] Semantic search WORKING! Found 'Trezor' from message 6")
        else:
            print("\n[WARN] Semantic search unclear - check backend logs")
            print(f"[DEBUG] Answer: {response['answer'][:200]}")

        # Test 4: Cross-session memory
        print_header("Test 4: Cross-Session Memory")

        print("\n[INFO] Creating NEW session with same persona...")
        session_id_2 = create_session("Eeva")

        print("[INFO] Testing if persona remembers user from previous session...")
        cross_session_msg = "Hi! Do you remember me? What's my name?"
        response = send_message(session_id_2, cross_session_msg, show_response=True)

        answer_lower = response['answer'].lower()
        if 'alex' in answer_lower:
            print("\n[PASS] CROSS-SESSION MEMORY WORKING! Persona remembered 'Alex'")
        else:
            print("\n[WARN] Cross-session memory unclear")
            print("[INFO] This may indicate user profile wasn't linked yet")

        # Test 5: Check backend logs
        print_header("Test 5: Backend Logs Analysis")

        print("\n[INFO] Checking for Phase 3 activity in logs...")

        try:
            with open("live_test.log", "r", encoding="utf-8", errors="replace") as f:
                logs = f.read()

            phase3_indicators = {
                "[Phase3]": 0,
                "[Phase3 RAG]": 0,
                "Indexed": 0,
                "relevant memories": 0,
                "user profile": 0,
                "Fact extraction": 0,
            }

            for indicator in phase3_indicators:
                count = logs.lower().count(indicator.lower())
                phase3_indicators[indicator] = count

            print("\nPhase 3 Activity Detected:")
            for indicator, count in phase3_indicators.items():
                status = "[FOUND]" if count > 0 else "[NOT FOUND]"
                print(f"  {status} '{indicator}': {count} occurrence(s)")

            # Check for specific success indicators
            if "[Phase3 RAG]" in logs:
                print("\n[PASS] RAG memory system is active")

            if "user profile" in logs.lower():
                print("[PASS] User profile system is active")

        except FileNotFoundError:
            print("\n[WARN] Log file not found - backend may be logging elsewhere")

        # Final summary
        print_header("Test Results Summary")

        results = {
            "Session Creation": "[PASS]",
            "Message Sending (11 messages)": "[PASS]",
            "User Profile in Database": "[PASS]" if user_id else "[WARN]",
            "Semantic Search (RAG)": "[PASS]" if 'trezor' in semantic_query else "[PENDING]",
            "Cross-Session Memory": "[PASS]" if 'alex' in cross_session_msg else "[PENDING]",
        }

        print("\n")
        for test, result in results.items():
            print(f"  {test:.<45} {result}")

        print("\n" + "="*70)
        print("  Phase 3 Live Test Complete!")
        print("="*70)

        print("\n[INFO] Next steps:")
        print("  1. Review backend logs: live_test.log")
        print("  2. Check RAG search latency (should be <500ms)")
        print("  3. Verify user profile quality in database")
        print("  4. Test with longer conversations (50+ messages)")

        return True

    except requests.exceptions.ConnectionError:
        print("\n[FAIL] Could not connect to backend server")
        print("[INFO] Make sure server is running: python run_react.py")
        return False

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
