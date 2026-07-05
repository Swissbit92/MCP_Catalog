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


class ToolBrainSettings(BaseSettings):
    """ADR-008 P1 single-model native tool-brain loop configuration.

    The daily-driver model (abliterated Mistral-Small-24B) decides + fills tool
    calls natively; deterministic middleware (ADR-004 interceptor + injection
    guard) gates execution; the same model synthesizes in-voice. When the model
    emits no native call, the loop falls back to the existing deterministic
    intent-router / force-search floor (the spike found native calling is
    phrasing-sensitive: explicit phrasings trigger calls, colloquial ones miss).

    ``enabled`` default **False** = byte-identical to the legacy force-search
    chat path; the whole loop is bypassed. Flip TOOL_BRAIN_ENABLED=true only
    after the TB4 red-team/eval gate.
    """

    enabled: bool = Field(
        default=False,
        description=(
            "Route non-wallet-flow chat turns through the native tool-brain loop "
            "(model-decided tool calls + deterministic fallback). False (default) "
            "= byte-identical legacy force-search path. Set TOOL_BRAIN_ENABLED=true."
        ),
        alias="TOOL_BRAIN_ENABLED",
    )
    max_iterations: int = Field(
        default=3,
        ge=1,
        le=6,
        description=(
            "Max native tool-call round-trips per turn before forcing synthesis. "
            "Bounds latency + injection-compounding on a local model. 3 covers "
            "search->fetch->answer; the reads-only MVP rarely needs more."
        ),
        alias="TOOL_BRAIN_MAX_ITERATIONS",
    )
    deterministic_fallback: bool = Field(
        default=True,
        description=(
            "When the model emits NO native tool call, fall back to the "
            "deterministic intent router / force-search (the reliability floor "
            "for colloquial phrasings the model misses). Default ON. OFF = pure "
            "native (research/debug only — will silently skip tools on ~40% of "
            "colloquial queries per the TB0 spike)."
        ),
        alias="TOOL_BRAIN_DETERMINISTIC_FALLBACK",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }
