#!/usr/bin/env python3
"""
Profile the per-turn prompt size and PREFILL cost for a persona chat turn.

Why: a single E.E.V.A. chat turn was observed at ~31s, of which ~29s was NOT
token generation but PREFILL of a large system prompt. This script quantifies:

  1. SIZE      — how many tokens the system prompt injects (total + breakdown),
                 so we know how much is trimmable.
  2. PREFILL   — the real prompt-processing time, measured via Ollama's own
                 `prompt_eval_count` / `prompt_eval_duration` (exact, not tiktoken).
  3. CACHE     — whether Ollama REUSES the static system-prompt prefix across
                 turns. This is the architectural smoking gun: if turn-2 with the
                 same prefix still reports a full `prompt_eval_count`, the prefix
                 cache is busted and we re-prefill everything every turn.

Read-only: does NOT change any app behavior. Talks to the already-running Ollama.

Usage:
    .venv/bin/python scripts/profiling/profile_prompt_prefill.py [persona_key]
    # default persona_key = nephilim_eeva
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

# Repo root on path so `src.coordinator...` imports resolve when run from anywhere.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.coordinator.config import get_settings  # noqa: E402
from src.coordinator.llm_client import estimate_tokens  # noqa: E402
from src.coordinator.prompt_builder import build_system_prompt  # noqa: E402

try:
    from langchain_core.prompts import ChatPromptTemplate
    _HAVE_LC = True
except Exception:  # pragma: no cover
    _HAVE_LC = False


def _render_like_app(system: str, user: str) -> str:
    """Render system+user exactly as LLMCompletionService.complete() does."""
    if _HAVE_LC:
        template = ChatPromptTemplate.from_messages([("system", "{system}"), ("user", "{user}")])
        return template.format_prompt(system=system, user=user).to_string()
    return f"System: {system}\nHuman: {user}"


def _ollama_generate(base: str, model: str, prompt: str, num_ctx: int) -> dict:
    """Call Ollama /api/generate with num_predict=1 to isolate PREFILL.

    Returns the raw JSON (has prompt_eval_count, prompt_eval_duration in ns).
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": -1,
        "options": {"num_ctx": num_ctx, "num_predict": 1, "temperature": 0},
    }
    req = urllib.request.Request(
        f"{base.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read())


def _ns_to_s(ns: int | None) -> float:
    return (ns or 0) / 1e9


def _section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def main() -> None:
    persona_key = sys.argv[1] if len(sys.argv) > 1 else "nephilim_eeva"
    settings = get_settings()
    base = settings.ollama.base
    model = settings.ollama.model  # PERSONA_MODEL alias resolves here
    num_ctx = settings.ollama.context_window

    _section(f"PROMPT SIZE — persona '{persona_key}'  (model {model}, num_ctx {num_ctx})")

    system = build_system_prompt(persona_key)

    # Best-effort wallet ground-truth injection (EEVA-class personas; see chat.py:124).
    wallet_state = ""
    try:
        from src.coordinator.services.query_handler_service import QueryHandlerService
        wallet_state = QueryHandlerService._build_wallet_state_context("default_user") or ""
    except Exception as e:  # pragma: no cover - wallet subsystem may be offline
        print(f"  (wallet ground-truth injection skipped: {type(e).__name__})")
    if wallet_state:
        system = f"{system}\n{wallet_state}"

    sys_tokens = estimate_tokens(system)
    print(f"  System prompt:        {len(system):>8,} chars   ~{sys_tokens:>6,} tokens (tiktoken est.)")
    if wallet_state:
        print(f"    └─ wallet block:    {len(wallet_state):>8,} chars   ~{estimate_tokens(wallet_state):>6,} tokens (DYNAMIC — live numbers, busts cache from here on)")

    # Static reference content that could move ON-DEMAND (lore-as-a-skill idea):
    persona_file = REPO_ROOT / "personas" / f"{persona_key}.json"
    if persona_file.exists():
        ptxt = persona_file.read_text()
        print(f"  Persona JSON (raw):   {len(ptxt):>8,} chars   ~{estimate_tokens(ptxt):>6,} tokens")
    lore_dir = REPO_ROOT / "docs" / "lore" / "wiki"
    if lore_dir.exists():
        lore_txt = "".join(p.read_text(errors="ignore") for p in lore_dir.rglob("*.md"))
        print(f"  Lore wiki (on disk):  {len(lore_txt):>8,} chars   ~{estimate_tokens(lore_txt):>6,} tokens   ← candidate for on-demand 'skill' loading")

    print(f"\n  As % of {num_ctx}-token context window: {round(100*sys_tokens/num_ctx,1)}%")

    # --- Empirical prefill + cache-reuse probe ----------------------------------
    _section("PREFILL + CACHE-REUSE PROBE  (Ollama prompt_eval_count / duration)")
    print("  Calling Ollama /api/generate with num_predict=1 to isolate prefill...\n")

    p1 = _render_like_app(system, "What is your name?")
    # Same static system prefix, DIFFERENT trailing user message — tests prefix reuse.
    p2 = _render_like_app(system, "Tell me one short fact about yourself, briefly.")

    try:
        r1 = _ollama_generate(base, model, p1, num_ctx)
        r2 = _ollama_generate(base, model, p2, num_ctx)
    except Exception as e:
        print(f"  ✗ Ollama call failed ({type(e).__name__}: {e}).")
        print(f"    Is Ollama up at {base} and the model pulled?")
        return

    def _row(label: str, r: dict) -> None:
        pe_count = r.get("prompt_eval_count")
        pe_dur = _ns_to_s(r.get("prompt_eval_duration"))
        load = _ns_to_s(r.get("load_duration"))
        pps = (pe_count / pe_dur) if (pe_count and pe_dur) else 0
        print(f"  {label:<22} prompt_eval_count={pe_count!s:>6}  prefill={pe_dur:>6.2f}s  "
              f"({pps:>6.0f} tok/s)  load={load:>5.2f}s")

    _row("Turn 1 (cold):", r1)
    _row("Turn 2 (same prefix):", r2)

    pe1 = r1.get("prompt_eval_count") or 0
    pe2 = r2.get("prompt_eval_count") or 0
    d1 = _ns_to_s(r1.get("prompt_eval_duration"))
    d2 = _ns_to_s(r2.get("prompt_eval_duration"))

    _section("VERDICT")
    if pe2 and pe2 < pe1 * 0.5:
        print(f"  ✓ PREFIX CACHE IS WORKING: turn-2 re-prefilled only {pe2} tokens "
              f"(vs {pe1} cold) — {round(d1-d2,2)}s saved. The static prefix is reused.")
        print("    → Latency lever is mostly the COLD first turn + dynamic tail. Trimming")
        print("      static content still helps the first turn; protect prefix stability.")
    else:
        print(f"  ✗ PREFIX CACHE NOT REUSED: turn-2 still re-prefilled {pe2} tokens "
              f"(cold was {pe1}). Every turn pays ~{d2:.1f}s of prefill.")
        print("    → BIG lever: make the static persona/lore prefix stable & cacheable,")
        print("      and/or move large static blocks (lore) to on-demand loading.")
    print()


if __name__ == "__main__":
    main()
