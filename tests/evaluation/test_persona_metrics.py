# tests/evaluation/test_persona_metrics.py
# Headless unit tests for the Phase-A persona-eval metrics (ADR-005).
# Deterministic fake embedder — no Ollama.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "persona_eval"))

import persona_metrics as pm  # noqa: E402


# Fake embedder: one-hot by cluster keyword → clean, deterministic separation.
_CLUSTERS = ["alpha", "beta", "gamma"]


def fake_embed(text: str):
    vec = [0.0] * len(_CLUSTERS)
    low = text.lower()
    for i, c in enumerate(_CLUSTERS):
        if c in low:
            vec[i] = 1.0
    if sum(vec) == 0:
        vec[0] = 1.0
    return vec


def test_attribution_perfect_when_separable():
    resp = {
        "alpha": ["alpha one", "alpha two", "alpha three"],
        "beta": ["beta one", "beta two", "beta three"],
        "gamma": ["gamma one", "gamma two", "gamma three"],
    }
    out = pm.attribution_accuracy(resp, fake_embed)
    assert out["overall"] == 1.0
    assert all(v == 1.0 for v in out["per_persona"].values())
    assert out["random_baseline"] == round(1 / 3, 4)
    assert out["n"] == 9


def test_attribution_at_chance_when_indistinguishable():
    # Every response maps to the same vector → can't separate → ~random.
    resp = {
        "alpha": ["alpha a", "alpha b", "alpha c"],
        "beta": ["alpha d", "alpha e", "alpha f"],   # also 'alpha' cluster
        "gamma": ["alpha g", "alpha h", "alpha i"],
    }
    out = pm.attribution_accuracy(resp, fake_embed)
    # ties resolve to the first persona → only its own are 'correct' → ~1/3
    assert out["overall"] <= 0.4
    assert out["overall"] <= out["random_baseline"] + 0.01


def test_attribution_requires_two_personas():
    try:
        pm.attribution_accuracy({"alpha": ["alpha one", "alpha two"]}, fake_embed)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_attribution_requires_two_responses_each():
    resp = {"alpha": ["alpha one"], "beta": ["beta one", "beta two"]}
    try:
        pm.attribution_accuracy(resp, fake_embed)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "<2 responses" in str(e)


def test_mean_separation_higher_when_distinct():
    distinct = {
        "alpha": ["alpha one", "alpha two"],
        "beta": ["beta one", "beta two"],
    }
    same = {
        "alpha": ["alpha one", "alpha two"],
        "beta": ["alpha three", "alpha four"],
    }
    assert pm.mean_separation(distinct, fake_embed) > pm.mean_separation(same, fake_embed)


# ----- flatness detector -----

def test_flatness_detects_assistant_mode():
    assert pm.is_flat("As an AI language model, I can't have opinions.")
    assert pm.is_flat("Sure! Is there anything else I can help with?")
    assert "tool_grammar_leak" in pm.flatness_hits("I ran brave_web_search for you.")


def test_flatness_passes_in_character():
    assert not pm.is_flat("The currents favour you tonight, Seeker. Tread carefully.")
    assert pm.flatness_hits("Ah, restless again? Good. Restlessness is honest.") == []


def test_flatness_rate():
    rs = ["As an AI, I cannot.", "The void hums, Seeker.", "Happy to help!"]
    assert pm.flatness_rate(rs) == round(2 / 3, 4)
    assert pm.flatness_rate([]) == 0.0


# ----- probe set -----

def test_probes_load_and_have_categories():
    probes = pm.load_probes()
    for cat in ("distinctiveness", "voice", "grounding", "adversarial", "drift"):
        assert cat in probes, f"missing category {cat}"
    assert len(probes["personas"]) == 8  # 6 NEPHILIM + gojo + gwen (gwen added → 8-persona ruler)
    # distinctiveness prompts are shared (asked to all personas) → need >=2 for attribution
    assert len(probes["distinctiveness"]) >= 2
    # drift probes carry multi-turn sequences
    assert all("turns" in d for d in probes["drift"])


# ----- research-depth metrics -----
#
# The load-bearing property under test is NOT "does it count words" — it is that
# none of these signals can be inflated by writing more. That is the specific
# way the retired keyword `persona_voice` scorer failed, and the specific bias
# (verbosity) that dominates LLM-judge error.

_DEEP = (
    "Funding accrues per 8h interval, so a per-day moving average overstates it "
    "roughly 3x. That is why the entries fire early. However, the deployed "
    "parameters were fitted under the same convention, so correcting the unit "
    "without refitting would change behaviour. I'd want to check it by "
    "recomputing both in one unit and diffing the entry decisions."
)
_SHALLOW = (
    "Funding rates are an important part of trading. It is always good to be "
    "careful and to manage your risk properly. Markets can be unpredictable and "
    "many traders find that discipline and patience are the keys to success "
    "over the long run, so stay focused on your plan."
)


def test_depth_signals_separate_a_deep_from_a_shallow_answer():
    deep, shallow = pm.depth_profile(_DEEP), pm.depth_profile(_SHALLOW)
    assert deep["causal_density"] > shallow["causal_density"]
    assert deep["numeric_density"] > shallow["numeric_density"]
    assert deep["has_falsification"] and not shallow["has_falsification"]


def test_density_is_length_normalised_not_a_raw_count():
    """Repeating a text verbatim must NOT change its density."""
    once = pm.causal_density(_DEEP)
    twice = pm.causal_density(_DEEP + " " + _DEEP)
    assert abs(once - twice) < 0.01


def test_padding_with_filler_lowers_density_it_cannot_inflate_it():
    """The verbosity tripwire: more words without more reasoning scores WORSE."""
    filler = " and then the market moved and people watched it move" * 20
    assert pm.causal_density(_DEEP + filler) < pm.causal_density(_DEEP)
    assert pm.numeric_density(_DEEP + filler) < pm.numeric_density(_DEEP)


def test_word_count_and_empty_text_are_safe():
    assert pm.word_count("") == 0
    assert pm.word_count("three little words") == 3
    empty = pm.depth_profile("")
    assert empty["words"] == 0
    assert empty["causal_density"] == 0.0
    assert empty["numeric_density"] == 0.0
    assert not empty["has_hedge"]


def test_hedge_and_falsification_are_binary():
    assert pm.has_hedge("It might be the fee drag, though I'm not sure.")
    assert not pm.has_hedge("It is definitely the fee drag.")
    assert pm.has_falsification("Run a permutation test to check.")
    assert not pm.has_falsification("It is simply how the market works.")


def test_numeric_density_catches_percentages_multiples_and_bps():
    prof = pm.depth_profile("Sharpe 1.9, up 40%, at 3x leverage, costing 10 bps.")
    assert prof["numeric_density"] > 0
    assert pm.numeric_density("no numbers at all here") == 0.0


def test_aggregate_reports_rates_not_just_means():
    agg = pm.aggregate_depth_profiles([_DEEP, _SHALLOW])
    assert agg["n"] == 2
    assert agg["falsification_rate"] == 0.5
    assert pm.aggregate_depth_profiles([]) == {"n": 0}
    assert pm.aggregate_depth_profiles(["", ""]) == {"n": 0}


# ----- paired statistics -----

def test_pearson_r_and_its_undefined_cases():
    assert pm.pearson_r([1, 2, 3], [2, 4, 6]) == 1.0
    assert pm.pearson_r([1, 2, 3], [6, 4, 2]) == -1.0
    assert pm.pearson_r([1], [1]) is None          # n < 2
    assert pm.pearson_r([1, 1, 1], [1, 2, 3]) is None  # zero variance
    assert pm.pearson_r([1, 2], [1, 2, 3]) is None     # mismatched lengths


def test_length_bias_tripwire_fires_only_when_length_tracks_score():
    coupled = pm.length_bias_check([10, 20, 30, 40], [1, 2, 3, 4])
    assert coupled["triggered"] and coupled["pearson_r"] == 1.0

    uncoupled = pm.length_bias_check([10, 20, 30, 40], [3, 1, 4, 2])
    assert not uncoupled["triggered"]

    # Undefined correlation must not be reported as a trigger.
    assert not pm.length_bias_check([5, 5, 5], [1, 2, 3])["triggered"]
    assert not pm.length_bias_check([], [])["triggered"]


def test_tripwire_is_not_blind_to_a_clean_sweep():
    """Regression: a candidate that wins EVERY pair has zero-variance score
    deltas, so Pearson is undefined and a correlation-only tripwire passes
    silently — in the exact case where 'did length drive this?' matters most.
    Sign concordance covers it."""
    sweep_longer = pm.length_bias_check([10, 20, 30, 40, 50, 60], [1, 1, 1, 1, 1, 1])
    assert sweep_longer["pearson_r"] is None       # undefined, as expected
    assert sweep_longer["sign_concordance"] == 1.0
    assert sweep_longer["triggered"]

    # A sweep won while being SHORTER is not length bias — it is the opposite.
    sweep_shorter = pm.length_bias_check([-10, -20, -30, -40, -50, -60], [1, 1, 1, 1, 1, 1])
    assert sweep_shorter["sign_concordance"] == 0.0
    assert not sweep_shorter["triggered"]

    # Too few signed pairs to trust concordance — 2-for-2 is noise, not evidence.
    assert not pm.length_bias_check([10, 20], [1, 1])["triggered"]


def test_bootstrap_ci_excludes_zero_only_for_a_consistent_effect():
    consistent = pm.paired_bootstrap([2.0, 3.0, 2.5, 3.5, 2.0, 3.0], seed=1)
    assert consistent["excludes_zero"]
    assert consistent["mean"] > 0

    mixed = pm.paired_bootstrap([2.0, -2.0, 1.0, -1.0, 3.0, -3.0], seed=1)
    assert not mixed["excludes_zero"]

    assert pm.paired_bootstrap([], seed=1)["excludes_zero"] is False


def test_bootstrap_is_deterministic_under_a_seed():
    """A gate that moves between runs is not a gate."""
    a = pm.paired_bootstrap([1.0, 2.0, 0.5, 1.5], seed=7)
    b = pm.paired_bootstrap([1.0, 2.0, 0.5, 1.5], seed=7)
    assert a == b


# ----- the depth probe set itself -----

def test_depth_probes_load_and_are_well_formed():
    probes = pm.load_depth_probes()
    assert len(probes["probes"]) >= 12
    ids = [p["id"] for p in probes["probes"]]
    assert len(ids) == len(set(ids)), "duplicate probe ids"
    for p in probes["probes"]:
        assert p["prompt"].strip()
        # A reference key is what makes grading reference-guided rather than
        # vibes-based; a probe without one cannot be judged consistently.
        assert len(p["key"]) >= 3, f"{p['id']} has too thin a reference key"
    assert len(probes["dimensions"]) == 7
