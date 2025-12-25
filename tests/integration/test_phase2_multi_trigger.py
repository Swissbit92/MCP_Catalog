#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test to trigger multi-message responses with multiple attempts."""

import sys
import io
import requests
import json

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BACKEND_URL = "http://127.0.0.1:8000"

# Create session
print("Creating session with Gojo...")
session_response = requests.post(
    f"{BACKEND_URL}/sessions",
    json={"persona_key": "Gojo", "title": "Multi-Message Test"}
)
session_id = session_response.json()["id"]
print(f"Session ID: {session_id}\n")

# Try different types of questions that should trigger multi-message
test_messages = [
    "I just bought my first 0.1 BTC! What should I do next to keep it safe?",
    "Tell me about yourself. What kind of topics are you interested in?",
    "I'm worried about the market crashing. Should I sell now or hold?",
    "What's the difference between hot wallets and cold wallets? Which one should I use?",
    "I heard about Bitcoin ETFs. Are they a good idea for beginners like me?"
]

multi_count = 0
total_count = 0

for i, message in enumerate(test_messages, 1):
    print(f"\n{'='*70}")
    print(f"Test {i}/5: {message[:60]}...")
    print('='*70)

    response = requests.post(
        f"{BACKEND_URL}/sessions/{session_id}/chat",
        json={"message": message}
    )

    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        continue

    data = response.json()
    total_count += 1

    message_flow = data.get("message_flow", "single")
    answer = data.get("answer")
    is_multi = isinstance(answer, list)

    if is_multi:
        multi_count += 1
        print(f"\n✅ MULTI-MESSAGE ({len(answer)} messages)")
        for j, msg in enumerate(answer, 1):
            print(f"\n[Message {j}]")
            print(msg)
    else:
        print(f"\n❌ Single message")
        preview = answer[:200] + "..." if len(answer) > 200 else answer
        print(preview)

print(f"\n{'='*70}")
print(f"RESULTS: {multi_count}/{total_count} responses used multi-message format")
print(f"Rate: {(multi_count/total_count*100):.1f}% (target: 20-25%)")
print('='*70)
