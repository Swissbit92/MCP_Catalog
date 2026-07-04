from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


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
