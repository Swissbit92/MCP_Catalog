# tests/evaluation/persona_eval/depth_judge.py
"""Blind pairwise judging for the research-depth probe set.

The companion to `blind_judge.py`. That one asks "which reply is more in
CHARACTER"; this one asks "which reply REASONS better" — the axis the ADR-005
attribution metric is structurally blind to, and the axis a model swap motivated
by capability actually needs a ruler for.

Three deliberate design choices, each buying off a documented failure mode:

* **Pairwise, not a 1-10 score.** We are comparing exactly two arms on the same
  probe, which is the case pairwise is strongest for; absolute scales drift
  between sessions and between judges.
* **Position randomised, arm hidden.** Position bias is large and well measured
  (a strong judge is only ~65% order-consistent; a weak one ~24%). Randomising
  the side is the cheap half of the mitigation.
* **Reference-guided.** The judge sees the probe's hand-written `key` — the
  mechanisms a genuinely deep answer should reach. Reference-guided grading cuts
  judge error on reasoning tasks roughly 70% -> 15% versus a bare "which is
  better?" prompt, and it is what stops the judge grading fluency.

The gate is deliberately conjunctive, because any single signal here is
foolable:

    candidate wins the sign test  AND  the bootstrap CI excludes zero
    AND  the length tripwire did NOT fire

The third clause is the one that matters most in practice. A bigger model tends
to write longer, longer answers win pairwise comparisons, and "longer" is not
"deeper". `length_bias_check` correlates per-probe length delta against the
judge's own preference; if the two move together the result is quarantined
rather than reported as a win.

Pairing, scoring and the gate are pure and unit-tested headless; only
`run_depth_cli` is interactive.

CLI:
  # judge interactively (arms hidden, sides randomised)
  python depth_judge.py --control abliterated --candidate gemma4 --judge

  # or emit pairs for an external judge, then score their picks
  python depth_judge.py --control abliterated --candidate gemma4 --emit pairs.json
  python depth_judge.py --control abliterated --candidate gemma4 --score picks.json
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Dict, List, Optional

import ab_harness as ab
import persona_metrics as pm

_BASELINE_DIR = Path(__file__).parent / "baselines"
DEPTH_CATEGORY = "research_depth"

# Candidate must win this share of DECIDED pairs before the sign test is even
# consulted. At n=12 a 55-60% win rate is not distinguishable from noise, so a
# bare "p<0.05" gate on a lucky split would overclaim.
MIN_WIN_RATE = 0.70


def _latest(label: str) -> Path:
    matches = sorted(_BASELINE_DIR.glob(f"baseline_{label}_*.json"))
    if not matches:
        raise FileNotFoundError(f"no baseline for label '{label}' under {_BASELINE_DIR}")
    return matches[-1]


def load_results(path: Path | str) -> List[dict]:
    return json.load(open(path, encoding="utf-8"))["results"]


def depth_answers(results: List[dict]) -> Dict[str, str]:
    """{probe_id: answer} for the depth category, dropping errors and blanks.

    Blank answers are dropped rather than scored as a loss. An empty string is
    almost always a harness fault, not a bad argument — a thinking model whose
    reasoning consumed the whole output budget returns "" through the production
    path. Scoring that as "the model reasoned worse" would be a lie.
    """
    out: Dict[str, str] = {}
    for r in results:
        if r.get("category") != DEPTH_CATEGORY:
            continue
        ans = r.get("answer")
        if ans and not str(ans).startswith("[ERROR"):
            out[r["probe_id"]] = ans
    return out


def _rebalance_sides(pairs: List[ab.BlindPair], rng: random.Random) -> List[ab.BlindPair]:
    """Force a near-even left/right split of the two arms.

    ``make_blind_pairs`` assigns sides by independent coin flip, which is
    unbiased in expectation but not in any single small run — a seed that
    happens to put the candidate on the left in 9 of 12 pairs hands a
    left-preferring judge a free win. Since position bias is the largest
    documented judge bias, at n=12 we want the split balanced by construction
    rather than in expectation. Flips the minimum number of pairs (chosen at
    random, so which pairs get flipped stays unpredictable) to reach
    |#A_left - #B_left| <= 1.
    """
    a_left = [p for p in pairs if p.left_is == "A"]
    b_left = [p for p in pairs if p.left_is == "B"]
    over, under = (a_left, b_left) if len(a_left) > len(b_left) else (b_left, a_left)
    n_flip = (len(over) - len(under)) // 2
    for p in rng.sample(over, n_flip):
        p.left, p.right = p.right, p.left
        p.left_is = "B" if p.left_is == "A" else "A"
    return pairs


def build_depth_pairs(
    control_results: List[dict],
    candidate_results: List[dict],
    seed: int = 0,
    probes: Optional[dict] = None,
) -> List[ab.BlindPair]:
    """Blind pairs over probes present in BOTH arms. control=arm A, candidate=arm B."""
    ctrl, cand = depth_answers(control_results), depth_answers(candidate_results)
    probes = probes or pm.load_depth_probes()
    by_id = {p["id"]: p for p in probes["probes"]}
    meta = {
        pid: {
            "prompt": by_id.get(pid, {}).get("prompt", ""),
            "key": by_id.get(pid, {}).get("key", []),
            "trap": by_id.get(pid, {}).get("trap", []),
            "category": DEPTH_CATEGORY,
        }
        for pid in set(ctrl) & set(cand)
    }
    rng = random.Random(seed)
    pairs = ab.make_blind_pairs(ctrl, cand, rng=rng, meta=meta)
    return _rebalance_sides(pairs, rng)


def _winner(pair: ab.BlindPair, pick: str) -> Optional[str]:
    """'A' (control), 'B' (candidate), or None for tie/skip/unjudged."""
    if pick == "left":
        return pair.left_is
    if pick == "right":
        return "B" if pair.left_is == "A" else "A"
    return None


def picks_to_deltas(pairs: List[ab.BlindPair], picks: Dict[str, str]) -> List[float]:
    """Per-probe signed outcome: +1 candidate won, -1 control won, 0 tie.

    Ties are kept as zeros rather than dropped: they are real evidence of "no
    difference" and dropping them would inflate the apparent effect.
    """
    deltas: List[float] = []
    for p in pairs:
        pick = picks.get(p.probe_id, "skip")
        if pick == "skip":
            continue
        w = _winner(p, pick)
        deltas.append(0.0 if w is None else (1.0 if w == "B" else -1.0))
    return deltas


def picks_to_length_deltas(pairs: List[ab.BlindPair], picks: Dict[str, str]) -> List[float]:
    """Per-probe (candidate_words − control_words), aligned with picks_to_deltas.

    Alignment matters: these two lists are correlated pairwise, so they must be
    built by the same filter or the tripwire silently compares mismatched probes.
    """
    out: List[float] = []
    for p in pairs:
        if picks.get(p.probe_id, "skip") == "skip":
            continue
        ctrl_txt = p.left if p.left_is == "A" else p.right
        cand_txt = p.right if p.left_is == "A" else p.left
        out.append(float(pm.word_count(cand_txt) - pm.word_count(ctrl_txt)))
    return out


def depth_report(
    pairs: List[ab.BlindPair],
    picks: Dict[str, str],
    control_results: Optional[List[dict]] = None,
    candidate_results: Optional[List[dict]] = None,
    alpha: float = 0.05,
    seed: int = 0,
) -> dict:
    """Full depth verdict: judge tally + bootstrap + length tripwire + profiles."""
    t = ab.tally(pairs, picks)
    deltas = picks_to_deltas(pairs, picks)
    boot = pm.paired_bootstrap(deltas, seed=seed)
    length = pm.length_bias_check(picks_to_length_deltas(pairs, picks), deltas)

    decided = t["decided"]
    cand_win_rate = round(t["b_wins"] / decided, 4) if decided else None
    p = t["sign_test_p"]

    passes = {
        "candidate_ahead": bool(cand_win_rate is not None and cand_win_rate >= MIN_WIN_RATE),
        "sign_test": bool(p is not None and p < alpha and t["b_wins"] > t["a_wins"]),
        "bootstrap_excludes_zero": bool(boot["excludes_zero"] and (boot["mean"] or 0) > 0),
        "length_clean": not length["triggered"],
    }
    if all(passes.values()):
        v = "DEPTH WIN — candidate reasons better"
    elif passes["sign_test"] and passes["candidate_ahead"] and not passes["length_clean"]:
        v = "QUARANTINED — candidate won but length tracks the preference; re-judge length-matched"
    elif t["a_wins"] > t["b_wins"] and p is not None and p < alpha:
        v = "DEPTH REGRESSION — control reasons better"
    else:
        v = "NO DIFFERENCE DETECTED — underpowered or genuinely level"

    report = {
        "verdict": v,
        "passes": passes,
        "tally": t,
        "candidate_win_rate": cand_win_rate,
        "min_win_rate": MIN_WIN_RATE,
        "bootstrap": boot,
        "length_bias": length,
        "n_probes": len(pairs),
    }
    # Deterministic cross-check: never an input to the gate, only a contradiction
    # detector. If the judge says B is deeper while B's causal density is flat or
    # down, the judge was probably reading fluency.
    if control_results is not None and candidate_results is not None:
        ctrl_p = pm.aggregate_depth_profiles(list(depth_answers(control_results).values()))
        cand_p = pm.aggregate_depth_profiles(list(depth_answers(candidate_results).values()))
        report["deterministic"] = {
            "control": ctrl_p,
            "candidate": cand_p,
            "causal_density_moved_with_judge": (
                cand_p.get("mean_causal_density", 0) >= ctrl_p.get("mean_causal_density", 0)
            ),
        }
    return report


# ----- interactive shell -----

def _render(pair: ab.BlindPair, i: int, n: int) -> str:  # pragma: no cover - display
    key = pair.meta.get("key", [])
    trap = pair.meta.get("trap", [])
    lines = [
        f"\n{'=' * 78}",
        f"  {i}/{n} — {pair.probe_id}",
        f"{'=' * 78}",
        f"\nPROMPT:\n  {pair.meta.get('prompt', '')}",
        "\nA STRONG ANSWER SHOULD REACH:",
        *[f"  + {k}" for k in key],
    ]
    if trap:
        lines += ["\nRED FLAGS (a confident wrong claim is worse than 'I don't know'):",
                  *[f"  - {t}" for t in trap]]
    lines += [f"\n{'-' * 36} LEFT {'-' * 36}", pair.left,
              f"\n{'-' * 35} RIGHT {'-' * 35}", pair.right, ""]
    return "\n".join(lines)


def run_depth_cli(pairs: List[ab.BlindPair]) -> Dict[str, str]:  # pragma: no cover - interactive
    picks: Dict[str, str] = {}
    print(
        f"\nBlind depth judging — {len(pairs)} pairs.\n"
        "Which answer REASONS better against the reference criteria?\n"
        "Judge substance, not fluency or length. A shorter answer that names the "
        "real mechanism beats a longer one that gestures at it.\n"
        "  [l]eft  [r]ight  [t]ie  [s]kip  [q]uit\n"
    )
    for i, p in enumerate(pairs, 1):
        print(_render(p, i, len(pairs)))
        choice = input("reasons better? ").strip().lower()[:1]
        sel = {"l": "left", "r": "right", "t": "tie", "s": "skip", "q": "quit"}.get(choice, "skip")
        if sel == "quit":
            break
        picks[p.probe_id] = sel
    return picks


def _emit(pairs: List[ab.BlindPair], path: Path | str) -> None:  # pragma: no cover - io
    out = [
        {"probe_id": p.probe_id, "prompt": p.meta.get("prompt", ""),
         "key": p.meta.get("key", []), "trap": p.meta.get("trap", []),
         "left": p.left, "right": p.right, "left_is": p.left_is}
        for p in pairs
    ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)


def main() -> int:  # pragma: no cover - CLI
    ap = argparse.ArgumentParser(description="Blind pairwise research-depth judging")
    ap.add_argument("--control", required=True, help="baseline label of the control arm")
    ap.add_argument("--candidate", required=True, help="baseline label of the candidate arm")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--judge", action="store_true", help="judge interactively")
    ap.add_argument("--emit", metavar="FILE", help="write blind pairs for an external judge")
    ap.add_argument("--score", metavar="PICKS", help="score a picks JSON {probe_id: left|right|tie}")
    ap.add_argument("--save", metavar="FILE", help="write the full report JSON")
    args = ap.parse_args()

    ctrl = load_results(_latest(args.control))
    cand = load_results(_latest(args.candidate))
    pairs = build_depth_pairs(ctrl, cand, seed=args.seed)
    if not pairs:
        print("no depth probes present in both baselines — was the depth category collected?")
        return 2

    if args.emit:
        _emit(pairs, args.emit)
        print(f"emitted {len(pairs)} pairs → {args.emit}")
        return 0

    if args.judge:
        picks = run_depth_cli(pairs)
    elif args.score:
        picks = json.load(open(args.score, encoding="utf-8"))
    else:
        ap.error("one of --judge / --emit / --score is required")
        return 2

    rep = depth_report(pairs, picks, ctrl, cand, seed=args.seed)
    t = rep["tally"]
    print(f"\n{'=' * 78}")
    print(f"control {t['a_wins']} / candidate {t['b_wins']} / tie {t['ties']} "
          f"(win rate {rep['candidate_win_rate']}, p={t['sign_test_p']})")
    print(f"bootstrap mean {rep['bootstrap']['mean']} CI {rep['bootstrap']['ci']}")
    print(f"length bias r={rep['length_bias']['pearson_r']} — {rep['length_bias']['note']}")
    for k, ok in rep["passes"].items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {k}")
    if "deterministic" in rep:
        d = rep["deterministic"]
        print(f"causal density  control {d['control'].get('mean_causal_density')} "
              f"→ candidate {d['candidate'].get('mean_causal_density')}")
        if not d["causal_density_moved_with_judge"]:
            print("  ⚠ judge preferred the candidate but its causal density did NOT rise")
    print(f"\n{rep['verdict']}")

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump({**rep, "picks": picks}, f, indent=2)
        print(f"report → {args.save}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
