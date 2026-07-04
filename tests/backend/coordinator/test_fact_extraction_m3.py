"""ADR-006 M3 — hermetic tests for triplet extraction, write policy, async worker.

No Ollama: a fake llm_client returns canned JSON. Real fact store on a tmp SQLite.
"""

from __future__ import annotations

import json

import pytest

from src.coordinator.triplet_extractor import TripletExtractor
from src.coordinator.fact_write_policy import apply_triples
from src.coordinator.fact_extraction_worker import FactExtractionWorker, ExtractionJob
from src.coordinator.repositories.memory_fact_repository import MemoryFactRepository

USER = "user-raphael"

TRANSCRIPT_MSGS = [
    {"role": "user", "content": "Hey, I'm Raphael. I moved to Geneva last month and I've been learning Rust."},
    {"role": "assistant", "content": "Welcome, Raphael."},
]


class _FakeLLM:
    def __init__(self, payload: str):
        self.payload = payload
        self.calls = 0

    def complete(self, system: str, user_prompt: str) -> str:
        self.calls += 1
        return self.payload


@pytest.fixture()
def repo(tmp_path):
    return MemoryFactRepository(db_path=str(tmp_path / "facts.db"))


# ---- extractor ----------------------------------------------------------

def test_extractor_keeps_valid_triples_with_present_quotes():
    payload = json.dumps({"facts": [
        {"subject": "self", "predicate": "has_name", "object": "Raphael", "quote": "I'm Raphael"},
        {"subject": "self", "predicate": "lives_in", "object": "Geneva", "quote": "I moved to Geneva last month"},
        {"subject": "self", "predicate": "is_learning", "object": "Rust", "quote": "I've been learning Rust"},
    ]})
    triples = TripletExtractor(_FakeLLM(payload)).extract_triples(TRANSCRIPT_MSGS)
    preds = {t["predicate"] for t in triples}
    assert preds == {"has_name", "lives_in", "is_learning"}


def test_extractor_drops_out_of_vocab_predicate():
    payload = json.dumps({"facts": [
        {"subject": "self", "predicate": "smells_like", "object": "rain", "quote": "I'm Raphael"},
    ]})
    assert TripletExtractor(_FakeLLM(payload)).extract_triples(TRANSCRIPT_MSGS) == []


def test_extractor_drops_fabricated_quote():
    # Quote not present in the transcript → fabrication guard drops it.
    payload = json.dumps({"facts": [
        {"subject": "self", "predicate": "works_as", "object": "astronaut", "quote": "I fly rockets for NASA"},
    ]})
    assert TripletExtractor(_FakeLLM(payload)).extract_triples(TRANSCRIPT_MSGS) == []


def test_extractor_abstains_on_empty():
    assert TripletExtractor(_FakeLLM('{"facts": []}')).extract_triples(TRANSCRIPT_MSGS) == []


def test_extractor_survives_unparseable_and_errors():
    assert TripletExtractor(_FakeLLM("not json at all")).extract_triples(TRANSCRIPT_MSGS) == []

    class _Boom:
        def complete(self, system, user_prompt):
            raise RuntimeError("ollama down")

    assert TripletExtractor(_Boom()).extract_triples(TRANSCRIPT_MSGS) == []


def test_extractor_parses_markdown_wrapped_json():
    payload = "```json\n" + json.dumps({"facts": [
        {"subject": "self", "predicate": "has_name", "object": "Raphael", "quote": "I'm Raphael"},
    ]}) + "\n```"
    triples = TripletExtractor(_FakeLLM(payload)).extract_triples(TRANSCRIPT_MSGS)
    assert len(triples) == 1 and triples[0]["object"] == "Raphael"


def test_extractor_empty_messages():
    assert TripletExtractor(_FakeLLM("{}")).extract_triples([]) == []


# ---- write policy -------------------------------------------------------

def test_write_policy_single_valued_supersedes(repo):
    apply_triples(repo, USER, [
        {"subject": "self", "predicate": "lives_in", "object": "Zurich", "object_type": "literal"},
    ])
    apply_triples(repo, USER, [
        {"subject": "self", "predicate": "lives_in", "object": "Geneva", "object_type": "literal"},
    ])
    subj = repo.get_or_create_entity(USER, "self", "self")
    active = repo.get_active_facts(USER, subj, "lives_in")
    assert len(active) == 1 and active[0]["object"] == "Geneva"
    assert active[0]["confidence"] == 0.8  # extracted-confidence marker


def test_write_policy_multi_valued_accretes_and_dedupes(repo):
    n1 = apply_triples(repo, USER, [{"subject": "self", "predicate": "likes", "object": "espresso"}])
    n2 = apply_triples(repo, USER, [{"subject": "self", "predicate": "likes", "object": "espresso"}])  # dup
    n3 = apply_triples(repo, USER, [{"subject": "self", "predicate": "likes", "object": "tea"}])
    assert (n1, n2, n3) == (1, 0, 1)
    subj = repo.get_or_create_entity(USER, "self", "self")
    assert {f["object"] for f in repo.get_active_facts(USER, subj, "likes")} == {"espresso", "tea"}


def test_write_policy_relationship_creates_person_subject(repo):
    apply_triples(repo, USER, [
        {"subject": "sister", "predicate": "lives_in", "object": "Bern", "object_type": "literal"},
    ])
    sister = repo.get_or_create_entity(USER, "sister", "person")
    assert len(repo.get_active_facts(USER, sister, "lives_in")) == 1


# ---- worker -------------------------------------------------------------

def test_worker_process_job_writes(repo):
    payload = json.dumps({"facts": [
        {"subject": "self", "predicate": "has_name", "object": "Raphael", "quote": "I'm Raphael"},
    ]})
    worker = FactExtractionWorker(lambda: TripletExtractor(_FakeLLM(payload)), repo)
    n = worker.process_job(ExtractionJob(user_id=USER, messages=TRANSCRIPT_MSGS, session_id="s1"))
    assert n == 1
    assert repo.count_active_facts(USER) == 1


def test_worker_async_drains_queue(repo):
    payload = json.dumps({"facts": [
        {"subject": "self", "predicate": "lives_in", "object": "Geneva", "quote": "I moved to Geneva last month"},
    ]})
    worker = FactExtractionWorker(lambda: TripletExtractor(_FakeLLM(payload)), repo)
    worker.start()
    try:
        assert worker.enqueue(ExtractionJob(USER, TRANSCRIPT_MSGS, "s1")) is True
        worker.join(timeout=5)
    finally:
        worker.stop()
    assert repo.count_active_facts(USER) == 1


def test_worker_survives_failing_extractor(repo):
    class _BoomExtractor:
        def extract_triples(self, messages):
            raise RuntimeError("kaboom")

    worker = FactExtractionWorker(lambda: _BoomExtractor(), repo)
    worker.start()
    try:
        worker.enqueue(ExtractionJob(USER, TRANSCRIPT_MSGS, "s1"))
        worker.join(timeout=5)
    finally:
        worker.stop()
    assert repo.count_active_facts(USER) == 0  # nothing written, worker alive
