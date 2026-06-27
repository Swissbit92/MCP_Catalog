# tests/evaluation/persona_eval/blind_judge.py
"""Per-persona blind A/B driver over two frozen baselines (ADR-005 Phase B).

Belt-and-suspenders confirmation beyond the attribution metric: pair each
persona's legacy vs lean-candidate response to the SAME probe, hide which arm is
which (sides randomised, seeded), let a blind judge pick the more in-character
reply, then tally per persona with the exact sign test + the ADR-005 gate verdict.

The judge is the human-in-the-loop part:
- ``--emit FILE``  writes the blind pairs (left/right text only in the judge view)
  so an external blind judge (a fresh LLM agent, or a human) can rate them.
- ``--score PICKS`` reads picks {persona: {probe_id: left|right|tie|skip}} and
  prints per-persona + overall tally/verdict.
- ``--human PERSONA`` runs the interactive ``ab_harness.run_cli`` for one persona.

Pairing + scoring are pure and unit-tested headless; only the judge step is live.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Dict, List

import ab_harness as ab

_BASELINE_DIR = Path(__file__).parent / "baselines"
# Categories that actually probe voice / in-character behaviour.
VOICE_CATEGORIES = ("distinctiveness", "voice")


def _latest(label: str) -> Path:
    matches = sorted(_BASELINE_DIR.glob(f"baseline_{label}_*.json"))
    if not matches:
        raise FileNotFoundError(f"no baseline for label '{label}' under {_BASELINE_DIR}")
    return matches[-1]


def load_results(path: Path | str) -> List[dict]:
    return json.load(open(path, encoding="utf-8"))["results"]


def answers_by_persona(results: List[dict], categories=VOICE_CATEGORIES) -> Dict[str, Dict[str, str]]:
    """{persona: {probe_id: answer}} for the chosen probe categories (non-empty)."""
    out: Dict[str, Dict[str, str]] = {}
    for r in results:
        if r.get("category") in categories and r.get("answer") and not str(r["answer"]).startswith("[ERROR"):
            out.setdefault(r["persona"], {})[r["probe_id"]] = r["answer"]
    return out


def _meta_by_persona(results: List[dict], categories=VOICE_CATEGORIES) -> Dict[str, Dict[str, dict]]:
    out: Dict[str, Dict[str, dict]] = {}
    for r in results:
        if r.get("category") in categories:
            out.setdefault(r["persona"], {})[r["probe_id"]] = {
                "persona": r["persona"], "category": r["category"], "prompt": r["prompt"],
            }
    return out


def build_persona_pairs(
    legacy_results: List[dict],
    candidate_results: List[dict],
    seed: int = 0,
    categories=VOICE_CATEGORIES,
) -> Dict[str, List[ab.BlindPair]]:
    """Per-persona blind pairs (legacy=arm A, candidate=arm B). Seeded for repro."""
    leg = answers_by_persona(legacy_results, categories)
    cand = answers_by_persona(candidate_results, categories)
    meta = _meta_by_persona(legacy_results, categories)
    pairs: Dict[str, List[ab.BlindPair]] = {}
    for persona in sorted(set(leg) & set(cand)):
        rng = random.Random(f"{seed}:{persona}")
        pairs[persona] = ab.make_blind_pairs(leg[persona], cand[persona], rng=rng, meta=meta.get(persona))
    return pairs


def score_from_picks(
    pairs_by_persona: Dict[str, List[ab.BlindPair]],
    picks_by_persona: Dict[str, Dict[str, str]],
    alpha: float = 0.05,
) -> dict:
    """Per-persona tally + verdict and a pooled overall (candidate = arm B)."""
    report: dict = {"per_persona": {}}
    pooled_a = pooled_b = 0
    for persona, pairs in pairs_by_persona.items():
        picks = picks_by_persona.get(persona, {})
        t = ab.tally(pairs, picks)
        report["per_persona"][persona] = {"tally": t, "verdict": ab.verdict(t, alpha=alpha)}
        pooled_a += t["a_wins"]
        pooled_b += t["b_wins"]
    overall = {
        "legacy_wins": pooled_a, "candidate_wins": pooled_b,
        "candidate_win_rate": round(pooled_b / (pooled_a + pooled_b), 4) if (pooled_a + pooled_b) else None,
        "sign_test_p": ab._two_sided_sign_test(pooled_a, pooled_b),
    }
    overall["verdict"] = ab.verdict(
        {"a_win_rate": round(pooled_a / (pooled_a + pooled_b), 4) if (pooled_a + pooled_b) else None,
         "sign_test_p": overall["sign_test_p"]},
        alpha=alpha,
    )
    report["overall"] = overall
    return report


def _emit(pairs_by_persona: Dict[str, List[ab.BlindPair]], path: Path | str) -> None:
    """Write blind pairs. Includes left_is for scoring; a judge is only shown left/right."""
    out = {
        persona: [
            {"probe_id": p.probe_id, "prompt": p.meta.get("prompt", ""), "category": p.meta.get("category", ""),
             "left": p.left, "right": p.right, "left_is": p.left_is}
            for p in pairs
        ]
        for persona, pairs in pairs_by_persona.items()
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)


def main() -> int:  # pragma: no cover - CLI
    ap = argparse.ArgumentParser(description="Per-persona blind A/B (ADR-005 Phase B)")
    ap.add_argument("--legacy-label", default="legacy")
    ap.add_argument("--candidate-label", default="lean-candidate")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--emit", metavar="FILE", help="write blind pairs to FILE for judging")
    ap.add_argument("--score", metavar="PICKS", help="score picks JSON {persona:{probe_id:left|right|tie}}")
    ap.add_argument("--human", metavar="PERSONA", help="interactive run_cli for one persona")
    args = ap.parse_args()

    pairs = build_persona_pairs(load_results(_latest(args.legacy_label)),
                                load_results(_latest(args.candidate_label)), seed=args.seed)

    if args.emit:
        _emit(pairs, args.emit)
        n = sum(len(v) for v in pairs.values())
        print(f"emitted {n} pairs across {len(pairs)} personas → {args.emit}")
        return 0
    if args.human:
        if args.human not in pairs:
            print(f"no pairs for persona '{args.human}'; have {sorted(pairs)}")
            return 1
        picks = ab.run_cli(pairs[args.human])
        rep = score_from_picks({args.human: pairs[args.human]}, {args.human: picks})
        print(json.dumps(rep["per_persona"][args.human], indent=2))
        return 0
    if args.score:
        picks_by_persona = json.load(open(args.score, encoding="utf-8"))
        rep = score_from_picks(pairs, picks_by_persona)
        for persona, r in rep["per_persona"].items():
            t = r["tally"]
            print(f"{persona:18s} legacy {t['a_wins']:2d} / cand {t['b_wins']:2d} / tie {t['ties']:2d}  "
                  f"cand_rate {t['a_win_rate']}  {r['verdict']}")
        o = rep["overall"]
        print(f"\nOVERALL  legacy {o['legacy_wins']} / candidate {o['candidate_wins']}  "
              f"cand_win_rate {o['candidate_win_rate']}  p={o['sign_test_p']}\n{o['verdict']}")
        return 0

    ap.error("one of --emit / --score / --human is required")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
