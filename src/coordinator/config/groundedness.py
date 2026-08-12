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
    classifier_temperature: float | None = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description=(
            "Sampling temperature for the gate's CLASSIFIER call. None = inherit the "
            "speaking persona's profile (pre-2026-08-12 behaviour). Default 0.0: the "
            "classifier makes a binary decision, not creative writing, and it "
            "previously inherited whatever the SPEAKING persona declared — cipher "
            "0.65, eeva 0.7, nyx 0.95 — so one safety control had six sensitivities "
            "and could return different verdicts for a byte-identical draft. "
            "MEASURED (19-case eval set, 5 repeats): flip_rate 0.10 -> 0.00, with "
            "catch_rate 0.90 and false_abstain_rate 0.10 BOTH UNCHANGED — this buys "
            "reproducibility, not accuracy. NOTE: PERSONA_TEMPERATURE cannot control "
            "this; create_llm_client prefers the persona card's own override, so the "
            "value must be passed explicitly at the call site."
        ),
        alias="GROUNDEDNESS_CLASSIFIER_TEMPERATURE",
    )
    live_state_claims_enabled: bool = Field(
        default=True,
        description=(
            "Extend the classifier's trigger to cover unverified claims about the "
            "USER'S OWN LIVE STATE — position hedged/unhedged, balance, holdings, "
            "open orders — not just real-world events. This is a TIGHTENING. "
            "MEASURED 2026-08-12: the gate passed 'your position is currently "
            "unhedged after the rebalance, so you're carrying directional risk' on "
            "5 of 5 attempts, because that claim is not a score, date, statistic or "
            "outcome about a real-world event and so falls outside the original "
            "trigger. It contains no digits, and numeral-presence was separately "
            "measured NOT to predict gate firing. This is the highest-blast-radius "
            "shape in the system: an unverified assertion about live position state, "
            "wrapped in valid reasoning, on the persona that proposes wallet swaps. "
            "Set false to restore the pre-fix trigger definition."
        ),
        alias="GROUNDEDNESS_LIVE_STATE_CLAIMS",
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
