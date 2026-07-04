from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class RoutingSettings(BaseSettings):
    """Intent-routing / semantic-router configuration.

    The bge-m3 semantic router is the primary (and only) intent classifier
    (HERMES-Agents Phase 0). ROUTING_SEMANTIC_PRIMARY was retired 2026-07-04
    (audit cleanup step 5) once it had graduated to the prod default; the legacy
    keyword-first order was removed. These knobs tune the semantic path.
    """

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
