# tests/evaluation/test_persona_ab_harness.py
# Headless tests for the Phase-A A/B harness + report core (ADR-005).

import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "persona_eval"))

import ab_harness as ab  # noqa: E402
import run_eval as re_  # noqa: E402


def _embed(text):
    # one-hot by cluster keyword (same trick as the metrics test)
    clusters = ["alpha", "beta", "gamma"]
    v = [0.0] * 3
    for i, c in enumerate(clusters):
        if c in text.lower():
            v[i] = 1.0
    if sum(v) == 0:
        v[0] = 1.0
    return v


# ----- make_blind_pairs -----

def test_pairs_cover_common_ids_and_hide_arm():
    a = {"p1": "A-one", "p2": "A-two", "p3": "A-three"}
    b = {"p1": "B-one", "p2": "B-two"}  # p3 missing in B
    pairs = ab.make_blind_pairs(a, b, rng=random.Random(0))
    assert {p.probe_id for p in pairs} == {"p1", "p2"}  # only common ids
    for p in pairs:
        assert {p.left, p.right} == {a[p.probe_id], b[p.probe_id]}
        assert p.left_is in ("A", "B")


def test_side_assignment_uses_rng_deterministically():
    a = {f"p{i}": f"A{i}" for i in range(20)}
    b = {f"p{i}": f"B{i}" for i in range(20)}
    p1 = ab.make_blind_pairs(a, b, rng=random.Random(42))
    p2 = ab.make_blind_pairs(a, b, rng=random.Random(42))
    assert [(p.probe_id, p.left_is) for p in p1] == [(p.probe_id, p.left_is) for p in p2]


# ----- tally + sign test -----

def test_tally_maps_sides_back_to_arms():
    pairs = [
        ab.BlindPair("p1", "L", "R", left_is="A"),  # pick left → A
        ab.BlindPair("p2", "L", "R", left_is="B"),  # pick left → B
        ab.BlindPair("p3", "L", "R", left_is="A"),  # pick right → B
    ]
    t = ab.tally(pairs, {"p1": "left", "p2": "left", "p3": "right"})
    assert t["a_wins"] == 1 and t["b_wins"] == 2 and t["decided"] == 3


def test_tally_handles_tie_and_skip():
    pairs = [ab.BlindPair("p1", "L", "R", "A"), ab.BlindPair("p2", "L", "R", "B")]
    t = ab.tally(pairs, {"p1": "tie", "p2": "skip"})
    assert t["ties"] == 1 and t["skipped"] == 1 and t["decided"] == 0
    assert t["a_win_rate"] is None


def test_sign_test_extremes():
    # 10-0 split is significant; 5-5 is not
    assert ab._two_sided_sign_test(10, 0) < 0.05
    assert ab._two_sided_sign_test(5, 5) == 1.0
    assert ab._two_sided_sign_test(0, 0) is None


def test_verdict_maps_to_gate():
    worse = ab.tally([ab.BlindPair(f"p{i}", "L", "R", "A") for i in range(10)],
                     {f"p{i}": "left" for i in range(10)})  # legacy(A) wins all
    assert "do NOT flip" in ab.verdict(worse)
    better = ab.tally([ab.BlindPair(f"p{i}", "L", "R", "B") for i in range(10)],
                      {f"p{i}": "left" for i in range(10)})  # candidate(B) wins all
    assert "flip" in ab.verdict(better).lower()
    parity = ab.tally([ab.BlindPair(f"p{i}", "L", "R", "A") for i in range(4)],
                      {"p0": "left", "p1": "left", "p2": "right", "p3": "right"})
    assert "PARITY" in ab.verdict(parity)


# ----- compute_report core -----

def _mk(persona, category, pid, answer):
    return {"persona": persona, "category": category, "probe_id": pid, "answer": answer}


def test_compute_report_distinctiveness_and_flatness():
    results = []
    for p, tag in [("eeva", "alpha"), ("nyx", "beta"), ("cipher", "gamma")]:
        for i in range(3):
            results.append(_mk(p, "distinctiveness", f"d{i}", f"{tag} reply {i}"))
    # one flat grounding answer
    results.append(_mk("eeva", "grounding", "g0", "As an AI, I cannot browse."))
    results.append(_mk("nyx", "grounding", "g1", "The void answers, beta."))
    rep = re_.compute_report(results, _embed)
    assert rep["distinctiveness"]["overall"] == 1.0
    assert rep["grounding_flatness_rate"] == 0.5  # 1 of 2 grounding answers flat
    assert rep["flatness_rate"]["eeva"] > 0


def test_compute_report_handles_insufficient_data():
    results = [_mk("eeva", "distinctiveness", "d0", "alpha")]  # only 1 persona/1 resp
    rep = re_.compute_report(results, _embed)
    assert "error" in rep["distinctiveness"]


def test_responses_by_persona_filters_category():
    results = [
        _mk("eeva", "distinctiveness", "d0", "alpha a"),
        _mk("eeva", "voice", "v0", "alpha b"),
    ]
    grouped = re_.responses_by_persona(results, "distinctiveness")
    assert grouped == {"eeva": ["alpha a"]}
