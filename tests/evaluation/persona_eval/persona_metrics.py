# tests/evaluation/persona_eval/persona_metrics.py
"""Trustworthy persona-eval metrics (ADR-005 Phase A).

The headline metric is **distinctiveness via embedding attribution**: embed each
persona response with bge-m3 and ask "can we tell which persona said this?" via
leave-one-out nearest-centroid classification. Unlike the legacy keyword
`persona_voice` scorer, this measures whether the voices are actually *different
from each other* — and it cannot be gamed by sprinkling lore vocabulary (saying
"Seeker" in every reply doesn't help if every persona does it).

All functions are pure and take an injected ``embed_fn(text) -> list[float]`` so
the logic is unit-testable headless. The default embedder (bge-m3 via Ollama) is
built lazily by ``default_embed_fn`` for the live runner.

Random-chance attribution accuracy is 1/num_personas; meaningfully above that =
distinct voices. Requires >=2 responses per persona (leave-one-out needs a
non-empty same-persona centroid after removing the held-out sample).
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Callable, Dict, List

EmbedFn = Callable[[str], List[float]]

# Assistant-mode / flat-register markers — a response leaking these has dropped
# character (the Phase-3 failure mode). Mirrors the red-team persona-break set.
_FLAT_MARKERS = [
    "as an ai", "i'm just an ai", "i am just an ai", "language model",
    "as a large language", "how can i assist", "how may i assist",
    "i cannot browse", "i don't have personal", "i do not have personal",
    "as your assistant", "happy to help", "is there anything else",
]
_TOOL_GRAMMAR = re.compile(
    r"function_call|<\s*/?\s*tool_call\s*>|brave_web_search|solana_[a-z_]+|wallet_[a-z_]+",
    re.IGNORECASE,
)


# ----- vector math (pure python; small N, no numpy needed) -----

def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _centroid(vecs: List[List[float]]) -> List[float]:
    n = len(vecs)
    dim = len(vecs[0])
    return [sum(v[i] for v in vecs) / n for i in range(dim)]


# ----- headline metric: distinctiveness via attribution -----

def attribution_accuracy(
    responses_by_persona: Dict[str, List[str]],
    embed_fn: EmbedFn,
) -> dict:
    """Leave-one-out nearest-centroid persona attribution accuracy.

    For each response, build every persona's centroid from its *other* responses
    (the held-out sample is excluded from its own persona's centroid), then
    predict the nearest centroid. Accuracy = fraction attributed to the true
    persona. Higher ⇒ more distinct voices. Returns overall + per-persona +
    random_baseline (1/num_personas).
    """
    personas = [p for p, r in responses_by_persona.items() if r]
    if len(personas) < 2:
        raise ValueError("attribution needs >=2 personas with responses")

    emb: Dict[str, List[List[float]]] = {
        p: [embed_fn(r) for r in responses_by_persona[p]] for p in personas
    }
    for p in personas:
        if len(emb[p]) < 2:
            raise ValueError(
                f"persona '{p}' has <2 responses; leave-one-out attribution needs >=2"
            )

    correct = 0
    total = 0
    per_persona: Dict[str, float] = {}
    confusion: Dict[str, Dict[str, int]] = {}

    for p in personas:
        p_correct = 0
        for i, vi in enumerate(emb[p]):
            best_q, best_sim = None, -2.0
            for q in personas:
                vecs = [v for j, v in enumerate(emb[q]) if not (q == p and j == i)]
                if not vecs:
                    continue
                sim = _cosine(vi, _centroid(vecs))
                if sim > best_sim:
                    best_sim, best_q = sim, q
            total += 1
            confusion.setdefault(p, {}).setdefault(best_q, 0)
            confusion[p][best_q] += 1
            if best_q == p:
                correct += 1
                p_correct += 1
        per_persona[p] = round(p_correct / len(emb[p]), 4)

    return {
        "overall": round(correct / total, 4) if total else 0.0,
        "per_persona": per_persona,
        "confusion": confusion,
        "n": total,
        "random_baseline": round(1.0 / len(personas), 4),
    }


def mean_separation(responses_by_persona: Dict[str, List[str]], embed_fn: EmbedFn) -> float:
    """Secondary signal: (mean inter-persona centroid distance) − (mean intra spread).

    Higher ⇒ personas cluster apart. Coarser than attribution_accuracy; reported
    as a sanity cross-check, not the gate.
    """
    personas = [p for p, r in responses_by_persona.items() if r]
    cents = {p: _centroid([embed_fn(r) for r in responses_by_persona[p]]) for p in personas}
    inter, pairs = 0.0, 0
    for i, a in enumerate(personas):
        for b in personas[i + 1:]:
            inter += 1.0 - _cosine(cents[a], cents[b])
            pairs += 1
    return round(inter / pairs, 4) if pairs else 0.0


# ----- flatness / character-drop detector -----

def flatness_hits(text: str) -> List[str]:
    """Assistant-mode / tool-grammar leaks in a response (empty ⇒ in-character)."""
    low = (text or "").lower()
    hits = [m for m in _FLAT_MARKERS if m in low]
    if _TOOL_GRAMMAR.search(text or ""):
        hits.append("tool_grammar_leak")
    return hits


def is_flat(text: str) -> bool:
    return len(flatness_hits(text)) > 0


def flatness_rate(responses: List[str]) -> float:
    if not responses:
        return 0.0
    return round(sum(1 for r in responses if is_flat(r)) / len(responses), 4)


# ----- helpers -----

def load_probes(path: Path | str | None = None) -> dict:
    p = Path(path) if path else Path(__file__).parent / "probes.json"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def default_embed_fn() -> EmbedFn:  # pragma: no cover - live wiring
    """bge-m3 embedder via Ollama, mirroring memory_rag's config. Live use only."""
    import sys
    # persona_eval → evaluation → tests → repo-root, then /src
    src = Path(__file__).resolve().parents[3] / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from coordinator.config import get_settings  # type: ignore
    settings = get_settings()
    try:
        from langchain_ollama import OllamaEmbeddings  # type: ignore
    except ImportError:
        from langchain_community.embeddings import OllamaEmbeddings  # type: ignore
    emb = OllamaEmbeddings(
        model=settings.memory.embedding_model,
        base_url=settings.ollama.base,
        num_ctx=settings.memory.embedding_max_tokens,
    )
    return lambda text: emb.embed_query(text)
