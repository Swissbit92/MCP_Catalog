# src/coordinator/tool_definitions.py
# Tool definitions and prompting strategies for LLM function calling
# Includes improved prompting to reduce false positives

from __future__ import annotations

import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Keywords that indicate NO web search needed
NO_SEARCH_KEYWORDS = {
    # Math/calculations
    "calculate", "compute", "what is", "plus", "minus", "multiply", "divide",
    "addition", "subtraction", "multiplication", "division", "equals",

    # Definitions/explanations
    "define", "definition", "what does", "meaning of", "explain what",
    "what are", "what is a", "explain the concept",

    # How-to (general knowledge)
    "how to", "how do i", "how does", "how can i",

    # Common knowledge
    "who is", "who was", "what was", "where is", "when was",
    "capital of", "president of", "history of"
}

# Keywords that indicate web search IS needed
SEARCH_KEYWORDS = {
    # Current/recent information
    "current", "latest", "recent", "today", "now", "this week", "this month",
    "2024", "2025", "breaking", "update", "news",

    # Market/price data
    "price", "cost", "worth", "value", "market", "stock", "crypto",

    # Events
    "election", "vote", "results", "winner", "outcome", "happened",

    # Weather/conditions
    "weather", "temperature", "forecast", "climate"
}


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


def build_tool_system_prompt(persona_system: str, tools: List[Dict[str, Any]]) -> str:
    """
    Build enhanced system prompt with tool definitions and improved guidance.

    Args:
        persona_system: The persona's system prompt
        tools: List of available tools

    Returns:
        Enhanced system prompt with tool calling instructions
    """

    tools_json = json.dumps(tools, indent=2)

    prompt = f"""{persona_system}

---

You have access to the following tools:

{tools_json}

**TOOL USAGE GUIDELINES:**

When to use tools:
- ONLY for current/recent information (2024-2025 events, current prices, today's news)
- ONLY when the answer requires up-to-date data you don't have
- ONLY when explicitly about recent events or real-time data

When NOT to use tools (answer directly):
- Math or calculations (2+2, percentages, conversions)
- Definitions or explanations (What is X? How does Y work?)
- Historical facts in your training data (before 2023)
- General knowledge (capitals, basic science, common concepts)
- How-to questions (How do I learn Python?)
- Philosophical or opinion questions

**EXAMPLES:**

User: "What is the current price of Bitcoin?"
→ USE TOOL: brave_web_search(query="Bitcoin price December 2024")
Reason: Current price information

User: "What is 25% of 80?"
→ ANSWER DIRECTLY: "25% of 80 is 20."
Reason: Simple math, no tool needed

User: "Explain what blockchain is"
→ ANSWER DIRECTLY: [Your explanation]
Reason: General knowledge definition

User: "Who won the 2024 US election?"
→ USE TOOL: brave_web_search(query="2024 US presidential election winner")
Reason: Recent event

User: "What is the capital of France?"
→ ANSWER DIRECTLY: "The capital of France is Paris."
Reason: Common knowledge

**RESPONSE FORMAT:**

If using a tool, respond with JSON:
{{
  "function_call": {{
    "name": "tool_name",
    "arguments": {{"param": "value"}}
  }}
}}

If NOT using a tool, respond naturally in your persona voice.

**IMPORTANT:** Stay in character as your persona. If you search the web, incorporate results naturally into your response style."""

    return prompt


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


# Tool registry
AVAILABLE_TOOLS = {
    "brave_web_search": get_brave_search_tool()
}


def get_tools_for_persona(persona_key: str, persona_rarity: str) -> List[Dict[str, Any]]:
    """
    Get available tools based on persona rarity.

    Args:
        persona_key: Persona identifier (e.g., "Eeva", "Frieren")
        persona_rarity: Persona rarity level ("common", "rare", "epic", "legendary")

    Returns:
        List of tool definitions
    """
    # Only rare, epic, and legendary personas get web search
    enabled_rarities = {"rare", "epic", "legendary"}

    if persona_rarity.lower() in enabled_rarities:
        return [get_brave_search_tool()]

    return []


# Example usage
if __name__ == "__main__":
    # Test keyword filtering
    test_queries = [
        "What is 2 + 2?",  # Should be False
        "What is the current Bitcoin price?",  # Should be True
        "Explain blockchain technology",  # Should be False
        "What happened in the 2024 election?",  # Should be True
        "Who is the president of the USA?"  # Should be None (let LLM decide)
    ]

    print("Testing keyword filter:\n")
    for query in test_queries:
        result = should_use_keyword_filter(query)
        status = "SEARCH" if result is True else ("NO SEARCH" if result is False else "LET LLM DECIDE")
        print(f"  '{query}'\n  → {status}\n")

    # Test tool definition
    print("\nBrave search tool definition:")
    tool = get_brave_search_tool()
    print(json.dumps(tool, indent=2))
