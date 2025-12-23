#!/usr/bin/env python3
"""Quick memory test - verifies database-backed context loading."""

import requests
import sys

API_BASE = "http://127.0.0.1:8000"

def test():
    # Create session
    print("Creating session...")
    resp = requests.post(f"{API_BASE}/sessions", json={"persona_key": "Eeva", "title": "Quick Test"})
    session_id = resp.json()["id"]
    print(f"Session: {session_id}\n")

    # Message 1: Introduce name
    print("1. Introducing name...")
    resp = requests.post(f"{API_BASE}/sessions/{session_id}/chat", json={"message": "My name is Alex"})
    print(f"   Response: {resp.json()['answer'][:80]}...\n")

    # Messages 2-5: Filler
    for i in range(2, 6):
        print(f"{i}. Sending filler message...")
        requests.post(f"{API_BASE}/sessions/{session_id}/chat", json={"message": f"Tell me about Bitcoin feature {i}"})

    # Message 6: Test recall
    print("\n6. Testing name recall...")
    resp = requests.post(f"{API_BASE}/sessions/{session_id}/chat", json={"message": "What's my name?"})
    answer = resp.json()["answer"]
    print(f"   Response: {answer}\n")

    # Check if name was recalled
    if "alex" in answer.lower():
        print("[PASS] Memory working! Persona recalled 'Alex' from message 1")
        return 0
    else:
        print("[FAIL] Memory broken. Persona did not recall 'Alex'")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(test())
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
