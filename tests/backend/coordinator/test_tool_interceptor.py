# test_tool_interceptor.py
# Unit tests for the Phase-3 deterministic tool-call interceptor (M2).

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from coordinator.services.tool_interceptor import (
    ToolCallInterceptor,
    ALLOWED_TOKENS,
    CAT_MCP,
    CAT_UNKNOWN,
    CAT_ARGS,
    CAT_DIRECT_EXEC,
)

BRAVE = ["brave_search"]
WALLET = ["brave_search", "solana_wallet"]

# enforce_arguments=True so tests are independent of the env flag.
ICEPT = ToolCallInterceptor(enforce_arguments=True)


def test_happy_path_brave():
    r = ICEPT.validate("brave_web_search", {"query": "bitcoin price today"},
                       "nephilim_eeva", WALLET)
    assert r.allowed is True
    assert r.requires_hitl is False
    assert r.blast_radius == "low"


def test_persona_without_mcp_access_blocked():
    # Nyx has no mcp_access -> any tool denied.
    r = ICEPT.validate("brave_web_search", {"query": "x"}, "nephilim_nyx", [])
    assert r.allowed is False
    assert r.blocked_category == CAT_MCP


def test_wallet_tool_requires_wallet_access():
    # A brave-only persona cannot touch wallet tools.
    r = ICEPT.validate("wallet_get_balances", {}, "nephilim_cipher", BRAVE)
    assert r.allowed is False
    assert r.blocked_category == CAT_MCP


def test_unknown_tool_denied():
    r = ICEPT.validate("rm_minus_rf", {}, "nephilim_eeva", WALLET)
    assert r.allowed is False
    assert r.blocked_category == CAT_UNKNOWN


def test_balances_read_is_no_hitl():
    r = ICEPT.validate("wallet_get_balances", {}, "nephilim_eeva", WALLET)
    assert r.allowed is True
    assert r.requires_hitl is False
    assert r.blast_radius == "none"


def test_propose_swap_requires_hitl_high_blast():
    r = ICEPT.validate("solana_propose_swap",
                       {"from_token": "SOL", "to_token": "USDC", "amount": 1.0},
                       "nephilim_eeva", WALLET)
    assert r.allowed is True
    assert r.requires_hitl is True
    assert r.blast_radius == "high"


def test_swap_bad_token_rejected():
    r = ICEPT.validate("solana_propose_swap",
                       {"from_token": "SOL", "to_token": "SCAMCOIN", "amount": 1.0},
                       "nephilim_eeva", WALLET)
    assert r.allowed is False
    assert r.blocked_category == CAT_ARGS


def test_swap_nonpositive_amount_rejected():
    r = ICEPT.validate("solana_propose_swap",
                       {"from_token": "SOL", "to_token": "USDC", "amount": 0},
                       "nephilim_eeva", WALLET)
    assert r.allowed is False
    assert r.blocked_category == CAT_ARGS


def test_swap_same_token_rejected():
    r = ICEPT.validate("solana_propose_swap",
                       {"from_token": "SOL", "to_token": "SOL", "amount": 1.0},
                       "nephilim_eeva", WALLET)
    assert r.allowed is False
    assert r.blocked_category == CAT_ARGS


def test_swap_bool_amount_rejected():
    # bool is a subclass of int; must not slip through the amount check.
    r = ICEPT.validate("solana_propose_swap",
                       {"from_token": "SOL", "to_token": "USDC", "amount": True},
                       "nephilim_eeva", WALLET)
    assert r.allowed is False
    assert r.blocked_category == CAT_ARGS


def test_direct_execute_swap_from_agent_hard_blocked():
    r = ICEPT.validate("solana_execute_swap",
                       {"from_token": "SOL", "to_token": "USDC", "amount": 1.0},
                       "nephilim_eeva", WALLET, source="agent")
    assert r.allowed is False
    assert r.blocked_category == CAT_DIRECT_EXEC


def test_execute_swap_alias_blocked_from_agent():
    r = ICEPT.validate("execute_swap", {}, "nephilim_eeva", WALLET, source="agent")
    assert r.allowed is False
    assert r.blocked_category == CAT_DIRECT_EXEC


def test_execute_swap_allowed_path_is_user_confirmed_only():
    # Even user_confirmed must still be a known tool; execute_swap isn't an LLM
    # tool, so it falls through to unknown_tool — i.e. it is never agent-callable
    # and never silently 'allowed'. This documents the defence-in-depth contract.
    r = ICEPT.validate("execute_swap", {}, "nephilim_eeva", WALLET,
                       source="user_confirmed")
    assert r.allowed is False  # not a registered LLM tool
    assert r.blocked_category == CAT_UNKNOWN


def test_query_too_long_rejected():
    r = ICEPT.validate("brave_web_search", {"query": "a" * 400},
                       "nephilim_eeva", WALLET)
    assert r.allowed is False
    assert r.blocked_category == CAT_ARGS


def test_query_with_ampersand_allowed():
    # Legitimate queries with shell-like chars must NOT be blocked (no shell).
    r = ICEPT.validate("brave_web_search", {"query": "AT&T stock price; C# vs C++"},
                       "nephilim_eeva", WALLET)
    assert r.allowed is True


def test_query_with_control_char_rejected():
    r = ICEPT.validate("brave_web_search", {"query": "evil\x00query"},
                       "nephilim_eeva", WALLET)
    assert r.allowed is False
    assert r.blocked_category == CAT_ARGS


def test_empty_query_rejected():
    r = ICEPT.validate("brave_web_search", {"query": "   "}, "nephilim_eeva", WALLET)
    assert r.allowed is False
    assert r.blocked_category == CAT_ARGS


def test_wallet_create_name_too_long_rejected():
    r = ICEPT.validate("wallet_create_guided", {"wallet_name": "x" * 40},
                       "nephilim_eeva", WALLET)
    assert r.allowed is False
    assert r.blocked_category == CAT_ARGS


def test_allowlist_off_skips_argument_check_but_keeps_mcp():
    lax = ToolCallInterceptor(enforce_arguments=False)
    # Bad token would normally fail; with allowlist off it passes (mcp still ok).
    r = lax.validate("solana_propose_swap",
                     {"from_token": "SOL", "to_token": "SCAM", "amount": 1.0},
                     "nephilim_eeva", WALLET)
    assert r.allowed is True
    # But mcp_access is still enforced even with the allowlist off.
    r2 = lax.validate("solana_propose_swap", {}, "nephilim_cipher", BRAVE)
    assert r2.allowed is False
    assert r2.blocked_category == CAT_MCP


def test_allowed_tokens_constant():
    assert ALLOWED_TOKENS == {"SOL", "USDC", "USDT"}


def test_startup_singleton_returns_interceptor():
    from coordinator.startup import get_tool_interceptor
    a = get_tool_interceptor()
    b = get_tool_interceptor()
    assert isinstance(a, ToolCallInterceptor)
    assert a is b  # shared singleton


# --- Defence-in-depth: execute_swap execution-mode guard ---

import asyncio  # noqa: E402


class _FakeJupiterOps:
    def __init__(self):
        self.called = False

    async def execute_swap(self, **kwargs):
        self.called = True
        return {"tx_signature": "sig", "out_amount": 1.0}


def test_execute_swap_rejects_unknown_execution_mode():
    from coordinator.services.wallet_execution_service import WalletExecutionService
    ops = _FakeJupiterOps()
    svc = WalletExecutionService(jupiter_ops=ops)

    async def run():
        return await svc.execute_swap(
            user_id="u", from_mint="m1", to_mint="m2",
            from_token="USDC", to_token="SOL", amount_lamports=1_000_000,
            execution_mode="agent_autonomous",  # NOT a confirmed mode
        )

    try:
        asyncio.run(run())
        assert False, "expected ValueError for non-confirmed execution_mode"
    except ValueError as e:
        assert "execution_mode" in str(e)
    assert ops.called is False  # never reached the MCP execute call


def test_execute_swap_accepts_confirmed_mode():
    from coordinator.services.wallet_execution_service import WalletExecutionService
    ops = _FakeJupiterOps()
    svc = WalletExecutionService(jupiter_ops=ops)

    async def run():
        return await svc.execute_swap(
            user_id="u", from_mint="m1", to_mint="m2",
            from_token="USDC", to_token="SOL", amount_lamports=1_000_000,
            execution_mode="adhoc_confirmed",
        )

    trade = asyncio.run(run())
    assert ops.called is True
    assert trade["status"] == "confirmed"
