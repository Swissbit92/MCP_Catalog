# src/coordinator/repositories/trade_history_repository.py
"""Local SQLite trade history — MongoDB fallback so trade records are never lost."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class TradeHistoryRepository(BaseRepository):
    """Persists trade records to SQLite as a fallback when MongoDB is unavailable.

    Dual-write pattern: WalletExecutionService writes to both MongoDB (if configured)
    and this table. On read, MongoDB is preferred; this table is the safety net.
    """

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        self._execute("""
            CREATE TABLE IF NOT EXISTS wallet_trades_local (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                wallet_id TEXT NOT NULL,
                tx_signature TEXT,
                pair TEXT NOT NULL,
                action TEXT NOT NULL,
                amount_in REAL NOT NULL,
                amount_in_token TEXT NOT NULL,
                amount_out REAL,
                amount_out_token TEXT NOT NULL,
                slippage_bps INTEGER,
                execution_mode TEXT,
                strategy_id TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        self._execute(
            "CREATE INDEX IF NOT EXISTS idx_trades_user ON wallet_trades_local(user_id)"
        )
        self._execute(
            "CREATE INDEX IF NOT EXISTS idx_trades_wallet ON wallet_trades_local(wallet_id)"
        )

    def record_trade(
        self,
        user_id: str,
        wallet_id: str,
        pair: str,
        action: str,
        amount_in: float,
        amount_in_token: str,
        amount_out_token: str,
        timestamp: str,
        tx_signature: Optional[str] = None,
        amount_out: Optional[float] = None,
        slippage_bps: Optional[int] = None,
        execution_mode: Optional[str] = None,
        strategy_id: Optional[str] = None,
    ) -> Dict:
        """Insert a trade record.

        Returns:
            The inserted trade row as a dict.
        """
        self._execute(
            """
            INSERT INTO wallet_trades_local
                (user_id, wallet_id, tx_signature, pair, action, amount_in,
                 amount_in_token, amount_out, amount_out_token, slippage_bps,
                 execution_mode, strategy_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, wallet_id, tx_signature, pair, action, amount_in,
                amount_in_token, amount_out, amount_out_token, slippage_bps,
                execution_mode, strategy_id, timestamp,
            ),
        )
        row = self._fetchone_dict(
            "SELECT * FROM wallet_trades_local WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        logger.info(f"[TradeHistory] Trade recorded locally: {pair} {action} for user={user_id}")
        return row  # type: ignore[return-value]

    def get_user_trades(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get recent trades for a user, newest first."""
        return self._fetchall_list(
            "SELECT * FROM wallet_trades_local WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )

    def get_wallet_trades(self, wallet_id: str, limit: int = 50) -> List[Dict]:
        """Get recent trades for a specific wallet, newest first."""
        return self._fetchall_list(
            "SELECT * FROM wallet_trades_local WHERE wallet_id = ? ORDER BY id DESC LIMIT ?",
            (wallet_id, limit),
        )

    def get_trade_count(self, user_id: str) -> int:
        """Get total trade count for a user."""
        row = self._fetchone_dict(
            "SELECT COUNT(*) as cnt FROM wallet_trades_local WHERE user_id = ?",
            (user_id,),
        )
        return row["cnt"] if row else 0

    def get_total_volume(self, user_id: str) -> float:
        """Get total USDC volume traded by a user (approximation from amount_in where token is USDC/USDT)."""
        row = self._fetchone_dict(
            """
            SELECT COALESCE(SUM(amount_in), 0.0) as vol
            FROM wallet_trades_local
            WHERE user_id = ? AND amount_in_token IN ('USDC', 'USDT')
            """,
            (user_id,),
        )
        return row["vol"] if row else 0.0
