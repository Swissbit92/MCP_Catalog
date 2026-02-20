"""
User repository for OAuth-authenticated users.
Stores Google OAuth user data (sub, email, display_name, avatar_url).
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Optional

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """Repository for OAuth user records (Google sub, email, display_name, avatar_url)."""

    def upsert_user(
        self,
        google_sub: str,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> dict:
        """Insert or update a user by Google sub claim. Returns the user record."""
        now = self._now()
        self._execute(
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
        row = self._fetchone_dict(
            "SELECT * FROM users WHERE google_sub = ?", (google_sub,)
        )
        return row or {}

    def get_user_by_sub(self, google_sub: str) -> Optional[dict]:
        """Retrieve a user by Google sub claim. Returns None if not found."""
        return self._fetchone_dict(
            "SELECT * FROM users WHERE google_sub = ?", (google_sub,)
        )

    def get_onboarding_status(self, google_sub: str) -> bool:
        """Return True if the user has completed onboarding."""
        row = self._fetchone_dict(
            "SELECT onboarding_completed FROM users WHERE google_sub = ?",
            (google_sub,),
        )
        return bool(row["onboarding_completed"]) if row else False

    def set_onboarding_completed(self, google_sub: str) -> None:
        """Mark onboarding as completed. Upserts the user row for local_user."""
        now = self._now()
        self._execute(
            """
            INSERT INTO users (google_sub, onboarding_completed, created_at, last_login)
            VALUES (?, 1, ?, ?)
            ON CONFLICT(google_sub) DO UPDATE SET onboarding_completed = 1
            """,
            (google_sub, now, now),
        )


# ── Module-level backward-compatible wrappers ────────────────────────────────
# auth.py calls these as user_repository.upsert_user(db_path=..., ...).
# These thin delegates keep auth.py unchanged while using the class internally.

def upsert_user(
    db_path: str,
    google_sub: str,
    email: Optional[str] = None,
    display_name: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> dict:
    return UserRepository(db_path).upsert_user(google_sub, email, display_name, avatar_url)


def get_user_by_sub(db_path: str, google_sub: str) -> Optional[dict]:
    return UserRepository(db_path).get_user_by_sub(google_sub)


def get_onboarding_status(db_path: str, google_sub: str) -> bool:
    return UserRepository(db_path).get_onboarding_status(google_sub)


def set_onboarding_completed(db_path: str, google_sub: str) -> None:
    UserRepository(db_path).set_onboarding_completed(google_sub)
