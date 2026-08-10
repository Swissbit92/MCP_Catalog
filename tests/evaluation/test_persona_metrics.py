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
