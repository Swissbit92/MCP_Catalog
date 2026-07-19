# tests/backend/coordinator/test_toolkit_characterization.py
"""Characterization tests pinning pre-ADR-009 toolkit behavior.

Written BEFORE the registry migration (ADR-009 Phase R) so the migration can
prove itself behavior-identical: tool selection (get_tools_for_query /
get_tools_for_persona) and the ADR-004 interceptor's allow/deny decisions
must not change for any existing tool. If one of these tests needs editing
during the migration, that is a behavior change and must be justified
explicitly, not absorbed silently.
"""
from __future__ import annotations

import pytest

from src.coordinator.services.tool_interceptor import (
    CAT_ARGS,
    CAT_DIRECT_EXEC,
    CAT_MCP,
    CAT_UNKNOWN,
    ToolCallInterceptor,
)
from src.coordinator.tools.intent_classifier import QueryIntent
from src.coordinator.tools.tool_utils import (
    get_tools_for_persona,
    get_tools_for_query,
)

WALLET_TOOL_NAMES = {
    "wallet_get_balances",
    "wallet_create_guided",
    "solana_get_quote",
    "solana_rsi_check",
    "solana_propose_swap",
    "solana_propose_strategy",
    "solana_trade_history",
}


def _names(tools):
    return {t["function"]["name"] for t in tools}


# --------------------------------------------------------- tool selection

class TestGetToolsForQuery:
    def test_web_intent_with_brave_access(self):
        tools = get_tools_for_query(
            "latest news", "eeva", "legendary",
            mcp_access=["brave_search", "solana_wallet"],
            precomputed_intent=QueryIntent.NEEDS_WEB_SEARCH,
        )
        assert _names(tools) == {"brave_web_search"}

    def test_wallet_intent_returns_all_seven(self):
        tools = get_tools_for_query(
            "my balance", "eeva", "legendary",
            mcp_access=["brave_search", "solana_wallet"],
            precomputed_intent=QueryIntent.NEEDS_WALLET,
        )
        assert _names(tools) == WALLET_TOOL_NAMES

    def test_neither_intent_returns_empty(self):
        tools = get_tools_for_query(
            "good morning", "eeva", "legendary",
            mcp_access=["brave_search", "solana_wallet"],
            precomputed_intent=QueryIntent.NEEDS_NEITHER,
        )
        assert tools == []

    def test_web_intent_shape_is_openai_function_dict(self):
        tools = get_tools_for_query(
            "latest news", "eeva", "legendary",
            mcp_access=["brave_search"],
            precomputed_intent=QueryIntent.NEEDS_WEB_SEARCH,
        )
        t = tools[0]
        assert t["type"] == "function"
        fn = t["function"]
        assert fn["name"] == "brave_web_search"
        assert "query" in fn["parameters"]["properties"]
        assert "query" in fn["parameters"]["required"]


class TestGetToolsForPersona:
    def test_explicit_mcp_access_full(self):
        tools = get_tools_for_persona(
            "eeva", "legendary", mcp_access=["brave_search", "solana_wallet"]
        )
        assert _names(tools) == {"brave_web_search"} | WALLET_TOOL_NAMES

    def test_explicit_mcp_access_brave_only(self):
        tools = get_tools_for_persona("aegis", "epic", mcp_access=["brave_search"])
        assert _names(tools) == {"brave_web_search"}

    def test_explicit_empty_mcp_access_gets_nothing(self):
        assert get_tools_for_persona("nyx", "rare", mcp_access=[]) == []

    def test_rarity_fallback_without_mcp_access(self):
        # Personas with NO mcp_access field: rare+ get brave, common gets nothing.
        assert _names(get_tools_for_persona("x", "epic", mcp_access=None)) == {
            "brave_web_search"
        }
        assert get_tools_for_persona("x", "common", mcp_access=None) == []


# --------------------------------------------------------- interceptor gate

@pytest.fixture
def interceptor():
    # enforce_arguments pinned ON explicitly (independent of env flags).
    return ToolCallInterceptor(enforce_arguments=True)


FULL_ACCESS = ["brave_search", "solana_wallet"]


class TestInterceptorCharacterization:
    def test_brave_ok(self, interceptor):
        r = interceptor.validate(
            "brave_web_search", {"query": "latest news"}, "eeva", FULL_ACCESS
        )
        assert r.allowed and r.blast_radius == "low" and not r.requires_hitl

    def test_execute_swap_hard_blocked_from_agent(self, interceptor):
        r = interceptor.validate(
            "solana_execute_swap",
            {"from_token": "SOL", "to_token": "USDC", "amount": 1},
            "eeva", FULL_ACCESS, source="agent",
        )
        assert not r.allowed and r.blocked_category == CAT_DIRECT_EXEC
        assert r.requires_hitl and r.blast_radius == "high"

    def test_execute_swap_allowed_path_is_user_confirmed_only(self, interceptor):
        # user_confirmed passes the hard block; the tool is then unknown to the
        # policy table (execution happens via the wallet routes, not here).
        r = interceptor.validate(
            "solana_execute_swap", {}, "eeva", FULL_ACCESS, source="user_confirmed"
        )
        assert not r.allowed and r.blocked_category == CAT_UNKNOWN

    def test_unknown_tool_denied(self, interceptor):
        r = interceptor.validate("rm_rf_tool", {}, "eeva", FULL_ACCESS)
        assert not r.allowed and r.blocked_category == CAT_UNKNOWN

    def test_mcp_access_reenforced(self, interceptor):
        r = interceptor.validate(
            "wallet_get_balances", {"user_id": "u"}, "aegis", ["brave_search"]
        )
        assert not r.allowed and r.blocked_category == CAT_MCP

    def test_propose_swap_requires_hitl(self, interceptor):
        r = interceptor.validate(
            "solana_propose_swap",
            {"from_token": "SOL", "to_token": "USDC", "amount": 0.5},
            "eeva", FULL_ACCESS,
        )
        assert r.allowed and r.requires_hitl and r.blast_radius == "high"

    def test_swap_token_enum_enforced(self, interceptor):
        r = interceptor.validate(
            "solana_propose_swap",
            {"from_token": "SOL", "to_token": "EVILCOIN", "amount": 1},
            "eeva", FULL_ACCESS,
        )
        assert not r.allowed and r.blocked_category == CAT_ARGS

    def test_query_control_chars_rejected(self, interceptor):
        r = interceptor.validate(
            "brave_web_search", {"query": "hi\x00there"}, "eeva", FULL_ACCESS
        )
        assert not r.allowed and r.blocked_category == CAT_ARGS

    def test_query_shell_metachars_allowed(self, interceptor):
        # Deliberate ADR-004 decision: no shell is invoked for search.
        r = interceptor.validate(
            "brave_web_search", {"query": "AT&T stock > $20?"}, "eeva", FULL_ACCESS
        )
        assert r.allowed

    def test_wallet_read_no_hitl(self, interceptor):
        r = interceptor.validate(
            "solana_trade_history", {"user_id": "u"}, "eeva", FULL_ACCESS
        )
        assert r.allowed and not r.requires_hitl and r.blast_radius == "none"
