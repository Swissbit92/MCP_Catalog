"""Comprehensive unit tests for TradeProposalRepository.

Coverage targets:
- create_proposal (happy path, custom TTL, various proposal types)
- get_proposal (found, not found, expired-pending auto-mark, non-pending expired)
- confirm_proposal (pending→confirmed, nonexistent, already confirmed, already cancelled, expired)
- cancel_proposal (pending→cancelled, nonexistent, already confirmed, already cancelled)
- expire_old_proposals (none, one, many, skips non-pending)
- get_pending_proposals (empty, one, multiple, filtered by user, excludes expired/non-pending)
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from src.coordinator.repositories.trade_proposal_repository import TradeProposalRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repo(tmp_path):
    """Fresh TradeProposalRepository backed by a temp SQLite file."""
    db_path = str(tmp_path / "test_proposals.db")
    return TradeProposalRepository(db_path)


def _make_proposal(repo: TradeProposalRepository, user_id: str = "user1",
                   proposal_type: str = "swap", data: dict | None = None,
                   ttl_seconds: int = 300) -> dict:
    if data is None:
        data = {"from": "SOL", "to": "USDC", "amount": 10.0}
    return repo.create_proposal(user_id, proposal_type, data, ttl_seconds)


# ---------------------------------------------------------------------------
# Tests — create_proposal
# ---------------------------------------------------------------------------

class TestCreateProposal:
    def test_returns_dict_with_expected_keys(self, repo):
        result = _make_proposal(repo)
        assert isinstance(result, dict)
        for key in ("id", "user_id", "proposal_type", "proposal_json",
                    "status", "created_at", "expires_at"):
            assert key in result

    def test_status_is_pending(self, repo):
        result = _make_proposal(repo)
        assert result["status"] == "pending"

    def test_proposal_json_is_serialized(self, repo):
        data = {"from": "BTC", "to": "ETH", "amount": 0.5}
        result = _make_proposal(repo, data=data)
        parsed = json.loads(result["proposal_json"])
        assert parsed == data

    def test_id_is_uuid_string(self, repo):
        import uuid
        result = _make_proposal(repo)
        # should not raise
        uuid.UUID(result["id"])

    def test_user_id_stored(self, repo):
        result = _make_proposal(repo, user_id="alice")
        assert result["user_id"] == "alice"

    def test_proposal_type_stored(self, repo):
        result = _make_proposal(repo, proposal_type="strategy")
        assert result["proposal_type"] == "strategy"

    def test_expires_at_is_after_created_at(self, repo):
        result = _make_proposal(repo, ttl_seconds=60)
        created = datetime.fromisoformat(result["created_at"].replace("Z", "+00:00"))
        expires = datetime.fromisoformat(result["expires_at"].replace("Z", "+00:00"))
        assert expires > created

    def test_custom_ttl_reflected(self, repo):
        result_short = _make_proposal(repo, ttl_seconds=10)
        result_long = _make_proposal(repo, ttl_seconds=600)
        exp_short = datetime.fromisoformat(result_short["expires_at"].replace("Z", "+00:00"))
        exp_long = datetime.fromisoformat(result_long["expires_at"].replace("Z", "+00:00"))
        assert exp_long > exp_short

    def test_multiple_proposals_have_distinct_ids(self, repo):
        a = _make_proposal(repo)
        b = _make_proposal(repo)
        assert a["id"] != b["id"]

    def test_timestamps_are_iso_format(self, repo):
        result = _make_proposal(repo)
        # Should parse without error
        datetime.fromisoformat(result["created_at"].replace("Z", "+00:00"))
        datetime.fromisoformat(result["expires_at"].replace("Z", "+00:00"))

    def test_empty_proposal_data(self, repo):
        result = _make_proposal(repo, data={})
        assert json.loads(result["proposal_json"]) == {}

    def test_nested_proposal_data(self, repo):
        data = {"nested": {"key": [1, 2, 3]}, "flag": True}
        result = _make_proposal(repo, data=data)
        assert json.loads(result["proposal_json"]) == data


# ---------------------------------------------------------------------------
# Tests — get_proposal
# ---------------------------------------------------------------------------

class TestGetProposal:
    def test_get_existing_pending(self, repo):
        created = _make_proposal(repo)
        fetched = repo.get_proposal(created["id"])
        assert fetched is not None
        assert fetched["id"] == created["id"]

    def test_get_nonexistent_returns_none(self, repo):
        result = repo.get_proposal("00000000-0000-0000-0000-000000000000")
        assert result is None

    def test_expired_pending_returns_none_and_marks_expired(self, repo):
        # Create with 1s TTL, then check after forcing time forward
        created = _make_proposal(repo, ttl_seconds=1)
        proposal_id = created["id"]

        # Manually set expires_at to past to simulate expiry
        past = datetime.now(timezone.utc) - timedelta(seconds=10)
        past_str = past.strftime("%Y-%m-%dT%H:%M:%SZ")
        repo._execute(
            "UPDATE trade_proposals SET expires_at = ? WHERE id = ?",
            (past_str, proposal_id),
        )

        result = repo.get_proposal(proposal_id)
        assert result is None

        # Verify it was marked expired in DB
        row = repo._fetchone_dict(
            "SELECT status FROM trade_proposals WHERE id = ?", (proposal_id,)
        )
        assert row["status"] == "expired"

    def test_confirmed_proposal_returned_even_if_past_expiry(self, repo):
        """Non-pending proposals should not be auto-expired by get_proposal."""
        created = _make_proposal(repo, ttl_seconds=300)
        repo.confirm_proposal(created["id"])

        # Push expires_at into the past
        past = datetime.now(timezone.utc) - timedelta(seconds=10)
        past_str = past.strftime("%Y-%m-%dT%H:%M:%SZ")
        repo._execute(
            "UPDATE trade_proposals SET expires_at = ? WHERE id = ?",
            (past_str, created["id"]),
        )

        result = repo.get_proposal(created["id"])
        # confirmed proposals are NOT None even past expiry (only pending ones expire)
        assert result is not None
        assert result["status"] == "confirmed"

    def test_get_returns_all_fields(self, repo):
        created = _make_proposal(repo)
        fetched = repo.get_proposal(created["id"])
        for key in ("id", "user_id", "proposal_type", "proposal_json",
                    "status", "created_at", "expires_at"):
            assert key in fetched


# ---------------------------------------------------------------------------
# Tests — confirm_proposal
# ---------------------------------------------------------------------------

class TestConfirmProposal:
    def test_confirm_pending_returns_true(self, repo):
        created = _make_proposal(repo)
        assert repo.confirm_proposal(created["id"]) is True

    def test_confirmed_proposal_has_confirmed_status(self, repo):
        created = _make_proposal(repo)
        repo.confirm_proposal(created["id"])
        row = repo._fetchone_dict(
            "SELECT status FROM trade_proposals WHERE id = ?", (created["id"],)
        )
        assert row["status"] == "confirmed"

    def test_confirm_nonexistent_returns_false(self, repo):
        assert repo.confirm_proposal("nonexistent-id") is False

    def test_confirm_already_confirmed_returns_false(self, repo):
        created = _make_proposal(repo)
        repo.confirm_proposal(created["id"])
        assert repo.confirm_proposal(created["id"]) is False

    def test_confirm_cancelled_returns_false(self, repo):
        created = _make_proposal(repo)
        repo.cancel_proposal(created["id"])
        assert repo.confirm_proposal(created["id"]) is False

    def test_confirm_expired_returns_false(self, repo):
        created = _make_proposal(repo)
        # Expire it manually
        past = datetime.now(timezone.utc) - timedelta(seconds=10)
        repo._execute(
            "UPDATE trade_proposals SET expires_at = ?, status = 'expired' WHERE id = ?",
            (past.strftime("%Y-%m-%dT%H:%M:%SZ"), created["id"]),
        )
        assert repo.confirm_proposal(created["id"]) is False


# ---------------------------------------------------------------------------
# Tests — cancel_proposal
# ---------------------------------------------------------------------------

class TestCancelProposal:
    def test_cancel_pending_returns_true(self, repo):
        created = _make_proposal(repo)
        assert repo.cancel_proposal(created["id"]) is True

    def test_cancelled_proposal_has_cancelled_status(self, repo):
        created = _make_proposal(repo)
        repo.cancel_proposal(created["id"])
        row = repo._fetchone_dict(
            "SELECT status FROM trade_proposals WHERE id = ?", (created["id"],)
        )
        assert row["status"] == "cancelled"

    def test_cancel_nonexistent_returns_false(self, repo):
        assert repo.cancel_proposal("nonexistent-id") is False

    def test_cancel_already_cancelled_returns_false(self, repo):
        created = _make_proposal(repo)
        repo.cancel_proposal(created["id"])
        assert repo.cancel_proposal(created["id"]) is False

    def test_cancel_confirmed_returns_false(self, repo):
        created = _make_proposal(repo)
        repo.confirm_proposal(created["id"])
        assert repo.cancel_proposal(created["id"]) is False

    def test_cancel_expired_returns_false(self, repo):
        """cancel_proposal uses raw DB fetch (not get_proposal), so it checks status directly."""
        created = _make_proposal(repo)
        repo._execute(
            "UPDATE trade_proposals SET status = 'expired' WHERE id = ?",
            (created["id"],),
        )
        assert repo.cancel_proposal(created["id"]) is False


# ---------------------------------------------------------------------------
# Tests — expire_old_proposals
# ---------------------------------------------------------------------------

class TestExpireOldProposals:
    def test_no_expired_proposals_returns_zero(self, repo):
        _make_proposal(repo, ttl_seconds=3600)
        assert repo.expire_old_proposals() == 0

    def test_one_expired_returns_one(self, repo):
        created = _make_proposal(repo, ttl_seconds=300)
        past = (datetime.now(timezone.utc) - timedelta(seconds=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
        repo._execute(
            "UPDATE trade_proposals SET expires_at = ? WHERE id = ?",
            (past, created["id"]),
        )
        count = repo.expire_old_proposals()
        assert count == 1

    def test_multiple_expired_returns_correct_count(self, repo):
        ids = [_make_proposal(repo)["id"] for _ in range(3)]
        past = (datetime.now(timezone.utc) - timedelta(seconds=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for pid in ids:
            repo._execute(
                "UPDATE trade_proposals SET expires_at = ? WHERE id = ?",
                (past, pid),
            )
        assert repo.expire_old_proposals() == 3

    def test_expire_marks_status_expired(self, repo):
        created = _make_proposal(repo)
        past = (datetime.now(timezone.utc) - timedelta(seconds=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        repo._execute(
            "UPDATE trade_proposals SET expires_at = ? WHERE id = ?",
            (past, created["id"]),
        )
        repo.expire_old_proposals()
        row = repo._fetchone_dict(
            "SELECT status FROM trade_proposals WHERE id = ?", (created["id"],)
        )
        assert row["status"] == "expired"

    def test_skips_confirmed_proposals(self, repo):
        created = _make_proposal(repo)
        repo.confirm_proposal(created["id"])
        past = (datetime.now(timezone.utc) - timedelta(seconds=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        repo._execute(
            "UPDATE trade_proposals SET expires_at = ? WHERE id = ?",
            (past, created["id"]),
        )
        count = repo.expire_old_proposals()
        assert count == 0

    def test_skips_cancelled_proposals(self, repo):
        created = _make_proposal(repo)
        repo.cancel_proposal(created["id"])
        past = (datetime.now(timezone.utc) - timedelta(seconds=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        repo._execute(
            "UPDATE trade_proposals SET expires_at = ? WHERE id = ?",
            (past, created["id"]),
        )
        assert repo.expire_old_proposals() == 0

    def test_skips_already_expired(self, repo):
        created = _make_proposal(repo)
        past = (datetime.now(timezone.utc) - timedelta(seconds=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        repo._execute(
            "UPDATE trade_proposals SET expires_at = ?, status = 'expired' WHERE id = ?",
            (past, created["id"]),
        )
        assert repo.expire_old_proposals() == 0

    def test_mixed_proposals_only_expires_pending_old(self, repo):
        # One valid pending, one expired pending, one confirmed
        valid = _make_proposal(repo, ttl_seconds=3600)
        expired_one = _make_proposal(repo)
        confirmed = _make_proposal(repo)
        repo.confirm_proposal(confirmed["id"])

        past = (datetime.now(timezone.utc) - timedelta(seconds=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        repo._execute(
            "UPDATE trade_proposals SET expires_at = ? WHERE id = ?",
            (past, expired_one["id"]),
        )
        count = repo.expire_old_proposals()
        assert count == 1


# ---------------------------------------------------------------------------
# Tests — get_pending_proposals
# ---------------------------------------------------------------------------

class TestGetPendingProposals:
    def test_empty_for_unknown_user(self, repo):
        assert repo.get_pending_proposals("ghost") == []

    def test_returns_pending_proposal(self, repo):
        _make_proposal(repo, user_id="alice")
        results = repo.get_pending_proposals("alice")
        assert len(results) == 1
        assert results[0]["status"] == "pending"

    def test_returns_multiple_pending(self, repo):
        for _ in range(3):
            _make_proposal(repo, user_id="bob")
        results = repo.get_pending_proposals("bob")
        assert len(results) == 3

    def test_isolates_by_user(self, repo):
        _make_proposal(repo, user_id="alice")
        _make_proposal(repo, user_id="bob")
        assert len(repo.get_pending_proposals("alice")) == 1
        assert len(repo.get_pending_proposals("bob")) == 1
        assert len(repo.get_pending_proposals("charlie")) == 0

    def test_excludes_confirmed(self, repo):
        created = _make_proposal(repo, user_id="dave")
        repo.confirm_proposal(created["id"])
        assert repo.get_pending_proposals("dave") == []

    def test_excludes_cancelled(self, repo):
        created = _make_proposal(repo, user_id="eve")
        repo.cancel_proposal(created["id"])
        assert repo.get_pending_proposals("eve") == []

    def test_excludes_expired_proposals(self, repo):
        created = _make_proposal(repo, user_id="frank")
        past = (datetime.now(timezone.utc) - timedelta(seconds=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        repo._execute(
            "UPDATE trade_proposals SET expires_at = ? WHERE id = ?",
            (past, created["id"]),
        )
        assert repo.get_pending_proposals("frank") == []

    def test_ordered_newest_first(self, repo):
        """Created_at ordering — manually set distinct timestamps to test ordering."""
        a = _make_proposal(repo, user_id="grace")
        b = _make_proposal(repo, user_id="grace")
        # Ensure distinct created_at by setting a's timestamp to the past
        past = "2020-01-01T00:00:00Z"
        future = "2030-01-01T00:00:00Z"
        repo._execute(
            "UPDATE trade_proposals SET created_at = ? WHERE id = ?",
            (past, a["id"]),
        )
        repo._execute(
            "UPDATE trade_proposals SET created_at = ? WHERE id = ?",
            (future, b["id"]),
        )
        results = repo.get_pending_proposals("grace")
        # Both present; b has newer created_at so should come first
        assert len(results) == 2
        assert results[0]["id"] == b["id"]
        assert results[1]["id"] == a["id"]

    def test_result_dicts_have_expected_keys(self, repo):
        _make_proposal(repo, user_id="heidi")
        results = repo.get_pending_proposals("heidi")
        for key in ("id", "user_id", "proposal_type", "status", "created_at", "expires_at"):
            assert key in results[0]
