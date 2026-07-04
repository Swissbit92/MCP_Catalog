from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class LoreSettings(BaseSettings):
    """On-demand hybrid lore retrieval configuration (HERMES-Agents Phase 2).

    Per-turn hybrid lore retrieval is always on: LORE_ONDEMAND_ENABLED was
    retired 2026-07-04 (audit cleanup step 5) once it had graduated to the prod
    default; the static-3-entity-only legacy path was removed. These knobs tune
    the retrieval.
    """

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
        default=True,
        description="Inject a seeker-rank narrative block into the per-turn system prompt for NEPHILIM personas. True (default, matches prod).",
        alias="LORE_RANK_CONTEXT_ENABLED",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }
