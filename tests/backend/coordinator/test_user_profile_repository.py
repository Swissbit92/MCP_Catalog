"""Unit tests for UserProfileRepository.

The repository DOES NOT call _ensure_tables() in __init__ — schema is
provisioned by Alembic in production.  Tests create the required tables
directly via sqlite3 before handing the db_path to the repository.

Schema summary (from alembic/versions/2dba9f1a6b1e_initial_schema.py):
  user_profiles(user_id PK, created_at, updated_at, profile_data)
  user_sessions(user_id FK→user_profiles, session_id FK→chat_sessions, created_at, PK(user_id,session_id))
  chat_sessions(id PK, ...)   — needed only for user_sessions FK

NOTE: user_sessions has a FK to chat_sessions.id, so to successfully call
link_session_to_user() the session_id must already exist in chat_sessions.
Tests that exercise link_session_to_user insert a stub chat_sessions row first.
"""
from __future__ import annotations

import sqlite3
import pytest

from src.coordinator.repositories.user_profile_repository import UserProfileRepository
from src.coordinator.user_profile import UserProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _provision_schema(db_path: str) -> None:
    """Create the tables that UserProfileRepository requires."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            persona_key TEXT NOT NULL DEFAULT 'test',
            title TEXT NOT NULL DEFAULT 'test',
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            profile_data TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_sessions (
            user_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (user_id, session_id),
            FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id);
    """)
    conn.commit()
    conn.close()


def _insert_chat_session(db_path: str, session_id: str) -> None:
    """Insert a stub row into chat_sessions so user_sessions FK constraint is satisfied."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        "INSERT OR IGNORE INTO chat_sessions(id, persona_key, title, created_at, updated_at) "
        "VALUES (?, 'test', 'test', '', '')",
        (session_id,),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_path(tmp_path) -> str:
    path = str(tmp_path / "test_profiles.db")
    _provision_schema(path)
    return path


@pytest.fixture()
def repo(db_path) -> UserProfileRepository:
    return UserProfileRepository(db_path)


# ---------------------------------------------------------------------------
# TestCreateProfile
# ---------------------------------------------------------------------------

class TestCreateProfile:
    """create_profile: happy-path + duplicate handling."""

    def test_returns_user_profile_instance(self, repo):
        profile = repo.create_profile("user_001")
        assert isinstance(profile, UserProfile)

    def test_profile_has_correct_user_id(self, repo):
        profile = repo.create_profile("user_001")
        assert profile.user_id == "user_001"

    def test_profile_data_has_default_fields(self, repo):
        profile = repo.create_profile("user_002")
        assert profile.data["name"] is None
        assert profile.data["total_sessions"] == 0
        assert isinstance(profile.data["facts"], list)
        assert isinstance(profile.data["background"], list)

    def test_create_persists_to_db(self, repo):
        repo.create_profile("user_persist")
        fetched = repo.get_profile("user_persist")
        assert fetched is not None
        assert fetched.user_id == "user_persist"

    def test_duplicate_create_returns_existing_profile(self, repo):
        first = repo.create_profile("user_dup")
        # Mutate first profile so we can detect which one is returned
        first.data["name"] = "Already There"
        repo.update_profile(first)

        second = repo.create_profile("user_dup")  # duplicate — must not raise
        assert isinstance(second, UserProfile)
        assert second.user_id == "user_dup"
        # Should be the persisted (existing) version
        assert second.data["name"] == "Already There"

    def test_multiple_distinct_users(self, repo):
        repo.create_profile("alice")
        repo.create_profile("bob")
        assert repo.get_profile("alice") is not None
        assert repo.get_profile("bob") is not None


# ---------------------------------------------------------------------------
# TestGetProfile
# ---------------------------------------------------------------------------

class TestGetProfile:
    """get_profile: found / not-found."""

    def test_returns_none_for_unknown_user(self, repo):
        result = repo.get_profile("ghost")
        assert result is None

    def test_returns_profile_for_known_user(self, repo):
        repo.create_profile("known_user")
        result = repo.get_profile("known_user")
        assert result is not None
        assert result.user_id == "known_user"

    def test_profile_data_round_trips(self, repo):
        profile = repo.create_profile("roundtrip")
        profile.data["name"] = "RoundTrip"
        profile.data["facts"].append("loves tests")
        repo.update_profile(profile)

        fetched = repo.get_profile("roundtrip")
        assert fetched.data["name"] == "RoundTrip"
        assert "loves tests" in fetched.data["facts"]


# ---------------------------------------------------------------------------
# TestUpdateProfile
# ---------------------------------------------------------------------------

class TestUpdateProfile:
    """update_profile: rowcount > 0 and no-op paths."""

    def test_update_persists_name_change(self, repo):
        profile = repo.create_profile("update_me")
        profile.data["name"] = "Updated Name"
        repo.update_profile(profile)

        fetched = repo.get_profile("update_me")
        assert fetched.data["name"] == "Updated Name"

    def test_update_persists_facts(self, repo):
        profile = repo.create_profile("update_facts")
        profile.data["facts"].append("fact_one")
        profile.data["facts"].append("fact_two")
        repo.update_profile(profile)

        fetched = repo.get_profile("update_facts")
        assert "fact_one" in fetched.data["facts"]
        assert "fact_two" in fetched.data["facts"]

    def test_update_nonexistent_profile_does_not_raise(self, repo):
        """Updating a non-existent profile logs a warning but must not raise."""
        orphan = UserProfile("orphan_user")
        orphan.data["name"] = "Ghost"
        repo.update_profile(orphan)  # should not raise

    def test_update_session_stats(self, repo):
        profile = repo.create_profile("stats_user")
        profile.update_from_session({
            "user_name": "Stats",
            "background": [],
            "topics": ["pytest"],
            "facts": [],
            "preferences": {},
            "persona_key": "aurora",
            "message_count": 5,
        })
        repo.update_profile(profile)

        fetched = repo.get_profile("stats_user")
        assert fetched.data["total_sessions"] == 1
        assert fetched.data["total_messages"] == 5


# ---------------------------------------------------------------------------
# TestDeleteProfile
# ---------------------------------------------------------------------------

class TestDeleteProfile:
    """delete_profile: returns True/False, removes from DB."""

    def test_delete_existing_profile_returns_true(self, repo):
        repo.create_profile("del_me")
        result = repo.delete_profile("del_me")
        assert result is True

    def test_deleted_profile_is_gone(self, repo):
        repo.create_profile("del_gone")
        repo.delete_profile("del_gone")
        assert repo.get_profile("del_gone") is None

    def test_delete_nonexistent_returns_false(self, repo):
        result = repo.delete_profile("nobody")
        assert result is False

    def test_delete_idempotent(self, repo):
        repo.create_profile("del_twice")
        repo.delete_profile("del_twice")
        second = repo.delete_profile("del_twice")
        assert second is False


# ---------------------------------------------------------------------------
# TestGetOrCreateProfile
# ---------------------------------------------------------------------------

class TestGetOrCreateProfile:
    """get_or_create_profile: returns existing or creates new."""

    def test_creates_new_when_absent(self, repo):
        profile = repo.get_or_create_profile("new_via_goc")
        assert isinstance(profile, UserProfile)
        assert profile.user_id == "new_via_goc"

    def test_returns_existing_when_present(self, repo):
        created = repo.create_profile("existing_goc")
        created.data["name"] = "Already Exists"
        repo.update_profile(created)

        fetched = repo.get_or_create_profile("existing_goc")
        assert fetched.data["name"] == "Already Exists"

    def test_subsequent_calls_are_idempotent(self, repo):
        repo.get_or_create_profile("idem_goc")
        repo.get_or_create_profile("idem_goc")  # must not raise or duplicate
        profiles = repo.list_all_profiles()
        user_ids = [p["user_id"] for p in profiles]
        assert user_ids.count("idem_goc") == 1


# ---------------------------------------------------------------------------
# TestListAllProfiles
# ---------------------------------------------------------------------------

class TestListAllProfiles:
    """list_all_profiles: returns summary dicts."""

    def test_empty_db_returns_empty_list(self, repo):
        result = repo.list_all_profiles()
        assert result == []

    def test_returns_one_per_profile(self, repo):
        repo.create_profile("list_a")
        repo.create_profile("list_b")
        result = repo.list_all_profiles()
        assert len(result) == 2

    def test_each_item_has_expected_keys(self, repo):
        repo.create_profile("list_keys")
        items = repo.list_all_profiles()
        item = items[0]
        for key in ("user_id", "created_at", "db_updated_at", "total_sessions", "facts_count"):
            assert key in item, f"Missing key: {key}"

    def test_ordered_by_updated_at_desc(self, repo):
        """Most-recently-updated profile should appear first."""
        import time
        repo.create_profile("old_profile")
        time.sleep(0.01)
        repo.create_profile("new_profile")
        items = repo.list_all_profiles()
        user_ids = [i["user_id"] for i in items]
        assert user_ids[0] == "new_profile"


# ---------------------------------------------------------------------------
# TestLinkSessionToUser
# ---------------------------------------------------------------------------

class TestLinkSessionToUser:
    """link_session_to_user: insert / ignore-duplicate paths."""

    def test_link_creates_association(self, repo, db_path):
        repo.create_profile("link_user")
        _insert_chat_session(db_path, "sess_001")
        repo.link_session_to_user("link_user", "sess_001")

        sessions = repo.get_user_sessions("link_user")
        assert "sess_001" in sessions

    def test_linking_twice_is_idempotent(self, repo, db_path):
        repo.create_profile("idem_link")
        _insert_chat_session(db_path, "sess_idem")
        repo.link_session_to_user("idem_link", "sess_idem")
        repo.link_session_to_user("idem_link", "sess_idem")  # INSERT OR IGNORE

        sessions = repo.get_user_sessions("idem_link")
        assert sessions.count("sess_idem") == 1

    def test_multiple_sessions_per_user(self, repo, db_path):
        repo.create_profile("multi_link")
        for sid in ("s1", "s2", "s3"):
            _insert_chat_session(db_path, sid)
            repo.link_session_to_user("multi_link", sid)

        sessions = repo.get_user_sessions("multi_link")
        assert set(sessions) == {"s1", "s2", "s3"}


# ---------------------------------------------------------------------------
# TestGetUserSessions
# ---------------------------------------------------------------------------

class TestGetUserSessions:
    """get_user_sessions: list ordering + empty."""

    def test_returns_empty_list_for_unknown_user(self, repo):
        result = repo.get_user_sessions("nobody")
        assert result == []

    def test_returns_session_ids(self, repo, db_path):
        repo.create_profile("sess_list_user")
        _insert_chat_session(db_path, "sA")
        _insert_chat_session(db_path, "sB")
        repo.link_session_to_user("sess_list_user", "sA")
        repo.link_session_to_user("sess_list_user", "sB")

        sessions = repo.get_user_sessions("sess_list_user")
        assert isinstance(sessions, list)
        assert set(sessions) == {"sA", "sB"}


# ---------------------------------------------------------------------------
# TestGetSessionUser
# ---------------------------------------------------------------------------

class TestGetSessionUser:
    """get_session_user: reverse-lookup session→user."""

    def test_returns_none_for_unknown_session(self, repo):
        result = repo.get_session_user("unknown_sess")
        assert result is None

    def test_returns_user_id_for_linked_session(self, repo, db_path):
        repo.create_profile("reverse_user")
        _insert_chat_session(db_path, "rev_sess")
        repo.link_session_to_user("reverse_user", "rev_sess")

        result = repo.get_session_user("rev_sess")
        assert result == "reverse_user"


# ---------------------------------------------------------------------------
# TestUnlinkSessionFromUser
# ---------------------------------------------------------------------------

class TestUnlinkSessionFromUser:
    """unlink_session_from_user: True / False return values."""

    def test_unlink_existing_returns_true(self, repo, db_path):
        repo.create_profile("unlink_user")
        _insert_chat_session(db_path, "unlink_sess")
        repo.link_session_to_user("unlink_user", "unlink_sess")

        result = repo.unlink_session_from_user("unlink_user", "unlink_sess")
        assert result is True

    def test_session_gone_after_unlink(self, repo, db_path):
        repo.create_profile("gone_user")
        _insert_chat_session(db_path, "gone_sess")
        repo.link_session_to_user("gone_user", "gone_sess")
        repo.unlink_session_from_user("gone_user", "gone_sess")

        sessions = repo.get_user_sessions("gone_user")
        assert "gone_sess" not in sessions

    def test_unlink_nonexistent_returns_false(self, repo):
        result = repo.unlink_session_from_user("nobody", "nosession")
        assert result is False

    def test_unlink_wrong_user_returns_false(self, repo, db_path):
        repo.create_profile("owner")
        repo.create_profile("other")
        _insert_chat_session(db_path, "owned_sess")
        repo.link_session_to_user("owner", "owned_sess")

        result = repo.unlink_session_from_user("other", "owned_sess")
        assert result is False


# ---------------------------------------------------------------------------
# TestGetUserByName
# ---------------------------------------------------------------------------

class TestGetUserByName:
    """get_user_by_name: fuzzy (exact-lowercase) name search."""

    def test_returns_none_when_no_profiles(self, repo):
        result = repo.get_user_by_name("Alice")
        assert result is None

    def test_returns_none_when_no_name_set(self, repo):
        repo.create_profile("unnamed")
        result = repo.get_user_by_name("Anyone")
        assert result is None

    def test_finds_user_by_exact_name(self, repo):
        profile = repo.create_profile("alice_id")
        profile.data["name"] = "Alice"
        repo.update_profile(profile)

        result = repo.get_user_by_name("Alice")
        assert result == "alice_id"

    def test_name_match_is_case_insensitive(self, repo):
        profile = repo.create_profile("alice_lower")
        profile.data["name"] = "Alice"
        repo.update_profile(profile)

        assert repo.get_user_by_name("alice") == "alice_lower"
        assert repo.get_user_by_name("ALICE") == "alice_lower"
        assert repo.get_user_by_name("Alice") == "alice_lower"

    def test_returns_none_for_partial_name(self, repo):
        profile = repo.create_profile("partial_name_user")
        profile.data["name"] = "Alice"
        repo.update_profile(profile)

        result = repo.get_user_by_name("Ali")
        assert result is None

    def test_finds_correct_user_among_many(self, repo):
        for uid, name in (("u1", "Bob"), ("u2", "Carol"), ("u3", "Dave")):
            p = repo.create_profile(uid)
            p.data["name"] = name
            repo.update_profile(p)

        assert repo.get_user_by_name("Carol") == "u2"
        assert repo.get_user_by_name("Bob") == "u1"
        assert repo.get_user_by_name("Dave") == "u3"

    def test_returns_none_for_nonexistent_name(self, repo):
        p = repo.create_profile("has_name")
        p.data["name"] = "Known"
        repo.update_profile(p)

        result = repo.get_user_by_name("Unknown")
        assert result is None


# ---------------------------------------------------------------------------
# TestDeleteCascade
# ---------------------------------------------------------------------------

class TestDeleteCascade:
    """Deleting a profile cascades to user_sessions (FK ON DELETE CASCADE)."""

    def test_delete_profile_removes_sessions(self, repo, db_path):
        repo.create_profile("cascade_user")
        _insert_chat_session(db_path, "casc_sess")
        repo.link_session_to_user("cascade_user", "casc_sess")

        # Confirm link exists
        assert "casc_sess" in repo.get_user_sessions("cascade_user")

        repo.delete_profile("cascade_user")

        # After deletion the session should no longer be findable via user_id
        result = repo.get_user_sessions("cascade_user")
        assert result == []
