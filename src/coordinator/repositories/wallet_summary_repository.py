# src/coordinator/repositories/wallet_summary_repository.py
"""Pre-computed wallet activity summaries and balance cache for AI context injection."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class WalletSummaryRepository(BaseRepository):
    """Stores per-user activity summaries and per-wallet balance snapshots.

    These tables power the enriched wallet state prompt injection so the AI
    has reliable, deterministic context about wallet count, last trade, and
    cached balances — without needing to call tools every message.
    """

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        # Per-user aggregated activity summary
        self._execute("""
            CREATE TABLE IF NOT EXISTS wallet_activity_summary (
                user_id TEXT PRIMARY KEY,
                active_wallet_count INTEGER DEFAULT 0,
                total_wallets_ever INTEGER DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                total_volume_usdc REAL DEFAULT 0.0,
                last_trade_timestamp TEXT,
                last_trade_pair TEXT,
                last_trade_action TEXT,
                active_strategies INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL
            )
        """)

        # Per-wallet cached balance (updated on every wallet_get_balances call)
        self._execute("""
            CREATE TABLE IF NOT EXISTS wallet_balance_cache (
                wallet_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                sol_balance REAL,
                token_count INTEGER DEFAULT 0,
                is_unlocked INTEGER DEFAULT 0,
                last_checked TEXT
            )
        """)

    # ---- Activity Summary ----

    def get_summary(self, user_id: str) -> Optional[Dict]:
        """Get the activity summary for a user."""
        return self._fetchone_dict(
            "SELECT * FROM wallet_activity_summary WHERE user_id = ?", (user_id,)
        )

    def upsert_summary(
        self,
        user_id: str,
        active_wallet_count: Optional[int] = None,
        total_wallets_ever: Optional[int] = None,
        total_trades: Optional[int] = None,
        total_volume_usdc: Optional[float] = None,
        last_trade_timestamp: Optional[str] = None,
        last_trade_pair: Optional[str] = None,
        last_trade_action: Optional[str] = None,
        active_strategies: Optional[int] = None,
    ) -> None:
        """Create or update the activity summary for a user.

        Only provided (non-None) fields are updated on conflict.
        """
        now = self._now()
        existing = self.get_summary(user_id)

        if not existing:
            self._execute(
                """
                INSERT INTO wallet_activity_summary
                    (user_id, active_wallet_count, total_wallets_ever, total_trades,
                     total_volume_usdc, last_trade_timestamp, last_trade_pair,
                     last_trade_action, active_strategies, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    active_wallet_count or 0,
                    total_wallets_ever or 0,
                    total_trades or 0,
                    total_volume_usdc or 0.0,
                    last_trade_timestamp,
                    last_trade_pair,
                    last_trade_action,
                    active_strategies or 0,
                    now,
                ),
            )
            return

        # Update only non-None fields
        updates = []
        params = []
        if active_wallet_count is not None:
            updates.append("active_wallet_count = ?")
            params.append(active_wallet_count)
        if total_wallets_ever is not None:
            updates.append("total_wallets_ever = ?")
            params.append(total_wallets_ever)
        if total_trades is not None:
            updates.append("total_trades = ?")
            params.append(total_trades)
        if total_volume_usdc is not None:
            updates.append("total_volume_usdc = ?")
            params.append(total_volume_usdc)
        if last_trade_timestamp is not None:
            updates.append("last_trade_timestamp = ?")
            params.append(last_trade_timestamp)
        if last_trade_pair is not None:
            updates.append("last_trade_pair = ?")
            params.append(last_trade_pair)
        if last_trade_action is not None:
            updates.append("last_trade_action = ?")
            params.append(last_trade_action)
        if active_strategies is not None:
            updates.append("active_strategies = ?")
            params.append(active_strategies)

        if not updates:
            return

        updates.append("updated_at = ?")
        params.append(now)
        params.append(user_id)

        self._execute(
            f"UPDATE wallet_activity_summary SET {', '.join(updates)} WHERE user_id = ?",
            tuple(params),
        )

    def increment_trade(
        self,
        user_id: str,
        volume_usdc: float,
        pair: str,
        action: str,
        timestamp: str,
    ) -> None:
        """Atomically increment trade count and volume, updating last trade info."""
        now = self._now()
        existing = self.get_summary(user_id)
        if not existing:
            self.upsert_summary(
                user_id=user_id,
                total_trades=1,
                total_volume_usdc=volume_usdc,
                last_trade_timestamp=timestamp,
                last_trade_pair=pair,
                last_trade_action=action,
            )
            return

        self._execute(
            """
            UPDATE wallet_activity_summary
            SET total_trades = total_trades + 1,
                total_volume_usdc = total_volume_usdc + ?,
                last_trade_timestamp = ?,
                last_trade_pair = ?,
                last_trade_action = ?,
                updated_at = ?
            WHERE user_id = ?
            """,
            (volume_usdc, timestamp, pair, action, now, user_id),
        )

    # ---- Balance Cache ----

    def get_balance_cache(self, wallet_id: str) -> Optional[Dict]:
        """Get cached balance for a wallet."""
        return self._fetchone_dict(
            "SELECT * FROM wallet_balance_cache WHERE wallet_id = ?", (wallet_id,)
        )

    def get_user_balances(self, user_id: str) -> List[Dict]:
        """Get all cached balances for a user's wallets."""
        return self._fetchall_list(
            "SELECT * FROM wallet_balance_cache WHERE user_id = ?", (user_id,)
        )

    def upsert_balance(
        self,
        wallet_id: str,
        user_id: str,
        sol_balance: Optional[float] = None,
        token_count: Optional[int] = None,
        is_unlocked: Optional[int] = None,
    ) -> None:
        """Create or update the balance cache for a wallet."""
        now = self._now()
        existing = self.get_balance_cache(wallet_id)

        if not existing:
            self._execute(
                """
                INSERT INTO wallet_balance_cache
                    (wallet_id, user_id, sol_balance, token_count, is_unlocked, last_checked)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (wallet_id, user_id, sol_balance, token_count or 0, is_unlocked or 0, now),
            )
            return

        updates = []
        params = []
        if sol_balance is not None:
            updates.append("sol_balance = ?")
            params.append(sol_balance)
        if token_count is not None:
            updates.append("token_count = ?")
            params.append(token_count)
        if is_unlocked is not None:
            updates.append("is_unlocked = ?")
            params.append(is_unlocked)

        if not updates:
            return

        updates.append("last_checked = ?")
        params.append(now)
        params.append(wallet_id)

        self._execute(
            f"UPDATE wallet_balance_cache SET {', '.join(updates)} WHERE wallet_id = ?",
            tuple(params),
        )

    def set_unlock_state(self, wallet_id: str, is_unlocked: bool) -> None:
        """Update the unlock state for a wallet in the cache."""
        self._execute(
            "UPDATE wallet_balance_cache SET is_unlocked = ? WHERE wallet_id = ?",
            (1 if is_unlocked else 0, wallet_id),
        )

    def reset_all_unlock_states(self) -> None:
        """Reset all wallets to locked (called on server startup)."""
        self._execute("UPDATE wallet_balance_cache SET is_unlocked = 0")
        logger.info("[WalletSummary] All wallet unlock states reset to locked")
