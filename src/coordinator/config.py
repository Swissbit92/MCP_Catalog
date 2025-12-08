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
