# tests/backend/coordinator/test_wallet_registry_repository.py
"""Comprehensive unit tests for WalletRegistryRepository.

Uses a temporary SQLite file per test (via tmp_path).  No network, no Ollama.
"""
from __future__ import annotations

import pytest

from src.coordinator.repositories.wallet_registry_repository import (
    WalletRegistryRepository,
    MAX_ACTIVE_WALLETS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo(tmp_path):
    """Fresh WalletRegistryRepository backed by a temp SQLite file."""
    db_path = str(tmp_path / "test_registry.db")
    return WalletRegistryRepository(db_path)


def _register(repo, user_id="user1", name="My Wallet", address=None):
    """Helper: register a wallet with a unique address if not provided."""
    import uuid

    addr = address or f"PublicKey{uuid.uuid4().hex[:8]}"
    return repo.register_wallet(user_id, name, addr)


# ===========================================================================
# TestCanCreateWallet
# ===========================================================================


class TestCanCreateWallet:
    def test_fresh_user_can_create(self, repo):
        allowed, count, slot = repo.can_create_wallet("brand_new_user")
        assert allowed is True
        assert count == 0
        assert slot == 1

    def test_slot_advances_after_first_wallet(self, repo):
        _register(repo, "slot_user")
        allowed, count, slot = repo.can_create_wallet("slot_user")
        assert allowed is True
        assert count == 1
        assert slot == 2

    def test_slot_advances_after_two_wallets(self, repo):
        _register(repo, "slot2_user")
        _register(repo, "slot2_user")
        allowed, count, slot = repo.can_create_wallet("slot2_user")
        assert allowed is True
        assert count == 2
        assert slot == 3

    def test_blocked_at_max_wallets(self, repo):
        for _ in range(MAX_ACTIVE_WALLETS):
            _register(repo, "max_user")
        allowed, count, slot = repo.can_create_wallet("max_user")
        assert allowed is False
        assert count == MAX_ACTIVE_WALLETS
        assert slot == 0

    def test_slot_reused_after_soft_delete(self, repo):
        w1 = _register(repo, "reuse_user")
        _register(repo, "reuse_user")
        _register(repo, "reuse_user")
        # Delete slot 1 wallet
        repo.soft_delete_wallet(w1["wallet_id"])
        allowed, count, slot = repo.can_create_wallet("reuse_user")
        assert allowed is True
        assert count == 2
        assert slot == 1  # slot 1 is free again

    def test_max_active_wallets_constant(self):
        assert MAX_ACTIVE_WALLETS == 3


# ===========================================================================
# TestRegisterWallet
# ===========================================================================


class TestRegisterWallet:
    def test_returns_dict_with_expected_fields(self, repo):
        row = _register(repo, "reg_user")
        expected_keys = {
            "id",
            "user_id",
            "wallet_id",
            "wallet_name",
            "public_address",
            "status",
            "slot_number",
            "created_at",
            "deleted_at",
            "updated_at",
        }
        assert expected_keys.issubset(row.keys())

    def test_status_is_active(self, repo):
        row = _register(repo)
        assert row["status"] == "active"

    def test_slot_number_is_1_for_first_wallet(self, repo):
        row = _register(repo, "slot_test")
        assert row["slot_number"] == 1

    def test_slot_number_increments(self, repo):
        r1 = _register(repo, "inc_user")
        r2 = _register(repo, "inc_user")
        r3 = _register(repo, "inc_user")
        assert {r1["slot_number"], r2["slot_number"], r3["slot_number"]} == {1, 2, 3}

    def test_wallet_id_is_uuid_string(self, repo):
        import uuid

        row = _register(repo)
        # Should not raise if valid UUID
        parsed = uuid.UUID(row["wallet_id"])
        assert str(parsed) == row["wallet_id"]

    def test_name_and_address_stored(self, repo):
        row = repo.register_wallet("named_user", "Hot Wallet", "SolanaAddress123")
        assert row["wallet_name"] == "Hot Wallet"
        assert row["public_address"] == "SolanaAddress123"

    def test_raises_value_error_at_limit(self, repo):
        for _ in range(MAX_ACTIVE_WALLETS):
            _register(repo, "limit_user")
        with pytest.raises(ValueError, match="active wallets"):
            _register(repo, "limit_user")

    def test_error_message_includes_count(self, repo):
        for _ in range(MAX_ACTIVE_WALLETS):
            _register(repo, "err_user")
        with pytest.raises(ValueError) as exc_info:
            _register(repo, "err_user")
        assert str(MAX_ACTIVE_WALLETS) in str(exc_info.value)

    def test_deleted_at_is_null_on_creation(self, repo):
        row = _register(repo)
        assert row["deleted_at"] is None

    def test_created_at_and_updated_at_set(self, repo):
        row = _register(repo)
        assert row["created_at"] is not None
        assert row["updated_at"] is not None


# ===========================================================================
# TestGetActiveWallets
# ===========================================================================


class TestGetActiveWallets:
    def test_returns_empty_list_for_unknown_user(self, repo):
        assert repo.get_active_wallets("ghost") == []

    def test_returns_registered_wallets(self, repo):
        _register(repo, "aw_user")
        _register(repo, "aw_user")
        result = repo.get_active_wallets("aw_user")
        assert len(result) == 2

    def test_ordered_by_slot_number(self, repo):
        _register(repo, "ord_user")
        _register(repo, "ord_user")
        _register(repo, "ord_user")
        slots = [r["slot_number"] for r in repo.get_active_wallets("ord_user")]
        assert slots == sorted(slots)

    def test_excludes_deleted_wallets(self, repo):
        w = _register(repo, "del_user")
        _register(repo, "del_user")
        repo.soft_delete_wallet(w["wallet_id"])
        result = repo.get_active_wallets("del_user")
        assert len(result) == 1
        assert result[0]["wallet_id"] != w["wallet_id"]

    def test_does_not_include_other_users_wallets(self, repo):
        _register(repo, "user_a")
        _register(repo, "user_b")
        result = repo.get_active_wallets("user_a")
        assert len(result) == 1
        assert result[0]["user_id"] == "user_a"


# ===========================================================================
# TestGetWalletById
# ===========================================================================


class TestGetWalletById:
    def test_returns_none_for_unknown_id(self, repo):
        assert repo.get_wallet_by_id("00000000-0000-0000-0000-000000000000") is None

    def test_returns_row_for_valid_id(self, repo):
        row = _register(repo)
        fetched = repo.get_wallet_by_id(row["wallet_id"])
        assert fetched is not None
        assert fetched["wallet_id"] == row["wallet_id"]

    def test_returns_deleted_wallet_too(self, repo):
        """get_wallet_by_id is not filtered by status — it returns any status."""
        row = _register(repo)
        repo.soft_delete_wallet(row["wallet_id"])
        fetched = repo.get_wallet_by_id(row["wallet_id"])
        assert fetched is not None
        assert fetched["status"] == "deleted"


# ===========================================================================
# TestGetWalletByAddress
# ===========================================================================


class TestGetWalletByAddress:
    def test_returns_none_for_unknown_address(self, repo):
        assert repo.get_wallet_by_address("NonExistentAddr") is None

    def test_returns_active_wallet(self, repo):
        repo.register_wallet("addr_user", "My Wallet", "KnownAddress123")
        row = repo.get_wallet_by_address("KnownAddress123")
        assert row is not None
        assert row["public_address"] == "KnownAddress123"

    def test_returns_none_for_deleted_wallet(self, repo):
        """get_wallet_by_address should only return active wallets."""
        w = repo.register_wallet("del_addr_user", "W", "DeletedAddr456")
        repo.soft_delete_wallet(w["wallet_id"])
        assert repo.get_wallet_by_address("DeletedAddr456") is None


# ===========================================================================
# TestSoftDeleteWallet
# ===========================================================================


class TestSoftDeleteWallet:
    def test_returns_true_on_success(self, repo):
        w = _register(repo)
        assert repo.soft_delete_wallet(w["wallet_id"]) is True

    def test_returns_false_for_unknown_wallet(self, repo):
        assert repo.soft_delete_wallet("00000000-0000-0000-0000-000000000000") is False

    def test_status_becomes_deleted(self, repo):
        w = _register(repo)
        repo.soft_delete_wallet(w["wallet_id"])
        row = repo.get_wallet_by_id(w["wallet_id"])
        assert row["status"] == "deleted"

    def test_deleted_at_is_set(self, repo):
        w = _register(repo)
        repo.soft_delete_wallet(w["wallet_id"])
        row = repo.get_wallet_by_id(w["wallet_id"])
        assert row["deleted_at"] is not None

    def test_wallet_not_in_active_list_after_delete(self, repo):
        w = _register(repo, "rm_user")
        repo.soft_delete_wallet(w["wallet_id"])
        active = repo.get_active_wallets("rm_user")
        assert all(r["wallet_id"] != w["wallet_id"] for r in active)

    def test_double_delete_returns_false(self, repo):
        w = _register(repo)
        repo.soft_delete_wallet(w["wallet_id"])
        assert repo.soft_delete_wallet(w["wallet_id"]) is False

    def test_delete_frees_slot_for_new_wallet(self, repo):
        wallets = [_register(repo, "free_slot_user") for _ in range(MAX_ACTIVE_WALLETS)]
        repo.soft_delete_wallet(wallets[0]["wallet_id"])
        # Should now be able to create a new wallet
        new_w = _register(repo, "free_slot_user")
        assert new_w is not None
        assert new_w["status"] == "active"


# ===========================================================================
# TestSoftDeleteByAddress
# ===========================================================================


class TestSoftDeleteByAddress:
    def test_returns_true_on_success(self, repo):
        repo.register_wallet("addr_del_user", "W", "DelByAddr_1")
        result = repo.soft_delete_by_address("addr_del_user", "DelByAddr_1")
        assert result is True

    def test_returns_false_for_unknown_address(self, repo):
        result = repo.soft_delete_by_address("any_user", "DoesNotExist_XYZ")
        assert result is False

    def test_wallet_marked_deleted(self, repo):
        w = repo.register_wallet("addr_del2", "W", "DelByAddr_2")
        repo.soft_delete_by_address("addr_del2", "DelByAddr_2")
        row = repo.get_wallet_by_id(w["wallet_id"])
        assert row["status"] == "deleted"

    def test_does_not_delete_other_users_wallet(self, repo):
        repo.register_wallet("user_a", "W", "SharedAddr")
        repo.register_wallet("user_b", "W2", "OtherAddr")
        # user_b tries to delete user_a's address
        result = repo.soft_delete_by_address("user_b", "SharedAddr")
        assert result is False
        # user_a's wallet should still be active
        row = repo.get_wallet_by_address("SharedAddr")
        assert row is not None

    def test_returns_false_on_already_deleted(self, repo):
        repo.register_wallet("repeat_del", "W", "AlreadyDeleted")
        repo.soft_delete_by_address("repeat_del", "AlreadyDeleted")
        result = repo.soft_delete_by_address("repeat_del", "AlreadyDeleted")
        assert result is False


# ===========================================================================
# TestGetActiveCount
# ===========================================================================


class TestGetActiveCount:
    def test_zero_for_new_user(self, repo):
        assert repo.get_active_count("count_user_new") == 0

    def test_increments_with_registrations(self, repo):
        _register(repo, "cnt_user")
        assert repo.get_active_count("cnt_user") == 1
        _register(repo, "cnt_user")
        assert repo.get_active_count("cnt_user") == 2

    def test_decrements_after_soft_delete(self, repo):
        w = _register(repo, "cnt_del_user")
        _register(repo, "cnt_del_user")
        assert repo.get_active_count("cnt_del_user") == 2
        repo.soft_delete_wallet(w["wallet_id"])
        assert repo.get_active_count("cnt_del_user") == 1

    def test_max_is_three(self, repo):
        for _ in range(MAX_ACTIVE_WALLETS):
            _register(repo, "max_cnt_user")
        assert repo.get_active_count("max_cnt_user") == MAX_ACTIVE_WALLETS

    def test_does_not_count_other_users_wallets(self, repo):
        _register(repo, "only_user")
        _register(repo, "other_user")
        assert repo.get_active_count("only_user") == 1


# ===========================================================================
# TestGetAllWallets
# ===========================================================================


class TestGetAllWallets:
    def test_returns_empty_list_for_unknown_user(self, repo):
        assert repo.get_all_wallets("ghost_audit") == []

    def test_returns_active_wallets(self, repo):
        _register(repo, "all_user")
        rows = repo.get_all_wallets("all_user")
        assert len(rows) == 1

    def test_includes_deleted_wallets(self, repo):
        w = _register(repo, "all_del_user")
        _register(repo, "all_del_user")
        repo.soft_delete_wallet(w["wallet_id"])
        rows = repo.get_all_wallets("all_del_user")
        assert len(rows) == 2
        statuses = {r["status"] for r in rows}
        assert "deleted" in statuses
        assert "active" in statuses

    def test_does_not_include_other_users_wallets(self, repo):
        _register(repo, "audit_a")
        _register(repo, "audit_b")
        rows = repo.get_all_wallets("audit_a")
        assert len(rows) == 1
        assert rows[0]["user_id"] == "audit_a"

    def test_ordered_by_slot_then_created_at(self, repo):
        _register(repo, "order_all")
        _register(repo, "order_all")
        _register(repo, "order_all")
        rows = repo.get_all_wallets("order_all")
        slots = [r["slot_number"] for r in rows]
        assert slots == sorted(slots)

    def test_shows_full_history_after_delete_and_recreate(self, repo):
        w1 = _register(repo, "hist_user")
        repo.soft_delete_wallet(w1["wallet_id"])
        _register(repo, "hist_user")  # slot 1 reused
        all_rows = repo.get_all_wallets("hist_user")
        assert len(all_rows) == 2


# ===========================================================================
# TestIsolation
# ===========================================================================


class TestIsolation:
    def test_separate_db_paths_do_not_share_data(self, tmp_path):
        db_a = str(tmp_path / "a.db")
        db_b = str(tmp_path / "b.db")
        repo_a = WalletRegistryRepository(db_a)
        repo_b = WalletRegistryRepository(db_b)
        repo_a.register_wallet("shared_user", "W", "AddrOnlyInA")
        # repo_b should see nothing
        assert repo_b.get_active_wallets("shared_user") == []


# ===========================================================================
# TestGuardrailEnforcement — stress the 3-wallet hard cap
# ===========================================================================


class TestGuardrailEnforcement:
    def test_cannot_bypass_limit_via_multiple_calls(self, repo):
        for _ in range(MAX_ACTIVE_WALLETS):
            _register(repo, "bypass_user")
        with pytest.raises(ValueError):
            _register(repo, "bypass_user")
        # Still only 3 active
        assert repo.get_active_count("bypass_user") == MAX_ACTIVE_WALLETS

    def test_after_delete_create_succeed_and_count_stays_at_max(self, repo):
        wallets = [_register(repo, "cap_user") for _ in range(MAX_ACTIVE_WALLETS)]
        repo.soft_delete_wallet(wallets[0]["wallet_id"])
        _register(repo, "cap_user")
        assert repo.get_active_count("cap_user") == MAX_ACTIVE_WALLETS

    def test_different_users_caps_are_independent(self, repo):
        for _ in range(MAX_ACTIVE_WALLETS):
            _register(repo, "user_cap_x")
        # user_cap_y should still be able to create wallets
        for _ in range(MAX_ACTIVE_WALLETS):
            _register(repo, "user_cap_y")
        assert repo.get_active_count("user_cap_x") == MAX_ACTIVE_WALLETS
        assert repo.get_active_count("user_cap_y") == MAX_ACTIVE_WALLETS
