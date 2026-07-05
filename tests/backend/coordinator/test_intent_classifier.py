# tests/backend/coordinator/test_intent_classifier.py
"""Unit tests for classify_query_intent — semantic-router intent classification.

ROUTING_SEMANTIC_PRIMARY was retired 2026-07-04 (audit cleanup step 5): the
bge-m3 semantic path is now the only classifier. All tests are headless — they
mock get_settings (routing thresholds) and route_by_embedding (the embedder), so
no live Ollama is needed.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import src.coordinator.tools.intent_classifier as ic  # noqa: F401
from src.coordinator.tools.intent_classifier import QueryIntent, classify_query_intent

EEVA_ACCESS = ["brave_search", "solana_wallet"]
BRAVE_ACCESS = ["brave_search"]


def _routing(threshold=0.61, margin=0.0):
    return SimpleNamespace(
        semantic_threshold=threshold,
        semantic_margin=margin,
    )


def _patch_settings(monkeypatch, routing):
    """Patch the lazily-imported get_settings so classify_query_intent sees our thresholds."""
    settings = SimpleNamespace(routing=routing)
    monkeypatch.setattr("src.coordinator.config.get_settings", lambda: settings, raising=False)


def _patch_semantic(monkeypatch, return_value):
    mock = MagicMock(return_value=return_value)
    monkeypatch.setattr(
        "src.coordinator.tools.semantic_router.route_by_embedding", mock, raising=False
    )
    return mock


class TestMediaSearchFastPath:
    """2026-07-05: colloquial media-find routes to web via the precise
    verb+media-noun keyword rule (before the semantic router). The semantic
    mock returns None here, so a web result proves the FAST-PATH caught it —
    and RP 'find me' must NOT match (no media noun)."""

    MEDIA = ["find me some images", "find me a video of a concert",
             "show me pictures of paris", "get me some pics", "pull up a video",
             "find me images of a redhead"]
    RP_NEG = ["come find me when you're ready", "I hope you find me pretty",
              "you'll find a better view in person", "did you find everything okay"]

    def test_media_find_routes_web(self, monkeypatch):
        _patch_settings(monkeypatch, _routing())
        _patch_semantic(monkeypatch, None)  # semantic says nothing
        for q in self.MEDIA:
            assert classify_query_intent(q, "legendary", mcp_access=BRAVE_ACCESS) \
                == QueryIntent.NEEDS_WEB_SEARCH, q

    def test_rp_find_me_does_not_route_web(self, monkeypatch):
        _patch_settings(monkeypatch, _routing())
        _patch_semantic(monkeypatch, None)
        for q in self.RP_NEG:
            assert classify_query_intent(q, "legendary", mcp_access=BRAVE_ACCESS) \
                == QueryIntent.NEEDS_NEITHER, q

    def test_media_rule_gated_on_brave_access(self, monkeypatch):
        # No brave access -> the media rule must not fire (nothing to route to).
        _patch_settings(monkeypatch, _routing())
        _patch_semantic(monkeypatch, None)
        assert classify_query_intent("find me some images", "common", mcp_access=[]) \
            == QueryIntent.NEEDS_NEITHER


class TestClassifyQueryIntent:
    """Fast-path → semantic router → NEEDS_NEITHER."""

    def test_semantic_wallet_routes_wallet(self, monkeypatch):
        _patch_settings(monkeypatch, _routing())
        _patch_semantic(monkeypatch, "wallet")
        result = classify_query_intent("thinking of moving funds around", "legendary", mcp_access=EEVA_ACCESS)
        assert result == QueryIntent.NEEDS_WALLET

    def test_semantic_wallet_blocked_by_negation(self, monkeypatch):
        _patch_settings(monkeypatch, _routing())
        _patch_semantic(monkeypatch, "wallet")
        result = classify_query_intent("I'm not going to swap anything", "legendary", mcp_access=EEVA_ACCESS)
        assert result != QueryIntent.NEEDS_WALLET

    def test_semantic_web_routes_web(self, monkeypatch):
        _patch_settings(monkeypatch, _routing())
        _patch_semantic(monkeypatch, "web_search")
        result = classify_query_intent("what's the vibe in the market", "epic", mcp_access=BRAVE_ACCESS)
        assert result == QueryIntent.NEEDS_WEB_SEARCH

    def test_wallet_fastpath_bypasses_semantic(self, monkeypatch):
        _patch_settings(monkeypatch, _routing())
        mock = _patch_semantic(monkeypatch, None)
        result = classify_query_intent("my wallet balance", "legendary", mcp_access=EEVA_ACCESS)
        assert result == QueryIntent.NEEDS_WALLET
        mock.assert_not_called()  # fast-path hit before the embed round-trip

    def test_explicit_search_fastpath_bypasses_semantic(self, monkeypatch):
        _patch_settings(monkeypatch, _routing())
        mock = _patch_semantic(monkeypatch, None)
        result = classify_query_intent("search the web for the bitcoin price", "epic", mcp_access=BRAVE_ACCESS)
        assert result == QueryIntent.NEEDS_WEB_SEARCH
        mock.assert_not_called()

    def test_semantic_none_falls_through_to_neither(self, monkeypatch):
        _patch_settings(monkeypatch, _routing())
        _patch_semantic(monkeypatch, None)
        result = classify_query_intent("tell me a story", "epic", mcp_access=BRAVE_ACCESS)
        assert result == QueryIntent.NEEDS_NEITHER

    def test_pure_llm_persona_skips_semantic(self, monkeypatch):
        _patch_settings(monkeypatch, _routing())
        mock = _patch_semantic(monkeypatch, "wallet")
        result = classify_query_intent("my balance", "common", mcp_access=[])
        assert result == QueryIntent.NEEDS_NEITHER
        mock.assert_not_called()  # no MCP capability → semantic path not entered

    def test_semantic_wallet_uses_primary_centroid_flag(self, monkeypatch):
        """The classifier must call route_by_embedding with drop_llm_only_centroid=True
        and the configured threshold/margin."""
        _patch_settings(monkeypatch, _routing(threshold=0.61, margin=0.0))
        mock = _patch_semantic(monkeypatch, "wallet")
        classify_query_intent("how are my trades doing", "legendary", mcp_access=EEVA_ACCESS)
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("drop_llm_only_centroid") is True
        assert kwargs.get("threshold") == 0.61
        assert kwargs.get("margin") == 0.0

    def test_follow_up_wins_before_semantic(self, monkeypatch):
        """Follow-up detection runs before the semantic branch."""
        _patch_settings(monkeypatch, _routing())
        mock = _patch_semantic(monkeypatch, None)
        result = classify_query_intent(
            "yes please", "legendary", mcp_access=EEVA_ACCESS,
            last_assistant_message="want me to check your wallet balance?",
        )
        assert result == QueryIntent.NEEDS_WALLET
        mock.assert_not_called()
