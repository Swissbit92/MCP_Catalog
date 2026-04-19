# src/coordinator/tools/token_registry.py
"""Token registry and indicator catalog for multi-asset MongoDB queries.

Centralizes token resolution, collection naming, and indicator interpretation
for 13 supported cryptocurrencies across 3 timeframes.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

# ── 13 supported tokens with aliases for natural language resolution ──

SUPPORTED_TOKENS: Dict[str, Dict] = {
    "btc":  {"name": "Bitcoin",       "aliases": ["bitcoin", "btc"]},
    "eth":  {"name": "Ethereum",      "aliases": ["ethereum", "ether", "eth"]},
    "sol":  {"name": "Solana",        "aliases": ["solana", "sol"]},
    "xrp":  {"name": "Ripple",        "aliases": ["ripple", "xrp"]},
    "ada":  {"name": "Cardano",       "aliases": ["cardano", "ada"]},
    "avax": {"name": "Avalanche",     "aliases": ["avalanche", "avax"]},
    "bnb":  {"name": "BNB",           "aliases": ["binance coin", "binance", "bnb"]},
    "doge": {"name": "Dogecoin",      "aliases": ["dogecoin", "doge"]},
    "dot":  {"name": "Polkadot",      "aliases": ["polkadot", "dot"]},
    "link": {"name": "Chainlink",     "aliases": ["chainlink", "link"]},
    "near": {"name": "NEAR Protocol", "aliases": ["near protocol", "near"]},
    "sui":  {"name": "Sui",           "aliases": ["sui"]},
    "ton":  {"name": "Toncoin",       "aliases": ["toncoin", "ton"]},
}

TIMEFRAMES = ["1h", "4h", "daily"]

# BTC also has legacy unprefixed collections (different schema/data range)
BTC_LEGACY_COLLECTIONS = {
    "1h_legacy": "1h_price_data",
    "daily_legacy": "daily_price_data",
}

# Build a reverse lookup: alias -> ticker (longest aliases first to avoid partial matches)
_ALIAS_TO_TICKER: List[tuple[str, str]] = []
for ticker, meta in SUPPORTED_TOKENS.items():
    for alias in meta["aliases"]:
        _ALIAS_TO_TICKER.append((alias, ticker))
# Sort by alias length descending so "binance coin" matches before "binance"
_ALIAS_TO_TICKER.sort(key=lambda x: len(x[0]), reverse=True)

# Pre-compiled word boundary patterns for each alias
_ALIAS_PATTERNS: List[tuple[re.Pattern, str]] = [
    (re.compile(r'\b' + re.escape(alias) + r'\b', re.IGNORECASE), ticker)
    for alias, ticker in _ALIAS_TO_TICKER
]


def resolve_token(query: str) -> Optional[str]:
    """Extract a supported token ticker from natural language query.

    Returns the first matching ticker (longest alias wins), or None if
    no supported token is mentioned.

    Examples:
        >>> resolve_token("what's the ethereum price?")
        'eth'
        >>> resolve_token("show me SOL 4h RSI")
        'sol'
        >>> resolve_token("how's the weather?")
        None
    """
    for pattern, ticker in _ALIAS_PATTERNS:
        if pattern.search(query):
            return ticker
    return None


def resolve_timeframe(query: str) -> str:
    """Extract timeframe from query, defaulting to '1h'.

    Examples:
        >>> resolve_timeframe("BTC 4h chart analysis")
        '4h'
        >>> resolve_timeframe("daily price of ETH")
        'daily'
        >>> resolve_timeframe("what's the BTC price?")
        '1h'
    """
    q = query.lower()
    if "4h" in q or "4 hour" in q or "four hour" in q:
        return "4h"
    if "daily" in q or "day " in q or "1d " in q or "24h" in q:
        return "daily"
    return "1h"


def get_collection(token: str, timeframe: str = "1h") -> str:
    """Build MongoDB collection name from token and timeframe.

    Args:
        token: Lowercase ticker (e.g., 'btc', 'eth')
        timeframe: One of '1h', '4h', 'daily'

    Returns:
        Collection name (e.g., 'eth_4h_price_data')
    """
    return f"{token}_{timeframe}_price_data"


def get_token_display_name(token: str) -> str:
    """Get human-readable display name for a token.

    >>> get_token_display_name("eth")
    'Ethereum'
    >>> get_token_display_name("unknown")
    'UNKNOWN'
    """
    meta = SUPPORTED_TOKENS.get(token)
    return meta["name"] if meta else token.upper()


def get_supported_token_list() -> List[str]:
    """Return list of all supported token tickers for tool enum values."""
    return list(SUPPORTED_TOKENS.keys())


def has_dca_data(token: str) -> bool:
    """Check if token has DCA (Dollar Cost Averaging) purchase data.

    Only BTC has the 'BTC dayli buying' collection.
    """
    return token == "btc"


# ── Indicator catalog: 80 indicators across 10 categories ──

INDICATOR_CATEGORIES: Dict[str, List[str]] = {
    "trend": [
        "ADX_14", "Aroon_Up", "Aroon_Down", "Aroon_Osc",
        "DI_Plus_14", "DI_Minus_14",
        "EMA_20", "EMA_50", "EMA_100", "EMA_200", "HMA_20",
        "Ichimoku_A", "Ichimoku_B", "Ichimoku_Base", "Ichimoku_Conversion",
        "KAMA_10", "PSAR",
        "SMA_50", "SMA_100", "SMA_200",
        "Supertrend_Value", "Supertrend_Direction",
    ],
    "momentum": [
        "RSI", "MACD_Line", "MACD_Signal", "MACD_Histogram",
        "Stoch_K", "Stoch_D", "Stoch_RSI_K", "Stoch_RSI_D",
        "CCI_20", "TRIX_18", "Williams_R_14",
    ],
    "volume": ["OBV", "CMF_20", "MFI_14"],
    "volatility": [
        "ATR_14", "NATR_14", "BB_High", "BB_Low", "CHOP_14",
        "Donchian_High", "Donchian_Low", "Donchian_Mid",
        "Parkinson_Vol_14", "Realized_Vol_14", "Realized_Vol_30",
        "Vol_Ratio_14_30", "Squeeze_Flag", "Squeeze_Momentum",
    ],
    "price_levels": ["Fib_100", "Fib_236", "Fib_382", "Fib_500", "Fib_618", "VWAP"],
    "sentiment": ["FnG_Value", "FnG_Class"],
    "custom": ["HDPR_MA", "HDPR_Distance", "HDPR_Signal"],
    "log_returns": ["LogReturn_1", "LogReturn_4", "LogReturn_12", "LogReturn_24"],
    "ml_features": [
        "BB_Width", "Candle_Body_Ratio", "Close_ZScore_100",
        "Lower_Wick_Ratio", "MACD_Slope_3", "Price_vs_EMA20",
        "Price_vs_SMA200", "RSI_Slope_3", "RSI_ZScore_100",
        "Upper_Wick_Ratio", "Volume_ZScore_100",
    ],
    "temporal": ["Hour_Sin", "Hour_Cos", "DOW_Sin", "DOW_Cos"],
}

# Flat list of all indicator names for validation
ALL_INDICATORS: List[str] = [ind for cat in INDICATOR_CATEGORIES.values() for ind in cat]


# ── Indicator interpretation logic ──

def interpret_indicator(name: str, value) -> Optional[str]:
    """Return a human-readable interpretation for an indicator value.

    Returns None if the indicator is not recognized or value is None.
    """
    if value is None:
        return None

    try:
        v = float(value)
    except (TypeError, ValueError):
        # String-valued indicators (e.g., FnG_Class)
        if name == "FnG_Class":
            return str(value)
        return None

    if name == "RSI":
        if v > 70:
            return "Overbought"
        elif v < 30:
            return "Oversold"
        elif v > 50:
            return "Neutral-Bullish"
        else:
            return "Neutral-Bearish"

    elif name == "ADX_14":
        if v > 50:
            return "Very strong trend"
        elif v > 25:
            return "Trending"
        elif v > 20:
            return "Weak trend"
        else:
            return "Ranging/No trend"

    elif name == "Supertrend_Direction":
        return "Uptrend" if v > 0 else "Downtrend"

    elif name == "Squeeze_Flag":
        return "Consolidation (BB inside Keltner)" if v == 1 else "Expanded (no squeeze)"

    elif name == "HDPR_Signal":
        if v > 0:
            return "Oversold / Buy signal"
        elif v < 0:
            return "Overbought / Sell signal"
        else:
            return "Neutral"

    elif name == "FnG_Value":
        if v >= 75:
            return "Extreme Greed"
        elif v >= 55:
            return "Greed"
        elif v >= 45:
            return "Neutral"
        elif v >= 25:
            return "Fear"
        else:
            return "Extreme Fear"

    elif name == "CCI_20":
        if v > 100:
            return "Overbought"
        elif v < -100:
            return "Oversold"
        else:
            return "Neutral"

    elif name == "Williams_R_14":
        if v > -20:
            return "Overbought"
        elif v < -80:
            return "Oversold"
        else:
            return "Neutral"

    elif name == "MFI_14":
        if v > 80:
            return "Overbought"
        elif v < 20:
            return "Oversold"
        else:
            return "Neutral"

    elif name == "CHOP_14":
        if v > 61.8:
            return "Choppy/Ranging"
        elif v < 38.2:
            return "Trending"
        else:
            return "Indeterminate"

    elif name == "CMF_20":
        if v > 0.05:
            return "Accumulation"
        elif v < -0.05:
            return "Distribution"
        else:
            return "Neutral"

    return None
