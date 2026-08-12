"""Headless unit tests for the frozen reference gallery scoring mode.

`attribution_accuracy(..., frozen_personas=...)` freezes the dormant personas as
reference prototypes (competitors, not scored) so the active personas can be
re-probed against the full label space. The headline test is geometric: it proves
that keeping a confusable neighbour FROZEN (vs dropping it, the invalid
label-space shrink) lowers the active persona's score exactly as it should —
i.e. the frozen field prevents the subset-inflation.

Deterministic keyed embedder — no Ollama.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PE = Path(__file__).parent / "persona_eval"
if str(_PE) not in sys.path:
    sys.path.insert(0, str(_PE))

import frozen_gallery as fg  # noqa: E402
import persona_metrics as pm  # noqa: E402
from run_eval import compute_report  # noqa: E402

# ---- deterministic 2-D unit-vector embedder keyed by response label ----
# Cosine attribution cares about ANGLE, so we place responses at fixed angles:
#   A at 0°, its stray response at 15°, C at 20° (confusable with A), B at 90°.
_VECS = {
    "A0a": [1.0, 0.0],  # 0°
    "A0b": [1.0, 0.0],  # 0°
    "A15": [0.9659, 0.2588],  # 15°  (leans toward C)
    "C20a": [0.9397, 0.3420],  # 20°
    "C20b": [0.9397, 0.3420],  # 20°
    "B90a": [0.0, 1.0],  # 90°
    "B90b": [0.0, 1.0],  # 90°
}


def keyed_embed(text: str):
    return _VECS[text]


def _abc():
    return {
        "A": ["A0a", "A0b", "A15"],
        "B": ["B90a", "B90b"],
        "C": ["C20a", "C20b"],
    }


# ---- backward compatibility: no frozen set ⇒ identical to the original ----


def test_no_frozen_is_byte_identical():
    resp = _abc()
    a = pm.attribution_accuracy(resp, keyed_embed)
    b = pm.attribution_accuracy(resp, keyed_embed, frozen_personas=None)
    c = pm.attribution_accuracy(resp, keyed_embed, frozen_personas=set())
    assert a == b == c
    # and it does NOT add the gallery-only keys when nothing is frozen
    assert "frozen_personas" not in a
    assert "scored_personas" not in a


# ---- the headline: frozen neighbour prevents subset inflation ----


def test_frozen_neighbour_prevents_inflation():
    resp = _abc()
    # Drop C entirely (the INVALID label-space shrink): A no longer competes with
    # its confusable neighbour, so its stray 15° response is safely attributed to A.
    dropped = pm.attribution_accuracy({"A": resp["A"], "B": resp["B"]}, keyed_embed)
    assert dropped["per_persona"]["A"] == 1.0
    assert dropped["random_baseline"] == round(1 / 2, 4)

    # Keep C as a FROZEN competitor (the valid gallery): the 15° response is now
    # nearer C's 20° centroid than A's held-out 0° centroid → correctly stolen.
    gallery = pm.attribution_accuracy(resp, keyed_embed, frozen_personas={"C"})
    assert gallery["per_persona"]["A"] == round(2 / 3, 4)  # lower, as it should be
    assert gallery["random_baseline"] == round(1 / 3, 4)  # chance stays 1/N_all
    # the stolen vote shows up in the confusion matrix as A→C
    assert gallery["confusion"]["A"].get("C") == 1
    # C is never scored (frozen); B is unaffected and still perfect
    assert "C" not in gallery["per_persona"]
    assert gallery["per_persona"]["B"] == 1.0


def test_frozen_run_marks_scored_and_frozen():
    out = pm.attribution_accuracy(_abc(), keyed_embed, frozen_personas={"C"})
    assert out["frozen_personas"] == ["C"]
    assert out["scored_personas"] == ["A", "B"]
    # random_baseline counts ALL personas (active + frozen), not just scored ones
    assert out["random_baseline"] == round(1 / 3, 4)


# ---- relaxed cardinality rules for frozen personas ----


def test_frozen_persona_allows_single_response():
    # C frozen with ONE response is fine (a 1-vector centroid is just that vector).
    resp = {"A": ["A0a", "A0b"], "B": ["B90a", "B90b"], "C": ["C20a"]}
    out = pm.attribution_accuracy(resp, keyed_embed, frozen_personas={"C"})
    assert out["scored_personas"] == ["A", "B"]


def test_active_persona_still_requires_two_responses():
    # A is ACTIVE with only one response → still errors even though C is frozen.
    resp = {"A": ["A0a"], "B": ["B90a", "B90b"], "C": ["C20a", "C20b"]}
    with pytest.raises(ValueError, match="<2 responses"):
        pm.attribution_accuracy(resp, keyed_embed, frozen_personas={"C"})


def test_all_frozen_leaves_nothing_to_score():
    resp = {"A": ["A0a", "A0b"], "B": ["B90a", "B90b"]}
    with pytest.raises(ValueError, match="active"):
        pm.attribution_accuracy(resp, keyed_embed, frozen_personas={"A", "B"})


def test_frozen_name_without_responses_is_noop():
    # A frozen persona present in the set but with no responses can't compete.
    resp = {"A": ["A0a", "A0b"], "B": ["B90a", "B90b"], "C": []}
    # C is dropped by the `if r` filter, so it isn't in `personas` at all → this is
    # just a 2-persona active run; freezing a name with no responses is a no-op.
    out = pm.attribution_accuracy(resp, keyed_embed, frozen_personas={"C"})
    assert "C" not in out["per_persona"]
    assert out["random_baseline"] == round(1 / 2, 4)


# ---- frozen_gallery: manifest + staleness ----


def _write_personas(tmp_path, keys):
    for k in keys:
        (tmp_path / f"{k}.json").write_text(f'{{"key": "{k}", "voice": "x"}}', encoding="utf-8")
    return tmp_path


def test_build_manifest_shape(tmp_path):
    _write_personas(tmp_path, ["eeva", "nyx"])
    m = fg.build_manifest(
        ["nyx", "eeva"], embedding_model="bge-m3", companion_model="abl-24b", persona_dir=tmp_path
    )
    assert m["n_personas"] == 2
    assert m["personas"] == ["eeva", "nyx"]  # sorted
    assert m["embedding_model"] == "bge-m3"
    assert m["companion_model"] == "abl-24b"
    assert set(m["persona_def_hashes"]) == {"eeva", "nyx"}
    assert all(isinstance(h, str) for h in m["persona_def_hashes"].values())


def test_persona_def_hash_missing_is_none(tmp_path):
    assert fg.persona_def_hash("ghost", persona_dir=tmp_path) is None


def test_staleness_no_manifest_warns_not_errors():
    cur = fg.build_manifest([], embedding_model="bge-m3", companion_model="a")
    errors, warnings = fg.check_staleness(cur, None, active=set())
    assert errors == []
    assert warnings and "no manifest" in warnings[0]


def test_staleness_clean_when_identical(tmp_path):
    _write_personas(tmp_path, ["eeva", "nyx"])
    m = fg.build_manifest(
        ["eeva", "nyx"], embedding_model="bge-m3", companion_model="a", persona_dir=tmp_path
    )
    errors, warnings = fg.check_staleness(m, m, active={"eeva"})
    assert errors == [] and warnings == []


def test_staleness_embedding_change_is_hard_error():
    gal = fg.build_manifest([], embedding_model="bge-m3", companion_model="a")
    cur = fg.build_manifest([], embedding_model="nomic", companion_model="a")
    errors, _ = fg.check_staleness(cur, gal, active=set())
    assert errors and "embedding model" in errors[0]


def test_staleness_companion_change_is_warning():
    gal = fg.build_manifest([], embedding_model="bge-m3", companion_model="old")
    cur = fg.build_manifest([], embedding_model="bge-m3", companion_model="new")
    errors, warnings = fg.check_staleness(cur, gal, active=set())
    assert errors == []
    assert any("companion model" in w for w in warnings)


def test_staleness_dormant_persona_drift_warns_active_does_not(tmp_path):
    _write_personas(tmp_path, ["eeva", "nyx"])
    gal = fg.build_manifest(
        ["eeva", "nyx"], embedding_model="bge-m3", companion_model="a", persona_dir=tmp_path
    )
    # Change BOTH persona defs after freeze.
    (tmp_path / "eeva.json").write_text('{"key": "eeva", "voice": "CHANGED"}', encoding="utf-8")
    (tmp_path / "nyx.json").write_text('{"key": "nyx", "voice": "CHANGED"}', encoding="utf-8")
    cur = fg.build_manifest(
        ["eeva", "nyx"], embedding_model="bge-m3", companion_model="a", persona_dir=tmp_path
    )
    # eeva is ACTIVE (expected to change → silent); nyx is DORMANT/frozen → warns.
    errors, warnings = fg.check_staleness(cur, gal, active={"eeva"})
    assert errors == []
    assert any("nyx" in w for w in warnings)
    assert not any("eeva" in w for w in warnings)


# ---- frozen_gallery: dormant extraction ----


def _baseline_results():
    return {
        "results": [
            {"persona": "eeva", "category": "distinctiveness", "answer": "e1"},
            {"persona": "eeva", "category": "distinctiveness", "answer": "e2"},
            {"persona": "nyx", "category": "distinctiveness", "answer": "n1"},
            {"persona": "nyx", "category": "distinctiveness", "answer": "n2"},
            {"persona": "nyx", "category": "voice", "answer": "v1"},  # wrong category
            {"persona": "aegis", "category": "distinctiveness", "answer": ""},  # empty
            {"persona": "aegis", "category": "distinctiveness", "answer": "a1"},
        ]
    }


def test_dormant_responses_excludes_active_and_filters_category():
    dormant = fg.dormant_responses(_baseline_results(), active={"eeva"})
    assert set(dormant) == {"nyx", "aegis"}  # eeva excluded (active)
    assert dormant["nyx"] == ["n1", "n2"]  # voice row excluded
    assert dormant["aegis"] == ["a1"]  # empty answer excluded


def test_dormant_responses_excludes_canned_non_voice_sources():
    # A groundedness-gate abstention / error string is a model-independent constant
    # and must NOT become a frozen reference prototype.
    baseline = {
        "results": [
            {
                "persona": "nyx",
                "category": "distinctiveness",
                "answer": "real voice",
                "source": "llm",
            },
            {
                "persona": "nyx",
                "category": "distinctiveness",
                "answer": "I don't have grounded info — want me to search?",
                "source": "groundedness_abstain",
            },
            {
                "persona": "aegis",
                "category": "distinctiveness",
                "answer": "[ERROR: boom]",
                "source": "error",
            },
            {
                "persona": "aegis",
                "category": "distinctiveness",
                "answer": "kept",
                "source": None,
            },  # no source → kept
        ]
    }
    dormant = fg.dormant_responses(baseline, active=set())
    assert dormant["nyx"] == ["real voice"]  # canned abstention dropped
    assert dormant["aegis"] == ["kept"]  # error dropped, source-less kept


def test_dormant_result_rows_marked_gallery():
    dormant = {"nyx": ["n1", "n2"]}
    rows = fg.dormant_result_rows(dormant)
    assert len(rows) == 2
    assert all(r["source"] == "gallery" for r in rows)
    assert all(r["category"] == "distinctiveness" for r in rows)


def test_resolve_baseline_path_passthrough(tmp_path):
    p = tmp_path / "baseline_x.json"
    p.write_text("{}", encoding="utf-8")
    assert fg.resolve_baseline(str(p)) == p


def test_resolve_baseline_unknown_label_raises():
    with pytest.raises(FileNotFoundError):
        fg.resolve_baseline("definitely-not-a-real-label-xyz")


# ---- compute_report frozen pass-through ----


def _rows(persona, answers, category="distinctiveness"):
    return [{"persona": persona, "category": category, "answer": a} for a in answers]


def test_compute_report_frozen_passthrough():
    # A, B active (>=2 each); C frozen (from gallery). Uses keyed geometric embedder.
    results = (
        _rows("A", ["A0a", "A0b", "A15"])
        + _rows("B", ["B90a", "B90b"])
        + _rows("C", ["C20a", "C20b"])
    )
    rep = compute_report(results, keyed_embed, frozen_personas={"C"})
    d = rep["distinctiveness"]
    assert d["frozen_personas"] == ["C"]
    assert set(d["scored_personas"]) == {"A", "B"}
    assert d["random_baseline"] == round(1 / 3, 4)  # chance over all 3


def test_compute_report_no_frozen_is_unchanged():
    results = _rows("A", ["A0a", "A0b"]) + _rows("B", ["B90a", "B90b"])
    rep = compute_report(results, keyed_embed)
    d = rep["distinctiveness"]
    assert "frozen_personas" not in d
    assert d["random_baseline"] == round(1 / 2, 4)


def test_compute_report_error_string_byte_identical_without_frozen():
    # <2 personas → error path. Without a gallery the message must be the ORIGINAL
    # string verbatim (byte-identical claim); the gallery suffix appears only when frozen.
    only_one = _rows("A", ["A0a", "A0b"])
    rep = compute_report(only_one, keyed_embed)
    assert rep["distinctiveness"]["error"] == "need >=2 personas with >=2 distinctiveness responses"
