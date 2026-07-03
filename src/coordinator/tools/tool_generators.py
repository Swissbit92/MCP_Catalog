# src/coordinator/tools/tool_generators.py
# Tool definition generators for LLM function calling
# Provides OpenAI-compatible function definitions for Brave Search

from __future__ import annotations

from typing import Dict, Any


def get_brave_search_tool() -> Dict[str, Any]:
    """
    Returns the Brave web search tool definition in OpenAI format.

    This format is compatible with most LLMs that support function calling.
    """
    return {
        "type": "function",
        "function": {
            "name": "brave_web_search",
            "description": (
                "Search the web for CURRENT or RECENT information using Brave Search API. "
                "Only use this when you need information that is:\n"
                "- Current/recent (prices, news, events from 2024-2025)\n"
                "- Time-sensitive (weather, stock prices, election results)\n"
                "- Not in your training data (recent developments)\n\n"
                "DO NOT use for:\n"
                "- Math calculations (2+2, percentages, etc.)\n"
                "- Definitions of common terms (blockchain, API, etc.)\n"
                "- General knowledge (history, geography, basic concepts)\n"
                "- How-to questions that don't need current data"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to execute. Be specific and concise."
                    },
                    "reason": {
                        "type": "string",
                        "description": "Brief reason why web search is needed (for logging)"
                    }
                },
                "required": ["query"]
            }
        }
    }


# Tool registry
AVAILABLE_TOOLS = {
    "brave_web_search": get_brave_search_tool(),
}
