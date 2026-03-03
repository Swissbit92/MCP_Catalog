# src/coordinator/services/mongodb_handlers.py
"""MongoDB tool handlers for multi-asset crypto data and bot state queries.

Supports 13 tokens × 3 timeframes from btc_data database, plus
bot strategy state from btc_bot_state database.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
import logging

from fastapi import HTTPException

from ..config import get_settings
from ..tools.token_registry import (
    get_collection,
    get_token_display_name,
    has_dca_data,
    interpret_indicator,
)

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

    # ── Generalized crypto data handlers ──

    def handle_crypto_current_price(
        self,
        token: str,
        reason: str,
        timeframe: str = "1h",
        include_indicators: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get current price with technical indicators for any supported token."""
        if not self._client:
            raise HTTPException(status_code=503, detail="MongoDB MCP not available")

        collection = get_collection(token, timeframe)
        display_name = get_token_display_name(token)

        def fetch():
            result = self._client.find(
                database="btc_data",
                collection=collection,
                filter={},
                sort={"timestamp": -1},
                limit=1
            )

            if not result or len(result) == 0:
                raise HTTPException(
                    status_code=404,
                    detail=f"No price data found for {display_name} in {collection}"
                )

            latest = result[0]

            # Build response with technical explanations
            indicators_to_include = include_indicators or [
                "RSI", "MACD_Line", "BB_High", "BB_Low", "EMA_20", "EMA_50"
            ]

            indicators_data = {}
            for ind in indicators_to_include:
                if ind in latest:
                    indicators_data[ind] = latest[ind]

            # Core indicator interpretations
            rsi = latest.get("RSI", 0)
            rsi_signal = interpret_indicator("RSI", rsi) or "Unknown"

            macd_hist = latest.get("MACD_Histogram", 0)
            macd_trend = "Bullish crossover" if macd_hist > 0 else "Bearish crossover"

            price = latest.get("Close", 0)
            bb_upper = latest.get("BB_High", 0)
            bb_lower = latest.get("BB_Low", 0)
            bb_mid = (bb_upper + bb_lower) / 2 if bb_upper and bb_lower else 0
            bb_position = "Near upper band" if price > bb_mid else "Near lower band"

            response = {
                "token": token,
                "token_name": display_name,
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
                "data_source": collection,
                "timeframe": timeframe,
            }

            # Extended indicators (only include if present in this collection)
            extended = {}
            for ind_name in [
                "ADX_14", "Supertrend_Direction", "Supertrend_Value",
                "Squeeze_Flag", "Squeeze_Momentum", "HDPR_Signal",
                "FnG_Value", "FnG_Class", "VWAP",
                "CCI_20", "Williams_R_14", "MFI_14", "CHOP_14",
                "CMF_20", "OBV", "ATR_14",
            ]:
                val = latest.get(ind_name)
                if val is not None:
                    interp = interpret_indicator(ind_name, val)
                    extended[ind_name] = {"value": val}
                    if interp:
                        extended[ind_name]["signal"] = interp

            if extended:
                response["indicators"]["extended"] = extended

            return response

        cache_key = f"{token}_current_price_{timeframe}"
        data, cache_status = self._check_cache_or_fetch(cache_key, fetch)
        data["cache_status"] = cache_status
        return data

    def handle_crypto_historical_prices(
        self,
        token: str,
        reason: str,
        start_date: str,
        end_date: Optional[str] = None,
        timeframe: str = "daily",
        indicators: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Query historical price data with date range for any supported token."""
        if not self._client:
            raise HTTPException(status_code=503, detail="MongoDB MCP not available")

        collection = get_collection(token, timeframe)
        display_name = get_token_display_name(token)

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
                "token": token,
                "token_name": display_name,
                "timeframe": timeframe,
                "start_date": start_date,
                "end_date": end_date,
                "count": len(results),
                "data": results,
                "data_source": collection
            }

        cache_key = f"{token}_historical_{start_date}_{end_date}_{timeframe}"
        data, cache_status = self._check_cache_or_fetch(cache_key, fetch)
        data["cache_status"] = cache_status
        return data

    def handle_crypto_trading_summary(
        self,
        token: str,
        reason: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get DCA trading statistics. Only BTC has DCA data."""
        display_name = get_token_display_name(token)

        # Only BTC has DCA purchase history — check before client guard
        # so non-BTC tokens get a graceful message even if client is unavailable
        if not has_dca_data(token):
            return {
                "token": token,
                "token_name": display_name,
                "total_purchased": 0,
                "total_spent": 0,
                "num_purchases": 0,
                "message": f"No DCA purchase history available for {display_name}. "
                           f"Only Bitcoin has DCA tracking in the database.",
                "data_source": None,
                "cache_status": "n/a",
            }

        if not self._client:
            raise HTTPException(status_code=503, detail="MongoDB MCP not available")

        def fetch():
            match_stage = {}
            if start_date or end_date:
                match_stage["timestamp"] = {}
                if start_date:
                    match_stage["timestamp"]["$gte"] = start_date
                if end_date:
                    match_stage["timestamp"]["$lte"] = end_date

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
                    "token": token,
                    "token_name": display_name,
                    "total_btc": 0,
                    "total_usdt_spent": 0,
                    "total_fees": 0,
                    "num_purchases": 0,
                    "data_source": "BTC dayli buying"
                }

            summary = results[0]
            summary["token"] = token
            summary["token_name"] = display_name
            summary["data_source"] = "BTC dayli buying"
            return summary

        cache_key = f"{token}_trading_summary_{start_date}_{end_date}"
        data, cache_status = self._check_cache_or_fetch(cache_key, fetch)
        data["cache_status"] = cache_status
        return data

    def handle_crypto_technical_analysis(
        self,
        token: str,
        reason: str,
        timeframe: str = "hourly",
    ) -> Dict[str, Any]:
        """Multi-timeframe technical analysis for any supported token."""
        if not self._client:
            raise HTTPException(status_code=503, detail="MongoDB MCP not available")

        # Map friendly timeframe names to collection timeframes
        tf_map = {"hourly": "1h", "4h": "4h", "daily": "daily", "1h": "1h"}
        tf_key = tf_map.get(timeframe, "1h")
        collection = get_collection(token, tf_key)
        display_name = get_token_display_name(token)

        def fetch():
            results = self._client.find(
                database="btc_data",
                collection=collection,
                filter={},
                sort={"timestamp": -1},
                limit=1
            )

            if not results or len(results) == 0:
                raise HTTPException(
                    status_code=404,
                    detail=f"No data found for {display_name} in {collection}"
                )

            latest = results[0]

            # Core trend analysis
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
                "token": token,
                "token_name": display_name,
                "price": price,
                "timestamp": latest.get("timestamp"),
                "timeframe": timeframe,
                "trend_indicators": {
                    "EMA_20": ema_20,
                    "EMA_50": ema_50,
                    "EMA_200": ema_200,
                    "trend": trend,
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
                    "Stochastic_RSI": latest.get("Stoch_RSI_K"),
                },
                "volatility_indicators": {
                    "Bollinger_Bands": {
                        "upper": bb_high,
                        "lower": bb_low,
                        "position": bb_position,
                    },
                },
                "support_resistance": {
                    "Donchian_High": latest.get("Donchian_High"),
                    "Donchian_Low": latest.get("Donchian_Low"),
                    "Ichimoku_Base": latest.get("Ichimoku_Base"),
                },
                "data_source": collection,
            }

            # Extended indicators — only include fields present in this collection
            # ADX + Directional Index
            adx = latest.get("ADX_14")
            if adx is not None:
                di_plus = latest.get("DI_Plus_14")
                di_minus = latest.get("DI_Minus_14")
                adx_signal = interpret_indicator("ADX_14", adx) or "Unknown"
                direction = "bullish" if (di_plus or 0) > (di_minus or 0) else "bearish"
                analysis["trend_indicators"]["ADX"] = {
                    "value": adx,
                    "signal": adx_signal,
                    "DI_Plus": di_plus,
                    "DI_Minus": di_minus,
                    "direction": direction,
                }

            # Supertrend
            st_dir = latest.get("Supertrend_Direction")
            if st_dir is not None:
                analysis["trend_indicators"]["Supertrend"] = {
                    "direction": interpret_indicator("Supertrend_Direction", st_dir) or "Unknown",
                    "value": latest.get("Supertrend_Value"),
                }

            # Squeeze
            sq_flag = latest.get("Squeeze_Flag")
            if sq_flag is not None:
                analysis["volatility_indicators"]["Squeeze"] = {
                    "flag": interpret_indicator("Squeeze_Flag", sq_flag) or "Unknown",
                    "momentum": latest.get("Squeeze_Momentum"),
                }

            # HDPR
            hdpr_sig = latest.get("HDPR_Signal")
            if hdpr_sig is not None:
                analysis["momentum_indicators"]["HDPR"] = {
                    "signal": interpret_indicator("HDPR_Signal", hdpr_sig) or "Neutral",
                    "ma": latest.get("HDPR_MA"),
                    "distance": latest.get("HDPR_Distance"),
                }

            # Sentiment (Fear & Greed)
            fng_val = latest.get("FnG_Value")
            if fng_val is not None:
                analysis["sentiment"] = {
                    "fear_greed_index": fng_val,
                    "classification": interpret_indicator("FnG_Value", fng_val) or latest.get("FnG_Class", "Unknown"),
                }

            # VWAP
            vwap = latest.get("VWAP")
            if vwap is not None:
                vwap_bias = "bullish (price > VWAP)" if price > vwap else "bearish (price < VWAP)"
                analysis["support_resistance"]["VWAP"] = {
                    "value": vwap,
                    "bias": vwap_bias,
                }

            # Fibonacci levels
            fib_levels = {}
            for fib in ["Fib_100", "Fib_236", "Fib_382", "Fib_500", "Fib_618"]:
                fval = latest.get(fib)
                if fval is not None:
                    fib_levels[fib] = fval
            if fib_levels:
                analysis["support_resistance"]["Fibonacci"] = fib_levels

            # Volume indicators
            vol_indicators = {}
            for vi_name in ["OBV", "CMF_20", "MFI_14"]:
                vi_val = latest.get(vi_name)
                if vi_val is not None:
                    interp = interpret_indicator(vi_name, vi_val)
                    vol_indicators[vi_name] = {"value": vi_val}
                    if interp:
                        vol_indicators[vi_name]["signal"] = interp
            if vol_indicators:
                analysis["volume_indicators"] = vol_indicators

            # Additional momentum
            for extra in ["CCI_20", "Williams_R_14", "CHOP_14"]:
                ev = latest.get(extra)
                if ev is not None:
                    interp = interpret_indicator(extra, ev)
                    analysis["momentum_indicators"][extra] = {"value": ev}
                    if interp:
                        analysis["momentum_indicators"][extra]["signal"] = interp

            # ATR
            atr = latest.get("ATR_14")
            if atr is not None:
                analysis["volatility_indicators"]["ATR_14"] = atr

            return analysis

        cache_key = f"{token}_technical_{timeframe}"
        data, cache_status = self._check_cache_or_fetch(cache_key, fetch)
        data["cache_status"] = cache_status
        return data

    # ── Bot state handlers (btc_bot_state database) ──

    def handle_bot_status(self) -> Dict[str, Any]:
        """Query btc_bot_state.bot_state — returns all strategy states."""
        if not self._client:
            raise HTTPException(status_code=503, detail="MongoDB MCP not available")

        def fetch():
            results = self._client.find(
                database="btc_bot_state",
                collection="bot_state",
                filter={},
                limit=50
            )
            return {
                "strategies": results,
                "count": len(results),
                "data_source": "btc_bot_state.bot_state",
            }

        data, cache_status = self._check_cache_or_fetch("bot_status", fetch)
        data["cache_status"] = cache_status
        return data

    def handle_bot_positions(self) -> Dict[str, Any]:
        """Query btc_bot_state.my_open_positions — returns active positions."""
        if not self._client:
            raise HTTPException(status_code=503, detail="MongoDB MCP not available")

        def fetch():
            results = self._client.find(
                database="btc_bot_state",
                collection="my_open_positions",
                filter={},
                limit=50
            )
            return {
                "positions": results,
                "count": len(results),
                "data_source": "btc_bot_state.my_open_positions",
            }

        data, cache_status = self._check_cache_or_fetch("bot_positions", fetch)
        data["cache_status"] = cache_status
        return data

    def handle_bot_trades(self, limit: int = 20) -> Dict[str, Any]:
        """Query btc_bot_state.trade_events — returns recent trades."""
        if not self._client:
            raise HTTPException(status_code=503, detail="MongoDB MCP not available")

        def fetch():
            results = self._client.find(
                database="btc_bot_state",
                collection="trade_events",
                filter={},
                sort={"timestamp": -1},
                limit=limit
            )
            return {
                "trades": results,
                "count": len(results),
                "data_source": "btc_bot_state.trade_events",
            }

        cache_key = f"bot_trades_{limit}"
        data, cache_status = self._check_cache_or_fetch(cache_key, fetch)
        data["cache_status"] = cache_status
        return data

    # ── Backward compatibility wrappers ──

    def handle_bitcoin_current_price(
        self,
        reason: str,
        include_indicators: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Backward compat: delegates to handle_crypto_current_price('btc', ...)."""
        return self.handle_crypto_current_price(
            "btc", reason, include_indicators=include_indicators
        )

    def handle_bitcoin_historical_prices(
        self,
        reason: str,
        start_date: str,
        end_date: Optional[str] = None,
        timeframe: str = "daily",
        indicators: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Backward compat: delegates to handle_crypto_historical_prices('btc', ...)."""
        return self.handle_crypto_historical_prices(
            "btc", reason, start_date, end_date, timeframe, indicators
        )

    def handle_bitcoin_trading_summary(
        self,
        reason: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Backward compat: delegates to handle_crypto_trading_summary('btc', ...)."""
        return self.handle_crypto_trading_summary(
            "btc", reason, start_date, end_date
        )

    def handle_bitcoin_technical_analysis(
        self,
        reason: str,
        timeframe: str = "hourly",
    ) -> Dict[str, Any]:
        """Backward compat: delegates to handle_crypto_technical_analysis('btc', ...)."""
        return self.handle_crypto_technical_analysis("btc", reason, timeframe)
