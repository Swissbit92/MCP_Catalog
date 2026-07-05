# tests/backend/coordinator/test_executor_bindings.py
"""ADR-008 TB2: web-executor binding + the safesearch clamp on the BOUND path.

The clamp being defined (test_web_toolset) is not enough — the QA finding was
that it's wired NOWHERE. These tests drive the actual bound registry executor
and assert the per-persona nsfw clamp reaches the search service.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.coordinator.tools import registrations  # noqa: F401 - register specs
from src.coordinator.tools.registry import registry
from src.coordinator.tools.executor_bindings import bind_web_executors


@pytest.fixture(autouse=True)
def _bound():
    # Re-bind before each test (idempotent) so registry.get(name).executor is set.
    bind_web_executors()
    yield


class TestBinding:
    def test_all_web_search_tools_bound(self):
        for name in ("web_search", "image_search", "video_search", "news_search", "fetch_url"):
            assert registry.get(name).executor is not None, f"{name} unbound"

    def test_returns_bound_names(self):
        bound = bind_web_executors()
        assert {"web_search", "image_search", "video_search", "news_search", "fetch_url"} <= set(bound)

    def test_wallet_tools_not_bound_here(self):
        # Wallet stays on the existing HITL/handle_wallet_query flow.
        assert registry.get("wallet_get_balances").executor is None


class TestSafesearchClampOnBoundExecutor:
    """The load-bearing TB2 test: clamp reaches the service via the bound path."""

    def _run(self, tool_name, persona_card, requested_safesearch=None):
        captured = {}

        class FakeSvc:
            def __init__(self, mcp_client=None):
                pass
            def execute_search(self, tool_call):
                captured["name"] = tool_call.name
                captured["args"] = dict(tool_call.arguments)
                return ["result"]

        args = {"query": "test"}
        if requested_safesearch is not None:
            args["safesearch"] = requested_safesearch
        with patch("src.coordinator.services.search_execution_service.SearchExecutionService", FakeSvc), \
             patch("src.coordinator.startup.get_brave_client", return_value=MagicMock()), \
             patch("src.coordinator.config.get_settings") as gs:
            gs.return_value.web_search.safesearch_default = "off"
            registry.get(tool_name).executor(args, persona_card)
        return captured

    def test_non_nsfw_persona_clamped_to_moderate(self):
        cap = self._run("web_search", {"key": "aegis", "nsfw": False}, requested_safesearch="off")
        assert cap["args"]["safesearch"] == "moderate"  # floor enforced

    def test_nsfw_persona_allows_off(self):
        cap = self._run("web_search", {"key": "gwen", "nsfw": True}, requested_safesearch="off")
        assert cap["args"]["safesearch"] == "off"

    def test_non_nsfw_default_off_becomes_moderate(self):
        # No per-call safesearch -> global default 'off' -> clamped up for non-nsfw.
        cap = self._run("web_search", {"key": "eeva", "nsfw": False})
        assert cap["args"]["safesearch"] == "moderate"

    def test_clamp_only_tightens(self):
        cap = self._run("web_search", {"key": "gwen", "nsfw": True}, requested_safesearch="strict")
        assert cap["args"]["safesearch"] == "strict"

    def test_image_search_forces_category(self):
        cap = self._run("image_search", {"key": "gwen", "nsfw": True})
        assert cap["args"]["category"] == "images"
        assert cap["name"] == "image_search"

    def test_video_search_forces_category(self):
        cap = self._run("video_search", {"key": "gwen", "nsfw": True})
        assert cap["args"]["category"] == "videos"


class TestFetchUrlExecutor:
    def test_fetch_url_routes_to_service(self):
        with patch("src.coordinator.services.web_fetch_service.fetch_url",
                   return_value="clean text") as m:
            out = registry.get("fetch_url").executor(
                {"url": "https://example.com", "mode": "text"}, {"key": "gwen"})
        assert out == "clean text"
        m.assert_called_once_with("https://example.com", "text")
