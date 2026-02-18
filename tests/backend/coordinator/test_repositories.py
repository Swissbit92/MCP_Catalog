#!/usr/bin/env python3
"""
Test script for repository pattern refactoring.
Tests basic CRUD operations for sessions and messages.
"""
import os
import sys
import tempfile

# Add src to path
sys.path.insert(0, 'src')

from coordinator.repositories.session_repository import SessionRepository
from coordinator.repositories.message_repository import MessageRepository

def test_repositories():
    """Test basic repository operations."""
    # Use a temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        # Initialize repositories
        session_repo = SessionRepository(db_path)
        message_repo = MessageRepository(db_path)

        # Initialize database schema
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            persona_key TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            latency_ms INTEGER,
            source_type TEXT DEFAULT 'llm',
            multi_message_id TEXT,
            multi_message_index INTEGER,
            FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
        )""")
        conn.commit()
        conn.close()

        print("[PASS] Database initialized")

        # Test 1: Create a session
        session_id = session_repo.create_session("eeva", "Test Chat Session")
        print(f"[PASS] Created session: {session_id}")

        # Test 2: Get the session
        session = session_repo.get_session(session_id)
        assert session is not None, "Session should exist"
        assert session['persona_key'] == "eeva"
        assert session['title'] == "Test Chat Session"
        print(f"[PASS] Retrieved session: {session['title']}")

        # Test 3: Create messages
        msg1_id = message_repo.create_message(
            session_id=session_id,
            role="user",
            content="Hello, test message!"
        )
        print(f"[PASS] Created message 1: {msg1_id}")

        msg2_id = message_repo.create_message(
            session_id=session_id,
            role="assistant",
            content="Hello! This is a test response.",
            latency_ms=150
        )
        print(f"[PASS] Created message 2: {msg2_id}")

        # Test 4: Get messages
        messages = message_repo.get_messages_by_session(session_id)
        assert len(messages) == 2, "Should have 2 messages"
        assert messages[0]['role'] == "user"
        assert messages[1]['role'] == "assistant"
        print(f"[PASS] Retrieved {len(messages)} messages")

        # Test 5: Update session title
        session_repo.update_session_title(session_id, "Updated Test Chat")
        updated_session = session_repo.get_session(session_id)
        assert updated_session['title'] == "Updated Test Chat"
        print(f"[PASS] Updated session title: {updated_session['title']}")

        # Test 6: Get all sessions
        all_sessions = session_repo.get_all_sessions()
        assert len(all_sessions) == 1
        assert all_sessions[0]['message_count'] == 2
        print(f"[PASS] Retrieved all sessions: {len(all_sessions)} sessions with {all_sessions[0]['message_count']} messages")

        # Test 7: Check session exists
        exists = session_repo.session_exists(session_id)
        assert exists, "Session should exist"
        print(f"[PASS] Session exists check passed")

        # Test 8: Delete session (should cascade delete messages)
        session_repo.delete_session(session_id)
        deleted_session = session_repo.get_session(session_id)
        assert deleted_session is None, "Session should be deleted"

        remaining_messages = message_repo.get_messages_by_session(session_id)
        assert len(remaining_messages) == 0, "Messages should be cascade deleted"
        print(f"[PASS] Session deleted (cascade delete verified)")

        print("\n[SUCCESS] All repository tests passed!")
        return True

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Clean up — ignore Windows file-lock errors (connections may still be pooled)
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
                print(f"[CLEANUP] Cleaned up test database")
            except PermissionError:
                pass

if __name__ == "__main__":
    success = test_repositories()
    sys.exit(0 if success else 1)
