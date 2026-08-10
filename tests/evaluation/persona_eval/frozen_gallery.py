"""Frozen reference gallery for the persona-eval distinctiveness metric.

Attribution accuracy is a discrimination-against-the-others metric (chance 1/N),
so re-probing only a subset of personas against a *shrunken* label space silently
inflates their scores. The frozen gallery avoids that: it loads the DORMANT
personas' responses from an existing baseline, re-embeds them as fixed reference
prototypes (via ``attribution_accuracy(..., frozen_personas=...)``), and re-probes
only the ACTIVE personas against the full N-centroid field — chance stays 1/N and
the confusable dormant neighbours stay live competitors.

This is closed-set identification against a fixed gallery / a frozen-prototype
NCM classifier. It is valid ONLY while the dormant personas' voices are unchanged
— so every gallery carries a **manifest** (embedding model, companion model,
prompt-builder version, per-persona definition hashes) and a staleness check
refuses on an embedding-model change (frozen vectors would live in a different
space) and warns on dormant-persona / model drift. See the README + the
compare_baselines commensurability guard.

Pure functions are unit-tested headless; ``default_manifest`` (live coordinator
settings) is the only live-wiring bit.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

_PERSONA_DIR = Path(__file__).resolve().parents[3] / "personas"
_BASELINE_DIR = Path(__file__).parent / "baselines"

# Bump when the prompt builder changes in a way that moves persona voices, so a
# gallery frozen under the old builder is flagged stale.
PROMPT_BUILDER_VERSION = "lean-v1"


# ----- hashing / manifest (pure) -----


def _sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def persona_def_hash(persona_key: str, persona_dir: Optional[Path] = None) -> Optional[str]:
    """Short content hash of a persona's JSON definition, or None if absent."""
    f = (persona_dir or _PERSONA_DIR) / f"{persona_key}.json"
    if not f.exists():
        return None
    return _sha16(f.read_text(encoding="utf-8"))


def build_manifest(
    personas: List[str],
    *,
    embedding_model: str,
    companion_model: str,
    persona_dir: Optional[Path] = None,
    prompt_builder_version: str = PROMPT_BUILDER_VERSION,
) -> dict:
    """Content-addressed record of everything the frozen centroids depend on.

    Checked before a gallery is trusted (see ``check_staleness``): an artifact is
    only comparable to a later run when these inputs still match.
    """
    ps = sorted(personas)
    return {
        "n_personas": len(ps),
        "personas": ps,
        "embedding_model": embedding_model,
        "companion_model": companion_model,
        "prompt_builder_version": prompt_builder_version,
        "persona_def_hashes": {p: persona_def_hash(p, persona_dir) for p in ps},
    }


def check_staleness(
    current: dict, gallery: Optional[dict], active: Set[str]
) -> Tuple[List[str], List[str]]:
    """Compare a current manifest against a gallery's frozen manifest.

    Returns ``(errors, warnings)``. Errors are hard-stop (the comparison would be
    meaningless); warnings are advisory. Only DORMANT (frozen) personas matter for
    drift — active personas are *expected* to change, that's the point of re-probing
    them. A missing gallery manifest is a warning, not a silent pass.
    """
    if not gallery:
        return [], [
            "gallery has no manifest — cannot verify it is not stale "
            "(frozen before manifests existed?); results may not be comparable"
        ]

    errors: List[str] = []
    warnings: List[str] = []

    # Embedding model defines the vector SPACE. A change makes frozen vectors and
    # freshly-embedded ones incomparable → hard stop.
    if current.get("embedding_model") != gallery.get("embedding_model"):
        errors.append(
            f"embedding model changed {gallery.get('embedding_model')!r} -> "
            f"{current.get('embedding_model')!r}: frozen centroids live in a "
            "different vector space; re-freeze the gallery"
        )

    # Companion model / prompt builder define the VOICE. A change may have drifted
    # the dormant personas away from their frozen centroids → advisory.
    if current.get("companion_model") != gallery.get("companion_model"):
        warnings.append(
            f"companion model changed {gallery.get('companion_model')!r} -> "
            f"{current.get('companion_model')!r}: dormant personas' voices may "
            "have drifted from their frozen centroids"
        )
    if current.get("prompt_builder_version") != gallery.get("prompt_builder_version"):
        warnings.append(
            "prompt builder version changed since the gallery was frozen: dormant "
            "voices may have drifted"
        )

    # Per-dormant-persona definition drift.
    gh = gallery.get("persona_def_hashes", {})
    ch = current.get("persona_def_hashes", {})
    for p in sorted(set(gh) - active):
        if p in ch and ch[p] != gh[p]:
            warnings.append(
                f"frozen persona '{p}' definition changed since freeze: its centroid may be stale"
            )
    return errors, warnings


# ----- baseline / gallery loading (pure given a path) -----


def resolve_baseline(label_or_path: str) -> Path:
    """Resolve a baseline label ('abliterated') to its newest file, or a path."""
    p = Path(label_or_path)
    if p.exists():
        return p
    matches = sorted(_BASELINE_DIR.glob(f"baseline_{label_or_path}_*.json"))
    if not matches:
        raise FileNotFoundError(
            f"no baseline for label {label_or_path!r} under {_BASELINE_DIR} (and not a path)"
        )
    return matches[-1]


def load_baseline(label_or_path: str) -> dict:
    with open(resolve_baseline(label_or_path), encoding="utf-8") as f:
        return json.load(f)


# Sources that are NOT genuine model voice — a canned/abstention/error string
# (e.g. the ADR-007 groundedness gate returns a fixed "want me to search?" line
# with source "groundedness_abstain"). Freezing one as a reference prototype would
# build the centroid partly from a model-INDEPENDENT constant, making personas look
# artificially identical across models. Excluded from the gallery by default.
# NOTE: "gallery" is deliberately NOT here — a row re-served from an earlier gallery
# is still genuine voice text, so a gallery-produced baseline can be reused as a
# gallery source without its dormant personas silently vanishing.
NON_VOICE_SOURCES = frozenset({"groundedness_abstain", "error"})


def dormant_responses(
    baseline: dict,
    active: Set[str],
    category: str = "distinctiveness",
    exclude_sources: frozenset[str] | set[str] = NON_VOICE_SOURCES,
) -> Dict[str, List[str]]:
    """Extract genuine-voice text for personas NOT in ``active`` — the frozen gallery.

    These become fixed reference prototypes. Only the requested category
    (distinctiveness by default) is used, matching what attribution scores over.
    Rows whose ``source`` is in ``exclude_sources`` are skipped: a canned
    abstention/error string is a model-independent constant and would pollute the
    frozen centroid with non-voice text. Rows with no ``source`` field are kept
    (older baselines predate the field).
    """
    out: Dict[str, List[str]] = {}
    for r in baseline.get("results", []):
        if r.get("category") != category or not r.get("answer"):
            continue
        if r.get("source") in exclude_sources:
            continue
        p = r.get("persona")
        if p and p not in active:
            out.setdefault(p, []).append(r["answer"])
    return out


def dormant_result_rows(
    dormant: Dict[str, List[str]], category: str = "distinctiveness"
) -> List[dict]:
    """Synthesize result rows for gallery-sourced dormant responses so they flow
    through ``compute_report`` alongside freshly-collected active rows. Marked
    ``source: "gallery"`` so a reader can tell them from live generations.
    """
    rows: List[dict] = []
    for persona, texts in dormant.items():
        for i, text in enumerate(texts):
            rows.append(
                {
                    "persona": persona,
                    "category": category,
                    "probe_id": f"gallery-{i}",
                    "prompt": "",
                    "answer": text,
                    "source": "gallery",
                    "elapsed": 0.0,
                }
            )
    return rows


def default_manifest(
    personas: List[str], persona_dir: Optional[Path] = None
) -> dict:  # pragma: no cover - live wiring
    """Build a manifest from live coordinator settings (embedding + companion model)."""
    import sys

    src = Path(__file__).resolve().parents[3] / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from coordinator.config import get_settings  # type: ignore

    s = get_settings()
    return build_manifest(
        personas,
        embedding_model=s.memory.embedding_model,
        companion_model=s.ollama.model,
        persona_dir=persona_dir,
    )
