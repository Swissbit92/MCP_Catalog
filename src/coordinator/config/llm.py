from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


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
