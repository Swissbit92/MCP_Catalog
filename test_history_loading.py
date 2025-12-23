#!/usr/bin/env python3
"""Test if history is actually being loaded from database."""

import requests
import sqlite3

# Create session
resp = requests.post("http://127.0.0.1:8000/sessions", json={"persona_key": "Eeva", "title": "History Test"})
session_id = resp.json()["id"]
print(f"Session: {session_id}\n")

# Send 3 messages
print("Sending 3 messages...")
for i in range(1, 4):
    requests.post(f"http://127.0.0.1:8000/sessions/{session_id}/chat", json={"message": f"Test message {i}"})
    print(f"  Sent message {i}")

# Check database
conn = sqlite3.connect("chats.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT COUNT(*) as count FROM messages WHERE session_id = ?", (session_id,))
db_count = cur.fetchone()['count']
conn.close()

print(f"\nMessages in database: {db_count}")
print(f"Expected: 6 (3 user + 3 assistant)")

if db_count == 6:
    print("\n[OK] Messages are being saved to database")
    print("\nNow testing if they're being LOADED...")

    # Send one more message and check logs
    resp = requests.post(f"http://127.0.0.1:8000/sessions/{session_id}/chat", json={"message": "Final test"})

    print("\nCheck backend logs for '[Memory] Loaded' - that proves messages were loaded from DB")
    print("If you don't see that log, the chat_with_session function isn't running our new code!")
else:
    print(f"\n[FAIL] Expected 6 messages, got {db_count}")
