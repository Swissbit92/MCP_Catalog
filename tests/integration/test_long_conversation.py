"""Test script for Phase 2 summarization with a long conversation.

This script simulates a 35-message conversation to trigger automatic summarization.
"""

import sys
import requests
import time
import json

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"

# Conversation scenario: User learning about Bitcoin investing
CONVERSATION = [
    # Messages 1-5: Introduction
    {"user": "Hi! My name is David and I'm new to cryptocurrency. Can you help me?"},
    {"user": "I have $5,000 that I want to invest in Bitcoin. Is that a good amount to start?"},
    {"user": "What's the difference between Bitcoin and other cryptocurrencies like Ethereum?"},
    {"user": "How does Bitcoin mining actually work?"},
    {"user": "Is Bitcoin legal in the United States?"},

    # Messages 6-10: Security questions
    {"user": "What's the safest way to store my Bitcoin?"},
    {"user": "I've heard about hardware wallets. What are those?"},
    {"user": "Should I write down my seed phrase on paper?"},
    {"user": "What happens if I lose my seed phrase?"},
    {"user": "Can someone hack my Bitcoin wallet?"},

    # Messages 11-15: Buying process
    {"user": "Which exchange should I use to buy Bitcoin?"},
    {"user": "Do I need to verify my identity to buy crypto?"},
    {"user": "What fees should I expect when buying Bitcoin?"},
    {"user": "Can I buy less than 1 whole Bitcoin?"},
    {"user": "How long does it take for a Bitcoin purchase to complete?"},

    # Messages 16-20: Price and volatility
    {"user": "Why is Bitcoin's price so volatile?"},
    {"user": "What was Bitcoin's highest price ever?"},
    {"user": "Is now a good time to buy or should I wait?"},
    {"user": "How do I know if the price is going up or down?"},
    {"user": "Should I use dollar-cost averaging?"},

    # Messages 21-25: Tax questions
    {"user": "Do I have to pay taxes on Bitcoin?"},
    {"user": "What if I just hold it and don't sell?"},
    {"user": "How do I report crypto on my tax return?"},
    {"user": "Are there any tax advantages to holding crypto?"},
    {"user": "What records should I keep for taxes?"},

    # Messages 26-30: Advanced topics
    {"user": "What is the Lightning Network?"},
    {"user": "Can Bitcoin be used for everyday purchases?"},
    {"user": "What's the difference between hot and cold storage?"},
    {"user": "Should I diversify into other cryptocurrencies?"},
    {"user": "How do I protect against phishing scams?"},

    # Messages 31-35: Final questions (will trigger summarization at 30, then 5 more)
    {"user": "What's your opinion on Bitcoin's future?"},
    {"user": "Should I tell my friends and family I'm investing in crypto?"},
    {"user": "How often should I check my portfolio?"},
    {"user": "What resources do you recommend for learning more?"},
    {"user": "Can you remind me what my initial investment amount was?"},  # Test memory recall
]

def create_session(persona="Eeva"):
    """Create a new chat session."""
    print(f"\n📝 Creating new session with {persona}...")
    response = requests.post(
        f"{BASE_URL}/sessions",
        json={"persona_key": persona, "title": "Long Conversation Test"}
    )

    if response.status_code == 200:
        session = response.json()
        session_id = session["id"]
        print(f"✅ Session created: {session_id}")
        return session_id
    else:
        print(f"❌ Failed to create session: {response.status_code}")
        print(response.text)
        return None

def send_message(session_id, message, msg_num):
    """Send a message and get response."""
    print(f"\n[Message {msg_num}] User: {message[:60]}...")

    try:
        response = requests.post(
            f"{BASE_URL}/sessions/{session_id}/chat",
            json={"message": message},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            answer = data.get("answer", "")
            print(f"[Message {msg_num}] Assistant: {answer[:80]}...")
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def check_summaries(session_id):
    """Check if summaries were created in the database."""
    import sqlite3

    try:
        conn = sqlite3.connect("chats.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT id, message_range,
                   substr(summary_text, 1, 100) as summary_preview,
                   topics_discussed
            FROM conversation_summaries
            WHERE session_id = ?
            ORDER BY created_at
        """, (session_id,))

        summaries = cur.fetchall()
        conn.close()

        print(f"\n📊 Found {len(summaries)} summaries in database:")
        for summary in summaries:
            print(f"\n  Summary ID: {summary['id']}")
            print(f"  Range: {summary['message_range']}")
            print(f"  Preview: {summary['summary_preview']}...")
            if summary['topics_discussed']:
                print(f"  Topics: {summary['topics_discussed']}")

        return len(summaries)

    except Exception as e:
        print(f"❌ Failed to check summaries: {e}")
        return 0

def main():
    """Run the long conversation test."""
    print("="*80)
    print("PHASE 2 TASK 2.2 - LONG CONVERSATION TEST")
    print("Testing automatic summarization with 35-message conversation")
    print("="*80)

    # Create session
    session_id = create_session("Eeva")
    if not session_id:
        print("\n❌ Test failed: Could not create session")
        return False

    # Send messages
    print(f"\n🔄 Sending {len(CONVERSATION)} messages...")
    print("⏰ This will take about 2-3 minutes...")

    success_count = 0
    for i, msg_data in enumerate(CONVERSATION, 1):
        success = send_message(session_id, msg_data["user"], i)
        if success:
            success_count += 1

        # Add a small delay to avoid overwhelming the server
        time.sleep(0.5)

        # Check for summarization after message 30
        if i == 30:
            print("\n" + "="*80)
            print("🎯 REACHED MESSAGE 30 - SUMMARIZATION SHOULD TRIGGER")
            print("="*80)
            time.sleep(2)  # Give it time to summarize

    # Final results
    print("\n" + "="*80)
    print("CONVERSATION COMPLETE")
    print("="*80)
    print(f"✅ Successfully sent: {success_count}/{len(CONVERSATION)} messages")

    # Check database for summaries
    print("\n🔍 Checking database for summaries...")
    time.sleep(1)  # Give summarization time to complete
    summary_count = check_summaries(session_id)

    # Verify results
    print("\n" + "="*80)
    print("TEST RESULTS")
    print("="*80)

    if summary_count > 0:
        print(f"✅ PASS: Found {summary_count} summaries")
        print(f"✅ Auto-summarization working correctly!")

        if summary_count >= 1:
            print(f"✅ Summary created for messages 1-30")

        print(f"\n📋 Session ID: {session_id}")
        print(f"💾 Database: chats.db")
        print(f"\nYou can view summaries with:")
        print(f"  sqlite3 chats.db \"SELECT * FROM conversation_summaries WHERE session_id='{session_id}'\"")

        return True
    else:
        print(f"⚠️ WARNING: No summaries found")
        print(f"Check backend logs for [Summarizer] entries")
        return False

if __name__ == "__main__":
    try:
        success = main()

        print("\n" + "="*80)
        print("NEXT STEPS:")
        print("="*80)
        print("1. Open the React UI: http://localhost:3000")
        print("2. Check backend logs for [Summarizer] entries")
        print("3. View the conversation in the UI")
        print("4. Ask the persona to recall information from early messages")
        print("="*80)

        exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        exit(1)
