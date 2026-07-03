# tests/evaluation/persona_eval/ab_harness.py
"""Blind A/B rating harness (ADR-005 Phase A).

The trustworthy human-in-the-loop judge: present a probe's legacy vs candidate
response side-by-side with sides randomised and labels hidden, collect the
rater's pick, then tally win-rate with an exact two-sided sign test. Used to
decide whether a leaned-prompt candidate (Phase B) matches-or-beats the legacy
baseline per persona — the ADR-005 acceptance gate.

Pure logic (pairing + tally + significance) is unit-tested headless; ``run_cli``
is the thin interactive shell.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class BlindPair:
    probe_id: str
    left: str
    right: str
    left_is: str  # "A" or "B" — which arm is on the left (hidden from the rater)
    meta: dict = field(default_factory=dict)


def make_blind_pairs(
    arm_a: Dict[str, str],
    arm_b: Dict[str, str],
    rng: Optional[random.Random] = None,
    meta: Optional[Dict[str, dict]] = None,
) -> List[BlindPair]:
    """Build blind pairs for every probe_id present in BOTH arms.

    Side assignment (which arm is 'left') is randomised per pair so the rater
    can't infer the arm from position. ``rng`` is injectable for deterministic
    tests. Probe order is also shuffled.
    """
    rng = rng or random.Random()
    meta = meta or {}
    ids = sorted(set(arm_a) & set(arm_b))
    rng.shuffle(ids)
    pairs: List[BlindPair] = []
    for pid in ids:
        a_on_left = rng.random() < 0.5
        pairs.append(BlindPair(
            probe_id=pid,
            left=arm_a[pid] if a_on_left else arm_b[pid],
            right=arm_b[pid] if a_on_left else arm_a[pid],
            left_is="A" if a_on_left else "B",
            meta=meta.get(pid, {}),
        ))
    return pairs


def tally(pairs: List[BlindPair], picks: Dict[str, str]) -> dict:
    """Tally ratings. ``picks`` maps probe_id -> 'left' | 'right' | 'tie' | 'skip'.

    Returns A/B win counts, A win-rate over decided pairs, and an exact two-sided
    sign-test p-value (probability of the observed split under 50/50, ties
    excluded).
    """
    a_wins = b_wins = ties = skipped = 0
    for p in pairs:
        choice = picks.get(p.probe_id, "skip")
        if choice == "tie":
            ties += 1
        elif choice == "skip":
            skipped += 1
        elif choice == "left":
            (a_wins, b_wins) = (a_wins + 1, b_wins) if p.left_is == "A" else (a_wins, b_wins + 1)
        elif choice == "right":
            (a_wins, b_wins) = (a_wins + 1, b_wins) if p.left_is == "B" else (a_wins, b_wins + 1)
    decided = a_wins + b_wins
    return {
        "a_wins": a_wins,
        "b_wins": b_wins,
        "ties": ties,
        "skipped": skipped,
        "decided": decided,
        "a_win_rate": round(a_wins / decided, 4) if decided else None,
        "sign_test_p": _two_sided_sign_test(a_wins, b_wins),
    }


def _two_sided_sign_test(k1: int, k2: int) -> Optional[float]:
    """Exact two-sided binomial sign test p-value for a k1 vs k2 split (p=0.5)."""
    n = k1 + k2
    if n == 0:
        return None
    k = min(k1, k2)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return round(min(1.0, 2 * tail), 4)


def verdict(tally_result: dict, arm_a_label: str = "legacy", arm_b_label: str = "candidate",
            alpha: float = 0.05) -> str:
    """Human-readable verdict mapped to the ADR-005 gate (candidate = arm B)."""
    rate = tally_result["a_win_rate"]
    if rate is None:
        return "no decided pairs"
    p = tally_result["sign_test_p"]
    sig = (p is not None and p < alpha)
    if not sig:
        return f"PARITY (no significant difference, p={p}) — candidate may flip"
    if rate < 0.5:
        return f"CANDIDATE BETTER ({arm_b_label} wins, p={p}) — flip"
    return f"CANDIDATE WORSE ({arm_a_label} wins, p={p}) — do NOT flip; fix or keep legacy"


# ----- thin interactive shell -----

def run_cli(pairs: List[BlindPair]) -> Dict[str, str]:  # pragma: no cover - interactive
    picks: Dict[str, str] = {}
    print(f"\nBlind A/B — {len(pairs)} pairs. For each: [l]eft / [r]ight / [t]ie / [s]kip / [q]uit\n")
    for i, p in enumerate(pairs, 1):
        ctx = f" ({p.meta.get('persona', '')}/{p.meta.get('category', '')})" if p.meta else ""
        print(f"\n=== {i}/{len(pairs)} — probe {p.probe_id}{ctx} ===")
        print(f"\n[LEFT]\n{p.left}\n\n[RIGHT]\n{p.right}\n")
        choice = input("more in-character? ").strip().lower()[:1]
        mapping = {"l": "left", "r": "right", "t": "tie", "s": "skip", "q": "quit"}
        sel = mapping.get(choice, "skip")
        if sel == "quit":
            break
        picks[p.probe_id] = sel
    return picks


def save_ratings(path: Path | str, pairs: List[BlindPair], picks: Dict[str, str],
                 extra: Optional[dict] = None) -> None:  # pragma: no cover - io
    out = {
        "tally": tally(pairs, picks),
        "verdict": verdict(tally(pairs, picks)),
        "picks": picks,
        "pairs": [{"probe_id": p.probe_id, "left_is": p.left_is, **p.meta} for p in pairs],
        **(extra or {}),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=True)
