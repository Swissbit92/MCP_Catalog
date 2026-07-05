"""ADR-006 M5 helper — compare two frozen persona-eval baselines (OFF vs ON).

Prints overall + per-persona distinctiveness attribution and the delta, plus
flatness. Match-or-beat is the gate: ON must not drop vs the OFF ruler.

Usage: python compare_baselines.py <off_baseline.json> <on_baseline.json>
"""
from __future__ import annotations

import json
import sys


def _load(path):
    with open(path) as f:
        return json.load(f)


def main() -> int:
    off, on = _load(sys.argv[1]), _load(sys.argv[2])
    od, nd = off["report"]["distinctiveness"], on["report"]["distinctiveness"]
    print(f"{'persona':<20} {'OFF':>7} {'ON':>7} {'delta':>8}")
    print("-" * 46)
    op, np_ = od.get("per_persona", {}), nd.get("per_persona", {})
    for p in sorted(set(op) | set(np_)):
        o, n = op.get(p), np_.get(p)
        d = (n - o) if (o is not None and n is not None) else float("nan")
        print(f"{p:<20} {o if o is not None else '-':>7} {n if n is not None else '-':>7} {d:>+8.3f}")
    print("-" * 46)
    oo, no = od.get("overall"), nd.get("overall")
    print(f"{'OVERALL':<20} {oo:>7.3f} {no:>7.3f} {(no - oo):>+8.3f}")
    print(f"random baseline: {od.get('random_baseline')}")
    print(f"flatness overall: OFF={off['report'].get('flatness_rate_overall')} "
          f"ON={on['report'].get('flatness_rate_overall')}")
    verdict = "MATCH-OR-BEAT ✅" if no >= oo - 0.01 else "REGRESSION ❌ (keep OFF)"
    print(f"\nGate: {verdict}  (ON {no:.3f} vs OFF ruler {oo:.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
