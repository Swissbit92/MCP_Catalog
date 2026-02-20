# src/coordinator/services/mongodb_handlers.py
"""MongoDB tool handlers for Bitcoin trading data queries."""

from __future__ import annotations

from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
import logging

from fastapi import HTTPException

from ..config import get_settings

logger = logging.getLogger(__name__)


class MongoDBService:
    """Service for handling MongoDB queries with caching."""

    def __init__(self, mongodb_client, mongodb_cache):
        self._client = mongodb_client
        self._cache = mongodb_cache

    @property
    def is_available(self) -> bool:
        """Check if MongoDB service is available."""
        return self._client is not None

    def _check_cache_or_fetch(
        self,
        cache_key: str,
        fetch_func: Callable,
        force_refresh: bool = False
    ) -> tuple[Any, str]:
        """Check cache first, then fetch from MongoDB if needed."""
        if not self._cache or not self._client:
            return None, "miss"

        # Check cache unless force refresh
        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached:
                logger.info(f"Cache HIT for {cache_key} (age: {cached.age_seconds()}s)")
                return cached.data, "hit"

        # Cache miss or force refresh - fetch from MongoDB
        logger.info(f"Cache MISS for {cache_key}, fetching from MongoDB...")
        try:
            data = fetch_func()
            # Cache the result
            ttl = get_settings().mongodb.get_cache_ttl(cache_key)
            self._cache.set(cache_key, data, ttl=ttl, source="mongodb_mcp")
            logger.info(f"Cached {cache_key} with TTL={ttl}s")
            return data, "miss"
        except Exception as e:
            logger.error(f"MongoDB fetch error for {cache_key}: {e}")
            raise

    def handle_bitcoin_current_price(
        self,
        reason: str,
        include_indicators: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get current Bitcoin price with key technical indicators."""
        if not self._client:
            raise HTTPException(status_code=503, detail="MongoDB MCP not available")

        def fetch():
            # Query 1h_price_data for latest document
            result = self._client.find(
                database="btc_data",
                collection="1h_price_data",
                filter={},
                sort={"timestamp": -1},
                limit=1
            )

            if not result or len(result) == 0:
                raise HTTPException(status_code=404, detail="No price data found")

            latest = result[0]

            # Build response with technical explanations
            indicators_to_include = include_indicators or [
                "RSI", "MACD_Line", "BB_High", "BB_Low", "EMA_20", "EMA_50"
            ]

            indicators_data = {}
            for ind in indicators_to_include:
                if ind in latest:
                    indicators_data[ind] = latest[ind]

            # Add signal interpretations
            # RSI thresholds: 70/30 (industry standard)
            # 70+ = Overbought (potential reversal down)
            # 30- = Oversold (potential reversal up)
            # Used by TradingView, Investopedia, and technical analysts worldwide.
            # DO NOT change unless implementing custom trading strategy.
            rsi = latest.get("RSI", 0)
            rsi_signal = (
                "Overbought" if rsi > 70
                else "Oversold" if rsi < 30
                else "Neutral-Bullish" if rsi > 50
                else "Neutral-Bearish"
            )

            macd_hist = latest.get("MACD_Histogram", 0)
            macd_trend = "Bullish crossover" if macd_hist > 0 else "Bearish crossover"

            price = latest.get("Close", 0)
            bb_upper = latest.get("BB_High", 0)
            bb_lower = latest.get("BB_Low", 0)
            bb_mid = (bb_upper + bb_lower) / 2 if bb_upper and bb_lower else 0
            bb_position = "Near upper band" if price > bb_mid else "Near lower band"

            return {
                "price": latest.get("Close"),
                "timestamp": latest.get("timestamp"),
                "volume": latest.get("Volume"),
                "indicators": {
                    "RSI": {"value": rsi, "signal": rsi_signal},
                    "MACD": {
                        "line": latest.get("MACD_Line"),
                        "signal": latest.get("MACD_Signal"),
                        "histogram": macd_hist,
                        "trend": macd_trend
                    },
                    "Bollinger_Bands": {
                        "upper": bb_upper,
                        "lower": bb_lower,
                        "signal": bb_position
                    },
                    "EMA_20": latest.get("EMA_20"),
                    "EMA_50": latest.get("EMA_50"),
                    "raw_indicators": indicators_data
                },
                "data_source": "1h_price_data"
            }

        data, cache_status = self._check_cache_or_fetch("bitcoin_current_price", fetch)
        data["cache_status"] = cache_status
        return data

    def handle_bitcoin_historical_prices(
        self,
        reason: str,
        start_date: str,
        end_date: Optional[str] = None,
        timeframe: str = "daily",
        indicators: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Query historical Bitcoin price data with date range."""
        if not self._client:
            raise HTTPException(status_code=503, detail="MongoDB MCP not available")

        collection = "daily_price_data" if timeframe == "daily" else "1h_price_data"

        # Build query filter
        query_filter = {}
        if start_date:
            if not end_date:
                end_date = datetime.utcnow().strftime("%Y-%m-%d")
            query_filter["timestamp"] = {"$gte": start_date, "$lte": end_date}

        # Build projection
        projection = {
            "timestamp": 1,
            "Open": 1,
            "High": 1,
            "Low": 1,
            "Close": 1,
            "Volume": 1
        }

        if indicators:
            for ind in indicators:
                projection[ind] = 1

        def fetch():
            results = self._client.find(
                database="btc_data",
                collection=collection,
                filter=query_filter,
                projection=projection,
                sort={"timestamp": 1},
                limit=100  # Safety limit
            )

            return {
                "timeframe": timeframe,
                "start_date": start_date,
                "end_date": end_date,
                "count": len(results),
                "data": results,
                "data_source": collection
            }

        # Use a cache key that includes the date range
        cache_key = f"bitcoin_historical_prices_{start_date}_{end_date}_{timeframe}"
        data, cache_status = self._check_cache_or_fetch(cache_key, fetch)
        data["cache_status"] = cache_status
        return data

    def handle_bitcoin_trading_summary(
        self,
        reason: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get DCA (Dollar Cost Averaging) trading statistics."""
        if not self._client:
            raise HTTPException(status_code=503, detail="MongoDB MCP not available")

        def fetch():
            # Build match stage
            match_stage = {}
            if start_date or end_date:
                match_stage["timestamp"] = {}
                if start_date:
                    match_stage["timestamp"]["$gte"] = start_date
                if end_date:
                    match_stage["timestamp"]["$lte"] = end_date

            # Aggregation pipeline
            pipeline = [
                {"$match": match_stage} if match_stage else {"$match": {}},
                {"$group": {
                    "_id": None,
                    "total_btc": {"$sum": "$dealSize"},
                    "total_usdt_spent": {"$sum": "$dealFunds"},
                    "total_fees": {"$sum": "$fee"},
                    "num_purchases": {"$sum": 1},
                    "avg_price": {"$avg": "$price"},
                    "min_price": {"$min": "$price"},
                    "max_price": {"$max": "$price"},
                    "first_purchase": {"$min": "$timestamp"},
                    "last_purchase": {"$max": "$timestamp"}
                }}
            ]

            results = self._client.aggregate(
                database="btc_data",
                collection="BTC dayli buying",
                pipeline=pipeline
            )

            if not results or len(results) == 0:
                return {
                    "total_btc": 0,
                    "total_usdt_spent": 0,
                    "total_fees": 0,
                    "num_purchases": 0,
                    "data_source": "BTC dayli buying"
                }

            summary = results[0]
            summary["data_source"] = "BTC dayli buying"
            return summary

        cache_key = f"bitcoin_trading_summary_{start_date}_{end_date}"
        data, cache_status = self._check_cache_or_fetch(cache_key, fetch)
        data["cache_status"] = cache_status
        return data

    def handle_bitcoin_technical_analysis(
        self,
        reason: str,
        timeframe: str = "hourly"
    ) -> Dict[str, Any]:
        """Multi-timeframe technical analysis."""
        if not self._client:
            raise HTTPException(status_code=503, detail="MongoDB MCP not available")

        def fetch():
            collection = "1h_price_data" if timeframe == "hourly" else "daily_price_data"

            # Get latest data
            results = self._client.find(
                database="btc_data",
                collection=collection,
                filter={},
                sort={"timestamp": -1},
                limit=1
            )

            if not results or len(results) == 0:
                raise HTTPException(status_code=404, detail="No data found")

            latest = results[0]

            # Analyze indicators
            price = latest.get("Close", 0)
            ema_20 = latest.get("EMA_20", 0)
            ema_50 = latest.get("EMA_50", 0)
            ema_200 = latest.get("EMA_200", 0)

            trend = "bullish" if price > ema_20 > ema_50 else "bearish"

            # RSI 70/30 thresholds (industry standard)
            rsi = latest.get("RSI", 0)
            rsi_signal = "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral"

            macd_hist = latest.get("MACD_Histogram", 0)
            macd_crossover = "bullish" if macd_hist > 0 else "bearish"

            bb_high = latest.get("BB_High", 0)
            bb_low = latest.get("BB_Low", 0)
            bb_mid = (bb_high + bb_low) / 2 if bb_high and bb_low else 0
            bb_position = "upper" if price > bb_mid else "lower"

            analysis = {
                "price": price,
                "timestamp": latest.get("timestamp"),
                "timeframe": timeframe,
                "trend_indicators": {
                    "EMA_20": ema_20,
                    "EMA_50": ema_50,
                    "EMA_200": ema_200,
                    "trend": trend
                },
                "momentum_indicators": {
                    "RSI": {
                        "value": rsi,
                        "signal": rsi_signal
                    },
                    "MACD": {
                        "line": latest.get("MACD_Line"),
                        "signal": latest.get("MACD_Signal"),
                        "histogram": macd_hist,
                        "crossover": macd_crossover
                    },
                    "Stochastic_RSI": latest.get("Stoch_RSI")
                },
                "volatility_indicators": {
                    "Bollinger_Bands": {
                        "upper": bb_high,
                        "lower": bb_low,
                        "position": bb_position
                    }
                },
                "support_resistance": {
                    "Donchian_High": latest.get("Donchian_High"),
                    "Donchian_Low": latest.get("Donchian_Low"),
                    "Ichimoku_Base": latest.get("Ichimoku_Base")
                },
                "data_source": collection
            }

            return analysis

        cache_key = f"bitcoin_technical_analysis_{timeframe}"
        data, cache_status = self._check_cache_or_fetch(cache_key, fetch)
        data["cache_status"] = cache_status
        return data
