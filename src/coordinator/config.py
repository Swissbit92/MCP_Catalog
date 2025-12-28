# src/coordinator/config.py
"""
Configuration management for MCP Coordinator.

Uses Pydantic BaseSettings for centralized, validated configuration.
Provides both class-based access (settings.field) and function-based
access (get_field()) for backward compatibility.

Phase 1.2 of Persona Quality Enhancement Roadmap.
"""

from __future__ import annotations

import os
import logging
from functools import lru_cache
from typing import Optional, Set

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class OllamaSettings(BaseSettings):
    """Ollama LLM configuration."""

    base: str = Field(
        default="http://127.0.0.1:11434",
        description="Ollama API base URL",
        alias="OLLAMA_BASE"
    )
    model: str = Field(
        default="mistral:latest",
        description="Default model for persona responses (fallback if PERSONA_MODEL not set)",
        alias="PERSONA_MODEL"
    )
    temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Default sampling temperature (0.0-2.0)",
        alias="PERSONA_TEMPERATURE"
    )
    context_window: int = Field(
        default=4096,
        ge=512,
        le=131072,
        description="Model context window size in tokens",
        alias="MODEL_CONTEXT_WINDOW"
    )

    # Operation-specific temperature overrides
    temp_rewrite: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Temperature for first-person rewrites",
        alias="OLLAMA_TEMP_REWRITE"
    )
    temp_summarization: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Temperature for conversation summarization",
        alias="OLLAMA_TEMP_SUMMARIZATION"
    )
    temp_fact_extraction: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Temperature for fact extraction",
        alias="OLLAMA_TEMP_FACT_EXTRACTION"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }


class BraveSettings(BaseSettings):
    """Brave Search MCP configuration."""

    api_key: str = Field(
        default="",
        description="Brave Search API key",
        alias="BRAVE_API_KEY"
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum search results to return",
        alias="BRAVE_MAX_RESULTS"
    )
    safesearch: str = Field(
        default="moderate",
        description="Safe search level: off|moderate|strict",
        alias="BRAVE_SAFESEARCH"
    )
    timeout: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Search timeout in seconds",
        alias="BRAVE_SEARCH_TIMEOUT"
    )
    enabled_rarities: str = Field(
        default="rare,epic,legendary",
        description="Comma-separated list of rarities with search access",
        alias="BRAVE_ENABLED_RARITIES"
    )

    @property
    def enabled(self) -> bool:
        """Check if Brave search is enabled (API key is set)."""
        return bool(self.api_key.strip())

    @property
    def enabled_rarities_set(self) -> Set[str]:
        """Get enabled rarities as a set."""
        if not self.enabled_rarities.strip():
            return set()
        return {r.strip().lower() for r in self.enabled_rarities.split(",") if r.strip()}

    @field_validator('safesearch')
    @classmethod
    def validate_safesearch(cls, v: str) -> str:
        """Validate safesearch value."""
        valid_values = {"off", "moderate", "strict"}
        if v.lower() not in valid_values:
            logger.warning(f"Invalid BRAVE_SAFESEARCH '{v}', defaulting to 'moderate'")
            return "moderate"
        return v.lower()

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }


class MemorySettings(BaseSettings):
    """Memory and RAG configuration (Phase 3)."""

    embedding_model: str = Field(
        default="nomic-embed-text:latest",
        description="Ollama embedding model for RAG semantic search",
        alias="MEMORY_EMBEDDING_MODEL"
    )
    summarization_interval: int = Field(
        default=30,
        ge=5,
        le=100,
        description="Number of messages before triggering auto-summarization",
        alias="MEMORY_SUMMARIZATION_INTERVAL"
    )
    fact_extraction_interval: int = Field(
        default=10,
        ge=5,
        le=50,
        description="Number of messages before triggering fact extraction",
        alias="MEMORY_FACT_EXTRACTION_INTERVAL"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }


class MongoDBSettings(BaseSettings):
    """MongoDB MCP configuration."""

    enabled: bool = Field(
        default=False,
        description="Enable MongoDB MCP integration",
        alias="MONGODB_ENABLED"
    )
    uri: str = Field(
        default="",
        description="MongoDB connection URI",
        alias="MONGODB_URI"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Operation timeout in seconds",
        alias="MONGODB_TIMEOUT"
    )
    max_response_bytes: int = Field(
        default=100000,
        ge=1000,
        le=10000000,
        description="Maximum response size in bytes",
        alias="MONGODB_MAX_RESPONSE_BYTES"
    )
    enabled_rarities: str = Field(
        default="epic,legendary",
        description="Comma-separated list of rarities with MongoDB access",
        alias="MONGODB_ENABLED_RARITIES"
    )
    cache_current_price: int = Field(
        default=60,
        ge=0,
        description="Cache TTL for current price queries",
        alias="MONGODB_CACHE_CURRENT_PRICE"
    )
    cache_technical: int = Field(
        default=60,
        ge=0,
        description="Cache TTL for technical analysis queries",
        alias="MONGODB_CACHE_TECHNICAL"
    )
    cache_historical: int = Field(
        default=3600,
        ge=0,
        description="Cache TTL for historical price queries",
        alias="MONGODB_CACHE_HISTORICAL"
    )
    cache_trading: int = Field(
        default=300,
        ge=0,
        description="Cache TTL for trading summary queries",
        alias="MONGODB_CACHE_TRADING"
    )

    @property
    def is_enabled(self) -> bool:
        """Check if MongoDB is enabled (flag true and URI set)."""
        return self.enabled and bool(self.uri.strip())

    @property
    def enabled_rarities_set(self) -> Set[str]:
        """Get enabled rarities as a set."""
        if not self.enabled_rarities.strip():
            return set()
        return {r.strip().lower() for r in self.enabled_rarities.split(",") if r.strip()}

    def get_cache_ttl(self, tool_name: str) -> int:
        """Get cache TTL for a specific tool."""
        ttl_map = {
            "bitcoin_current_price": self.cache_current_price,
            "bitcoin_technical_analysis": self.cache_technical,
            "bitcoin_historical_prices": self.cache_historical,
            "bitcoin_trading_summary": self.cache_trading,
        }
        return ttl_map.get(tool_name, 60)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }


class CoordinatorSettings(BaseSettings):
    """Main coordinator configuration.

    Aggregates all subsystem settings into a single settings object.
    Access via `settings` singleton or `get_settings()` function.
    """

    # Core settings
    persona_dir: str = Field(
        default="personas",
        description="Directory containing persona JSON files",
        alias="PERSONA_DIR"
    )
    coord_port: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        description="Coordinator server port",
        alias="COORD_PORT"
    )
    coord_url: str = Field(
        default="http://127.0.0.1:8000",
        description="Coordinator base URL",
        alias="COORD_URL"
    )
    db_path: str = Field(
        default="chats.db",
        description="SQLite database path",
        alias="COORDINATOR_DB_PATH"
    )

    # Subsystem settings (nested)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    brave: BraveSettings = Field(default_factory=BraveSettings)
    mongodb: MongoDBSettings = Field(default_factory=MongoDBSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }


@lru_cache(maxsize=1)
def get_settings() -> CoordinatorSettings:
    """Get the singleton settings instance.

    Uses lru_cache to ensure settings are only loaded once.
    """
    return CoordinatorSettings()


# Singleton instance for direct attribute access
settings = get_settings()


# ============================================================================
# BACKWARD COMPATIBILITY FUNCTIONS
# These functions maintain compatibility with existing code that uses the
# function-based API. They delegate to the Pydantic settings object.
# ============================================================================


def _required(name: str) -> str:
    """Legacy helper for required env vars (kept for compatibility)."""
    val = os.getenv(name, "").strip()
    if not val:
        raise RuntimeError(
            f"Missing required environment variable: {name}\n"
            f"Set it in your .env (e.g. {name}=value)"
        )
    return val


def get_ollama_base() -> str:
    """Get Ollama base URL."""
    return settings.ollama.base


def get_persona_model() -> str:
    """Get default persona model."""
    return settings.ollama.model


def get_persona_dir() -> str:
    """Get persona directory path."""
    return settings.persona_dir


def get_persona_temperature() -> float:
    """Get default sampling temperature."""
    return settings.ollama.temperature


def get_model_context_window() -> int:
    """Get model context window size in tokens."""
    return settings.ollama.context_window


# Brave MCP Configuration
def get_brave_api_key() -> str:
    """Get Brave API key."""
    return settings.brave.api_key


def get_brave_max_results() -> int:
    """Get max results for Brave search."""
    return settings.brave.max_results


def get_brave_safesearch() -> str:
    """Get Brave safesearch setting."""
    return settings.brave.safesearch


def get_brave_search_timeout() -> int:
    """Get Brave search timeout in seconds."""
    return settings.brave.timeout


def get_brave_enabled_rarities() -> set:
    """Get set of persona rarities with web search enabled."""
    return settings.brave.enabled_rarities_set


def is_brave_enabled() -> bool:
    """Check if Brave MCP is enabled."""
    return settings.brave.enabled


# MongoDB MCP Configuration
def get_mongodb_uri() -> str:
    """Get MongoDB connection URI."""
    return settings.mongodb.uri


def get_mongodb_timeout() -> int:
    """Get MongoDB operation timeout in seconds."""
    return settings.mongodb.timeout


def get_mongodb_max_response_bytes() -> int:
    """Get max response size in bytes."""
    return settings.mongodb.max_response_bytes


def get_mongodb_enabled_rarities() -> set:
    """Get set of persona rarities with MongoDB access enabled."""
    return settings.mongodb.enabled_rarities_set


def is_mongodb_enabled() -> bool:
    """Check if MongoDB MCP is enabled."""
    return settings.mongodb.is_enabled


def get_mongodb_cache_ttl(tool_name: str) -> int:
    """Get cache TTL for a specific MongoDB tool."""
    return settings.mongodb.get_cache_ttl(tool_name)


# Memory & RAG Configuration
def get_embedding_model() -> str:
    """Get Ollama embedding model for RAG semantic search."""
    return settings.memory.embedding_model


def get_summarization_interval() -> int:
    """Get number of messages before triggering auto-summarization."""
    return settings.memory.summarization_interval


def get_fact_extraction_interval() -> int:
    """Get number of messages before triggering fact extraction."""
    return settings.memory.fact_extraction_interval


# Ollama Temperature Overrides
def get_temp_rewrite() -> float:
    """Get temperature for first-person rewrites."""
    return settings.ollama.temp_rewrite


def get_temp_summarization() -> float:
    """Get temperature for conversation summarization."""
    return settings.ollama.temp_summarization


def get_temp_fact_extraction() -> float:
    """Get temperature for fact extraction."""
    return settings.ollama.temp_fact_extraction


def get_persona_temperature_override(persona_card: dict) -> float:
    """Get persona-specific temperature or fallback to global default.

    Args:
        persona_card: Persona dictionary from JSON (must contain model_preferences)

    Returns:
        Per-persona temperature if defined, otherwise global PERSONA_TEMPERATURE

    Example:
        >>> card = {"model_preferences": {"temperature": 0.7}}
        >>> get_persona_temperature_override(card)
        0.7
        >>> get_persona_temperature_override({})  # Uses global default
        0.9
    """
    model_prefs = persona_card.get("model_preferences", {})
    if isinstance(model_prefs, dict) and "temperature" in model_prefs:
        temp = model_prefs["temperature"]
        # Validate it's a reasonable number
        if isinstance(temp, (int, float)) and 0.0 <= temp <= 2.0:
            return float(temp)
        else:
            logger.warning(
                f"Invalid temperature in persona model_preferences: {temp}. "
                f"Using global default {settings.ollama.temperature}"
            )

    # Fallback to global setting
    return settings.ollama.temperature
