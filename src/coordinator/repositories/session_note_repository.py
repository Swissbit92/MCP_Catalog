# src/coordinator/repositories/session_note_repository.py
"""ADR-011 — per-session author's note (the /note director directive).

A single sticky note per session, injected into every subsequent turn's system
context (post-`lru_cache`, via ``chat_session_service._build_turn_prompt``) so the
user can set standing scene/style guidance without it being a chat message.

``_ensure_table`` self-creates (dual-covered with the alembic ``5session_notes``
revision, matching MemoryFactRepository / EmotionalStateRepository) so it works in
Docker envs that skip alembic and in unit tests.
"""

from __future__ import annotations

import logging
from typing import Optional

from .base_repository import BaseRepository, utc_now_iso

logger = logging.getLogger(__name__)


class SessionNoteRepository(BaseRepository):
    """CRUD for the one-row-per-session author's note."""

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path)
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Create the session_notes table if absent (dual-covered with alembic)."""
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS session_notes (
                session_id TEXT PRIMARY KEY,
                note       TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

    def get_note(self, session_id: str) -> Optional[str]:
        """Return the session's note text, or None if unset."""
        row = self._fetchone_dict(
            "SELECT note FROM session_notes WHERE session_id = ?", (session_id,)
        )
        return row["note"] if row else None

    def set_note(self, session_id: str, note: str) -> None:
        """Upsert the session's note."""
        now = utc_now_iso()
        self._execute(
            """
            INSERT INTO session_notes (session_id, note, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET note = excluded.note, updated_at = excluded.updated_at
            """,
            (session_id, note, now),
        )

    def clear_note(self, session_id: str) -> bool:
        """Delete the session's note. Returns True if a row was removed."""
        with self._lock:
            conn = self._conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM session_notes WHERE session_id = ?", (session_id,))
            deleted = cur.rowcount
            conn.commit()
            conn.close()
        return deleted > 0
