# src/coordinator/tools/tool_utils.py
# Utility functions for tool calling, search result formatting, and query routing
# Supports both static persona-based and dynamic intent-based tool injection

from __future__ import annotations

import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .keywords import NO_SEARCH_KEYWORDS, SEARCH_KEYWORDS
from .intent_classifier import QueryIntent, classify_query_intent
from .tool_generators import (
    get_brave_search_tool,
    get_mongodb_tools,
)


@dataclass
class ToolCall:
    """Represents a function call from the LLM."""
    name: str
    arguments: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "arguments": self.arguments
        }


def should_use_keyword_filter(query: str) -> Optional[bool]:
    """
    Quick keyword-based filter to prevent obvious false positives.

    Returns:
        True: Should search (has search keywords)
        False: Should NOT search (has no-search keywords)
        None: Uncertain, let LLM decide
    """
    query_lower = query.lower()

    # Check for no-search keywords
    for keyword in NO_SEARCH_KEYWORDS:
        if keyword in query_lower:
            # Exception: if also has search keywords, let LLM decide
            has_search_keyword = any(kw in query_lower for kw in SEARCH_KEYWORDS)
            if not has_search_keyword:
                return False

    # Check for search keywords
    for keyword in SEARCH_KEYWORDS:
        if keyword in query_lower:
            return True

    # No strong signal, let LLM decide
    return None


def parse_tool_call(response: str) -> Optional[ToolCall]:
    """
    Parse LLM response for function call.

    Args:
        response: Raw LLM response text

    Returns:
        ToolCall if found, None otherwise
    """
    # Try to find JSON in response
    try:
        # Check if entire response is JSON
        if response.strip().startswith('{'):
            data = json.loads(response)
            if "function_call" in data:
                fc = data["function_call"]
                return ToolCall(
                    name=fc["name"],
                    arguments=fc.get("arguments", {})
                )
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from text
    json_pattern = r'\{[^{}]*"function_call"[^{}]*\{[^{}]*\}[^{}]*\}'
    match = re.search(json_pattern, response, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if "function_call" in data:
                fc = data["function_call"]
                return ToolCall(
                    name=fc["name"],
                    arguments=fc.get("arguments", {})
                )
        except json.JSONDecodeError:
            pass

    return None


def format_search_results_for_llm(results: List[Any], max_results: int = 5) -> str:
    """
    Format search results for LLM context.

    Args:
        results: List of SearchResult objects from mcp_client
        max_results: Maximum number of results to include

    Returns:
        Formatted string with search results
    """
    if not results:
        return "No search results found."

    formatted = "Web search results:\n\n"

    for i, result in enumerate(results[:max_results], 1):
        formatted += f"{i}. {result.title}\n"
        formatted += f"   URL: {result.url}\n"
        formatted += f"   {result.description}\n"
        if hasattr(result, 'age') and result.age:
            formatted += f"   Published: {result.age}\n"
        formatted += "\n"

    formatted += (
        "\nIMPORTANT: Use this information to answer the user's question. "
        "You MUST cite your sources using markdown links at the end of your response:\n\n"
        "🔍 Sources:\n"
        "• [Title - Source Name](URL)\n"
    )

    return formatted


def get_tools_for_persona(
    persona_key: str,
    persona_rarity: str,
    mcp_access: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Get available tools based on persona rarity or explicit mcp_access (static approach).

    NOTE: For intent-based routing, use get_tools_for_query() instead.

    Args:
        persona_key: Persona identifier (e.g., "Eeva", "Frieren")
        persona_rarity: Persona rarity level ("common", "rare", "epic", "legendary")
        mcp_access: Optional explicit list of allowed MCP services from the persona
                    JSON ``mcp_access`` field.  When provided, overrides rarity gating.

    Returns:
        List of tool definitions
    """
    tools = []

    if mcp_access is not None:
        # Per-persona MCP access (from persona JSON mcp_access field)
        if "brave_search" in mcp_access:
            tools.append(get_brave_search_tool())
        if "mongodb" in mcp_access:
            tools.extend(get_mongodb_tools())
        if "solana_wallet" in mcp_access:
            from .wallet_tool_generators import get_wallet_tools
            tools.extend(get_wallet_tools())
    else:
        # Fallback to rarity-based access for personas without mcp_access field
        # Brave MCP: rare, epic, legendary
        if persona_rarity.lower() in {"rare", "epic", "legendary"}:
            tools.append(get_brave_search_tool())
        # MongoDB MCP: epic, legendary only
        if persona_rarity.lower() in {"epic", "legendary"}:
            tools.extend(get_mongodb_tools())

    return tools


def get_tools_for_query(
    query: str,
    persona_key: str,
    persona_rarity: str,
    mcp_access: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Layer 2: Dynamic tool injection based on query intent.

    This is the recommended approach - only inject relevant tools for the specific query.

    Args:
        query: User query string
        persona_key: Persona identifier
        persona_rarity: Persona rarity level
        mcp_access: Optional explicit list of allowed MCP services from the persona
                    JSON ``mcp_access`` field.  When provided, overrides rarity gating.

    Returns:
        List of tool definitions relevant to this specific query
    """
    intent = classify_query_intent(query, persona_rarity, mcp_access=mcp_access)

    tools = []

    if intent == QueryIntent.NEEDS_WEB_SEARCH:
        tools.append(get_brave_search_tool())

    elif intent == QueryIntent.NEEDS_MONGODB:
        tools.extend(get_mongodb_tools())

    elif intent == QueryIntent.NEEDS_BOTH:
        tools.append(get_brave_search_tool())
        tools.extend(get_mongodb_tools())

    elif intent == QueryIntent.NEEDS_WALLET:
        from .wallet_tool_generators import get_wallet_tools
        tools.extend(get_wallet_tools())

    # QueryIntent.NEEDS_NEITHER → empty tools list

    return tools
