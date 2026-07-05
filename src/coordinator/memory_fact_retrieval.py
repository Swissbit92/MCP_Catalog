"""ADR-006 Phase 1 (M4) — fact retrieval + prose rendering for framed injection.

Reads the M2 fact store and turns the currently-valid facts into a prose narrative
that M1's `frame_injected_context` wraps per-persona. Retrieval policy (research):
below `inject_all_threshold` facts, inject them all and skip vector search (semantic
retrieval is wasted complexity at low fact counts); at/above it, rank by cosine to
the query and keep top-k.

The embedder is injected (`embed_fn`), so the selection logic is unit-testable
without Ollama; the live wiring passes the bge-m3 embedder. When no embedder is
available the above-threshold path degrades gracefully to recency+confidence order.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Self-subject predicate → natural clause ("They ..."). Named subjects fall back to
# a generic "<name>: <predicate> <object>" rendering.
_SELF_TEMPLATES: Dict[str, str] = {
    "has_name": "their name is {o}",
    "has_nickname": "they go by {o}",
    "has_age": "they are {o}",
    "has_birthday": "their birthday is {o}",
    "has_pronouns": "their pronouns are {o}",
    "lives_in": "they live in {o}",
    "works_as": "they work as {o}",
    "works_at": "they work at {o}",
    "studies_at": "they study at {o}",
    "has_relationship": "someone close to them: {o}",
    "has_pet": "they have a pet, {o}",
    "likes": "they like {o}",
    "dislikes": "they dislike {o}",
    "prefers": "they prefer {o}",
    "is_allergic_to": "they're allergic to {o}",
    "avoids": "they avoid {o}",
    "has_opinion_on": "they hold a firm view on {o}",
    "has_favorite": "a favorite of theirs is {o}",
    "has_goal": "they're working toward {o}",
    "plans_to": "they plan to {o}",
    "has_deadline": "they have a deadline: {o}",
    "is_concerned_about": "they've been worried about {o}",
    "has_health_condition": "they live with {o}",
    "takes_medication": "they take {o}",
    "has_hobby": "they enjoy {o}",
    "has_skill": "they're skilled at {o}",
    "is_learning": "they're learning {o}",
    "follows_routine": "they keep a routine: {o}",
    "has_daily_habit": "a daily habit of theirs: {o}",
    "is_currently_engaged_with": "they're currently into {o}",
    "experienced_life_event": "they went through {o}",
    "attended_event": "they attended {o}",
    "owns": "they own {o}",
}

_SELF_ALIASES = frozenset({"self", "me", "i", "user", "myself"})


def _fact_clause(fact: Dict[str, Any], subject_name: Optional[str]) -> str:
    """Render one fact row as a lowercase clause (no leading capital / period)."""
    predicate = fact.get("predicate", "")
    obj = str(fact.get("object", "")).strip()
    is_self = (subject_name or "self").lower() in _SELF_ALIASES
    if is_self:
        tmpl = _SELF_TEMPLATES.get(predicate)
        if tmpl:
            return tmpl.format(o=obj)
        return f"{predicate.replace('_', ' ')} {obj}".strip()
    # Named subject (e.g. sister, partner, pet).
    return f"{subject_name} — {predicate.replace('_', ' ')} {obj}".strip()


def render_facts_narrative(
    facts: List[Dict[str, Any]],
    subject_names: Optional[Dict[str, str]] = None,
) -> str:
    """Turn fact rows into one prose paragraph ("You also remember that ...").

    `subject_names` maps subject_id → entity name (for non-self subjects). Missing
    ids render as self.
    """
    if not facts:
        return ""
    subject_names = subject_names or {}
    clauses = [
        _fact_clause(f, subject_names.get(f.get("subject_id"), "self"))
        for f in facts
    ]
    clauses = [c for c in clauses if c]
    if not clauses:
        return ""
    joined = "; ".join(clauses)
    return f"You also remember that {joined}."


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def select_facts_for_injection(
    facts: List[Dict[str, Any]],
    query: str,
    *,
    k: int = 5,
    inject_all_threshold: int = 15,
    embed_fn: Optional[Callable[[str], List[float]]] = None,
    subject_names: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Pick which active facts to inject this turn.

    - ``len(facts) <= inject_all_threshold`` → all of them (recency/insertion order).
    - otherwise, if ``embed_fn`` is given → cosine-rank fact clauses vs ``query``,
      top-k; if not → most-recent k (highest id) as a cheap fallback.
    """
    if len(facts) <= inject_all_threshold:
        return list(facts)
    if embed_fn is None:
        return sorted(facts, key=lambda f: f.get("id", 0), reverse=True)[:k]
    try:
        qv = embed_fn(query)
        subject_names = subject_names or {}
        scored = [
            (_cosine(qv, embed_fn(_fact_clause(f, subject_names.get(f.get("subject_id"), "self")))), f)
            for f in facts
        ]
        scored.sort(key=lambda s: s[0], reverse=True)
        return [f for _, f in scored[:k]]
    except Exception as e:  # embedding failure must not break injection
        logger.warning(f"[FactRetrieval] embed ranking failed, falling back to recency: {e}")
        return sorted(facts, key=lambda f: f.get("id", 0), reverse=True)[:k]
