#!/usr/bin/env python3
"""Check if messages are in database."""

import sqlite3

conn = sqlite3.connect("chats.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get recent sessions
cur.execute("SELECT id, persona_key, title FROM chat_sessions ORDER BY created_at DESC LIMIT 3")
sessions = cur.fetchall()

print("Recent sessions:")
for sess in sessions:
    print(f"  Session {sess['id']}: {sess['persona_key']} - {sess['title']}")

    # Get messages for this session
    cur.execute("SELECT COUNT(*) as count FROM messages WHERE session_id = ?", (sess['id'],))
    count = cur.fetchone()['count']
    print(f"    Messages: {count}")

    # Show first few messages
    cur.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp LIMIT 5", (sess['id'],))
    msgs = cur.fetchall()
    for msg in msgs:
        print(f"      [{msg['role']}] {msg['content'][:50]}...")
    print()

conn.close()
