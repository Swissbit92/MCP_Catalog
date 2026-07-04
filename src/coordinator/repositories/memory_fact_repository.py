# src/coordinator/repositories/memory_fact_repository.py
"""ADR-006 Phase 1 (M2) — the two-table ontology-lite fact store.

A normalized, *temporal* fact store for companion memory: `memory_entities`
(the user and the people/places/things they mention) + `memory_facts`
(subject-predicate-object triples with bi-temporal validity, provenance, and
confidence). This is the structured source of truth that M3 (async extraction)
writes and M4 (retrieval + framed injection) reads; FAISS indexes over it for
semantic recall but never owns the facts (it can't update, delete, or dedup).

Design (evidence-backed — MemPalace two-table split, Graphiti bi-temporal edges,
Mem0 recency-wins consolidation; see ADR-006 Alternatives Considered for why this
is *not* a graph DB):

- **Temporal validity, not deletion.** A superseded fact keeps its row; we set
  `valid_to` and link `superseded_by`. "was sick" → "recovered" keeps both, each
  with its interval. Retrieval filters `valid_to IS NULL` for the current view.
- **Provenance + confidence** on every fact (source session/message, extraction
  confidence) so contradiction resolution is debuggable and low-confidence facts
  can be down-weighted.
- **Controlled predicate vocabulary** (`PREDICATE_VOCABULARY`) — the useful ~10%
  of an "ontology": a closed set that makes dedup/conflict tractable without a
  formal schema. `SINGLE_VALUED_PREDICATES` marks the ones where a new value
  supersedes the old (name, age, residence) vs. accreting (likes, goals, events).

This module is the pure storage layer; extraction and the recency-wins write
policy live in M3. `_ensure_table` self-creates (dual-covered with the alembic
revision, matching EmotionalStateRepository) so it works in Docker envs that skip
alembic and in unit tests.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from .base_repository import BaseRepository, utc_now_iso

logger = logging.getLogger(__name__)

# Closed predicate vocabulary for a personal companion (ADR-006 P1 research).
# Kept intentionally small; extraction (M3) must map into this set or drop the fact.
PREDICATE_VOCABULARY: frozenset[str] = frozenset({
    # identity
    "has_name", "has_nickname", "has_age", "has_birthday", "has_pronouns",
    # place / occupation / study
    "lives_in", "works_as", "works_at", "studies_at",
    # relationships (object is a person; use object_type='entity')
    "has_relationship", "has_pet",
    # preferences / stances
    "likes", "dislikes", "prefers", "is_allergic_to", "avoids", "has_opinion_on",
    "has_favorite",
    # goals / plans / time-bound
    "has_goal", "plans_to", "has_deadline", "is_concerned_about",
    # health
    "has_health_condition", "takes_medication",
    # activity / habit / interest
    "has_hobby", "has_skill", "is_learning", "follows_routine", "has_daily_habit",
    "is_currently_engaged_with",
    # events / ownership
    "experienced_life_event", "attended_event", "owns",
})

# Predicates where a single current value is expected — a new fact supersedes the
# prior one (recency-wins). The rest accrete multiple concurrent valid facts.
SINGLE_VALUED_PREDICATES: frozenset[str] = frozenset({
    "has_name", "has_nickname", "has_age", "has_birthday", "has_pronouns",
    "lives_in", "works_as", "works_at", "studies_at",
})


class MemoryFactRepository(BaseRepository):
    """CRUD + temporal-supersede over `memory_entities` / `memory_facts`."""

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path)
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Create both tables + indexes if absent (dual-covered with alembic)."""
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS memory_entities (
                entity_id   TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                name        TEXT NOT NULL,
                entity_type TEXT NOT NULL DEFAULT 'person',
                properties  TEXT,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
            """
        )
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS memory_facts (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id           TEXT NOT NULL,
                subject_id        TEXT NOT NULL,
                predicate         TEXT NOT NULL,
                object            TEXT NOT NULL,
                object_type       TEXT NOT NULL DEFAULT 'literal',
                valid_from        TEXT NOT NULL,
                valid_to          TEXT,
                confidence        REAL NOT NULL DEFAULT 1.0,
                source_session_id TEXT,
                source_message_id TEXT,
                superseded_by     INTEGER,
                created_at        TEXT NOT NULL,
                FOREIGN KEY (subject_id) REFERENCES memory_entities(entity_id),
                FOREIGN KEY (superseded_by) REFERENCES memory_facts(id)
            )
            """
        )
        self._execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_facts_subject_pred "
            "ON memory_facts(user_id, subject_id, predicate)"
        )
        self._execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_facts_valid ON memory_facts(valid_to)"
        )
        self._execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_entities_user "
            "ON memory_entities(user_id, entity_type, name)"
        )
        logger.debug("[MemoryFacts] tables ensured")

    # ---- entities -------------------------------------------------------

    def get_or_create_entity(
        self,
        user_id: str,
        name: str,
        entity_type: str = "person",
        properties: Optional[str] = None,
    ) -> str:
        """Return the entity_id for (user, name, type), creating it if new.

        Dedup is case-insensitive on name within (user_id, entity_type). Returns
        the existing id on a hit so facts always attach to one canonical entity.
        """
        norm = (name or "").strip()
        if not norm:
            raise ValueError("entity name must be non-empty")
        existing = self._fetchone_dict(
            "SELECT entity_id FROM memory_entities "
            "WHERE user_id = ? AND entity_type = ? AND lower(name) = lower(?)",
            (user_id, entity_type, norm),
        )
        if existing:
            return existing["entity_id"]
        entity_id = uuid.uuid4().hex
        now = utc_now_iso()
        self._execute(
            "INSERT INTO memory_entities "
            "(entity_id, user_id, name, entity_type, properties, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (entity_id, user_id, norm, entity_type, properties, now, now),
        )
        return entity_id

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        return self._fetchone_dict(
            "SELECT * FROM memory_entities WHERE entity_id = ?", (entity_id,)
        )

    # ---- facts ----------------------------------------------------------

    def add_fact(
        self,
        user_id: str,
        subject_id: str,
        predicate: str,
        obj: str,
        *,
        object_type: str = "literal",
        confidence: float = 1.0,
        source_session_id: Optional[str] = None,
        source_message_id: Optional[str] = None,
        valid_from: Optional[str] = None,
    ) -> int:
        """Insert a currently-valid fact and return its id.

        `predicate` must be in `PREDICATE_VOCABULARY` (fail-loud — extraction is
        responsible for mapping into the closed set). This is a raw insert; the
        recency-wins supersede policy is applied by the M3 write path via
        `supersede_and_add`.
        """
        if predicate not in PREDICATE_VOCABULARY:
            raise ValueError(f"predicate {predicate!r} not in the controlled vocabulary")
        now = utc_now_iso()
        cur = self._execute(
            "INSERT INTO memory_facts "
            "(user_id, subject_id, predicate, object, object_type, valid_from, "
            " valid_to, confidence, source_session_id, source_message_id, "
            " superseded_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, NULL, ?)",
            (user_id, subject_id, predicate, obj, object_type, valid_from or now,
             confidence, source_session_id, source_message_id, now),
        )
        return int(cur.lastrowid)

    def get_active_facts(
        self,
        user_id: str,
        subject_id: Optional[str] = None,
        predicate: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Currently-valid facts (`valid_to IS NULL`), optionally filtered."""
        q = "SELECT * FROM memory_facts WHERE user_id = ? AND valid_to IS NULL"
        params: List[Any] = [user_id]
        if subject_id is not None:
            q += " AND subject_id = ?"
            params.append(subject_id)
        if predicate is not None:
            q += " AND predicate = ?"
            params.append(predicate)
        q += " ORDER BY id"
        return self._fetchall_list(q, tuple(params))

    def find_active_fact(
        self, user_id: str, subject_id: str, predicate: str, obj: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """The current valid fact for (subject, predicate)[, object], or None.

        Used by the write path to detect a conflict (same subject+predicate,
        different object) or a duplicate (same object).
        """
        rows = self.get_active_facts(user_id, subject_id, predicate)
        if obj is None:
            return rows[0] if rows else None
        for r in rows:
            if r["object"] == obj:
                return r
        return None

    def supersede_fact(self, fact_id: int, superseded_by: Optional[int] = None,
                       at: Optional[str] = None) -> None:
        """Close a fact's validity window (recency-wins invalidation)."""
        self._execute(
            "UPDATE memory_facts SET valid_to = ?, superseded_by = ? WHERE id = ?",
            (at or utc_now_iso(), superseded_by, fact_id),
        )

    def supersede_and_add(
        self,
        user_id: str,
        subject_id: str,
        predicate: str,
        obj: str,
        **kwargs: Any,
    ) -> int:
        """Recency-wins write for single-valued predicates.

        If an active fact exists for (subject, predicate) with a *different*
        object, close it and link it to the new one. If the active object is
        identical, this is a NOOP-return of the existing id. For multi-valued
        predicates, callers should use `add_fact` directly.
        """
        active = self.find_active_fact(user_id, subject_id, predicate)
        if active and active["object"] == obj:
            return int(active["id"])  # duplicate — nothing to do
        new_id = self.add_fact(user_id, subject_id, predicate, obj, **kwargs)
        if active:
            self.supersede_fact(int(active["id"]), superseded_by=new_id)
        return new_id

    def get_fact(self, fact_id: int) -> Optional[Dict[str, Any]]:
        return self._fetchone_dict("SELECT * FROM memory_facts WHERE id = ?", (fact_id,))

    def count_active_facts(self, user_id: str) -> int:
        row = self._fetchone_dict(
            "SELECT COUNT(*) AS n FROM memory_facts WHERE user_id = ? AND valid_to IS NULL",
            (user_id,),
        )
        return int(row["n"]) if row else 0
