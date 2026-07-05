# src/coordinator/services/search_execution_service.py
"""
Search Execution Service - Execute Brave web search tool calls.

Extracted from llm_client.py as part of Phase 2 Service Decomposition.
Handles MCP client invocation for web search operations.
"""

from __future__ import annotations

import logging
import re
from typing import Optional, List, Any

from ..tool_definitions import ToolCall

logger = logging.getLogger(__name__)

# Queries about the immediate present/near future benefit from Brave's
# `freshness` filter (2026-07-05 incident: a "latest news in switzerland
# today" search surfaced a 5-day-old roundup; a weather query surfaced a
# generic 10-day-forecast page). Conservative, whole-word heuristics: when in
# doubt pass NO freshness filter (full index) — a too-narrow window can
# starve legitimate queries of results.
_FRESHNESS_DAY_RE = re.compile(
    r"\b(today|tonight|right now|breaking)\b", re.IGNORECASE
)
_FRESHNESS_WEEK_RE = re.compile(
    r"\b(tomorrow|weather|forecast|latest|this week|recent|news|headlines|"
    r"currently)\b",
    re.IGNORECASE,
)


def infer_freshness(query: str) -> Optional[str]:
    """Map temporal cues in a query to a Brave freshness filter.

    Returns 'pd' (past day) for immediate/now cues, 'pw' (past week) for
    recency cues, or None (no filter) when the query carries no temporal cue.
    """
    if not query:
        return None
    if _FRESHNESS_DAY_RE.search(query):
        return "pd"
    if _FRESHNESS_WEEK_RE.search(query):
        return "pw"
    return None


class SearchExecutionService:
    """Service for executing web search operations via MCP client.

    Handles:
    - Brave web search execution
    - Query validation
    - Error handling for search operations

    This service requires an MCP client for operation.
    """

    def __init__(self, mcp_client: Optional[Any] = None):
        """Initialize the search execution service.

        Args:
            mcp_client: Brave MCP client for web search (BraveMCPClientStdio)
        """
        self.mcp_client = mcp_client

    def execute_search(self, tool_call: ToolCall) -> Optional[List[Any]]:
        """Execute a Brave web search tool call.

        Args:
            tool_call: ToolCall with brave_web_search

        Returns:
            List of SearchResult objects, or None if search failed
        """
        if not self.mcp_client:
            logger.error("[SearchExecution] Brave MCP client not available, cannot execute search")
            return None

        try:
            query = tool_call.arguments.get("query", "")
            if not query:
                logger.warning("[SearchExecution] Search query is empty")
                return None

            # Locale + freshness (2026-07-05 incident: neither was ever passed —
            # a Swiss weather query returned a US aggregator in °F, and "news
            # today" surfaced a 5-day-old roundup). Country/lang come from
            # settings (lazy import: config imports at module level cycle);
            # freshness is inferred from temporal cues in the resolved query.
            from ..config import get_settings

            brave = get_settings().brave
            country = brave.country or None
            search_lang = brave.search_lang or None
            freshness = infer_freshness(query)

            logger.info(
                f"[SearchExecution] Executing Brave search: '{query}' "
                f"(country={country}, lang={search_lang}, freshness={freshness})"
            )
            results = self.mcp_client.search_web(
                query,
                country=country,
                search_lang=search_lang,
                freshness=freshness,
            )
            logger.info(f"[SearchExecution] Brave search returned {len(results)} results")

            return results

        except Exception as e:
            logger.error(f"[SearchExecution] Brave search failed: {e}", exc_info=True)
            return None
