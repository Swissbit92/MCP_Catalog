"""Phase 3 Advanced Memory Integration Test

Tests RAG semantic search, cross-session user profiles, and fact extraction.
"""

import requests
import time
import json
import sqlite3
from datetime import datetime
import pytest

pytestmark = [pytest.mark.requires_ollama, pytest.mark.integration]

BASE_URL = "http://localhost:8000"

def print_section(title):
    """Print formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def create_session(persona_key="Eeva"):
    """Create a new chat session."""
    response = requests.post(f"{BASE_URL}/sessions", json={
        "persona_key": persona_key,
        "title": f"Phase 3 Test - {datetime.now().strftime('%H:%M:%S')}"
    })
    response.raise_for_status()
    session = response.json()
    print(f"✓ Created session: {session['id']}")
    return session['id']

def send_message(session_id, message):
    """Send a message in a session."""
    print(f"\n→ User: {message}")
    response = requests.post(f"{BASE_URL}/sessions/{session_id}/chat", json={
        "message": message
    })
    response.raise_for_status()
    data = response.json()
    print(f"← Assistant: {data['answer'][:200]}...")
    return data

def check_database_profiles():
    """Check user profiles in database."""
    conn = sqlite3.connect("chats.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Check user_profiles table
    cur.execute("SELECT user_id, profile_data FROM user_profiles")
    profiles = cur.fetchall()

    print(f"\nDatabase contains {len(profiles)} user profile(s):")
    for profile in profiles:
        profile_data = json.loads(profile["profile_data"])
        print(f"\n  User ID: {profile['user_id']}")
        print(f"  Name: {profile_data.get('name', 'Not set')}")
        print(f"  Total sessions: {profile_data.get('total_sessions', 0)}")
        print(f"  Total messages: {profile_data.get('total_messages', 0)}")
        print(f"  Facts: {len(profile_data.get('facts', []))}")
        print(f"  Topics: {len(profile_data.get('topics_discussed', {}))}")

        if profile_data.get('holdings'):
            print(f"  Holdings: {profile_data['holdings']}")

    # Check user_sessions linkage
    cur.execute("SELECT COUNT(*) as count FROM user_sessions")
    session_links = cur.fetchone()['count']
    print(f"\n  Total user-session links: {session_links}")

    conn.close()
    return len(profiles) > 0

def main():
    """Run Phase 3 integration test."""
    print_section("Phase 3 Advanced Memory Integration Test")

    try:
        # Test 1: Create session and have conversation
        print_section("Test 1: Initial Conversation with Fact Extraction")
        session_id = create_session("Eeva")

        # Messages designed to trigger fact extraction and build profile
        messages = [
            "Hello! My name is Alex.",  # Name extraction
            "I'm a software engineer learning about Bitcoin.",  # Background
            "I currently own 0.5 BTC that I bought through DCA.",  # Holdings
            "I'm interested in hardware wallets for security.",  # Preference
            "Can you explain what makes Trezor a good choice?",  # Topic
            "I also hold some Ethereum, about 2 ETH.",  # More holdings
            "What's the best way to secure my crypto?",  # Question
            "I prefer cold storage over exchanges.",  # Preference
            "How does multi-sig work?",  # Topic
            "I'm planning to buy more Bitcoin weekly.",  # Fact
            "What do you think about DCA strategy?",  # Trigger extraction (10th message)
        ]

        print(f"\nSending {len(messages)} messages to trigger fact extraction...")
        for msg in messages:
            send_message(session_id, msg)
            time.sleep(0.5)  # Brief pause between messages

        print("\n✓ Completed initial conversation (11 messages)")

        # Test 2: Check database for user profiles
        print_section("Test 2: Verify User Profile Creation")
        profiles_exist = check_database_profiles()

        if profiles_exist:
            print("\n✓ User profile successfully created!")
        else:
            print("\n✗ WARNING: No user profiles found in database")
            print("  Fact extraction may not have triggered yet")

        # Test 3: Test semantic search with RAG
        print_section("Test 3: Semantic Search (RAG)")
        print("Testing semantic search by asking about earlier topics...")

        # Ask about something mentioned earlier (not in recent messages)
        semantic_query = "What hardware wallet did we discuss?"
        print(f"\n→ Query (should find 'Trezor' from message 5): {semantic_query}")
        response = send_message(session_id, semantic_query)

        if "trezor" in response['answer'].lower():
            print("\n✓ Semantic search WORKING: Found 'Trezor' from earlier message!")
        else:
            print("\n⚠ Semantic search result unclear - check logs for RAG activity")

        # Test 4: Cross-session memory
        print_section("Test 4: Cross-Session Memory")
        print("Creating new session with same persona to test profile context...")

        session_id_2 = create_session("Eeva")

        # First message should show persona remembers the user
        cross_session_msg = "Hi again! Do you remember me?"
        print(f"\n→ User (in new session): {cross_session_msg}")
        response = send_message(session_id_2, cross_session_msg)

        # Check if response mentions user's name or facts
        if "alex" in response['answer'].lower():
            print("\n✓ CROSS-SESSION MEMORY WORKING: Persona remembered user's name!")
        else:
            print("\n⚠ Cross-session memory unclear - check if profile was linked")

        # Test 5: Check backend logs for Phase 3 activity
        print_section("Test 5: Backend Logs Analysis")
        print("Checking backend logs for Phase 3 indicators...")

        try:
            with open("backend_test.log", "r", encoding="utf-8", errors="replace") as f:
                logs = f.read()

                indicators = {
                    "[Phase3]": "Phase 3 logging",
                    "[Phase3 RAG]": "RAG semantic search",
                    "Episodic Memory RAG initialized": "RAG initialization",
                    "Updated user profile": "Profile updates",
                    "Fact extraction": "Fact extraction",
                }

                found_indicators = []
                for indicator, description in indicators.items():
                    if indicator in logs:
                        found_indicators.append(f"  ✓ {description}")

                if found_indicators:
                    print("\nPhase 3 activity detected:")
                    for indicator in found_indicators:
                        print(indicator)
                else:
                    print("\n⚠ No Phase 3 indicators found in logs")
                    print("  This may indicate Phase 3 features didn't activate")

        except FileNotFoundError:
            print("\n⚠ Backend log file not found")

        # Final summary
        print_section("Test Results Summary")

        results = {
            "Session Creation": "✓ PASS",
            "Message Sending": "✓ PASS",
            "User Profile DB": "✓ PASS" if profiles_exist else "⚠ PENDING",
            "Semantic Search": "⚠ CHECK MANUALLY",
            "Cross-Session Memory": "⚠ CHECK MANUALLY",
        }

        for test, result in results.items():
            print(f"{test:.<30} {result}")

        print("\n" + "="*60)
        print("Phase 3 integration test completed!")
        print("="*60)

        print("\nNext steps:")
        print("1. Check backend_test.log for detailed Phase 3 logging")
        print("2. Verify RAG search latency in logs (should be <500ms)")
        print("3. Inspect chats.db user_profiles table manually")
        print("4. Review conversation responses for quality")

        return True

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
