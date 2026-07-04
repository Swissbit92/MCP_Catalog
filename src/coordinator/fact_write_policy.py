"""ADR-006 Phase 1 (M3) — recency-wins write policy for extracted triples.

Applies validated triples (from TripletExtractor) to the MemoryFactRepository:
resolves the subject entity, then for single-valued predicates supersedes the
prior value (invalidate-not-delete), and for multi-valued predicates accretes
non-duplicate facts. Pure w.r.t. the LLM — no extraction here.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .repositories.memory_fact_repository import (
    MemoryFactRepository,
    SINGLE_VALUED_PREDICATES,
)

logger = logging.getLogger(__name__)

_SELF_ALIASES = frozenset({"self", "me", "i", "user", "myself"})

# Extracted facts carry sub-1.0 confidence to distinguish them from any manual /
# ground-truth writes (e.g. wallet holdings) that use the default 1.0.
_EXTRACTED_CONFIDENCE = 0.8


def apply_triples(
    repo: MemoryFactRepository,
    user_id: str,
    triples: List[Dict[str, Any]],
    session_id: Optional[str] = None,
    message_id: Optional[str] = None,
) -> int:
    """Write validated triples, returning the number of facts added/updated."""
    written = 0
    for t in triples:
        try:
            subject_name = str(t.get("subject", "self")).strip() or "self"
            predicate = t["predicate"]
            obj = t["object"]
            is_self = subject_name.lower() in _SELF_ALIASES
            subject_id = repo.get_or_create_entity(
                user_id,
                "self" if is_self else subject_name,
                entity_type="self" if is_self else "person",
            )
            kwargs = dict(
                object_type=t.get("object_type", "literal"),
                confidence=_EXTRACTED_CONFIDENCE,
                source_session_id=session_id,
                source_message_id=message_id,
            )
            if predicate in SINGLE_VALUED_PREDICATES:
                before = repo.find_active_fact(user_id, subject_id, predicate)
                new_id = repo.supersede_and_add(user_id, subject_id, predicate, obj, **kwargs)
                # supersede_and_add returns the existing id on an exact duplicate.
                if not (before and before["object"] == obj):
                    written += 1
            else:
                if repo.find_active_fact(user_id, subject_id, predicate, obj) is None:
                    repo.add_fact(user_id, subject_id, predicate, obj, **kwargs)
                    written += 1
        except Exception as e:  # one bad triple must not abort the batch
            logger.warning(f"[FactWrite] skipped triple {t!r}: {e}")
    if written:
        logger.info(f"[FactWrite] wrote {written} fact(s) for {user_id}")
    return written
