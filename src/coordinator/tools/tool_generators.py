# src/coordinator/tools/tool_generators.py
# Tool definition generators for LLM function calling
# Provides OpenAI-compatible function definitions for Brave Search, MongoDB, and bot state tools

from __future__ import annotations

from typing import Dict, List, Any

from .token_registry import get_supported_token_list


# ── Token enum for tool definitions ──
_TOKEN_ENUM = get_supported_token_list()


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
    Returns all semantic MongoDB tool definitions for crypto trading data.

    These are high-level tools that abstract MongoDB query complexity.
    Supports 13 tokens across 3 timeframes.
    """
    return [
        get_crypto_current_price_tool(),
        get_crypto_historical_prices_tool(),
        get_crypto_trading_summary_tool(),
        get_crypto_technical_analysis_tool(),
    ]


def get_bot_state_tools() -> List[Dict[str, Any]]:
    """Returns bot state tool definitions for trading bot monitoring."""
    return [
        get_bot_status_tool(),
        get_bot_positions_tool(),
        get_bot_trade_history_tool(),
    ]


def get_crypto_current_price_tool() -> Dict[str, Any]:
    """Get current price with technical indicators for any supported cryptocurrency."""
    return {
        "type": "function",
        "function": {
            "name": "crypto_current_price",
            "description": (
                "Get the CURRENT price with key technical indicators for any supported cryptocurrency. "
                "Supports 13 tokens: BTC, ETH, SOL, XRP, ADA, AVAX, BNB, DOGE, DOT, LINK, NEAR, SUI, TON. "
                "Data updates hourly. "
                "Use this when user asks about:\n"
                "- Current/latest price of any crypto\n"
                "- Current technical indicators (RSI, MACD, Bollinger Bands)\n"
                "- Current market conditions\n\n"
                "Returns: price, timestamp, RSI, MACD, Bollinger Bands, EMAs, volume, extended indicators"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "token": {
                        "type": "string",
                        "enum": _TOKEN_ENUM,
                        "description": "Token ticker symbol (lowercase)"
                    },
                    "timeframe": {
                        "type": "string",
                        "enum": ["1h", "4h", "daily"],
                        "description": "Data timeframe. Default: 1h"
                    },
                    "include_indicators": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional list of specific indicators to return. "
                            "Available: RSI, MACD_Line, MACD_Signal, BB_High, BB_Low, "
                            "EMA_20, EMA_50, EMA_100, SMA_50, SMA_100, ADX_14, "
                            "Supertrend_Direction, FnG_Value, VWAP, CCI_20, MFI_14"
                        )
                    },
                    "reason": {
                        "type": "string",
                        "description": "REQUIRED: Brief explanation of why you need this data (1 sentence)"
                    }
                },
                "required": ["token", "reason"]
            }
        }
    }


def get_crypto_historical_prices_tool() -> Dict[str, Any]:
    """Query historical price data with date range for any supported token."""
    return {
        "type": "function",
        "function": {
            "name": "crypto_historical_prices",
            "description": (
                "Query HISTORICAL price data with date range for any supported cryptocurrency. "
                "Supports 13 tokens across 1h, 4h, and daily timeframes. "
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
                    "token": {
                        "type": "string",
                        "enum": _TOKEN_ENUM,
                        "description": "Token ticker symbol (lowercase)"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (e.g., '2024-01-01')"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format. Defaults to today."
                    },
                    "timeframe": {
                        "type": "string",
                        "enum": ["1h", "4h", "daily"],
                        "description": "Data granularity: '1h' (recent), '4h' (mid-term), 'daily' (long-term)"
                    },
                    "reason": {
                        "type": "string",
                        "description": "REQUIRED: Why you need historical data (1 sentence)"
                    }
                },
                "required": ["token", "start_date", "reason"]
            }
        }
    }


def get_crypto_trading_summary_tool() -> Dict[str, Any]:
    """Get DCA trading statistics (BTC only — other tokens return graceful message)."""
    return {
        "type": "function",
        "function": {
            "name": "crypto_trading_summary",
            "description": (
                "Get summary statistics for DCA (Dollar Cost Averaging) purchases. "
                "NOTE: DCA data is currently only available for Bitcoin (BTC). "
                "For other tokens, returns a message indicating no DCA data. "
                "Use this when user asks about:\n"
                "- How much crypto was bought\n"
                "- Total spending\n"
                "- Purchase history\n"
                "- Average buy price\n"
                "- Trading statistics\n\n"
                "Returns: total purchased, total spent, fees, average price, number of purchases"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "token": {
                        "type": "string",
                        "enum": _TOKEN_ENUM,
                        "description": "Token ticker symbol (lowercase)"
                    },
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
                "required": ["token", "reason"]
            }
        }
    }


def get_crypto_technical_analysis_tool() -> Dict[str, Any]:
    """Multi-timeframe technical analysis for any supported token."""
    return {
        "type": "function",
        "function": {
            "name": "crypto_technical_analysis",
            "description": (
                "Get comprehensive technical analysis with trend, momentum, volatility, and sentiment indicators. "
                "Supports 13 tokens across 1h, 4h, and daily timeframes. "
                "Includes 80 indicators: RSI, MACD, Bollinger Bands, ADX, Supertrend, Squeeze, "
                "Fear & Greed, VWAP, Fibonacci, Ichimoku, and more. "
                "Use this when user asks about:\n"
                "- Technical analysis\n"
                "- Market indicators\n"
                "- Trading signals\n"
                "- Trend analysis\n\n"
                "Returns: detailed indicator analysis with interpretations"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "token": {
                        "type": "string",
                        "enum": _TOKEN_ENUM,
                        "description": "Token ticker symbol (lowercase)"
                    },
                    "timeframe": {
                        "type": "string",
                        "enum": ["hourly", "4h", "daily"],
                        "description": "Analysis timeframe: 'hourly' for short-term, '4h' for mid-term, 'daily' for long-term"
                    },
                    "reason": {
                        "type": "string",
                        "description": "REQUIRED: Why you need technical analysis (1 sentence)"
                    }
                },
                "required": ["token", "reason"]
            }
        }
    }


def get_bot_status_tool() -> Dict[str, Any]:
    """Get trading bot strategy states."""
    return {
        "type": "function",
        "function": {
            "name": "bot_status",
            "description": (
                "Get the current status of all trading bot strategies. "
                "Shows which strategies are active, their last processed timestamp, "
                "entry/exit signals, and waiting states. "
                "Use when user asks about bot status, strategy state, or 'what is my bot doing'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "REQUIRED: Why you need bot status (1 sentence)"
                    }
                },
                "required": ["reason"]
            }
        }
    }


def get_bot_positions_tool() -> Dict[str, Any]:
    """Get open bot positions."""
    return {
        "type": "function",
        "function": {
            "name": "bot_positions",
            "description": (
                "Get all currently open positions held by the trading bot. "
                "Shows entry price, size, stop loss, and take profit levels. "
                "Use when user asks about open positions or active trades."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "REQUIRED: Why you need position data (1 sentence)"
                    }
                },
                "required": ["reason"]
            }
        }
    }


def get_bot_trade_history_tool() -> Dict[str, Any]:
    """Get recent bot trade events."""
    return {
        "type": "function",
        "function": {
            "name": "bot_trade_history",
            "description": (
                "Get recent trade events from the trading bot (entries and exits). "
                "Shows strategy, symbol, event type, filled price, size, fees, "
                "stop loss, and take profit for each trade. "
                "Use when user asks about recent bot trades, trade history, or bot performance."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of trade events to return (default 20, max 50)"
                    },
                    "reason": {
                        "type": "string",
                        "description": "REQUIRED: Why you need trade history (1 sentence)"
                    }
                },
                "required": ["reason"]
            }
        }
    }


# Tool registry
AVAILABLE_TOOLS = {
    "brave_web_search": get_brave_search_tool(),
    "crypto_current_price": get_crypto_current_price_tool(),
    "crypto_historical_prices": get_crypto_historical_prices_tool(),
    "crypto_trading_summary": get_crypto_trading_summary_tool(),
    "crypto_technical_analysis": get_crypto_technical_analysis_tool(),
    "bot_status": get_bot_status_tool(),
    "bot_positions": get_bot_positions_tool(),
    "bot_trade_history": get_bot_trade_history_tool(),
}
