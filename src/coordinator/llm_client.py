# src/coordinator/llm_client.py
# LLM client wrapper for GraphRAG Local QA Chat with Personas
# Uses LangChain's OllamaLLM with ChatPromptTemplate for prompt formatting.
# Handles Ollama connectivity errors.
# Enhanced with function calling support for autonomous tool usage.

import logging
from typing import List, Dict, Any, Optional, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.llms import OllamaLLM
from ollama._types import ResponseError

# Import tool definitions and MCP client
from .tool_definitions import (
    build_tool_system_prompt,
    build_synthesis_prompt,
    parse_tool_call,
    format_search_results_for_llm,
    should_use_keyword_filter,
    ToolCall
)
from .mcp_client import BraveMCPClient

logger = logging.getLogger(__name__)

class LC_OllamaClient:
    """Thin wrapper around LangChain's OllamaLLM using ChatPromptTemplate.

    Enhanced with function calling support for autonomous tool usage (e.g., web search).
    """

    def __init__(
        self,
        base: str,
        model: str,
        temperature: float = 0.1,
        mcp_client: Optional[BraveMCPClient] = None
    ):
        """Initialize the LLM client.

        Args:
            base: Ollama base URL
            model: Model name (e.g., 'dolphin-llama3:8b')
            temperature: Sampling temperature (0.0-1.0)
            mcp_client: Optional Brave MCP client for web search
        """
        self.llm = OllamaLLM(base_url=base, model=model, temperature=temperature)
        self.mcp_client = mcp_client
        logger.info(f"Initialized LC_OllamaClient with model={model}, temperature={temperature}, tools_enabled={mcp_client is not None}")

    def _invoke(self, prompt: str) -> str:
        try:
            return self.llm.invoke(prompt).strip()
        except ResponseError as e:
            msg = str(e)
            if "not found" in msg.lower():
                raise RuntimeError(
                    "Ollama model not found.\n"
                    f"Pull it:\n  ollama pull {self.llm.model}\n"
                    f"base_url={self.llm.base_url}\n"
                )
            raise

    def complete(self, system: str, user_prompt: str) -> str:
        """Complete a prompt without tool support (backward compatible).

        Args:
            system: System prompt
            user_prompt: User message

        Returns:
            LLM response string
        """
        template = ChatPromptTemplate.from_messages([
            ("system", "{system}"),
            ("user", "{user}")
        ])
        rendered = template.format_prompt(system=system, user=user_prompt).to_string()
        return self._invoke(rendered)

    def _should_force_search(self, query: str) -> bool:
        """
        Determine if we should force search execution (bypass LLM decision).

        For queries with high-confidence search intent (price, current, latest),
        we force search instead of relying on LLM to call the tool.

        Args:
            query: User query string

        Returns:
            True if search should be forced, False otherwise
        """
        query_lower = query.lower()

        # High-confidence price/current data patterns
        force_patterns = [
            # Price queries
            ("price", ["ethereum", "bitcoin", "btc", "eth", "crypto", "stock", "current", "now", "right now", "today"]),
            ("cost", ["ethereum", "bitcoin", "btc", "eth", "current", "now", "today"]),
            ("value", ["ethereum", "bitcoin", "btc", "eth", "current", "now", "today"]),
            ("worth", ["ethereum", "bitcoin", "btc", "eth", "current", "now", "today"]),

            # Current/latest queries
            ("latest", ["news", "update", "price", "data", "info", "developments", "development"]),
            ("current", ["price", "news", "data", "status", "situation"]),
            ("right now", []),
            ("today", ["price", "news", "happening"]),
            ("recent", ["news", "update", "development", "change"]),

            # Market queries
            ("trading at", []),
            ("market price", []),
        ]

        for primary, secondary_list in force_patterns:
            if primary in query_lower:
                # If primary keyword found, check if any secondary keywords also present
                if not secondary_list:  # No secondary required
                    return True
                if any(sec in query_lower for sec in secondary_list):
                    return True

        return False

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
            response = self.complete(persona_system, user_prompt)
            return (response, None, None)

        # Check if we should force search execution
        force_search = self._should_force_search(user_prompt)
        if force_search:
            logger.info(f"[Force Search] High-confidence search query detected: '{user_prompt[:100]}'")
            logger.info("[Force Search] Bypassing LLM tool calling, executing search directly")

            # Check if brave_web_search tool is available
            brave_tool = next((t for t in tools if t.get("function", {}).get("name") == "brave_web_search"), None)
            if brave_tool and self.mcp_client:
                # Force execute search
                search_results = self._execute_brave_search(ToolCall(
                    name="brave_web_search",
                    arguments={"query": user_prompt, "reason": "Forced search for price/current data query"}
                ))

                if search_results:
                    # Format results and synthesize
                    formatted_results = format_search_results_for_llm(search_results)
                    conversation_history = [formatted_results, f"User: {user_prompt}"]

                    # Build synthesis prompt
                    synthesis_system = build_synthesis_prompt(persona_system, has_search_results=True)
                    logger.info(f"[Synthesis] Using synthesis prompt (length: {len(synthesis_system)} chars, search_results: {len(search_results)})")

                    # Generate answer (WITHOUT citations - LLM focuses on content only)
                    llm_answer = self.complete(synthesis_system, "\n\n".join(conversation_history))
                    logger.info(f"[Synthesis] Generated answer (length: {len(llm_answer)} chars)")

                    # Auto-generate accurate citations from search results
                    accurate_citations = self._auto_generate_citations(search_results)

                    # Combine answer + system-generated citations
                    final_response = llm_answer + accurate_citations

                    return (final_response, ToolCall(name="brave_web_search", arguments={"query": user_prompt}), search_results)
                else:
                    logger.warning("[Anti-Hallucination] Forced search returned no results - admitting ignorance")
                    honest_response = "I attempted to search for current information on this topic, but the search didn't return any results. I don't have up-to-date information to answer this question accurately. I'd rather admit I don't know than guess or use potentially outdated information."
                    return (honest_response, None, None)

        # Pre-filter with keywords to reduce false positives
        keyword_decision = should_use_keyword_filter(user_prompt)
        if keyword_decision is False:
            logger.info(f"Keyword filter: NO SEARCH needed for query: '{user_prompt[:100]}'")
            response = self.complete(persona_system, user_prompt)
            # Strip any hallucinated citations
            response = self._strip_hallucinated_citations(response)
            return (response, None, None)

        search_expected = keyword_decision is True
        if search_expected:
            logger.info(f"Keyword filter: SEARCH likely needed for query: '{user_prompt[:100]}'")

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
                response = self.complete(enhanced_system, user_prompt)
            else:
                # Subsequent iterations with conversation history
                messages = "\n\n".join(conversation_history)
                response = self.complete(enhanced_system, f"{messages}\n\nUser: {user_prompt}")

            logger.debug(f"LLM response length: {len(response)} chars")
            logger.debug(f"LLM response preview: {response[:200]}")

            # Parse for tool calls
            tool_call = parse_tool_call(response)

            if tool_call is None:
                # No tool call, this is the final answer
                logger.info("No tool call detected, returning final answer")

                # CRITICAL: If search was expected but LLM didn't search, admit ignorance
                if search_expected:
                    logger.warning(f"[Anti-Hallucination] Search expected but LLM didn't call tool - returning honest 'don't know' response")
                    honest_response = "I don't have access to current information on this topic. A web search was attempted but didn't execute successfully. I'd rather admit I don't know than provide potentially outdated or incorrect information."
                    return (honest_response, None, None)

                # Strip any hallucinated citations
                response = self._strip_hallucinated_citations(response)
                return (response, None, None)

            # Tool call detected
            logger.info(f"Tool call detected: {tool_call.name}({list(tool_call.arguments.keys())})")

            if tool_call.name == "brave_web_search":
                # Execute web search
                search_results = self._execute_brave_search(tool_call)

                if not search_results:
                    logger.warning("[Anti-Hallucination] Web search returned no results - admitting ignorance")
                    honest_response = "I attempted to search for current information on this topic, but the search didn't return any results. I don't have up-to-date information to answer this question accurately. I'd rather admit I don't know than guess or use potentially outdated information."
                    return (honest_response, None, None)

                # Format search results for LLM
                formatted_results = format_search_results_for_llm(search_results)
                logger.info(f"Formatted {len(search_results)} search results for LLM")

                # Add results to conversation and ask LLM to synthesize
                conversation_history.append(formatted_results)
                conversation_history.append(f"User: {user_prompt}")

                # Build synthesis prompt (includes search result usage instructions)
                synthesis_system = build_synthesis_prompt(
                    persona_system,
                    has_search_results=True
                )
                logger.info(f"[Synthesis] Using synthesis prompt (length: {len(synthesis_system)} chars, search_results: {len(search_results)})")

                # Generate answer (WITHOUT citations - LLM focuses on content only)
                llm_answer = self.complete(
                    synthesis_system,  # Use synthesis prompt with enhanced instructions
                    "\n\n".join(conversation_history)
                )

                logger.info(f"[Synthesis] Generated answer (length: {len(llm_answer)} chars)")

                # Auto-generate accurate citations from search results
                accurate_citations = self._auto_generate_citations(search_results)

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
        response = self.complete(persona_system, user_prompt)
        return (response, None, None)

    def _strip_hallucinated_citations(self, response: str) -> str:
        """
        Strip any hallucinated citations from LLM response.

        If the LLM hallucinates citations (when search wasn't used),
        we remove them entirely. This prevents showing fake sources to users.

        Args:
            response: LLM response that may contain hallucinated citations

        Returns:
            Response with citations removed (if they exist)
        """
        # Check if response contains citation markers
        citation_markers = ["🔍 Sources:", "Sources:", "**Sources:**"]

        for marker in citation_markers:
            if marker in response:
                # Remove everything from the marker onwards
                response = response.split(marker)[0].strip()
                logger.warning(f"[Anti-Hallucination] Stripped hallucinated citations from response")
                break

        return response

    def _auto_generate_citations(self, search_results: List[Any]) -> str:
        """
        Auto-generate formatted citations from search results.

        This ensures 100% accurate URLs with no hallucination risk.
        The LLM is NOT responsible for formatting citations - the system
        generates them automatically from actual search results.

        Args:
            search_results: List of SearchResult objects from Brave

        Returns:
            Formatted citations string with 🔍 emoji and markdown links
        """
        if not search_results:
            return ""

        citations = "\n\n🔍 Sources:\n"

        # Use top 5 search results for citations
        for result in search_results[:5]:
            # Use actual title and URL from search result (cannot be hallucinated)
            title = result.title if result.title else "Untitled"
            url = result.url if result.url else "#"

            citations += f"• [{title}]({url})\n"

        logger.info(f"[Auto-Citations] Generated {min(len(search_results), 5)} citations with verified URLs")

        return citations

    def _execute_brave_search(self, tool_call: ToolCall) -> Optional[List[Any]]:
        """Execute a Brave web search tool call.

        Args:
            tool_call: ToolCall with brave_web_search

        Returns:
            List of SearchResult objects, or None if search failed
        """
        if not self.mcp_client:
            logger.error("Brave MCP client not available, cannot execute search")
            return None

        try:
            query = tool_call.arguments.get("query", "")
            if not query:
                logger.warning("Search query is empty")
                return None

            logger.info(f"Executing Brave search: '{query}'")
            results = self.mcp_client.search_web(query)
            logger.info(f"Brave search returned {len(results)} results")

            return results

        except Exception as e:
            logger.error(f"Brave search failed: {e}", exc_info=True)
            return None
