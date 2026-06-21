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

# Explicit search commands — the user is directly instructing a web search
# ("search the web to confirm", "google it", "look it up").
# Single source of truth: also consumed by ForceSearchService.FORCE_PATTERNS so an
# explicit command both (a) routes intent → NEEDS_WEB_SEARCH (the Brave tool is
# offered) and (b) bypasses the unreliable LLM tool-calling loop (forced direct
# execution). High-precision MULTIWORD phrases only — never bare "search" (it
# substring-matches "research"/"researcher" and would over-trigger).
EXPLICIT_SEARCH_COMMANDS = (
    "search the web", "search online", "search the internet", "search for",
    "web search", "look it up", "look this up", "look that up",
    "look online", "look up online", "google it", "google this", "google that",
    "find online", "find out online", "check online", "check the web",
    "confirm online", "verify online", "browse the web",
)

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

# Fold explicit search commands into the web-search trigger set (single source of truth).
SEARCH_KEYWORDS.update(EXPLICIT_SEARCH_COMMANDS)

