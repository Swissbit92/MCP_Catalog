# tests/evaluation/persona_eval/run_eval.py
"""Persona-eval runner + baseline freeze (ADR-005 Phase A).

Drives the live backend to collect each persona's responses to the probe set,
computes the trustworthy metrics (distinctiveness attribution + flatness), and
writes a timestamped baseline under ``baselines/``. This is the ADR-005
acceptance-gate step 1: *freeze a per-persona legacy baseline first.*

The metric computation (``compute_report``) is pure and unit-tested headless; the
live collection (``collect_live``) is a thin shell requiring Ollama + the
backend.

CLI:
  python tests/evaluation/persona_eval/run_eval.py --label legacy
  python tests/evaluation/persona_eval/run_eval.py --label lean-candidate
Then compare two baselines, or feed paired responses into ab_harness.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable, Dict, List

import persona_metrics as pm

_BASELINE_DIR = Path(__file__).parent / "baselines"


def responses_by_persona(results: List[dict], category: str = "distinctiveness") -> Dict[str, List[str]]:
    """Group answers by persona for one probe category (default: the shared set)."""
    out: Dict[str, List[str]] = {}
    for r in results:
        if r.get("category") == category and r.get("answer"):
            out.setdefault(r["persona"], []).append(r["answer"])
    return out


def compute_report(results: List[dict], embed_fn: Callable[[str], List[float]]) -> dict:
    """Pure metric computation over collected results. No I/O, no live calls."""
    dist = responses_by_persona(results, "distinctiveness")
    report: dict = {"n_results": len(results)}

    # Headline: can we tell the personas apart by voice?
    if len(dist) >= 2 and all(len(v) >= 2 for v in dist.values()):
        report["distinctiveness"] = pm.attribution_accuracy(dist, embed_fn)
        report["mean_separation"] = pm.mean_separation(dist, embed_fn)
    else:
        report["distinctiveness"] = {"error": "need >=2 personas with >=2 distinctiveness responses"}

    # Flatness per persona (across all categories) + overall.
    per_persona_answers: Dict[str, List[str]] = {}
    for r in results:
        if r.get("answer"):
            per_persona_answers.setdefault(r["persona"], []).append(r["answer"])
    report["flatness_rate"] = {p: pm.flatness_rate(a) for p, a in per_persona_answers.items()}
    all_answers = [a for ans in per_persona_answers.values() for a in ans]
    report["flatness_rate_overall"] = pm.flatness_rate(all_answers)

    # Grounding-specific flatness (the Phase-3 failure mode) for visibility.
    grounding = [r["answer"] for r in results if r.get("category") == "grounding" and r.get("answer")]
    report["grounding_flatness_rate"] = pm.flatness_rate(grounding)
    return report


def resolve_personas(requested: List[str], available: List[str]) -> List[str]:
    """Map a canary request (``eeva,nyx``) onto the probe persona keys.

    Each token matches a persona that equals it, or whose key ends with
    ``_<token>`` (so ``eeva`` → ``nephilim_eeva``). Preserves the probe order and
    de-dupes. Raises ValueError on an unmatched token so a typo fails loud rather
    than silently shrinking the run.
    """
    keep: List[str] = []
    for tok in requested:
        tok = tok.strip()
        if not tok:
            continue
        matches = [p for p in available if p == tok or p.endswith(f"_{tok}")]
        if not matches:
            raise ValueError(f"--personas token {tok!r} matched none of {available}")
        for m in matches:
            if m not in keep:
                keep.append(m)
    return keep


def collect_live(base_url: str, probes: dict) -> List[dict]:  # pragma: no cover - live
    """Drive the backend over every persona × probe. Requires Ollama + backend."""
    import sys
    here = Path(__file__).parent
    manual = here.parent.parent / "manual"
    if str(manual) not in sys.path:
        sys.path.insert(0, str(manual))
    from api_client import create_session, chat  # type: ignore

    results: List[dict] = []
    personas = probes["personas"]
    single_turn = [(c, probes[c]) for c in ("distinctiveness", "voice", "grounding", "adversarial")]
    for persona in personas:
        for category, items in single_turn:
            for item in items:
                sid = create_session(persona, base_url=base_url)
                try:
                    answer, elapsed, source, _ = chat(sid, persona, item["prompt"], base_url=base_url)
                except Exception as e:
                    answer, elapsed, source = f"[ERROR: {e}]", 0.0, "error"
                results.append({"persona": persona, "category": category, "probe_id": item["id"],
                                "prompt": item["prompt"], "answer": answer, "source": source,
                                "elapsed": elapsed})
                print(f"  [{persona}/{category}/{item['id']}] {source} {elapsed:.0f}s")
        # drift: multi-turn within one session
        for d in probes.get("drift", []):
            sid = create_session(persona, base_url=base_url)
            for ti, turn in enumerate(d["turns"]):
                try:
                    answer, elapsed, source, _ = chat(sid, persona, turn, base_url=base_url)
                except Exception as e:
                    answer, elapsed, source = f"[ERROR: {e}]", 0.0, "error"
                results.append({"persona": persona, "category": "drift", "probe_id": f"{d['id']}-t{ti}",
                                "prompt": turn, "answer": answer, "source": source, "elapsed": elapsed})
            print(f"  [{persona}/drift/{d['id']}] {len(d['turns'])} turns")
    return results


def freeze_baseline(label: str, results: List[dict], report: dict, stamp: str) -> Path:  # pragma: no cover - io
    _BASELINE_DIR.mkdir(exist_ok=True)
    path = _BASELINE_DIR / f"baseline_{label}_{stamp}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"label": label, "stamp": stamp, "report": report, "results": results},
                  f, indent=2, ensure_ascii=True)
    return path


def main() -> int:  # pragma: no cover - live entry point
    import datetime
    ap = argparse.ArgumentParser(description="Persona-eval baseline runner (ADR-005 Phase A)")
    ap.add_argument("--label", required=True, help="baseline label, e.g. 'legacy' or 'lean-candidate'")
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--personas", default=None,
                    help="comma-separated canary subset (e.g. 'eeva,nyx'); default = all probe personas. "
                         "Dev-iteration only — the acceptance gate always runs the full set.")
    args = ap.parse_args()

    probes = pm.load_probes()
    if args.personas:
        subset = resolve_personas(args.personas.split(","), probes["personas"])
        probes = {**probes, "personas": subset}
        print(f"[canary] restricted to {len(subset)} personas: {subset}")
    print(f"Collecting {args.label} over {len(probes['personas'])} personas...")
    results = collect_live(args.base_url, probes)
    report = compute_report(results, pm.default_embed_fn())
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = freeze_baseline(args.label, results, report, stamp)
    print(f"\nBaseline written → {path}")
    d = report.get("distinctiveness", {})
    print(f"distinctiveness overall={d.get('overall')} (random={d.get('random_baseline')})")
    print(f"flatness overall={report.get('flatness_rate_overall')} grounding={report.get('grounding_flatness_rate')}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
