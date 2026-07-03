# tests/backend/coordinator/test_intent_classifier.py
"""Unit tests for classify_query_intent — legacy (flag-OFF) and semantic-PRIMARY paths.

All tests are headless: the semantic-primary path mocks both get_settings (the flag)
and route_by_embedding (the embedder), so no live Ollama is needed.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import src.coordinator.tools.intent_classifier as ic
from src.coordinator.tools.intent_classifier import QueryIntent, classify_query_intent

EEVA_ACCESS = ["brave_search", "solana_wallet"]
BRAVE_ACCESS = ["brave_search"]


def _routing(semantic_primary=False, threshold=0.61, margin=0.0):
    return SimpleNamespace(
        semantic_primary=semantic_primary,
        semantic_threshold=threshold,
        semantic_margin=margin,
    )


def _patch_settings(monkeypatch, routing):
    """Patch the lazily-imported get_settings so classify_query_intent sees our flag."""
    settings = SimpleNamespace(routing=routing)
    monkeypatch.setattr("src.coordinator.config.get_settings", lambda: settings, raising=False)


def _patch_semantic(monkeypatch, return_value):
    mock = MagicMock(return_value=return_value)
    monkeypatch.setattr(
        "src.coordinator.tools.semantic_router.route_by_embedding", mock, raising=False
    )
    return mock


class TestLegacyPath:
    """Flag-OFF: the keyword-first behaviour must be preserved."""

    def test_follow_up_wallet(self, monkeypatch):
        _patch_settings(monkeypatch, _routing(semantic_primary=False))
        result = classify_query_intent(
            "yes", "legendary", mcp_access=EEVA_ACCESS,
            last_assistant_message="your wallet has 0.5 sol",
        )
        assert result == QueryIntent.NEEDS_WALLET

    def test_wallet_keyword(self, monkeypatch):
        _patch_settings(monkeypatch, _routing(semantic_primary=False))
        result = classify_query_intent("my balance", "legendary", mcp_access=EEVA_ACCESS)
        assert result == QueryIntent.NEEDS_WALLET

    def test_negation_guard_blocks_wallet(self, monkeypatch):
        _patch_settings(monkeypatch, _routing(semantic_primary=False))
        result = classify_query_intent("I'm not buying bitcoin", "legendary", mcp_access=EEVA_ACCESS)
        assert result != QueryIntent.NEEDS_WALLET

    def test_web_keyword(self, monkeypatch):
        _patch_settings(monkeypatch, _routing(semantic_primary=False))
        result = classify_query_intent("what's the latest news on solana", "epic", mcp_access=BRAVE_ACCESS)
        assert result == QueryIntent.NEEDS_WEB_SEARCH

    def test_educational_neither(self, monkeypatch):
        _patch_settings(monkeypatch, _routing(semantic_primary=False))
        result = classify_query_intent("how does solana work", "epic", mcp_access=BRAVE_ACCESS)
        assert result == QueryIntent.NEEDS_NEITHER

    def test_pure_llm_persona_unaffected(self, monkeypatch):
        _patch_settings(monkeypatch, _routing(semantic_primary=False))
        result = classify_query_intent("what's in my wallet", "common", mcp_access=[])
        assert result == QueryIntent.NEEDS_NEITHER

    def test_flag_off_never_calls_primary_semantic(self, monkeypatch):
        """Flag-OFF must not enter _classify_semantic_primary (no drop_llm_only call)."""
        _patch_settings(monkeypatch, _routing(semantic_primary=False))
        mock = _patch_semantic(monkeypatch, "wallet")
        classify_query_intent("tell me about yourself", "epic", mcp_access=BRAVE_ACCESS)
        # Legacy path may call route_by_embedding as a last-resort fallback, but never
        # with drop_llm_only_centroid=True (the primary-mode marker).
        for call in mock.call_args_list:
            assert call.kwargs.get("drop_llm_only_centroid", False) is False


class TestSemanticPrimaryPath:
    """Flag-ON: fast-path → semantic router → NEEDS_NEITHER."""

    def test_semantic_wallet_routes_wallet(self, monkeypatch):
        _patch_settings(monkeypatch, _routing(semantic_primary=True))
        _patch_semantic(monkeypatch, "wallet")
        result = classify_query_intent("thinking of moving funds around", "legendary", mcp_access=EEVA_ACCESS)
        assert result == QueryIntent.NEEDS_WALLET

    def test_semantic_wallet_blocked_by_negation(self, monkeypatch):
        _patch_settings(monkeypatch, _routing(semantic_primary=True))
        _patch_semantic(monkeypatch, "wallet")
        result = classify_query_intent("I'm not going to swap anything", "legendary", mcp_access=EEVA_ACCESS)
        assert result != QueryIntent.NEEDS_WALLET

    def test_semantic_web_routes_web(self, monkeypatch):
        _patch_settings(monkeypatch, _routing(semantic_primary=True))
        _patch_semantic(monkeypatch, "web_search")
        result = classify_query_intent("what's the vibe in the market", "epic", mcp_access=BRAVE_ACCESS)
        assert result == QueryIntent.NEEDS_WEB_SEARCH

    def test_wallet_fastpath_bypasses_semantic(self, monkeypatch):
        _patch_settings(monkeypatch, _routing(semantic_primary=True))
        mock = _patch_semantic(monkeypatch, None)
        result = classify_query_intent("my wallet balance", "legendary", mcp_access=EEVA_ACCESS)
        assert result == QueryIntent.NEEDS_WALLET
        mock.assert_not_called()  # fast-path hit before the embed round-trip

    def test_explicit_search_fastpath_bypasses_semantic(self, monkeypatch):
        _patch_settings(monkeypatch, _routing(semantic_primary=True))
        mock = _patch_semantic(monkeypatch, None)
        result = classify_query_intent("search the web for the bitcoin price", "epic", mcp_access=BRAVE_ACCESS)
        assert result == QueryIntent.NEEDS_WEB_SEARCH
        mock.assert_not_called()

    def test_semantic_none_falls_through_to_neither(self, monkeypatch):
        _patch_settings(monkeypatch, _routing(semantic_primary=True))
        _patch_semantic(monkeypatch, None)
        result = classify_query_intent("tell me a story", "epic", mcp_access=BRAVE_ACCESS)
        assert result == QueryIntent.NEEDS_NEITHER

    def test_pure_llm_persona_skips_semantic(self, monkeypatch):
        _patch_settings(monkeypatch, _routing(semantic_primary=True))
        mock = _patch_semantic(monkeypatch, "wallet")
        result = classify_query_intent("my balance", "common", mcp_access=[])
        assert result == QueryIntent.NEEDS_NEITHER
        mock.assert_not_called()  # no MCP capability → semantic path not entered

    def test_semantic_wallet_uses_primary_centroid_flag(self, monkeypatch):
        """The primary path must call route_by_embedding with drop_llm_only_centroid=True
        and the configured threshold/margin."""
        _patch_settings(monkeypatch, _routing(semantic_primary=True, threshold=0.61, margin=0.0))
        mock = _patch_semantic(monkeypatch, "wallet")
        classify_query_intent("how are my trades doing", "legendary", mcp_access=EEVA_ACCESS)
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("drop_llm_only_centroid") is True
        assert kwargs.get("threshold") == 0.61
        assert kwargs.get("margin") == 0.0

    def test_follow_up_still_wins_under_flag(self, monkeypatch):
        """Follow-up detection runs before the semantic branch, for both flag states."""
        _patch_settings(monkeypatch, _routing(semantic_primary=True))
        mock = _patch_semantic(monkeypatch, None)
        result = classify_query_intent(
            "yes please", "legendary", mcp_access=EEVA_ACCESS,
            last_assistant_message="want me to check your wallet balance?",
        )
        assert result == QueryIntent.NEEDS_WALLET
        mock.assert_not_called()
