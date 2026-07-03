# tests/backend/coordinator/test_wallet_summary_repository.py
"""Comprehensive unit tests for WalletSummaryRepository.

Uses a temporary SQLite file per test (via tmp_path).  No network, no Ollama.
"""
from __future__ import annotations

import pytest

from src.coordinator.repositories.wallet_summary_repository import WalletSummaryRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo(tmp_path):
    """Fresh WalletSummaryRepository backed by a temp SQLite file."""
    db_path = str(tmp_path / "test_summary.db")
    return WalletSummaryRepository(db_path)


# ===========================================================================
# TestGetSummary
# ===========================================================================


class TestGetSummary:
    def test_returns_none_for_unknown_user(self, repo):
        result = repo.get_summary("no_such_user")
        assert result is None

    def test_returns_dict_after_insert(self, repo):
        repo.upsert_summary("user1", active_wallet_count=2)
        result = repo.get_summary("user1")
        assert result is not None
        assert result["user_id"] == "user1"

    def test_schema_fields_present(self, repo):
        repo.upsert_summary("user_schema")
        row = repo.get_summary("user_schema")
        expected_keys = {
            "user_id",
            "active_wallet_count",
            "total_wallets_ever",
            "total_trades",
            "total_volume_usdc",
            "last_trade_timestamp",
            "last_trade_pair",
            "last_trade_action",
            "active_strategies",
            "updated_at",
        }
        assert expected_keys.issubset(row.keys())


# ===========================================================================
# TestUpsertSummary — insert path
# ===========================================================================


class TestUpsertSummaryInsert:
    def test_insert_creates_row(self, repo):
        repo.upsert_summary("new_user")
        assert repo.get_summary("new_user") is not None

    def test_insert_default_integers_zero(self, repo):
        repo.upsert_summary("defaults_user")
        row = repo.get_summary("defaults_user")
        assert row["active_wallet_count"] == 0
        assert row["total_wallets_ever"] == 0
        assert row["total_trades"] == 0
        assert row["active_strategies"] == 0

    def test_insert_default_volume_zero(self, repo):
        repo.upsert_summary("vol_user")
        row = repo.get_summary("vol_user")
        assert row["total_volume_usdc"] == 0.0

    def test_insert_default_nullable_trade_fields_none(self, repo):
        repo.upsert_summary("null_user")
        row = repo.get_summary("null_user")
        assert row["last_trade_timestamp"] is None
        assert row["last_trade_pair"] is None
        assert row["last_trade_action"] is None

    def test_insert_all_fields(self, repo):
        repo.upsert_summary(
            "full_user",
            active_wallet_count=3,
            total_wallets_ever=5,
            total_trades=10,
            total_volume_usdc=9999.99,
            last_trade_timestamp="2024-01-01T00:00:00Z",
            last_trade_pair="SOL/USDC",
            last_trade_action="buy",
            active_strategies=2,
        )
        row = repo.get_summary("full_user")
        assert row["active_wallet_count"] == 3
        assert row["total_wallets_ever"] == 5
        assert row["total_trades"] == 10
        assert abs(row["total_volume_usdc"] - 9999.99) < 0.001
        assert row["last_trade_timestamp"] == "2024-01-01T00:00:00Z"
        assert row["last_trade_pair"] == "SOL/USDC"
        assert row["last_trade_action"] == "buy"
        assert row["active_strategies"] == 2

    def test_insert_is_idempotent_on_second_call(self, repo):
        """Second call for same user should update (not raise IntegrityError)."""
        repo.upsert_summary("idempotent_user", active_wallet_count=1)
        repo.upsert_summary("idempotent_user", active_wallet_count=2)
        row = repo.get_summary("idempotent_user")
        assert row["active_wallet_count"] == 2

    def test_updated_at_is_set(self, repo):
        repo.upsert_summary("ts_user")
        row = repo.get_summary("ts_user")
        assert row["updated_at"] is not None
        assert len(row["updated_at"]) > 0


# ===========================================================================
# TestUpsertSummary — update path
# ===========================================================================


class TestUpsertSummaryUpdate:
    def test_update_single_field(self, repo):
        repo.upsert_summary("upd_user", active_wallet_count=1, total_trades=5)
        repo.upsert_summary("upd_user", active_wallet_count=3)
        row = repo.get_summary("upd_user")
        assert row["active_wallet_count"] == 3
        # Other field should be unchanged
        assert row["total_trades"] == 5

    def test_update_total_wallets_ever(self, repo):
        repo.upsert_summary("tw_user")
        repo.upsert_summary("tw_user", total_wallets_ever=7)
        row = repo.get_summary("tw_user")
        assert row["total_wallets_ever"] == 7

    def test_update_total_trades(self, repo):
        repo.upsert_summary("tt_user", total_trades=2)
        repo.upsert_summary("tt_user", total_trades=10)
        row = repo.get_summary("tt_user")
        assert row["total_trades"] == 10

    def test_update_volume(self, repo):
        repo.upsert_summary("vol_upd_user", total_volume_usdc=100.0)
        repo.upsert_summary("vol_upd_user", total_volume_usdc=250.5)
        row = repo.get_summary("vol_upd_user")
        assert abs(row["total_volume_usdc"] - 250.5) < 0.001

    def test_update_last_trade_fields(self, repo):
        repo.upsert_summary("trade_upd_user")
        repo.upsert_summary(
            "trade_upd_user",
            last_trade_timestamp="2024-06-01T12:00:00Z",
            last_trade_pair="ETH/USDC",
            last_trade_action="sell",
        )
        row = repo.get_summary("trade_upd_user")
        assert row["last_trade_timestamp"] == "2024-06-01T12:00:00Z"
        assert row["last_trade_pair"] == "ETH/USDC"
        assert row["last_trade_action"] == "sell"

    def test_update_active_strategies(self, repo):
        repo.upsert_summary("strat_user")
        repo.upsert_summary("strat_user", active_strategies=4)
        row = repo.get_summary("strat_user")
        assert row["active_strategies"] == 4

    def test_update_with_no_fields_is_noop(self, repo):
        """Calling upsert with no optional fields on an existing user should not crash."""
        repo.upsert_summary("noop_user", active_wallet_count=1)
        repo.upsert_summary("noop_user")  # no updates
        row = repo.get_summary("noop_user")
        # Row should still exist with original value
        assert row["active_wallet_count"] == 1

    def test_multiple_users_are_independent(self, repo):
        repo.upsert_summary("alpha", active_wallet_count=1)
        repo.upsert_summary("beta", active_wallet_count=5)
        assert repo.get_summary("alpha")["active_wallet_count"] == 1
        assert repo.get_summary("beta")["active_wallet_count"] == 5


# ===========================================================================
# TestIncrementTrade
# ===========================================================================


class TestIncrementTrade:
    def test_increment_creates_row_when_none_exists(self, repo):
        repo.increment_trade("new_trader", 500.0, "SOL/USDC", "buy", "2024-01-01T00:00:00Z")
        row = repo.get_summary("new_trader")
        assert row is not None
        assert row["total_trades"] == 1
        assert abs(row["total_volume_usdc"] - 500.0) < 0.001

    def test_increment_on_new_user_sets_last_trade_fields(self, repo):
        repo.increment_trade("trader2", 200.0, "ETH/USDC", "sell", "2024-02-01T00:00:00Z")
        row = repo.get_summary("trader2")
        assert row["last_trade_pair"] == "ETH/USDC"
        assert row["last_trade_action"] == "sell"
        assert row["last_trade_timestamp"] == "2024-02-01T00:00:00Z"

    def test_increment_accumulates_trades(self, repo):
        repo.upsert_summary("accum_user", total_trades=3, total_volume_usdc=1000.0)
        repo.increment_trade("accum_user", 250.0, "BTC/USDC", "buy", "2024-03-01T00:00:00Z")
        row = repo.get_summary("accum_user")
        assert row["total_trades"] == 4
        assert abs(row["total_volume_usdc"] - 1250.0) < 0.001

    def test_increment_updates_last_trade_info(self, repo):
        repo.upsert_summary(
            "info_user",
            total_trades=1,
            last_trade_pair="SOL/USDC",
            last_trade_action="buy",
            last_trade_timestamp="2024-01-01T00:00:00Z",
        )
        repo.increment_trade("info_user", 99.0, "ETH/USDC", "sell", "2024-06-01T00:00:00Z")
        row = repo.get_summary("info_user")
        assert row["last_trade_pair"] == "ETH/USDC"
        assert row["last_trade_action"] == "sell"
        assert row["last_trade_timestamp"] == "2024-06-01T00:00:00Z"

    def test_increment_multiple_times(self, repo):
        repo.upsert_summary("multi_inc")
        for i in range(5):
            repo.increment_trade("multi_inc", 100.0, "SOL/USDC", "buy", f"2024-0{i+1}-01T00:00:00Z")
        row = repo.get_summary("multi_inc")
        assert row["total_trades"] == 5
        assert abs(row["total_volume_usdc"] - 500.0) < 0.001


# ===========================================================================
# TestGetBalanceCache
# ===========================================================================


class TestGetBalanceCache:
    def test_returns_none_for_unknown_wallet(self, repo):
        assert repo.get_balance_cache("ghost_wallet") is None

    def test_returns_row_after_upsert(self, repo):
        repo.upsert_balance("w1", "user_a", sol_balance=5.0)
        row = repo.get_balance_cache("w1")
        assert row is not None
        assert row["wallet_id"] == "w1"
        assert row["user_id"] == "user_a"

    def test_schema_fields_present(self, repo):
        repo.upsert_balance("w_schema", "user_b")
        row = repo.get_balance_cache("w_schema")
        expected_keys = {"wallet_id", "user_id", "sol_balance", "token_count", "is_unlocked", "last_checked"}
        assert expected_keys.issubset(row.keys())


# ===========================================================================
# TestGetUserBalances
# ===========================================================================


class TestGetUserBalances:
    def test_returns_empty_list_for_unknown_user(self, repo):
        result = repo.get_user_balances("ghost_user")
        assert result == []

    def test_returns_all_wallets_for_user(self, repo):
        repo.upsert_balance("w_a", "user_x", sol_balance=1.0)
        repo.upsert_balance("w_b", "user_x", sol_balance=2.0)
        results = repo.get_user_balances("user_x")
        assert len(results) == 2
        ids = {r["wallet_id"] for r in results}
        assert ids == {"w_a", "w_b"}

    def test_does_not_return_other_users_wallets(self, repo):
        repo.upsert_balance("w_mine", "user_me", sol_balance=3.0)
        repo.upsert_balance("w_theirs", "user_them", sol_balance=99.0)
        results = repo.get_user_balances("user_me")
        assert len(results) == 1
        assert results[0]["wallet_id"] == "w_mine"


# ===========================================================================
# TestUpsertBalance — insert path
# ===========================================================================


class TestUpsertBalanceInsert:
    def test_insert_creates_row(self, repo):
        repo.upsert_balance("new_w", "uid1")
        assert repo.get_balance_cache("new_w") is not None

    def test_insert_defaults(self, repo):
        repo.upsert_balance("def_w", "uid2")
        row = repo.get_balance_cache("def_w")
        assert row["token_count"] == 0
        assert row["is_unlocked"] == 0

    def test_insert_with_sol_balance(self, repo):
        repo.upsert_balance("sol_w", "uid3", sol_balance=12.345)
        row = repo.get_balance_cache("sol_w")
        assert abs(row["sol_balance"] - 12.345) < 0.0001

    def test_insert_with_token_count(self, repo):
        repo.upsert_balance("tok_w", "uid4", token_count=7)
        row = repo.get_balance_cache("tok_w")
        assert row["token_count"] == 7

    def test_insert_with_is_unlocked(self, repo):
        repo.upsert_balance("unlock_w", "uid5", is_unlocked=1)
        row = repo.get_balance_cache("unlock_w")
        assert row["is_unlocked"] == 1

    def test_insert_sets_last_checked(self, repo):
        repo.upsert_balance("lc_w", "uid6")
        row = repo.get_balance_cache("lc_w")
        assert row["last_checked"] is not None


# ===========================================================================
# TestUpsertBalance — update path
# ===========================================================================


class TestUpsertBalanceUpdate:
    def test_update_sol_balance(self, repo):
        repo.upsert_balance("upd_w", "u1", sol_balance=1.0)
        repo.upsert_balance("upd_w", "u1", sol_balance=99.9)
        row = repo.get_balance_cache("upd_w")
        assert abs(row["sol_balance"] - 99.9) < 0.001

    def test_update_token_count(self, repo):
        repo.upsert_balance("tok_upd_w", "u2", token_count=3)
        repo.upsert_balance("tok_upd_w", "u2", token_count=10)
        row = repo.get_balance_cache("tok_upd_w")
        assert row["token_count"] == 10

    def test_update_is_unlocked(self, repo):
        repo.upsert_balance("lock_upd_w", "u3", is_unlocked=0)
        repo.upsert_balance("lock_upd_w", "u3", is_unlocked=1)
        row = repo.get_balance_cache("lock_upd_w")
        assert row["is_unlocked"] == 1

    def test_update_with_no_fields_is_noop(self, repo):
        repo.upsert_balance("noop_w", "u4", sol_balance=5.0)
        repo.upsert_balance("noop_w", "u4")  # no fields to update
        row = repo.get_balance_cache("noop_w")
        assert abs(row["sol_balance"] - 5.0) < 0.001

    def test_update_does_not_change_user_id(self, repo):
        repo.upsert_balance("fixed_w", "original_user", sol_balance=1.0)
        repo.upsert_balance("fixed_w", "original_user", sol_balance=2.0)
        row = repo.get_balance_cache("fixed_w")
        assert row["user_id"] == "original_user"

    def test_partial_update_preserves_other_fields(self, repo):
        repo.upsert_balance("partial_w", "u5", sol_balance=3.0, token_count=5, is_unlocked=1)
        repo.upsert_balance("partial_w", "u5", sol_balance=7.0)
        row = repo.get_balance_cache("partial_w")
        assert abs(row["sol_balance"] - 7.0) < 0.001
        assert row["token_count"] == 5
        assert row["is_unlocked"] == 1


# ===========================================================================
# TestSetUnlockState
# ===========================================================================


class TestSetUnlockState:
    def test_set_unlocked_true(self, repo):
        repo.upsert_balance("lock_w1", "u1", is_unlocked=0)
        repo.set_unlock_state("lock_w1", True)
        row = repo.get_balance_cache("lock_w1")
        assert row["is_unlocked"] == 1

    def test_set_unlocked_false(self, repo):
        repo.upsert_balance("lock_w2", "u2", is_unlocked=1)
        repo.set_unlock_state("lock_w2", False)
        row = repo.get_balance_cache("lock_w2")
        assert row["is_unlocked"] == 0

    def test_set_unlock_on_nonexistent_wallet_does_not_crash(self, repo):
        """UPDATE on a nonexistent wallet_id should be a no-op, not raise."""
        repo.set_unlock_state("ghost_wallet_xyz", True)  # should not raise

    def test_toggle_unlock_state(self, repo):
        repo.upsert_balance("toggle_w", "u3", is_unlocked=0)
        repo.set_unlock_state("toggle_w", True)
        assert repo.get_balance_cache("toggle_w")["is_unlocked"] == 1
        repo.set_unlock_state("toggle_w", False)
        assert repo.get_balance_cache("toggle_w")["is_unlocked"] == 0


# ===========================================================================
# TestResetAllUnlockStates
# ===========================================================================


class TestResetAllUnlockStates:
    def test_resets_single_wallet(self, repo):
        repo.upsert_balance("r_w1", "u1", is_unlocked=1)
        repo.reset_all_unlock_states()
        row = repo.get_balance_cache("r_w1")
        assert row["is_unlocked"] == 0

    def test_resets_multiple_wallets(self, repo):
        repo.upsert_balance("r_w2", "u2", is_unlocked=1)
        repo.upsert_balance("r_w3", "u3", is_unlocked=1)
        repo.upsert_balance("r_w4", "u4", is_unlocked=1)
        repo.reset_all_unlock_states()
        for wid in ("r_w2", "r_w3", "r_w4"):
            assert repo.get_balance_cache(wid)["is_unlocked"] == 0

    def test_reset_when_table_empty_does_not_crash(self, repo):
        """reset_all_unlock_states on an empty table should be a no-op."""
        repo.reset_all_unlock_states()  # should not raise

    def test_reset_leaves_already_locked_wallets_locked(self, repo):
        repo.upsert_balance("already_locked", "u5", is_unlocked=0)
        repo.reset_all_unlock_states()
        row = repo.get_balance_cache("already_locked")
        assert row["is_unlocked"] == 0

    def test_reset_does_not_affect_other_fields(self, repo):
        repo.upsert_balance("safe_w", "u6", sol_balance=42.0, token_count=3, is_unlocked=1)
        repo.reset_all_unlock_states()
        row = repo.get_balance_cache("safe_w")
        assert abs(row["sol_balance"] - 42.0) < 0.001
        assert row["token_count"] == 3
        assert row["is_unlocked"] == 0


# ===========================================================================
# TestIsolation — separate repos / db_paths don't bleed into each other
# ===========================================================================


class TestIsolation:
    def test_separate_db_paths_are_independent(self, tmp_path):
        db_a = str(tmp_path / "a.db")
        db_b = str(tmp_path / "b.db")
        repo_a = WalletSummaryRepository(db_a)
        repo_b = WalletSummaryRepository(db_b)
        repo_a.upsert_summary("shared_user_id", active_wallet_count=99)
        assert repo_b.get_summary("shared_user_id") is None
