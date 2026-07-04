# src/coordinator/services/tool_calling_service.py
"""
Tool Calling Service - Autonomous tool calling orchestration.

Extracted from llm_client.py as part of Phase 2 Service Decomposition.
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
from .llm_completion_service import LLMCompletionService
from .citation_service import CitationService
from .query_extraction_service import QueryExtractionService
from .query_resolution_service import QueryResolutionService
from .force_search_service import ForceSearchService
from .search_execution_service import SearchExecutionService
from .search_relevance_service import SearchRelevanceService

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
    - QueryExtractionService for query extraction
    - ForceSearchService for force-search detection
    - SearchExecutionService for search execution
    """

    def __init__(
        self,
        llm_service: LLMCompletionService,
        citation_service: Optional[CitationService] = None,
        query_extractor: Optional[QueryExtractionService] = None,
        force_search: Optional[ForceSearchService] = None,
        search_executor: Optional[SearchExecutionService] = None,
        query_resolver: Optional[QueryResolutionService] = None,
        relevance_service: Optional[SearchRelevanceService] = None
    ):
        """Initialize tool calling service.

        Args:
            llm_service: LLM completion service for generating responses
            citation_service: Optional citation service (defaults to CitationService)
            query_extractor: Optional query extraction service (defaults to QueryExtractionService)
            force_search: Optional force search service (defaults to ForceSearchService)
            search_executor: Optional search execution service (required for search functionality)
        """
        self.llm_service = llm_service
        self.citation_service = citation_service or CitationService()
        self.query_extractor = query_extractor or QueryExtractionService()
        self.query_resolver = query_resolver or QueryResolutionService(
            llm_service, query_extractor=self.query_extractor
        )
        self.relevance_service = relevance_service or SearchRelevanceService()
        self.force_search = force_search or ForceSearchService()
        self.search_executor = search_executor

        logger.info(
            f"Initialized ToolCallingService: "
            f"tools_enabled={search_executor is not None and search_executor.mcp_client is not None}"
        )

    def _synthesis_user_turn(self, user_prompt: str, query: str) -> str:
        """Build the 'User:' turn shown to the synthesis LLM.

        Default (legacy): the full compiled conversation. That carries the poison
        — an earlier in-conversation self-apology/refusal ("I can't search / I
        hallucinated") that a local model (no instruction-hierarchy training)
        weights equally to system rules and echoes, refusing even when fresh
        correct results are present.

        With SEARCH_SYNTHESIS_TRUST_RESULTS on, the synthesis LLM sees only the
        fresh results (already prepended by the caller) + the RESOLVED QUERY as
        the question — not the chat log. The topic was already folded into the
        query by resolution, so no context is lost; the poison is deterministically
        gone (it isn't in the input at all). This is the reliable lever; the
        RULE 0 prompt directive is belt-and-suspenders reinforcement.
        """
        from ..config import get_settings

        if get_settings().search.synthesis_trust_results and query and query.strip():
            return f"User: {query.strip()}"
        return f"User: {user_prompt}"

    def _relevance_gate_rejects(self, query: str, results: Optional[List[Any]]) -> bool:
        """True if the relevance gate is on AND the results are off-topic.

        No-op (returns False) when SEARCH_RELEVANCE_GATE_ENABLED is off, so the
        legacy path is byte-identical. Fail-open lives in the service itself.
        """
        if not results:
            return False
        from ..config import get_settings

        search_cfg = get_settings().search
        if not search_cfg.relevance_gate_enabled:
            return False
        return not self.relevance_service.is_relevant(
            query, results, search_cfg.relevance_min_cosine
        )

    def complete_with_tools(
        self,
        persona_system: str,
        user_prompt: str,
        tools: List[Dict[str, Any]],
        max_iterations: int = 2
    ) -> Tuple[str, Optional[ToolCall], Optional[List[Any]]]:
        """Complete a prompt with autonomous tool calling support.

        The LLM can decide to use tools (e.g., web search) or answer directly.
        Implements improved prompting strategy to reduce false positives.

        For high-confidence search queries (price, current, latest), we FORCE
        search execution instead of relying on LLM's tool calling decision.

        Args:
            persona_system: Original persona system prompt
            user_prompt: User message
            tools: List of tool definitions (OpenAI format)
            max_iterations: Max tool calls allowed (default 2)

        Returns:
            Tuple of (final_response, tool_call_used, search_results)
            - final_response: LLM's final answer
            - tool_call_used: ToolCall object if tool was used, else None
            - search_results: Search results if web search was used, else None
        """
        if not tools:
            # No tools available, fall back to regular completion
            logger.debug("No tools provided, using regular completion")
            response = self.llm_service.complete(persona_system, user_prompt)
            return (response, None, None)

        # Check if we should force search execution
        force_search = self.force_search.should_force_search(user_prompt)
        if force_search:
            logger.info(f"[Force Search] High-confidence search query detected: '{user_prompt[:100]}'")
            logger.info("[Force Search] Bypassing LLM tool calling, executing search directly")

            # Check if brave_web_search tool is available
            brave_tool = next((t for t in tools if t.get("function", {}).get("name") == "brave_web_search"), None)
            if brave_tool and self.search_executor and self.search_executor.mcp_client:
                # Resolve the search query (deictic follow-ups resolved against
                # prior context when SEARCH_QUERY_RESOLUTION_ENABLED; otherwise
                # the raw latest user message, as before).
                search_query = self.query_resolver.resolve(user_prompt)
                logger.info(f"[Force Search] Resolved search query: '{search_query[:100]}'")

                # Force execute search
                search_results = self.search_executor.execute_search(ToolCall(
                    name="brave_web_search",
                    arguments={"query": search_query, "reason": "Forced search for price/current data query"}
                ))

                # Relevance gate: non-empty-but-off-topic results are treated as
                # no-result (honest abstention) instead of synthesized over.
                if self._relevance_gate_rejects(search_query, search_results):
                    logger.warning("[Relevance Gate] Forced-search results off-topic - abstaining")
                    search_results = None

                if search_results:
                    # Format results and synthesize
                    formatted_results = format_search_results_for_llm(search_results)
                    conversation_history = [formatted_results, self._synthesis_user_turn(user_prompt, search_query)]

                    # Build synthesis prompt
                    synthesis_system = build_synthesis_prompt(persona_system, has_search_results=True)
                    logger.info(f"[Synthesis] Using synthesis prompt (length: {len(synthesis_system)} chars, search_results: {len(search_results)})")

                    # Generate answer (WITHOUT citations - LLM focuses on content only)
                    llm_answer = self.llm_service.complete(synthesis_system, "\n\n".join(conversation_history))
                    logger.info(f"[Synthesis] Generated answer (length: {len(llm_answer)} chars)")

                    # Check if LLM included citations (for monitoring)
                    had_citations = any(marker in llm_answer for marker in ["🔍 Sources:", "Sources:", "**Sources:**"])

                    # Strip any LLM-generated citations (anti-hallucination defense)
                    llm_answer = self.citation_service.strip_hallucinated_citations(llm_answer)

                    # Log violation for monitoring
                    if had_citations:
                        logger.warning("[Anti-Hallucination] LLM ignored citation instruction - stripped and replaced with verified citations")

                    # Auto-generate accurate citations from search results
                    accurate_citations = self.citation_service.auto_generate_citations(search_results)

                    # Combine answer + system-generated citations
                    final_response = llm_answer + accurate_citations

                    return (final_response, ToolCall(name="brave_web_search", arguments={"query": search_query}), search_results)
                else:
                    logger.warning("[Anti-Hallucination] Forced search returned no results - admitting ignorance")
                    honest_response = "I attempted to search for current information on this topic, but the search didn't return any results. I don't have up-to-date information to answer this question accurately. I'd rather admit I don't know than guess or use potentially outdated information."
                    return (honest_response, None, None)

        # Pre-filter with keywords to reduce false positives
        keyword_decision = should_use_keyword_filter(user_prompt)
        if keyword_decision is False:
            logger.info(f"Keyword filter: NO SEARCH needed for query: '{user_prompt[:100]}'")
            response = self.llm_service.complete(persona_system, user_prompt)
            # Strip any hallucinated citations
            response = self.citation_service.strip_hallucinated_citations(response)
            return (response, None, None)

        search_expected = keyword_decision is True
        if search_expected:
            logger.info(f"Keyword filter: SEARCH likely needed for query: '{user_prompt[:100]}'")

        # If keyword filter determined search IS needed, force-execute it directly
        # instead of relying on the local LLM to generate a JSON tool call
        # (small models are unreliable at structured tool calling)
        if search_expected:
            brave_tool = next((t for t in tools if t.get("function", {}).get("name") == "brave_web_search"), None)
            if brave_tool and self.search_executor and self.search_executor.mcp_client:
                search_query = self.query_resolver.resolve(user_prompt)
                logger.info(f"[Keyword Force Search] Executing search directly: '{search_query[:100]}'")

                search_results = self.search_executor.execute_search(ToolCall(
                    name="brave_web_search",
                    arguments={"query": search_query, "reason": "Keyword filter determined search is needed"}
                ))

                if self._relevance_gate_rejects(search_query, search_results):
                    logger.warning("[Relevance Gate] Keyword-forced-search results off-topic - abstaining")
                    search_results = None

                if search_results:
                    formatted_results = format_search_results_for_llm(search_results)
                    conversation_history = [formatted_results, self._synthesis_user_turn(user_prompt, search_query)]

                    synthesis_system = build_synthesis_prompt(persona_system, has_search_results=True)
                    logger.info(f"[Synthesis] Using synthesis prompt (length: {len(synthesis_system)} chars, search_results: {len(search_results)})")

                    llm_answer = self.llm_service.complete(synthesis_system, "\n\n".join(conversation_history))
                    logger.info(f"[Synthesis] Generated answer (length: {len(llm_answer)} chars)")

                    had_citations = any(marker in llm_answer for marker in ["🔍 Sources:", "Sources:", "**Sources:**"])
                    llm_answer = self.citation_service.strip_hallucinated_citations(llm_answer)
                    if had_citations:
                        logger.warning("[Anti-Hallucination] LLM ignored citation instruction - stripped and replaced with verified citations")

                    accurate_citations = self.citation_service.auto_generate_citations(search_results)
                    final_response = llm_answer + accurate_citations

                    return (final_response, ToolCall(name="brave_web_search", arguments={"query": search_query}), search_results)
                else:
                    logger.warning("[Anti-Hallucination] Keyword-forced search returned no results - admitting ignorance")
                    honest_response = "I attempted to search for current information on this topic, but the search didn't return any results. I don't have up-to-date information to answer this question accurately. I'd rather admit I don't know than guess or use potentially outdated information."
                    return (honest_response, None, None)

        # Build enhanced system prompt with tool definitions
        enhanced_system = build_tool_system_prompt(persona_system, tools)
        logger.debug(f"Enhanced system prompt length: {len(enhanced_system)} chars")

        iteration = 0
        conversation_history = []

        while iteration < max_iterations:
            iteration += 1
            logger.debug(f"Tool calling iteration {iteration}/{max_iterations}")

            # Get LLM response
            if not conversation_history:
                # First iteration
                response = self.llm_service.complete(enhanced_system, user_prompt)
            else:
                # Subsequent iterations with conversation history
                messages = "\n\n".join(conversation_history)
                response = self.llm_service.complete(enhanced_system, f"{messages}\n\nUser: {user_prompt}")

            logger.debug(f"LLM response length: {len(response)} chars")
            logger.debug(f"LLM response preview: {response[:200]}")

            # Parse for tool calls
            tool_call = parse_tool_call(response)

            if tool_call is None:
                # No tool call, this is the final answer
                logger.info("No tool call detected, returning final answer")

                # CRITICAL: If search was expected but LLM didn't search, admit ignorance
                if search_expected:
                    logger.warning("[Anti-Hallucination] Search expected but LLM didn't call tool - returning honest 'don't know' response")
                    honest_response = "I don't have access to current information on this topic. A web search was attempted but didn't execute successfully. I'd rather admit I don't know than provide potentially outdated or incorrect information."
                    return (honest_response, None, None)

                # Strip any hallucinated citations
                response = self.citation_service.strip_hallucinated_citations(response)
                return (response, None, None)

            # Tool call detected
            logger.info(f"Tool call detected: {tool_call.name}({list(tool_call.arguments.keys())})")

            if tool_call.name == "brave_web_search":
                # Execute web search
                if not self.search_executor:
                    logger.error("Search executor not available, cannot execute search")
                    honest_response = "I attempted to search but the search service is not available. I'd rather admit I don't know than provide potentially incorrect information."
                    return (honest_response, None, None)

                search_results = self.search_executor.execute_search(tool_call)

                if self._relevance_gate_rejects(tool_call.arguments.get("query", ""), search_results):
                    logger.warning("[Relevance Gate] LLM-tool-call search results off-topic - abstaining")
                    search_results = None

                if not search_results:
                    logger.warning("[Anti-Hallucination] Web search returned no results - admitting ignorance")
                    honest_response = "I attempted to search for current information on this topic, but the search didn't return any results. I don't have up-to-date information to answer this question accurately. I'd rather admit I don't know than guess or use potentially outdated information."
                    return (honest_response, None, None)

                # Format search results for LLM
                formatted_results = format_search_results_for_llm(search_results)
                logger.info(f"Formatted {len(search_results)} search results for LLM")

                # Add results to conversation and ask LLM to synthesize
                conversation_history.append(formatted_results)
                conversation_history.append(
                    self._synthesis_user_turn(user_prompt, tool_call.arguments.get("query", ""))
                )

                # Build synthesis prompt (includes search result usage instructions)
                synthesis_system = build_synthesis_prompt(
                    persona_system,
                    has_search_results=True
                )
                logger.info(f"[Synthesis] Using synthesis prompt (length: {len(synthesis_system)} chars, search_results: {len(search_results)})")

                # Generate answer (WITHOUT citations - LLM focuses on content only)
                llm_answer = self.llm_service.complete(
                    synthesis_system,  # Use synthesis prompt with enhanced instructions
                    "\n\n".join(conversation_history)
                )

                logger.info(f"[Synthesis] Generated answer (length: {len(llm_answer)} chars)")

                # Check if LLM included citations (for monitoring)
                had_citations = any(marker in llm_answer for marker in ["🔍 Sources:", "Sources:", "**Sources:**"])

                # Strip any LLM-generated citations (anti-hallucination defense)
                llm_answer = self.citation_service.strip_hallucinated_citations(llm_answer)

                # Log violation for monitoring
                if had_citations:
                    logger.warning("[Anti-Hallucination] LLM ignored citation instruction - stripped and replaced with verified citations")

                # Auto-generate accurate citations from search results
                accurate_citations = self.citation_service.auto_generate_citations(search_results)

                # Combine answer + system-generated citations
                final_response = llm_answer + accurate_citations

                return (final_response, tool_call, search_results)

            else:
                # Unknown tool
                logger.warning(f"Unknown tool requested: {tool_call.name}")
                conversation_history.append(f"Tool '{tool_call.name}' is not available. Please answer directly.")
                continue

        # Max iterations reached
        logger.warning(f"Max iterations ({max_iterations}) reached without final answer")
        response = self.llm_service.complete(persona_system, user_prompt)
        return (response, None, None)
