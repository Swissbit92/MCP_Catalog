"""Repository for user profile database operations.

Handles CRUD operations for user profiles and user-session associations,
enabling cross-session memory for personas.
"""

from __future__ import annotations

import sqlite3
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from .base_repository import BaseRepository
from ..user_profile import UserProfile

logger = logging.getLogger(__name__)


class UserProfileRepository(BaseRepository):
    """Database repository for user profiles.

    Manages persistent user profiles that accumulate knowledge across
    multiple chat sessions with different personas.
    """

    def create_profile(self, user_id: str) -> UserProfile:
        """Create a new user profile.

        Args:
            user_id: Unique identifier for the user

        Returns:
            Newly created UserProfile instance
        """
        profile = UserProfile(user_id)
        now = datetime.utcnow().isoformat()

        try:
            self._execute("""
                INSERT INTO user_profiles (user_id, created_at, updated_at, profile_data)
                VALUES (?, ?, ?, ?)
            """, (user_id, now, now, profile.to_json()))

            logger.info(f"[UserProfileRepo] Created profile for user: {user_id}")

        except sqlite3.IntegrityError:
            logger.warning(f"[UserProfileRepo] Profile already exists for user: {user_id}")
            # Return existing profile
            return self.get_profile(user_id)

        return profile

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by ID.

        Args:
            user_id: User identifier

        Returns:
            UserProfile instance or None if not found
        """
        row = self._fetchone_dict("""
            SELECT profile_data FROM user_profiles WHERE user_id = ?
        """, (user_id,))

        if row:
            profile = UserProfile.from_json(user_id, row["profile_data"])
            return profile
        else:
            return None

    def update_profile(self, profile: UserProfile) -> None:
        """Update an existing user profile.

        Args:
            profile: UserProfile instance to save
        """
        now = datetime.utcnow().isoformat()

        cur = self._execute("""
            UPDATE user_profiles
            SET profile_data = ?, updated_at = ?
            WHERE user_id = ?
        """, (profile.to_json(), now, profile.user_id))

        if cur.rowcount == 0:
            logger.warning(f"[UserProfileRepo] Profile not found for update: {profile.user_id}")
        else:
            logger.debug(f"[UserProfileRepo] Updated profile for user: {profile.user_id}")

    def delete_profile(self, user_id: str) -> bool:
        """Delete a user profile.

        Also deletes all user_sessions associations via CASCADE.

        Args:
            user_id: User identifier

        Returns:
            True if deleted, False if not found
        """
        cur = self._execute("DELETE FROM user_profiles WHERE user_id = ?", (user_id,))
        deleted = cur.rowcount > 0

        if deleted:
            logger.info(f"[UserProfileRepo] Deleted profile for user: {user_id}")
        else:
            logger.warning(f"[UserProfileRepo] Profile not found for deletion: {user_id}")

        return deleted

    def get_or_create_profile(self, user_id: str) -> UserProfile:
        """Get existing profile or create new one if doesn't exist.

        Args:
            user_id: User identifier

        Returns:
            UserProfile instance (existing or newly created)
        """
        profile = self.get_profile(user_id)

        if profile is None:
            profile = self.create_profile(user_id)

        return profile

    def list_all_profiles(self) -> List[Dict[str, Any]]:
        """List all user profiles with basic stats.

        Returns:
            List of profile summary dicts
        """
        rows = self._fetchall_list("""
            SELECT user_id, created_at, updated_at, profile_data
            FROM user_profiles
            ORDER BY updated_at DESC
        """)

        profiles = []

        for row in rows:
            profile = UserProfile.from_json(row["user_id"], row["profile_data"])
            stats = profile.get_stats()
            stats.update({
                "created_at": row["created_at"],
                "db_updated_at": row["updated_at"]
            })
            profiles.append(stats)

        return profiles

    def link_session_to_user(self, user_id: str, session_id: str) -> None:
        """Link a chat session to a user profile.

        Args:
            user_id: User identifier
            session_id: Chat session identifier
        """
        now = datetime.utcnow().isoformat()

        cur = self._execute("""
            INSERT OR IGNORE INTO user_sessions (user_id, session_id, created_at)
            VALUES (?, ?, ?)
        """, (user_id, session_id, now))

        if cur.rowcount > 0:
            logger.debug(f"[UserProfileRepo] Linked session {session_id} to user {user_id}")
        else:
            logger.debug(f"[UserProfileRepo] Session {session_id} already linked to user {user_id}")

    def get_user_sessions(self, user_id: str) -> List[str]:
        """Get all session IDs associated with a user.

        Args:
            user_id: User identifier

        Returns:
            List of session IDs
        """
        rows = self._fetchall_list("""
            SELECT session_id FROM user_sessions
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))

        return [row["session_id"] for row in rows]

    def get_session_user(self, session_id: str) -> Optional[str]:
        """Get the user ID associated with a session.

        Args:
            session_id: Chat session identifier

        Returns:
            User ID or None if not linked
        """
        row = self._fetchone_dict("""
            SELECT user_id FROM user_sessions WHERE session_id = ?
        """, (session_id,))

        return row["user_id"] if row else None

    def unlink_session_from_user(self, user_id: str, session_id: str) -> bool:
        """Unlink a session from a user.

        Args:
            user_id: User identifier
            session_id: Session identifier

        Returns:
            True if unlinked, False if association didn't exist
        """
        cur = self._execute("""
            DELETE FROM user_sessions
            WHERE user_id = ? AND session_id = ?
        """, (user_id, session_id))

        deleted = cur.rowcount > 0

        if deleted:
            logger.debug(f"[UserProfileRepo] Unlinked session {session_id} from user {user_id}")

        return deleted

    def get_user_by_name(self, name: str) -> Optional[str]:
        """Find user ID by name (fuzzy search).

        Useful for identifying returning users who haven't been linked yet.

        Args:
            name: User's name

        Returns:
            User ID or None if no match
        """
        name_lower = name.lower()

        rows = self._fetchall_list("""
            SELECT user_id, profile_data FROM user_profiles
        """)

        for row in rows:
            profile = UserProfile.from_json(row["user_id"], row["profile_data"])
            if profile.data.get("name"):
                if profile.data["name"].lower() == name_lower:
                    return row["user_id"]

        return None
