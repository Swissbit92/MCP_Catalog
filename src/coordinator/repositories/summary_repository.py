"""Repository for conversation summaries database operations."""

from __future__ import annotations
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
import logging
import threading

logger = logging.getLogger(__name__)


class SummaryRepository:
    """Handles database operations for conversation summaries."""

    def __init__(self, db_path: str):
        """Initialize summary repository.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._lock = threading.Lock()

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
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            try:
                cur = conn.cursor()
                now = datetime.utcnow().isoformat(timespec="seconds") + "Z"

                cur.execute("""
                    INSERT INTO conversation_summaries
                    (session_id, message_range, summary_text, emotional_developments,
                     topics_discussed, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, message_range, summary_text, emotional_developments,
                      topics_discussed, now))

                conn.commit()
                summary_id = cur.lastrowid

                logger.info(
                    f"[SummaryRepo] Created summary {summary_id} for session {session_id} "
                    f"(range: {message_range})"
                )

                return summary_id

            finally:
                conn.close()

    def get_summaries_by_session(self, session_id: str) -> List[Dict]:
        """Get all summaries for a session, ordered by creation time.

        Args:
            session_id: Session ID

        Returns:
            List of summary dicts
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, session_id, message_range, summary_text,
                       emotional_developments, topics_discussed, created_at
                FROM conversation_summaries
                WHERE session_id = ?
                ORDER BY created_at ASC
            """, (session_id,))

            rows = cur.fetchall()
            return [dict(row) for row in rows]

        finally:
            conn.close()

    def get_latest_summary(self, session_id: str) -> Optional[Dict]:
        """Get the most recent summary for a session.

        Args:
            session_id: Session ID

        Returns:
            Summary dict or None if no summaries exist
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, session_id, message_range, summary_text,
                       emotional_developments, topics_discussed, created_at
                FROM conversation_summaries
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (session_id,))

            row = cur.fetchone()
            return dict(row) if row else None

        finally:
            conn.close()

    def count_summaries(self, session_id: str) -> int:
        """Count summaries for a session.

        Args:
            session_id: Session ID

        Returns:
            Number of summaries
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*) FROM conversation_summaries
                WHERE session_id = ?
            """, (session_id,))

            count = cur.fetchone()[0]
            return count

        finally:
            conn.close()

    def delete_summaries_by_session(self, session_id: str) -> int:
        """Delete all summaries for a session.

        Args:
            session_id: Session ID

        Returns:
            Number of summaries deleted
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            try:
                cur = conn.cursor()
                cur.execute("""
                    DELETE FROM conversation_summaries
                    WHERE session_id = ?
                """, (session_id,))

                conn.commit()
                deleted_count = cur.rowcount

                if deleted_count > 0:
                    logger.info(
                        f"[SummaryRepo] Deleted {deleted_count} summaries "
                        f"for session {session_id}"
                    )

                return deleted_count

            finally:
                conn.close()

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
