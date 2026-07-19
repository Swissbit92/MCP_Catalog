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


class TestImageJunkFilterOnBoundExecutor:
    """The denylist is wired into the bound image_search path (always-on)."""

    def _run_image_search(self, results, persona_card=None):
        from src.coordinator.models.mcp_models import SearchResult  # noqa: F401

        class FakeSvc:
            def __init__(self, mcp_client=None):
                pass
            def execute_search(self, tool_call):
                return results

        persona_card = persona_card or {"key": "gwen", "nsfw": True}
        with patch("src.coordinator.services.search_execution_service.SearchExecutionService", FakeSvc), \
             patch("src.coordinator.startup.get_brave_client", return_value=MagicMock()):
            return registry.get("image_search").executor({"query": "cat"}, persona_card)

    def test_icon_svg_junk_stripped_from_image_results(self):
        from src.coordinator.models.mcp_models import SearchResult
        results = [
            SearchResult(title="cat photo", url="https://photos.com/cat.jpg", description="a cat"),
            SearchResult(title="hadoop icon", url="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/hadoop/hadoop-original.svg", description=""),
            SearchResult(title="arrow", url="https://cdn.jsdelivr.net/npm/lucide-static/icons/a-arrow-up.svg", description=""),
        ]
        out = self._run_image_search(results)
        urls = [r.url for r in out]
        assert urls == ["https://photos.com/cat.jpg"]

    def test_all_junk_falls_back_to_original(self):
        from src.coordinator.models.mcp_models import SearchResult
        results = [
            SearchResult(title="a", url="https://cdn.jsdelivr.net/npm/lucide-static/icons/x.svg", description=""),
            SearchResult(title="b", url="https://www.svgrepo.com/show/1/y.svg", description=""),
        ]
        out = self._run_image_search(results)
        assert len(out) == 2  # never-empty fallback

    def test_web_search_category_not_filtered(self):
        # An icon-CDN URL is NOT junk for a general web search.
        from src.coordinator.models.mcp_models import SearchResult

        class FakeSvc:
            def __init__(self, mcp_client=None):
                pass
            def execute_search(self, tool_call):
                return [SearchResult(title="devicon docs",
                                     url="https://cdn.jsdelivr.net/npm/devicon/readme.md",
                                     description="")]
        with patch("src.coordinator.services.search_execution_service.SearchExecutionService", FakeSvc), \
             patch("src.coordinator.startup.get_brave_client", return_value=MagicMock()):
            out = registry.get("web_search").executor({"query": "devicon"}, {"key": "eeva", "nsfw": False})
        assert len(out) == 1


class TestRelevanceFilterGatingOnBoundExecutor:
    """The relevance filter is flag-gated and default-OFF on the bound path."""

    def _run(self, results, gate_enabled, stub_embedder=None, min_cosine=0.5):
        import types
        from src.coordinator.tools import executor_bindings as eb
        from src.coordinator.services.search_relevance_service import SearchRelevanceService

        class FakeSvc:
            def __init__(self, mcp_client=None):
                pass
            def execute_search(self, tool_call):
                return results

        fake_settings = types.SimpleNamespace(
            web_search=types.SimpleNamespace(safesearch_default="off"),
            search=types.SimpleNamespace(
                relevance_gate_enabled=gate_enabled,
                relevance_min_cosine=min_cosine,
            ),
        )
        # Inject a stub relevance service so no real embedder is built.
        prev = eb._relevance_service
        if stub_embedder is not None:
            eb._relevance_service = SearchRelevanceService(embedder=stub_embedder)
        try:
            with patch("src.coordinator.services.search_execution_service.SearchExecutionService", FakeSvc), \
                 patch("src.coordinator.startup.get_brave_client", return_value=MagicMock()), \
                 patch("src.coordinator.config.get_settings", return_value=fake_settings):
                return registry.get("image_search").executor({"query": "cat"}, {"key": "gwen", "nsfw": True})
        finally:
            eb._relevance_service = prev

    def test_gate_off_passes_through(self):
        from src.coordinator.models.mcp_models import SearchResult
        results = [SearchResult(title="dog", url="https://a/dog.jpg", description="")]
        out = self._run(results, gate_enabled=False)
        assert len(out) == 1  # off -> no relevance filtering

    def test_gate_on_drops_off_topic(self):
        from src.coordinator.models.mcp_models import SearchResult

        class Stub:
            def _v(self, t):
                return [1.0, 0.0] if "cat" in t.lower() else [0.0, 1.0]
            def embed_query(self, t):
                return self._v(t)
            def embed_documents(self, ts):
                return [self._v(t) for t in ts]

        results = [
            SearchResult(title="cat photo", url="https://a/cat.jpg", description=""),
            SearchResult(title="mercury artwork", url="https://b/art.jpg", description=""),
        ]
        out = self._run(results, gate_enabled=True, stub_embedder=Stub(), min_cosine=0.5)
        assert [r.url for r in out] == ["https://a/cat.jpg"]


class TestFetchUrlExecutor:
    def test_fetch_url_routes_to_service(self):
        with patch("src.coordinator.services.web_fetch_service.fetch_url",
                   return_value="clean text") as m:
            out = registry.get("fetch_url").executor(
                {"url": "https://example.com", "mode": "text"}, {"key": "gwen"})
        assert out == "clean text"
        m.assert_called_once_with("https://example.com", "text")
