#!/usr/bin/env python3
"""Test the API directly and inspect response."""

import requests

# Use existing session with messages
session_id = "b87e4c0e-2fa8-4e66-aea8-20b5da6fd5f5"

print(f"Testing session: {session_id}")
print("\nSending test message...")

resp = requests.post(
    f"http://127.0.0.1:8000/sessions/{session_id}/chat",
    json={"message": "Remind me what my name is"}
)

data = resp.json()

print(f"\nFull response:")
print(data)

print(f"\nAnswer:")
print(data["answer"])
