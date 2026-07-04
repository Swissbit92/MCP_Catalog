# tests/backend/coordinator/test_capability_context.py
"""M4 tests — internal capability gating + diegetic unlock detection.

Headless: lore_loader capability lookups are monkeypatched; no Ollama/wiki needed.
On-demand lore retrieval is always on (LORE_ONDEMAND_ENABLED retired 2026-07-04),
so the flag-OFF cases were removed.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import src.coordinator.lore_loader as ll
import src.coordinator.lore_retrieval as lr


def _cap(eid, persona="nephilim_eeva", rank="Adept", aff=0, body="cap body", voice="v"):
    return {
        "entity_id": eid, "body": body, "entity_type": "capability",
        "frontmatter": {
            "title": eid, "activation_persona": persona,
            "activation_rank": rank, "activation_affinity": aff,
            "persona_voice_line": voice,
        },
    }


def _patch_caps(monkeypatch, caps):
    monkeypatch.setattr(ll, "get_capability_ids", lambda: list(caps.keys()))
    monkeypatch.setattr(ll, "load_entity_with_metadata", lambda eid: caps.get(eid))


class TestBuildCapabilityContext:
    def test_non_nephilim_empty(self, monkeypatch):
        _patch_caps(monkeypatch, {"c1": _cap("c1")})
        assert lr.build_capability_context("gojo", "Adept", 0) == ""

    def test_below_rank_excluded(self, monkeypatch):
        _patch_caps(monkeypatch, {"c1": _cap("c1", rank="Adept")})
        out = lr.build_capability_context("nephilim_eeva", "Acolyte", 0)
        assert out == ""

    def test_at_rank_included(self, monkeypatch):
        _patch_caps(monkeypatch, {"c1": _cap("c1", rank="Adept", body="deep counsel")})
        out = lr.build_capability_context("nephilim_eeva", "Adept", 0)
        assert "<capabilities>" in out and "c1" in out

    def test_below_affinity_excluded(self, monkeypatch):
        _patch_caps(monkeypatch, {"c1": _cap("c1", rank="Initiate", aff=5)})
        assert lr.build_capability_context("nephilim_eeva", "Adept", 3) == ""

    def test_persona_mismatch_excluded(self, monkeypatch):
        _patch_caps(monkeypatch, {"c1": _cap("c1", persona="nephilim_solace")})
        assert lr.build_capability_context("nephilim_eeva", "Nephilim", 0) == ""


class TestDetectNewCapabilityUnlocks:
    def test_returns_and_records_crossing_capability(self, monkeypatch):
        _patch_caps(monkeypatch, {"c1": _cap("c1", rank="Adept", voice="I see clearly now")})
        repo = MagicMock()
        repo.get_unlocked_lore.return_value = []  # nothing yet
        newly = lr.detect_new_capability_unlocks(repo, "u1", "nephilim_eeva", "Adept", 0)
        assert [c["id"] for c in newly] == ["c1"]
        assert newly[0]["persona_voice_line"] == "I see clearly now"
        repo.unlock_lore.assert_called_once_with("u1", "nephilim_eeva", "c1")

    def test_already_unlocked_not_refired(self, monkeypatch):
        _patch_caps(monkeypatch, {"c1": _cap("c1", rank="Adept")})
        repo = MagicMock()
        repo.get_unlocked_lore.return_value = [{"fragment_id": "c1"}]
        newly = lr.detect_new_capability_unlocks(repo, "u1", "nephilim_eeva", "Adept", 0)
        assert newly == []
        repo.unlock_lore.assert_not_called()
