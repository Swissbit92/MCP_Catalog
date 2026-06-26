# tests/evaluation/eval_lore_retrieval.py
"""Golden-set evaluation for the on-demand lore retrieval (Phase-2).

Measures precision/recall of the bge-m3 semantic tier (search_lore) against a
hand-labelled golden set, and sweeps the relevance threshold. The headless
schema test always runs; the live metric test needs Ollama + bge-m3.

Usage:
    .venv/bin/python tests/evaluation/eval_lore_retrieval.py            # live sweep
    .venv/bin/python -m pytest tests/evaluation/eval_lore_retrieval.py  # gated
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List

import pytest

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# (query, set of acceptable canon entity_ids — retrieval should surface >=1)
GOLDEN_CASES: List[Dict] = [
    {"query": "what is resonance and the hum I feel", "expected": ["concept-resonance"]},
    {"query": "tell me about ascension and rising through the ranks", "expected": ["concept-ascension"]},
    {"query": "where is the central nexus", "expected": ["location-central-nexus"]},
    {"query": "describe the neon labyrinth", "expected": ["location-neon-labyrinth"]},
    {"query": "the bastion of order and its walls", "expected": ["location-bastion-of-order"]},
    {"query": "the sanctuary of stillness and quiet", "expected": ["location-sanctuary-of-stillness"]},
    {"query": "the archive of infinite knowledge", "expected": ["location-archive-infinite"]},
    {"query": "the horizon spire reaching upward", "expected": ["location-horizon-spire"]},
    {"query": "house of the crown and sovereignty", "expected": ["house-crown"]},
    {"query": "the veil and hidden things", "expected": ["house-veil"]},
    {"query": "the rank of an initiate just beginning", "expected": ["rank-initiate"]},
    {"query": "becoming an adept of real skill", "expected": ["rank-adept", "rank-acolyte"]},
    {"query": "the highest rank of nephilim", "expected": ["rank-nephilim"]},
    {"query": "tell me about eeva the guide", "expected": ["persona-eeva"]},
    {"query": "who is nyx of the veil", "expected": ["persona-nyx"]},
    {"query": "solace and comfort", "expected": ["persona-solace"]},
    {"query": "the house of order and discipline aegis", "expected": ["house-bastion", "persona-aegis"]},
    {"query": "the ember and warmth", "expected": ["house-ember"]},
]


@dataclass
class EvalResult:
    threshold: float
    k: int
    precision: float
    recall: float
    f1: float
    hits: int
    total: int


def run_eval(rag, threshold: float = 0.5, k: int = 5) -> EvalResult:
    """Recall = fraction of cases where >=1 expected id is in top-k; precision =
    fraction of returned entities that were expected (per case, averaged)."""
    hits = 0
    precisions = []
    for case in GOLDEN_CASES:
        res = rag.search_lore(case["query"], k=k, min_relevance=threshold, canon_only=True)
        got = [m["entity_id"] for m, _ in res]
        expected = set(case["expected"])
        if expected & set(got):
            hits += 1
        if got:
            precisions.append(len(expected & set(got)) / len(got))
        else:
            precisions.append(0.0)
    recall = hits / len(GOLDEN_CASES)
    precision = sum(precisions) / len(precisions)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return EvalResult(threshold, k, round(precision, 3), round(recall, 3), round(f1, 3), hits, len(GOLDEN_CASES))


def sweep(rag) -> List[EvalResult]:
    out = []
    for thr in [0.40, 0.45, 0.50, 0.55, 0.60]:
        r = run_eval(rag, threshold=thr, k=5)
        out.append(r)
        logger.info(f"thr={thr:.2f} k=5 | P={r.precision:.3f} R={r.recall:.3f} "
                    f"F1={r.f1:.3f} ({r.hits}/{r.total})")
    return out


class TestLoreEval:
    def test_golden_set_schema(self):
        assert len(GOLDEN_CASES) >= 15
        for c in GOLDEN_CASES:
            assert c["query"].strip() and c["expected"]

    @pytest.mark.slow
    @pytest.mark.requires_ollama
    def test_live_recall(self):
        from src.coordinator.memory_rag import EpisodicMemoryRAG
        rag = EpisodicMemoryRAG()
        rag.index_lore_corpus()
        r = run_eval(rag, threshold=0.45, k=5)
        logger.info(f"Lore retrieval recall={r.recall:.3f} precision={r.precision:.3f}")
        assert r.recall >= 0.70, f"recall {r.recall} below 0.70 on golden set"


if __name__ == "__main__":
    from src.coordinator.memory_rag import EpisodicMemoryRAG
    _rag = EpisodicMemoryRAG()
    _rag.index_lore_corpus()
    best = max(sweep(_rag), key=lambda r: r.f1)
    print(f"\nBest: thr={best.threshold} F1={best.f1} (P={best.precision} R={best.recall})")
