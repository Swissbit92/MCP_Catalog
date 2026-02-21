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


def _parse_rarities(csv: str) -> Set[str]:
    """Parse a comma-separated rarity string into a lowercase set."""
    if not csv.strip():
        return set()
    return {r.strip().lower() for r in csv.split(",") if r.strip()}


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
    # Per-persona mcp_access field in persona JSON takes priority over these rarity-based settings
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
        return _parse_rarities(self.enabled_rarities)

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
    # Per-persona mcp_access field in persona JSON takes priority over these rarity-based settings
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
        return _parse_rarities(self.enabled_rarities)

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


class JupiterSettings(BaseSettings):
    """Jupiter DEX + Solana wallet configuration."""

    enabled: bool = Field(
        default=False,
        description="Enable Jupiter wallet integration",
        alias="JUPITER_ENABLED"
    )
    mcp_image: str = Field(
        default="localhost/jupiter-mcp:latest",
        description="Docker image for Jupiter MCP server",
        alias="JUPITER_MCP_IMAGE"
    )
    slippage_bps: int = Field(
        default=50,
        ge=0,
        le=10000,
        description="Default slippage tolerance in basis points",
        alias="JUPITER_SLIPPAGE_BPS"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Jupiter MCP operation timeout in seconds",
        alias="JUPITER_TIMEOUT"
    )
    solana_rpc_url: str = Field(
        default="https://api.devnet.solana.com",
        description="Solana RPC URL (devnet by default for safety)",
        alias="SOLANA_RPC_URL"
    )
    strategies_dir: str = Field(
        default="strategies",
        description="Directory containing strategy JSON files",
        alias="STRATEGIES_DIR"
    )
    mongodb_write_uri: str = Field(
        default="",
        description="MongoDB URI for writing trade history",
        alias="MONGODB_WRITE_URI"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }


class EmailSettings(BaseSettings):
    """Email notification configuration for trade alerts."""

    enabled: bool = Field(
        default=False,
        description="Enable email trade notifications",
        alias="EMAIL_ENABLED"
    )
    smtp_host: str = Field(
        default="smtp.gmail.com",
        description="SMTP server hostname",
        alias="EMAIL_SMTP_HOST"
    )
    smtp_port: int = Field(
        default=587,
        ge=1,
        le=65535,
        description="SMTP server port",
        alias="EMAIL_SMTP_PORT"
    )
    username: str = Field(
        default="",
        description="SMTP username/email",
        alias="EMAIL_USERNAME"
    )
    password: str = Field(
        default="",
        description="SMTP password or app password",
        alias="EMAIL_PASSWORD"
    )
    from_addr: str = Field(
        default="",
        description="From email address",
        alias="EMAIL_FROM"
    )
    to_addr: str = Field(
        default="",
        description="Recipient email address for trade notifications",
        alias="EMAIL_TO"
    )

    @property
    def is_enabled(self) -> bool:
        """Check if email notifications are configured."""
        return self.enabled and bool(self.username.strip()) and bool(self.to_addr.strip())

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }


class AuthSettings(BaseSettings):
    """Google OAuth and JWT configuration."""

    google_client_id: str = Field(
        default="",
        description="Google OAuth Client ID",
        alias="GOOGLE_CLIENT_ID"
    )
    jwt_secret_key: str = Field(
        default="dev-secret-change-in-production-min-32-chars!!",
        description="Secret key for signing JWT tokens",
        alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm",
        alias="JWT_ALGORITHM"
    )
    jwt_expire_hours: int = Field(
        default=1,
        ge=1,
        le=168,
        description="Access token expiry in hours",
        alias="JWT_EXPIRE_HOURS"
    )
    refresh_expire_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Refresh token expiry in days",
        alias="JWT_REFRESH_EXPIRE_DAYS"
    )
    auth_required: bool = Field(
        default=False,
        description="Require authentication (set True in production)",
        alias="AUTH_REQUIRED"
    )
    auth_env: str = Field(
        default="development",
        description="Environment: development or production",
        alias="AUTH_ENV"
    )

    @property
    def cookie_secure(self) -> bool:
        """Use secure cookies in production (requires HTTPS)."""
        return self.auth_env == "production"

    @property
    def is_google_configured(self) -> bool:
        """Check if Google OAuth credentials are set."""
        return bool(self.google_client_id.strip())

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
        default="data/chats.db",
        description="SQLite database path",
        alias="COORDINATOR_DB_PATH"
    )

    # Subsystem settings (nested)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    brave: BraveSettings = Field(default_factory=BraveSettings)
    mongodb: MongoDBSettings = Field(default_factory=MongoDBSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    jupiter: JupiterSettings = Field(default_factory=JupiterSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)

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
# HELPER FUNCTIONS
# ============================================================================


def get_persona_temperature_override(persona_card: dict) -> float:
    """Get persona-specific temperature or fallback to global default.

    Args:
        persona_card: Persona dictionary from JSON (must contain model_preferences)

    Returns:
        Per-persona temperature if defined, otherwise global PERSONA_TEMPERATURE
    """
    model_prefs = persona_card.get("model_preferences", {})
    if isinstance(model_prefs, dict) and "temperature" in model_prefs:
        temp = model_prefs["temperature"]
        if isinstance(temp, (int, float)) and 0.0 <= temp <= 2.0:
            return float(temp)
        else:
            logger.warning(
                f"Invalid temperature in persona model_preferences: {temp}. "
                f"Using global default {settings.ollama.temperature}"
            )

    return settings.ollama.temperature
