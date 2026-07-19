# src/coordinator/repositories/message_repository.py
# Repository for messages table operations

from __future__ import annotations
from typing import Optional, List, Dict, Any
import uuid
from .base_repository import BaseRepository

class MessageRepository(BaseRepository):
    """Repository for managing chat messages."""

    def create_message(
        self,
        session_id: str,
        role: str,
        content: str,
        latency_ms: Optional[int] = None,
        timestamp: Optional[str] = None,
        source_type: str = "llm",
        multi_message_id: Optional[str] = None,
        multi_message_index: Optional[int] = None
    ) -> str:
        """
        Create a new message in a session.

        Args:
            session_id: Session identifier
            role: Message role (user/assistant)
            content: Message content
            latency_ms: Optional latency in milliseconds
            timestamp: Optional timestamp (defaults to current time if not provided)
            source_type: Source type (llm, brave_mcp)
            multi_message_id: Optional ID linking related multi-messages together
            multi_message_index: Optional index for multi-message ordering (0-based)

        Returns:
            Message ID
        """
        message_id = str(uuid.uuid4())
        ts = timestamp or self._now()

        query = """
            INSERT INTO messages (id, session_id, role, content, timestamp, latency_ms, source_type, multi_message_id, multi_message_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._execute(query, (message_id, session_id, role, content, ts, latency_ms, source_type, multi_message_id, multi_message_index))

        return message_id

    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get message by ID.

        Args:
            message_id: Message identifier

        Returns:
            Message dictionary or None if not found
        """
        query = "SELECT * FROM messages WHERE id = ?"
        return self._fetchone_dict(query, (message_id,))

    def get_messages_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all messages for a session ordered by timestamp.

        Args:
            session_id: Session identifier

        Returns:
            List of message dictionaries
        """
        query = """
            SELECT * FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """
        return self._fetchall_list(query, (session_id,))

    def get_recent_messages(
        self,
        session_id: str,
        limit: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Get recent messages from a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return

        Returns:
            List of recent message dictionaries
        """
        query = """
            SELECT * FROM messages
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        messages = self._fetchall_list(query, (session_id, limit))
        # Reverse to get chronological order
        return list(reversed(messages))

    def delete_messages_by_session(self, session_id: str) -> int:
        """
        Delete all messages for a session.

        Args:
            session_id: Session identifier

        Returns:
            Number of messages deleted
        """
        with self._lock:
            conn = self._conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            deleted_count = cur.rowcount
            conn.commit()
            conn.close()

        return deleted_count

    def count_messages_by_session(self, session_id: str) -> int:
        """
        Count messages in a session.

        Args:
            session_id: Session identifier

        Returns:
            Number of messages
        """
        result = self._fetchone_dict(
            "SELECT COUNT(*) as count FROM messages WHERE session_id = ?",
            (session_id,)
        )
        return result["count"] if result else 0

    def get_last_message(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent message from a session.

        Args:
            session_id: Session identifier

        Returns:
            Message dictionary or None if no messages
        """
        query = """
            SELECT * FROM messages
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """
        return self._fetchone_dict(query, (session_id,))

    def delete_message(self, message_id: str) -> bool:
        """
        Delete a single message by ID (ADR-011 undo/regenerate — partial deletes).

        Unlike ``delete_messages_by_session`` (full wipe), this removes exactly one
        row so conversation-control verbs can drop the last turn without touching
        the rest of the history.

        Args:
            message_id: Message identifier

        Returns:
            True if a row was deleted, False if no message matched.
        """
        with self._lock:
            conn = self._conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM messages WHERE id = ?", (message_id,))
            deleted = cur.rowcount
            conn.commit()
            conn.close()

        return deleted > 0
