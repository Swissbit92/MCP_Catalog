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

        # Pre-filter with keywords to reduce false positives
        keyword_decision = should_use_keyword_filter(user_prompt)
        if keyword_decision is False:
            logger.info(f"Keyword filter: NO SEARCH needed for query: '{user_prompt[:100]}'")
            response = self.complete(persona_system, user_prompt)
            return (response, None, None)

        if keyword_decision is True:
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
                return (response, None, None)

            # Tool call detected
            logger.info(f"Tool call detected: {tool_call.name}({list(tool_call.arguments.keys())})")

            if tool_call.name == "brave_web_search":
                # Execute web search
                search_results = self._execute_brave_search(tool_call)

                if not search_results:
                    logger.warning("Web search returned no results")
                    # Ask LLM to answer without search results
                    conversation_history.append(f"Tool call failed (no results). Please answer the question directly.")
                    continue

                # Format search results for LLM
                formatted_results = format_search_results_for_llm(search_results)
                logger.info(f"Formatted {len(search_results)} search results for LLM")

                # Add results to conversation and ask LLM to synthesize
                conversation_history.append(formatted_results)
                conversation_history.append(f"User: {user_prompt}")

                # Get final synthesized response
                final_response = self.complete(
                    persona_system,  # Use original persona prompt
                    "\n\n".join(conversation_history)
                )

                logger.info("Final response with search results generated")
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
