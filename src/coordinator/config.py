# src/coordinator/config.py
"""
Configuration management for MCP Coordinator.

Uses Pydantic BaseSettings for centralized, validated configuration.
Provides both class-based access (settings.field) and function-based
access (get_field()) for backward compatibility.

Phase 1.2 of Persona Quality Enhancement Roadmap.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

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
        default="gemma2:9b-instruct-q5_K_M",
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
    min_p: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Default Min-P sampling threshold (0.0 = disabled). "
                    "Dynamically filters low-probability tokens based on top token confidence.",
        alias="PERSONA_MIN_P"
    )
    context_window: int = Field(
        default=4096,
        ge=512,
        le=131072,
        description="Model context window size in tokens",
        alias="MODEL_CONTEXT_WINDOW"
    )
    max_output_tokens: int = Field(
        default=400,
        ge=64,
        le=4096,
        description=(
            "Hard cap on generated tokens per turn (Ollama num_predict). Turn latency "
            "is ~linear in output tokens (~16 tok/s on the 24B), so an unbounded reply "
            "can run 30s+. Generous backstop — normal texting-style replies sit well "
            "under it; persona response-format guidance drives typical brevity."
        ),
        alias="MODEL_MAX_OUTPUT_TOKENS"
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
        default=20,
        ge=1,
        le=60,
        description=(
            "Search timeout in seconds. Covers the ephemeral `docker run` container "
            "cold-start + Brave API call. 10s was too tight on a cold image pull "
            "(silently returned no results); 20s gives margin once the image is cached."
        ),
        alias="BRAVE_SEARCH_TIMEOUT"
    )

    @property
    def enabled(self) -> bool:
        """Check if Brave search is enabled (API key is set)."""
        return bool(self.api_key.strip())

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
        default="bge-m3:latest",
        description="Ollama embedding model for RAG semantic search "
                    "(bge-m3: 8192-token native context, dense+sparse)",
        alias="MEMORY_EMBEDDING_MODEL"
    )
    embedding_max_tokens: int = Field(
        default=8192,
        ge=256,
        le=40960,
        description="Native input window of the embedding model. Text is "
                    "chunked/truncated below a safety margin of this before "
                    "embedding to avoid Ollama HTTP 500 overflow errors. "
                    "(bge-m3=8192, nomic-embed-text=2048, qwen3-embedding=32768)",
        alias="MEMORY_EMBEDDING_MAX_TOKENS"
    )
    embedding_chunk_overlap_tokens: int = Field(
        default=128,
        ge=0,
        le=1024,
        description="Token overlap between chunks when an oversized message is "
                    "split before embedding (preserves cross-chunk context)",
        alias="MEMORY_EMBEDDING_CHUNK_OVERLAP_TOKENS"
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
    prewarm_sessions: int = Field(
        default=10,
        ge=0,
        le=200,
        description="ADR-006 M1: number of most-recently-updated sessions to "
                    "pre-index into the FAISS store at startup (background daemon "
                    "thread). The index is otherwise rebuilt lazily from SQLite on "
                    "first chat per session — pre-warming only removes that one-time "
                    "cold-start re-index latency after a restart. 0 disables.",
        alias="MEMORY_PREWARM_SESSIONS"
    )

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


class RoutingSettings(BaseSettings):
    """Intent-routing / semantic-router configuration.

    Phase 0 of the HERMES-Agents track: optionally promote the bge-m3 semantic
    router to PRIMARY intent classification. When ``semantic_primary`` is False
    (default) the legacy keyword-first order is preserved byte-for-byte.
    """

    semantic_primary: bool = Field(
        default=False,
        description=(
            "Promote the bge-m3 semantic router to primary intent classification. "
            "False (default) keeps the legacy keyword-first order unchanged. "
            "Set ROUTING_SEMANTIC_PRIMARY=true to enable."
        ),
        alias="ROUTING_SEMANTIC_PRIMARY",
    )
    semantic_threshold: float = Field(
        default=0.66,
        ge=0.50,
        le=1.0,
        description=(
            "Cosine confidence floor for the semantic-PRIMARY path (only used when "
            "semantic_primary=True). Empirically tuned for bge-m3 max-over-examples "
            "scoring via tests/evaluation/tune_routing_threshold.py on a HELD-OUT set "
            "(acc 0.91, wallet precision 1.0, wallet recall 0.96 at 0.66). The legacy "
            "fallback path keeps its own 0.75 centroid threshold."
        ),
        alias="ROUTING_SEMANTIC_THRESHOLD",
    )
    semantic_margin: float = Field(
        default=0.0,
        ge=0.0,
        le=0.5,
        description=(
            "Minimum gap (top - 2nd centroid score) to accept a route; below it the "
            "query falls through to NEEDS_NEITHER. 0.0 (default) disables the gate "
            "— the sweep found no accuracy gain from it on the current eval set."
        ),
        alias="ROUTING_SEMANTIC_MARGIN",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }


class LoreSettings(BaseSettings):
    """On-demand hybrid lore retrieval configuration (HERMES-Agents Phase 2).

    When ``ondemand_enabled`` is False (default) the static 3-entity-per-persona
    lore prefill is the only lore in the prompt — byte-identical to pre-Phase-2.
    """

    ondemand_enabled: bool = Field(
        default=False,
        description=(
            "Enable per-turn hybrid lore retrieval (keyword + bge-m3) appended to the "
            "system prompt. False (default) = static 3-entity core only, byte-identical. "
            "Set LORE_ONDEMAND_ENABLED=true to enable."
        ),
        alias="LORE_ONDEMAND_ENABLED",
    )
    retrieval_k: int = Field(
        default=5, ge=1, le=20,
        description="Number of lore entries to retrieve per semantic (Tier-2b) query.",
        alias="LORE_RETRIEVAL_K",
    )
    embed_min_relevance: float = Field(
        default=0.5, ge=0.3, le=0.9,
        description=(
            "Cosine floor for embedding-tier lore retrieval. Same bge-m3 calibration "
            "as memory RAG min_relevance (0.5 recall-leaning floor)."
        ),
        alias="LORE_EMBED_MIN_RELEVANCE",
    )
    keyword_window_messages: int = Field(
        default=4, ge=1, le=10,
        description="How many recent messages to scan for keyword/alias matches (Tier-2a).",
        alias="LORE_KEYWORD_WINDOW",
    )
    max_budget_tokens: int = Field(
        default=600, ge=100, le=2000,
        description="Soft token ceiling for the <dynamic_lore> block; lowest-priority entries drop first.",
        alias="LORE_MAX_BUDGET_TOKENS",
    )
    rank_context_enabled: bool = Field(
        default=False,
        description="Inject a seeker-rank narrative block into the per-turn system prompt for NEPHILIM personas.",
        alias="LORE_RANK_CONTEXT_ENABLED",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }


class AgentSettings(BaseSettings):
    """Persona-safe agentic behaviour configuration (HERMES-Agents Phase 3).

    Gates single-action, in-character tool use where ALL enforcement is
    deterministic middleware, never LLM self-policing. When ``enabled`` is False
    (default) the existing handle_brave_query / handle_wallet_query paths run
    unchanged — byte-identical to pre-Phase-3.

    The two safety flags (``argument_allowlist`` / ``injection_guard``) default
    True so the interceptor and injection guard harden the EXISTING tool paths
    even before ``enabled`` is flipped, at zero functional cost when off.
    """

    enabled: bool = Field(
        default=False,
        description=(
            "Enable persona-safe single-action agentic tool calls (the two-stage "
            "pipeline). False (default) = byte-identical to pre-Phase-3. "
            "Set AGENTIC_ENABLED=true to enable."
        ),
        alias="AGENTIC_ENABLED",
    )
    argument_allowlist: bool = Field(
        default=True,
        description=(
            "Enforce the per-tool argument-level allowlist in the tool-call "
            "interceptor. Default ON — disabling drops to mcp_access checks only "
            "(removes the argument schema validation layer)."
        ),
        alias="AGENTIC_ARGUMENT_ALLOWLIST",
    )
    injection_guard: bool = Field(
        default=True,
        description=(
            "Block tool triggers sourced from RAG/lore context and sanitize "
            "memory writes (trust hierarchy: system > user > retrieved). Default "
            "ON — shippable independently of AGENTIC_ENABLED."
        ),
        alias="AGENTIC_INJECTION_GUARD",
    )
    trigger_similarity_threshold: float = Field(
        default=0.85,
        ge=0.5,
        le=1.0,
        description=(
            "Cosine floor above which a proposed tool argument is treated as "
            "mirroring retrieved (RAG/lore) content — i.e. a suspected indirect "
            "injection. bge-m3 scoring, reuses the RAG embedder."
        ),
        alias="AGENTIC_TRIGGER_SIMILARITY_THRESHOLD",
    )
    extraction_coherence_threshold: float = Field(
        default=0.55,
        ge=0.3,
        le=0.9,
        description=(
            "Cosine floor for the argument-extraction semantic gate: an extracted "
            "argument must be this topically related to the user message or the "
            "extraction is rejected (catches well-formed-but-hallucinated values)."
        ),
        alias="AGENTIC_EXTRACTION_COHERENCE_THRESHOLD",
    )
    extraction_max_retries: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Max grammar-constrained extraction attempts before regex fallback.",
        alias="AGENTIC_EXTRACTION_MAX_RETRIES",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }


class PersonaPromptSettings(BaseSettings):
    """Lean persona system-prompt configuration (ADR-005 Phase B).

    Gates a leaner exemplar-first / voice-last system-prompt builder that drops
    the duplicated wiki lore dump, dedupes repeated directives, and consumes a
    per-persona ``voice_signature`` for inter-character distinctiveness.

    When ``lean_enabled`` is False (default) AND a persona is not in
    ``lean_personas``, the legacy builder runs unchanged — byte-identical to
    pre-Phase-B, so the frozen legacy persona-eval baseline stays valid and
    revert is instant. ``lean_personas`` gives the ADR-required PER-PERSONA
    fallback: only personas that match-or-beat their legacy baseline in the
    acceptance A/B get added; the rest stay on the legacy prompt.
    """

    lean_enabled: bool = Field(
        default=False,
        description=(
            "Globally enable the lean persona prompt for ALL personas. False "
            "(default) = legacy builder unless a persona is listed in "
            "PERSONA_LEAN_PROMPT_PERSONAS. Set PERSONA_LEAN_PROMPT=true to enable all."
        ),
        alias="PERSONA_LEAN_PROMPT",
    )
    lean_personas: str = Field(
        default="",
        description=(
            "Comma-separated persona keys (e.g. 'nephilim_eeva,nephilim_solace') "
            "to serve the lean prompt while the global flag is off. The per-persona "
            "acceptance-gate allowlist. Empty (default) = none."
        ),
        alias="PERSONA_LEAN_PROMPT_PERSONAS",
    )

    def lean_persona_set(self) -> frozenset[str]:
        """Parsed, normalized set of per-persona lean-prompt opt-ins."""
        return frozenset(
            k.strip() for k in self.lean_personas.split(",") if k.strip()
        )

    def use_lean_for(self, persona_key: Optional[str]) -> bool:
        """Whether the lean prompt should be used for this persona key."""
        if self.lean_enabled:
            return True
        if not persona_key:
            return False
        return persona_key in self.lean_persona_set()

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
    memory: MemorySettings = Field(default_factory=MemorySettings)
    jupiter: JupiterSettings = Field(default_factory=JupiterSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    routing: RoutingSettings = Field(default_factory=RoutingSettings)
    lore: LoreSettings = Field(default_factory=LoreSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    prompt: PersonaPromptSettings = Field(default_factory=PersonaPromptSettings)

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


def get_persona_sampling_overrides(persona_card: dict) -> dict:
    """Get all sampling parameter overrides from a persona card.

    Reads model_preferences from the persona JSON and returns a dict of
    sampling params (temperature, min_p, repeat_penalty) that should be
    passed to the LLM client. Only includes values explicitly set in the
    persona card; missing values are omitted so callers can apply their
    own defaults.

    Args:
        persona_card: Persona dictionary from JSON

    Returns:
        Dict with keys like 'temperature', 'min_p', 'repeat_penalty' (only present if set)
    """
    model_prefs = persona_card.get("model_preferences", {})
    if not isinstance(model_prefs, dict):
        return {"temperature": settings.ollama.temperature}

    overrides: dict = {}

    # Temperature
    temp = model_prefs.get("temperature")
    if isinstance(temp, (int, float)) and 0.0 <= temp <= 2.0:
        overrides["temperature"] = float(temp)
    else:
        overrides["temperature"] = settings.ollama.temperature

    # Min-P
    min_p = model_prefs.get("min_p")
    if isinstance(min_p, (int, float)) and 0.0 < min_p <= 1.0:
        overrides["min_p"] = float(min_p)
    elif settings.ollama.min_p > 0.0:
        overrides["min_p"] = settings.ollama.min_p

    # Repeat penalty
    repeat_penalty = model_prefs.get("repeat_penalty")
    if isinstance(repeat_penalty, (int, float)) and 1.0 <= repeat_penalty <= 2.0:
        overrides["repeat_penalty"] = float(repeat_penalty)

    return overrides
