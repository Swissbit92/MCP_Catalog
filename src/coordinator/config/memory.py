from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


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
    context_inject_enabled: bool = Field(
        default=False,
        description="ADR-006 M0: pass the session context blocks (cross-session "
                    "user profile, emotional state, unlocked/on-demand lore, seeker "
                    "rank, capability) through to the LLM system prompt. These are "
                    "built by handle_session_chat but were historically DROPPED "
                    "(ChatBody carried no system prompt). "
                    "⚠️ GATE 0 (2026-06-28) FAILED ON VOICE (full six-block inject: "
                    "distinctiveness 0.768→0.643). ⚠️ GATE 0.1 (2026-07-03) ALSO "
                    "FAILED: M0.1 selective injection (user-profile + emotional only, "
                    "the current code path) still homogenizes — 0.768→0.679/0.696 "
                    "across two independent runs, eeva 0.625→0.25/0.375. Identically-"
                    "formatted blocks pull every persona toward the same injected "
                    "text; block CHOICE is not the fix. DO NOT enable without "
                    "per-persona framing of the injected content (render facts in "
                    "the persona's voice, or tag as non-echoable metadata) AND a "
                    "re-gate. Seam + plumbing remain correct. See ADR-006.",
        alias="MEMORY_CONTEXT_INJECT"
    )
    context_max_tokens: int = Field(
        default=2000,
        ge=0,
        le=12000,
        description="ADR-006 M0: token budget cap for the injected session context "
                    "blocks. Highest-priority blocks (user profile, emotional state) "
                    "are kept first; lower-priority blocks (lore, rank, capability) "
                    "are dropped when the budget is exceeded, protecting the context "
                    "window. 0 = no cap.",
        alias="MEMORY_CONTEXT_MAX_TOKENS"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }
