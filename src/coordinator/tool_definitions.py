# src/coordinator/tool_definitions.py
# Tool definitions and prompting strategies for LLM function calling
# Includes improved prompting to reduce false positives
# MongoDB MCP integration with 3-layer intent classification

from __future__ import annotations

import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

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

    # Market/price data (general web search, not MongoDB)
    "stock market", "nasdaq", "dow jones", "s&p 500",

    # Events
    "election", "vote", "results", "winner", "outcome", "happened",

    # Weather/conditions
    "weather", "temperature", "forecast", "climate",

    # Trending/popularity (NEW - Priority 1 improvements)
    "trending", "trend", "popular", "viral", "hot topic", "buzz",

    # Happening/current events (NEW)
    "happening", "occurring", "going on", "what's new", "new with",
    "latest on", "developments", "progress",

    # Expert opinions/predictions (NEW)
    "saying", "experts say", "analysts say", "predictions",
    "forecasts", "outlook", "opinions", "views", "thoughts on",
    "expect", "expecting", "anticipated",

    # Social/community sentiment (NEW)
    "talking about", "discussing", "debate", "community",
    "twitter", "reddit", "social", "sentiment", "mood", "feeling about",

    # Market commentary (NEW)
    "commentary", "analysis article", "opinion piece",
    "market watch", "crypto watch"
}

# MongoDB-specific keywords for Bitcoin/crypto data
MONGODB_PRICE_KEYWORDS = {
    "bitcoin price", "btc price", "price of bitcoin", "current price",
    "bitcoin cost", "btc cost", "how much is bitcoin", "bitcoin value",

    # Value/worth (NEW - Priority 1 improvements)
    "value", "valued", "valued at", "worth", "worth now",
    "what's it worth", "how much is",

    # Trading phrases (NEW)
    "trading at", "trading for", "trades at", "going for",
    "selling for", "cost", "costs",

    # Current state (NEW)
    "current value", "right now", "at the moment", "as of", "currently"
}

MONGODB_HISTORICAL_KEYWORDS = {
    "price history", "historical price", "past price", "was the price",
    "price on", "price in", "price over time", "price trend",

    # Historical data (NEW)
    "historical", "history", "past", "ago", "was", "were", "been"
}

MONGODB_TRADING_KEYWORDS = {
    "bought", "purchased", "dca", "dollar cost averaging", "trading stats",
    "my portfolio", "my bitcoin", "total btc", "how much btc",
    "purchase history", "buy history",

    # Personal queries (NEW)
    "my", "mine", "portfolio", "holdings"
}

MONGODB_TECHNICAL_KEYWORDS = {
    "rsi", "macd", "bollinger", "bollinger bands", "technical indicator",
    "ema", "sma", "moving average", "stochastic", "ichimoku",
    "technical analysis", "chart analysis", "indicators",

    # Analysis/outlook (NEW)
    "analysis", "trend analysis", "outlook", "technical outlook",
    "market analysis", "signals"
}


class QueryIntent(Enum):
    """Query intent classification for MCP routing."""
    NEEDS_WEB_SEARCH = "web"      # Brave MCP
    NEEDS_MONGODB = "mongodb"      # MongoDB MCP
    NEEDS_BOTH = "both"            # Multi-MCP
    NEEDS_NEITHER = "llm"          # Pure LLM


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


def classify_query_intent(query: str, persona_rarity: str) -> QueryIntent:
    """
    Layer 1: Fast keyword-based intent classification for MCP routing.

    Args:
        query: User query string
        persona_rarity: Persona rarity level (common, rare, epic, legendary)

    Returns:
        QueryIntent enum indicating which MCP(s) to use
    """
    query_lower = query.lower()

    # Check rarity permissions
    can_use_mongodb = persona_rarity.lower() in {"epic", "legendary"}
    can_use_brave = persona_rarity.lower() in {"rare", "epic", "legendary"}

    # Check for definition/math keywords (NO MCP needed)
    # But allow queries that are asking for prices/values/opinions/web data despite having "what is/are"
    has_definition_intent = any(kw in query_lower for kw in NO_SEARCH_KEYWORDS)

    # Educational queries that mention Bitcoin but aren't asking for data
    educational_phrases = ["why was", "how does", "how do i", "how to", "what does", "who is", "who was"]
    is_educational = any(phrase in query_lower for phrase in educational_phrases)

    # Opinion/sentiment queries should NOT be blocked by definition intent
    opinion_keywords = ["saying", "think", "believe", "opinion", "sentiment", "talking about", "experts say", "analysts"]
    has_opinion_intent = any(kw in query_lower for kw in opinion_keywords)

    # Check if query needs web search despite having definition keywords
    has_web_search_intent = any(kw in query_lower for kw in SEARCH_KEYWORDS)

    # Check if query is asking for data despite having definition keywords
    data_keywords = ["price", "value", "worth", "cost", "indicator"]
    has_data_intent = any(kw in query_lower for kw in data_keywords)

    if has_definition_intent and not has_opinion_intent and not has_data_intent and not has_web_search_intent:
        # Pure educational/definition queries don't need MCPs
        return QueryIntent.NEEDS_NEITHER

    if is_educational and not has_opinion_intent and not has_web_search_intent:
        # Educational queries like "Why was Bitcoin created?" should not trigger MCPs
        return QueryIntent.NEEDS_NEITHER

    # Check MongoDB triggers first (highest priority for Bitcoin queries)
    # Detect MongoDB intent BEFORE checking rarity permissions
    has_mongodb_intent = False
    if "bitcoin" in query_lower or "btc" in query_lower:
        # Check specific MongoDB keyword groups
        if any(kw in query_lower for kw in MONGODB_PRICE_KEYWORDS):
            has_mongodb_intent = True
        elif any(kw in query_lower for kw in MONGODB_HISTORICAL_KEYWORDS):
            has_mongodb_intent = True
        elif any(kw in query_lower for kw in MONGODB_TRADING_KEYWORDS):
            has_mongodb_intent = True
        elif any(kw in query_lower for kw in MONGODB_TECHNICAL_KEYWORDS):
            has_mongodb_intent = True
        # Generic "price" with "bitcoin" also triggers MongoDB intent
        elif "price" in query_lower:
            has_mongodb_intent = True

    # Only grant MongoDB access if persona has permission
    needs_mongodb = has_mongodb_intent and can_use_mongodb

    # Check web search triggers
    needs_web = False
    # Don't fallback to web search for MongoDB queries when persona lacks access
    can_fallback_to_web = not (has_mongodb_intent and not can_use_mongodb)

    # Allow web search if: no definition intent, OR has opinion intent, OR has web search keywords
    if can_use_brave and can_fallback_to_web and (not has_definition_intent or has_opinion_intent or has_web_search_intent):
        # Bitcoin news/articles need web search, NOT MongoDB
        if ("bitcoin" in query_lower or "btc" in query_lower) and any(word in query_lower for word in ["news", "article", "report", "announcement"]):
            needs_web = True
            # If query also asks for price AND news, keep both
            if not ("price" in query_lower or "cost" in query_lower):
                needs_mongodb = False  # News only = web only

        # General web search keywords (but not if MongoDB already triggered for Bitcoin price)
        elif not needs_mongodb:
            if any(kw in query_lower for kw in SEARCH_KEYWORDS):
                needs_web = True

        # "current" in Bitcoin context means MongoDB, not web search
        if needs_mongodb and "current" in query_lower and "bitcoin" in query_lower:
            # Check if it's asking for current price data (MongoDB)
            # vs current news/events (web)
            if "news" not in query_lower and "article" not in query_lower:
                needs_web = False  # Current price data, not current news

    # Return intent
    if needs_mongodb and needs_web:
        return QueryIntent.NEEDS_BOTH
    elif needs_mongodb:
        return QueryIntent.NEEDS_MONGODB
    elif needs_web:
        return QueryIntent.NEEDS_WEB_SEARCH
    elif has_mongodb_intent and not can_use_mongodb:
        # MongoDB query detected but persona doesn't have access
        # Don't fallback to web search - return NEITHER
        return QueryIntent.NEEDS_NEITHER
    else:
        return QueryIntent.NEEDS_NEITHER


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


def get_mongodb_tools() -> List[Dict[str, Any]]:
    """
    Returns all semantic MongoDB tool definitions for Bitcoin trading data.

    These are high-level tools that abstract MongoDB query complexity.
    """
    return [
        get_bitcoin_current_price_tool(),
        get_bitcoin_historical_prices_tool(),
        get_bitcoin_trading_summary_tool(),
        get_bitcoin_technical_analysis_tool()
    ]


def get_bitcoin_current_price_tool() -> Dict[str, Any]:
    """Get current Bitcoin price with key technical indicators."""
    return {
        "type": "function",
        "function": {
            "name": "bitcoin_current_price",
            "description": (
                "Get the CURRENT Bitcoin price with key technical indicators from our trading database. "
                "Data updates hourly. "
                "Use this when user asks about:\n"
                "- Current/latest Bitcoin price\n"
                "- Current technical indicators (RSI, MACD, Bollinger Bands)\n"
                "- Current market conditions\n\n"
                "Returns: price, timestamp, RSI, MACD, Bollinger Bands, EMAs, volume"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "include_indicators": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional list of specific indicators to return. "
                            "Available: RSI, MACD_Line, MACD_Signal, BB_High, BB_Low, "
                            "EMA_20, EMA_50, EMA_100, SMA_50, SMA_100, Stoch_RSI"
                        )
                    },
                    "reason": {
                        "type": "string",
                        "description": "REQUIRED: Brief explanation of why you need this data (1 sentence)"
                    }
                },
                "required": ["reason"]
            }
        }
    }


def get_bitcoin_historical_prices_tool() -> Dict[str, Any]:
    """Query historical Bitcoin price data with date range."""
    return {
        "type": "function",
        "function": {
            "name": "bitcoin_historical_prices",
            "description": (
                "Query Bitcoin HISTORICAL price data with date range. "
                "Available data: 2016-07-18 to present (9+ years). "
                "Use this when user asks about:\n"
                "- Historical prices (past data)\n"
                "- Price trends over time\n"
                "- Specific date ranges\n"
                "- Comparing prices across periods\n\n"
                "Returns: OHLCV data and optional technical indicators for the date range"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (e.g., '2024-01-01')"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (e.g., '2024-12-31'). Defaults to today."
                    },
                    "timeframe": {
                        "type": "string",
                        "enum": ["hourly", "daily"],
                        "description": "Data granularity: 'hourly' (last 6 months) or 'daily' (2016-present)"
                    },
                    "reason": {
                        "type": "string",
                        "description": "REQUIRED: Why you need historical data (1 sentence)"
                    }
                },
                "required": ["start_date", "reason"]
            }
        }
    }


def get_bitcoin_trading_summary_tool() -> Dict[str, Any]:
    """Get DCA trading statistics."""
    return {
        "type": "function",
        "function": {
            "name": "bitcoin_trading_summary",
            "description": (
                "Get summary statistics for Bitcoin DCA (Dollar Cost Averaging) purchases. "
                "Use this when user asks about:\n"
                "- How much Bitcoin was bought\n"
                "- Total spending on Bitcoin\n"
                "- Purchase history\n"
                "- Average buy price\n"
                "- Trading statistics\n\n"
                "Returns: total BTC, total USDT spent, fees, average price, number of purchases"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Optional start date to filter purchases (YYYY-MM-DD)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Optional end date to filter purchases (YYYY-MM-DD)"
                    },
                    "reason": {
                        "type": "string",
                        "description": "REQUIRED: Why you need trading stats (1 sentence)"
                    }
                },
                "required": ["reason"]
            }
        }
    }


def get_bitcoin_technical_analysis_tool() -> Dict[str, Any]:
    """Multi-timeframe technical analysis."""
    return {
        "type": "function",
        "function": {
            "name": "bitcoin_technical_analysis",
            "description": (
                "Get comprehensive technical analysis with trend, momentum, and volatility indicators. "
                "Use this when user asks about:\n"
                "- Technical analysis\n"
                "- Market indicators (RSI, MACD, Bollinger Bands)\n"
                "- Trading signals\n"
                "- Trend analysis\n\n"
                "Returns: detailed indicator analysis with interpretations (RSI, MACD, BB, EMAs, Ichimoku)"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "timeframe": {
                        "type": "string",
                        "enum": ["hourly", "daily"],
                        "description": "Analysis timeframe: 'hourly' for short-term or 'daily' for long-term"
                    },
                    "reason": {
                        "type": "string",
                        "description": "REQUIRED: Why you need technical analysis (1 sentence)"
                    }
                },
                "required": ["reason"]
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
    "brave_web_search": get_brave_search_tool(),
    "bitcoin_current_price": get_bitcoin_current_price_tool(),
    "bitcoin_historical_prices": get_bitcoin_historical_prices_tool(),
    "bitcoin_trading_summary": get_bitcoin_trading_summary_tool(),
    "bitcoin_technical_analysis": get_bitcoin_technical_analysis_tool()
}


def get_tools_for_persona(persona_key: str, persona_rarity: str) -> List[Dict[str, Any]]:
    """
    Get available tools based on persona rarity (static approach).

    NOTE: For intent-based routing, use get_tools_for_query() instead.

    Args:
        persona_key: Persona identifier (e.g., "Eeva", "Frieren")
        persona_rarity: Persona rarity level ("common", "rare", "epic", "legendary")

    Returns:
        List of tool definitions
    """
    tools = []

    # Brave MCP: rare, epic, legendary
    if persona_rarity.lower() in {"rare", "epic", "legendary"}:
        tools.append(get_brave_search_tool())

    # MongoDB MCP: epic, legendary only
    if persona_rarity.lower() in {"epic", "legendary"}:
        tools.extend(get_mongodb_tools())

    return tools


def get_tools_for_query(query: str, persona_key: str, persona_rarity: str) -> List[Dict[str, Any]]:
    """
    Layer 2: Dynamic tool injection based on query intent.

    This is the recommended approach - only inject relevant tools for the specific query.

    Args:
        query: User query string
        persona_key: Persona identifier
        persona_rarity: Persona rarity level

    Returns:
        List of tool definitions relevant to this specific query
    """
    intent = classify_query_intent(query, persona_rarity)

    tools = []

    if intent == QueryIntent.NEEDS_WEB_SEARCH:
        tools.append(get_brave_search_tool())

    elif intent == QueryIntent.NEEDS_MONGODB:
        tools.extend(get_mongodb_tools())

    elif intent == QueryIntent.NEEDS_BOTH:
        tools.append(get_brave_search_tool())
        tools.extend(get_mongodb_tools())

    # QueryIntent.NEEDS_NEITHER → empty tools list

    return tools


# Example usage
if __name__ == "__main__":
    print("Testing Intent Classification")
    print("=" * 80)

    # Test queries with expected intents
    test_cases = [
        # MongoDB queries (Epic persona)
        ("What's the current Bitcoin price?", "epic", QueryIntent.NEEDS_MONGODB),
        ("Show me Bitcoin's RSI and MACD", "epic", QueryIntent.NEEDS_MONGODB),
        ("How much Bitcoin have I bought?", "epic", QueryIntent.NEEDS_MONGODB),
        ("What was Bitcoin price in January 2024?", "epic", QueryIntent.NEEDS_MONGODB),

        # Web search queries (Rare persona)
        ("Latest Bitcoin news", "rare", QueryIntent.NEEDS_WEB_SEARCH),
        ("What happened in the 2024 election?", "rare", QueryIntent.NEEDS_WEB_SEARCH),
        ("Who won the election?", "rare", QueryIntent.NEEDS_WEB_SEARCH),

        # No MCP needed (any persona)
        ("What is Bitcoin?", "epic", QueryIntent.NEEDS_NEITHER),
        ("Explain blockchain technology", "epic", QueryIntent.NEEDS_NEITHER),
        ("What is 2 + 2?", "epic", QueryIntent.NEEDS_NEITHER),
        ("How does mining work?", "epic", QueryIntent.NEEDS_NEITHER),

        # Multi-MCP (needs both)
        ("What's the Bitcoin price and recent news?", "epic", QueryIntent.NEEDS_BOTH),

        # Permission-based blocking
        ("What's the Bitcoin price?", "common", QueryIntent.NEEDS_NEITHER),  # No MongoDB access
        ("Latest news", "common", QueryIntent.NEEDS_NEITHER),  # No Brave access
    ]

    passed = 0
    failed = 0

    for query, rarity, expected_intent in test_cases:
        result = classify_query_intent(query, rarity)
        status = "[OK]" if result == expected_intent else "[FAIL]"

        if result == expected_intent:
            passed += 1
        else:
            failed += 1

        print(f"{status} Query: '{query}'")
        print(f"      Rarity: {rarity}, Expected: {expected_intent.value}, Got: {result.value}")
        print()

    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed")

    # Test tool injection
    print("\n" + "=" * 80)
    print("Testing Dynamic Tool Injection")
    print("=" * 80)

    test_query = "What's the current Bitcoin price?"
    tools = get_tools_for_query(test_query, "Eeva", "epic")
    print(f"\nQuery: '{test_query}'")
    print(f"Persona: Eeva (Epic)")
    print(f"Tools injected: {[tool['function']['name'] for tool in tools]}")
    print(f"Tool count: {len(tools)}")

    test_query2 = "Explain what Bitcoin is"
    tools2 = get_tools_for_query(test_query2, "Eeva", "epic")
    print(f"\nQuery: '{test_query2}'")
    print(f"Persona: Eeva (Epic)")
    print(f"Tools injected: {[tool['function']['name'] for tool in tools2]}")
    print(f"Tool count: {len(tools2)} (should be 0 - no MCP needed)")
