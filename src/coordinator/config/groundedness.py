from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class GroundednessSettings(BaseSettings):
    """Generation-time groundedness gate (ADR-007).

    Closes a gap distinct from the SearchSettings guards: those guards
    (query_resolution_enabled, relevance_gate_enabled) all live INSIDE the
    tool-calling path and only ever run when the intent router already decided
    a tool call was needed. When routing itself misses (a search-worthy
    factual/temporal query falls through to NEEDS_NEITHER), the entire
    tool-calling guard chain — including the "no results -> I don't know" and
    "LLM skipped tool -> I don't know" guards — is architecturally unreachable,
    and a bare LLM completion can confidently fabricate real-world facts with
    zero grounding (2026-07-04 incident, session dcc3693d: a fabricated FIFA
    World Cup match result with no tool call at all).

    This gate runs AFTER a draft response is generated in the no-tools branch
    (routes/chat.py's `if not tools:` branch only — never on turns that
    already had a tool call, which are grounded by construction). It asks the
    same loaded persona LLM a second, cheap yes/no classification question:
    does the draft assert a specific, falsifiable, temporally-scoped
    real-world claim (a score/date/outcome/statistic) with nothing backing it?
    If yes, the draft is replaced with an honest offer-to-search instead of
    being returned as-is.

    Default OFF. The named risk is false-abstention — the gate refusing to
    answer things E.E.V.A. legitimately knows (in-fiction lore, timeless
    general knowledge) or re-litigating an already-grounded turn. See
    tests/evaluation/groundedness_eval_set.json and
    docs/decisions/007-generation-time-groundedness-gate.md for the eval-first
    validation this must clear before being enabled in production.
    """

    gate_enabled: bool = Field(
        default=False,
        description=(
            "Run the post-hoc groundedness classifier on no-tool-call responses "
            "and replace flagged drafts with an honest offer-to-search. False "
            "(default) = byte-identical to legacy (the draft is always returned "
            "as-is). Set GROUNDEDNESS_GATE_ENABLED=true to enable."
        ),
        alias="GROUNDEDNESS_GATE_ENABLED",
    )
    reinforcement_check_enabled: bool = Field(
        default=False,
        description=(
            "When a recent turn was tagged 'unverified' by the gate, re-run the "
            "gate on a later turn that appears to 'confirm' that claim, instead "
            "of treating the user's paraphrase-back as corroborating evidence. "
            "Independent of gate_enabled's own on/off state so it can be tuned "
            "separately once the base gate is validated. Set "
            "GROUNDEDNESS_REINFORCEMENT_CHECK_ENABLED=true to enable."
        ),
        alias="GROUNDEDNESS_REINFORCEMENT_CHECK_ENABLED",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }
