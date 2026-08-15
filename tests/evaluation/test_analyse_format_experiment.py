# tests/evaluation/test_analyse_format_experiment.py
# Headless tests for the pre-registered format-experiment analysis.
# Pure statistics — no Ollama, no backend. These exist because the analysis is
# the thing standing between a promising mean and a false ship.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "persona_eval"))

import analyse_format_experiment as af  # noqa: E402


def _rows(probe_answers, repeats=3):
    """probe_answers: {probe_id: text} -> repeated rows."""
    return [{"probe_id": p, "repeat": r, "answer": a}
            for p, a in probe_answers.items() for r in range(repeats)]


# ----- aggregation -----

def test_item_means_average_within_probe_before_pairing():
    """The unit of independence is the PROBE. Repeats sharpen its estimate;
    they must not become extra rows in the test."""
    rows = [{"probe_id": "a", "answer": "x"}, {"probe_id": "a", "answer": "xxx"},
            {"probe_id": "b", "answer": "xx"}]
    means = af.item_means(rows, lambda t: float(len(t)))
    assert means == {"a": 2.0, "b": 2.0}


def test_errored_and_blank_generations_are_dropped_not_scored_zero():
    rows = [{"probe_id": "a", "answer": "ok"}, {"probe_id": "a", "answer": ""},
            {"probe_id": "a", "answer": "[ERROR: boom]"}, {"probe_id": "a", "answer": None}]
    assert af.item_means(rows, lambda t: 10.0) == {"a": 10.0}


def test_pairing_only_covers_probes_in_both_arms_and_is_order_stable():
    c, k = {"a": 1.0, "b": 2.0, "z": 9.0}, {"a": 2.0, "b": 2.5, "q": 0.0}
    assert af.paired_deltas(c, k) == [1.0, 0.5]  # sorted by probe id


# ----- the exact permutation test -----

def test_permutation_is_exhaustive_and_symmetric():
    """All 2^n flips, and the p-value must not depend on the sign convention."""
    d = [1.0, 2.0, 3.0]
    assert af.exact_permutation_p(d) == af.exact_permutation_p([-x for x in d])


def test_a_unanimous_effect_reaches_the_minimum_achievable_p():
    """n=12 all-positive => only the all-positive and all-negative flips are as
    extreme => p = 2/4096."""
    p = af.exact_permutation_p([1.0] * 12)
    assert p == round(2 / 4096, 6)
    assert p < 0.05


def test_a_null_shaped_sample_is_not_significant():
    assert af.exact_permutation_p([1.0, -1.0, 1.0, -1.0, 0.5, -0.5]) > 0.05


def test_permutation_refuses_to_blow_up_on_large_n():
    import pytest
    with pytest.raises(ValueError):
        af.exact_permutation_p([1.0] * 21)


def test_empty_input_returns_none_not_a_fake_pvalue():
    assert af.exact_permutation_p([]) is None


# ----- sign test + effect size -----

def test_sign_test_matches_the_prereg_threshold_at_n12():
    """The pre-registration states 10/12 reaches p<0.05 and 9/12 does not.
    If this ever fails, the pre-registered rule was mis-stated."""
    ten = af.exact_sign_test([1.0] * 10 + [-1.0] * 2)
    nine = af.exact_sign_test([1.0] * 9 + [-1.0] * 3)
    assert ten["p"] < 0.05
    assert nine["p"] > 0.05


def test_sign_test_drops_ties():
    r = af.exact_sign_test([1.0, -1.0, 0.0, 0.0])
    assert r["favour_candidate"] == 1 and r["favour_control"] == 1 and r["ties"] == 2


def test_cohens_d_is_undefined_rather_than_infinite_for_constant_deltas():
    assert af.paired_cohens_d([2.0] * 5) is None
    assert af.paired_cohens_d([1.0]) is None


# ----- the decision rule -----

def test_ship_requires_both_significance_and_breadth():
    """A significant mean carried by a few big items is NOT a ship — the
    pre-registration demands >=10/12 items favour the candidate."""
    broad = [0.4] * 11 + [-0.05]
    v = af.decide(broad, af.exact_sign_test(broad), af.exact_permutation_p(broad),
                  af.paired_cohens_d(broad))
    assert v.startswith("SHIP")

    narrow = [6.0, 6.0, 6.0] + [-0.2] * 9   # big mean, only 3 items favour it
    v2 = af.decide(narrow, af.exact_sign_test(narrow), af.exact_permutation_p(narrow),
                   af.paired_cohens_d(narrow))
    assert not v2.startswith("SHIP")


def test_flat_result_is_killed_not_called_inconclusive():
    flat = [0.02, -0.03, 0.01, -0.02, 0.0, 0.01, -0.01, 0.02, -0.02, 0.01, 0.0, -0.01]
    v = af.decide(flat, af.exact_sign_test(flat), af.exact_permutation_p(flat),
                  af.paired_cohens_d(flat))
    assert v.startswith("KILL")


def test_underpowered_large_effect_is_inconclusive_and_says_more_items():
    """The trap this guards: reporting 'not significant' as 'does not work'
    when n=12 simply cannot resolve it. 8 of 12 items favour the candidate at
    d=0.54 — a real, moderate-to-large effect — and the permutation p is still
    0.119, because at n=12 nothing short of ~10/12 can clear 0.05."""
    d = [1.5] * 8 + [-1.0] * 4
    p, dd = af.exact_permutation_p(d), af.paired_cohens_d(d)
    assert p > 0.05 and dd >= 0.5          # the branch we mean to exercise
    v = af.decide(d, af.exact_sign_test(d), p, dd)
    assert "INCONCLUSIVE" in v
    assert "MORE ITEMS" in v               # the follow-up must be items, not repeats


def test_a_large_mean_with_a_huge_spread_is_flat_not_underpowered():
    """Guard against the mirror mistake: [3,-2.5,4,-3,3.5,-2] LOOKS dramatic but
    is mean 0.5 against sd 3.3, i.e. d=0.15. That is flat, and calling it
    'underpowered' would keep a dead idea alive."""
    d = [3.0, -2.5, 4.0, -3.0, 3.5, -2.0]
    v = af.decide(d, af.exact_sign_test(d), af.exact_permutation_p(d), af.paired_cohens_d(d))
    assert v.startswith("KILL")


def test_no_data_is_reported_as_such():
    assert af.decide([], {"favour_candidate": 0}, None, None) == "NO DATA"


# ----- the pre-registration itself -----

def test_prereg_is_present_and_names_the_primary_endpoint():
    p = af.load_prereg()
    assert p["registered_before_any_data_collected"] is True
    assert p["primary_endpoint"]["metric"] == "causal_density"
    assert "SHIP" in p["decision_rule"] and "KILL" in p["decision_rule"]
    # Word count must NOT be the primary endpoint — the change is expected to
    # increase length, so scoring it would measure compliance, not reasoning.
    assert p["primary_endpoint"]["metric"] != "words"
    assert "words" in p["secondary_metrics"]["metrics"]
