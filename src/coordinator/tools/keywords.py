# src/coordinator/tools/keywords.py
"""Keyword dictionaries for intent classification and query routing."""

from __future__ import annotations

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
    "current", "latest", "recent", "today", "tomorrow", "now", "this week", "this month",
    "2024", "2025", "2026", "breaking", "update", "news",

    # Market/price data (general web search, not MongoDB)
    "stock market", "nasdaq", "dow jones", "s&p 500",

    # Events
    "election", "vote", "results", "winner", "outcome", "happened",

    # Weather/conditions
    "weather", "temperature", "forecast", "climate",

    # Trending/popularity
    "trending", "trend", "popular", "viral", "hot topic", "buzz",

    # Happening/current events
    "happening", "occurring", "going on", "what's new", "new with",
    "latest on", "developments", "progress",

    # Expert opinions/predictions
    "saying", "experts say", "analysts say", "analysts think", "analysts",
    "predictions", "forecasts", "outlook", "opinions", "views", "thoughts on",
    "expect", "expecting", "anticipated",

    # Social/community sentiment
    "talking about", "discussing", "debate", "community",
    "twitter", "reddit", "social", "sentiment", "mood", "feeling about",

    # Market commentary
    "commentary", "analysis article", "opinion piece",
    "market watch", "crypto watch"
}

# MongoDB-specific keywords for Bitcoin/crypto data
MONGODB_PRICE_KEYWORDS = {
    "bitcoin price", "btc price", "price of bitcoin", "current price",
    "bitcoin cost", "btc cost", "how much is bitcoin", "bitcoin value",

    # Value/worth
    "value", "valued", "valued at", "worth", "worth now",
    "what's it worth", "how much is",

    # Trading phrases
    "trading at", "trading for", "trades at", "going for",
    "selling for", "cost", "costs",

    # Current state
    "current value", "right now", "at the moment", "as of", "currently"
}

MONGODB_HISTORICAL_KEYWORDS = {
    "price history", "historical price", "past price", "was the price",
    "price on", "price in", "price over time", "price trend",

    # Historical data
    "historical", "history", "past", "ago", "was", "were", "been"
}

MONGODB_TRADING_KEYWORDS = {
    "bought", "purchased", "dca", "dollar cost averaging", "trading stats",
    "trading summary", "summary",
    "my portfolio", "my bitcoin", "total btc", "how much btc",
    "purchase history", "buy history",

    # Personal queries
    "my", "mine", "portfolio", "holdings"
}

MONGODB_TECHNICAL_KEYWORDS = {
    "rsi", "macd", "bollinger", "bollinger bands", "technical indicator",
    "ema", "sma", "moving average", "stochastic", "ichimoku",
    "technical analysis", "chart analysis", "indicators",

    # Analysis/outlook
    "analysis", "trend analysis", "outlook", "technical outlook",
    "market analysis", "signals",

    # Extended indicators (Phase: Multi-Asset)
    "adx", "supertrend", "squeeze", "fear and greed", "fear & greed",
    "fng", "f&g", "vwap", "fibonacci", "fib levels", "donchian",
    "aroon", "cci", "williams", "mfi", "money flow", "obv",
    "on-balance volume", "choppiness", "choppy", "atr", "volatility",
    "keltner", "hdpr", "log return",
}

# Bot state keywords — for routing to btc_bot_state database
BOT_STATE_KEYWORDS = {
    "my bot", "bot status", "bot state", "open positions", "bot trades",
    "trading bot", "active positions", "bot performance", "bot running",
    "bollinger bot", "rsi strategy", "strategy status", "trade events",
    "what is my bot doing", "bot entry", "bot exit", "stop loss",
    "take profit", "filled price", "filled size",
    "strategy", "bot history", "recent trades from bot",
}
