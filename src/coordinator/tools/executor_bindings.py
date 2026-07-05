# src/coordinator/tools/executor_bindings.py
"""Bind runtime executors onto registry ToolSpecs — ADR-008 TB2.

The registry declares tool definitions + safety policy at import (registrations.py);
this module attaches the *executors* at service-wiring time (startup). Until now
`registry.bind_executor` and `clamp_safesearch` were both dead code — this wires
them.

Executor contract (used by the TB3 tool-brain loop):

    executor(arguments: dict, persona_card: dict) -> Any

`arguments` are the model's native tool-call args; `persona_card` is in scope so
the search family can apply the per-persona nsfw safesearch clamp (a non-nsfw
persona can never drop below "moderate", enforced HERE — the only place the
persona and the tool call meet). Brave client + settings are resolved lazily at
call time (not captured at bind time) so binding is init-order-independent.

Scope (MVP, reads only): the web toolset — web_search / image_search /
video_search / news_search / fetch_url. Wallet tools stay on the existing
propose->confirm->execute / handle_wallet_query flow (the loop delegates to it,
they are NOT bound here). `extract` is LLM-dependent and bound by the loop.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List

from .registry import registry
from .web_tool_generators import WEB_TOOL_CATEGORY
from .web_safesearch import clamp_safesearch

logger = logging.getLogger(__name__)


def _make_search_executor(tool_name: str) -> Callable[[Dict[str, Any], Dict[str, Any]], Any]:
    """Executor for a search-family tool. Applies the nsfw safesearch clamp,
    forces the tool's category, and routes through the SearXNG->Brave chain."""
    category = WEB_TOOL_CATEGORY.get(tool_name, "general")

    def executor(arguments: Dict[str, Any], persona_card: Dict[str, Any]) -> Any:
        # Lazy imports: avoid config/startup import cycles + init-order coupling.
        from ..startup import get_brave_client
        from ..services.search_execution_service import SearchExecutionService
        from ..tool_definitions import ToolCall
        from ..config import get_settings

        nsfw = registry.persona_nsfw(persona_card)
        default = get_settings().web_search.safesearch_default
        clamped = clamp_safesearch(arguments.get("safesearch"), nsfw, default)
        args = {
            **arguments,
            "safesearch": clamped,            # per-persona floor enforced here
            "category": arguments.get("category") or category,
        }
        svc = SearchExecutionService(mcp_client=get_brave_client())
        return svc.execute_search(ToolCall(name=tool_name, arguments=args))

    return executor


def _fetch_url_executor(arguments: Dict[str, Any], persona_card: Dict[str, Any]) -> Any:
    """Executor for fetch_url (SSRF-guarded, size/timeout-capped in the service)."""
    from ..services.web_fetch_service import fetch_url

    url = arguments.get("url", "")
    mode = arguments.get("mode", "markdown")
    return fetch_url(url, mode)


# Tools bound here (web toolset, reads only). Wallet + extract are handled by
# the TB3 loop (HITL flow / LLM), not bound as plain executors.
_SEARCH_TOOLS = ("web_search", "image_search", "video_search", "news_search")


def bind_web_executors() -> List[str]:
    """Attach web-toolset executors onto the registry. Idempotent (safe to call
    more than once). Returns the list of tool names bound. Skips any tool not
    registered (defensive) rather than raising, so a partial registry never
    breaks startup."""
    from . import registrations  # noqa: F401 - ensure specs registered

    bound: List[str] = []
    for name in _SEARCH_TOOLS:
        if registry.get(name) is None:
            logger.warning(f"[executor_bindings] tool '{name}' not registered — skipped")
            continue
        registry.bind_executor(name, _make_search_executor(name))
        bound.append(name)
    if registry.get("fetch_url") is not None:
        registry.bind_executor("fetch_url", _fetch_url_executor)
        bound.append("fetch_url")
    logger.info(f"[executor_bindings] bound web executors: {bound}")
    return bound
