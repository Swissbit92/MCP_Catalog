# src/coordinator/repositories/wallet_repository.py
"""Repository for user_wallets table — stores encrypted Solana keypairs."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class WalletRepository(BaseRepository):
    """Repository for managing encrypted user wallets."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize with database path and ensure tables exist."""
        super().__init__(db_path)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """Create user_wallets table and indexes if they don't exist."""
        self._execute("""
            CREATE TABLE IF NOT EXISTS user_wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                wallet_name TEXT NOT NULL DEFAULT 'My Wallet',
                public_address TEXT NOT NULL,
                encrypted_private_key TEXT NOT NULL,
                key_salt TEXT NOT NULL,
                key_nonce TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)
        self._execute("""
            CREATE INDEX IF NOT EXISTS idx_wallets_user_id ON user_wallets(user_id)
        """)

    def create_wallet(
        self,
        user_id: str,
        wallet_name: str,
        public_address: str,
        encrypted_private_key: str,
        key_salt: str,
        key_nonce: str,
    ) -> Dict:
        """Create a new wallet entry for a user.

        Args:
            user_id: Seeker/user identifier
            wallet_name: Human-readable wallet label
            public_address: Solana public key (base58)
            encrypted_private_key: AES-GCM ciphertext (hex or base64)
            key_salt: Salt used for key derivation (hex)
            key_nonce: Nonce used for AES-GCM encryption (hex)

        Returns:
            Dict with the created wallet record
        """
        now = self._now()
        self._execute(
            """
            INSERT INTO user_wallets
                (user_id, wallet_name, public_address, encrypted_private_key,
                 key_salt, key_nonce, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (user_id, wallet_name, public_address, encrypted_private_key,
             key_salt, key_nonce, now),
        )
        row = self._fetchone_dict(
            "SELECT * FROM user_wallets WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        return row  # type: ignore[return-value]

    def get_active_wallet(self, user_id: str) -> Optional[Dict]:
        """Get the active wallet for a user.

        Args:
            user_id: Seeker/user identifier

        Returns:
            Wallet dict, or None if no active wallet exists
        """
        return self._fetchone_dict(
            "SELECT * FROM user_wallets WHERE user_id = ? AND is_active = 1 ORDER BY id DESC LIMIT 1",
            (user_id,),
        )

    def get_all_wallets(self, user_id: str) -> List[Dict]:
        """Get all wallets for a user (active and inactive).

        Args:
            user_id: Seeker/user identifier

        Returns:
            List of wallet dicts ordered by creation time desc
        """
        return self._fetchall_list(
            "SELECT * FROM user_wallets WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        )

    def deactivate_wallet(self, wallet_id: int) -> bool:
        """Deactivate a wallet by ID (soft delete).

        Args:
            wallet_id: Primary key of the wallet row

        Returns:
            True if a row was updated, False if wallet_id not found
        """
        self._execute(
            "UPDATE user_wallets SET is_active = 0 WHERE id = ?",
            (wallet_id,),
        )
        row = self._fetchone_dict(
            "SELECT id FROM user_wallets WHERE id = ?",
            (wallet_id,),
        )
        return row is not None
