"""
NEPHILIM Comprehensive Persona Test Suite
==========================================

Runs ~100 queries per persona across all MCPs and behavioral dimensions.
Tests persona voice consistency, MCP routing correctness, anti-hallucination,
adversarial robustness, emotional intelligence, and lore accuracy.

Usage
-----
# Full run — all personas, all tests (600+ queries)
python tests/manual/comprehensive_persona_test.py

# Single persona
python tests/manual/comprehensive_persona_test.py --persona nephilim_eeva

# Category filter
python tests/manual/comprehensive_persona_test.py --category BRAVE_ROUTING

# Quick mode — core tests only, no MCP bank
python tests/manual/comprehensive_persona_test.py --quick

# No wallet tests (skip if wallet service not configured)
python tests/manual/comprehensive_persona_test.py --no-wallet

# Custom backend
python tests/manual/comprehensive_persona_test.py --base-url http://localhost:8000

Outputs
-------
  tests/manual/results/comprehensive_results.json   — full per-test data
  tests/manual/results/comprehensive_report.html    — visual HTML report
  tests/manual/results/comprehensive_summary.txt    — plain-text summary

Scoring
-------
Each response is scored across 7 dimensions (see scoring_engine.py):
  mcp_routing, persona_voice, no_leak, safety, factual_anchor,
  response_quality, emotional_fit

Composite score ≥ 0.60 AND check passes → PASS.
Grades: A(≥0.90) B(≥0.75) C(≥0.60) D(≥0.40) F(<0.40)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
import urllib.error
from collections.abc import Callable
from datetime import datetime

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

# ─── Local imports ─────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from api_client import check_backend, chat, create_session  # noqa: E402
from scoring_engine import score_response, aggregate_scores  # noqa: E402
from test_reporter import (  # noqa: E402
    print_progress, print_summary, save_json, save_html,
)
from test_bank_core import get_core_tests  # noqa: E402
from test_bank_mcp import get_mcp_tests, PERSONA_MCP_ACCESS  # noqa: E402

# ─── Constants ────────────────────────────────────────────────────────────────

RESULTS_DIR = os.path.join(_HERE, "results")

# Default personas to test (6 NEPHILIM + 2 Wanderers)
DEFAULT_PERSONAS = [
    "nephilim_eeva",
    "nephilim_aegis",
    "nephilim_aurora",
    "nephilim_cipher",
    "nephilim_solace",
    "nephilim_nyx",
    "Frieren",
    "Gojo",
]

# ANSI
_R = "\033[0m"
_BOLD = "\033[1m"
_CYAN = "\033[96m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_GREEN = "\033[92m"
_DIM = "\033[2m"


def _c(text: str, *codes: str) -> str:
    return "".join(codes) + text + _R


# ─── Session management ────────────────────────────────────────────────────────

class SessionPool:
    """Maintains one open session per persona to preserve context across tests."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self._sessions: dict[str, str] = {}

    def get(self, persona_key: str) -> str:
        if persona_key not in self._sessions:
            sid = create_session(persona_key, base_url=self.base_url)
            self._sessions[persona_key] = sid
        return self._sessions[persona_key]

    def reset(self, persona_key: str) -> str:
        """Force a new session (e.g., between test categories)."""
        sid = create_session(persona_key, base_url=self.base_url)
        self._sessions[persona_key] = sid
        return sid


# ─── Test execution ────────────────────────────────────────────────────────────

def run_test(
    test: dict,
    pool: SessionPool,
    base_url: str,
    timeout: int,
    verbose: bool,
) -> dict:
    """Execute one test against the live API and score the response."""
    persona = test["persona"]
    question = test["question"]

    try:
        sid = pool.get(persona)
        answer, elapsed, source, tools = chat(
            sid, persona, question,
            base_url=base_url, timeout=timeout,
        )
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode(errors="replace")[:200]
        except Exception:
            pass
        answer = f"HTTP {e.code}: {body}"
        elapsed = 0.0
        source = "error"
        tools = []
    except Exception as e:
        answer = f"ERROR: {e}"
        elapsed = 0.0
        source = "error"
        tools = []

    scoring = score_response(test, answer, source, elapsed)

    result = {
        **test,
        "answer": answer,
        "elapsed": round(elapsed, 2),
        "source": source,
        "tools": tools,
        **scoring,
    }

    if verbose:
        flags_str = " | ".join(scoring["flags"][:2]) if scoring["flags"] else ""
        q_short = question[:50]
        status_str = _c("PASS", _GREEN, _BOLD) if scoring["passed"] else _c("FAIL", _RED, _BOLD)
        print(
            f"  {status_str} [{scoring['grade']}] {scoring['score']:.2f} "
            f"({source}) {elapsed:.1f}s — {q_short}"
        )
        if flags_str:
            print(f"       {_c(flags_str, _YELLOW)}")

    return result


def _checkpoint(output_dir: str, all_results: list[dict], label: str = "") -> None:
    """Overwrite stable checkpoint files so partial results survive a crash."""
    if not all_results:
        return
    agg = aggregate_scores(all_results)
    cp_json = os.path.join(output_dir, "checkpoint.json")
    cp_html = os.path.join(output_dir, "checkpoint.html")
    # Write JSON atomically: write to .tmp then rename
    tmp = cp_json + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                {"results": all_results, "aggregate": agg, "checkpoint_at": label},
                f, indent=2, ensure_ascii=False,
            )
        os.replace(tmp, cp_json)
    except Exception as e:
        print(f"  {_c(f'checkpoint JSON write failed: {e}', _YELLOW)}")
    try:
        save_html(all_results, agg, cp_html)
    except Exception as e:
        print(f"  {_c(f'checkpoint HTML write failed: {e}', _YELLOW)}")
    tag = f" [{label}]" if label else ""
    print(f"  {_c(f'✓ checkpoint{tag} — {len(all_results)} results saved', _DIM)}", flush=True)


def run_persona(
    persona_key: str,
    tests: list[dict],
    all_results: list[dict],          # shared list — appended to directly
    pool: SessionPool,
    base_url: str,
    timeout: int,
    verbose: bool,
    total_so_far: int,
    grand_total: int,
    checkpoint_fn: "Callable[[], None] | None" = None,
    checkpoint_every: int = 20,
) -> int:
    """Run all tests for one persona, appending into all_results. Returns count_done."""
    current = total_so_far
    tests_this_call = 0

    # Group by category for better UX output
    categories_seen: set[str] = set()

    for test in tests:
        cat = test.get("category", "?")
        if cat not in categories_seen:
            categories_seen.add(cat)
            print(f"\n  {_c(f'── {cat}', _DIM)}")
            # Reset session at certain category boundaries to avoid contamination
            if cat in ("ADVERSARIAL", "SECURITY", "DRIFT"):
                pool.reset(persona_key)

        current += 1
        tests_this_call += 1
        print_progress(current, grand_total, test)
        result = run_test(test, pool, base_url, timeout, verbose=False)
        print_progress(current, grand_total, test, result)
        all_results.append(result)

        # Mid-persona checkpoint every N tests
        if checkpoint_fn and tests_this_call % checkpoint_every == 0:
            checkpoint_fn()

        # Small delay to avoid overwhelming the backend
        time.sleep(0.3)

    return current


# ─── Build test plan ───────────────────────────────────────────────────────────

def build_test_plan(
    personas: list[str],
    quick: bool,
    no_wallet: bool,
    category_filter: str | None,
    include_mcp: bool,
) -> dict[str, list[dict]]:
    """Build per-persona test list.

    Returns dict: persona_key → [test_dict, ...]
    """
    plan: dict[str, list[dict]] = {}

    for persona in personas:
        persona_tests: list[dict] = []
        seen_ids: set[str] = set()

        # Core behavioral tests
        core = get_core_tests(
            persona_filter=persona,
            category_filter=category_filter,
        )
        for t in core:
            if t["id"] not in seen_ids:
                seen_ids.add(t["id"])
                persona_tests.append(dict(t, persona=persona))

        # MCP routing tests
        if include_mcp and not quick:
            mcp = get_mcp_tests(
                persona_filter=persona,
                category_filter=category_filter,
            )
            for t in mcp:
                if no_wallet and t.get("category") == "WALLET_ROUTING":
                    continue
                if t["id"] not in seen_ids:
                    seen_ids.add(t["id"])
                    persona_tests.append(t)

        # Quick mode: cap at 30 tests, prioritise variety
        if quick:
            cat_quota: dict[str, int] = {}
            filtered: list[dict] = []
            for t in persona_tests:
                cat = t.get("category", "?")
                cat_quota[cat] = cat_quota.get(cat, 0)
                if cat_quota[cat] < 5:
                    filtered.append(t)
                    cat_quota[cat] += 1
                if len(filtered) >= 30:
                    break
            persona_tests = filtered

        plan[persona] = persona_tests

    return plan


# ─── Main entry ────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="NEPHILIM Comprehensive Persona Test Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--persona", "-p",
        help="Test only this persona key (e.g. nephilim_eeva)",
    )
    parser.add_argument(
        "--category", "-c",
        help="Only run tests in this category (e.g. BRAVE_ROUTING)",
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Quick mode: ~30 tests per persona, no MCP bank",
    )
    parser.add_argument(
        "--no-wallet",
        action="store_true",
        help="Skip wallet tests (if wallet service not configured)",
    )
    parser.add_argument(
        "--no-mcp",
        action="store_true",
        help="Skip MCP test bank, run core behavioral tests only",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Backend base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--timeout",
        type=int, default=120,
        help="Per-request timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed per-test output",
    )
    parser.add_argument(
        "--output-dir",
        default=RESULTS_DIR,
        help=f"Output directory for results (default: {RESULTS_DIR})",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip the confirmation prompt and run immediately",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    os.makedirs(args.output_dir, exist_ok=True)

    # ── Banner ────────────────────────────────────────────────────────────────
    print(_c("\n  ⬡ NEPHILIM COMPREHENSIVE PERSONA TEST SUITE", _BOLD, _CYAN))
    print(f"  Backend: {base_url}")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"  Started: {ts}\n")

    # ── Backend health check ──────────────────────────────────────────────────
    print("  Checking backend... ", end="", flush=True)
    ok, msg = check_backend(base_url)
    if not ok:
        print(_c(f"UNREACHABLE: {msg}", _RED, _BOLD))
        print("  Is the backend running? Try: python -m uvicorn src.coordinator.server:app --port 8000")
        return 1
    print(_c(f"OK ({msg})", _GREEN))

    # ── Determine personas to test ────────────────────────────────────────────
    if args.persona:
        personas = [args.persona]
    else:
        personas = DEFAULT_PERSONAS

    print(f"  Personas: {', '.join(_c(p, _CYAN) for p in personas)}")

    # ── Build test plan ───────────────────────────────────────────────────────
    plan = build_test_plan(
        personas=personas,
        quick=args.quick,
        no_wallet=args.no_wallet,
        category_filter=args.category,
        include_mcp=not args.no_mcp,
    )

    grand_total = sum(len(v) for v in plan.values())
    print(f"  Total tests planned: {_c(str(grand_total), _BOLD)}")
    for p, tests in plan.items():
        cats = {}
        for t in tests:
            cats[t.get("category", "?")] = cats.get(t.get("category", "?"), 0) + 1
        cat_str = ", ".join(f"{c}:{n}" for c, n in sorted(cats.items()))
        print(f"  {p:<26} {len(tests):3d} tests  ({cat_str})")

    print()
    if not args.yes:
        confirm = input("  Proceed? [Y/n]: ").strip().lower()
        if confirm and confirm != "y":
            print("  Aborted.")
            return 0

    # ── Run tests ─────────────────────────────────────────────────────────────
    pool = SessionPool(base_url)
    all_results: list[dict] = []
    total_done = 0

    # Checkpoint lambda — called every 20 tests AND after every persona
    def do_checkpoint(label: str = "") -> None:
        _checkpoint(args.output_dir, all_results, label)

    for persona in personas:
        tests = plan.get(persona, [])
        if not tests:
            continue

        acc = PERSONA_MCP_ACCESS.get(persona, {})
        mcp_label = ", ".join(
            k for k, v in [("brave", acc.get("brave")), ("mongodb", acc.get("mongodb")), ("wallet", acc.get("wallet"))]
            if v
        ) or "none"

        print(f"\n{'─' * 80}")
        print(f"  {_c(persona, _CYAN, _BOLD)}  [{mcp_label}]  {len(tests)} tests")
        print(f"{'─' * 80}")

        persona_start = time.time()
        count_before = len(all_results)
        try:
            total_done = run_persona(
                persona_key=persona,
                tests=tests,
                all_results=all_results,
                pool=pool,
                base_url=base_url,
                timeout=args.timeout,
                verbose=args.verbose,
                total_so_far=total_done,
                grand_total=grand_total,
                checkpoint_fn=lambda: do_checkpoint(f"mid-{persona}"),
                checkpoint_every=20,
            )
        except KeyboardInterrupt:
            print(f"\n  {_c('Interrupted by user', _YELLOW)} — saving partial results...")
            do_checkpoint(f"interrupted-{persona}")
            break

        persona_time = time.time() - persona_start
        persona_results = all_results[count_before:]
        passed = sum(1 for r in persona_results if r.get("passed", False))
        avg_score = sum(r.get("score", 0) for r in persona_results) / max(len(persona_results), 1)

        print(f"\n  → {persona}: {_c(str(passed), _GREEN)}/{len(persona_results)} pass "
              f"| avg score {avg_score:.3f} | {persona_time:.0f}s")

        # Checkpoint after each persona (stable overwrite + per-persona snapshot)
        do_checkpoint(persona)
        _snap = os.path.join(args.output_dir, f"persona_{persona}.json")
        save_json(persona_results, _snap)

    # ── Final report ──────────────────────────────────────────────────────────
    if not all_results:
        print("  No results collected.")
        return 1

    aggregate = aggregate_scores(all_results)
    print_summary(aggregate, verbose=True)

    _ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(args.output_dir, f"comprehensive_results_{_ts}.json")
    html_path = os.path.join(args.output_dir, f"comprehensive_report_{_ts}.html")

    # Also write stable "latest" files
    latest_json = os.path.join(args.output_dir, "latest.json")
    latest_html = os.path.join(args.output_dir, "latest.html")

    save_json(all_results, json_path)
    save_html(all_results, aggregate, html_path)

    # Enrich results with aggregate for "latest" files
    enriched = {"results": all_results, "aggregate": aggregate, "generated": _ts}
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=2, ensure_ascii=False)
    save_html(all_results, aggregate, latest_html)

    print(f"\n  Reports written:")
    print(f"    JSON  → {json_path}")
    print(f"    HTML  → {html_path}")
    print(f"    Open: file:///{html_path.replace(os.sep, '/')}")

    # Summary txt
    txt_path = os.path.join(args.output_dir, f"comprehensive_summary_{_ts}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"NEPHILIM Comprehensive Test Summary\n")
        f.write(f"Generated: {_ts}\n")
        f.write(f"{'=' * 60}\n")
        f.write(f"Total:    {aggregate['total']}\n")
        f.write(f"Passed:   {aggregate['passed']}\n")
        f.write(f"Failed:   {aggregate['failed']}\n")
        f.write(f"Pass rate:{aggregate['pass_rate']*100:.1f}%\n")
        f.write(f"Avg score:{aggregate['avg_score']:.3f}\n\n")
        f.write("Per-persona:\n")
        for p, d in aggregate.get("by_persona", {}).items():
            f.write(f"  {p:<26} {d['pass_rate']*100:5.1f}%  score:{d['avg_score']:.3f}  n={d['total']}\n")
        f.write("\nPer-category:\n")
        for c, d in sorted(aggregate.get("by_category", {}).items()):
            f.write(f"  {c:<28} {d['pass_rate']*100:5.1f}%  score:{d['avg_score']:.3f}  n={d['total']}\n")
    print(f"    TXT   → {txt_path}")

    passed_total = aggregate["passed"]
    failed_total = aggregate["failed"]
    overall_pass = aggregate["pass_rate"] >= 0.70

    print(f"\n  Final verdict: {_c('PASS', _GREEN, _BOLD) if overall_pass else _c('FAIL', _RED, _BOLD)} "
          f"({passed_total}/{passed_total + failed_total} = {aggregate['pass_rate']*100:.1f}%)\n")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  Aborted.")
        sys.exit(130)
