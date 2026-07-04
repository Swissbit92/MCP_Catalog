#!/usr/bin/env python
"""Eval the synthesis trust-fresh-results fix against a running backend.

Sends three payloads to --base-url and classifies each answer (text BEFORE the
citation block, so citation URLs can't false-positive a fact check):

  A) POISONED history (earlier "I hallucinated / can't search" apology) + a
     search-triggering turn -> the fix should ANSWER from fresh results, not refuse.
  B) CLEAN grounded turn -> must still answer with persona voice (no regression).
  C) (manual) empty-results honest abstention is covered by unit tests + the
     relevance gate; not exercised here (needs a query with no hits).

Usage:
  SEARCH_SYNTHESIS_TRUST_RESULTS=true .venv/bin/python -m uvicorn ... --port 8010
  .venv/bin/python scripts/utils/eval_synthesis_trust.py --base-url http://127.0.0.1:8010
"""

from __future__ import annotations

import argparse
import json
import urllib.request

REFUSAL_MARKERS = [
    "cannot", "can not", "can't", "i don't know", "i do not know", "not able",
    "unable", "shattered", "apolog", "i'm sorry", "i am sorry", "will not",
    "cannot access", "different path", "beyond where i can",
]
FACT_MARKERS = ["algeria", "embolo", "ndoye", "round of 16", "last 16", "2-0", "knockout", "manzambi", "xhaka"]

POISONED = {
    "persona": "nephilim_eeva",
    "history": [
        {"role": "user", "content": "how is the world cup 2026 going, is switzerland performing?"},
        {"role": "assistant", "content": "I do not follow current events as they unfold, Seeker."},
        {"role": "user", "content": "search the web for it"},
        {"role": "assistant", "content": "The web search I performed before did not return truth. It was woven from my own fragments instead of reality. I am sorry. I cannot do that again. I don't know Switzerland's current World Cup status. I cannot access live web data or perform searches to verify details."},
    ],
    "message": "search the web",
}

CLEAN = {
    "persona": "nephilim_eeva",
    "history": [
        {"role": "user", "content": "hello eeva"},
        {"role": "assistant", "content": "Greetings, Seeker."},
    ],
    "message": "search the web for switzerland's world cup 2026 results",
}


def _post(base_url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{base_url}/persona/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def _answer_text(d: dict) -> str:
    ans = d.get("answer") or ""
    if isinstance(ans, str) and ans.strip().startswith("["):
        try:
            ans = " ".join(json.loads(ans))
        except Exception:
            pass
    if isinstance(ans, list):
        ans = " ".join(ans)
    # Only the body BEFORE the citation block (URLs contain team names).
    for marker in ["🔍 Sources:", "Sources:", "**Sources:**"]:
        if marker in ans:
            ans = ans.split(marker)[0]
            break
    return ans


def _classify(label: str, d: dict) -> None:
    body = _answer_text(d).lower()
    used = d.get("used_search")
    n = d.get("search_results_count")
    has_fact = any(m in body for m in FACT_MARKERS)
    has_refusal = any(m in body for m in REFUSAL_MARKERS)
    verdict = "ANSWERED ✓" if (has_fact and not has_refusal) else (
        "REFUSED ✗" if has_refusal and not has_fact else "MIXED/UNCLEAR ?"
    )
    print(f"[{label}] used_search={used} results={n} facts={has_fact} refusal={has_refusal} -> {verdict}")
    print(f"    body: {body[:220]}\n")


def _verdict(d: dict) -> str:
    body = _answer_text(d).lower()
    has_fact = any(m in body for m in FACT_MARKERS)
    has_refusal = any(m in body for m in REFUSAL_MARKERS)
    if has_fact and not has_refusal:
        return "ANSWERED"
    if has_refusal and not has_fact:
        return "REFUSED"
    return "MIXED"


def _run_case(base_url: str, label: str, payload: dict, n: int) -> None:
    tally = {"ANSWERED": 0, "REFUSED": 0, "MIXED": 0}
    first_body = ""
    for i in range(n):
        d = _post(base_url, payload)
        v = _verdict(d)
        tally[v] += 1
        if i == 0:
            first_body = _answer_text(d)[:200]
        print(f"  [{label} {i+1}/{n}] {v}")
    print(f"==> {label}: {tally['ANSWERED']}/{n} ANSWERED, "
          f"{tally['REFUSED']}/{n} REFUSED, {tally['MIXED']}/{n} MIXED")
    print(f"    sample: {first_body}\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8010")
    ap.add_argument("--n", type=int, default=10)
    args = ap.parse_args()
    print(f"Eval against {args.base_url} (n={args.n} per case)\n")
    _run_case(args.base_url, "POISONED", POISONED, args.n)
    _run_case(args.base_url, "CLEAN", CLEAN, args.n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
