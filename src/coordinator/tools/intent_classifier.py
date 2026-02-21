# src/coordinator/tools/intent_classifier.py
"""Intent classification for query routing to appropriate MCP services."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from .keywords import (
    NO_SEARCH_KEYWORDS,
    SEARCH_KEYWORDS,
    MONGODB_PRICE_KEYWORDS,
    MONGODB_HISTORICAL_KEYWORDS,
    MONGODB_TRADING_KEYWORDS,
    MONGODB_TECHNICAL_KEYWORDS,
)


class QueryIntent(Enum):
    """Query intent classification for MCP routing."""
    NEEDS_WEB_SEARCH = "web"      # Brave MCP
    NEEDS_MONGODB = "mongodb"      # MongoDB MCP
    NEEDS_BOTH = "both"            # Multi-MCP
    NEEDS_NEITHER = "llm"          # Pure LLM
    NEEDS_WALLET = "wallet"        # Jupiter wallet / Solana trading


def classify_query_intent(
    query: str,
    persona_rarity: str,
    mcp_access: Optional[List[str]] = None,
) -> QueryIntent:
    """
    Layer 1: Fast keyword-based intent classification for MCP routing.

    Args:
        query: User query string
        persona_rarity: Persona rarity level (common, rare, epic, legendary)
        mcp_access: Optional explicit list of allowed MCP services from the persona
                    JSON ``mcp_access`` field (e.g. ``["brave_search", "mongodb"]``).
                    When provided this takes priority over ``persona_rarity``-based
                    gating entirely.

    Returns:
        QueryIntent enum indicating which MCP(s) to use
    """
    query_lower = query.lower()

    # Determine wallet access
    can_use_wallet = "solana_wallet" in (mcp_access or [])

    # Wallet intent keywords (check before MongoDB/Brave)
    WALLET_KEYWORDS = [
        # Direct commands
        "swap ", "swap usdc", "swap sol", "buy sol", "sell sol",
        "buy usdc", "exchange usdc", "exchange sol",
        # Portfolio queries
        "my balance", "my wallet", "my portfolio", "my holdings",
        "how much sol", "what's in my wallet", "wallet balance",
        # Advisory conversations (key for co-pilot feel)
        "should i buy", "good time to buy", "good time to sell",
        "dca into", "dollar cost average", "accumulate sol",
        "is this a good time", "what do you think about buying",
        # Strategy management
        "rsi strategy", "dca strategy", "set up a strategy",
        "automate my", "start trading", "stop trading",
        "pause strategy", "pause my strategy", "stop my strategy",
        "cancel strategy", "resume strategy",
        # Performance review
        "trade history", "my trades", "strategy performance",
        "how did my strategy", "how are my trades",
        "p&l", "profit and loss", "trading returns",
        # Wallet management
        "create wallet", "new wallet", "solana wallet",
        "my address", "public address", "private key",
        "create a wallet", "set up a wallet",
        # Quote/price
        "solana quote", "jupiter quote", "swap quote",
        "get a quote", "check rsi", "sol rsi",
        # Common misspellings / aliases
        "jupyter wallet", "jupyter quote", "jupyter swap",
        "jupter wallet", "jupter quote",
        "my sol", "my usdc", "my tokens",
        "wallet address", "fund my wallet",
    ]

    if can_use_wallet and any(kw in query_lower for kw in WALLET_KEYWORDS):
        return QueryIntent.NEEDS_WALLET

    # Determine MCP permissions — per-persona mcp_access takes priority
    if mcp_access is not None:
        # Per-persona MCP access (from persona JSON mcp_access field)
        can_use_brave = "brave_search" in mcp_access
        can_use_mongodb = "mongodb" in mcp_access
    else:
        # Fallback to rarity-based access for personas without mcp_access field
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
