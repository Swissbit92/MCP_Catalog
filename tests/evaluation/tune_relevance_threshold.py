# tests/evaluation/tune_relevance_threshold.py
"""Threshold sweep for the search relevance gate (SearchRelevanceService).

Picks a candidate value for SEARCH_RELEVANCE_MIN_COSINE by sweeping
relevance_gate_eval_set.json and selecting the config that pins the
FALSE-ABSTENTION RATE low first (on samples labeled "relevant" — abstaining on
a genuinely-relevant, answerable result set is the user-visible cost the
gate's own docstring calls out as the risk to avoid), then maximizes junk-catch
recall (on samples labeled "off_topic") among thresholds that clear the
false-abstention bar.

This is the INVERSE priority order from tune_routing_threshold.py, where wallet
false-positives (a live tool action) were the costly class pinned first. Here,
the gate has no destructive side effect — its only failure mode is an honest
"I don't know" where a real answer existed, so false-abstention is the
costly class.

Efficiency: each query/result pair is embedded ONCE; every threshold in the
sweep grid is then evaluated in pure Python from the cached best-cosine score.

Usage:
    # Standalone full sweep (needs Ollama + bge-m3):
    .venv/bin/python tests/evaluation/tune_relevance_threshold.py

    # Via pytest (slow sweep auto-skips when Ollama is unreachable):
    .venv/bin/python -m pytest tests/evaluation/tune_relevance_threshold.py -v -s
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

import pytest

from src.coordinator.services.search_relevance_service import SearchRelevanceService

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

EVAL_SET_PATH = Path(__file__).parent / "relevance_gate_eval_set.json"
RESULTS_PATH = Path(__file__).parent / "relevance_tuning_results.json"

# Sweep grid. bge-m3 cosine floor for unrelated pairs is ~0.60 on the routing
# eval (see tune_routing_threshold.py), but relevance-gate pairs are
# short title+description snippets rather than the router's curated intent
# examples, so scores run lower on average — sweep a wider, lower range.
THRESHOLDS = [round(0.20 + 0.02 * i, 2) for i in range(26)]  # 0.20 .. 0.70

# False-abstention rate ceiling: the fraction of "relevant" samples the gate
# is allowed to wrongly abstain on, at the chosen threshold. Mirrors how
# tune_routing_threshold.py pins wallet precision=1.0 as its hard constraint —
# here the hard constraint is on the OTHER class (relevant, not off_topic),
# reflecting the inverted risk (no destructive action, just an honest "I don't
# know" that costs a real answer).
MAX_FALSE_ABSTENTION_RATE = 0.10


@dataclass
class RelevanceResult:
    threshold: float
    n_samples: int
    n_relevant: int
    n_off_topic: int
    false_abstention_rate: float  # relevant samples wrongly gated as off_topic
    junk_catch_recall: float  # off_topic samples correctly gated
    accuracy: float
    embed_p50_ms: float = 0.0
    embed_p95_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RelevanceThresholdTuner:
    """Embed-once, sweep-many tuner for the relevance gate's cosine floor."""

    def __init__(self, eval_path: Path = EVAL_SET_PATH) -> None:
        self.eval_path = eval_path
        self.samples: List[Dict[str, Any]] = []
        self._best_cosines: List[Optional[float]] = []
        self._golds: List[str] = []
        self._embed_latencies_ms: List[float] = []

    def load(self) -> None:
        with open(self.eval_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.samples = data["samples"]
        logger.info(f"Loaded {len(self.samples)} eval samples from {self.eval_path.name}")

    def precompute_scores(self) -> None:
        """Compute best cosine per sample once; sweep grid reuses these."""
        gate = SearchRelevanceService()
        # Force embedder construction now so a missing Ollama/bge-m3 fails
        # loudly here, not silently mid-loop.
        gate._get_embedder()

        self._best_cosines = []
        self._golds = []
        self._embed_latencies_ms = []
        for s in self.samples:
            results = [SimpleNamespace(title=r["title"], description=r["description"]) for r in s["results"]]
            t0 = time.perf_counter()
            best = gate.max_similarity(s["query"], results)
            self._embed_latencies_ms.append((time.perf_counter() - t0) * 1000.0)
            self._best_cosines.append(best)
            self._golds.append(s["expected_verdict"])

        logger.info(f"Embedded {len(self._golds)} query/result pairs")

    def _latency_percentiles(self) -> Tuple[float, float]:
        if not self._embed_latencies_ms:
            return 0.0, 0.0
        s = sorted(self._embed_latencies_ms)
        p50 = s[int(0.50 * (len(s) - 1))]
        p95 = s[int(0.95 * (len(s) - 1))]
        return round(p50, 1), round(p95, 1)

    def evaluate(self, threshold: float) -> RelevanceResult:
        n_relevant = sum(1 for g in self._golds if g == "relevant")
        n_off_topic = sum(1 for g in self._golds if g == "off_topic")

        false_abstentions = 0  # relevant, but best_cosine < threshold
        junk_caught = 0  # off_topic, and best_cosine < threshold
        correct = 0

        for best, gold in zip(self._best_cosines, self._golds):
            # None (no embeddable results) fails open -> treated as "relevant"
            # (never gates), matching SearchRelevanceService.is_relevant's own
            # fail-open contract.
            predicted = "off_topic" if (best is not None and best < threshold) else "relevant"
            if predicted == gold:
                correct += 1
            if gold == "relevant" and predicted == "off_topic":
                false_abstentions += 1
            if gold == "off_topic" and predicted == "off_topic":
                junk_caught += 1

        p50, p95 = self._latency_percentiles()
        return RelevanceResult(
            threshold=threshold,
            n_samples=len(self._golds),
            n_relevant=n_relevant,
            n_off_topic=n_off_topic,
            false_abstention_rate=round(false_abstentions / n_relevant, 3) if n_relevant else 0.0,
            junk_catch_recall=round(junk_caught / n_off_topic, 3) if n_off_topic else 0.0,
            accuracy=round(correct / len(self._golds), 3) if self._golds else 0.0,
            embed_p50_ms=p50,
            embed_p95_ms=p95,
        )

    def sweep(self) -> List[RelevanceResult]:
        return [self.evaluate(t) for t in THRESHOLDS]

    def recommend(self, results: List[RelevanceResult]) -> Optional[RelevanceResult]:
        """Pin false-abstention-rate <= MAX_FALSE_ABSTENTION_RATE first, then
        maximize junk-catch recall among the survivors. Returns None if no
        threshold clears the false-abstention bar at all."""
        eligible = [r for r in results if r.false_abstention_rate <= MAX_FALSE_ABSTENTION_RATE]
        if not eligible:
            return None
        return max(eligible, key=lambda r: (r.junk_catch_recall, -r.threshold))


def _run_and_save() -> Tuple[List[RelevanceResult], Optional[RelevanceResult]]:
    tuner = RelevanceThresholdTuner()
    tuner.load()
    tuner.precompute_scores()
    results = tuner.sweep()
    best = tuner.recommend(results)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "eval_set": EVAL_SET_PATH.name,
        "max_false_abstention_rate_constraint": MAX_FALSE_ABSTENTION_RATE,
        "sweep": [r.to_dict() for r in results],
        "recommendation": best.to_dict() if best else None,
    }
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    logger.info(f"Saved sweep results → {RESULTS_PATH}")
    return results, best


def main() -> None:
    results, best = _run_and_save()
    for r in results:
        logger.info(
            f"thr={r.threshold:.2f} | acc={r.accuracy:.3f} | "
            f"false_abstention={r.false_abstention_rate:.3f} | "
            f"junk_catch_recall={r.junk_catch_recall:.3f}"
        )
    print("\n" + "=" * 70)
    if best is None:
        print(
            f"NO THRESHOLD clears the false-abstention constraint "
            f"(<= {MAX_FALSE_ABSTENTION_RATE:.0%}). RECOMMENDATION: keep "
            f"SEARCH_RELEVANCE_GATE_ENABLED=false — do not enable on this eval set."
        )
    else:
        print(
            f"RECOMMENDED: SEARCH_RELEVANCE_MIN_COSINE={best.threshold:.2f}\n"
            f"  false_abstention_rate={best.false_abstention_rate:.3f} "
            f"(constraint <= {MAX_FALSE_ABSTENTION_RATE:.0%})\n"
            f"  junk_catch_recall={best.junk_catch_recall:.3f}  accuracy={best.accuracy:.3f}\n"
            f"  embed latency p50={best.embed_p50_ms}ms p95={best.embed_p95_ms}ms"
        )
    print("=" * 70)


@pytest.mark.requires_ollama
def test_relevance_threshold_sweep_runs_and_recommends():
    """Slow live sweep — auto-skips headless (requires_ollama marker)."""
    results, best = _run_and_save()
    assert len(results) == len(THRESHOLDS)
    # Not asserting a specific recommendation value here (that's a human
    # decision recorded in the ADR/config docstring once reviewed) — this
    # test only guards that the sweep mechanism itself runs end-to-end.


if __name__ == "__main__":
    main()
