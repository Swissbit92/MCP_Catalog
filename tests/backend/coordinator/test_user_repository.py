"""Unit tests for UserRepository and module-level wrapper functions.

Tests cover:
- Table auto-creation via _ensure_tables (idempotent)
- upsert_user: insert new, update existing
- get_user_by_sub: found / not found
- get_onboarding_status: true / false / missing user
- set_onboarding_completed: via upsert + update branch
- Module-level wrapper functions (backward-compat delegates)
"""
from __future__ import annotations

import pytest

from src.coordinator.repositories.user_repository import (
    UserRepository,
    upsert_user,
    get_user_by_sub,
    get_onboarding_status,
    set_onboarding_completed,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_path(tmp_path) -> str:
    """Return a fresh temp SQLite path; UserRepository auto-creates schema."""
    return str(tmp_path / "test_users.db")


@pytest.fixture()
def repo(db_path) -> UserRepository:
    """Fully-initialised UserRepository backed by a fresh temp DB."""
    r = UserRepository(db_path)
    r._ensure_tables()
    return r


# ---------------------------------------------------------------------------
# TestUserRepository — class-level tests
# ---------------------------------------------------------------------------

class TestUserRepositoryEnsureTables:
    """_ensure_tables must be idempotent (safe to call multiple times)."""

    def test_ensure_tables_idempotent(self, db_path):
        r = UserRepository(db_path)
        r._ensure_tables()
        r._ensure_tables()  # second call must not raise
        # Verify table exists by querying it
        row = r.get_user_by_sub("probe")
        assert row is None

    def test_ensure_tables_backfills_onboarding_column(self, tmp_path):
        """Simulates a legacy DB without onboarding_completed: ALTER TABLE must succeed."""
        import sqlite3
        legacy_db = str(tmp_path / "legacy.db")
        # Create table WITHOUT onboarding_completed
        conn = sqlite3.connect(legacy_db)
        conn.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                google_sub TEXT UNIQUE NOT NULL,
                email TEXT,
                display_name TEXT,
                avatar_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

        # _ensure_tables must add the column without raising
        r = UserRepository(legacy_db)
        r._ensure_tables()
        r2 = UserRepository(legacy_db)
        r2._ensure_tables()  # idempotent on the now-migrated DB

        # Column should be accessible
        status = r.get_onboarding_status("nobody")
        assert status is False


class TestUpsertUser:
    """upsert_user: insert and update paths."""

    def test_insert_new_user_returns_dict(self, repo):
        result = repo.upsert_user("sub_001", email="a@example.com", display_name="Alice")
        assert isinstance(result, dict)
        assert result["google_sub"] == "sub_001"
        assert result["email"] == "a@example.com"
        assert result["display_name"] == "Alice"

    def test_insert_sets_id_and_timestamps(self, repo):
        result = repo.upsert_user("sub_002")
        assert result.get("id") is not None
        assert result.get("created_at") is not None

    def test_insert_with_all_fields(self, repo):
        result = repo.upsert_user(
            "sub_full",
            email="full@x.com",
            display_name="Full User",
            avatar_url="https://example.com/avatar.png",
        )
        assert result["avatar_url"] == "https://example.com/avatar.png"

    def test_insert_with_none_optional_fields(self, repo):
        result = repo.upsert_user("sub_minimal")
        assert result["email"] is None
        assert result["display_name"] is None
        assert result["avatar_url"] is None

    def test_update_existing_user(self, repo):
        repo.upsert_user("sub_upd", email="old@x.com", display_name="Old")
        result = repo.upsert_user("sub_upd", email="new@x.com", display_name="New")
        assert result["email"] == "new@x.com"
        assert result["display_name"] == "New"
        # created_at should be preserved (only one row)
        assert result["google_sub"] == "sub_upd"

    def test_update_refreshes_last_login(self, repo):
        first = repo.upsert_user("sub_login", email="a@a.com")
        second = repo.upsert_user("sub_login", email="a@a.com")
        # last_login should exist on both (not None); may or may not differ in same second
        assert second.get("last_login") is not None

    def test_upsert_returns_empty_dict_when_impossible(self, tmp_path):
        """Regression guard: get_user_by_sub after successful upsert must not return None."""
        r = UserRepository(str(tmp_path / "edge.db"))
        r._ensure_tables()
        result = r.upsert_user("sub_edge")
        # Returned dict must have the sub
        assert result.get("google_sub") == "sub_edge"

    def test_multiple_users_independent(self, repo):
        repo.upsert_user("alpha", email="alpha@x.com")
        repo.upsert_user("beta", email="beta@x.com")
        a = repo.get_user_by_sub("alpha")
        b = repo.get_user_by_sub("beta")
        assert a["email"] == "alpha@x.com"
        assert b["email"] == "beta@x.com"


class TestGetUserBySub:
    """get_user_by_sub: found / not-found paths."""

    def test_returns_none_for_unknown_sub(self, repo):
        result = repo.get_user_by_sub("does_not_exist")
        assert result is None

    def test_returns_dict_for_known_sub(self, repo):
        repo.upsert_user("sub_known", email="known@x.com")
        result = repo.get_user_by_sub("sub_known")
        assert result is not None
        assert result["google_sub"] == "sub_known"
        assert result["email"] == "known@x.com"

    def test_all_expected_columns_present(self, repo):
        repo.upsert_user("sub_cols", email="c@x.com", display_name="C", avatar_url="u")
        row = repo.get_user_by_sub("sub_cols")
        for col in ("id", "google_sub", "email", "display_name", "avatar_url",
                    "onboarding_completed", "created_at", "last_login"):
            assert col in row, f"Missing column: {col}"


class TestGetOnboardingStatus:
    """get_onboarding_status returns bool."""

    def test_default_is_false(self, repo):
        repo.upsert_user("sub_ob", email="ob@x.com")
        assert repo.get_onboarding_status("sub_ob") is False

    def test_returns_false_for_nonexistent_user(self, repo):
        assert repo.get_onboarding_status("nobody") is False

    def test_returns_true_after_completion(self, repo):
        repo.upsert_user("sub_complete")
        repo.set_onboarding_completed("sub_complete")
        assert repo.get_onboarding_status("sub_complete") is True


class TestSetOnboardingCompleted:
    """set_onboarding_completed: upsert (new user) + update (existing user) branches."""

    def test_sets_flag_for_existing_user(self, repo):
        repo.upsert_user("sub_exist")
        assert repo.get_onboarding_status("sub_exist") is False
        repo.set_onboarding_completed("sub_exist")
        assert repo.get_onboarding_status("sub_exist") is True

    def test_creates_user_row_if_not_exists(self, repo):
        """set_onboarding_completed uses INSERT ON CONFLICT, so it upserts."""
        repo.set_onboarding_completed("sub_brand_new")
        assert repo.get_onboarding_status("sub_brand_new") is True

    def test_idempotent_when_already_completed(self, repo):
        repo.upsert_user("sub_idem")
        repo.set_onboarding_completed("sub_idem")
        repo.set_onboarding_completed("sub_idem")  # must not raise
        assert repo.get_onboarding_status("sub_idem") is True


# ---------------------------------------------------------------------------
# TestModuleLevelWrappers — backward-compat module-level functions
# ---------------------------------------------------------------------------

@pytest.fixture()
def initialized_db_path(tmp_path) -> str:
    """A db_path where the users table has already been created.

    Module-level wrapper functions create a fresh UserRepository internally
    but do NOT call _ensure_tables(), so we must provision the schema first.
    """
    path = str(tmp_path / "wrap_users.db")
    r = UserRepository(path)
    r._ensure_tables()
    return path


class TestModuleLevelWrappers:
    """Module-level functions delegate to UserRepository correctly."""

    def test_upsert_user_module(self, initialized_db_path):
        result = upsert_user(initialized_db_path, "wrap_sub", email="wrap@x.com")
        assert result["google_sub"] == "wrap_sub"
        assert result["email"] == "wrap@x.com"

    def test_get_user_by_sub_found(self, initialized_db_path):
        upsert_user(initialized_db_path, "gsub_01", email="g@x.com")
        row = get_user_by_sub(initialized_db_path, "gsub_01")
        assert row is not None
        assert row["email"] == "g@x.com"

    def test_get_user_by_sub_not_found(self, initialized_db_path):
        result = get_user_by_sub(initialized_db_path, "ghost")
        assert result is None

    def test_get_onboarding_status_module(self, initialized_db_path):
        upsert_user(initialized_db_path, "ob_wrap")
        assert get_onboarding_status(initialized_db_path, "ob_wrap") is False

    def test_set_onboarding_completed_module(self, initialized_db_path):
        upsert_user(initialized_db_path, "ob_done")
        set_onboarding_completed(initialized_db_path, "ob_done")
        assert get_onboarding_status(initialized_db_path, "ob_done") is True

    def test_each_wrapper_call_creates_fresh_repo(self, initialized_db_path):
        """Each module wrapper creates a new UserRepository; state persists via DB."""
        upsert_user(initialized_db_path, "persist_sub", display_name="Persist")
        row = get_user_by_sub(initialized_db_path, "persist_sub")
        assert row["display_name"] == "Persist"
