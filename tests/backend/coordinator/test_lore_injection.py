# tests/backend/coordinator/test_lore_injection.py
"""M2 tests — per-turn hybrid lore injection (_build_ondemand_lore_context).

Headless: the embedder/lore_store are mocked; lore_loader lookups monkeypatched.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import src.coordinator.lore_loader as ll
import src.coordinator.services.chat_session_service as css

_build = css._build_ondemand_lore_context


def _settings(enabled=True, k=5, min_rel=0.5, window=4, budget=600):
    return SimpleNamespace(lore=SimpleNamespace(
        ondemand_enabled=enabled, retrieval_k=k, embed_min_relevance=min_rel,
        keyword_window_messages=window, max_budget_tokens=budget,
    ))


def _rag(search_return=None):
    rag = SimpleNamespace()
    rag.lore_store = object()  # truthy → "indexed"
    rag.search_lore = MagicMock(return_value=search_return or [])
    return rag


def _patch_loader(monkeypatch, aliases=None, bodies=None, core=None):
    monkeypatch.setattr(ll, "get_alias_index", lambda: (aliases or {}))
    monkeypatch.setattr(ll, "get_static_core_ids", lambda pk: (core or set()))
    bodies = bodies or {}
    monkeypatch.setattr(
        ll, "load_entity_with_metadata",
        lambda eid: ({"entity_id": eid, "body": bodies.get(eid, "")} if eid in bodies else None),
    )


class TestFlagOff:
    def test_flag_off_returns_empty_and_no_search(self, monkeypatch):
        rag = _rag()
        out = _build("tell me about ananke", [], "nephilim_eeva", rag, _settings(enabled=False))
        assert out == ""
        rag.search_lore.assert_not_called()

    def test_lore_store_none_returns_empty(self):
        rag = SimpleNamespace(lore_store=None, search_lore=MagicMock())
        out = _build("x", [], "nephilim_eeva", rag, _settings(enabled=True))
        assert out == ""
        rag.search_lore.assert_not_called()


class TestKeywordTier:
    def test_alias_match_injects_entity(self, monkeypatch):
        _patch_loader(monkeypatch, aliases={"ananke": "entity-ananke"},
                      bodies={"entity-ananke": "Ananke is the weaver of fate."})
        rag = _rag(search_return=[])
        out = _build("tell me about ananke please", [], "nephilim_eeva", rag, _settings())
        assert "entity-ananke" in out
        assert "<dynamic_lore>" in out

    def test_alias_in_core_is_excluded(self, monkeypatch):
        _patch_loader(monkeypatch, aliases={"eeva": "persona-eeva"},
                      bodies={"persona-eeva": "core"}, core={"persona-eeva"})
        rag = _rag(search_return=[])
        out = _build("hey eeva", [], "nephilim_eeva", rag, _settings())
        assert out == ""  # static core entity must not be re-injected


class TestEmbeddingTier:
    def test_semantic_hit_injects_entity(self, monkeypatch):
        _patch_loader(monkeypatch)
        rag = _rag(search_return=[({"entity_id": "concept-resonance", "body": "Resonance binds the realm."}, 0.72)])
        out = _build("what is the hum I feel", [], "nephilim_eeva", rag, _settings())
        assert "concept-resonance" in out

    def test_dedup_excludes_static_core(self, monkeypatch):
        _patch_loader(monkeypatch, core={"persona-eeva"})
        rag = _rag(search_return=[
            ({"entity_id": "persona-eeva", "body": "core"}, 0.9),
            ({"entity_id": "entity-aletheia", "body": "Aletheia witnesses truth."}, 0.7),
        ])
        out = _build("truth", [], "nephilim_eeva", rag, _settings())
        assert "persona-eeva" not in out
        assert "entity-aletheia" in out


class TestSeekerRankContext:
    def test_present_for_adept(self):
        out = css._build_seeker_rank_context("Adept")
        assert "<seeker_rank>" in out and "Adept" in out

    def test_empty_for_initiate_and_blank(self):
        assert css._build_seeker_rank_context("Initiate") == ""
        assert css._build_seeker_rank_context("") == ""


class TestBudget:
    def test_budget_drops_low_priority(self, monkeypatch):
        _patch_loader(monkeypatch)
        big = " ".join(["word"] * 200)
        rag = _rag(search_return=[
            ({"entity_id": f"e{i}", "body": big}, 0.6 - i * 0.01) for i in range(8)
        ])
        out = _build("q", [], "nephilim_eeva", rag, _settings(budget=200))
        injected = [ln for ln in out.splitlines() if ln.startswith("### ")]
        assert 1 <= len(injected) <= 2, f"budget should cap entries, got {len(injected)}"
