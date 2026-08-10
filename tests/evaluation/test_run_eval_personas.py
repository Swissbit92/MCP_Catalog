"""ADR-006 M1 — unit test for the persona-eval canary subset resolver."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PE = Path(__file__).parent / "persona_eval"
if str(_PE) not in sys.path:
    sys.path.insert(0, str(_PE))

from run_eval import resolve_personas  # noqa: E402

AVAILABLE = [
    "nephilim_eeva", "nephilim_nyx", "nephilim_aegis",
    "nephilim_aurora", "nephilim_cipher", "nephilim_solace", "gojo",
]


def test_short_form_maps_to_full_keys():
    assert resolve_personas(["eeva", "nyx"], AVAILABLE) == ["nephilim_eeva", "nephilim_nyx"]


def test_exact_key_matches():
    assert resolve_personas(["gojo"], AVAILABLE) == ["gojo"]
    assert resolve_personas(["nephilim_cipher"], AVAILABLE) == ["nephilim_cipher"]


def test_preserves_probe_order_and_dedupes():
    # Request order differs, but the resolver de-dupes; both tokens are distinct here.
    assert resolve_personas(["nyx", "eeva", "nyx"], AVAILABLE) == ["nephilim_nyx", "nephilim_eeva"]


def test_blank_tokens_ignored():
    assert resolve_personas(["eeva", "", "  "], AVAILABLE) == ["nephilim_eeva"]


def test_unknown_token_fails_loud():
    with pytest.raises(ValueError):
        resolve_personas(["nope"], AVAILABLE)


# ----- research-depth collection scope + report block -----

from run_eval import compute_report, depth_personas  # noqa: E402


def _fake_embed(text: str):
    """Deterministic 3-dim embedder keyed on a persona marker — no Ollama."""
    low = text.lower()
    return [1.0 if m in low else 0.0 for m in ("alpha", "beta", "gamma")] or [1.0, 0.0, 0.0]


def _row(persona, category, pid, answer):
    return {"persona": persona, "category": category, "probe_id": pid,
            "prompt": "p", "answer": answer}


def test_depth_scope_is_intersected_with_the_run_personas():
    """--personas stays authoritative: a canary must never silently probe
    someone the operator excluded."""
    dp = {"personas": ["nephilim_eeva"]}
    assert depth_personas(dp, ["nephilim_eeva", "nephilim_nyx"]) == ["nephilim_eeva"]
    assert depth_personas(dp, ["nephilim_nyx"]) == []
    assert depth_personas({}, ["nephilim_eeva"]) == []


def test_report_gains_a_research_depth_block_only_when_depth_rows_exist():
    voice_only = [_row("alpha", "distinctiveness", "d1", "alpha one"),
                  _row("alpha", "distinctiveness", "d2", "alpha two"),
                  _row("beta", "distinctiveness", "d1", "beta one"),
                  _row("beta", "distinctiveness", "d2", "beta two")]
    assert "research_depth" not in compute_report(voice_only, _fake_embed)

    with_depth = voice_only + [
        _row("alpha", "research_depth", "x1", "It fails because fees exceed carry."),
        _row("alpha", "research_depth", "x2", "Roughly 3x, so entries fire early."),
    ]
    rep = compute_report(with_depth, _fake_embed)
    assert rep["research_depth"]["n"] == 2
    assert rep["research_depth"]["mean_causal_density"] > 0


def test_errored_and_blank_depth_answers_are_excluded_from_the_aggregate():
    """A thinking model returns "" through the prod path — that is a harness
    fault, and averaging it in would understate the model's real depth."""
    rows = [_row("alpha", "distinctiveness", "d1", "alpha one"),
            _row("alpha", "distinctiveness", "d2", "alpha two"),
            _row("beta", "distinctiveness", "d1", "beta one"),
            _row("beta", "distinctiveness", "d2", "beta two"),
            _row("alpha", "research_depth", "x1", "Because fees exceed carry."),
            _row("alpha", "research_depth", "x2", ""),
            _row("alpha", "research_depth", "x3", "[ERROR: timeout]")]
    assert compute_report(rows, _fake_embed)["research_depth"]["n"] == 1


def test_a_depth_only_run_reports_depth_without_crashing_on_attribution():
    """The cheap control arm: depth rows only. Attribution is undefined with no
    distinctiveness responses and must degrade to an explicit error, not raise."""
    rows = [_row("alpha", "research_depth", "x1", "Because fees exceed carry."),
            _row("alpha", "research_depth", "x2", "Roughly 3x, therefore early.")]
    rep = compute_report(rows, _fake_embed)
    assert rep["research_depth"]["n"] == 2
    assert "error" in rep["distinctiveness"]
