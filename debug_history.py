#!/usr/bin/env python3
"""Debug: Check what history is being sent."""

import requests

# Create fresh session
resp = requests.post("http://127.0.0.1:8000/sessions", json={"persona_key": "Eeva", "title": "Debug"})
session_id = resp.json()["id"]
print(f"Session: {session_id}\n")

# Send 3 messages
print("Sending messages...")
for i in range(1, 4):
    msg = f"Message {i}"
    resp = requests.post(f"http://127.0.0.1:8000/sessions/{session_id}/chat", json={"message": msg})
    print(f"{i}. Sent: {msg}")

# Now check database
import sqlite3
conn = sqlite3.connect("chats.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT COUNT(*) as count FROM messages WHERE session_id = ?", (session_id,))
print(f"\nMessages in DB: {cur.fetchone()['count']}")

cur.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp", (session_id,))
for msg in cur.fetchall():
    print(f"  [{msg['role']}] {msg['content'][:30]}")

conn.close()

print("\nIf you see messages in DB but persona forgets them, our code ISN'T being executed!")
