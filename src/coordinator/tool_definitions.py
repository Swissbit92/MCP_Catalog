# src/coordinator/tool_definitions.py
# BACKWARD COMPATIBILITY WRAPPER
# This file re-exports all functions from the modular tools/ package
# to maintain compatibility with existing code that imports from tool_definitions.py

from __future__ import annotations

# Re-export keyword dictionaries
from .tools.keywords import (
    NO_SEARCH_KEYWORDS,
    SEARCH_KEYWORDS,
    MONGODB_PRICE_KEYWORDS,
    MONGODB_HISTORICAL_KEYWORDS,
    MONGODB_TRADING_KEYWORDS,
    MONGODB_TECHNICAL_KEYWORDS,
)

# Re-export intent classifier
from .tools.intent_classifier import (
    QueryIntent,
    classify_query_intent,
)

# Re-export tool generators
from .tools.tool_generators import (
    get_brave_search_tool,
    get_mongodb_tools,
    get_bitcoin_current_price_tool,
    get_bitcoin_historical_prices_tool,
    get_bitcoin_trading_summary_tool,
    get_bitcoin_technical_analysis_tool,
    AVAILABLE_TOOLS,
)

# Re-export synthesis prompts
from .tools.synthesis_prompts import (
    build_tool_system_prompt,
    build_synthesis_prompt,
    build_mongodb_synthesis_prompt,
)

# Re-export utility functions
from .tools.tool_utils import (
    ToolCall,
    should_use_keyword_filter,
    parse_tool_call,
    format_search_results_for_llm,
    get_tools_for_persona,
    get_tools_for_query,
)


# Example usage and testing
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
