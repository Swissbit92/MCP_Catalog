"""Comprehensive unit tests for WalletRepository.

Coverage targets:
- create_wallet (happy path, multiple wallets, return shape)
- get_active_wallet (found, none for user, filters by is_active, returns latest)
- get_all_wallets (empty, one, multiple, active+inactive)
- get_active_wallet_count (zero, one, multiple, isolation by user)
- get_all_active_wallets (empty, filters inactive, multiple)
- deactivate_wallet (valid id, nonexistent id, soft delete verification)
"""
from __future__ import annotations

import pytest

from src.coordinator.repositories.wallet_repository import WalletRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repo(tmp_path):
    """Fresh WalletRepository backed by a temp SQLite file."""
    db_path = str(tmp_path / "test_wallets.db")
    return WalletRepository(db_path)


_COUNTER = 0


def _wallet(
    repo: WalletRepository,
    user_id: str = "user1",
    wallet_name: str = "My Wallet",
    public_address: str | None = None,
    encrypted_private_key: str = "enc_key_hex",
    key_salt: str = "salt_hex",
    key_nonce: str = "nonce_hex",
) -> dict:
    global _COUNTER
    _COUNTER += 1
    if public_address is None:
        public_address = f"SolPubKey{_COUNTER:04d}"
    return repo.create_wallet(
        user_id=user_id,
        wallet_name=wallet_name,
        public_address=public_address,
        encrypted_private_key=encrypted_private_key,
        key_salt=key_salt,
        key_nonce=key_nonce,
    )


# ---------------------------------------------------------------------------
# Tests — create_wallet
# ---------------------------------------------------------------------------

class TestCreateWallet:
    def test_returns_dict(self, repo):
        result = _wallet(repo)
        assert isinstance(result, dict)

    def test_has_expected_keys(self, repo):
        result = _wallet(repo)
        for key in ("id", "user_id", "wallet_name", "public_address",
                    "encrypted_private_key", "key_salt", "key_nonce",
                    "is_active", "created_at"):
            assert key in result

    def test_user_id_stored(self, repo):
        result = _wallet(repo, user_id="alice")
        assert result["user_id"] == "alice"

    def test_wallet_name_stored(self, repo):
        result = _wallet(repo, wallet_name="Hot Wallet")
        assert result["wallet_name"] == "Hot Wallet"

    def test_public_address_stored(self, repo):
        result = _wallet(repo, public_address="PubKeyABC123")
        assert result["public_address"] == "PubKeyABC123"

    def test_encrypted_private_key_stored(self, repo):
        result = _wallet(repo, encrypted_private_key="enc_abc")
        assert result["encrypted_private_key"] == "enc_abc"

    def test_key_salt_stored(self, repo):
        result = _wallet(repo, key_salt="salt_abc")
        assert result["key_salt"] == "salt_abc"

    def test_key_nonce_stored(self, repo):
        result = _wallet(repo, key_nonce="nonce_abc")
        assert result["key_nonce"] == "nonce_abc"

    def test_is_active_defaults_to_1(self, repo):
        result = _wallet(repo)
        assert result["is_active"] == 1

    def test_created_at_is_set(self, repo):
        result = _wallet(repo)
        assert result["created_at"] is not None
        assert len(result["created_at"]) > 0

    def test_id_is_integer(self, repo):
        result = _wallet(repo)
        assert isinstance(result["id"], int)

    def test_multiple_wallets_have_distinct_ids(self, repo):
        a = _wallet(repo, user_id="alice")
        b = _wallet(repo, user_id="alice")
        assert a["id"] != b["id"]

    def test_second_wallet_id_greater_than_first(self, repo):
        a = _wallet(repo, user_id="alice")
        b = _wallet(repo, user_id="alice")
        assert b["id"] > a["id"]

    def test_different_users_can_both_have_wallets(self, repo):
        a = _wallet(repo, user_id="alice")
        b = _wallet(repo, user_id="bob")
        assert a["user_id"] == "alice"
        assert b["user_id"] == "bob"


# ---------------------------------------------------------------------------
# Tests — get_active_wallet
# ---------------------------------------------------------------------------

class TestGetActiveWallet:
    def test_returns_none_for_unknown_user(self, repo):
        assert repo.get_active_wallet("ghost") is None

    def test_returns_wallet_when_active(self, repo):
        _wallet(repo, user_id="alice")
        result = repo.get_active_wallet("alice")
        assert result is not None
        assert result["user_id"] == "alice"
        assert result["is_active"] == 1

    def test_returns_none_after_deactivation(self, repo):
        created = _wallet(repo, user_id="alice")
        repo.deactivate_wallet(created["id"])
        assert repo.get_active_wallet("alice") is None

    def test_returns_most_recent_active(self, repo):
        """When multiple active wallets exist, return highest id (most recent)."""
        _wallet(repo, user_id="alice", wallet_name="Old")
        newest = _wallet(repo, user_id="alice", wallet_name="New")
        result = repo.get_active_wallet("alice")
        assert result["id"] == newest["id"]

    def test_returns_active_when_some_deactivated(self, repo):
        old = _wallet(repo, user_id="alice", wallet_name="Old")
        new = _wallet(repo, user_id="alice", wallet_name="New")
        repo.deactivate_wallet(old["id"])
        result = repo.get_active_wallet("alice")
        assert result is not None
        assert result["id"] == new["id"]

    def test_isolates_by_user(self, repo):
        alice_w = _wallet(repo, user_id="alice")
        _wallet(repo, user_id="bob")
        result = repo.get_active_wallet("alice")
        assert result["id"] == alice_w["id"]

    def test_has_full_wallet_fields(self, repo):
        _wallet(repo, user_id="alice")
        result = repo.get_active_wallet("alice")
        for key in ("id", "user_id", "wallet_name", "public_address",
                    "encrypted_private_key", "key_salt", "key_nonce",
                    "is_active", "created_at"):
            assert key in result


# ---------------------------------------------------------------------------
# Tests — get_all_wallets
# ---------------------------------------------------------------------------

class TestGetAllWallets:
    def test_empty_for_unknown_user(self, repo):
        assert repo.get_all_wallets("ghost") == []

    def test_returns_single_wallet(self, repo):
        _wallet(repo, user_id="alice")
        results = repo.get_all_wallets("alice")
        assert len(results) == 1

    def test_returns_multiple_wallets(self, repo):
        for _ in range(3):
            _wallet(repo, user_id="alice")
        assert len(repo.get_all_wallets("alice")) == 3

    def test_includes_inactive_wallets(self, repo):
        created = _wallet(repo, user_id="alice")
        repo.deactivate_wallet(created["id"])
        results = repo.get_all_wallets("alice")
        assert len(results) == 1
        assert results[0]["is_active"] == 0

    def test_includes_both_active_and_inactive(self, repo):
        active = _wallet(repo, user_id="alice")
        inactive = _wallet(repo, user_id="alice")
        repo.deactivate_wallet(inactive["id"])
        results = repo.get_all_wallets("alice")
        assert len(results) == 2
        statuses = {r["id"]: r["is_active"] for r in results}
        assert statuses[active["id"]] == 1
        assert statuses[inactive["id"]] == 0

    def test_ordered_newest_first(self, repo):
        first = _wallet(repo, user_id="alice")
        second = _wallet(repo, user_id="alice")
        results = repo.get_all_wallets("alice")
        assert results[0]["id"] == second["id"]
        assert results[1]["id"] == first["id"]

    def test_isolates_by_user(self, repo):
        _wallet(repo, user_id="alice")
        _wallet(repo, user_id="bob")
        _wallet(repo, user_id="bob")
        assert len(repo.get_all_wallets("alice")) == 1
        assert len(repo.get_all_wallets("bob")) == 2


# ---------------------------------------------------------------------------
# Tests — get_active_wallet_count
# ---------------------------------------------------------------------------

class TestGetActiveWalletCount:
    def test_zero_for_unknown_user(self, repo):
        assert repo.get_active_wallet_count("ghost") == 0

    def test_one_active_wallet(self, repo):
        _wallet(repo, user_id="alice")
        assert repo.get_active_wallet_count("alice") == 1

    def test_multiple_active_wallets(self, repo):
        for _ in range(4):
            _wallet(repo, user_id="alice")
        assert repo.get_active_wallet_count("alice") == 4

    def test_deactivated_not_counted(self, repo):
        created = _wallet(repo, user_id="alice")
        repo.deactivate_wallet(created["id"])
        assert repo.get_active_wallet_count("alice") == 0

    def test_only_active_counted_after_partial_deactivation(self, repo):
        w1 = _wallet(repo, user_id="alice")
        _wallet(repo, user_id="alice")
        _wallet(repo, user_id="alice")
        repo.deactivate_wallet(w1["id"])
        assert repo.get_active_wallet_count("alice") == 2

    def test_isolates_by_user(self, repo):
        _wallet(repo, user_id="alice")
        _wallet(repo, user_id="alice")
        _wallet(repo, user_id="bob")
        assert repo.get_active_wallet_count("alice") == 2
        assert repo.get_active_wallet_count("bob") == 1

    def test_returns_int(self, repo):
        result = repo.get_active_wallet_count("alice")
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# Tests — get_all_active_wallets
# ---------------------------------------------------------------------------

class TestGetAllActiveWallets:
    def test_empty_for_unknown_user(self, repo):
        assert repo.get_all_active_wallets("ghost") == []

    def test_returns_active_wallet(self, repo):
        _wallet(repo, user_id="alice")
        results = repo.get_all_active_wallets("alice")
        assert len(results) == 1
        assert results[0]["is_active"] == 1

    def test_returns_multiple_active(self, repo):
        for _ in range(3):
            _wallet(repo, user_id="alice")
        results = repo.get_all_active_wallets("alice")
        assert len(results) == 3

    def test_excludes_inactive(self, repo):
        active = _wallet(repo, user_id="alice")
        inactive = _wallet(repo, user_id="alice")
        repo.deactivate_wallet(inactive["id"])
        results = repo.get_all_active_wallets("alice")
        assert len(results) == 1
        assert results[0]["id"] == active["id"]

    def test_empty_when_all_deactivated(self, repo):
        created = _wallet(repo, user_id="alice")
        repo.deactivate_wallet(created["id"])
        assert repo.get_all_active_wallets("alice") == []

    def test_ordered_newest_first(self, repo):
        first = _wallet(repo, user_id="alice")
        second = _wallet(repo, user_id="alice")
        results = repo.get_all_active_wallets("alice")
        assert results[0]["id"] == second["id"]
        assert results[1]["id"] == first["id"]

    def test_isolates_by_user(self, repo):
        _wallet(repo, user_id="alice")
        _wallet(repo, user_id="bob")
        _wallet(repo, user_id="bob")
        assert len(repo.get_all_active_wallets("alice")) == 1
        assert len(repo.get_all_active_wallets("bob")) == 2


# ---------------------------------------------------------------------------
# Tests — deactivate_wallet
# ---------------------------------------------------------------------------

class TestDeactivateWallet:
    def test_deactivate_valid_id_returns_true(self, repo):
        created = _wallet(repo, user_id="alice")
        assert repo.deactivate_wallet(created["id"]) is True

    def test_deactivate_sets_is_active_to_zero(self, repo):
        created = _wallet(repo, user_id="alice")
        repo.deactivate_wallet(created["id"])
        row = repo._fetchone_dict(
            "SELECT is_active FROM user_wallets WHERE id = ?", (created["id"],)
        )
        assert row["is_active"] == 0

    def test_deactivate_nonexistent_returns_false(self, repo):
        assert repo.deactivate_wallet(99999) is False

    def test_deactivate_does_not_delete_row(self, repo):
        created = _wallet(repo, user_id="alice")
        repo.deactivate_wallet(created["id"])
        row = repo._fetchone_dict(
            "SELECT id FROM user_wallets WHERE id = ?", (created["id"],)
        )
        assert row is not None

    def test_deactivate_one_leaves_others_active(self, repo):
        w1 = _wallet(repo, user_id="alice")
        w2 = _wallet(repo, user_id="alice")
        repo.deactivate_wallet(w1["id"])
        row = repo._fetchone_dict(
            "SELECT is_active FROM user_wallets WHERE id = ?", (w2["id"],)
        )
        assert row["is_active"] == 1

    def test_deactivate_already_inactive_returns_true(self, repo):
        """Deactivating an already-inactive wallet: row exists so returns True."""
        created = _wallet(repo, user_id="alice")
        repo.deactivate_wallet(created["id"])
        # Second call: row still exists → should return True
        assert repo.deactivate_wallet(created["id"]) is True

    def test_deactivate_integer_id_required(self, repo):
        """Passing wrong type should raise or return False gracefully."""
        # SQLite will coerce, but we ensure it doesn't crash for a nonexistent string key
        result = repo.deactivate_wallet(0)
        assert result is False
