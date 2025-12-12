#!/usr/bin/env python
"""
Test script for MongoDB MCP Phase 4 backend integration.
Tests intent classification, tool handlers, and caching.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_intent_classification():
    """Test intent classification for MongoDB queries."""
    print("\n=== Testing Intent Classification ===")
    from coordinator.tool_definitions import classify_query_intent, QueryIntent

    test_cases = [
        ("What's the current Bitcoin price?", "epic", QueryIntent.NEEDS_MONGODB),
        ("What is Bitcoin?", "epic", QueryIntent.NEEDS_NEITHER),
        ("Latest Bitcoin news", "rare", QueryIntent.NEEDS_WEB_SEARCH),
        ("Show me the Bitcoin price and latest news", "legendary", QueryIntent.NEEDS_BOTH),
        ("What's the Bitcoin price?", "common", QueryIntent.NEEDS_NEITHER),  # No MongoDB access
    ]

    passed = 0
    for query, rarity, expected in test_cases:
        result = classify_query_intent(query, rarity)
        status = "[PASS]" if result == expected else "[FAIL]"
        print(f"{status} Query: '{query[:50]}...' | Rarity: {rarity} | Expected: {expected} | Got: {result}")
        if result == expected:
            passed += 1

    print(f"\nPassed: {passed}/{len(test_cases)}")
    return passed == len(test_cases)

def test_tool_injection():
    """Test dynamic tool injection based on query intent."""
    print("\n=== Testing Tool Injection ===")
    from coordinator.tool_definitions import get_tools_for_query

    test_cases = [
        ("What's the current Bitcoin price?", "epic", True, False),  # MongoDB only
        ("Latest Bitcoin news", "rare", False, True),  # Brave only
        ("Show me Bitcoin price and news", "legendary", True, True),  # Both
        ("What is Bitcoin?", "epic", False, False),  # Neither
    ]

    passed = 0
    for query, rarity, expect_mongodb, expect_brave in test_cases:
        tools = get_tools_for_query(query, "test_persona", rarity)
        has_mongodb = any(t.get("function", {}).get("name", "").startswith("bitcoin_") for t in tools)
        has_brave = any(t.get("function", {}).get("name", "") == "brave_web_search" for t in tools)

        correct = (has_mongodb == expect_mongodb) and (has_brave == expect_brave)
        status = "[PASS]" if correct else "[FAIL]"
        print(f"{status} Query: '{query[:40]}...' | MongoDB: {has_mongodb} (expect {expect_mongodb}) | Brave: {has_brave} (expect {expect_brave})")
        if correct:
            passed += 1

    print(f"\nPassed: {passed}/{len(test_cases)}")
    return passed == len(test_cases)

def test_mongodb_client_init():
    """Test MongoDB client initialization."""
    print("\n=== Testing MongoDB Client Initialization ===")
    from coordinator.mongodb_mcp_client import MongoDBMCPClient
    from coordinator.config import get_mongodb_uri, get_mongodb_timeout, is_mongodb_enabled

    if not is_mongodb_enabled():
        print("[FAIL] MongoDB is not enabled in config")
        return False

    try:
        uri = get_mongodb_uri()
        timeout = get_mongodb_timeout()
        print(f"[PASS] MongoDB URI configured: {uri[:50]}...")
        print(f"[PASS] MongoDB timeout: {timeout}s")

        # Try to initialize client
        client = MongoDBMCPClient(
            connection_uri=uri,
            timeout=timeout,
            max_response_bytes=100000
        )
        print(f"[PASS] MongoDB MCP client initialized successfully")

        # Try a simple query
        results = client.find(
            database="btc_data",
            collection="1h_price_data",
            filter={},
            sort={"timestamp": -1},
            limit=1
        )

        if results and len(results) > 0:
            latest = results[0]
            print(f"[PASS] Successfully queried MongoDB")
            print(f"  Latest price: ${latest.get('Close', 'N/A'):.2f}")
            print(f"  Timestamp: {latest.get('timestamp', 'N/A')}")
            print(f"  RSI: {latest.get('RSI', 'N/A')}")
            client.close()
            return True
        else:
            print("[FAIL] Query returned no results")
            client.close()
            return False

    except Exception as e:
        print(f"[FAIL] MongoDB client initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cache():
    """Test caching functionality."""
    print("\n=== Testing Cache ===")
    from coordinator.cache import get_cache
    import time

    try:
        cache = get_cache()

        # Test set and get
        test_data = {"price": 91793.10, "timestamp": "2025-12-11 20:00:00"}
        cache.set("test_key", test_data, ttl=5, source="test")

        # Retrieve
        cached = cache.get("test_key")
        if cached and cached.data == test_data:
            print(f"[PASS] Cache set and get working")
            print(f"  Cached data: {cached.data}")
            print(f"  Age: {cached.age_seconds():.2f}s")
            print(f"  Source: {cached.source}")
        else:
            print("[FAIL] Cache get failed")
            return False

        # Test expiry
        time.sleep(2)
        cached = cache.get("test_key")
        if cached:
            print(f"[PASS] Cache still valid after 2s (TTL=5s)")
        else:
            print("[FAIL] Cache expired too early")
            return False

        # Test statistics
        stats = cache.get_stats()
        print(f"[PASS] Cache statistics:")
        print(f"  Hits: {stats['hits']}")
        print(f"  Misses: {stats['misses']}")
        print(f"  Hit rate: {stats['hit_rate']:.2%}")

        return True

    except Exception as e:
        print(f"[FAIL] Cache test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tool_handler():
    """Test MongoDB tool handler."""
    print("\n=== Testing Tool Handler ===")

    # We can't easily test tool handlers without a running server
    # But we can verify they're importable and have correct signatures
    try:
        from coordinator.server import (
            handle_bitcoin_current_price,
            handle_bitcoin_historical_prices,
            handle_bitcoin_trading_summary,
            handle_bitcoin_technical_analysis
        )

        print("[PASS] All tool handlers imported successfully")
        print("  - handle_bitcoin_current_price")
        print("  - handle_bitcoin_historical_prices")
        print("  - handle_bitcoin_trading_summary")
        print("  - handle_bitcoin_technical_analysis")

        return True

    except Exception as e:
        print(f"[FAIL] Tool handler import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("MongoDB MCP Phase 4 Integration Tests")
    print("=" * 60)

    results = []

    # Test 1: Intent Classification
    results.append(("Intent Classification", test_intent_classification()))

    # Test 2: Tool Injection
    results.append(("Tool Injection", test_tool_injection()))

    # Test 3: Cache
    results.append(("Cache", test_cache()))

    # Test 4: Tool Handlers
    results.append(("Tool Handlers Import", test_tool_handler()))

    # Test 5: MongoDB Client (requires network)
    print("\nNote: MongoDB client test requires network connection and valid credentials")
    results.append(("MongoDB Client", test_mongodb_client_init()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status:8} {name}")

    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n[SUCCESS] All tests passed! Phase 4 is ready.")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed. Review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
