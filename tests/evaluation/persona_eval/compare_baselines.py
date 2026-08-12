"""ADR-006 M5 helper — compare two frozen persona-eval baselines (OFF vs ON).

Prints overall + per-persona distinctiveness attribution and the delta, plus
flatness. Match-or-beat is the gate: ON must not drop vs the OFF ruler.

**Commensurability guard.** Attribution accuracy is a discrimination-against-the-
others metric: its chance floor is ``1/N`` for ``N`` personas, so a candidate run
over a *different* label space (fewer personas ⇒ higher chance, fewer competing
centroids) is NOT comparable to the ruler — comparing them silently reports a
green verdict that is pure chance-baseline shift (see the frozen-gallery design
note in the README). This module refuses a verdict when the two runs have
different ``N`` (``random_baseline``), and switches to a per-persona gate over the
shared personas when the candidate scored only a subset of the ruler's set (the
frozen-gallery case: same ``N``, active personas only).

Usage: python compare_baselines.py <off_baseline.json> <on_baseline.json>
Exit code: 0 = MATCH-OR-BEAT · 1 = REGRESSION · 2 = INCOMMENSURABLE (no verdict).
"""

from __future__ import annotations

import json
import sys

# Match-or-beat tolerance: ON must not drop more than this below the OFF ruler.
TOL = 0.01


def _load(path):
    with open(path) as f:
        return json.load(f)


def _n_from_baseline(random_baseline):
    """Recover the label-space size N from the reported chance floor (1/N)."""
    if not random_baseline:
        return None
    return round(1.0 / random_baseline)


def compare(off: dict, on: dict) -> dict:
    """Pure comparison core — no I/O. Returns a verdict dict the CLI renders.

    Verdicts: ``MATCH-OR-BEAT`` / ``REGRESSION`` (commensurable) or
    ``INCOMMENSURABLE`` (different label space ⇒ scores not comparable, no gate).
    ``mode`` is ``overall`` (full-vs-full) or ``per_persona`` (frozen-gallery: the
    candidate scored a subset of the ruler's personas against the same N-centroid
    field, so we gate each active persona against its own ruler value).
    """
    od = off["report"]["distinctiveness"]
    nd = on["report"]["distinctiveness"]
    ob, nb = od.get("random_baseline"), nd.get("random_baseline")
    op, np_ = od.get("per_persona", {}), nd.get("per_persona", {})
    n_off, n_on = _n_from_baseline(ob), _n_from_baseline(nb)

    # Guard 1 — different label space (N). This is the silent-inflation hole: a
    # 2-persona candidate (chance 0.5) vs a 7-persona ruler (chance 0.14) would
    # otherwise trivially clear a bare `overall` gate. `not ob` catches BOTH a
    # missing (None) AND a degenerate 0 random_baseline — an undefined chance
    # floor must land here explicitly, never slide into a comparison as "passed".
    if not ob or not nb or abs(ob - nb) > 1e-9:
        return {
            "commensurable": False,
            "verdict": "INCOMMENSURABLE",
            "reason": (
                f"different label space — ruler chance 1/{n_off} vs candidate "
                f"1/{n_on}; attribution accuracy is not comparable across N"
            ),
            "n_off": n_off,
            "n_on": n_on,
        }

    # Same N from here on.
    if set(op) == set(np_):
        # Full-vs-full: gate on overall (same population, same field).
        oo, no = od.get("overall"), nd.get("overall")
        return {
            "commensurable": True,
            "mode": "overall",
            "n": n_off,
            "off": oo,
            "on": no,
            "delta": no - oo,
            "verdict": "MATCH-OR-BEAT" if no >= oo - TOL else "REGRESSION",
        }

    # Same N, different persona sets — the frozen-gallery case (candidate scored
    # only the active subset against the full frozen field). `overall` populations
    # differ, so gate per-persona over the personas present in BOTH.
    shared = [p for p in op if p in np_]
    if not shared:
        return {
            "commensurable": False,
            "verdict": "INCOMMENSURABLE",
            "reason": (
                f"same N (1/{n_off}) but no shared personas between ruler and "
                "candidate — nothing to gate"
            ),
            "n_off": n_off,
            "n_on": n_on,
        }
    deltas = {p: round(np_[p] - op[p], 4) for p in shared}
    worst = min(deltas.values())
    return {
        "commensurable": True,
        "mode": "per_persona",
        "n": n_off,
        "shared": shared,
        "deltas": deltas,
        "worst": worst,
        "verdict": "MATCH-OR-BEAT" if worst >= -TOL else "REGRESSION",
    }


def main() -> int:
    off, on = _load(sys.argv[1]), _load(sys.argv[2])
    od, nd = off["report"]["distinctiveness"], on["report"]["distinctiveness"]
    op, np_ = od.get("per_persona", {}), nd.get("per_persona", {})

    print(f"{'persona':<20} {'OFF':>7} {'ON':>7} {'delta':>8}")
    print("-" * 46)
    for p in sorted(set(op) | set(np_)):
        o, n = op.get(p), np_.get(p)
        d = (n - o) if (o is not None and n is not None) else float("nan")
        print(
            f"{p:<20} {o if o is not None else '-':>7} {n if n is not None else '-':>7} {d:>+8.3f}"
        )
    print("-" * 46)
    oo, no = od.get("overall"), nd.get("overall")
    if oo is not None and no is not None:
        print(f"{'OVERALL':<20} {oo:>7.3f} {no:>7.3f} {(no - oo):>+8.3f}")
    print(f"random baseline: OFF={od.get('random_baseline')} ON={nd.get('random_baseline')}")
    print(
        f"flatness overall: OFF={off['report'].get('flatness_rate_overall')} "
        f"ON={on['report'].get('flatness_rate_overall')}"
    )

    res = compare(off, on)
    print()
    if not res["commensurable"]:
        print(f"Gate: INCOMMENSURABLE ⛔ — {res['reason']}")
        print(
            "No verdict: re-run the candidate over the SAME persona set as the ruler "
            "(or use --gallery so chance stays 1/N)."
        )
        return 2
    if res["mode"] == "overall":
        icon = "✅" if res["verdict"] == "MATCH-OR-BEAT" else "❌ (keep OFF)"
        print(
            f"Gate: {res['verdict']} {icon}  (ON {res['on']:.3f} vs OFF ruler "
            f"{res['off']:.3f}, chance 1/{res['n']})"
        )
    else:  # per_persona (frozen-gallery)
        icon = "✅" if res["verdict"] == "MATCH-OR-BEAT" else "❌ (keep OFF)"
        print(
            f"Gate: {res['verdict']} {icon}  [frozen-gallery, chance 1/{res['n']}] "
            f"per-persona over {res['shared']}; worst delta {res['worst']:+.3f}"
        )
    return 0 if res["verdict"] == "MATCH-OR-BEAT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
