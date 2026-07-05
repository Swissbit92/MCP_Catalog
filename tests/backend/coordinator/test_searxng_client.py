# tests/backend/coordinator/test_searxng_client.py
"""Unit tests for the SearXNG client + backend chain (ADR-009 Phase W)."""
from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest

from src.coordinator.config import get_settings
from src.coordinator.models.mcp_models import (
    MCPConnectionError,
    SearchResult,
)
from src.coordinator.searxng_client import SearxngClient, safesearch_to_int
from src.coordinator.services.search_execution_service import SearchExecutionService
from src.coordinator.tool_definitions import ToolCall


@pytest.fixture(autouse=True)
def _clean_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _fake_http(payload: dict):
    """Return a context-manager mock mimicking urlopen()."""
    body = json.dumps(payload).encode("utf-8")
    cm = MagicMock()
    cm.__enter__.return_value = io.BytesIO(body)
    cm.__exit__.return_value = False
    return cm


# ---------------------------------------------------------- safesearch map

def test_safesearch_map():
    assert safesearch_to_int("off") == 0
    assert safesearch_to_int("moderate") == 1
    assert safesearch_to_int("strict") == 2
    assert safesearch_to_int(None) == 0
    assert safesearch_to_int("bogus") == 0


# ---------------------------------------------------------- SearxngClient

class TestSearxngClient:
    def test_parses_results(self):
        payload = {"results": [
            {"url": "https://a.com", "title": "A", "content": "snippet a",
             "publishedDate": "2026-07-01"},
            {"url": "https://b.com", "title": "B", "content": "snippet b"},
        ]}
        with patch("urllib.request.urlopen", return_value=_fake_http(payload)):
            out = SearxngClient("http://sx:8888").search("hello")
        assert [r.url for r in out] == ["https://a.com", "https://b.com"]
        assert out[0].description == "snippet a" and out[0].age == "2026-07-01"
        assert isinstance(out[0], SearchResult)

    def test_respects_count_limit(self):
        payload = {"results": [{"url": f"https://{i}.com", "title": str(i),
                                "content": ""} for i in range(10)]}
        with patch("urllib.request.urlopen", return_value=_fake_http(payload)):
            out = SearxngClient("http://sx:8888", max_results=3).search("hi")
        assert len(out) == 3

    def test_skips_result_without_url(self):
        payload = {"results": [{"title": "no url", "content": "x"},
                               {"url": "https://ok.com", "title": "ok"}]}
        with patch("urllib.request.urlopen", return_value=_fake_http(payload)):
            out = SearxngClient("http://sx:8888").search("hi")
        assert [r.url for r in out] == ["https://ok.com"]

    def test_empty_results(self):
        with patch("urllib.request.urlopen", return_value=_fake_http({"results": []})):
            assert SearxngClient("http://sx:8888").search("hi") == []

    def test_category_and_safesearch_in_query(self):
        captured = {}

        def _fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            return _fake_http({"results": []})

        with patch("urllib.request.urlopen", side_effect=_fake_urlopen):
            SearxngClient("http://sx:8888").search(
                "porn", category="videos", safesearch="off"
            )
        assert "categories=videos" in captured["url"]
        assert "safesearch=0" in captured["url"]
        assert "format=json" in captured["url"]

    def test_invalid_category_falls_back_to_general(self):
        captured = {}

        def _fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            return _fake_http({"results": []})

        with patch("urllib.request.urlopen", side_effect=_fake_urlopen):
            SearxngClient("http://sx:8888").search("q", category="bogus")
        assert "categories=general" in captured["url"]

    def test_connection_error_raises(self):
        with patch("urllib.request.urlopen", side_effect=OSError("refused")):
            with pytest.raises(MCPConnectionError):
                SearxngClient("http://sx:8888").search("hi")

    def test_empty_query_rejected(self):
        with pytest.raises(ValueError):
            SearxngClient("http://sx:8888").search("   ")


# ---------------------------------------------- backend chain in the service

class TestBackendChain:
    def _svc(self):
        brave = MagicMock()
        brave.search_web.return_value = [SearchResult("BraveTitle", "https://brave", "d")]
        return SearchExecutionService(mcp_client=brave), brave

    def test_auto_no_searxng_url_uses_brave(self, monkeypatch):
        monkeypatch.setenv("WEB_SEARCH_BACKEND", "auto")
        monkeypatch.setenv("SEARXNG_BASE_URL", "")
        get_settings.cache_clear()
        svc, brave = self._svc()
        out = svc.execute_search(ToolCall("brave_web_search", {"query": "hi"}))
        assert out[0].title == "BraveTitle"
        brave.search_web.assert_called_once()

    def test_searxng_works_with_no_brave_client(self, monkeypatch):
        # ADR-008 live-smoke bug fix: a SearXNG-primary deployment must work even
        # with NO Brave client (the old `if not self.mcp_client: return None`
        # guard bailed before SearXNG ran).
        monkeypatch.setenv("WEB_SEARCH_BACKEND", "auto")
        monkeypatch.setenv("SEARXNG_BASE_URL", "http://sx:8888")
        get_settings.cache_clear()
        svc = SearchExecutionService(mcp_client=None)  # no brave
        payload = {"results": [{"url": "https://sx", "title": "SxOnly", "content": ""}]}
        with patch("urllib.request.urlopen", return_value=_fake_http(payload)):
            out = svc.execute_search(ToolCall("brave_web_search", {"query": "hi"}))
        assert out[0].title == "SxOnly"

    def test_no_client_no_searxng_returns_none(self, monkeypatch):
        monkeypatch.setenv("WEB_SEARCH_BACKEND", "auto")
        monkeypatch.setenv("SEARXNG_BASE_URL", "")
        get_settings.cache_clear()
        svc = SearchExecutionService(mcp_client=None)
        assert svc.execute_search(ToolCall("brave_web_search", {"query": "hi"})) is None

    def test_auto_with_searxng_url_uses_searxng(self, monkeypatch):
        monkeypatch.setenv("WEB_SEARCH_BACKEND", "auto")
        monkeypatch.setenv("SEARXNG_BASE_URL", "http://sx:8888")
        get_settings.cache_clear()
        svc, brave = self._svc()
        payload = {"results": [{"url": "https://sx-hit", "title": "SxTitle", "content": ""}]}
        with patch("urllib.request.urlopen", return_value=_fake_http(payload)):
            out = svc.execute_search(ToolCall("brave_web_search", {"query": "hi"}))
        assert out[0].title == "SxTitle"
        brave.search_web.assert_not_called()

    def test_auto_searxng_error_falls_back_to_brave(self, monkeypatch):
        monkeypatch.setenv("WEB_SEARCH_BACKEND", "auto")
        monkeypatch.setenv("SEARXNG_BASE_URL", "http://sx:8888")
        get_settings.cache_clear()
        svc, brave = self._svc()
        with patch("urllib.request.urlopen", side_effect=OSError("down")):
            out = svc.execute_search(ToolCall("brave_web_search", {"query": "hi"}))
        assert out[0].title == "BraveTitle"
        brave.search_web.assert_called_once()

    def test_searxng_only_error_does_not_hit_brave(self, monkeypatch):
        monkeypatch.setenv("WEB_SEARCH_BACKEND", "searxng")
        monkeypatch.setenv("SEARXNG_BASE_URL", "http://sx:8888")
        get_settings.cache_clear()
        svc, brave = self._svc()
        with patch("urllib.request.urlopen", side_effect=OSError("down")):
            out = svc.execute_search(ToolCall("brave_web_search", {"query": "hi"}))
        assert out == []
        brave.search_web.assert_not_called()

    def test_brave_backend_ignores_searxng_url(self, monkeypatch):
        monkeypatch.setenv("WEB_SEARCH_BACKEND", "brave")
        monkeypatch.setenv("SEARXNG_BASE_URL", "http://sx:8888")
        get_settings.cache_clear()
        svc, brave = self._svc()
        # urlopen must never be called; if it were, this would error loudly.
        with patch("urllib.request.urlopen", side_effect=AssertionError("searxng hit")):
            out = svc.execute_search(ToolCall("brave_web_search", {"query": "hi"}))
        assert out[0].title == "BraveTitle"

    def test_per_call_safesearch_flows_to_searxng(self, monkeypatch):
        monkeypatch.setenv("WEB_SEARCH_BACKEND", "searxng")
        monkeypatch.setenv("SEARXNG_BASE_URL", "http://sx:8888")
        get_settings.cache_clear()
        svc, _ = self._svc()
        captured = {}

        def _fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            return _fake_http({"results": []})

        with patch("urllib.request.urlopen", side_effect=_fake_urlopen):
            svc.execute_search(ToolCall(
                "brave_web_search",
                {"query": "hi", "safesearch": "strict", "category": "images"},
            ))
        assert "safesearch=2" in captured["url"] and "categories=images" in captured["url"]
