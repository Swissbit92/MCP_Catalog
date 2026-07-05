"""ADR-006 M2 — unit tests for the two-table ontology-lite fact store.

Hermetic: a throwaway SQLite file per test (self-created via _ensure_table), no
Ollama, no alembic. Covers entity dedup, predicate validation, temporal supersede
(recency-wins), and multi-valued accretion.
"""

from __future__ import annotations

import pytest

from src.coordinator.repositories.memory_fact_repository import (
    MemoryFactRepository,
    PREDICATE_VOCABULARY,
    SINGLE_VALUED_PREDICATES,
)

USER = "user-raphael"


@pytest.fixture()
def repo(tmp_path):
    return MemoryFactRepository(db_path=str(tmp_path / "facts.db"))


def test_get_or_create_entity_dedupes_case_insensitively(repo):
    a = repo.get_or_create_entity(USER, "Raphael", "self")
    b = repo.get_or_create_entity(USER, "raphael", "self")
    assert a == b
    # Different type is a different entity.
    c = repo.get_or_create_entity(USER, "Raphael", "person")
    assert c != a


def test_get_or_create_entity_rejects_blank(repo):
    with pytest.raises(ValueError):
        repo.get_or_create_entity(USER, "   ", "self")


def test_add_and_get_active_fact(repo):
    subj = repo.get_or_create_entity(USER, "Raphael", "self")
    fid = repo.add_fact(USER, subj, "works_as", "quant trader", source_session_id="s1")
    facts = repo.get_active_facts(USER, subj, "works_as")
    assert len(facts) == 1
    assert facts[0]["id"] == fid
    assert facts[0]["object"] == "quant trader"
    assert facts[0]["valid_to"] is None
    assert facts[0]["confidence"] == 1.0
    assert facts[0]["source_session_id"] == "s1"


def test_add_fact_rejects_unknown_predicate(repo):
    subj = repo.get_or_create_entity(USER, "Raphael", "self")
    with pytest.raises(ValueError):
        repo.add_fact(USER, subj, "enjoys_the_smell_of", "rain")


def test_supersede_recency_wins_on_single_valued(repo):
    subj = repo.get_or_create_entity(USER, "Raphael", "self")
    old = repo.supersede_and_add(USER, subj, "lives_in", "Zurich")
    new = repo.supersede_and_add(USER, subj, "lives_in", "Geneva")
    assert new != old
    # Only the new value is active; the old is closed and linked.
    active = repo.get_active_facts(USER, subj, "lives_in")
    assert len(active) == 1
    assert active[0]["object"] == "Geneva"
    old_row = repo.get_fact(old)
    assert old_row["valid_to"] is not None       # invalidated, not deleted
    assert old_row["superseded_by"] == new       # linked to its successor


def test_supersede_same_object_is_noop(repo):
    subj = repo.get_or_create_entity(USER, "Raphael", "self")
    a = repo.supersede_and_add(USER, subj, "has_name", "Raphael")
    b = repo.supersede_and_add(USER, subj, "has_name", "Raphael")
    assert a == b  # duplicate returns the existing id
    assert repo.count_active_facts(USER) == 1


def test_multi_valued_predicate_accretes(repo):
    subj = repo.get_or_create_entity(USER, "Raphael", "self")
    repo.add_fact(USER, subj, "likes", "espresso")
    repo.add_fact(USER, subj, "likes", "long walks")
    active = repo.get_active_facts(USER, subj, "likes")
    assert {f["object"] for f in active} == {"espresso", "long walks"}


def test_find_active_fact_by_object(repo):
    subj = repo.get_or_create_entity(USER, "Raphael", "self")
    repo.add_fact(USER, subj, "has_goal", "ship the memory layer")
    assert repo.find_active_fact(USER, subj, "has_goal", "ship the memory layer") is not None
    assert repo.find_active_fact(USER, subj, "has_goal", "learn to surf") is None


def test_facts_are_user_scoped(repo):
    s1 = repo.get_or_create_entity("user-a", "Raphael", "self")
    repo.add_fact("user-a", s1, "has_name", "Raphael")
    assert repo.count_active_facts("user-a") == 1
    assert repo.count_active_facts("user-b") == 0


def test_vocabulary_invariants():
    # Single-valued predicates must be a subset of the full vocabulary.
    assert SINGLE_VALUED_PREDICATES <= PREDICATE_VOCABULARY
    assert "has_name" in SINGLE_VALUED_PREDICATES
    assert "likes" not in SINGLE_VALUED_PREDICATES
