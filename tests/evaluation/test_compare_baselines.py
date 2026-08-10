"""Headless unit tests for the compare_baselines commensurability guard.

The guard closes a silent-inflation hole: attribution accuracy's chance floor is
1/N, so a candidate run over a different (smaller) label space is not comparable
to a full-N ruler and must not clear a bare `overall` gate. Also covers the
frozen-gallery case (same N, active-persona subset → per-persona gate).
"""

from __future__ import annotations

import sys
from pathlib import Path

_PE = Path(__file__).parent / "persona_eval"
if str(_PE) not in sys.path:
    sys.path.insert(0, str(_PE))

from compare_baselines import compare  # noqa: E402


def _baseline(per_persona: dict, overall: float, n: int, flatness: float = 0.0) -> dict:
    """Minimal baseline artifact shaped like freeze_baseline output."""
    return {
        "report": {
            "distinctiveness": {
                "overall": overall,
                "per_persona": per_persona,
                "random_baseline": round(1.0 / n, 4),
            },
            "flatness_rate_overall": flatness,
        }
    }


# ---- full-vs-full (same N, same persona set) → overall gate ----


def test_full_match_or_beat_passes():
    off = _baseline({"a": 0.7, "b": 0.7, "c": 0.7}, overall=0.70, n=3)
    on = _baseline({"a": 0.75, "b": 0.7, "c": 0.72}, overall=0.723, n=3)
    res = compare(off, on)
    assert res["commensurable"] is True
    assert res["mode"] == "overall"
    assert res["verdict"] == "MATCH-OR-BEAT"


def test_full_regression_fails():
    off = _baseline({"a": 0.8, "b": 0.8, "c": 0.8}, overall=0.80, n=3)
    on = _baseline({"a": 0.5, "b": 0.6, "c": 0.7}, overall=0.60, n=3)
    res = compare(off, on)
    assert res["mode"] == "overall"
    assert res["verdict"] == "REGRESSION"


def test_full_within_tolerance_still_passes():
    # ON drops exactly TOL (0.01) below → still MATCH-OR-BEAT (>= off - TOL).
    off = _baseline({"a": 0.75, "b": 0.75}, overall=0.75, n=2)
    on = _baseline({"a": 0.75, "b": 0.74}, overall=0.74, n=2)
    assert compare(off, on)["verdict"] == "MATCH-OR-BEAT"


# ---- the silent-inflation hole: different N → INCOMMENSURABLE, no verdict ----


def test_different_n_refuses_verdict():
    # 7-persona ruler (chance 0.1429) vs 2-persona candidate (chance 0.5).
    off = _baseline(dict.fromkeys("abcdefg", 0.7), overall=0.70, n=7)
    on = _baseline({"a": 1.0, "b": 1.0}, overall=1.00, n=2)
    res = compare(off, on)
    assert res["commensurable"] is False
    assert res["verdict"] == "INCOMMENSURABLE"
    assert res["n_off"] == 7 and res["n_on"] == 2


def test_different_n_does_not_report_match_or_beat():
    # Even though the 2-persona candidate 'overall' 1.0 >> ruler 0.70, no green.
    off = _baseline(dict.fromkeys("abcdefgh", 0.7), overall=0.70, n=8)
    on = _baseline({"a": 1.0, "b": 1.0}, overall=1.00, n=2)
    assert compare(off, on)["verdict"] != "MATCH-OR-BEAT"


# ---- frozen-gallery: same N (8), candidate scored only active subset ----


def test_gallery_subset_gates_per_persona_pass():
    off = _baseline(
        dict(zip("abcdefgh", [0.75, 0.5, 0.75, 0.875, 0.75, 0.625, 0.875, 0.6], strict=True)),
        overall=0.71,
        n=8,
    )
    # Only two active personas re-probed, same N=8 label space (frozen gallery).
    on = _baseline({"a": 0.75, "h": 0.625}, overall=0.6875, n=8)
    res = compare(off, on)
    assert res["commensurable"] is True
    assert res["mode"] == "per_persona"
    assert set(res["shared"]) == {"a", "h"}
    assert res["verdict"] == "MATCH-OR-BEAT"  # a flat, h improved


def test_gallery_subset_gates_per_persona_regression():
    off = _baseline(dict.fromkeys("abcdefgh", 0.75), overall=0.75, n=8)
    on = _baseline({"a": 0.5, "h": 0.75}, overall=0.625, n=8)  # a collapsed
    res = compare(off, on)
    assert res["mode"] == "per_persona"
    assert res["verdict"] == "REGRESSION"
    assert res["worst"] < 0


def test_gallery_same_n_but_no_shared_personas_refuses():
    off = _baseline({"a": 0.75, "b": 0.75}, overall=0.75, n=8)
    on = _baseline({"c": 0.75, "d": 0.75}, overall=0.75, n=8)
    res = compare(off, on)
    assert res["commensurable"] is False
    assert res["verdict"] == "INCOMMENSURABLE"


def test_missing_random_baseline_refuses():
    off = {"report": {"distinctiveness": {"overall": 0.7, "per_persona": {"a": 0.7, "b": 0.7}}}}
    on = _baseline({"a": 0.7, "b": 0.7}, overall=0.7, n=2)
    assert compare(off, on)["verdict"] == "INCOMMENSURABLE"


def test_degenerate_zero_random_baseline_refuses():
    # A random_baseline of 0 is an undefined 1/N floor — must land in
    # INCOMMENSURABLE explicitly, never slide into a comparison as "passed".
    off = {
        "report": {
            "distinctiveness": {
                "overall": 0.7,
                "per_persona": {"a": 0.7, "b": 0.7},
                "random_baseline": 0,
            }
        }
    }
    on = _baseline({"a": 0.9, "b": 0.9}, overall=0.9, n=2)
    res = compare(off, on)
    assert res["commensurable"] is False
    assert res["verdict"] == "INCOMMENSURABLE"
