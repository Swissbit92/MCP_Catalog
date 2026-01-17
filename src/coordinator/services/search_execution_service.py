# src/coordinator/services/search_execution_service.py
"""
Search Execution Service - Execute Brave web search tool calls.

Extracted from llm_client.py as part of Phase 2 Service Decomposition.
Handles MCP client invocation for web search operations.
"""

from __future__ import annotations

import logging
from typing import Optional, List, Any

from ..tool_definitions import ToolCall

logger = logging.getLogger(__name__)


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

            logger.info(f"[SearchExecution] Executing Brave search: '{query}'")
            results = self.mcp_client.search_web(query)
            logger.info(f"[SearchExecution] Brave search returned {len(results)} results")

            return results

        except Exception as e:
            logger.error(f"[SearchExecution] Brave search failed: {e}", exc_info=True)
            return None
