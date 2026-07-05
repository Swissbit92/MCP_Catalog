# src/coordinator/tools/registrations.py
"""Declarative tool registrations — ADR-009 Phase R (R2 migration).

Imported for side effects: every existing tool declares its ToolSpec here
(definition factory + safety policy). Policies mirror the pre-ADR-009
interceptor `_TOOL_POLICY` table EXACTLY — the migration is behavior-identical
by construction, and test_toolkit_characterization pins that.

Executors are bound separately at service-wiring time (not here) to keep this
module free of `services/` imports.

Import this module once at startup (startup.py) so the registry is populated
before any request. Registration is idempotent.
"""

from __future__ import annotations

from .registry import register_tool
from .tool_generators import get_brave_search_tool
from .wallet_tool_generators import (
    get_solana_get_quote_tool,
    get_solana_propose_strategy_tool,
    get_solana_propose_swap_tool,
    get_solana_rsi_check_tool,
    get_solana_trade_history_tool,
    get_wallet_create_guided_tool,
    get_wallet_get_balances_tool,
)


def register_builtin_tools() -> None:
    """Register the 8 pre-ADR-009 tools. Idempotent."""
    # --- web toolset --------------------------------------------------
    register_tool(
        "brave_web_search", "web", get_brave_search_tool,
        blast_radius="low", requires_hitl=False,
    )

    # --- wallet toolset ----------------------------------------------
    # Registration order matches get_wallet_tools() exactly so the tool list
    # presented to the model is byte-order-identical to the legacy path.
    # (blast_radius/requires_hitl mirror the interceptor _TOOL_POLICY.)
    register_tool(
        "wallet_get_balances", "wallet", get_wallet_get_balances_tool,
        blast_radius="none", requires_hitl=False,
    )
    register_tool(
        "wallet_create_guided", "wallet", get_wallet_create_guided_tool,
        blast_radius="high", requires_hitl=True,
    )
    register_tool(
        "solana_get_quote", "wallet", get_solana_get_quote_tool,
        blast_radius="none", requires_hitl=False,
    )
    register_tool(
        "solana_rsi_check", "wallet", get_solana_rsi_check_tool,
        blast_radius="none", requires_hitl=False,
    )
    register_tool(
        "solana_propose_swap", "wallet", get_solana_propose_swap_tool,
        blast_radius="high", requires_hitl=True,
    )
    register_tool(
        "solana_propose_strategy", "wallet", get_solana_propose_strategy_tool,
        blast_radius="high", requires_hitl=True,
    )
    register_tool(
        "solana_trade_history", "wallet", get_solana_trade_history_tool,
        blast_radius="none", requires_hitl=False,
    )


# Populate on import so `from . import registrations` is enough.
register_builtin_tools()
