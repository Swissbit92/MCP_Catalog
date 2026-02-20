# src/coordinator/repositories/trade_proposal_repository.py
"""Repository for trade_proposals table — ephemeral HITL proposal records (5-min TTL)."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class TradeProposalRepository(BaseRepository):
    """Repository for managing trade proposals with 5-minute TTL."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize with database path and ensure tables exist."""
        super().__init__(db_path)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """Create trade_proposals table and indexes if they don't exist."""
        self._execute("""
            CREATE TABLE IF NOT EXISTS trade_proposals (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                proposal_type TEXT NOT NULL DEFAULT 'swap',
                proposal_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)
        self._execute("""
            CREATE INDEX IF NOT EXISTS idx_proposals_user_id
            ON trade_proposals(user_id, status)
        """)

    @staticmethod
    def _utcnow() -> datetime:
        """Return timezone-aware UTC datetime."""
        return datetime.now(timezone.utc)

    @staticmethod
    def _iso(dt: datetime) -> str:
        """Format datetime as ISO-8601 UTC string."""
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def create_proposal(
        self,
        user_id: str,
        proposal_type: str,
        proposal_data: Dict,
        ttl_seconds: int = 300,
    ) -> Dict:
        """Create a new trade proposal.

        Args:
            user_id: Seeker/user identifier
            proposal_type: 'swap' | 'strategy' | etc.
            proposal_data: Proposal details dict (serialized to JSON)
            ttl_seconds: Time-to-live in seconds (default 300 = 5 minutes)

        Returns:
            Dict with the created proposal record
        """
        proposal_id = str(uuid.uuid4())
        now = self._utcnow()
        expires = now + timedelta(seconds=ttl_seconds)
        now_str = self._iso(now)
        expires_str = self._iso(expires)
        proposal_json = json.dumps(proposal_data)

        self._execute(
            """
            INSERT INTO trade_proposals
                (id, user_id, proposal_type, proposal_json, status, created_at, expires_at)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """,
            (proposal_id, user_id, proposal_type, proposal_json, now_str, expires_str),
        )

        return {
            "id": proposal_id,
            "user_id": user_id,
            "proposal_type": proposal_type,
            "proposal_json": proposal_json,
            "status": "pending",
            "created_at": now_str,
            "expires_at": expires_str,
        }

    def get_proposal(self, proposal_id: str) -> Optional[Dict]:
        """Get a proposal by ID, returning None if expired or not found.

        Args:
            proposal_id: UUID string

        Returns:
            Proposal dict, or None if not found or already expired
        """
        row = self._fetchone_dict(
            "SELECT * FROM trade_proposals WHERE id = ?",
            (proposal_id,),
        )
        if row is None:
            return None

        # Check expiry
        try:
            expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
            if self._utcnow() > expires_at and row["status"] == "pending":
                # Mark expired in-place
                self._execute(
                    "UPDATE trade_proposals SET status = 'expired' WHERE id = ?",
                    (proposal_id,),
                )
                return None
        except (KeyError, ValueError):
            pass

        return row

    def confirm_proposal(self, proposal_id: str) -> bool:
        """Mark a proposal as confirmed.

        Args:
            proposal_id: UUID string

        Returns:
            True if updated, False if not found or already in terminal state
        """
        row = self.get_proposal(proposal_id)
        if row is None or row.get("status") != "pending":
            return False
        self._execute(
            "UPDATE trade_proposals SET status = 'confirmed' WHERE id = ?",
            (proposal_id,),
        )
        return True

    def cancel_proposal(self, proposal_id: str) -> bool:
        """Mark a proposal as cancelled.

        Args:
            proposal_id: UUID string

        Returns:
            True if updated, False if not found or already in terminal state
        """
        row = self._fetchone_dict(
            "SELECT status FROM trade_proposals WHERE id = ?",
            (proposal_id,),
        )
        if row is None or row.get("status") not in ("pending",):
            return False
        self._execute(
            "UPDATE trade_proposals SET status = 'cancelled' WHERE id = ?",
            (proposal_id,),
        )
        return True

    def expire_old_proposals(self) -> int:
        """Set status='expired' for all pending proposals past their expires_at.

        Returns:
            Number of proposals expired
        """
        now_str = self._iso(self._utcnow())
        # Fetch IDs to expire first (SQLite lacks RETURNING on UPDATE in older versions)
        rows = self._fetchall_list(
            "SELECT id FROM trade_proposals WHERE status = 'pending' AND expires_at <= ?",
            (now_str,),
        )
        if not rows:
            return 0
        ids = [r["id"] for r in rows]
        placeholders = ",".join("?" * len(ids))
        self._execute(
            f"UPDATE trade_proposals SET status = 'expired' WHERE id IN ({placeholders})",
            tuple(ids),
        )
        logger.info(f"Expired {len(ids)} trade proposals")
        return len(ids)

    def get_pending_proposals(self, user_id: str) -> List[Dict]:
        """Get all pending (non-expired) proposals for a user.

        Args:
            user_id: Seeker/user identifier

        Returns:
            List of pending proposal dicts
        """
        now_str = self._iso(self._utcnow())
        return self._fetchall_list(
            """
            SELECT * FROM trade_proposals
            WHERE user_id = ?
              AND status = 'pending'
              AND expires_at > ?
            ORDER BY created_at DESC
            """,
            (user_id, now_str),
        )
