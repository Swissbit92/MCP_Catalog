"""
Unit tests for src/coordinator/routes/personas.py

Mocks:
- src.coordinator.routes.personas._load_all_cards_cached
- src.coordinator.routes.personas.cleanup_orphaned_sessions
- src.coordinator.routes.personas.get_or_build_cv_summary
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from fastapi.testclient import TestClient
from src.coordinator.server import app

client = TestClient(app)  # no context manager → lifespan skipped

_CARD_MINIMAL = {
    "key": "eeva",
    "display_name": "E.E.V.A.",
    "style": "analytical",
    "rarity": "archon",
    "celestial_order": "archon",
    "mcp_access": ["brave", "wallet"],
    "coordinator_label": "Financial AI",
    "image": "/images/eeva.png",
    "avatar": "/images/eeva_avatar.png",
    "bg": "/images/eeva_bg.png",
    "voice": "en-US-Neural",
}

_CARD_WITH_LORE = {
    **_CARD_MINIMAL,
    "key": "aegis",
    "display_name": "Aegis",
    "nephilim_lore": {
        "relationships": {"eeva": "ally"},
        "realm_domain": "Protection",
        "secret_field": "should_be_stripped",
    },
}


class TestListPersonas:
    def test_empty_cards_returns_empty_list(self):
        with patch("src.coordinator.routes.personas._load_all_cards_cached", return_value=[]), \
             patch("src.coordinator.routes.personas.cleanup_orphaned_sessions") as mock_cleanup:
            resp = client.get("/personas")
        assert resp.status_code == 200
        assert resp.json() == []
        # Cleanup called when key set changes (empty → empty: first call sets keys)
        # Depending on prior state this may or may not call; just assert no exception.

    def test_single_card_returned(self):
        with patch("src.coordinator.routes.personas._load_all_cards_cached", return_value=[_CARD_MINIMAL]):
            resp = client.get("/personas")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["key"] == "eeva"
        assert data[0]["display_name"] == "E.E.V.A."

    def test_response_shape_has_expected_keys(self):
        with patch("src.coordinator.routes.personas._load_all_cards_cached", return_value=[_CARD_MINIMAL]):
            resp = client.get("/personas")
        p = resp.json()[0]
        for key in ("key", "display_name", "style", "rarity", "celestial_order", "mcp_access"):
            assert key in p, f"Missing key '{key}'"

    def test_nephilim_lore_slimmed_to_relationships_and_realm_domain(self):
        with patch("src.coordinator.routes.personas._load_all_cards_cached", return_value=[_CARD_WITH_LORE]):
            resp = client.get("/personas")
        lore = resp.json()[0]["nephilim_lore"]
        assert "relationships" in lore
        assert "realm_domain" in lore
        assert "secret_field" not in lore

    def test_card_without_lore_has_no_nephilim_lore_key(self):
        with patch("src.coordinator.routes.personas._load_all_cards_cached", return_value=[_CARD_MINIMAL]):
            resp = client.get("/personas")
        assert "nephilim_lore" not in resp.json()[0]

    def test_multiple_cards(self):
        cards = [_CARD_MINIMAL, {**_CARD_MINIMAL, "key": "nyx", "display_name": "Nyx"}]
        with patch("src.coordinator.routes.personas._load_all_cards_cached", return_value=cards):
            resp = client.get("/personas")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_display_name_falls_back_to_key(self):
        card = {**_CARD_MINIMAL, "display_name": None}
        with patch("src.coordinator.routes.personas._load_all_cards_cached", return_value=[card]):
            resp = client.get("/personas")
        assert resp.json()[0]["display_name"] == "eeva"

    def test_cleanup_called_when_keys_change(self):
        import src.coordinator.routes.personas as pmod
        pmod._last_persona_keys = set()  # ensure fresh state
        with patch("src.coordinator.routes.personas._load_all_cards_cached", return_value=[_CARD_MINIMAL]), \
             patch("src.coordinator.routes.personas.cleanup_orphaned_sessions") as mock_cleanup:
            client.get("/personas")
        mock_cleanup.assert_called_once()

    def test_exception_in_load_returns_500(self):
        with patch("src.coordinator.routes.personas._load_all_cards_cached", side_effect=RuntimeError("disk error")):
            resp = client.get("/personas")
        assert resp.status_code == 500
        assert "Failed to list personas" in resp.json()["detail"]


class TestPersonaSummary:
    def test_happy_path_returns_summary(self):
        fake_data = {"key": "eeva", "hash": "abc123", "updated": "2026-01-01", "summary": "E.E.V.A. is the financial AI."}
        with patch("src.coordinator.routes.personas.get_or_build_cv_summary", return_value=fake_data):
            resp = client.post("/persona/summary", json={"persona": "eeva"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["key"] == "eeva"
        assert "summary" in body

    def test_none_persona_is_accepted(self):
        fake_data = {"key": "eeva", "hash": "abc", "updated": "2026-01-01", "summary": "..."}
        with patch("src.coordinator.routes.personas.get_or_build_cv_summary", return_value=fake_data):
            resp = client.post("/persona/summary", json={"persona": None})
        assert resp.status_code == 200

    def test_exception_returns_500(self):
        with patch("src.coordinator.routes.personas.get_or_build_cv_summary", side_effect=ValueError("not found")):
            resp = client.post("/persona/summary", json={"persona": "unknown"})
        assert resp.status_code == 500
        assert "Summary error" in resp.json()["detail"]

    def test_missing_persona_field_uses_none_default(self):
        fake_data = {"key": "eeva", "hash": "x", "updated": "2026-01-01", "summary": "..."}
        with patch("src.coordinator.routes.personas.get_or_build_cv_summary", return_value=fake_data) as mock_fn:
            resp = client.post("/persona/summary", json={})
        assert resp.status_code == 200
        mock_fn.assert_called_once_with(None)
