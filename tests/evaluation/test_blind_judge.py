# tests/evaluation/test_blind_judge.py
# Headless tests for the per-persona blind A/B driver (ADR-005 Phase B).

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "persona_eval"))

import blind_judge as bj  # noqa: E402


def _res(persona, probe_id, answer, category="distinctiveness", prompt="p"):
    return {"persona": persona, "category": category, "probe_id": probe_id,
            "prompt": prompt, "answer": answer, "source": "llm", "elapsed": 1.0}


LEGACY = [
    _res("nephilim_eeva", "d1", "LEG eeva 1"),
    _res("nephilim_eeva", "d2", "LEG eeva 2"),
    _res("nephilim_aegis", "d1", "LEG aegis 1"),
    _res("nephilim_eeva", "g1", "LEG eeva grounding", category="grounding"),  # excluded category
]
CAND = [
    _res("nephilim_eeva", "d1", "CAND eeva 1"),
    _res("nephilim_eeva", "d2", "CAND eeva 2"),
    _res("nephilim_aegis", "d1", "CAND aegis 1"),
    _res("nephilim_eeva", "d3", "CAND eeva 3 (no legacy match)"),  # unpaired
]


def test_answers_by_persona_filters_categories():
    a = bj.answers_by_persona(LEGACY)
    assert "g1" not in a["nephilim_eeva"]  # grounding excluded
    assert a["nephilim_eeva"]["d1"] == "LEG eeva 1"


def test_build_pairs_only_shared_probes_per_persona():
    pairs = bj.build_persona_pairs(LEGACY, CAND, seed=1)
    assert set(pairs) == {"nephilim_eeva", "nephilim_aegis"}
    eeva_ids = {p.probe_id for p in pairs["nephilim_eeva"]}
    assert eeva_ids == {"d1", "d2"}  # d3 unpaired, g1 wrong category -> dropped


def test_pairs_are_arm_labeled_and_blind():
    pairs = bj.build_persona_pairs(LEGACY, CAND, seed=1)
    for p in pairs["nephilim_eeva"]:
        # whichever side, arm A text starts with LEG, arm B with CAND
        a_text = p.left if p.left_is == "A" else p.right
        b_text = p.right if p.left_is == "A" else p.left
        assert a_text.startswith("LEG")
        assert b_text.startswith("CAND")


def test_build_pairs_seed_deterministic():
    p1 = bj.build_persona_pairs(LEGACY, CAND, seed=7)
    p2 = bj.build_persona_pairs(LEGACY, CAND, seed=7)
    sides1 = [(p.probe_id, p.left_is) for p in p1["nephilim_eeva"]]
    sides2 = [(p.probe_id, p.left_is) for p in p2["nephilim_eeva"]]
    assert sides1 == sides2


def test_score_candidate_better_when_b_always_picked():
    pairs = bj.build_persona_pairs(LEGACY, CAND, seed=3)
    # Build picks that always choose the candidate (arm B) side.
    picks = {}
    for persona, plist in pairs.items():
        picks[persona] = {}
        for p in plist:
            picks[persona][p.probe_id] = "left" if p.left_is == "B" else "right"
    rep = bj.score_from_picks(pairs, picks)
    eeva = rep["per_persona"]["nephilim_eeva"]["tally"]
    assert eeva["b_wins"] == 2 and eeva["a_wins"] == 0
    assert rep["overall"]["candidate_wins"] == 3 and rep["overall"]["legacy_wins"] == 0
    assert rep["overall"]["candidate_win_rate"] == 1.0


def test_score_ties_and_skips_counted():
    pairs = bj.build_persona_pairs(LEGACY, CAND, seed=3)
    picks = {"nephilim_eeva": {"d1": "tie", "d2": "skip"}}
    rep = bj.score_from_picks(pairs, picks)
    t = rep["per_persona"]["nephilim_eeva"]["tally"]
    assert t["ties"] == 1 and t["skipped"] == 1 and t["decided"] == 0


def test_verdict_parity_when_split():
    # Two decided pairs split 1-1 -> not significant -> PARITY.
    pairs = bj.build_persona_pairs(LEGACY, CAND, seed=3)
    plist = pairs["nephilim_eeva"]
    picks = {"nephilim_eeva": {
        plist[0].probe_id: "left" if plist[0].left_is == "A" else "right",   # legacy win
        plist[1].probe_id: "left" if plist[1].left_is == "B" else "right",   # candidate win
    }}
    rep = bj.score_from_picks(pairs, picks)
    assert "PARITY" in rep["per_persona"]["nephilim_eeva"]["verdict"]
