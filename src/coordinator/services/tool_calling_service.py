# src/coordinator/services/tool_calling_service.py
"""
Tool Calling Service - Autonomous tool calling orchestration.

Extracted from llm_client.py as part of Phase 2 Core Refactoring.
Handles LLM tool calling loop with force-search detection and synthesis.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Tuple

from ..tool_definitions import (
    build_tool_system_prompt,
    build_synthesis_prompt,
    parse_tool_call,
    format_search_results_for_llm,
    should_use_keyword_filter,
    ToolCall
)
from ..mcp_client_stdio import BraveMCPClientStdio
from .llm_completion_service import LLMCompletionService
from .citation_service import CitationService

logger = logging.getLogger(__name__)


class ToolCallingService:
    """Service for autonomous tool calling with LLM.

    Handles:
    - Tool calling orchestration loop
    - Force-search detection for high-confidence queries
    - Search result synthesis
    - Anti-hallucination strategies

    Depends on:
    - LLMCompletionService for basic completions
    - CitationService for citation generation
    - BraveMCPClientStdio for web search
    """

    def __init__(
        self,
        llm_service: LLMCompletionService,
        mcp_client: Optional[BraveMCPClientStdio] = None,
        citation_service: Optional[CitationService] = None
    ):
        """Initialize tool calling service.

        Args:
            llm_service: LLM completion service for generating responses
            mcp_client: Optional Brave MCP client for web search
            citation_service: Optional citation service (defaults to CitationService)
        """
        self.llm_service = llm_service
        self.mcp_client = mcp_client
        self.citation_service = citation_service or CitationService()

        logger.info(
            f"Initialized ToolCallingService: "
            f"tools_enabled={mcp_client is not None}"
        )

    def complete_with_tools(
        self,
        persona_system: str,
        user_prompt: str,
        tools: List[Dict[str, Any]],
        max_iterations: int = 2
    ) -> Tuple[str, Optional[ToolCall], Optional[List[Any]]]:
        """Complete a prompt with autonomous tool calling - delegates to original llm_client for now.
        
        TODO: Full implementation in progress. Currently wraps original LC_OllamaClient behavior.
        """
        # Import here to avoid circular dependency during transition
        from ..llm_client import LC_OllamaClient
        
        # Create temporary client with same config as llm_service
        temp_client = LC_OllamaClient(
            base=self.llm_service.llm.base_url,
            model=self.llm_service.llm.model,
            temperature=self.llm_service.llm.temperature,
            mcp_client=self.mcp_client,
            sampling_config=self.llm_service.sampling_config
        )
        
        return temp_client.complete_with_tools(persona_system, user_prompt, tools, max_iterations)
