# tests/evaluation/tune_routing_threshold.py
"""Threshold/margin sweep for the bge-m3 semantic-PRIMARY intent router.

Picks the shipping value for ROUTING_SEMANTIC_THRESHOLD / ROUTING_SEMANTIC_MARGIN
by sweeping a labelled eval set (routing_eval_set.json) and selecting the config
that pins precision=1.0 on the costly classes (wallet first, then web_search) and
then maximises accuracy. A wallet false-positive can touch a live wallet tool, so
wallet precision is the dominant constraint.

Efficiency: each query is embedded ONCE against the primary centroids; every
(threshold, margin) combo is then evaluated in pure Python from the cached scores.
This mirrors route_by_embedding's availability-filter + rank + threshold + margin
logic exactly (see _decide()), so results transfer to production.

Usage:
    # Standalone full sweep (needs Ollama + bge-m3):
    .venv/bin/python tests/evaluation/tune_routing_threshold.py

    # Via pytest (slow sweep auto-skips when Ollama is unreachable):
    .venv/bin/python -m pytest tests/evaluation/tune_routing_threshold.py -v -s
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

import src.coordinator.tools.semantic_router as sr

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

EVAL_SET_PATH = Path(__file__).parent / "routing_eval_set.json"
RESULTS_PATH = Path(__file__).parent / "routing_tuning_results.json"

# Sweep grid. bge-m3 cosine floor for unrelated pairs is ~0.60, so sweep from
# there up to 0.88. (The classic "anchor 0.80" rule over-restricts for our
# centroid setup — the data, not the rule, picks the value.)
THRESHOLDS = [round(0.60 + 0.01 * i, 2) for i in range(29)]  # 0.60 .. 0.88
MARGINS = [0.0, 0.02, 0.04, 0.06, 0.08, 0.10]

COSTLY = ("wallet", "web_search")


# ---------------------------------------------------------------------------
# Availability + decision logic — mirrors semantic_router.route_by_embedding
# ---------------------------------------------------------------------------
def _availability(sample: Dict[str, Any]) -> Tuple[bool, bool]:
    """Derive (can_use_brave, can_use_wallet) exactly as classify_query_intent does."""
    mcp_access = sample.get("mcp_access")
    can_use_wallet = "solana_wallet" in (mcp_access or [])
    if mcp_access is not None:
        can_use_brave = "brave_search" in mcp_access
    else:
        can_use_brave = str(sample.get("persona_rarity", "")).lower() in {"rare", "epic", "legendary"}
    return can_use_brave, can_use_wallet


def _decide(
    ranked: List[Tuple[float, str]], threshold: float, margin: float
) -> str:
    """Apply threshold + margin gate to pre-ranked (score, intent) pairs.

    Returns the predicted intent label, or "neither" on fall-through. Mirrors the
    primary path: centroids exclude llm_only, so any below-threshold/margin result
    falls through to neither.
    """
    if not ranked:
        return "neither"
    best_score, best_intent = ranked[0]
    if best_score < threshold:
        return "neither"
    if margin > 0.0 and len(ranked) >= 2:
        if (ranked[0][0] - ranked[1][0]) < margin:
            return "neither"
    return best_intent


@dataclass
class RoutingConfig:
    threshold: float
    margin: float

    def __str__(self) -> str:
        return f"threshold={self.threshold:.2f}, margin={self.margin:.2f}"


@dataclass
class RoutingResult:
    config: RoutingConfig
    accuracy: float
    precision_wallet: float
    recall_wallet: float
    precision_web: float
    recall_web: float
    wallet_false_positives: int
    silent_neither_rate: float  # frac of costly-intent samples predicted "neither"
    n_samples: int
    embed_p50_ms: float = 0.0
    embed_p95_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["config"] = asdict(self.config)
        return d


def _score_label(preds: List[str], golds: List[str], label: str) -> Tuple[float, float]:
    tp = sum(1 for p, g in zip(preds, golds) if p == label and g == label)
    fp = sum(1 for p, g in zip(preds, golds) if p == label and g != label)
    fn = sum(1 for p, g in zip(preds, golds) if p != label and g == label)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    return precision, recall


class RoutingThresholdTuner:
    """Embed-once, sweep-many tuner for the semantic-primary router."""

    def __init__(self, eval_path: Path = EVAL_SET_PATH) -> None:
        self.eval_path = eval_path
        self.samples: List[Dict[str, Any]] = []
        # Per-sample cached ranked (score, intent) pairs against primary centroids.
        self._ranked: List[List[Tuple[float, str]]] = []
        self._golds: List[str] = []
        self._embed_latencies_ms: List[float] = []

    def load(self) -> None:
        with open(self.eval_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.samples = data["samples"]
        logger.info(f"Loaded {len(self.samples)} eval samples from {self.eval_path.name}")

    def precompute_scores(self) -> None:
        """Embed each query once; cache availability-filtered ranked scores.

        Mirrors production's PRIMARY scoring exactly: max cosine over each intent's
        example vectors (nearest-example), not cosine to a mean centroid.
        """
        emb_model = sr._get_embeddings_model()
        if emb_model is None:
            raise RuntimeError("Embedding model unavailable — is Ollama running with bge-m3?")
        vecs = sr._ensure_example_vecs_primary(emb_model)
        if not vecs:
            raise RuntimeError("Primary example vectors could not be built.")

        # HELD-OUT: exclude samples whose query is an exact primary example phrase —
        # they score 1.0 by construction and would inflate accuracy (train/test leak).
        example_phrases = {
            p.strip().lower() for phrases in sr._INTENT_EXAMPLES_PRIMARY.values() for p in phrases
        }

        self._ranked = []
        self._golds = []
        self._embed_latencies_ms = []
        leaked = 0
        for s in self.samples:
            if s["query"].strip().lower() in example_phrases:
                leaked += 1
                continue
            self._golds.append(s["expected_intent"])
            can_brave, can_wallet = _availability(s)

            t0 = time.perf_counter()
            query_vec = emb_model.embed_query(s["query"])
            self._embed_latencies_ms.append((time.perf_counter() - t0) * 1000.0)

            usable: List[str] = []
            if can_wallet and "wallet" in vecs:
                usable.append("wallet")
            if can_brave and "web_search" in vecs:
                usable.append("web_search")

            ranked = sorted(
                ((max(sr._cosine_similarity(query_vec, e) for e in vecs[intent]), intent)
                 for intent in usable),
                reverse=True,
            )
            self._ranked.append(ranked)

        logger.info(
            f"Held-out eval: excluded {leaked} exact-example-phrase samples (leakage); "
            f"{len(self._golds)} held-out samples remain"
        )

    def _latency_percentiles(self) -> Tuple[float, float]:
        if not self._embed_latencies_ms:
            return 0.0, 0.0
        s = sorted(self._embed_latencies_ms)
        p50 = s[int(0.50 * (len(s) - 1))]
        p95 = s[int(0.95 * (len(s) - 1))]
        return round(p50, 1), round(p95, 1)

    def evaluate(self, cfg: RoutingConfig) -> RoutingResult:
        preds = [_decide(r, cfg.threshold, cfg.margin) for r in self._ranked]
        golds = self._golds
        n = len(golds)
        accuracy = sum(1 for p, g in zip(preds, golds) if p == g) / n if n else 0.0
        p_wallet, r_wallet = _score_label(preds, golds, "wallet")
        p_web, r_web = _score_label(preds, golds, "web_search")
        wallet_fp = sum(1 for p, g in zip(preds, golds) if p == "wallet" and g != "wallet")
        costly_total = sum(1 for g in golds if g in COSTLY)
        silent = sum(1 for p, g in zip(preds, golds) if g in COSTLY and p == "neither")
        silent_rate = silent / costly_total if costly_total else 0.0
        p50, p95 = self._latency_percentiles()
        return RoutingResult(
            config=cfg,
            accuracy=round(accuracy, 4),
            precision_wallet=round(p_wallet, 4),
            recall_wallet=round(r_wallet, 4),
            precision_web=round(p_web, 4),
            recall_web=round(r_web, 4),
            wallet_false_positives=wallet_fp,
            silent_neither_rate=round(silent_rate, 4),
            n_samples=n,
            embed_p50_ms=p50,
            embed_p95_ms=p95,
        )

    def grid_search(
        self, thresholds: List[float] = THRESHOLDS, margins: List[float] = MARGINS
    ) -> Tuple[RoutingResult, List[RoutingResult]]:
        results: List[RoutingResult] = []
        total = len(thresholds) * len(margins)
        n = 0
        for t in thresholds:
            for m in margins:
                n += 1
                res = self.evaluate(RoutingConfig(threshold=t, margin=m))
                results.append(res)
                logger.info(
                    f"[{n}/{total}] thr={t:.2f} margin={m:.2f} | "
                    f"acc={res.accuracy:.3f} | P_wallet={res.precision_wallet:.3f} "
                    f"R_wallet={res.recall_wallet:.3f} | P_web={res.precision_web:.3f} "
                    f"R_web={res.recall_web:.3f} | wallet_FP={res.wallet_false_positives} "
                    f"silent={res.silent_neither_rate:.3f}"
                )
        best = self._select_best(results)
        logger.info(
            f"\nNEW BEST: {best.config} | acc={best.accuracy:.3f} "
            f"P_wallet={best.precision_wallet:.3f} P_web={best.precision_web:.3f} "
            f"silent={best.silent_neither_rate:.3f}"
        )
        return best, results

    @staticmethod
    def _select_best(results: List[RoutingResult]) -> RoutingResult:
        """Select the shipping config.

        Wallet precision==1.0 is the ONLY hard gate — a wallet false-positive can
        touch a live wallet tool. A web false-positive is cheap (a wasted search),
        so web precision is only a soft tie-break, NOT a gate (gating it sacrifices
        accuracy and recall for no real safety gain). Among zero-wallet-FP configs:
        maximise accuracy, then prefer fewer silent misses, then HIGHER threshold
        (more robust against future query drift), then higher web precision.
        """

        def key(r: RoutingResult) -> Tuple:
            return (
                r.precision_wallet >= 1.0,      # hard gate: no wallet false-positives
                round(r.accuracy, 4),           # maximise accuracy
                -r.silent_neither_rate,         # minimise silent misses
                r.config.threshold,             # prefer higher threshold (robustness)
                r.precision_web,                # soft tie-break: fewer wasted searches
            )

        return sorted(results, key=key, reverse=True)[0]

    def save_results(self, best: RoutingResult, all_results: List[RoutingResult],
                     path: Path = RESULTS_PATH) -> None:
        payload = {
            "tuning_date": datetime.now(timezone.utc).isoformat(),
            "eval_set": self.eval_path.name,
            "n_samples": len(self.samples),
            "embedder": "bge-m3 (primary centroids, no llm_only)",
            "grid": {"thresholds": THRESHOLDS, "margins": MARGINS},
            "best_config": best.to_dict(),
            "all_results": [r.to_dict() for r in all_results],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        logger.info(f"Saved sweep results → {path}")


# ---------------------------------------------------------------------------
# Pytest integration
# ---------------------------------------------------------------------------
class TestRoutingEvalSet:
    def test_eval_set_schema(self) -> None:
        """Fast, headless: validate routing_eval_set.json structure + labels."""
        with open(EVAL_SET_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "samples" in data and isinstance(data["samples"], list)
        assert len(data["samples"]) >= 100, "Need >=100 labelled samples for trustworthy calibration"
        valid = {"wallet", "web_search", "neither"}
        for s in data["samples"]:
            assert s["expected_intent"] in valid, f"bad label: {s}"
            assert "query" in s and s["query"].strip()
            assert "mcp_access" in s  # may be null or list
        borderline = sum(1 for s in data["samples"] if s.get("is_borderline"))
        assert borderline >= 15, "Want >=15 borderline samples to stress threshold selection"

    @pytest.mark.slow
    @pytest.mark.requires_ollama
    def test_full_sweep(self) -> None:
        """Run the full sweep against live bge-m3 and assert a viable config exists."""
        tuner = RoutingThresholdTuner()
        tuner.load()
        tuner.precompute_scores()
        best, all_results = tuner.grid_search()
        tuner.save_results(best, all_results)
        # A usable shipping config must exist: zero wallet false-positives and
        # meaningfully better-than-trivial accuracy.
        assert best.precision_wallet >= 1.0, "No zero-wallet-FP config found — investigate centroids"
        assert best.accuracy >= 0.70, f"Best accuracy {best.accuracy} too low to ship"


if __name__ == "__main__":
    tuner = RoutingThresholdTuner()
    tuner.load()
    tuner.precompute_scores()
    best, all_results = tuner.grid_search()
    tuner.save_results(best, all_results)
    p50, p95 = tuner._latency_percentiles()
    print("\n" + "=" * 70)
    print(f"RECOMMENDED: ROUTING_SEMANTIC_THRESHOLD={best.config.threshold:.2f} "
          f"ROUTING_SEMANTIC_MARGIN={best.config.margin:.2f}")
    print(f"  accuracy={best.accuracy:.3f}  P_wallet={best.precision_wallet:.3f}  "
          f"P_web={best.precision_web:.3f}  silent_neither={best.silent_neither_rate:.3f}")
    print(f"  embed latency p50={p50}ms p95={p95}ms (budget <150ms p95)")
    print("=" * 70)
