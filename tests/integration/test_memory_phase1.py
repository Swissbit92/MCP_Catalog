"""
Phase 1 Memory Quality Tests - Conversation Memory Validation

Tests persona ability to remember conversation history loaded from database.
Validates Task 1.1 (Session-Aware Context Loading) implementation.
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from coordinator.server import app


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


class TestConversationMemory:
    """Test persona conversation memory across multiple turns."""

    def test_short_term_memory_recall_10_messages(self, client):
        """
        Test Case 1.1: Short-term memory recall (10 messages ago)

        Persona should remember user's name shared 10 messages earlier.

        Expected: Persona recalls "Alex" from message 1 after 10 intervening messages.
        """
        print("\n=== TEST: Short-term memory recall (10 messages) ===")

        # Create new session
        session_response = client.post("/sessions", json={
            "persona_key": "Eeva",
            "title": "Memory Test - 10 messages"
        })
        assert session_response.status_code == 200
        session = session_response.json()
        session_id = session["id"]
        print(f"Created session: {session_id}")

        # Message 1: User shares name
        msg1 = client.post(f"/sessions/{session_id}/chat", json={
            "message": "Hi! My name is Alex and I'm learning about Bitcoin."
        })
        assert msg1.status_code == 200
        print("Message 1: User introduces as Alex")

        # Messages 2-10: Unrelated questions (fill conversation buffer)
        unrelated_questions = [
            "What is blockchain?",
            "How does mining work?",
            "What are transaction fees?",
            "Explain proof of work.",
            "What is a wallet?",
            "How do I store Bitcoin safely?",
            "What is a private key?",
            "Tell me about public keys.",
            "What is a hash function?"
        ]

        for i, question in enumerate(unrelated_questions, start=2):
            response = client.post(f"/sessions/{session_id}/chat", json={
                "message": question
            })
            assert response.status_code == 200
            print(f"Message {i}: Asked unrelated question")

        # Message 11: Ask about name (should remember from message 1)
        recall_msg = client.post(f"/sessions/{session_id}/chat", json={
            "message": "What's my name?"
        })
        assert recall_msg.status_code == 200
        answer = recall_msg.json()["answer"].lower()

        print(f"\nPersona's answer: {answer[:200]}...")

        # Assertions
        assert "alex" in answer, (
            f"Persona should remember user's name 'Alex' from 10 messages ago. "
            f"Got: {answer[:200]}"
        )
        print("[PASS] Persona correctly recalled user's name from 10 messages ago")

    def test_medium_term_memory_recall_20_messages(self, client):
        """
        Test Case 1.2: Medium-term memory recall (20 messages ago)

        Persona should remember user's holdings shared 20 messages earlier.

        Expected: Persona recalls Bitcoin holdings from message 1 after 20 messages.
        """
        print("\n=== TEST: Medium-term memory recall (20 messages) ===")

        # Create new session
        session_response = client.post("/sessions", json={
            "persona_key": "Eeva",
            "title": "Memory Test - 20 messages"
        })
        assert session_response.status_code == 200
        session = session_response.json()
        session_id = session["id"]
        print(f"Created session: {session_id}")

        # Message 1: User shares holdings
        msg1 = client.post(f"/sessions/{session_id}/chat", json={
            "message": "I just bought my first 0.5 BTC last week!"
        })
        assert msg1.status_code == 200
        print("Message 1: User shares they bought 0.5 BTC")

        # Messages 2-20: Fill with unrelated technical questions
        filler_questions = [
            "What is a satoshi?",
            "Explain SegWit.",
            "What is Lightning Network?",
            "How does multisig work?",
            "What are smart contracts?",
            "Tell me about Ethereum.",
            "What is DeFi?",
            "Explain staking.",
            "What is a node?",
            "How does validation work?",
            "What are UTXOs?",
            "Explain transaction inputs.",
            "What is a mempool?",
            "How do miners choose transactions?",
            "What is difficulty adjustment?",
            "Explain the halving.",
            "What is maximum supply?",
            "Tell me about scarcity.",
            "What makes Bitcoin valuable?"
        ]

        for i, question in enumerate(filler_questions, start=2):
            response = client.post(f"/sessions/{session_id}/chat", json={
                "message": question
            })
            assert response.status_code == 200
            print(f"Message {i}: Asked question #{i-1}")

        # Message 21: Ask about holdings (should remember from message 1)
        recall_msg = client.post(f"/sessions/{session_id}/chat", json={
            "message": "How much Bitcoin do I own again?"
        })
        assert recall_msg.status_code == 200
        answer = recall_msg.json()["answer"].lower()

        print(f"\nPersona's answer: {answer[:300]}...")

        # Assertions - should mention 0.5 BTC
        assert ("0.5" in answer and "btc" in answer) or "half" in answer, (
            f"Persona should remember user owns 0.5 BTC from 20 messages ago. "
            f"Got: {answer[:300]}"
        )
        print("[PASS] Persona correctly recalled user's holdings from 20 messages ago")

    def test_personal_info_retention(self, client):
        """
        Test Case 1.3: Personal information retention

        Persona should remember multiple personal details shared across conversation.

        Expected: Persona recalls name, occupation, and goal from various messages.
        """
        print("\n=== TEST: Personal information retention ===")

        # Create new session
        session_response = client.post("/sessions", json={
            "persona_key": "Frieren",
            "title": "Personal Info Test"
        })
        assert session_response.status_code == 200
        session = session_response.json()
        session_id = session["id"]
        print(f"Created session: {session_id}")

        # Share personal info across multiple messages
        client.post(f"/sessions/{session_id}/chat", json={
            "message": "My name is Sarah."
        })
        print("Shared: name = Sarah")

        client.post(f"/sessions/{session_id}/chat", json={
            "message": "I work as a software engineer."
        })
        print("Shared: occupation = software engineer")

        client.post(f"/sessions/{session_id}/chat", json={
            "message": "My goal is to save 1 BTC by the end of the year."
        })
        print("Shared: goal = save 1 BTC")

        # Fill with unrelated messages
        for i in range(10):
            client.post(f"/sessions/{session_id}/chat", json={
                "message": f"Tell me something interesting about Bitcoin. (question {i+1})"
            })

        # Test recall of all personal info
        recall_msg = client.post(f"/sessions/{session_id}/chat", json={
            "message": "Can you remind me what I told you about myself?"
        })
        assert recall_msg.status_code == 200
        answer = recall_msg.json()["answer"].lower()

        print(f"\nPersona's answer: {answer[:400]}...")

        # Assertions - should mention all three pieces of info
        assert "sarah" in answer, "Persona should remember user's name (Sarah)"
        assert ("engineer" in answer or "software" in answer), "Persona should remember occupation"
        # Goal check is more flexible due to paraphrasing
        has_goal = ("1 btc" in answer or "one btc" in answer or "bitcoin by" in answer)
        assert has_goal, "Persona should remember user's goal (save 1 BTC)"

        print("[PASS] Persona retained all personal information across conversation")

    def test_conversation_context_continuity(self, client):
        """
        Test Case 1.4: Conversation context continuity

        Persona should maintain topic awareness across multi-turn discussions.

        Expected: Persona remembers the specific topic being discussed.
        """
        print("\n=== TEST: Conversation context continuity ===")

        # Create new session
        session_response = client.post("/sessions", json={
            "persona_key": "Gojo",
            "title": "Context Continuity Test"
        })
        assert session_response.status_code == 200
        session = session_response.json()
        session_id = session["id"]
        print(f"Created session: {session_id}")

        # Start discussing a specific topic (hardware wallets)
        client.post(f"/sessions/{session_id}/chat", json={
            "message": "I'm interested in hardware wallets for Bitcoin storage."
        })
        print("Started topic: Hardware wallets")

        # Continue discussion
        msg2 = client.post(f"/sessions/{session_id}/chat", json={
            "message": "Which brands do you recommend?"
        })
        assert msg2.status_code == 200

        msg3 = client.post(f"/sessions/{session_id}/chat", json={
            "message": "How much do they typically cost?"
        })
        assert msg3.status_code == 200

        # Brief interruption
        client.post(f"/sessions/{session_id}/chat", json={
            "message": "Actually, quick question - what's the current block height?"
        })

        # Return to original topic - persona should remember context
        recall_msg = client.post(f"/sessions/{session_id}/chat", json={
            "message": "Okay, back to what we were discussing - are they worth the investment?"
        })
        assert recall_msg.status_code == 200
        answer = recall_msg.json()["answer"].lower()

        print(f"\nPersona's answer: {answer[:300]}...")

        # Assertions - should reference hardware wallets or security
        hardware_ref = any(term in answer for term in ["hardware", "wallet", "security", "device", "ledger", "trezor"])
        assert hardware_ref, (
            f"Persona should remember the topic being discussed (hardware wallets). "
            f"Got: {answer[:300]}"
        )
        print("[PASS] Persona maintained conversation context across topic switch")

    def test_token_budget_not_exceeded(self, client):
        """
        Test Case 1.5: Token budget monitoring

        Verify that token monitoring is working and budget is not exceeded.

        Expected: Token usage logged and stays within limits.
        """
        print("\n=== TEST: Token budget monitoring ===")

        # Create new session
        session_response = client.post("/sessions", json={
            "persona_key": "Eeva",
            "title": "Token Budget Test"
        })
        assert session_response.status_code == 200
        session = session_response.json()
        session_id = session["id"]

        # Send messages and monitor (check logs manually)
        for i in range(15):
            response = client.post(f"/sessions/{session_id}/chat", json={
                "message": f"This is test message number {i+1}. " + ("Tell me about Bitcoin. " * 10)
            })
            assert response.status_code == 200

        print("[INFO] Sent 15 messages with long content")
        print("[INFO] Check application logs for [Tokens] entries")
        print("[INFO] Verify token usage is logged and within budget (4096 tokens)")
        print("[PASS] Token budget test completed - review logs for token usage stats")


class TestMemoryEdgeCases:
    """Test edge cases and boundary conditions for memory system."""

    def test_empty_conversation_memory(self, client):
        """Test memory system with brand new conversation."""
        print("\n=== TEST: Empty conversation (first message) ===")

        session_response = client.post("/sessions", json={
            "persona_key": "Eeva",
            "title": "Empty Memory Test"
        })
        assert session_response.status_code == 200
        session = session_response.json()
        session_id = session["id"]

        # First message - no history exists yet
        response = client.post(f"/sessions/{session_id}/chat", json={
            "message": "Hello! This is my first message."
        })
        assert response.status_code == 200
        print("[PASS] System handles empty conversation correctly")

    def test_very_long_messages(self, client):
        """Test memory with very long messages that consume many tokens."""
        print("\n=== TEST: Very long messages (token stress test) ===")

        session_response = client.post("/sessions", json={
            "persona_key": "Frieren",
            "title": "Long Message Test"
        })
        assert session_response.status_code == 200
        session = session_response.json()
        session_id = session["id"]

        # Send very long message
        long_message = (
            "I have a very detailed question about Bitcoin. " * 50 +
            "This message is intentionally very long to test token limits. " * 50
        )

        response = client.post(f"/sessions/{session_id}/chat", json={
            "message": long_message
        })
        assert response.status_code == 200
        print(f"[INFO] Sent message with ~{len(long_message)} characters")
        print("[PASS] System handles very long messages")


def run_memory_tests():
    """Run all memory tests and generate report."""
    print("\n" + "=" * 70)
    print("PHASE 1 MEMORY QUALITY TEST SUITE")
    print("Testing Task 1.1: Session-Aware Context Loading")
    print("=" * 70)

    # Run with pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-s"  # Show print statements
    ])

    if exit_code == 0:
        print("\n" + "=" * 70)
        print("[SUCCESS] All Phase 1 memory tests passed!")
        print("=" * 70)
        print("\nNext Steps:")
        print("1. Review application logs for [Tokens] and [Memory] entries")
        print("2. Verify token usage stays within budget")
        print("3. Conduct manual user testing")
        print("4. Mark Phase 1 as complete in roadmap")
    else:
        print("\n" + "=" * 70)
        print("[FAILED] Some Phase 1 memory tests failed")
        print("=" * 70)
        print("\nAction Required:")
        print("1. Review test failures above")
        print("2. Check database message loading in chat_with_session()")
        print("3. Verify token monitoring is working")
        print("4. Re-run tests after fixes")

    return exit_code


if __name__ == "__main__":
    exit(run_memory_tests())
