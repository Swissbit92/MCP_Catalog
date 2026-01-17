# tests/backend/coordinator/test_mongodb_handlers.py
"""
Unit tests for MongoDBService - MongoDB query handlers with caching.

Tests cover:
- Service availability checking
- Cache hit/miss logic
- Bitcoin price query handling
- Historical data queries
- Error handling
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi import HTTPException

from src.coordinator.services.mongodb_handlers import MongoDBService


class TestMongoDBService:
    """Test MongoDBService functionality."""

    def test_is_available_with_client(self):
        """Test service availability when client is configured."""
        mock_client = Mock()
        mock_cache = Mock()

        service = MongoDBService(mongodb_client=mock_client, mongodb_cache=mock_cache)

        assert service.is_available is True

    def test_is_available_without_client(self):
        """Test service availability when client is None."""
        service = MongoDBService(mongodb_client=None, mongodb_cache=Mock())

        assert service.is_available is False

    def test_check_cache_hit(self):
        """Test cache hit scenario."""
        mock_client = Mock()
        mock_cache = Mock()

        cached_data = Mock()
        cached_data.data = {"price": 50000}
        cached_data.age_seconds.return_value = 30
        mock_cache.get.return_value = cached_data

        service = MongoDBService(mongodb_client=mock_client, mongodb_cache=mock_cache)

        fetch_func = Mock()  # Should NOT be called
        data, status = service._check_cache_or_fetch("test_key", fetch_func)

        # Verify cache was checked
        mock_cache.get.assert_called_once_with("test_key")

        # Verify fetch was NOT called (cache hit)
        fetch_func.assert_not_called()

        # Verify result
        assert data == {"price": 50000}
        assert status == "hit"

    def test_check_cache_miss(self):
        """Test cache miss scenario."""
        mock_client = Mock()
        mock_cache = Mock()
        mock_cache.get.return_value = None  # Cache miss

        service = MongoDBService(mongodb_client=mock_client, mongodb_cache=mock_cache)

        fetch_func = Mock()
        fetch_func.return_value = {"price": 50000}

        with patch("src.coordinator.services.mongodb_handlers.get_mongodb_cache_ttl") as mock_ttl:
            mock_ttl.return_value = 60

            data, status = service._check_cache_or_fetch("test_key", fetch_func)

        # Verify cache was checked
        mock_cache.get.assert_called_once_with("test_key")

        # Verify fetch was called
        fetch_func.assert_called_once()

        # Verify data was cached
        mock_cache.set.assert_called_once()

        # Verify result
        assert data == {"price": 50000}
        assert status == "miss"

    def test_check_cache_force_refresh(self):
        """Test force refresh bypasses cache."""
        mock_client = Mock()
        mock_cache = Mock()
        mock_cache.get.return_value = Mock(data={"old": "data"})  # Has cached data

        service = MongoDBService(mongodb_client=mock_client, mongodb_cache=mock_cache)

        fetch_func = Mock()
        fetch_func.return_value = {"price": 50000}

        with patch("src.coordinator.services.mongodb_handlers.get_mongodb_cache_ttl") as mock_ttl:
            mock_ttl.return_value = 60

            data, status = service._check_cache_or_fetch("test_key", fetch_func, force_refresh=True)

        # Verify cache was NOT checked (force refresh)
        mock_cache.get.assert_not_called()

        # Verify fetch was called
        fetch_func.assert_called_once()

        # Verify result is fresh data
        assert data == {"price": 50000}
        assert status == "miss"

    def test_check_cache_fetch_error(self):
        """Test error handling when fetch fails."""
        mock_client = Mock()
        mock_cache = Mock()
        mock_cache.get.return_value = None  # Cache miss

        service = MongoDBService(mongodb_client=mock_client, mongodb_cache=mock_cache)

        fetch_func = Mock()
        fetch_func.side_effect = Exception("MongoDB connection error")

        with pytest.raises(Exception, match="MongoDB connection error"):
            service._check_cache_or_fetch("test_key", fetch_func)

    def test_handle_bitcoin_current_price_no_client(self):
        """Test Bitcoin price query when client is None."""
        service = MongoDBService(mongodb_client=None, mongodb_cache=Mock())

        with pytest.raises(HTTPException) as exc_info:
            service.handle_bitcoin_current_price(reason="Test")

        assert exc_info.value.status_code == 503
        assert "MongoDB MCP not available" in str(exc_info.value.detail)

    @patch("src.coordinator.services.mongodb_handlers.get_mongodb_cache_ttl")
    def test_handle_bitcoin_current_price_success(self, mock_ttl):
        """Test successful Bitcoin price query."""
        mock_ttl.return_value = 60

        mock_client = Mock()
        mock_client.find.return_value = [{
            "timestamp": "2025-01-17T10:00:00Z",
            "close": 50000,
            "RSI": 65,
            "MACD_Line": 100,
            "BB_High": 51000,
            "BB_Low": 49000,
            "EMA_20": 49500,
            "EMA_50": 49000
        }]

        mock_cache = Mock()
        mock_cache.get.return_value = None  # Cache miss

        service = MongoDBService(mongodb_client=mock_client, mongodb_cache=mock_cache)

        result = service.handle_bitcoin_current_price(reason="User query")

        # Verify MongoDB query was called
        mock_client.find.assert_called_once()
        call_kwargs = mock_client.find.call_args.kwargs

        assert call_kwargs["database"] == "btc_data"
        assert call_kwargs["collection"] == "1h_price_data"
        assert call_kwargs["sort"] == {"timestamp": -1}
        assert call_kwargs["limit"] == 1

        # Verify result structure
        assert "price" in result or "close" in result
        assert "timestamp" in result

    @patch("src.coordinator.services.mongodb_handlers.get_mongodb_cache_ttl")
    def test_handle_bitcoin_current_price_no_data(self, mock_ttl):
        """Test Bitcoin price query when no data found."""
        mock_ttl.return_value = 60

        mock_client = Mock()
        mock_client.find.return_value = []  # No data

        mock_cache = Mock()
        mock_cache.get.return_value = None

        service = MongoDBService(mongodb_client=mock_client, mongodb_cache=mock_cache)

        with pytest.raises(HTTPException) as exc_info:
            service.handle_bitcoin_current_price(reason="Test")

        assert exc_info.value.status_code == 404
        assert "No price data found" in str(exc_info.value.detail)

    def test_check_cache_no_cache_configured(self):
        """Test behavior when cache is not configured."""
        mock_client = Mock()

        service = MongoDBService(mongodb_client=mock_client, mongodb_cache=None)

        fetch_func = Mock()
        data, status = service._check_cache_or_fetch("test_key", fetch_func)

        # Should return None, "miss" when cache not configured
        assert data is None
        assert status == "miss"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
