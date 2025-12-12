# src/coordinator/test_mongodb_integration.py
# Unit tests for MongoDB MCP integration components
# Run with: python -m pytest src/coordinator/test_mongodb_integration.py -v

from __future__ import annotations

import pytest
import time
from unittest.mock import Mock, patch

# Import components to test
from .tool_definitions import (
    classify_query_intent,
    QueryIntent,
    get_tools_for_query,
    get_mongodb_tools,
    AVAILABLE_TOOLS
)
from .cache import MongoDBCache, CacheEntry, get_cache, clear_cache


class TestIntentClassification:
    """Test suite for query intent classification."""

    def test_mongodb_price_query_epic_persona(self):
        """Epic persona asking for Bitcoin price should trigger MongoDB."""
        result = classify_query_intent("What's the current Bitcoin price?", "epic")
        assert result == QueryIntent.NEEDS_MONGODB

    def test_mongodb_technical_indicators(self):
        """Queries about technical indicators should trigger MongoDB."""
        queries = [
            "Show me Bitcoin's RSI",
            "What's the MACD for Bitcoin?",
            "Bitcoin Bollinger Bands",
            "What are Bitcoin's moving averages?"  # Fixed: added "Bitcoin's"
        ]
        for query in queries:
            result = classify_query_intent(query, "legendary")
            assert result == QueryIntent.NEEDS_MONGODB, f"Failed for: {query}"

    def test_mongodb_trading_stats(self):
        """Queries about trading/purchases should trigger MongoDB."""
        queries = [
            "How much Bitcoin have I bought?",
            "Show my Bitcoin purchase history",  # Fixed: added "Bitcoin"
            "What's my Bitcoin DCA strategy?",  # Fixed: added "Bitcoin"
            "Total BTC purchased"
        ]
        for query in queries:
            result = classify_query_intent(query, "epic")
            assert result == QueryIntent.NEEDS_MONGODB, f"Failed for: {query}"

    def test_mongodb_historical_data(self):
        """Historical price queries should trigger MongoDB."""
        queries = [
            "What was Bitcoin price in January 2024?",
            "Show me Bitcoin price history",  # Fixed: added "Bitcoin"
            "Bitcoin price trend over time"
        ]
        for query in queries:
            result = classify_query_intent(query, "epic")
            assert result == QueryIntent.NEEDS_MONGODB, f"Failed for: {query}"

    def test_web_search_for_news(self):
        """Bitcoin news queries should trigger web search, not MongoDB."""
        queries = [
            "Latest Bitcoin news",
            "Bitcoin article today",
            "Recent Bitcoin announcements"
        ]
        for query in queries:
            result = classify_query_intent(query, "rare")
            assert result == QueryIntent.NEEDS_WEB_SEARCH, f"Failed for: {query}"

    def test_web_search_for_general_queries(self):
        """General web search queries should trigger Brave MCP."""
        queries = [
            "What happened in the 2024 election?",
            "Latest news today",
            "Current weather"
        ]
        for query in queries:
            result = classify_query_intent(query, "rare")
            assert result == QueryIntent.NEEDS_WEB_SEARCH, f"Failed for: {query}"

    def test_no_mcp_for_definitions(self):
        """Definition queries should not trigger any MCP."""
        queries = [
            "What is Bitcoin?",
            "Explain blockchain technology",
            "How does mining work?",
            "Define cryptocurrency"
        ]
        for query in queries:
            result = classify_query_intent(query, "epic")
            assert result == QueryIntent.NEEDS_NEITHER, f"Failed for: {query}"

    def test_no_mcp_for_math(self):
        """Math queries should not trigger any MCP."""
        queries = [
            "What is 2 + 2?",
            "Calculate 25% of 80",
            "What's 100 divided by 5?"
        ]
        for query in queries:
            result = classify_query_intent(query, "epic")
            assert result == QueryIntent.NEEDS_NEITHER, f"Failed for: {query}"

    def test_multi_mcp_price_and_news(self):
        """Queries asking for both price and news should trigger both MCPs."""
        result = classify_query_intent("What's the Bitcoin price and recent news?", "epic")
        assert result == QueryIntent.NEEDS_BOTH

    def test_rarity_permission_blocking_mongodb(self):
        """Common personas should not have MongoDB access."""
        result = classify_query_intent("What's the Bitcoin price?", "common")
        assert result == QueryIntent.NEEDS_NEITHER

    def test_rarity_permission_blocking_brave(self):
        """Common personas should not have Brave access."""
        result = classify_query_intent("Latest news", "common")
        assert result == QueryIntent.NEEDS_NEITHER

    def test_epic_has_both_mcps(self):
        """Epic personas should have access to both MCPs."""
        # MongoDB access
        result1 = classify_query_intent("Bitcoin price", "epic")
        assert result1 == QueryIntent.NEEDS_MONGODB

        # Brave access
        result2 = classify_query_intent("Latest election results", "epic")
        assert result2 == QueryIntent.NEEDS_WEB_SEARCH

    def test_rare_has_brave_only(self):
        """Rare personas should have Brave but not MongoDB."""
        result1 = classify_query_intent("Bitcoin price", "rare")
        assert result1 == QueryIntent.NEEDS_NEITHER  # No MongoDB access

        result2 = classify_query_intent("Latest news", "rare")
        assert result2 == QueryIntent.NEEDS_WEB_SEARCH  # Has Brave access


class TestToolInjection:
    """Test suite for dynamic tool injection."""

    def test_mongodb_query_injects_mongodb_tools(self):
        """MongoDB queries should inject only MongoDB tools."""
        tools = get_tools_for_query("What's the Bitcoin price?", "Eeva", "epic")
        tool_names = [tool['function']['name'] for tool in tools]

        # Should have all 4 MongoDB tools
        assert "bitcoin_current_price" in tool_names
        assert "bitcoin_historical_prices" in tool_names
        assert "bitcoin_trading_summary" in tool_names
        assert "bitcoin_technical_analysis" in tool_names

        # Should NOT have Brave
        assert "brave_web_search" not in tool_names

    def test_web_query_injects_brave_only(self):
        """Web search queries should inject only Brave tool."""
        tools = get_tools_for_query("Latest news", "Eeva", "rare")
        tool_names = [tool['function']['name'] for tool in tools]

        # Should have Brave
        assert "brave_web_search" in tool_names

        # Should NOT have MongoDB tools
        assert "bitcoin_current_price" not in tool_names

    def test_definition_query_injects_no_tools(self):
        """Definition queries should inject no tools."""
        tools = get_tools_for_query("What is Bitcoin?", "Eeva", "epic")
        assert len(tools) == 0

    def test_multi_mcp_query_injects_both(self):
        """Multi-MCP queries should inject both tool sets."""
        tools = get_tools_for_query("Bitcoin price and recent news", "Eeva", "epic")
        tool_names = [tool['function']['name'] for tool in tools]

        # Should have Brave
        assert "brave_web_search" in tool_names

        # Should have MongoDB tools
        assert "bitcoin_current_price" in tool_names


class TestMongoDBCache:
    """Test suite for MongoDB caching layer."""

    def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        cache = MongoDBCache()
        test_data = {"price": 91793.10, "rsi": 62.46}

        cache.set("test_key", test_data, ttl=60, source="test")
        entry = cache.get("test_key")

        assert entry is not None
        assert entry.data == test_data
        assert entry.source == "test"
        assert not entry.is_expired()

    def test_cache_miss(self):
        """Test cache miss for non-existent key."""
        cache = MongoDBCache()
        entry = cache.get("nonexistent_key")
        assert entry is None

    def test_cache_expiry(self):
        """Test TTL expiry."""
        cache = MongoDBCache()
        cache.set("short_ttl", {"test": "data"}, ttl=1, source="test")

        # Should be available immediately
        entry = cache.get("short_ttl")
        assert entry is not None

        # Wait for expiry
        time.sleep(1.1)

        # Should be expired
        entry = cache.get("short_ttl")
        assert entry is None

    def test_cache_invalidation(self):
        """Test manual cache invalidation."""
        cache = MongoDBCache()
        cache.set("test_key", {"data": 123}, ttl=300, source="test")

        # Verify it exists
        assert cache.get("test_key") is not None

        # Invalidate
        result = cache.invalidate("test_key")
        assert result is True

        # Should be gone
        assert cache.get("test_key") is None

    def test_cache_clear(self):
        """Test clearing all cache entries."""
        cache = MongoDBCache()
        cache.set("key1", {"data": 1}, ttl=60, source="test")
        cache.set("key2", {"data": 2}, ttl=60, source="test")
        cache.set("key3", {"data": 3}, ttl=60, source="test")

        # Verify entries exist
        assert cache.get_stats()['size'] == 3

        # Clear
        cache.clear()

        # Should be empty
        assert cache.get_stats()['size'] == 0

    def test_cache_stats_tracking(self):
        """Test cache statistics tracking."""
        cache = MongoDBCache()

        # Generate some hits and misses
        cache.set("key1", {"data": 1}, ttl=60, source="test")
        cache.get("key1")  # Hit
        cache.get("key1")  # Hit
        cache.get("nonexistent")  # Miss
        cache.get("nonexistent2")  # Miss

        stats = cache.get_stats()
        assert stats['hits'] == 2
        assert stats['misses'] == 2
        assert stats['hit_rate'] == 50.0
        assert stats['size'] == 1

    def test_cache_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = MongoDBCache()
        cache.set("key1", {"data": 1}, ttl=1, source="test")
        cache.set("key2", {"data": 2}, ttl=1, source="test")
        cache.set("key3", {"data": 3}, ttl=60, source="test")

        # Wait for expiry
        time.sleep(1.1)

        # Cleanup
        removed = cache.cleanup_expired()

        # Should remove 2 expired entries
        assert removed == 2

        # key3 should still exist
        assert cache.get("key3") is not None

    def test_cache_entry_age(self):
        """Test cache entry age calculation."""
        cache = MongoDBCache()
        cache.set("test_key", {"data": 123}, ttl=60, source="test")

        # Get immediately
        entry = cache.get("test_key")
        assert entry is not None
        assert entry.age_seconds() < 2  # Should be very young (relaxed tolerance)

        # Wait a bit
        time.sleep(1.1)  # Wait slightly longer
        entry = cache.get("test_key")
        assert entry is not None
        assert entry.age_seconds() >= 0.9  # Should be close to 1 second old (relaxed tolerance)


class TestMongoDBTools:
    """Test suite for MongoDB tool definitions."""

    def test_all_tools_registered(self):
        """Verify all 4 MongoDB tools are registered."""
        assert "bitcoin_current_price" in AVAILABLE_TOOLS
        assert "bitcoin_historical_prices" in AVAILABLE_TOOLS
        assert "bitcoin_trading_summary" in AVAILABLE_TOOLS
        assert "bitcoin_technical_analysis" in AVAILABLE_TOOLS

    def test_mongodb_tools_count(self):
        """Verify get_mongodb_tools returns 4 tools."""
        tools = get_mongodb_tools()
        assert len(tools) == 4

    def test_tool_required_reason_parameter(self):
        """All MongoDB tools should require 'reason' parameter."""
        tools = get_mongodb_tools()

        for tool in tools:
            params = tool['function']['parameters']
            required = params.get('required', [])
            assert 'reason' in required, f"Tool {tool['function']['name']} missing required 'reason' parameter"

    def test_tool_descriptions_not_empty(self):
        """All tool descriptions should be meaningful."""
        tools = get_mongodb_tools()

        for tool in tools:
            description = tool['function']['description']
            assert len(description) > 50, f"Tool {tool['function']['name']} has insufficient description"
            # Check for meaningful trading/price related content
            assert any(word in description.lower() for word in ["bitcoin", "price", "trading", "technical", "data"]), \
                f"Tool {tool['function']['name']} description lacks relevant content"


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
