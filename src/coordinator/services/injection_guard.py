# src/coordinator/services/injection_guard.py
"""Trust-hierarchy injection guard (HERMES-Agents Phase 3, M3).

Roleplay is the highest-ASR jailbreak surface (~89.6%, arXiv 2507.22171), and
indirect injection via RAG/memory can smuggle tool triggers the persona treats as
authoritative. The defence is a strict trust hierarchy:

    system prompt  >  user turn  >  retrieved (RAG / lore) content

Retrieved content may *inform* a response but must NEVER *trigger* a tool call,
and content written to long-term memory must be stripped of tool-call syntax so a
stored payload cannot fire on a later turn.

Three deterministic, dependency-light surfaces (an embedder is optional — when
absent, token-overlap heuristics carry the check, so unit tests run headless):

* ``check_tool_trigger_source`` — is a proposed tool argument sourced from
  retrieved context rather than the user? -> block.
* ``sanitize_memory_write`` — strip tool-call syntax / instruction-override
  payloads before a RAG write.
* ``detect_escalation`` — flag a multi-turn drift toward "act without asking".
"""

from __future__ import annotations

import logging
import re
from typing import Any, List, Tuple

logger = logging.getLogger(__name__)

_WORD = re.compile(r"[a-z0-9]+")

# Tool-call syntax + instruction-override payloads neutralised on memory write.
_MEMORY_STRIP_PATTERNS = [
    re.compile(r"<\s*/?\s*tool_call\s*>", re.IGNORECASE),
    re.compile(r"<\s*/?\s*function(?:_call)?\b[^>]*>", re.IGNORECASE),
    re.compile(r'"?function_call"?\s*:', re.IGNORECASE),
    # explicit tool-invocation call syntax: name( ... )
    re.compile(r"\b(?:brave_web_search|solana_[a-z_]+|wallet_[a-z_]+)\s*\(", re.IGNORECASE),
    # classic injection imperatives
    re.compile(r"\bignore (?:all )?(?:previous|prior|above) instructions\b", re.IGNORECASE),
    re.compile(r"\byou are now\b", re.IGNORECASE),
    re.compile(r"\bdeveloper mode\b", re.IGNORECASE),
    re.compile(r"\bdisregard (?:the )?(?:system|your) (?:prompt|instructions)\b", re.IGNORECASE),
]

_REDACTION = "[redacted]"

# Escalation markers — requests to act autonomously / stop confirming.
_ESCALATION_MARKERS = [
    "do it yourself",
    "just do it",
    "without asking",
    "without confirmation",
    "stop asking",
    "don't ask",
    "dont ask",
    "automatically",
    "on your own",
    "from now on",
    "you have permission",
    "you don't need to ask",
    "just execute",
    "no need to confirm",
]


def _tokens(text: str) -> set:
    return set(_WORD.findall((text or "").lower()))


def _overlap_ratio(a: str, b: str) -> float:
    """Fraction of ``a``'s tokens that also appear in ``b`` (containment of a in b)."""
    ta = _tokens(a)
    if not ta:
        return 0.0
    tb = _tokens(b)
    return len(ta & tb) / len(ta)


class InjectionGuard:
    """Deterministic-first injection guard. ``embedder`` is optional.

    ``embedder`` (if provided) must expose ``embed_query(text) -> list[float]``;
    when absent the guard relies on token-overlap heuristics only.
    """

    def __init__(self, embedder: Any = None):
        self.embedder = embedder

    # ----- 1. trust hierarchy: retrieved content must not trigger tools -----

    def check_tool_trigger_source(
        self,
        proposed_argument: str,
        user_message: str,
        rag_context: str = "",
        lore_context: str = "",
        user_overlap_floor: float = 0.34,
        context_overlap_ceiling: float = 0.6,
    ) -> Tuple[bool, str]:
        """Return ``(is_injection_suspected, reason)`` for a proposed tool argument.

        Suspected injection when the argument is strongly grounded in retrieved
        context yet poorly grounded in the user's own message — i.e. the *trigger*
        came from RAG/lore, not the user. A blank argument or no retrieved context
        is never flagged (nothing to smuggle).
        """
        arg = (proposed_argument or "").strip()
        if not arg:
            return (False, "")

        retrieved = f"{rag_context}\n{lore_context}".strip()
        if not retrieved:
            return (False, "")

        user_overlap = _overlap_ratio(arg, user_message)
        if user_overlap >= user_overlap_floor:
            # The user's own words substantially account for the argument — fine.
            return (False, "")

        ctx_overlap = _overlap_ratio(arg, retrieved)

        # Optional semantic confirmation via embedder.
        sem = None
        if self.embedder is not None:
            try:
                sem = self._cosine(arg, retrieved)
            except Exception as e:  # pragma: no cover - embedder optional
                logger.debug(f"[InjectionGuard] embedder failed, deterministic only: {e}")

        from ..config import get_settings
        sem_threshold = get_settings().agent.trigger_similarity_threshold

        if ctx_overlap >= context_overlap_ceiling or (sem is not None and sem >= sem_threshold):
            return (
                True,
                f"tool argument appears sourced from retrieved context "
                f"(user_overlap={user_overlap:.2f}, ctx_overlap={ctx_overlap:.2f}"
                + (f", semantic={sem:.2f}" if sem is not None else "")
                + ") — retrieved content may inform but not trigger tools",
            )
        return (False, "")

    def _cosine(self, a: str, b: str) -> float:
        va = self.embedder.embed_query(a)
        vb = self.embedder.embed_query(b)
        dot = sum(x * y for x, y in zip(va, vb))
        na = sum(x * x for x in va) ** 0.5
        nb = sum(x * x for x in vb) ** 0.5
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    # ----- 2. sanitize memory writes -----

    def sanitize_memory_write(self, content: str) -> str:
        """Strip tool-call syntax / injection payloads before a RAG write.

        Pure string manipulation, zero latency. Returns the cleaned content.
        """
        if not content:
            return content
        cleaned = content
        for pat in _MEMORY_STRIP_PATTERNS:
            cleaned = pat.sub(_REDACTION, cleaned)
        return cleaned

    # ----- 3. multi-turn escalation detection -----

    def detect_escalation(
        self,
        conversation_history: List[dict],
        window: int = 5,
    ) -> bool:
        """True if recent user turns show a drift toward 'act without asking'.

        Companion relationships are an elevated social-engineering surface; a
        progressive push to remove confirmation across turns is the signature.
        Flags when >= 2 distinct escalation markers appear across the window.
        """
        if not conversation_history:
            return False
        user_turns = [
            m.get("content", "")
            for m in conversation_history
            if m.get("role") == "user"
        ][-window:]
        blob = " \n ".join(t.lower() for t in user_turns)
        hits = {marker for marker in _ESCALATION_MARKERS if marker in blob}
        return len(hits) >= 2


def get_injection_guard(embedder: Any = None) -> InjectionGuard:
    """Convenience factory (kept simple; the guard is cheap to construct)."""
    return InjectionGuard(embedder=embedder)
