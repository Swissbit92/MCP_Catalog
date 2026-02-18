"""
User repository for OAuth-authenticated users.
Stores Google OAuth user data (sub, email, display_name, avatar_url).
"""
from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()


def _get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def upsert_user(
    db_path: str,
    google_sub: str,
    email: Optional[str] = None,
    display_name: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> dict:
    """Insert or update a user by Google sub claim. Returns the user record."""
    with _lock:
        conn = _get_conn(db_path)
        try:
            now = datetime.utcnow().isoformat()
            conn.execute(
                """
                INSERT INTO users (google_sub, email, display_name, avatar_url, created_at, last_login)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(google_sub) DO UPDATE SET
                    email        = excluded.email,
                    display_name = excluded.display_name,
                    avatar_url   = excluded.avatar_url,
                    last_login   = excluded.last_login
                """,
                (google_sub, email, display_name, avatar_url, now, now),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM users WHERE google_sub = ?", (google_sub,)
            ).fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()


def get_user_by_sub(db_path: str, google_sub: str) -> Optional[dict]:
    """Retrieve a user by Google sub claim. Returns None if not found."""
    with _lock:
        conn = _get_conn(db_path)
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE google_sub = ?", (google_sub,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
