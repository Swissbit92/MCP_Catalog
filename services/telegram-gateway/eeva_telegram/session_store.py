"""SQLite-backed mapping of (telegram chat_id, persona_key) -> nephilim session_id.

Stdlib sqlite3 only — no new dependency. The table is keyed on
(chat_id, persona_key) from day one so a future per-chat persona switch is
purely additive; today each chat has exactly one persona so it is effectively
one row per chat.

The DB is a tiny local operational file (data/sessions.sqlite3), not user data
in the privacy sense — it holds only integer chat ids, persona keys, and opaque
session UUIDs, never message content.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chat_sessions (
    chat_id     INTEGER NOT NULL,
    persona_key TEXT    NOT NULL,
    session_id  TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL,
    PRIMARY KEY (chat_id, persona_key)
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


class SessionStore:
    """Persistent chat_id+persona -> session_id map.

    A module-level lock serialises writes; sqlite is opened with
    check_same_thread=False so the single connection is safe across PTB's
    handler threads.
    """

    def __init__(self, db_path: Path | str) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def get(self, chat_id: int, persona_key: str) -> str | None:
        """Return the stored session_id for this chat+persona, or None."""
        with self._lock:
            row = self._conn.execute(
                "SELECT session_id FROM chat_sessions WHERE chat_id = ? AND persona_key = ?",
                (chat_id, persona_key),
            ).fetchone()
        return row["session_id"] if row else None

    def set(self, chat_id: int, persona_key: str, session_id: str) -> None:
        """Insert or replace the mapping for this chat+persona."""
        now = _now()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO chat_sessions (chat_id, persona_key, session_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(chat_id, persona_key) DO UPDATE SET
                    session_id = excluded.session_id,
                    updated_at = excluded.updated_at
                """,
                (chat_id, persona_key, session_id, now, now),
            )
            self._conn.commit()

    def delete(self, chat_id: int, persona_key: str) -> None:
        """Remove the mapping (used when a stored session is gone from the backend)."""
        with self._lock:
            self._conn.execute(
                "DELETE FROM chat_sessions WHERE chat_id = ? AND persona_key = ?",
                (chat_id, persona_key),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
