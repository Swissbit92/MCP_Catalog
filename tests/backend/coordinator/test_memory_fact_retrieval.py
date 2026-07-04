"""ADR-006 M4 — unit tests for fact retrieval + prose rendering. Hermetic."""

from __future__ import annotations

from src.coordinator.memory_fact_retrieval import (
    render_facts_narrative,
    select_facts_for_injection,
)


def _fact(i, predicate, obj, subject_id="self"):
    return {"id": i, "subject_id": subject_id, "predicate": predicate, "object": obj}


def test_render_self_facts_as_prose():
    facts = [
        _fact(1, "has_name", "Raphael"),
        _fact(2, "lives_in", "Geneva"),
        _fact(3, "is_learning", "Rust"),
    ]
    out = render_facts_narrative(facts, subject_names={"self": "self"})
    assert out.startswith("You also remember that")
    assert "their name is Raphael" in out
    assert "they live in Geneva" in out
    assert "they're learning Rust" in out
    assert "\n- " not in out and "**" not in out  # prose, not a skeleton


def test_render_named_subject():
    facts = [_fact(1, "lives_in", "Bern", subject_id="e-sister")]
    out = render_facts_narrative(facts, subject_names={"e-sister": "sister"})
    assert "sister" in out and "Bern" in out


def test_render_empty():
    assert render_facts_narrative([]) == ""


def test_render_unknown_predicate_falls_back():
    facts = [_fact(1, "owns", "a sailboat")]
    out = render_facts_narrative(facts, subject_names={"self": "self"})
    assert "sailboat" in out


def test_select_injects_all_below_threshold():
    facts = [_fact(i, "likes", f"thing{i}") for i in range(5)]
    got = select_facts_for_injection(facts, "anything", k=3, inject_all_threshold=15)
    assert len(got) == 5  # all of them; no vector search


def test_select_topk_recency_fallback_without_embedder():
    facts = [_fact(i, "likes", f"thing{i}") for i in range(20)]
    got = select_facts_for_injection(facts, "q", k=3, inject_all_threshold=15, embed_fn=None)
    assert len(got) == 3
    assert [f["id"] for f in got] == [19, 18, 17]  # most-recent


def test_select_topk_cosine_with_embedder():
    facts = [
        _fact(1, "likes", "espresso"),
        _fact(2, "likes", "hiking"),
        _fact(3, "likes", "jazz"),
    ] + [_fact(i, "likes", f"filler{i}") for i in range(4, 20)]

    # Fake embedder: the query and 'hiking' clause share a token → high cosine.
    def embed(text: str):
        t = text.lower()
        return [
            1.0 if "hiking" in t else 0.0,
            1.0 if "espresso" in t else 0.0,
            0.1,
        ]

    got = select_facts_for_injection(
        facts, "let's go hiking", k=1, inject_all_threshold=5, embed_fn=embed
    )
    assert len(got) == 1
    assert got[0]["object"] == "hiking"


def test_select_embed_failure_falls_back_to_recency():
    facts = [_fact(i, "likes", f"t{i}") for i in range(20)]

    def boom(text):
        raise RuntimeError("embed down")

    got = select_facts_for_injection(facts, "q", k=2, inject_all_threshold=5, embed_fn=boom)
    assert [f["id"] for f in got] == [19, 18]
