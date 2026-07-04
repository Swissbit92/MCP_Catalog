from __future__ import annotations

import logging

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


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

class SearchSettings(BaseSettings):
    """Web-search grounding configuration (follow-up query resolution + gate).

    Two independent, default-OFF guards for the Brave force-search path. Both
    off (default) = byte-identical to the legacy behavior, so revert is a single
    env flip and no eval baseline shifts.

    ``query_resolution_enabled`` fixes the "search the web for it" bug: a deictic
    follow-up turn was sent to Brave verbatim (topic lost), returning junk
    meta-results. When on, the latest turn is resolved against prior conversation
    before the search — with a hard fallback to the raw latest turn on any
    failure, so it can never be worse than the legacy path.

    ``relevance_gate_enabled`` is defense-in-depth: even a resolved query can
    return off-topic results, and non-empty junk currently bypasses the
    "no results -> I don't know" guard. When on, results whose max bge-m3 cosine
    to the query falls below ``relevance_min_cosine`` are treated as no-result
    (honest abstention) instead of fed to synthesis.
    """

    query_resolution_enabled: bool = Field(
        default=False,
        description=(
            "Resolve deictic/follow-up search turns against prior conversation "
            "before hitting Brave. False (default) = legacy verbatim behavior. "
            "Set SEARCH_QUERY_RESOLUTION_ENABLED=true to enable."
        ),
        alias="SEARCH_QUERY_RESOLUTION_ENABLED",
    )
    relevance_gate_enabled: bool = Field(
        default=False,
        description=(
            "Abstain when search results are off-topic (max bge-m3 cosine to the "
            "query < relevance_min_cosine) instead of synthesizing over junk. "
            "False (default) = legacy behavior. Independent of query resolution."
        ),
        alias="SEARCH_RELEVANCE_GATE_ENABLED",
    )
    relevance_min_cosine: float = Field(
        default=0.28,
        ge=0.0,
        le=1.0,
        description=(
            "Cosine floor (bge-m3, exact 1 - D/2) below which the best search "
            "result is treated as off-topic and the relevance gate abstains. "
            "Tuned 2026-07-04 (ADR-007, tests/evaluation/tune_relevance_threshold.py) "
            "on relevance_gate_eval_set.json (n=8, small — first-pass calibration, "
            "not a large-scale validation): 0.28 catches the 2026-07-04 incident's "
            "exact junk shape (a sports-fixture query scoring 0.263 against generic "
            "'how to search a webpage' results) with ZERO false-abstention on any "
            "of 6 relevant samples. A real, measured tension exists at higher "
            "thresholds: a second junk sample (cosine 0.347) sits only 0.011 below "
            "a deliberately-adversarial lexically-distant-but-relevant sample "
            "(0.358) — raising the floor to catch the former would also falsely "
            "abstain on the latter. 0.40 (the prior untuned placeholder) was "
            "conservative-by-guess, not conservative-by-data."
        ),
        alias="SEARCH_RELEVANCE_MIN_COSINE",
    )
    synthesis_trust_results: bool = Field(
        default=False,
        description=(
            "Add a synthesis-prompt directive telling the model the search "
            "results below are fresh/just-retrieved/verified and must be used to "
            "answer, overriding any earlier in-conversation self-doubt/refusal "
            "about searching (context-poisoning fix). Scoped: does NOT override "
            "honest abstention when results are genuinely empty. False (default) "
            "= byte-identical synthesis prompt. Set "
            "SEARCH_SYNTHESIS_TRUST_RESULTS=true to enable."
        ),
        alias="SEARCH_SYNTHESIS_TRUST_RESULTS",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }
