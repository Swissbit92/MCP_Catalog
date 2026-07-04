# src/coordinator/repositories/wallet_flow_repository.py
"""Durable state for the multi-turn guided wallet-creation flow.

Replaces the former ``_wallet_flows`` module global in
``services/query_handler_service.py`` (audit step 7): a process-global dict is
lost on restart and is unsafe under multiple worker processes. This SQLite-backed
store keys the flow by ``session_id`` and persists only the **non-secret** step
state.

SECURITY — the BIP39 mnemonic is deliberately NOT a column here. It is generated,
displayed once, and (in the flow) only ever wiped — it is never re-read across
turns, so persisting it would put a seed phrase on disk (WAL/backups) for zero
functional benefit. It stays a request-local variable in the step handler and
never outlives the request that creates it.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)

# Abandoned half-finished flows are swept after this many seconds (guided UI flow;
# a real user finishes in a minute or two). Applied on startup + on demand.
FLOW_TTL_SECONDS = 1800  # 30 minutes

# Columns persisted from the flow-state dict (mnemonic intentionally excluded).
_FIELDS = ("step", "user_id", "wallet_name", "public_address", "slots_used", "slots_max")


class WalletFlowRepository(BaseRepository):
    """Persist the guided wallet-creation flow state (no secrets)."""

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        self._execute("""
            CREATE TABLE IF NOT EXISTS wallet_flow_state (
                session_id     TEXT PRIMARY KEY,
                step           INTEGER NOT NULL,
                user_id        TEXT NOT NULL,
                wallet_name    TEXT,
                public_address TEXT,
                slots_used     INTEGER,
                slots_max      INTEGER,
                updated_at     TEXT NOT NULL
            )
        """)

    def get(self, session_id: str) -> Optional[Dict]:
        """Return the flow-state row for *session_id* (dict), or None."""
        if not session_id:
            return None
        return self._fetchone_dict(
            "SELECT * FROM wallet_flow_state WHERE session_id = ?", (session_id,)
        )

    def upsert(self, session_id: str, state: Dict) -> None:
        """Insert or replace the flow state for *session_id*.

        Reads only the known non-secret columns from *state*; any extra keys
        (e.g. a transient ``mnemonic``) are ignored and never written.
        """
        self._execute(
            """
            INSERT OR REPLACE INTO wallet_flow_state
                (session_id, step, user_id, wallet_name, public_address,
                 slots_used, slots_max, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                int(state.get("step", 1)),
                state.get("user_id") or "default_user",
                state.get("wallet_name"),
                state.get("public_address"),
                state.get("slots_used"),
                state.get("slots_max"),
                self._now(),
            ),
        )

    def delete(self, session_id: str) -> None:
        """Remove the flow state for *session_id* (flow complete / aborted / reset)."""
        if not session_id:
            return
        self._execute("DELETE FROM wallet_flow_state WHERE session_id = ?", (session_id,))

    def sweep_stale(self, ttl_seconds: int = FLOW_TTL_SECONDS) -> int:
        """Delete abandoned flows older than *ttl_seconds*. Returns rows removed."""
        cutoff = (
            datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=ttl_seconds)
        ).isoformat(timespec="seconds") + "Z"
        cur = self._execute(
            "DELETE FROM wallet_flow_state WHERE updated_at < ?", (cutoff,)
        )
        removed = cur.rowcount if cur is not None and cur.rowcount and cur.rowcount > 0 else 0
        if removed:
            logger.info(f"[WalletFlow] Swept {removed} stale wallet-creation flow(s)")
        return removed
