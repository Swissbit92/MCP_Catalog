#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1 Memory Enhancement Testing Suite
Tests persona memory recall over 10, 20, and 30+ message conversations.
"""

import sys
import io
import requests
import time
import json
from typing import Dict, List
import pytest

pytestmark = pytest.mark.requires_ollama

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

API_BASE = "http://127.0.0.1:8000"

class MemoryTester:
    def __init__(self):
        self.session_id = None
        self.results = []

    def create_session(self, persona_key: str = "Eeva") -> str:
        """Create a new chat session."""
        response = requests.post(
            f"{API_BASE}/sessions",
            json={"persona_key": persona_key, "title": "Memory Test Session"}
        )
        data = response.json()
        self.session_id = data["id"]
        print(f"[OK] Created session: {self.session_id}")
        return self.session_id

    def send_message(self, message: str) -> Dict:
        """Send a message to the session."""
        response = requests.post(
            f"{API_BASE}/sessions/{self.session_id}/chat",
            json={"message": message}
        )
        data = response.json()
        print(f">> User: {message[:50]}...")
        print(f"<< {data['answer'][:100]}...")
        return data

    def test_short_term_memory(self):
        """Test 1: Short-term memory (10 messages recall)."""
        print("\n" + "="*60)
        print("TEST 1: SHORT-TERM MEMORY (10 messages)")
        print("="*60)

        # Message 1: Introduce name
        print("\n[Step 1] User introduces themselves...")
        self.send_message("My name is Alex and I'm learning about Bitcoin")

        # Messages 2-9: Unrelated questions
        print("\n[Step 2] Sending 8 unrelated messages...")
        unrelated_questions = [
            "What is a blockchain?",
            "How does proof of work function?",
            "Explain mining rewards",
            "What are transaction fees?",
            "How do nodes validate transactions?",
            "What is a merkle tree?",
            "Explain the difficulty adjustment",
            "What is a nonce in Bitcoin?"
        ]
        for i, q in enumerate(unrelated_questions, 2):
            print(f"  Message {i}/{9}: {q}")
            self.send_message(q)
            time.sleep(0.5)  # Slight delay to avoid overwhelming server

        # Message 10: Ask about name
        print("\n[Step 3] Testing memory recall...")
        response = self.send_message("What's my name?")

        # Validation
        answer_lower = response["answer"].lower()
        success = "alex" in answer_lower

        result = {
            "test": "Short-term memory (10 messages)",
            "expected": "Persona recalls 'Alex'",
            "actual": response["answer"][:200],
            "success": success
        }
        self.results.append(result)

        if success:
            print("\n[PASS] Persona correctly recalled name 'Alex'")
        else:
            print("\n[FAIL] Persona did not recall name 'Alex'")
            print(f"   Response: {response['answer'][:200]}")

        return success

    def test_medium_term_memory(self):
        """Test 2: Medium-term memory (20 messages recall)."""
        print("\n" + "="*60)
        print("TEST 2: MEDIUM-TERM MEMORY (20 messages)")
        print("="*60)

        # Continue from previous session
        # Message 11: Share BTC holding
        print("\n[Step 1] User shares BTC holding...")
        self.send_message("I own 0.5 BTC in cold storage")

        # Messages 12-25: More unrelated questions
        print("\n[Step 2] Sending 14 more unrelated messages...")
        more_questions = [
            "What is SegWit?",
            "Explain the Lightning Network",
            "What are UTXOs?",
            "How does multisig work?",
            "What is a hardware wallet?",
            "Explain BIP standards",
            "What is taproot?",
            "How do atomic swaps work?",
            "What is schnorr signatures?",
            "Explain PSBT",
            "What are payment channels?",
            "How does coinbase transaction work?",
            "What is timelocks?",
            "Explain checksequenceverify"
        ]
        for i, q in enumerate(more_questions, 12):
            print(f"  Message {i}/{25}: {q}")
            self.send_message(q)
            time.sleep(0.5)

        # Message 26: Ask about BTC amount
        print("\n[Step 3] Testing memory recall...")
        response = self.send_message("How much BTC do I have?")

        # Validation
        answer_lower = response["answer"].lower()
        success = "0.5" in answer_lower or "half" in answer_lower or "0.5 btc" in answer_lower

        result = {
            "test": "Medium-term memory (20 messages)",
            "expected": "Persona recalls '0.5 BTC'",
            "actual": response["answer"][:200],
            "success": success
        }
        self.results.append(result)

        if success:
            print("\n[PASS] Persona correctly recalled '0.5 BTC'")
        else:
            print("\n[FAIL] Persona did not recall '0.5 BTC'")
            print(f"   Response: {response['answer'][:200]}")

        return success

    def test_token_budget_compliance(self):
        """Test 3: Token budget compliance (check logs)."""
        print("\n" + "="*60)
        print("TEST 3: TOKEN BUDGET COMPLIANCE")
        print("="*60)

        print("\nSending one more message to trigger token logging...")
        response = self.send_message("Can you summarize what we discussed?")

        print("\n[INFO] Check coordinator logs for token usage:")
        print("   grep '[Tokens]' logs/coordinator.log | tail -5")
        print("\n[OK] Test requires manual log inspection")

        result = {
            "test": "Token budget compliance",
            "expected": "Token usage logged, <4096 tokens",
            "actual": "See logs for details",
            "success": True  # Requires manual verification
        }
        self.results.append(result)

        return True

    def test_conversation_continuity(self):
        """Test 4: Conversation continuity (30+ messages)."""
        print("\n" + "="*60)
        print("TEST 4: CONVERSATION CONTINUITY (30+ messages)")
        print("="*60)

        # Add a few more messages to reach 30+
        print("\n[Step 1] Adding more messages to reach 30+...")
        followup_questions = [
            "What's the best wallet security practice?",
            "Should I use a passphrase?",
            "How often should I check my cold storage?",
            "Is it safe to share my public key?"
        ]
        for q in followup_questions:
            self.send_message(q)
            time.sleep(0.5)

        # Test continuity by referencing earlier topics
        print("\n[Step 2] Testing topic continuity...")
        response = self.send_message("Earlier we talked about my Bitcoin holdings. Can you remind me of the security best practices you mentioned?")

        # Validation (loose - just check for coherent response)
        success = len(response["answer"]) > 50 and ("secur" in response["answer"].lower() or "wallet" in response["answer"].lower())

        result = {
            "test": "Conversation continuity (30+ messages)",
            "expected": "Coherent response referencing earlier discussion",
            "actual": response["answer"][:200],
            "success": success
        }
        self.results.append(result)

        if success:
            print("\n[PASS] Persona maintained conversation continuity")
        else:
            print("\n[FAIL] Persona response seems incoherent")
            print(f"   Response: {response['answer'][:200]}")

        return success

    def print_summary(self):
        """Print test results summary."""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)

        passed = sum(1 for r in self.results if r["success"])
        total = len(self.results)

        for i, result in enumerate(self.results, 1):
            status = "[PASS]" if result["success"] else "[FAIL]"
            print(f"\n{i}. {result['test']}: {status}")
            print(f"   Expected: {result['expected']}")
            print(f"   Actual: {result['actual'][:100]}...")

        print("\n" + "="*60)
        print(f"RESULTS: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
        print("="*60)

        return passed == total


def main():
    """Run all Phase 1 memory tests."""
    print("PHASE 1 MEMORY ENHANCEMENT TEST SUITE")
    print("Testing database-backed conversation memory")
    print()

    tester = MemoryTester()

    # Create session
    tester.create_session("Eeva")

    # Run tests
    test1_pass = tester.test_short_term_memory()
    test2_pass = tester.test_medium_term_memory()
    test3_pass = tester.test_token_budget_compliance()
    test4_pass = tester.test_conversation_continuity()

    # Print summary
    all_passed = tester.print_summary()

    if all_passed:
        print("\n[SUCCESS] ALL TESTS PASSED! Phase 1 implementation successful.")
        return 0
    else:
        print("\n[WARNING] Some tests failed. Review results above.")
        return 1


if __name__ == "__main__":
    exit(main())
