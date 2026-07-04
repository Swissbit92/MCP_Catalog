# tests/backend/coordinator/test_search_relevance_service.py
"""Unit tests for SearchRelevanceService and its wiring into ToolCallingService.

Headless: a stub embedder returns controlled vectors so cosine is deterministic;
the flag is toggled via env + settings cache clear.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.coordinator.config import SearchSettings, get_settings
from src.coordinator.models.mcp_models import SearchResult
from src.coordinator.services.search_execution_service import SearchExecutionService
from src.coordinator.services.search_relevance_service import SearchRelevanceService
from src.coordinator.services.tool_calling_service import ToolCallingService


def test_relevance_min_cosine_default_is_the_2026_07_04_tuned_value():
    """Env-independent: assert the model_fields default directly, not a live
    settings instance (which could be overridden by the ambient .env).

    Tuned value from tests/evaluation/tune_relevance_threshold.py against
    relevance_gate_eval_set.json (ADR-007) — 0.28 catches the 2026-07-04
    incident's exact junk shape with zero measured false-abstention on the
    (small, n=8) eval set. Was 0.40 (an untuned, guessed placeholder).
    """
    assert SearchSettings.model_fields["relevance_min_cosine"].default == 0.28


class _StubEmbedder:
    """Maps text -> vector by keyword, so relevant/junk cosine is controllable."""

    def __init__(self, mapping):
        self._mapping = mapping

    def _vec(self, text: str):
        low = text.lower()
        for key, vec in self._mapping.items():
            if key in low:
                return vec
        return [0.0, 0.0, 1.0]  # orthogonal "unknown" direction

    def embed_query(self, text):
        return self._vec(text)

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]


@pytest.fixture(autouse=True)
def _clean_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _results(*titles):
    return [SearchResult(title=t, url="https://x", description="desc") for t in titles]


# ------------------------------------------------------- service-level cosine

def test_on_topic_results_are_relevant():
    emb = _StubEmbedder({"world cup": [1.0, 0.0, 0.0], "switzerland": [1.0, 0.0, 0.0]})
    svc = SearchRelevanceService(embedder=emb)
    results = _results("Switzerland at the World Cup")
    assert svc.is_relevant("Switzerland World Cup", results, min_cosine=0.4) is True


def test_off_topic_results_are_rejected():
    # Query points one way, the junk result points orthogonally.
    emb = _StubEmbedder(
        {"world cup": [1.0, 0.0, 0.0], "search the web in chrome": [0.0, 1.0, 0.0]}
    )
    svc = SearchRelevanceService(embedder=emb)
    junk = _results("Search the web in Chrome - Google Chrome Help")
    assert svc.is_relevant("Switzerland World Cup", junk, min_cosine=0.4) is False


def test_embedder_error_fails_open():
    boom = MagicMock()
    boom.embed_query.side_effect = RuntimeError("ollama down")
    svc = SearchRelevanceService(embedder=boom)
    assert svc.is_relevant("q", _results("anything"), min_cosine=0.9) is True


def test_no_results_returns_none():
    svc = SearchRelevanceService(embedder=_StubEmbedder({}))
    assert svc.max_similarity("q", []) is None


# ------------------------------------------------------- wiring via ToolCalling

def _tool_service(monkeypatch, *, gate_enabled, embedder):
    monkeypatch.setenv("SEARCH_RELEVANCE_GATE_ENABLED", "true" if gate_enabled else "false")
    monkeypatch.setenv("SEARCH_RELEVANCE_MIN_COSINE", "0.4")
    # Resolution off so the query stays the raw latest turn for this test.
    monkeypatch.setenv("SEARCH_QUERY_RESOLUTION_ENABLED", "false")
    get_settings.cache_clear()

    mock_mcp = MagicMock()
    mock_mcp.search_web.return_value = [
        SearchResult(
            title="Search the web in Chrome - Google Chrome Help",
            url="https://support.google.com",
            description="How to search the web.",
        )
    ]
    search_executor = SearchExecutionService(mcp_client=mock_mcp)

    mock_llm = MagicMock()
    mock_llm.complete.return_value = "synthesized answer"

    service = ToolCallingService(
        llm_service=mock_llm,
        search_executor=search_executor,
        relevance_service=SearchRelevanceService(embedder=embedder),
    )
    tools = [{"type": "function", "function": {"name": "brave_web_search"}}]
    return service, mock_llm, tools


def test_gate_on_junk_results_triggers_abstention(monkeypatch):
    """Junk-but-non-empty results -> honest 'I don't know', no synthesis."""
    emb = _StubEmbedder(
        {"world cup": [1.0, 0.0, 0.0], "search the web in chrome": [0.0, 1.0, 0.0]}
    )
    service, mock_llm, tools = _tool_service(monkeypatch, gate_enabled=True, embedder=emb)

    response, tool_call, results = service.complete_with_tools(
        persona_system="You are E.E.V.A.",
        user_prompt="User: search the web for the world cup",
        tools=tools,
    )

    assert results is None
    assert tool_call is None
    assert "didn't return any results" in response or "don't know" in response.lower()
    mock_llm.complete.assert_not_called()  # never synthesized over junk


def test_gate_off_junk_results_pass_through(monkeypatch):
    """Default OFF: junk results still reach synthesis (legacy behavior)."""
    emb = _StubEmbedder(
        {"world cup": [1.0, 0.0, 0.0], "search the web in chrome": [0.0, 1.0, 0.0]}
    )
    service, mock_llm, tools = _tool_service(monkeypatch, gate_enabled=False, embedder=emb)

    response, tool_call, results = service.complete_with_tools(
        persona_system="You are E.E.V.A.",
        user_prompt="User: search the web for the world cup",
        tools=tools,
    )

    assert results is not None  # junk was NOT gated
    mock_llm.complete.assert_called()  # synthesis ran
