# src/coordinator/llm_client.py
# LLM client wrapper for GraphRAG Local QA Chat with Personas
# Uses LangChain's OllamaLLM with ChatPromptTemplate for prompt formatting.
# Handles Ollama connectivity errors.
# Enhanced with function calling support for autonomous tool usage.
# Phase 1.3: Added advanced sampling parameters support.

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
from .mcp_client_stdio import BraveMCPClientStdio
from .models.mcp_models import SearchResult

# Import sampling presets (Phase 1.3)
from .models.sampling_presets import (
    SamplingConfig,
    get_preset_or_default,
    get_sampling_for_persona,
)

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """Estimate token count (4 chars ≈ 1 token).

    Args:
        text: Input text to estimate tokens for

    Returns:
        Estimated token count
    """
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except (ImportError, Exception):
        # Fallback: character-based approximation
        return max(1, len(text) // 4)


def log_context_stats(system_prompt: str, history: List[Any], query: str, model_context_window: int = 4096) -> dict:
    """Log token usage statistics for monitoring.

    Args:
        system_prompt: System prompt text
        history: List of ChatTurn objects
        query: User query text
        model_context_window: Model's context window size (default: 4096)

    Returns:
        Dictionary with token usage statistics
    """
    system_tokens = estimate_tokens(system_prompt)
    history_tokens = sum(estimate_tokens(turn.content) for turn in history)
    query_tokens = estimate_tokens(query)
    total_tokens = system_tokens + history_tokens + query_tokens

    stats = {
        "system_tokens": system_tokens,
        "history_tokens": history_tokens,
        "history_messages": len(history),
        "query_tokens": query_tokens,
        "total_input_tokens": total_tokens,
        "estimated_budget_remaining": model_context_window - total_tokens,
        "budget_usage_percent": round((total_tokens / model_context_window) * 100, 1)
    }

    # Log with color coding based on usage
    usage_pct = stats["budget_usage_percent"]
    if usage_pct > 90:
        logger.warning(
            f"[Tokens] ⚠️ HIGH USAGE: {total_tokens}/{model_context_window} tokens ({usage_pct}%) | "
            f"History: {len(history)} msgs ({history_tokens} tokens) | Remaining: {stats['estimated_budget_remaining']}"
        )
    elif usage_pct > 70:
        logger.info(
            f"[Tokens] Input: {total_tokens}/{model_context_window} tokens ({usage_pct}%) | "
            f"History: {len(history)} msgs ({history_tokens} tokens) | Remaining: {stats['estimated_budget_remaining']}"
        )
    else:
        logger.debug(
            f"[Tokens] Input: {total_tokens}/{model_context_window} tokens ({usage_pct}%) | "
            f"History: {len(history)} msgs ({history_tokens} tokens)"
        )

    return stats


class LC_OllamaClient:
    """Thin wrapper around LangChain's OllamaLLM using ChatPromptTemplate.

    Enhanced with function calling support for autonomous tool usage (e.g., web search).
    Phase 1.3: Added advanced sampling parameters (repeat_penalty, top_k, top_p, min_p).
    """

    def __init__(
        self,
        base: str,
        model: str,
        temperature: float = 0.1,
        mcp_client: Optional[BraveMCPClientStdio] = None,
        sampling_config: Optional[SamplingConfig] = None,
        # Individual sampling params (override sampling_config if provided)
        repeat_penalty: Optional[float] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
    ):
        """Initialize the LLM client with advanced sampling support.

        Args:
            base: Ollama base URL
            model: Model name (e.g., 'dolphin-llama3:8b')
            temperature: Sampling temperature (0.0-2.0)
            mcp_client: Optional Brave MCP client for web search
            sampling_config: Optional SamplingConfig for preset-based configuration
            repeat_penalty: Optional repetition penalty (1.0-2.0)
            top_k: Optional Top-K sampling (0-100)
            top_p: Optional nucleus sampling threshold (0.0-1.0)
        """
        # Build Ollama params
        ollama_params = {
            "base_url": base,
            "model": model,
            "temperature": temperature,
        }

        # Apply sampling config if provided
        if sampling_config:
            config_params = sampling_config.to_ollama_params()
            # Temperature from sampling_config unless explicitly overridden
            if temperature == 0.1:  # default value
                ollama_params["temperature"] = config_params.get("temperature", 0.1)
            if "repeat_penalty" in config_params:
                ollama_params["repeat_penalty"] = config_params["repeat_penalty"]
            if "top_k" in config_params:
                ollama_params["top_k"] = config_params["top_k"]
            if "top_p" in config_params:
                ollama_params["top_p"] = config_params["top_p"]

        # Individual params override sampling_config
        if repeat_penalty is not None:
            ollama_params["repeat_penalty"] = repeat_penalty
        if top_k is not None:
            ollama_params["top_k"] = top_k
        if top_p is not None:
            ollama_params["top_p"] = top_p

        self.llm = OllamaLLM(**ollama_params)
        self.mcp_client = mcp_client
        self.sampling_config = sampling_config

        # Log sampling parameters
        sampling_info = f"temp={ollama_params['temperature']}"
        if "repeat_penalty" in ollama_params:
            sampling_info += f", repeat_penalty={ollama_params['repeat_penalty']}"
        if "top_k" in ollama_params:
            sampling_info += f", top_k={ollama_params['top_k']}"
        if "top_p" in ollama_params:
            sampling_info += f", top_p={ollama_params['top_p']}"

        preset_name = sampling_config.name if sampling_config else "custom"
        logger.info(
            f"Initialized LC_OllamaClient with model={model}, "
            f"sampling=[{sampling_info}], preset={preset_name}, "
            f"tools_enabled={mcp_client is not None}"
        )

    def get_sampling_info(self) -> Dict[str, Any]:
        """Get current sampling configuration as dict for response metadata."""
        info = {
            "temperature": self.llm.temperature,
            "model": self.llm.model,
        }
        if hasattr(self.llm, "repeat_penalty") and self.llm.repeat_penalty:
            info["repeat_penalty"] = self.llm.repeat_penalty
        if hasattr(self.llm, "top_k") and self.llm.top_k:
            info["top_k"] = self.llm.top_k
        if hasattr(self.llm, "top_p") and self.llm.top_p:
            info["top_p"] = self.llm.top_p
        if self.sampling_config:
            info["preset"] = self.sampling_config.name
        return info

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

    def _extract_latest_user_message(self, conversation: str) -> str:
        """
        Extract the latest user message from a conversation history.

        The conversation format is:
            User: <message 1>

            Assistant: <response 1>

            User: <message 2>

        Args:
            conversation: Full conversation history

        Returns:
            Latest user message only
        """
        # Split by lines and find the last "User: " message
        lines = conversation.split("\n")
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith("User: "):
                return line[6:].strip()  # Remove "User: " prefix

        # Fallback: return entire conversation if no "User: " prefix found
        logger.warning("[Query Extraction] Could not extract latest user message, using full conversation")
        return conversation

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
                # Extract just the latest user message for search query
                search_query = self._extract_latest_user_message(user_prompt)
                logger.info(f"[Force Search] Extracted search query: '{search_query[:100]}'")

                # Force execute search
                search_results = self._execute_brave_search(ToolCall(
                    name="brave_web_search",
                    arguments={"query": search_query, "reason": "Forced search for price/current data query"}
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

                    # Check if LLM included citations (for monitoring)
                    had_citations = any(marker in llm_answer for marker in ["🔍 Sources:", "Sources:", "**Sources:**"])

                    # Strip any LLM-generated citations (anti-hallucination defense)
                    llm_answer = self._strip_hallucinated_citations(llm_answer)

                    # Log violation for monitoring
                    if had_citations:
                        logger.warning(f"[Anti-Hallucination] LLM ignored citation instruction - stripped and replaced with verified citations")

                    # Auto-generate accurate citations from search results
                    accurate_citations = self._auto_generate_citations(search_results)

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

                # Check if LLM included citations (for monitoring)
                had_citations = any(marker in llm_answer for marker in ["🔍 Sources:", "Sources:", "**Sources:**"])

                # Strip any LLM-generated citations (anti-hallucination defense)
                llm_answer = self._strip_hallucinated_citations(llm_answer)

                # Log violation for monitoring
                if had_citations:
                    logger.warning(f"[Anti-Hallucination] LLM ignored citation instruction - stripped and replaced with verified citations")

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
