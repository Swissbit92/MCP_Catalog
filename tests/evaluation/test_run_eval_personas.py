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
