# tests/backend/coordinator/test_search_execution_service.py
"""Unit tests for SearchExecutionService — all branches."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.coordinator.config import get_settings
from src.coordinator.services.search_execution_service import (
    SearchExecutionService,
    infer_freshness,
)
from src.coordinator.tool_definitions import ToolCall


def _tool_call(query: str = "bitcoin price") -> ToolCall:
    return ToolCall(name="brave_web_search", arguments={"query": query})


def _clear_locale_env(monkeypatch):
    """Hermetic defaults: no locale leaking in from process env OR a dev .env.

    setenv (not delenv) because pydantic-settings gives process env precedence
    over the .env file — an empty string wins over a .env BRAVE_COUNTRY=CH.
    """
    monkeypatch.setenv("BRAVE_COUNTRY", "")
    monkeypatch.setenv("BRAVE_SEARCH_LANG", "")
    # ADR-009 Phase W: force the Brave backend path (no SearXNG) + a known
    # safesearch default, so these Brave-focused tests stay hermetic vs a dev
    # .env that might configure SearXNG.
    monkeypatch.setenv("WEB_SEARCH_BACKEND", "brave")
    monkeypatch.setenv("SEARXNG_BASE_URL", "")
    monkeypatch.setenv("WEB_SAFESEARCH_DEFAULT", "off")
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _clean_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestSearchExecutionServiceInit:
    def test_no_client_by_default(self):
        svc = SearchExecutionService()
        assert svc.mcp_client is None

    def test_client_stored(self):
        client = MagicMock()
        svc = SearchExecutionService(mcp_client=client)
        assert svc.mcp_client is client


class TestExecuteSearch:
    """Tests for SearchExecutionService.execute_search."""

    # ------------------------------------------------------------------
    # No MCP client → returns None immediately
    # ------------------------------------------------------------------

    def test_returns_none_when_no_client(self):
        svc = SearchExecutionService(mcp_client=None)
        result = svc.execute_search(_tool_call())
        assert result is None

    # ------------------------------------------------------------------
    # Empty query → returns None
    # ------------------------------------------------------------------

    def test_empty_query_returns_none(self):
        client = MagicMock()
        svc = SearchExecutionService(mcp_client=client)
        tc = ToolCall(name="brave_web_search", arguments={"query": ""})
        result = svc.execute_search(tc)
        assert result is None
        client.search_web.assert_not_called()

    def test_missing_query_key_returns_none(self):
        """arguments dict has no 'query' key → empty string → None."""
        client = MagicMock()
        svc = SearchExecutionService(mcp_client=client)
        tc = ToolCall(name="brave_web_search", arguments={})
        result = svc.execute_search(tc)
        assert result is None

    # ------------------------------------------------------------------
    # Successful search → returns results
    # ------------------------------------------------------------------

    def test_successful_search_returns_results(self, monkeypatch):
        _clear_locale_env(monkeypatch)
        fake_results = [{"title": "BTC news", "url": "https://example.com"}]
        client = MagicMock()
        client.search_web.return_value = fake_results
        svc = SearchExecutionService(mcp_client=client)
        result = svc.execute_search(_tool_call("bitcoin"))
        assert result == fake_results
        client.search_web.assert_called_once_with(
            "bitcoin", country=None, search_lang=None, freshness=None,
            safesearch="off",
        )

    def test_empty_results_list_returned(self):
        client = MagicMock()
        client.search_web.return_value = []
        svc = SearchExecutionService(mcp_client=client)
        result = svc.execute_search(_tool_call("obscure query"))
        assert result == []

    # ------------------------------------------------------------------
    # Exception handling → returns None
    # ------------------------------------------------------------------

    def test_search_exception_returns_none(self):
        client = MagicMock()
        client.search_web.side_effect = RuntimeError("connection refused")
        svc = SearchExecutionService(mcp_client=client)
        result = svc.execute_search(_tool_call("bitcoin"))
        assert result is None

    def test_search_timeout_returns_none(self):
        client = MagicMock()
        client.search_web.side_effect = TimeoutError("timed out")
        svc = SearchExecutionService(mcp_client=client)
        result = svc.execute_search(_tool_call("query"))
        assert result is None


class TestInferFreshness:
    """Temporal-cue → Brave freshness filter mapping (2026-07-05 incident)."""

    @pytest.mark.parametrize("query", [
        "latest news in switzerland today",
        "what is happening right now",
        "breaking developments in the market",
        "top stories tonight",
    ])
    def test_day_cues(self, query):
        assert infer_freshness(query) == "pd"

    @pytest.mark.parametrize("query", [
        "weather tomorrow in Brugg Switzerland",
        "weather forecast Zurich",
        "latest ethereum upgrades",
        "recent crypto regulation",
        "switzerland headlines",
    ])
    def test_week_cues(self, query):
        assert infer_freshness(query) == "pw"

    @pytest.mark.parametrize("query", [
        "who is the president of switzerland",
        "bitcoin whitepaper explained",
        "how does proof of stake work",
        "",
    ])
    def test_no_cue_no_filter(self, query):
        assert infer_freshness(query) is None

    def test_day_cue_wins_over_week_cue(self):
        # "news" (week) + "today" (day) → the tighter window.
        assert infer_freshness("what is the latest news today") == "pd"

    def test_no_substring_false_positives(self):
        # "nowhere" must not match "now"; "renew" must not match "new(s)".
        assert infer_freshness("nowhere to renew a passport") is None


class TestLocaleParams:
    """BRAVE_COUNTRY / BRAVE_SEARCH_LANG flow through to search_web."""

    def test_country_and_lang_passed_when_configured(self, monkeypatch):
        _clear_locale_env(monkeypatch)  # force Brave backend, safesearch=off
        monkeypatch.setenv("BRAVE_COUNTRY", "CH")
        monkeypatch.setenv("BRAVE_SEARCH_LANG", "en")
        get_settings.cache_clear()
        client = MagicMock()
        client.search_web.return_value = []
        svc = SearchExecutionService(mcp_client=client)
        svc.execute_search(_tool_call("weather tomorrow in Brugg"))
        client.search_web.assert_called_once_with(
            "weather tomorrow in Brugg",
            country="CH",
            search_lang="en",
            freshness="pw",
            safesearch="off",
        )

    def test_country_normalized_to_upper(self, monkeypatch):
        monkeypatch.setenv("BRAVE_COUNTRY", "ch")
        monkeypatch.setenv("BRAVE_SEARCH_LANG", "")
        get_settings.cache_clear()
        client = MagicMock()
        client.search_web.return_value = []
        svc = SearchExecutionService(mcp_client=client)
        svc.execute_search(_tool_call("bitcoin"))
        _, kwargs = client.search_web.call_args
        assert kwargs["country"] == "CH"

    def test_invalid_country_dropped(self, monkeypatch):
        monkeypatch.setenv("BRAVE_COUNTRY", "Switzerland")
        monkeypatch.setenv("BRAVE_SEARCH_LANG", "")
        get_settings.cache_clear()
        client = MagicMock()
        client.search_web.return_value = []
        svc = SearchExecutionService(mcp_client=client)
        svc.execute_search(_tool_call("bitcoin"))
        _, kwargs = client.search_web.call_args
        assert kwargs["country"] is None
