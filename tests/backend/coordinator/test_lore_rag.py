# tests/backend/coordinator/test_lore_rag.py
"""M1 tests — global lore corpus index + search_lore, and lore_loader helpers.

Loader tests run against the REAL wiki (no embedder). Store/filter tests use a
deterministic fake embedder (no Ollama). One @requires_ollama live test.
"""

from __future__ import annotations

import math
from typing import List

import pytest
from langchain_core.embeddings import Embeddings

import src.coordinator.lore_loader as ll
from src.coordinator.memory_rag import EpisodicMemoryRAG


# ---------------------------------------------------------------------------
# Deterministic fake embedder: char-frequency histogram → unit vector (dim 26).
# Subclasses langchain Embeddings so FAISS uses embed_query at search time.
# ---------------------------------------------------------------------------
class _FakeEmbeddings(Embeddings):
    def _vec(self, text: str) -> List[float]:
        v = [0.0] * 26
        for ch in text.lower():
            i = ord(ch) - 97
            if 0 <= i < 26:
                v[i] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._vec(text)


def _rag_with_fake() -> EpisodicMemoryRAG:
    rag = EpisodicMemoryRAG.__new__(EpisodicMemoryRAG)  # skip __init__/Ollama
    rag.embeddings = _FakeEmbeddings()
    rag._embed_max_tokens = 8192
    rag._embed_overlap = 128
    rag.vectorstores = {}
    rag.lore_store = None
    rag.use_gpu = False
    return rag


# ---------------------------------------------------------------------------
# Loader helpers — real wiki
# ---------------------------------------------------------------------------
class TestLoreLoaderHelpers:
    def test_get_all_entity_ids_nonempty(self):
        ids = ll.get_all_entity_ids()
        assert len(ids) >= 30, f"expected ~34 wiki entities, got {len(ids)}"
        assert "persona-eeva" in ids
        assert "concept-resonance" in ids

    def test_load_entity_with_metadata(self):
        meta = ll.load_entity_with_metadata("persona-eeva")
        assert meta is not None
        assert meta["entity_id"] == "persona-eeva"
        assert meta["body"].strip()
        assert isinstance(meta["aliases"], list)
        assert isinstance(meta["canon"], bool)

    def test_load_missing_entity_returns_none(self):
        assert ll.load_entity_with_metadata("does-not-exist-xyz") is None

    def test_alias_index_self_maps_entity_id(self):
        idx = ll.get_alias_index()
        assert idx.get("persona-eeva") == "persona-eeva"

    def test_static_core_ids(self):
        core = ll.get_static_core_ids("nephilim_eeva")
        assert core == {"persona-eeva", "house-crown", "location-central-nexus"}
        assert ll.get_static_core_ids("gojo") == set()


# ---------------------------------------------------------------------------
# search_lore / index_lore_corpus — fake embedder
# ---------------------------------------------------------------------------
class TestSearchLore:
    def test_search_returns_empty_when_store_none(self):
        rag = _rag_with_fake()
        assert rag.lore_store is None
        assert rag.search_lore("anything") == []

    def test_index_builds_store(self, monkeypatch):
        monkeypatch.setattr(ll, "get_all_entity_ids", lambda: ["a", "b", "c"])
        metas = {
            "a": {"entity_id": "a", "body": "alpha resonance ascension", "entity_type": "concept", "aliases": [], "relationships": [], "canon": True},
            "b": {"entity_id": "b", "body": "bravo bastion order wall", "entity_type": "location", "aliases": [], "relationships": [], "canon": True},
            "c": {"entity_id": "c", "body": "charlie draft entity", "entity_type": "capability", "aliases": [], "relationships": [], "canon": False},
        }
        monkeypatch.setattr(ll, "load_entity_with_metadata", lambda eid: metas.get(eid))
        rag = _rag_with_fake()
        rag.index_lore_corpus()
        assert rag.lore_store is not None
        assert rag.lore_store.index.ntotal == 3

    def test_entity_type_filter(self, monkeypatch):
        monkeypatch.setattr(ll, "get_all_entity_ids", lambda: ["a", "b", "c"])
        metas = {
            "a": {"entity_id": "a", "body": "alpha resonance", "entity_type": "concept", "aliases": [], "relationships": [], "canon": True},
            "b": {"entity_id": "b", "body": "bravo bastion", "entity_type": "location", "aliases": [], "relationships": [], "canon": True},
            "c": {"entity_id": "c", "body": "charlie capability skill", "entity_type": "capability", "aliases": [], "relationships": [], "canon": True},
        }
        monkeypatch.setattr(ll, "load_entity_with_metadata", lambda eid: metas.get(eid))
        rag = _rag_with_fake()
        rag.index_lore_corpus()
        # min_relevance=-1 bypasses the cosine floor so we isolate the type filter
        res = rag.search_lore("charlie capability skill", k=10, min_relevance=-1.0,
                              entity_type_filter="capability")
        assert res, "expected at least one capability result"
        assert all(m["entity_type"] == "capability" for m, _ in res)

    def test_canon_only_filter(self, monkeypatch):
        monkeypatch.setattr(ll, "get_all_entity_ids", lambda: ["a", "c"])
        metas = {
            "a": {"entity_id": "a", "body": "alpha canon", "entity_type": "concept", "aliases": [], "relationships": [], "canon": True},
            "c": {"entity_id": "c", "body": "charlie draft", "entity_type": "entity", "aliases": [], "relationships": [], "canon": False},
        }
        monkeypatch.setattr(ll, "load_entity_with_metadata", lambda eid: metas.get(eid))
        rag = _rag_with_fake()
        rag.index_lore_corpus()
        res = rag.search_lore("alpha charlie", k=10, min_relevance=-1.0, canon_only=True)
        assert all(m["canon"] for m, _ in res)
        assert all(m["entity_id"] != "c" for m, _ in res)

    def test_result_shape_and_k_cap(self, monkeypatch):
        monkeypatch.setattr(ll, "get_all_entity_ids", lambda: ["a", "b", "c"])
        metas = {e: {"entity_id": e, "body": f"{e} body text", "entity_type": "concept",
                     "aliases": [], "relationships": [], "canon": True} for e in ["a", "b", "c"]}
        monkeypatch.setattr(ll, "load_entity_with_metadata", lambda eid: metas.get(eid))
        rag = _rag_with_fake()
        rag.index_lore_corpus()
        res = rag.search_lore("a body text", k=2, min_relevance=-1.0)
        assert len(res) <= 2
        for meta, score in res:
            assert set(meta) >= {"entity_id", "entity_type", "canon", "body"}
            assert -1.0 <= score <= 1.0


@pytest.mark.requires_ollama
class TestSearchLoreLive:
    def test_live_semantic_retrieval(self):
        rag = EpisodicMemoryRAG()
        rag.index_lore_corpus()
        assert rag.lore_store is not None
        res = rag.search_lore("the path of ascension and resonance", k=5, min_relevance=0.4)
        ids = {m["entity_id"] for m, _ in res}
        assert ids & {"concept-resonance", "concept-ascension"}, f"got {ids}"
