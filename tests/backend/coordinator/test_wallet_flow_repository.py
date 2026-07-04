# tests/backend/coordinator/test_wallet_flow_repository.py
"""Unit tests for WalletFlowRepository (guided wallet-creation flow state).

Uses a temporary SQLite file per test (via tmp_path). No network, no Ollama.
Locks in the security invariant that the BIP39 mnemonic is NEVER persisted.
"""
from __future__ import annotations

import pytest

from src.coordinator.repositories.wallet_flow_repository import WalletFlowRepository


@pytest.fixture()
def repo(tmp_path):
    return WalletFlowRepository(str(tmp_path / "flow.db"))


def test_get_missing_returns_none(repo):
    assert repo.get("nope") is None
    assert repo.get("") is None


def test_upsert_then_get_roundtrip(repo):
    repo.upsert("s1", {"step": 1, "user_id": "u", "wallet_name": "W",
                       "slots_used": 0, "slots_max": 3})
    row = repo.get("s1")
    assert row["step"] == 1
    assert row["user_id"] == "u"
    assert row["wallet_name"] == "W"
    assert row["slots_used"] == 0 and row["slots_max"] == 3


def test_upsert_replaces_in_place(repo):
    repo.upsert("s1", {"step": 1, "user_id": "u", "wallet_name": "W"})
    repo.upsert("s1", {"step": 3, "user_id": "u", "wallet_name": "W",
                       "public_address": "ADDR"})
    row = repo.get("s1")
    assert row["step"] == 3
    assert row["public_address"] == "ADDR"
    # still a single row for the session
    assert repo._fetchall_list("SELECT session_id FROM wallet_flow_state", ()) == [
        {"session_id": "s1"}
    ]


def test_mnemonic_is_never_persisted(repo):
    """The seed phrase must never reach disk — the core security invariant."""
    seed = "abandon abandon abandon ... about"
    repo.upsert("s1", {"step": 3, "user_id": "u", "wallet_name": "W",
                       "public_address": "ADDR", "mnemonic": seed})
    row = repo.get("s1")
    assert "mnemonic" not in row
    # and the secret value appears in no column
    assert seed not in " ".join(str(v) for v in row.values())


def test_delete_removes_row(repo):
    repo.upsert("s1", {"step": 1, "user_id": "u"})
    repo.delete("s1")
    assert repo.get("s1") is None
    repo.delete("s1")  # idempotent / no error
    repo.delete("")    # no-op on empty


def test_sweep_stale_removes_only_expired(repo):
    repo.upsert("fresh", {"step": 1, "user_id": "u"})
    repo.upsert("old", {"step": 2, "user_id": "u"})
    # Backdate 'old' well past the TTL by rewriting its updated_at directly.
    repo._execute(
        "UPDATE wallet_flow_state SET updated_at = ? WHERE session_id = ?",
        ("2000-01-01T00:00:00Z", "old"),
    )
    removed = repo.sweep_stale(ttl_seconds=1)
    assert removed == 1
    assert repo.get("old") is None
    assert repo.get("fresh") is not None
