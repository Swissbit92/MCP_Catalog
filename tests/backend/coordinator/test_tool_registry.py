# tests/backend/coordinator/test_tool_registry.py
"""Unit tests for the ADR-009 tool registry (Phase R)."""
from __future__ import annotations

import pytest

from src.coordinator.tools.registry import (
    ToolRegistry,
    ToolSpec,
    register_tool,
    registry as global_registry,
)
# Import for side effect: registers the 8 builtin tools into global_registry.
from src.coordinator.tools import registrations  # noqa: F401

WALLET_TOOLS = {
    "wallet_get_balances", "wallet_create_guided", "solana_get_quote",
    "solana_rsi_check", "solana_propose_swap", "solana_propose_strategy",
    "solana_trade_history",
}


def _fake_def(name):
    return lambda: {"type": "function", "function": {"name": name, "description": f"{name} desc. more.", "parameters": {"type": "object", "properties": {}}}}


# ------------------------------------------------------------ core registry

class TestRegistryCore:
    def test_register_and_get(self):
        r = ToolRegistry()
        spec = r.register(ToolSpec("t1", "web", _fake_def("t1")))
        assert r.get("t1") is spec
        assert r.get("missing") is None

    def test_register_idempotent_keeps_first(self):
        r = ToolRegistry()
        first = r.register(ToolSpec("t", "web", _fake_def("t"), blast_radius="low"))
        second = r.register(ToolSpec("t", "web", _fake_def("t"), blast_radius="high"))
        assert second is first and r.get("t").blast_radius == "low"

    def test_replace_existing(self):
        r = ToolRegistry()
        r.register(ToolSpec("t", "web", _fake_def("t"), blast_radius="low"))
        r.register(ToolSpec("t", "web", _fake_def("t"), blast_radius="high"),
                   replace_existing=True)
        assert r.get("t").blast_radius == "high"

    def test_bind_executor(self):
        r = ToolRegistry()
        r.register(ToolSpec("t", "web", _fake_def("t")))
        r.bind_executor("t", lambda **k: "ran", result_formatter=lambda x: "fmt")
        assert r.get("t").executor(x=1) == "ran"
        assert r.get("t").result_formatter(None) == "fmt"

    def test_bind_unknown_raises(self):
        r = ToolRegistry()
        with pytest.raises(KeyError):
            r.bind_executor("nope", lambda: None)

    def test_specs_for_toolsets(self):
        r = ToolRegistry()
        r.register(ToolSpec("a", "web", _fake_def("a")))
        r.register(ToolSpec("b", "wallet", _fake_def("b")))
        assert {s.name for s in r.specs_for_toolsets(["web"])} == {"a"}
        assert {s.name for s in r.specs_for_toolsets(["web", "wallet"])} == {"a", "b"}
        assert r.specs_for_toolsets([]) == []


# ------------------------------------------------- persona toolset resolution

class TestPersonaResolution:
    @pytest.fixture
    def r(self):
        reg = ToolRegistry()
        reg.register(ToolSpec("web_search", "web", _fake_def("web_search")))
        reg.register(ToolSpec("wallet_get_balances", "wallet", _fake_def("wallet_get_balances")))
        reg.register(ToolSpec("memory_search", "memory", _fake_def("memory_search")))
        return reg

    def test_explicit_toolsets_field(self, r):
        card = {"key": "eeva", "toolsets": ["web", "memory"]}
        assert r.toolsets_for_persona(card) == {"web", "memory"}

    def test_explicit_empty_toolsets(self, r):
        assert r.toolsets_for_persona({"key": "nyx", "toolsets": []}) == set()

    def test_mcp_access_alias_maps_to_toolsets(self, r):
        card = {"key": "eeva", "mcp_access": ["brave_search", "solana_wallet"]}
        assert r.toolsets_for_persona(card) == {"web", "wallet"}

    def test_mcp_access_empty(self, r):
        assert r.toolsets_for_persona({"key": "nyx", "mcp_access": []}) == set()

    def test_toolsets_field_accepts_legacy_aliases(self, r):
        # A persona listing legacy mcp strings in the new field still resolves.
        card = {"key": "x", "toolsets": ["brave_search"]}
        assert r.toolsets_for_persona(card) == {"web"}

    def test_rarity_fallback_when_neither_field(self, r):
        assert r.toolsets_for_persona({"key": "x", "rarity": "epic"}) == {"web"}
        assert r.toolsets_for_persona({"key": "x", "rarity": "common"}) == set()

    def test_toolsets_precedence_over_mcp_access(self, r):
        card = {"key": "x", "toolsets": ["memory"], "mcp_access": ["brave_search"]}
        assert r.toolsets_for_persona(card) == {"memory"}

    def test_unknown_toolset_ignored(self, r):
        card = {"key": "x", "toolsets": ["web", "bogus"]}
        assert r.toolsets_for_persona(card) == {"web"}

    def test_nsfw_flag(self, r):
        assert r.persona_nsfw({"nsfw": True}) is True
        assert r.persona_nsfw({}) is False


# ----------------------------------------------------- builtin registrations

class TestBuiltinRegistrations:
    def test_all_eight_registered(self):
        assert global_registry.names() >= {"brave_web_search"} | WALLET_TOOLS

    def test_toolsets(self):
        assert global_registry.get("brave_web_search").toolset == "web"
        for w in WALLET_TOOLS:
            assert global_registry.get(w).toolset == "wallet"

    def test_policy_mirrors_interceptor(self):
        # Must match tool_interceptor._TOOL_POLICY exactly (behavior-identical).
        assert global_registry.get("brave_web_search").blast_radius == "low"
        assert not global_registry.get("brave_web_search").requires_hitl
        for w in ("wallet_get_balances", "solana_get_quote", "solana_rsi_check",
                  "solana_trade_history"):
            assert global_registry.get(w).blast_radius == "none"
            assert not global_registry.get(w).requires_hitl
        for w in ("solana_propose_swap", "solana_propose_strategy", "wallet_create_guided"):
            assert global_registry.get(w).blast_radius == "high"
            assert global_registry.get(w).requires_hitl

    def test_eeva_full_toolkit(self):
        card = {"key": "nephilim_eeva", "mcp_access": ["brave_search", "solana_wallet"]}
        names = {s.name for s in global_registry.specs_for_persona(card)}
        assert names == {"brave_web_search"} | WALLET_TOOLS

    def test_describe_for_persona_shape(self):
        card = {"key": "nephilim_eeva", "mcp_access": ["brave_search"], "nsfw": True}
        desc = global_registry.describe_for_persona(card)
        assert desc["persona_key"] == "nephilim_eeva"
        assert desc["nsfw"] is True
        assert desc["toolsets"] == ["web"]
        assert desc["tools"]["web"][0]["name"] == "brave_web_search"
