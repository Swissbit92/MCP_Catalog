# tests/evaluation/eval_tool_firing.py
"""Tool-firing eval for the ADR-008 tool brain.

Answers the question the soak could not: *when a turn needs a tool, does one
actually fire — and is it the native tool brain or the legacy floor doing the
work?* Drives a fixed golden set (``tool_firing_cases.py``) through the live
session API and scores the observable outcome of each turn.

Why this exists: ``TOOL_BRAIN_ENABLED=true`` has been live since 2026-07-05 but
organic traffic never materialised (24 tool_brain messages, all from the
live-test day itself), so ROADMAP item 21 accrued elapsed time rather than
evidence. This harness generates the traffic instead of waiting for it, and its
IMAGE/VIDEO buckets are the decider for ROADMAP item 45 (media-aware fallback
floor), which is explicitly gated on "build only if soak shows media queries
slipping".

What it measures, per case, from ``ResponseMetadata``:

* **correct**       — did ``source_type`` land in the case's ``expect`` set?
* **native fire**   — was it ``tool_brain`` (model decided) rather than
                      ``brave_mcp`` (deterministic floor caught it)?
* **tool match**    — for media cases, was the expected tool the one used?
* **false positive**— did a chitchat/wallet turn fire a tool it must not?

The headline numbers are per-bucket accuracy and the NATIVE-FIRE RATE. High
accuracy with a low native-fire rate means the legacy floor is carrying the
system and the tool brain is decorative — a materially different conclusion
from high accuracy with a high native-fire rate, and one the raw
``source_type`` counts in the database cannot distinguish.

Usage:
    # live scorecard (needs Ollama + the backend on :8000)
    .venv/bin/python tests/evaluation/eval_tool_firing.py

    # live test via pytest (skips cleanly when Ollama is unreachable)
    .venv/bin/python -m pytest tests/evaluation/eval_tool_firing.py -v

    # headless guards on the case set + scoring math (run in the normal suite)
    .venv/bin/python -m pytest tests/evaluation/test_tool_firing_cases.py -v
"""

from __future__ import annotations

import json
import logging
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
# Own directory too, so the sibling case set imports whether this module is
# collected by pytest or run directly as a script.
sys.path.insert(0, str(Path(__file__).parent))

from tool_firing_cases import (  # noqa: E402
    BUCKETS,
    CHITCHAT,
    GOLDEN_CASES,
    GROUNDED,
    IMAGE_FIND,
    NATIVE,
    VIDEO_FIND,
    WALLET,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

BACKEND = os.environ.get("NEPHILIM_BASE_URL", "http://127.0.0.1:8000")
# Generation is the bottleneck (~16 tok/s) and OLLAMA_NUM_PARALLEL=1 serialises
# every call, so a slow turn is normal, not a failure. Budget generously.
TURN_TIMEOUT_S = int(os.environ.get("TOOL_FIRING_TIMEOUT", "180"))


# --- result model ------------------------------------------------------------


@dataclass
class CaseResult:
    """Outcome of one golden case against the live stack."""

    case_id: str
    bucket: str
    query: str
    source_type: str
    tools_used: list[str] = field(default_factory=list)
    correct: bool = False
    native_fire: bool = False
    tool_match: bool | None = None  # None when the case declares no expected tool
    error: str | None = None

    @property
    def grounded(self) -> bool:
        return self.source_type in GROUNDED


@dataclass
class Scorecard:
    """Aggregate over all cases, sliced the way the ROADMAP items need."""

    results: list[CaseResult]

    def _subset(self, bucket: str | None = None) -> list[CaseResult]:
        ok = [r for r in self.results if r.error is None]
        return [r for r in ok if bucket is None or r.bucket == bucket]

    def accuracy(self, bucket: str | None = None) -> float:
        rs = self._subset(bucket)
        return (sum(r.correct for r in rs) / len(rs)) if rs else 0.0

    def native_fire_rate(self, bucket: str | None = None) -> float:
        """Share of GROUNDED turns the model drove natively (vs the floor).

        Denominator is grounded turns only — a chitchat turn that correctly
        fired nothing is not evidence about native calling either way, and
        including it would silently inflate the rate.
        """
        rs = [r for r in self._subset(bucket) if r.grounded]
        return (sum(r.native_fire for r in rs) / len(rs)) if rs else 0.0

    def tool_match_rate(self, bucket: str | None = None) -> float:
        rs = [r for r in self._subset(bucket) if r.tool_match is not None]
        return (sum(bool(r.tool_match) for r in rs) / len(rs)) if rs else 0.0

    def false_positives(self) -> list[CaseResult]:
        """Turns that fired a tool when they must not have."""
        return [
            r
            for r in self._subset()
            if r.bucket in (CHITCHAT, WALLET) and r.source_type in GROUNDED
        ]

    def wallet_leaks(self) -> list[CaseResult]:
        """Wallet turns that reached the model-decided native surface.

        TB5 scoped the tool brain to NEEDS_WEB_SEARCH so this should be
        structurally impossible; any hit is a safety regression, not a miss.
        """
        return [r for r in self._subset(WALLET) if r.source_type == "tool_brain"]

    def errors(self) -> list[CaseResult]:
        return [r for r in self.results if r.error is not None]

    def render(self) -> str:
        lines = [
            "",
            "=" * 74,
            "TOOL-FIRING SCORECARD (ADR-008 tool brain)",
            "=" * 74,
            f"{'bucket':<16} {'n':>3} {'accuracy':>9} {'native':>8}  notes",
            "-" * 74,
        ]
        for b in BUCKETS:
            rs = self._subset(b)
            if not rs:
                continue
            note = ""
            if b in (IMAGE_FIND, VIDEO_FIND):
                note = f"tool match {self.tool_match_rate(b):.0%}"
            elif b in (CHITCHAT, WALLET):
                note = "must not fire"
            lines.append(
                f"{b:<16} {len(rs):>3} {self.accuracy(b):>8.0%} "
                f"{self.native_fire_rate(b):>7.0%}  {note}"
            )
        lines += [
            "-" * 74,
            f"{'OVERALL':<16} {len(self._subset()):>3} {self.accuracy():>8.0%} "
            f"{self.native_fire_rate():>7.0%}",
            "",
        ]

        fps = self.false_positives()
        lines.append(f"False positives (fired when it must not): {len(fps)}")
        for r in fps:
            lines.append(f"  ✗ [{r.case_id}] {r.query!r} -> {r.source_type}")

        leaks = self.wallet_leaks()
        lines.append(f"Wallet leaks to native surface: {len(leaks)}")
        for r in leaks:
            lines.append(f"  ⚠ [{r.case_id}] {r.query!r} -> {r.source_type}")

        misses = [r for r in self._subset() if not r.correct]
        lines.append(f"Misses: {len(misses)}")
        for r in misses:
            lines.append(
                f"  ✗ [{r.case_id}/{r.bucket}] {r.query!r} -> {r.source_type} "
                f"tools={r.tools_used}"
            )

        errs = self.errors()
        if errs:
            lines.append(f"Errors (excluded from rates): {len(errs)}")
            for r in errs:
                lines.append(f"  ! [{r.case_id}] {r.error}")

        lines.append("=" * 74)
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "overall": {
                "n": len(self._subset()),
                "accuracy": round(self.accuracy(), 4),
                "native_fire_rate": round(self.native_fire_rate(), 4),
                "false_positives": len(self.false_positives()),
                "wallet_leaks": len(self.wallet_leaks()),
                "errors": len(self.errors()),
            },
            "buckets": {
                b: {
                    "n": len(self._subset(b)),
                    "accuracy": round(self.accuracy(b), 4),
                    "native_fire_rate": round(self.native_fire_rate(b), 4),
                    "tool_match_rate": round(self.tool_match_rate(b), 4),
                }
                for b in BUCKETS
                if self._subset(b)
            },
            "cases": [
                {
                    "id": r.case_id,
                    "bucket": r.bucket,
                    "source_type": r.source_type,
                    "tools_used": r.tools_used,
                    "correct": r.correct,
                    "native_fire": r.native_fire,
                    "tool_match": r.tool_match,
                    "error": r.error,
                }
                for r in self.results
            ],
        }


# --- live driver -------------------------------------------------------------


def _post(path: str, payload: dict, timeout: int) -> dict:
    req = urllib.request.Request(
        f"{BACKEND}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _delete(path: str, timeout: int = 15) -> None:
    req = urllib.request.Request(f"{BACKEND}{path}", method="DELETE")
    try:
        urllib.request.urlopen(req, timeout=timeout).close()
    except Exception as e:  # cleanup is best-effort — never fail a run on it
        logger.debug(f"cleanup failed for {path}: {e}")


def backend_reachable() -> bool:
    try:
        urllib.request.urlopen(f"{BACKEND}/personas", timeout=5).close()
        return True
    except Exception:
        return False


def run_case(case: dict, timeout: int = TURN_TIMEOUT_S) -> CaseResult:
    """Drive one case through a throwaway session and score the outcome."""
    result = CaseResult(
        case_id=case["id"],
        bucket=case["bucket"],
        query=case["query"],
        source_type="",
    )
    session_id = None
    try:
        session = _post(
            "/sessions",
            {"persona_key": case["persona"], "title": f"tool-firing {case['id']}"},
            timeout=15,
        )
        session_id = session.get("session_id") or session.get("id")
        if not session_id:
            result.error = f"no session_id in {session!r}"
            return result

        body = _post(
            f"/sessions/{session_id}/chat",
            {"message": case["query"], "persona": case["persona"]},
            timeout=timeout,
        )
        meta = body.get("metadata") or {}
        result.source_type = meta.get("source_type", "")
        result.tools_used = meta.get("tools_used") or []
        result.correct = result.source_type in case["expect"]
        result.native_fire = result.source_type in NATIVE
        if "expect_tool" in case:
            result.tool_match = case["expect_tool"] in result.tools_used
    except urllib.error.HTTPError as e:
        result.error = f"HTTP {e.code}"
    except Exception as e:
        result.error = f"{type(e).__name__}: {e}"
    finally:
        if session_id:
            _delete(f"/sessions/{session_id}")
    return result


def run_eval(cases: list[dict] | None = None) -> Scorecard:
    """Run the full golden set serially and return the scorecard.

    Serial by necessity, not oversight: the coordinator runs
    ``OLLAMA_NUM_PARALLEL=1`` and serialises LLM calls behind a lock, so
    concurrency here would queue at the backend while making per-turn timings
    meaningless.
    """
    cases = cases if cases is not None else GOLDEN_CASES
    results = []
    for i, case in enumerate(cases, 1):
        logger.info(f"[{i}/{len(cases)}] {case['bucket']:<15} {case['query'][:52]!r}")
        r = run_case(case)
        flag = "ok " if r.correct else "MISS"
        if r.error:
            flag = "ERR "
        logger.info(f"        -> {flag} source={r.source_type or '-'} tools={r.tools_used}")
        results.append(r)
    return Scorecard(results=results)


# --- pytest surface ----------------------------------------------------------
#
# Only the LIVE test lives here. The headless guards on the case set and the
# scoring math live in test_tool_firing_cases.py so they are auto-collected.


@pytest.mark.requires_ollama
def test_tool_firing_live():
    """Live: run the golden set and assert the safety floor holds.

    Deliberately asserts only the non-negotiables — no wallet leak to the
    native surface, and no hard errors. Accuracy/native-fire are REPORTED,
    not asserted: this harness exists to establish the baseline, and a
    threshold invented before the first measurement would be arbitrary.
    """
    if not backend_reachable():
        pytest.skip(f"nephilim backend not reachable at {BACKEND}")

    card = run_eval()
    logger.info(card.render())

    assert not card.wallet_leaks(), (
        f"wallet turns reached the native tool surface: "
        f"{[r.case_id for r in card.wallet_leaks()]}"
    )
    assert len(card.errors()) <= 1, f"too many hard errors: {card.errors()}"


if __name__ == "__main__":
    if not backend_reachable():
        logger.error(f"backend not reachable at {BACKEND} — is com.nephilim.backend up?")
        raise SystemExit(1)

    scorecard = run_eval()
    print(scorecard.render())

    out = Path(__file__).parent / "tool_firing_results.json"
    out.write_text(json.dumps(scorecard.to_dict(), indent=2) + "\n")
    print(f"wrote {out}")
