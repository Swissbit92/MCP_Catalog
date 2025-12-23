# src/coordinator/config.py
# Configuration utilities for GraphRAG Local QA Chat with Personas
# Functions to retrieve required environment variables.
# Uses python-dotenv to load .env files.

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def _required(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        raise RuntimeError(
            f"Missing required environment variable: {name}\n"
            f"Set it in your .env (e.g. {name}=value)"
        )
    return val

def get_ollama_base() -> str:
    return _required("OLLAMA_BASE")

def get_persona_model() -> str:
    return _required("PERSONA_MODEL")

def get_persona_dir() -> str:
    return os.getenv("PERSONA_DIR", "personas")

def get_persona_temperature() -> float:
    try:
        return float(os.getenv("PERSONA_TEMPERATURE", "0.1"))
    except ValueError:
        return 0.1

def get_model_context_window() -> int:
    """Get model context window size in tokens (default 4096)."""
    try:
        return int(os.getenv("MODEL_CONTEXT_WINDOW", "4096"))
    except ValueError:
        return 4096

# Brave MCP Configuration
def get_brave_api_key() -> str:
    """Get Brave API key (required if Brave MCP is enabled)."""
    return os.getenv("BRAVE_API_KEY", "").strip()

def get_brave_max_results() -> int:
    """Get max results for Brave search (default 5)."""
    try:
        return int(os.getenv("BRAVE_MAX_RESULTS", "5"))
    except ValueError:
        return 5

def get_brave_safesearch() -> str:
    """Get Brave safesearch setting (off, moderate, strict)."""
    return os.getenv("BRAVE_SAFESEARCH", "moderate").strip()

def get_brave_search_timeout() -> int:
    """Get Brave search timeout in seconds (default 10)."""
    try:
        return int(os.getenv("BRAVE_SEARCH_TIMEOUT", "10"))
    except ValueError:
        return 10

def get_brave_enabled_rarities() -> set:
    """Get set of persona rarities that have web search enabled."""
    rarities_str = os.getenv("BRAVE_ENABLED_RARITIES", "rare,epic,legendary").strip()
    if not rarities_str:
        return set()
    return {r.strip().lower() for r in rarities_str.split(",") if r.strip()}

def is_brave_enabled() -> bool:
    """Check if Brave MCP is enabled (API key is set)."""
    return bool(get_brave_api_key())

# MongoDB MCP Configuration
def get_mongodb_uri() -> str:
    """Get MongoDB connection URI (required if MongoDB MCP is enabled)."""
    return os.getenv("MONGODB_URI", "").strip()

def get_mongodb_timeout() -> int:
    """Get MongoDB operation timeout in seconds (default 30)."""
    try:
        return int(os.getenv("MONGODB_TIMEOUT", "30"))
    except ValueError:
        return 30

def get_mongodb_max_response_bytes() -> int:
    """Get max response size in bytes (default 100KB)."""
    try:
        return int(os.getenv("MONGODB_MAX_RESPONSE_BYTES", "100000"))
    except ValueError:
        return 100000

def get_mongodb_enabled_rarities() -> set:
    """Get set of persona rarities that have MongoDB access enabled."""
    rarities_str = os.getenv("MONGODB_ENABLED_RARITIES", "epic,legendary").strip()
    if not rarities_str:
        return set()
    return {r.strip().lower() for r in rarities_str.split(",") if r.strip()}

def is_mongodb_enabled() -> bool:
    """Check if MongoDB MCP is enabled (URI is set and feature flag is true)."""
    enabled_flag = os.getenv("MONGODB_ENABLED", "false").lower() in ("true", "1", "yes")
    has_uri = bool(get_mongodb_uri())
    return enabled_flag and has_uri

# Cache TTL Configuration
def get_mongodb_cache_ttl(tool_name: str) -> int:
    """Get cache TTL for a specific MongoDB tool (in seconds)."""
    ttl_map = {
        "bitcoin_current_price": int(os.getenv("MONGODB_CACHE_CURRENT_PRICE", "60")),
        "bitcoin_technical_analysis": int(os.getenv("MONGODB_CACHE_TECHNICAL", "60")),
        "bitcoin_historical_prices": int(os.getenv("MONGODB_CACHE_HISTORICAL", "3600")),
        "bitcoin_trading_summary": int(os.getenv("MONGODB_CACHE_TRADING", "300")),
    }
    return ttl_map.get(tool_name, 60)  # Default 60s
