# tests/evaluation/test_tool_firing_cases.py
"""Headless guards for the tool-firing eval (``eval_tool_firing.py``).

The eval runner itself is named ``eval_*`` and so is NOT auto-collected
(``pytest.ini``: ``python_files = test_*.py``) — same convention as
``eval_lore_retrieval.py``, since running it costs real LLM turns. These guards
live in a collected file on purpose: they keep the golden set and the scoring
math honest on every suite run, so the harness cannot silently rot between the
occasional live executions.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from eval_tool_firing import CaseResult, Scorecard  # noqa: E402
from tool_firing_cases import (  # noqa: E402
    BUCKETS,
    CHITCHAT,
    GOLDEN_CASES,
    IMAGE_FIND,
    VIDEO_FIND,
    WALLET,
    cases_for_bucket,
)


def test_golden_set_schema():
    """The case set is well-formed and every bucket is populated."""
    seen_ids = set()
    for c in GOLDEN_CASES:
        assert c["id"] not in seen_ids, f"duplicate case id {c['id']}"
        seen_ids.add(c["id"])
        assert c["bucket"] in BUCKETS, f"{c['id']}: unknown bucket {c['bucket']}"
        assert c["query"].strip(), f"{c['id']}: empty query"
        assert isinstance(c["expect"], set) and c["expect"], f"{c['id']}: bad expect"
        assert c["persona"], f"{c['id']}: no persona"

    for b in BUCKETS:
        assert cases_for_bucket(b), f"bucket {b} has no cases"


def test_negative_buckets_stay_populated():
    """Chitchat/wallet catch the expensive failure — firing when it must not.

    Guards against the negative cases being whittled down over time, which
    would leave the eval measuring only the happy path.
    """
    assert len(cases_for_bucket(CHITCHAT)) >= 5
    assert len(cases_for_bucket(WALLET)) >= 3


def test_media_cases_declare_expected_tool():
    """Media cases must pin the tool, else ROADMAP item 45 stays undecidable."""
    for c in GOLDEN_CASES:
        if c["bucket"] in (IMAGE_FIND, VIDEO_FIND):
            assert "expect_tool" in c, f"{c['id']}: media case needs expect_tool"


def test_accuracy_and_false_positives():
    card = Scorecard(
        results=[
            CaseResult("a", "web_explicit", "q", "tool_brain", correct=True, native_fire=True),
            CaseResult("b", "web_explicit", "q", "brave_mcp", correct=True),
            CaseResult("c", CHITCHAT, "q", "llm", correct=True),
            CaseResult("d", CHITCHAT, "q", "tool_brain", native_fire=True),
        ]
    )
    assert card.accuracy() == 0.75
    assert [r.case_id for r in card.false_positives()] == ["d"]


def test_native_fire_rate_divides_by_grounded_turns_only():
    """Denominator must be grounded turns, not all turns.

    Dividing by everything would let a pile of correctly-silent chitchat mask
    a tool brain that never natively fires — the exact conclusion this eval
    exists to expose.
    """
    card = Scorecard(
        results=[
            CaseResult("a", "web_explicit", "q", "tool_brain", correct=True, native_fire=True),
            CaseResult("b", "web_explicit", "q", "brave_mcp", correct=True),
            CaseResult("c", CHITCHAT, "q", "llm", correct=True),
            CaseResult("d", CHITCHAT, "q", "llm", correct=True),
        ]
    )
    # grounded = a, b -> 1 of 2 native. Not 1 of 4.
    assert card.native_fire_rate() == 0.5


def test_errors_excluded_from_rates_not_counted_as_failures():
    """A transport error is missing data, not a wrong answer."""
    card = Scorecard(
        results=[
            CaseResult("a", "web_explicit", "q", "tool_brain", correct=True, native_fire=True),
            CaseResult("e", "web_explicit", "q", "", error="boom"),
        ]
    )
    assert card.accuracy() == 1.0
    assert card.native_fire_rate() == 1.0
    assert len(card.errors()) == 1


def test_wallet_leak_detection():
    """A wallet turn on the native surface is a safety fail, flagged separately."""
    card = Scorecard(
        results=[
            CaseResult("w1", WALLET, "q", "wallet_mcp", correct=True),
            CaseResult("w2", WALLET, "q", "tool_brain"),
        ]
    )
    assert [r.case_id for r in card.wallet_leaks()] == ["w2"]


def test_scorecard_renders_and_serialises_without_live_data():
    card = Scorecard(
        results=[CaseResult("a", "web_explicit", "q", "tool_brain", correct=True, native_fire=True)]
    )
    assert "TOOL-FIRING SCORECARD" in card.render()
    d = card.to_dict()
    assert d["overall"]["n"] == 1
    assert d["buckets"]["web_explicit"]["accuracy"] == 1.0


def test_empty_scorecard_does_not_divide_by_zero():
    card = Scorecard(results=[])
    assert card.accuracy() == 0.0
    assert card.native_fire_rate() == 0.0
    assert card.tool_match_rate() == 0.0
    assert card.render()
