# tests/backend/coordinator/test_memory_rag_overflow.py
"""Headless regression tests for the RAG embedding-overflow guard.

Uses a fake embeddings object (no Ollama) that RECORDS every text handed to the
embedder, so we can assert the overflow guard chunks/truncates oversized input
before it would have tripped Ollama's HTTP 500. Runs without Ollama/network.
"""

from __future__ import annotations

from typing import List

import pytest

from langchain_core.embeddings import Embeddings

from src.coordinator.memory_rag import EpisodicMemoryRAG
from src.coordinator.memory_text_utils import estimate_tokens, safe_token_budget


class _RecordingEmbeddings(Embeddings):
    """Fake LangChain embeddings that records inputs and returns fixed vectors.

    Subclasses ``Embeddings`` so FAISS recognises it and routes queries through
    ``embed_query`` (rather than treating it as a bare callable).
    """

    def __init__(self) -> None:
        self.documents_seen: List[str] = []
        self.queries_seen: List[str] = []

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        self.documents_seen.extend(texts)
        return [[float(i % 3), 0.1, 0.2, 0.3] for i, _ in enumerate(texts)]

    def embed_query(self, text: str) -> List[float]:
        self.queries_seen.append(text)
        return [0.0, 0.1, 0.2, 0.3]


@pytest.fixture
def rag() -> EpisodicMemoryRAG:
    # Construction is lazy (no Ollama connection); swap in the recording fake.
    instance = EpisodicMemoryRAG(embedding_model="bge-m3:latest")
    instance.embeddings = _RecordingEmbeddings()
    return instance


def _huge_message(rag: EpisodicMemoryRAG, role: str = "assistant") -> dict:
    budget = safe_token_budget(rag._embed_max_tokens)
    content = " ".join(f"token{i}" for i in range(budget * 2))  # ~2x over budget
    return {"id": "m1", "role": role, "content": content, "timestamp": "t0"}


def test_index_session_chunks_oversized_message(rag):
    budget = safe_token_budget(rag._embed_max_tokens)
    rag.index_session("s1", [_huge_message(rag)])

    fake = rag.embeddings
    assert len(fake.documents_seen) > 1, "oversized message should be split into chunks"
    for text in fake.documents_seen:
        assert estimate_tokens(text) <= budget, "no embedded chunk may exceed the budget"


def test_index_session_skips_empty_messages(rag):
    msgs = [
        {"id": "a", "role": "user", "content": "   ", "timestamp": "t0"},
        {"id": "b", "role": "assistant", "content": "actual reply", "timestamp": "t1"},
    ]
    rag.index_session("s2", msgs)
    fake = rag.embeddings
    # Only the non-empty message is embedded (note the "role: content" format).
    assert any("actual reply" in t for t in fake.documents_seen)
    assert all(t.strip() for t in fake.documents_seen)


def test_update_session_chunks_oversized_message(rag):
    budget = safe_token_budget(rag._embed_max_tokens)
    # Seed an initial small index, then add an oversized message incrementally.
    rag.index_session("s3", [{"id": "m0", "role": "user", "content": "hi", "timestamp": "t0"}])
    rag.embeddings.documents_seen.clear()

    huge = _huge_message(rag)
    rag.update_session("s3", [huge], full_history=[
        {"id": "m0", "role": "user", "content": "hi", "timestamp": "t0"}, huge,
    ])

    for text in rag.embeddings.documents_seen:
        assert estimate_tokens(text) <= budget


def test_search_memory_truncates_long_query(rag):
    budget = safe_token_budget(rag._embed_max_tokens)
    rag.index_session("s4", [{"id": "m0", "role": "user", "content": "hello world", "timestamp": "t0"}])

    long_query = " ".join(f"q{i}" for i in range(budget * 3))
    rag.search_memory("s4", long_query, k=3)

    assert rag.embeddings.queries_seen, "query should have been embedded"
    for q in rag.embeddings.queries_seen:
        assert estimate_tokens(q) <= budget, "long query must be truncated before embedding"
