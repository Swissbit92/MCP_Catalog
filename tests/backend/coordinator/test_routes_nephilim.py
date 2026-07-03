"""
Unit tests for src/coordinator/routes/nephilim.py

Mocks:
- src.coordinator.routes.nephilim.get_seeker_progression_repo  (via _require_progression_repo dependency)
- src.coordinator.routes.nephilim.get_persona_card
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from fastapi.testclient import TestClient
from src.coordinator.server import app
from src.coordinator.routes.nephilim import _require_progression_repo

client = TestClient(app)

# ─── Fake data ────────────────────────────────────────────────────────────────

_FAKE_PROFILE = {
    "user_id": "user-1",
    "rank_name": "Initiate",
    "total_resonance": 0,
    "faction_primary": None,
    "faction_secondary": None,
    "rank_achieved_at": None,
    "created_at": "2026-01-01T00:00:00",
    "updated_at": "2026-01-01T00:00:00",
}

_FAKE_RANK_PROGRESS = {
    "current_rank": "Initiate",
    "current_resonance": 0,
    "next_rank": "Acolyte",
    "resonance_needed": 100,
    "progress_percent": 0,
}

_FAKE_AFFINITY = {
    "user_id": "user-1",
    "persona_key": "eeva",
    "messages_count": 5,
    "affinity_level": 1,
    "first_conversation": "2026-01-01T00:00:00",
    "last_conversation": "2026-01-02T00:00:00",
}

_FAKE_LORE = {
    "id": 1,
    "user_id": "user-1",
    "persona_key": "eeva",
    "fragment_id": "frag-1",
    "unlocked_at": "2026-01-01T00:00:00",
}

_FAKE_SUMMARY = {
    "exists": True,
    "user_id": "user-1",
    "rank": "Initiate",
    "total_resonance": 0,
    "faction_primary": None,
    "faction_secondary": None,
    "rank_progress": _FAKE_RANK_PROGRESS,
    "persona_affinities": [_FAKE_AFFINITY],
    "unlocked_lore_count": 0,
    "created_at": "2026-01-01T00:00:00",
    "updated_at": "2026-01-01T00:00:00",
}


def _make_repo():
    repo = MagicMock()
    repo.get_or_create_seeker.return_value = _FAKE_PROFILE
    repo.get_seeker_summary.return_value = _FAKE_SUMMARY
    repo.get_resonance_to_next_rank.return_value = _FAKE_RANK_PROGRESS
    repo.award_resonance.return_value = {"new_resonance": 10, "new_rank": "Initiate", "rank_changed": False, "previous_rank": "Initiate"}
    repo.get_resonance_history.return_value = []
    repo.get_all_affinities.return_value = [_FAKE_AFFINITY]
    repo.get_or_create_affinity.return_value = _FAKE_AFFINITY
    repo.get_unlocked_lore.return_value = [_FAKE_LORE]
    repo.update_seeker_faction.return_value = True
    repo.check_and_unlock_lore.return_value = []
    return repo


def _patch_repo(repo=None):
    r = repo or _make_repo()
    return patch.object(app, "dependency_overrides", {**app.dependency_overrides, _require_progression_repo: lambda: r}), r


# ─── Seeker profile ───────────────────────────────────────────────────────────

class TestGetSeekerProfile:
    def test_returns_profile(self):
        repo = _make_repo()
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            resp = client.get("/nephilim/seeker/user-1")
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == "user-1"
        assert body["rank_name"] == "Initiate"

    def test_calls_get_or_create_seeker(self):
        repo = _make_repo()
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            client.get("/nephilim/seeker/user-99")
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        repo.get_or_create_seeker.assert_called_once_with("user-99")

    def test_503_when_repo_not_initialized(self):
        from src.coordinator.routes.nephilim import _require_progression_repo
        with patch("src.coordinator.routes.nephilim.get_seeker_progression_repo", side_effect=RuntimeError("not init")):
            resp = client.get("/nephilim/seeker/user-1")
        assert resp.status_code == 503


class TestGetSeekerSummary:
    def test_returns_summary(self):
        repo = _make_repo()
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            resp = client.get("/nephilim/seeker/user-1/summary")
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 200
        body = resp.json()
        assert body["exists"] is True
        assert body["user_id"] == "user-1"
        assert "persona_affinities" in body

    def test_summary_with_no_rank_progress(self):
        repo = _make_repo()
        summary = {**_FAKE_SUMMARY, "rank_progress": None}
        repo.get_seeker_summary.return_value = summary
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            resp = client.get("/nephilim/seeker/user-1/summary")
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 200
        assert resp.json()["rank_progress"] is None


class TestSetFaction:
    def test_valid_faction_set(self):
        repo = _make_repo()
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            resp = client.post("/nephilim/seeker/user-1/faction", json={"faction_primary": "lumina"})
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["faction_primary"] == "lumina"

    def test_invalid_faction_returns_400(self):
        repo = _make_repo()
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            resp = client.post("/nephilim/seeker/user-1/faction", json={"faction_primary": "invalid_faction"})
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 400
        assert "Invalid faction" in resp.json()["detail"]

    def test_invalid_secondary_faction_returns_400(self):
        repo = _make_repo()
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            resp = client.post("/nephilim/seeker/user-1/faction", json={
                "faction_primary": "lumina",
                "faction_secondary": "bad_faction",
            })
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 400

    def test_faction_not_updated_returns_404(self):
        repo = _make_repo()
        repo.update_seeker_faction.return_value = False
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            resp = client.post("/nephilim/seeker/user-1/faction", json={"faction_primary": "prism"})
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 404

    def test_all_valid_factions_accepted(self):
        valid = ["lumina", "ironclad", "sanctuary", "prism", "archive", "horizon"]
        repo = _make_repo()
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            for faction in valid:
                resp = client.post("/nephilim/seeker/user-1/faction", json={"faction_primary": faction})
                assert resp.status_code == 200, f"Expected 200 for faction '{faction}', got {resp.status_code}"
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)


class TestGetRankProgress:
    def test_returns_rank_progress(self):
        repo = _make_repo()
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            resp = client.get("/nephilim/seeker/user-1/rank")
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 200
        body = resp.json()
        assert "current_rank" in body
        assert "progress_percent" in body


class TestAwardResonance:
    def test_awards_resonance(self):
        repo = _make_repo()
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            resp = client.post("/nephilim/seeker/user-1/resonance", json={
                "amount": 10,
                "reason": "test award",
            })
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert "new_resonance" in body
        assert "rank_changed" in body

    def test_zero_amount_returns_400(self):
        repo = _make_repo()
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            resp = client.post("/nephilim/seeker/user-1/resonance", json={"amount": 0, "reason": "x"})
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 400

    def test_negative_amount_returns_400(self):
        repo = _make_repo()
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            resp = client.post("/nephilim/seeker/user-1/resonance", json={"amount": -5, "reason": "x"})
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 400


class TestResonanceHistory:
    def test_returns_events_list(self):
        repo = _make_repo()
        repo.get_resonance_history.return_value = [{"amount": 10, "reason": "chat"}]
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            resp = client.get("/nephilim/seeker/user-1/resonance/history")
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 200
        assert "events" in resp.json()

    def test_custom_limit_accepted(self):
        repo = _make_repo()
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            resp = client.get("/nephilim/seeker/user-1/resonance/history?limit=10")
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 200
        repo.get_resonance_history.assert_called_once_with("user-1", 10)

    def test_limit_too_large_returns_422(self):
        repo = _make_repo()
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            resp = client.get("/nephilim/seeker/user-1/resonance/history?limit=999")
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 422


class TestAffinities:
    def test_get_all_affinities(self):
        repo = _make_repo()
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            resp = client.get("/nephilim/seeker/user-1/affinity")
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_persona_affinity(self):
        repo = _make_repo()
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            resp = client.get("/nephilim/seeker/user-1/affinity/eeva")
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 200
        body = resp.json()
        assert body["persona_key"] == "eeva"

    def test_empty_affinities_returns_empty_list(self):
        repo = _make_repo()
        repo.get_all_affinities.return_value = []
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            resp = client.get("/nephilim/seeker/user-1/affinity")
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.json() == []


class TestLore:
    def test_get_unlocked_lore(self):
        repo = _make_repo()
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            resp = client.get("/nephilim/seeker/user-1/lore")
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_unlocked_lore_filter_by_persona(self):
        repo = _make_repo()
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            resp = client.get("/nephilim/seeker/user-1/lore?persona_key=eeva")
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 200
        repo.get_unlocked_lore.assert_called_once_with("user-1", "eeva")

    def test_get_persona_lore_with_content_persona_not_found(self):
        repo = _make_repo()
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            with patch("src.coordinator.routes.nephilim.get_persona_card", return_value=None):
                resp = client.get("/nephilim/seeker/user-1/lore/unknown_persona/full")
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 404

    def test_get_persona_lore_with_content_no_fragments(self):
        repo = _make_repo()
        fake_card = {"key": "eeva", "unlockable_lore": []}
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            with patch("src.coordinator.routes.nephilim.get_persona_card", return_value=fake_card):
                resp = client.get("/nephilim/seeker/user-1/lore/eeva/full")
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_persona_lore_with_content_unlocked(self):
        repo = _make_repo()
        repo.get_unlocked_lore.return_value = [{"fragment_id": "frag-1", "unlocked_at": "2026-01-01"}]
        fake_card = {
            "key": "eeva",
            "unlockable_lore": [
                {"fragment_id": "frag-1", "fragment_title": "The Beginning", "fragment": "Long ago...", "messages_required": 5, "rarity": "common"},
            ],
        }
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            with patch("src.coordinator.routes.nephilim.get_persona_card", return_value=fake_card):
                resp = client.get("/nephilim/seeker/user-1/lore/eeva/full")
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 200
        frags = resp.json()
        assert frags[0]["unlocked"] is True
        assert frags[0]["fragment"] == "Long ago..."

    def test_get_persona_lore_locked_fragment_hides_content(self):
        repo = _make_repo()
        repo.get_unlocked_lore.return_value = []  # nothing unlocked
        fake_card = {
            "key": "eeva",
            "unlockable_lore": [
                {"fragment_id": "frag-1", "fragment_title": "Secret", "fragment": "Secret content", "messages_required": 50, "rarity": "rare"},
            ],
        }
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            with patch("src.coordinator.routes.nephilim.get_persona_card", return_value=fake_card):
                resp = client.get("/nephilim/seeker/user-1/lore/eeva/full")
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 200
        frags = resp.json()
        assert frags[0]["unlocked"] is False
        assert "Locked" in frags[0]["fragment"]

    def test_check_lore_unlocks_persona_not_found(self):
        repo = _make_repo()
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            with patch("src.coordinator.routes.nephilim.get_persona_card", return_value=None):
                resp = client.post("/nephilim/seeker/user-1/lore/unknown/check")
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 404

    def test_check_lore_unlocks_success(self):
        repo = _make_repo()
        fake_card = {"key": "eeva", "unlockable_lore": []}
        app.dependency_overrides[_require_progression_repo] = lambda: repo
        try:
            with patch("src.coordinator.routes.nephilim.get_persona_card", return_value=fake_card):
                resp = client.post("/nephilim/seeker/user-1/lore/eeva/check")
        finally:
            app.dependency_overrides.pop(_require_progression_repo, None)
        assert resp.status_code == 200
        body = resp.json()
        assert "newly_unlocked" in body
        assert "fragments" in body


class TestRanksAndFactions:
    def test_get_ranks_returns_list(self):
        resp = client.get("/nephilim/ranks")
        assert resp.status_code == 200
        body = resp.json()
        assert "ranks" in body
        assert len(body["ranks"]) > 0
        assert all("name" in r and "resonance_required" in r for r in body["ranks"])

    def test_get_factions_returns_six_factions(self):
        resp = client.get("/nephilim/factions")
        assert resp.status_code == 200
        body = resp.json()
        assert "factions" in body
        assert len(body["factions"]) == 6

    def test_faction_keys_are_correct(self):
        resp = client.get("/nephilim/factions")
        keys = {f["key"] for f in resp.json()["factions"]}
        assert keys == {"lumina", "ironclad", "sanctuary", "prism", "archive", "horizon"}
