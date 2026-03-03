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
