"""ADR-006 Phase 1 — per-persona framing of injected session context.

Gate 0 (2026-06-28) and Gate 0.1 (2026-07-03) both failed on voice: injecting the
`[User Profile]` / `[Emotional State]` blocks dropped persona distinctiveness
(0.768→0.643 full, →0.679/0.696 selective). The mechanism, isolated in Gate 0.1:
the blocks are *identically formatted* across every persona (`**Header**\n- field:
value`), and that uniform skeleton is itself a stylistic signal the model imitates —
strong voices (gojo held 1.0) absorb it, advisory voices (eeva/solace/aegis) blur
toward it. Block *choice* was not the lever; *framing* is.

This module reframes injected memory as **non-echoable background knowledge** rather
than a data dump:

1. **Diegetic prose, not a bullet skeleton** — the narrative variants
   (`UserProfile.get_narrative_context`, `EmotionalState.to_narrative_context`)
   emit flowing sentences, removing the imitable `field: value` shape.
2. **A non-imitation instruction** adjacent to the content, addressed to the
   persona by name, telling it this is knowledge to draw on — not text to recite
   or let flatten its own voice.
3. **A non-echoable wrapper tag** (`<remembered>`) so the block reads as private
   memory metadata, distinct from the response surface.

The content (facts about the *user*) is persona-neutral by nature; per-persona
variation comes from the named frame plus the removed skeleton, letting each voice
render the same knowledge in its own register. This is the Gate-0/0.1 prerequisite
for flipping `MEMORY_CONTEXT_INJECT`; it is validated by the persona-eval canary
(eeva+nyx) and then the full 7-persona attribution gate before any flag flip.
"""

from __future__ import annotations

from typing import Dict, List, Optional


def _persona_name(persona_key: str, card: Optional[Dict]) -> str:
    """Human display name for the non-imitation frame; fall back to the key."""
    if card:
        name = card.get("display_name") or card.get("title")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return persona_key


def frame_injected_context(
    persona_key: str,
    card: Optional[Dict],
    body: str,
) -> Optional[str]:
    """Wrap already-capped narrative memory in a non-echoable, per-persona frame.

    ``body`` is the token-capped narrative context (profile + emotional, in
    priority order) produced upstream. Returns None when ``body`` is empty so the
    caller injects nothing. The returned string is what reaches the LLM as
    ``extra_system_context``.
    """
    if not body or not body.strip():
        return None
    name = _persona_name(persona_key, card)
    preamble = (
        f"This is what you, {name}, quietly carry from earlier conversations with "
        "this seeker — background you already know, not a script. Let it shape what "
        "you say and never recite it back as a list; keep speaking entirely in your "
        "own voice. Its plain wording is a note to yourself, not a style to copy."
    )
    return f"<remembered>\n{preamble}\n\n{body.strip()}\n</remembered>"


def _sentence_join(parts: List[str]) -> str:
    """Join clause fragments into a single spaced prose string, de-duped of blanks."""
    return " ".join(p.strip() for p in parts if p and p.strip())
