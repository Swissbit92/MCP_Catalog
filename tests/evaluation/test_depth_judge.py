# tests/evaluation/test_depth_judge.py
# Headless unit tests for the research-depth blind judging harness.
# Pure pairing/scoring/gate logic — no Ollama, no backend, no interactivity.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "persona_eval"))

import ab_harness as ab  # noqa: E402
import depth_judge as dj  # noqa: E402


def _row(probe_id, answer, category="research_depth", persona="nephilim_eeva"):
    return {"persona": persona, "category": category, "probe_id": probe_id,
            "prompt": "p", "answer": answer, "source": "llm", "elapsed": 1.0}


# ----- extraction -----

def test_depth_answers_selects_only_the_depth_category():
    rows = [_row("d1", "deep"), _row("v1", "voice", category="voice")]
    assert dj.depth_answers(rows) == {"d1": "deep"}


def test_depth_answers_drops_errors_and_blanks_rather_than_scoring_them():
    """An empty answer is a harness fault (thinking model ate the budget), not a
    weak argument. Scoring it as a loss would fabricate evidence."""
    rows = [_row("d1", ""), _row("d2", "[ERROR: boom]"), _row("d3", "real"), _row("d4", None)]
    assert dj.depth_answers(rows) == {"d3": "real"}


# ----- pairing -----

def test_pairs_only_cover_probes_present_in_both_arms():
    ctrl = [_row("d1", "c1"), _row("d2", "c2")]
    cand = [_row("d2", "x2"), _row("d3", "x3")]
    pairs = dj.build_depth_pairs(ctrl, cand, seed=1, probes={"probes": []})
    assert [p.probe_id for p in pairs] == ["d2"]


def test_pairs_carry_the_reference_key_for_the_judge():
    probes = {"probes": [{"id": "d1", "prompt": "why?", "key": ["k1", "k2"], "trap": ["t1"]}]}
    pairs = dj.build_depth_pairs([_row("d1", "c")], [_row("d1", "x")], seed=0, probes=probes)
    assert pairs[0].meta["key"] == ["k1", "k2"]
    assert pairs[0].meta["trap"] == ["t1"]
    assert pairs[0].meta["prompt"] == "why?"


def test_arm_identity_is_hidden_but_recoverable_for_scoring():
    ctrl, cand = [_row("d1", "CONTROL")], [_row("d1", "CANDIDATE")]
    p = dj.build_depth_pairs(ctrl, cand, seed=3, probes={"probes": []})[0]
    shown = {p.left, p.right}
    assert shown == {"CONTROL", "CANDIDATE"}
    # left_is tells the scorer which side was the control without telling the judge
    assert (p.left == "CONTROL") == (p.left_is == "A")


# ----- pick -> outcome mapping -----

def _pair(pid, left_is):
    return ab.BlindPair(probe_id=pid, left="L", right="R", left_is=left_is, meta={})


def test_winner_mapping_respects_the_randomised_side():
    assert dj._winner(_pair("a", "A"), "left") == "A"
    assert dj._winner(_pair("a", "A"), "right") == "B"
    assert dj._winner(_pair("a", "B"), "left") == "B"
    assert dj._winner(_pair("a", "B"), "right") == "A"
    assert dj._winner(_pair("a", "A"), "tie") is None


def test_deltas_are_signed_candidate_positive_and_ties_are_kept_as_zero():
    pairs = [_pair("d1", "A"), _pair("d2", "B"), _pair("d3", "A"), _pair("d4", "A")]
    picks = {"d1": "right", "d2": "left", "d3": "left", "d4": "tie"}
    #        d1: B wins(+1)   d2: B wins(+1)  d3: A wins(-1)  d4: tie(0)
    assert dj.picks_to_deltas(pairs, picks) == [1.0, 1.0, -1.0, 0.0]


def test_skipped_pairs_are_excluded_entirely():
    pairs = [_pair("d1", "A"), _pair("d2", "A")]
    assert dj.picks_to_deltas(pairs, {"d1": "left"}) == [-1.0]  # d2 unjudged => skip


def test_length_deltas_stay_aligned_with_outcome_deltas():
    """The tripwire correlates these two lists pairwise — a length mismatch would
    silently compare different probes and produce a meaningless r."""
    ctrl = [_row("d1", "one two three"), _row("d2", "a"), _row("d3", "x")]
    cand = [_row("d1", "one"), _row("d2", "a b c d e"), _row("d3", "y")]
    pairs = dj.build_depth_pairs(ctrl, cand, seed=5, probes={"probes": []})
    picks = {p.probe_id: ("left" if i else "tie") for i, p in enumerate(pairs)}
    picks[pairs[0].probe_id] = "skip"  # one skipped => both lists must shrink together
    assert len(dj.picks_to_deltas(pairs, picks)) == len(dj.picks_to_length_deltas(pairs, picks))


def test_length_delta_sign_is_candidate_minus_control():
    ctrl, cand = [_row("d1", "a")], [_row("d1", "a b c d e")]
    pairs = dj.build_depth_pairs(ctrl, cand, seed=0, probes={"probes": []})
    assert dj.picks_to_length_deltas(pairs, {"d1": "left"}) == [4.0]


# ----- the gate -----

def _sweep(n, candidate_wins, left_is="A"):
    """n pairs where the first `candidate_wins` are won by the candidate (arm B)."""
    pairs = [_pair(f"d{i}", left_is) for i in range(n)]
    picks = {}
    for i in range(n):
        # left_is="A" => picking "right" is a candidate win
        picks[f"d{i}"] = "right" if i < candidate_wins else "left"
    return pairs, picks


def test_clean_sweep_for_the_candidate_is_a_depth_win():
    pairs, picks = _sweep(12, 12)
    rep = dj.depth_report(pairs, picks, seed=1)
    assert rep["passes"]["sign_test"]
    assert rep["passes"]["bootstrap_excludes_zero"]
    assert rep["passes"]["length_clean"]
    assert rep["verdict"].startswith("DEPTH WIN")


def test_a_narrow_win_does_not_clear_the_gate():
    """7/12 is ~58% — inside noise at this n. Must not report a win."""
    pairs, picks = _sweep(12, 7)
    rep = dj.depth_report(pairs, picks, seed=1)
    assert not rep["passes"]["candidate_ahead"]
    assert rep["verdict"].startswith("NO DIFFERENCE")


def test_control_sweep_is_a_regression():
    pairs, picks = _sweep(12, 0)
    rep = dj.depth_report(pairs, picks, seed=1)
    assert rep["verdict"].startswith("DEPTH REGRESSION")
    assert not rep["passes"]["bootstrap_excludes_zero"]


def test_a_win_driven_by_length_is_quarantined_not_reported():
    """The load-bearing test. Candidate sweeps, but every win coincides with a
    longer answer — exactly the verbosity bias the judge is known to fall for."""
    n = 12
    ctrl = [_row(f"d{i}", "short") for i in range(n)]
    cand = [_row(f"d{i}", " ".join(["word"] * (5 + 10 * i))) for i in range(n)]
    pairs = dj.build_depth_pairs(ctrl, cand, seed=2, probes={"probes": []})
    picks = {p.probe_id: ("right" if p.left_is == "A" else "left") for p in pairs}  # candidate always
    rep = dj.depth_report(pairs, picks, ctrl, cand, seed=1)
    assert rep["passes"]["sign_test"] and rep["passes"]["candidate_ahead"]
    assert not rep["passes"]["length_clean"]
    assert rep["verdict"].startswith("QUARANTINED")


def test_deterministic_cross_check_flags_a_judge_who_liked_flat_reasoning():
    """Judge prefers the candidate, but the candidate's causal density did NOT
    rise — the signal that the judge rated fluency, not reasoning."""
    ctrl = [_row(f"d{i}", "It fails because fees exceed carry, therefore it loses.")
            for i in range(4)]
    cand = [_row(f"d{i}", "Markets move in mysterious ways and outcomes vary widely.")
            for i in range(4)]
    pairs = dj.build_depth_pairs(ctrl, cand, seed=4, probes={"probes": []})
    picks = {p.probe_id: ("right" if p.left_is == "A" else "left") for p in pairs}
    rep = dj.depth_report(pairs, picks, ctrl, cand, seed=1)
    assert rep["deterministic"]["causal_density_moved_with_judge"] is False


def test_no_judgements_reports_no_difference_rather_than_crashing():
    pairs = [_pair("d1", "A"), _pair("d2", "B")]
    rep = dj.depth_report(pairs, {}, seed=1)
    assert rep["tally"]["decided"] == 0
    assert rep["candidate_win_rate"] is None
    assert rep["verdict"].startswith("NO DIFFERENCE")


def test_report_is_deterministic_under_a_seed():
    pairs, picks = _sweep(12, 10)
    assert dj.depth_report(pairs, picks, seed=9) == dj.depth_report(pairs, picks, seed=9)
