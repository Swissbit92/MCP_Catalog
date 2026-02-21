"""Repository for conversation summaries database operations."""

from __future__ import annotations
from typing import List, Dict, Optional
import logging

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class SummaryRepository(BaseRepository):
    """Handles database operations for conversation summaries."""

    def __init__(self, db_path: str):
        """Initialize summary repository.

        Args:
            db_path: Path to SQLite database file
        """
        super().__init__(db_path)

    def create_summary(
        self,
        session_id: str,
        message_range: str,
        summary_text: str,
        emotional_developments: str = "",
        topics_discussed: str = ""
    ) -> int:
        """Create a new conversation summary.

        Args:
            session_id: Session ID
            message_range: Range of messages (e.g., "1-30")
            summary_text: Summary content
            emotional_developments: Emotional context
            topics_discussed: Topics covered

        Returns:
            Summary ID
        """
        now = self._now()

        cur = self._execute("""
            INSERT INTO conversation_summaries
            (session_id, message_range, summary_text, emotional_developments,
             topics_discussed, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, message_range, summary_text, emotional_developments,
              topics_discussed, now))

        summary_id = cur.lastrowid

        logger.info(
            f"[SummaryRepo] Created summary {summary_id} for session {session_id} "
            f"(range: {message_range})"
        )

        return summary_id

    def get_summaries_by_session(self, session_id: str) -> List[Dict]:
        """Get all summaries for a session, ordered by creation time.

        Args:
            session_id: Session ID

        Returns:
            List of summary dicts
        """
        return self._fetchall_list("""
            SELECT id, session_id, message_range, summary_text,
                   emotional_developments, topics_discussed, created_at
            FROM conversation_summaries
            WHERE session_id = ?
            ORDER BY created_at ASC
        """, (session_id,))

    def get_latest_summary(self, session_id: str) -> Optional[Dict]:
        """Get the most recent summary for a session.

        Args:
            session_id: Session ID

        Returns:
            Summary dict or None if no summaries exist
        """
        return self._fetchone_dict("""
            SELECT id, session_id, message_range, summary_text,
                   emotional_developments, topics_discussed, created_at
            FROM conversation_summaries
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (session_id,))

    def count_summaries(self, session_id: str) -> int:
        """Count summaries for a session.

        Args:
            session_id: Session ID

        Returns:
            Number of summaries
        """
        row = self._fetchone_dict("""
            SELECT COUNT(*) as cnt FROM conversation_summaries
            WHERE session_id = ?
        """, (session_id,))

        return row["cnt"] if row else 0

    def delete_summaries_by_session(self, session_id: str) -> int:
        """Delete all summaries for a session.

        Args:
            session_id: Session ID

        Returns:
            Number of summaries deleted
        """
        cur = self._execute("""
            DELETE FROM conversation_summaries
            WHERE session_id = ?
        """, (session_id,))

        deleted_count = cur.rowcount

        if deleted_count > 0:
            logger.info(
                f"[SummaryRepo] Deleted {deleted_count} summaries "
                f"for session {session_id}"
            )

        return deleted_count

    def get_message_range_from_summary(self, summary: Dict) -> tuple[int, int]:
        """Parse message range from summary.

        Args:
            summary: Summary dict with message_range field

        Returns:
            Tuple of (start_msg_num, end_msg_num)
        """
        try:
            range_str = summary.get("message_range", "0-0")
            start, end = range_str.split("-")
            return (int(start), int(end))
        except (ValueError, AttributeError):
            logger.warning(
                f"[SummaryRepo] Invalid message_range format: {summary.get('message_range')}"
            )
            return (0, 0)
