# src/coordinator/cache.py
# TTL-based caching for MongoDB MCP queries
# Thread-safe implementation with configurable expiry times

from __future__ import annotations

import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached value with expiry metadata."""
    data: Any
    expires_at: float  # Unix timestamp when entry expires
    fetched_at: str  # ISO format timestamp (for display)
    created_at: float  # Unix timestamp when entry was created
    source: str  # Tool name that generated this data

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() >= self.expires_at

    def age_seconds(self) -> float:
        """Get age of cache entry in seconds."""
        return time.time() - self.created_at

    def get_ttl(self) -> float:
        """Get remaining TTL in seconds."""
        return max(0, self.expires_at - time.time())


class MongoDBCache:
    """
    Thread-safe TTL-based cache for MongoDB query results.

    Features:
    - Configurable TTL per tool
    - Thread-safe operations
    - Automatic expiry
    - Cache hit/miss tracking
    - Manual invalidation support
    """

    def __init__(self):
        """Initialize empty cache."""
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        logger.info("Initialized MongoDB cache")

    def get(self, key: str) -> Optional[CacheEntry]:
        """
        Get cached value if exists and not expired.

        Args:
            key: Cache key (usually tool name)

        Returns:
            CacheEntry if valid, None if not found or expired
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                logger.debug(f"Cache miss: {key}")
                return None

            entry = self._cache[key]

            # Check if expired
            if entry.is_expired():
                logger.debug(f"Cache expired: {key} (age: {entry.age_seconds():.1f}s)")
                del self._cache[key]
                self._evictions += 1
                self._misses += 1
                return None

            self._hits += 1
            logger.debug(f"Cache hit: {key} (age: {entry.age_seconds():.1f}s)")
            return entry

    def set(self, key: str, data: Any, ttl: int, source: str):
        """
        Store value in cache with TTL.

        Args:
            key: Cache key
            data: Data to cache
            ttl: Time-to-live in seconds
            source: Tool name that generated this data
        """
        with self._lock:
            now = time.time()
            expires_at = now + ttl
            fetched_at = datetime.utcnow().isoformat() + "Z"

            entry = CacheEntry(
                data=data,
                expires_at=expires_at,
                fetched_at=fetched_at,
                created_at=now,
                source=source
            )

            self._cache[key] = entry
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")

    def invalidate(self, key: str) -> bool:
        """
        Manually invalidate a cache entry.

        Args:
            key: Cache key to invalidate

        Returns:
            True if entry was found and removed, False otherwise
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache invalidated: {key}")
                return True
            return False

    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared: {count} entries removed")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with hits, misses, hit_rate, size, evictions
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate": round(hit_rate, 2),
                "size": len(self._cache),
                "keys": list(self._cache.keys())
            }

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]

            for key in expired_keys:
                del self._cache[key]
                self._evictions += 1

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired entries")

            return len(expired_keys)


# Global cache instance
_mongodb_cache: Optional[MongoDBCache] = None


def get_cache() -> MongoDBCache:
    """
    Get the global MongoDB cache instance (singleton).

    Returns:
        MongoDBCache instance
    """
    global _mongodb_cache
    if _mongodb_cache is None:
        _mongodb_cache = MongoDBCache()
    return _mongodb_cache


def clear_cache():
    """Clear the global cache."""
    cache = get_cache()
    cache.clear()


# Example usage
if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("Testing MongoDB Cache")
    print("=" * 60)

    cache = MongoDBCache()

    # Test 1: Set and get
    print("\nTest 1: Basic set/get")
    test_data = {"price": 91793.10, "rsi": 62.46}
    cache.set("bitcoin_current_price", test_data, ttl=60, source="1h_price_data")

    entry = cache.get("bitcoin_current_price")
    if entry:
        print(f"[OK] Cache hit: {entry.data}")
        print(f"     Fetched at: {entry.fetched_at}")
        print(f"     Expires in: {entry.get_ttl():.1f}s")
    else:
        print("[FAIL] Cache miss")

    # Test 2: Cache miss
    print("\nTest 2: Cache miss")
    entry = cache.get("nonexistent_key")
    if entry is None:
        print("[OK] Cache miss as expected")
    else:
        print("[FAIL] Should have been a miss")

    # Test 3: Expiry
    print("\nTest 3: TTL expiry")
    cache.set("short_ttl", {"test": "data"}, ttl=1, source="test")
    print("Waiting 2 seconds...")
    time.sleep(2)
    entry = cache.get("short_ttl")
    if entry is None:
        print("[OK] Entry expired as expected")
    else:
        print("[FAIL] Entry should have expired")

    # Test 4: Cache stats
    print("\nTest 4: Cache statistics")
    stats = cache.get_stats()
    print(f"Hits: {stats['hits']}")
    print(f"Misses: {stats['misses']}")
    print(f"Hit rate: {stats['hit_rate']}%")
    print(f"Size: {stats['size']}")
    print(f"Evictions: {stats['evictions']}")

    # Test 5: Manual invalidation
    print("\nTest 5: Manual invalidation")
    cache.set("test_key", {"data": 123}, ttl=300, source="test")
    invalidated = cache.invalidate("test_key")
    if invalidated:
        print("[OK] Entry invalidated")
        entry = cache.get("test_key")
        if entry is None:
            print("[OK] Entry no longer in cache")
        else:
            print("[FAIL] Entry should have been removed")
    else:
        print("[FAIL] Invalidation failed")

    # Test 6: Clear all
    print("\nTest 6: Clear all")
    cache.set("key1", {"data": 1}, ttl=60, source="test")
    cache.set("key2", {"data": 2}, ttl=60, source="test")
    cache.set("key3", {"data": 3}, ttl=60, source="test")
    print(f"Cache size before clear: {cache.get_stats()['size']}")
    cache.clear()
    print(f"Cache size after clear: {cache.get_stats()['size']}")
    if cache.get_stats()['size'] == 0:
        print("[OK] Cache cleared successfully")
    else:
        print("[FAIL] Cache should be empty")

    print("\n" + "=" * 60)
    print("[OK] All tests completed!")
