# src/coordinator/tools/__init__.py
# Tools package for LLM function calling and intent classification
# This package provides modular components for:
# - Query intent classification (MongoDB, Brave Search, or neither)
# - Tool definition generation (OpenAI-compatible function definitions)
# - Synthesis prompt building (anti-hallucination, persona voice preservation)
# - Tool calling utilities (parsing, formatting, routing)

from __future__ import annotations

# Keyword dictionaries for intent classification
from .keywords import (
    NO_SEARCH_KEYWORDS,
    SEARCH_KEYWORDS,
    MONGODB_PRICE_KEYWORDS,
    MONGODB_HISTORICAL_KEYWORDS,
    MONGODB_TRADING_KEYWORDS,
    MONGODB_TECHNICAL_KEYWORDS,
)

# Intent classifier
from .intent_classifier import (
    QueryIntent,
    classify_query_intent,
)

# Tool generators
from .tool_generators import (
    get_brave_search_tool,
    get_mongodb_tools,
    get_bot_state_tools,
    get_crypto_current_price_tool,
    get_crypto_historical_prices_tool,
    get_crypto_trading_summary_tool,
    get_crypto_technical_analysis_tool,
    get_bot_status_tool,
    get_bot_positions_tool,
    get_bot_trade_history_tool,
    AVAILABLE_TOOLS,
)

# Synthesis prompts
from .synthesis_prompts import (
    build_tool_system_prompt,
    build_synthesis_prompt,
    build_mongodb_synthesis_prompt,
)

# Utility functions
from .tool_utils import (
    ToolCall,
    should_use_keyword_filter,
    parse_tool_call,
    format_search_results_for_llm,
    get_tools_for_persona,
    get_tools_for_query,
)

__all__ = [
    # Keywords
    "NO_SEARCH_KEYWORDS",
    "SEARCH_KEYWORDS",
    "MONGODB_PRICE_KEYWORDS",
    "MONGODB_HISTORICAL_KEYWORDS",
    "MONGODB_TRADING_KEYWORDS",
    "MONGODB_TECHNICAL_KEYWORDS",
    # Intent
    "QueryIntent",
    "classify_query_intent",
    # Tool generators
    "get_brave_search_tool",
    "get_mongodb_tools",
    "get_bot_state_tools",
    "get_crypto_current_price_tool",
    "get_crypto_historical_prices_tool",
    "get_crypto_trading_summary_tool",
    "get_crypto_technical_analysis_tool",
    "get_bot_status_tool",
    "get_bot_positions_tool",
    "get_bot_trade_history_tool",
    "AVAILABLE_TOOLS",
    # Synthesis prompts
    "build_tool_system_prompt",
    "build_synthesis_prompt",
    "build_mongodb_synthesis_prompt",
    # Utils
    "ToolCall",
    "should_use_keyword_filter",
    "parse_tool_call",
    "format_search_results_for_llm",
    "get_tools_for_persona",
    "get_tools_for_query",
]
