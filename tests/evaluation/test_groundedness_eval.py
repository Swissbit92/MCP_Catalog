# tests/evaluation/test_groundedness_eval.py
# Headless tests for the groundedness-gate eval harness. Pure scoring only —
# no Ollama, no backend. (eval_*.py is not auto-collected by pytest.ini, so the
# guards for it live here, matching eval_tool_firing / test_tool_firing_cases.)

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import eval_groundedness_gate as ev  # noqa: E402


def _row(category, expected, verdicts):
    return {"category": category, "expected_abstain": expected, "verdicts": verdicts}


# ----- ground truth -----

def test_abstain_categories_cover_every_must_stop_case():
    assert ev.expected_abstain({"category": "should_abstain"})
    assert ev.expected_abstain({"category": "reinforcement_turn"})
    assert ev.expected_abstain({"category": "adversarial_fabricated_premise"})
    assert not ev.expected_abstain({"category": "should_pass_analytical"})
    assert not ev.expected_abstain({"category": "should_pass_lore"})
    assert not ev.expected_abstain({"category": "should_pass_general_knowledge"})


# ----- the two rates -----

def test_perfect_gate_scores_clean():
    s = ev.score([
        _row("should_abstain", True, [True]),
        _row("adversarial_fabricated_premise", True, [True]),
        _row("should_pass_analytical", False, [False]),
        _row("should_pass_lore", False, [False]),
    ])
    assert s["catch_rate"] == 1.0
    assert s["false_abstain_rate"] == 0.0
    assert s["critical_missed"] == 0


def test_the_measured_bug_shows_up_as_false_abstain_not_low_catch():
    """2026-08-12: the gate caught what it should AND destroyed good answers.
    Those are separate numbers; a single 'accuracy' would have hidden it."""
    s = ev.score([
        _row("should_abstain", True, [True]),
        _row("should_abstain", True, [True]),
        _row("should_pass_analytical", False, [True]),   # destroyed
        _row("should_pass_analytical", False, [True]),   # destroyed
        _row("should_pass_analytical", False, [False]),
    ])
    assert s["catch_rate"] == 1.0          # safety looks perfect...
    assert s["false_abstain_rate"] > 0.6   # ...while utility is wrecked


# ----- the veto -----

def test_one_adversarial_miss_vetoes_even_a_great_aggregate():
    """The load-bearing rule. A fabricated premise inside valid reasoning is
    the exact failure this gate exists for — it cannot be averaged away."""
    s = ev.score([
        _row("should_abstain", True, [True]) for _ in range(20)
    ] + [
        _row("should_pass_analytical", False, [False]) for _ in range(20)
    ] + [
        _row("adversarial_fabricated_premise", True, [False]),  # the one miss
    ])
    assert s["false_abstain_rate"] == 0.0
    assert s["catch_rate"] > 0.9
    assert s["critical_missed"] == 1
    assert ev.verdict(s).startswith("REJECT")


def test_catch_rate_regression_is_rejected_even_if_false_abstain_improved():
    base = ev.score([_row("should_abstain", True, [True]) for _ in range(4)]
                    + [_row("should_pass_analytical", False, [True])])
    worse = ev.score([_row("should_abstain", True, [True]) for _ in range(3)]
                     + [_row("should_abstain", True, [False])]
                     + [_row("should_pass_analytical", False, [False])])
    assert worse["false_abstain_rate"] < base["false_abstain_rate"]  # utility up
    assert worse["catch_rate"] < base["catch_rate"]                  # safety down
    assert ev.verdict(worse, base).startswith("REJECT")


def test_a_real_improvement_is_recognised():
    base = ev.score([_row("should_abstain", True, [True])] * 3
                    + [_row("should_pass_analytical", False, [True])] * 2)
    better = ev.score([_row("should_abstain", True, [True])] * 3
                      + [_row("should_pass_analytical", False, [False])] * 2)
    assert ev.verdict(better, base).startswith("IMPROVED")


# ----- nondeterminism -----

def test_flip_rate_exposes_a_nondeterministic_classifier():
    """The gate inherits PERSONA_TEMPERATURE (0.9 in prod), so its verdict is a
    sample, not a function. Without repeats this is invisible."""
    s = ev.score([
        _row("should_abstain", True, [True, False, True]),      # flipped
        _row("should_pass_analytical", False, [False, True, False]),  # flipped
        _row("should_pass_lore", False, [False, False, False]),       # stable
    ])
    assert s["flipped_cases"] == 2
    assert s["flip_rate"] == round(2 / 3, 4)


def test_majority_decides_a_flipped_case_not_first_or_any():
    """2/3 abstain => abstained. 1/3 => passed. 'any' would over-report."""
    mostly_abstain = ev.score([_row("should_pass_analytical", False, [True, True, False])])
    assert mostly_abstain["false_abstained"] == 1
    mostly_pass = ev.score([_row("should_pass_analytical", False, [True, False, False])])
    assert mostly_pass["false_abstained"] == 0


def test_single_repeat_reports_zero_flips_rather_than_claiming_stability():
    s = ev.score([_row("should_abstain", True, [True]),
                  _row("should_pass_analytical", False, [False])])
    assert s["flip_rate"] == 0.0  # unknown, not proven stable — hence --repeats


def test_empty_and_degenerate_inputs_do_not_crash():
    s = ev.score([])
    assert s["n_cases"] == 0 and s["catch_rate"] is None and s["false_abstain_rate"] is None
    only_pass = ev.score([_row("should_pass_lore", False, [False])])
    assert only_pass["catch_rate"] is None      # nothing to catch
    assert only_pass["false_abstain_rate"] == 0.0
    assert ev.score([_row("should_abstain", True, [])])["n_cases"] == 1  # no verdicts collected


# ----- the corpus itself -----

def test_eval_set_covers_the_categories_the_harness_scores():
    data = ev.load_eval_set()
    cats = {s["category"] for s in data["samples"]}
    # Regression guard: the corpus shipped for a year with neither of these,
    # which is why the false-abstain bug was invisible.
    assert "should_pass_analytical" in cats
    assert "adversarial_fabricated_premise" in cats
    assert ev.ABSTAIN_CATEGORIES <= cats | {"reinforcement_turn"}
    for s in data["samples"]:
        assert s["category"] in data["categories"], f"undocumented category {s['category']}"
        assert s["user_turn"].strip() and s["drafted_response"].strip()


def test_adversarial_cases_include_a_no_numeral_case():
    """Numeral-presence was measured NOT predictive of gate firing, so the
    adversarial set must not be trivially solvable by a digit regex."""
    data = ev.load_eval_set()
    adv = [s for s in data["samples"]
           if s["category"] == "adversarial_fabricated_premise"]
    assert len(adv) >= 3
    assert any(not any(ch.isdigit() for ch in s["drafted_response"]) for s in adv), \
        "need at least one fabricated-premise case with no digits at all"
