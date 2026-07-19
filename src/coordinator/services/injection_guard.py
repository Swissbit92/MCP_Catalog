# src/coordinator/services/injection_guard.py
"""Memory-write sanitizer for the RAG trust hierarchy.

Indirect injection via RAG/memory can smuggle instructions the persona later
treats as authoritative. Content written to long-term memory is therefore
stripped of tool-call syntax and instruction-override payloads, so a stored
payload cannot fire on a later turn.

* ``sanitize_memory_write`` — strip tool-call syntax / instruction-override
  payloads before a RAG write. Called from ``chat_session_service``, gated by
  ``AGENTIC_INJECTION_GUARD`` (default ON).

Originally (HERMES-Agents Phase 3, M3) this module also carried
``check_tool_trigger_source`` (retrieved content may inform but never *trigger* a
tool call) and ``detect_escalation`` (multi-turn drift toward "act without
asking"). Both were removed 2026-07-19 with the ADR-004 two-stage pipeline, which
was their only caller — they were never wired into the ADR-008 tool brain that
superseded it, so they never protected production. This was a deliberate choice
to delete rather than rewire; see ADR-004's supersession note. Recoverable from
git history if the threat model changes.
"""

from __future__ import annotations

import re

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


class InjectionGuard:
    """Deterministic memory-write sanitizer. Pure string manipulation."""

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


def get_injection_guard() -> InjectionGuard:
    """Convenience factory (kept simple; the guard is cheap to construct)."""
    return InjectionGuard()
