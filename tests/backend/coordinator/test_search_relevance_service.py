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
    relevance_gate_eval_set.json (ADR-007), extended same-day to n=25 with 17
    real Brave query/result pairs — 0.36 catches 100% of junk with only a 5%
    false-abstention rate (the one false-abstention being the original n=8
    pass's own synthetic adversarial sample, not real data). Was 0.28 (n=8,
    mostly hand-written), before that 0.40 (untuned placeholder).
    """
    assert SearchSettings.model_fields["relevance_min_cosine"].default == 0.36


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


# ------------------------------------------------ per-result filter_relevant
# (image-search shape: keep on-topic hits, drop keyword-collision outliers)

def test_filter_relevant_drops_only_off_topic():
    emb = _StubEmbedder({
        "deepthroat": [1.0, 0.0, 0.0],
        "bbc": [1.0, 0.0, 0.0],
        "mercury": [0.0, 1.0, 0.0],   # the artwork outlier, orthogonal
    })
    svc = SearchRelevanceService(embedder=emb)
    results = [
        SearchResult(title="BBC Deepthroat", url="https://a", description=""),
        SearchResult(title="Deepthroat MILFs", url="https://b", description=""),
        SearchResult(title="Mercury with the Head of Argus", url="https://c", description=""),
    ]
    kept = svc.filter_relevant("deepthroat bbc", results, min_cosine=0.5)
    urls = [r.url for r in kept]
    assert "https://c" not in urls          # the artwork is dropped
    assert urls == ["https://a", "https://b"]


def test_filter_relevant_keeps_all_when_all_on_topic():
    emb = _StubEmbedder({"cat": [1.0, 0.0, 0.0]})
    svc = SearchRelevanceService(embedder=emb)
    results = [SearchResult(title="a cat", url="https://a", description=""),
               SearchResult(title="cat photo", url="https://b", description="")]
    kept = svc.filter_relevant("cat", results, min_cosine=0.5)
    assert len(kept) == 2


def test_filter_relevant_never_empties_uniform_low_set():
    # Every result is off-topic -> degrade to original rather than abstain here.
    emb = _StubEmbedder({"cat": [1.0, 0.0, 0.0]})  # results map to unknown dir
    svc = SearchRelevanceService(embedder=emb)
    results = [SearchResult(title="dog", url="https://a", description=""),
               SearchResult(title="fish", url="https://b", description="")]
    kept = svc.filter_relevant("cat", results, min_cosine=0.9)
    assert kept is results  # original returned unchanged


def test_filter_relevant_empty_and_no_query():
    svc = SearchRelevanceService(embedder=_StubEmbedder({}))
    assert svc.filter_relevant("q", [], 0.5) == []
    r = [SearchResult(title="x", url="https://a", description="")]
    assert svc.filter_relevant("", r, 0.5) is r


def test_filter_relevant_fails_open_on_embedder_error():
    boom = MagicMock()
    boom.embed_query.side_effect = RuntimeError("ollama down")
    svc = SearchRelevanceService(embedder=boom)
    r = [SearchResult(title="x", url="https://a", description="")]
    assert svc.filter_relevant("q", r, 0.9) is r


def test_filter_relevant_keeps_unscoreable_results():
    # A result with no title/description can't be embedded -> never dropped.
    emb = _StubEmbedder({"cat": [1.0, 0.0, 0.0]})
    svc = SearchRelevanceService(embedder=emb)
    results = [SearchResult(title="", url="https://a", description=""),
               SearchResult(title="cat", url="https://b", description="")]
    kept = svc.filter_relevant("cat", results, min_cosine=0.5)
    assert "https://a" in [r.url for r in kept]
