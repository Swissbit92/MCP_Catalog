# src/coordinator/repositories/session_repository.py
# Repository for chat_sessions table operations

from __future__ import annotations
from typing import Optional, List, Dict, Any
import uuid
from .base_repository import BaseRepository

class SessionRepository(BaseRepository):
    """Repository for managing chat sessions."""

    def create_session(
        self,
        persona_key: str,
        title: str,
        session_id: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None
    ) -> str:
        """
        Create a new chat session.

        Args:
            persona_key: Persona identifier
            title: Session title
            session_id: Optional custom session ID (generates UUID if not provided)
            created_at: Optional creation timestamp (defaults to current time)
            updated_at: Optional update timestamp (defaults to current time)

        Returns:
            Session ID
        """
        sid = session_id or str(uuid.uuid4())
        now = self._now()
        created = created_at or now
        updated = updated_at or now

        query = """
            INSERT INTO chat_sessions (id, persona_key, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """
        self._execute(query, (sid, persona_key, title, created, updated))

        return sid

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session dictionary or None if not found
        """
        query = "SELECT * FROM chat_sessions WHERE id = ?"
        return self._fetchone_dict(query, (session_id,))

    def get_sessions_by_persona(self, persona_key: str) -> List[Dict[str, Any]]:
        """
        Get all sessions for a persona.

        Args:
            persona_key: Persona identifier

        Returns:
            List of session dictionaries
        """
        query = """
            SELECT * FROM chat_sessions
            WHERE persona_key = ?
            ORDER BY updated_at DESC
        """
        return self._fetchall_list(query, (persona_key,))

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all chat sessions ordered by update time.

        Returns:
            List of session dictionaries with message counts
        """
        query = """
            SELECT
                s.id,
                s.persona_key,
                s.title,
                s.created_at,
                s.updated_at,
                COUNT(m.id) as message_count
            FROM chat_sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            GROUP BY s.id, s.persona_key, s.title, s.created_at, s.updated_at
            ORDER BY s.updated_at DESC
        """
        return self._fetchall_list(query)

    def update_session_title(self, session_id: str, title: str) -> None:
        """
        Update session title.

        Args:
            session_id: Session identifier
            title: New title
        """
        query = """
            UPDATE chat_sessions
            SET title = ?, updated_at = ?
            WHERE id = ?
        """
        self._execute(query, (title, self._now(), session_id))

    def update_session_timestamp(self, session_id: str) -> None:
        """
        Update session's updated_at timestamp.

        Args:
            session_id: Session identifier
        """
        query = "UPDATE chat_sessions SET updated_at = ? WHERE id = ?"
        self._execute(query, (self._now(), session_id))

    def delete_session(self, session_id: str) -> None:
        """
        Delete a session (messages will be cascade deleted).

        Args:
            session_id: Session identifier
        """
        query = "DELETE FROM chat_sessions WHERE id = ?"
        self._execute(query, (session_id,))

    def delete_sessions_by_persona(self, persona_keys: List[str]) -> int:
        """
        Delete all sessions for specified personas.

        Args:
            persona_keys: List of persona identifiers to delete

        Returns:
            Number of sessions deleted
        """
        if not persona_keys:
            return 0

        placeholders = ','.join('?' * len(persona_keys))
        query = f"DELETE FROM chat_sessions WHERE persona_key IN ({placeholders})"

        with self._lock:
            conn = self._conn()
            cur = conn.cursor()
            cur.execute(query, persona_keys)
            deleted_count = cur.rowcount
            conn.commit()
            conn.close()

        return deleted_count

    def get_persona_key(self, session_id: str) -> Optional[str]:
        """
        Get persona key for a session.

        Args:
            session_id: Session identifier

        Returns:
            Persona key or None if session not found
        """
        result = self._fetchone_dict(
            "SELECT persona_key FROM chat_sessions WHERE id = ?",
            (session_id,)
        )
        return result["persona_key"] if result else None

    def session_exists(self, session_id: str) -> bool:
        """
        Check if session exists.

        Args:
            session_id: Session identifier

        Returns:
            True if session exists, False otherwise
        """
        result = self._fetchone_dict(
            "SELECT 1 FROM chat_sessions WHERE id = ?",
            (session_id,)
        )
        return result is not None
