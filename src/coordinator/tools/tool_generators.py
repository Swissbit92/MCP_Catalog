# src/coordinator/tools/tool_generators.py
# Tool definition generators for LLM function calling
# Provides OpenAI-compatible function definitions for Brave Search and MongoDB tools

from __future__ import annotations

from typing import Dict, List, Any


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


# Tool registry
AVAILABLE_TOOLS = {
    "brave_web_search": get_brave_search_tool(),
    "bitcoin_current_price": get_bitcoin_current_price_tool(),
    "bitcoin_historical_prices": get_bitcoin_historical_prices_tool(),
    "bitcoin_trading_summary": get_bitcoin_trading_summary_tool(),
    "bitcoin_technical_analysis": get_bitcoin_technical_analysis_tool()
}
