# src/coordinator/services/groundedness_gate_service.py
"""
Groundedness Gate Service - Catch confident fabrication when routing itself
missed a search-worthy query (ADR-007).

Distinct from the SearchSettings guards (query_resolution, relevance_gate):
those live INSIDE the tool-calling path and only run when the intent router
already decided a tool call was needed. This gate covers the case where
routing decided NO tool was needed at all — routes/chat.py's `if not tools:`
branch — where none of the existing anti-hallucination guards are reachable.

2026-07-04 incident (session dcc3693d): "What was their last match?" fell
through to NEEDS_NEITHER (no force-search pattern, no semantic-router match —
see docs/decisions/007-generation-time-groundedness-gate.md), and the bare LLM
completion fabricated a detailed, confident sports result with zero grounding.

Mechanism: after a draft response is generated with no tool call this turn,
ask the same loaded persona LLM a second, cheap yes/no question — does the
draft assert a specific, falsifiable, temporally-scoped real-world claim (a
score/date/outcome/statistic) with nothing backing it? If yes, the draft is
replaced with an honest offer-to-search. Narrowly scoped to avoid the named
top risk (false-abstention on legitimate persona lore or general knowledge) —
see the classifier prompt and tests/evaluation/groundedness_eval_set.json.

Fail-open by design, same principle as SearchRelevanceService: any classifier
error returns "not flagged" so the gate can never make a response worse than
the legacy (no-gate) path — it only ever *adds* honest abstentions on clearly
fabricated real-world claims.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_CLASSIFIER_SYSTEM = (
    "You are a strict fact-checker reviewing a DRAFT response before it is sent. "
    "No search or tool was used to produce this draft.\n\n"
    "Flag the draft ONLY if it states a SPECIFIC, FALSIFIABLE, TIME-SENSITIVE "
    "real-world claim — a score, date, statistic, or outcome about an actual "
    "real-world event (sports, elections, prices, breaking news) — as if it "
    "were a confirmed fact.\n\n"
    "Do NOT flag:\n"
    "- In-character fictional/persona lore or worldbuilding (this is a roleplay "
    "companion; its own backstory or the world's fiction is not a real-world claim)\n"
    "- General, timeless knowledge (definitions, settled history, science "
    "concepts, \"capital of France\" style facts)\n"
    "- Opinions, feelings, creative writing, or hedged/uncertain language "
    "(\"I'm not sure, but...\", \"I don't have live access...\")\n"
    "- Responses that already reference search results or cite sources\n\n"
    "Answer with exactly one word: YES if the draft states an ungrounded "
    "real-world factual claim, or NO otherwise."
)

_ABSTAIN_MESSAGE = (
    "I don't actually have grounded, up-to-date information on that — I'd "
    "rather admit that than guess or make something up. Want me to search "
    "for it?"
)


@dataclass(frozen=True)
class GroundednessVerdict:
    """Result of a groundedness check."""

    should_abstain: bool
    reason: str  # "flag_off" | "grounded" | "ungrounded" | "classifier_error_fail_open"


class GroundednessGateService:
    """Post-hoc classifier gating no-tool-call responses for ungrounded claims.

    Stateless apart from the injected LLM client.
    """

    def __init__(self, llm_client: Any):
        """Args:
        llm_client: object exposing complete(system: str, user_prompt: str) -> str,
            matching create_llm_client(card)'s interface (routes/chat.py's
            _complete_or_503 uses the same shape).
        """
        self.llm_client = llm_client

    def check(self, user_turn: str, drafted_response: str) -> GroundednessVerdict:
        """Check whether `drafted_response` should be replaced with an abstention.

        Never raises: on any classifier failure, fails open (never blocks a
        response the legacy path would have returned).
        """
        from ..config import get_settings

        if not get_settings().groundedness.gate_enabled:
            return GroundednessVerdict(should_abstain=False, reason="flag_off")

        try:
            user_prompt = (
                f"User asked: {user_turn}\n\n"
                f"Draft response:\n{drafted_response}\n\n"
                "Answer (YES/NO):"
            )
            raw_verdict = self.llm_client.complete(_CLASSIFIER_SYSTEM, user_prompt)
            flagged = self._parse_verdict(raw_verdict)
            if flagged:
                logger.warning(
                    f"[GroundednessGate] Flagged ungrounded claim for query="
                    f"'{user_turn[:60]}' draft='{drafted_response[:80]}'"
                )
            return GroundednessVerdict(
                should_abstain=flagged,
                reason="ungrounded" if flagged else "grounded",
            )
        except Exception as e:  # noqa: BLE001 - gate must never break chat
            logger.warning(f"[GroundednessGate] Classifier failed ({e}); failing open")
            return GroundednessVerdict(should_abstain=False, reason="classifier_error_fail_open")

    @staticmethod
    def _parse_verdict(raw: str) -> bool:
        """True iff the classifier's first word is exactly YES (case-insensitive).

        Exact match, not a prefix check — "Yesterday..." must not be misread as
        "YES" via naive startswith("YES") substring matching.
        """
        if not raw or not raw.strip():
            return False
        first_word = raw.strip().split()[0].strip(".,:;\"'").upper()
        return first_word == "YES"

    @staticmethod
    def abstain_message() -> str:
        """Fixed, voice-neutral honest-abstention string (persona post-processing
        already applies first-person/voice adjustments downstream, same as any
        other LLM output)."""
        return _ABSTAIN_MESSAGE
