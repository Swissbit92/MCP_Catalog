# src/coordinator/repositories/wallet_registry_repository.py
"""Registry for multi-wallet management with hard 3-wallet limit enforcement."""
from __future__ import annotations

import uuid
import logging
from typing import Dict, List, Optional, Tuple

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)

MAX_ACTIVE_WALLETS = 3


class WalletRegistryRepository(BaseRepository):
    """Per-user wallet registry with count enforcement and slot management.

    Tracks ALL wallets (active + deleted). The 3-wallet limit is enforced
    at the repository level — even if the LLM hallucinates and tries to
    create a 4th wallet, this layer rejects it.
    """

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        self._execute("""
            CREATE TABLE IF NOT EXISTS wallet_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                wallet_id TEXT NOT NULL UNIQUE,
                wallet_name TEXT NOT NULL DEFAULT 'My Wallet',
                public_address TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                slot_number INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                deleted_at TEXT,
                updated_at TEXT NOT NULL
            )
        """)
        self._execute(
            "CREATE INDEX IF NOT EXISTS idx_registry_user ON wallet_registry(user_id)"
        )
        self._execute(
            "CREATE INDEX IF NOT EXISTS idx_registry_status ON wallet_registry(user_id, status)"
        )

    # ---- Guardrail: wallet count enforcement ----

    def can_create_wallet(self, user_id: str) -> Tuple[bool, int, int]:
        """Check if user can create a new wallet.

        Returns:
            (allowed, active_count, next_slot_number)
            If allowed is False, active_count == MAX_ACTIVE_WALLETS.
        """
        active = self._fetchall_list(
            "SELECT slot_number FROM wallet_registry WHERE user_id = ? AND status = 'active'",
            (user_id,),
        )
        count = len(active)
        used_slots = {r["slot_number"] for r in active}
        next_slot = next((s for s in [1, 2, 3] if s not in used_slots), None)
        if next_slot is None or count >= MAX_ACTIVE_WALLETS:
            return (False, count, 0)
        return (True, count, next_slot)

    # ---- CRUD ----

    def register_wallet(
        self,
        user_id: str,
        wallet_name: str,
        public_address: str,
    ) -> Dict:
        """Register a new wallet, enforcing the 3-wallet limit.

        Raises:
            ValueError: If user already has MAX_ACTIVE_WALLETS active wallets.

        Returns:
            The newly created wallet registry row as a dict.
        """
        allowed, count, next_slot = self.can_create_wallet(user_id)
        if not allowed:
            raise ValueError(
                f"User {user_id} already has {count} active wallets (max {MAX_ACTIVE_WALLETS}). "
                "Delete one before creating a new wallet."
            )

        wallet_id = str(uuid.uuid4())
        now = self._now()
        self._execute(
            """
            INSERT INTO wallet_registry
                (user_id, wallet_id, wallet_name, public_address, status, slot_number, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'active', ?, ?, ?)
            """,
            (user_id, wallet_id, wallet_name, public_address, next_slot, now, now),
        )
        row = self._fetchone_dict(
            "SELECT * FROM wallet_registry WHERE wallet_id = ?", (wallet_id,)
        )
        logger.info(
            f"[WalletRegistry] Registered wallet slot={next_slot} for user={user_id} "
            f"(total active: {count + 1}/{MAX_ACTIVE_WALLETS})"
        )
        return row  # type: ignore[return-value]

    def get_active_wallets(self, user_id: str) -> List[Dict]:
        """Get all active wallets for a user, ordered by slot number."""
        return self._fetchall_list(
            "SELECT * FROM wallet_registry WHERE user_id = ? AND status = 'active' ORDER BY slot_number",
            (user_id,),
        )

    def get_wallet_by_id(self, wallet_id: str) -> Optional[Dict]:
        """Get a single wallet by its stable UUID."""
        return self._fetchone_dict(
            "SELECT * FROM wallet_registry WHERE wallet_id = ?", (wallet_id,)
        )

    def get_wallet_by_address(self, public_address: str) -> Optional[Dict]:
        """Look up a wallet by its Solana public address."""
        return self._fetchone_dict(
            "SELECT * FROM wallet_registry WHERE public_address = ? AND status = 'active'",
            (public_address,),
        )

    def soft_delete_wallet(self, wallet_id: str) -> bool:
        """Soft-delete a wallet (status → 'deleted'), freeing the slot.

        Returns True if a row was updated, False if wallet_id not found.
        """
        now = self._now()
        self._execute(
            "UPDATE wallet_registry SET status = 'deleted', deleted_at = ?, updated_at = ? WHERE wallet_id = ? AND status = 'active'",
            (now, now, wallet_id),
        )
        row = self._fetchone_dict(
            "SELECT * FROM wallet_registry WHERE wallet_id = ? AND status = 'deleted'",
            (wallet_id,),
        )
        if row:
            logger.info(f"[WalletRegistry] Wallet {wallet_id} soft-deleted")
            return True
        return False

    def soft_delete_by_address(self, user_id: str, public_address: str) -> bool:
        """Soft-delete by public address (used by chat deletion flow)."""
        now = self._now()
        self._execute(
            "UPDATE wallet_registry SET status = 'deleted', deleted_at = ?, updated_at = ? "
            "WHERE user_id = ? AND public_address = ? AND status = 'active'",
            (now, now, user_id, public_address),
        )
        row = self._fetchone_dict(
            "SELECT * FROM wallet_registry WHERE user_id = ? AND public_address = ? AND status = 'deleted'",
            (user_id, public_address),
        )
        return row is not None

    def get_active_count(self, user_id: str) -> int:
        """Return the number of active wallets for a user."""
        row = self._fetchone_dict(
            "SELECT COUNT(*) as cnt FROM wallet_registry WHERE user_id = ? AND status = 'active'",
            (user_id,),
        )
        return row["cnt"] if row else 0

    def get_all_wallets(self, user_id: str) -> List[Dict]:
        """Get all wallets (active + deleted) for audit/history."""
        return self._fetchall_list(
            "SELECT * FROM wallet_registry WHERE user_id = ? ORDER BY slot_number, created_at",
            (user_id,),
        )
