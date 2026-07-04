---
title: Lessons Learned
status: active
created: 2026-04-19
last_reviewed_on: 2026-06-22
review_in: 12 months
applies_to: nephilim
---

# Lessons Learned

Append-only, dated entries. Newest first. Each entry: what happened, what we learned, how to apply going forward.

## 2026-07-04 — Anti-hallucination guards can all be bypassed by one upstream decision

- **What:** A real Telegram conversation surfaced E.E.V.A. confidently fabricating a FIFA World Cup match result, then reinforcing her own fabrication when the user "confirmed" it. Traced via `data/chats.db` message `source_type` per turn (not guesswork) to five distinct causes across routing, query resolution, and grounding.
- **Learned:** All three existing anti-hallucination guards ("no results → I don't know", "LLM skipped tool → I don't know", relevance gate) lived entirely inside `tool_calling_service.py::complete_with_tools()` — code that is architecturally unreachable once the upstream intent classifier decides `NEEDS_NEITHER`. A defense-in-depth design is only as deep as its *shallowest* entry point; if one upstream router decision can route around the entire guard chain, the guards provide no defense for that path at all. The fix (ADR-007) had to be a mechanism decoupled from the router — checking the drafted *output*, not gating based on what the router decided was needed.
- **Learned:** An eval sample deliberately designed to test a risk ("false-abstention on a lexically-distant-but-relevant result") turned out to sit 0.011 cosine away from an actual junk sample in the same corpus, once run against a real embedder — confirming the risk was real, not hypothetical, before any flag got flipped. Building the adversarial case into the eval set *before* tuning, rather than tuning first and hoping, is what surfaced this.
- **Learned:** A "regression test" for a not-yet-fixed bug should still be written and run — `pytest.mark.xfail(strict=True)` locks in the exact failure mode as a named, dated artifact and automatically flips to a hard failure (XPASS) the moment someone's fix accidentally already resolves it, which is a stronger signal than a comment or a TODO.
- **Apply:** When auditing any multi-layer guard system, ask "what does the FIRST decision point route around?" before trusting that downstream layers provide defense-in-depth. When building an eval corpus for a new gate, deliberately include the adversarial case the gate is *supposed* to almost get wrong — a corpus of only easy cases validates nothing.

## 2026-07-04 — Telegram gateway: built standalone, folded in same session

- **What:** Built `services/telegram-gateway/` as a standalone `eeva-telegram` repo first, then folded it into nephilim as a subsystem within the same session, once the architecture question was pressed on.
- **Learned:** The whole feature was a transport problem, not an agent problem — nephilim's non-streaming `POST /sessions/{id}/chat` maps 1:1 onto Telegram's `sendMessage`, and the HERMES safety middleware (inside the shared `chat()` function, not the route layer) is inherited automatically by any new client, so zero backend changes were needed. Separately: "separate repo vs. subfolder" isn't really about blast-radius or dependency isolation (a subfolder with its own venv/tests/launchd gives you both) — those only require *process* separation. The real axis is whether the new thing is an independent product (like `eeva-dca`/`eeva-exec`, which trade on KuCoin and would exist regardless of nephilim) or purely a client of this repo's own API contract. For the latter, same-repo/same-PR changes prevent client/server drift structurally; cross-repo bookkeeping doesn't.
- **Apply:** Before creating a new repo for a "client of X", ask whether it's an independent product or purely a consumer of X's own contract. Only the former justifies a separate repo by default.

## 2026-06-22 — Test-coverage push 41%→63% (gate now passes)

- **What:** Raised headless coverage to **63%**, clearing the `--cov-fail-under=60` gate. (The "23%" starting figure was a `--collect-only` artifact; real baseline was 41%.) Added ~1,060 tests across repositories, pure-logic modules, jupiter strategies, and FastAPI routes (TestClient). Suite 321 → ~1,420 collected; final headless run 1381 passed / 0 failed / 38 skipped / 5 xfailed.
- **Learned:**
  - Repositories self-init schema via `_ensure_tables()` on construction → trivially testable with a `tmp_path` SQLite db (no manual schema). Exception: `UserProfileRepository` relies on Alembic, so its test must provision tables.
  - **Python 3.12 gotcha:** `asyncio.get_event_loop().run_until_complete()` in a test helper passes alone but raises "no current event loop" *in-suite* (once an earlier async test closes the thread loop). Use `asyncio.run(coro)`. Classic pass-alone/fail-in-suite.
  - Adding a stray `tests/backend/coordinator/__init__.py` (when parent dirs lack `__init__.py`) breaks `sys.path`-style imports in older test files → collection errors. Don't add package files to this test tree.
  - `--collect-only` coverage is meaningless (imports only); always measure with tests actually running.
  - To mock a function imported *locally inside* a function body, patch it at its source module, not on the importing module (e.g. `has_active_wallet_flow` patched at `services.query_handler_service`, not `routes.chat`).
- **Bugs surfaced AND fixed** (same day; the xfail tests now pass normally): `get_resonance_history` tie ordering (`, id DESC`); `wallet_registry` `soft_delete_*` double-delete returning `True` (now `cursor.rowcount`); `message_processing_service` dead 3-message branch (non-greedy `(.*?)`→greedy `(.*)`). Still outstanding: widespread `datetime.utcnow()` deprecation.
- **Apply:** Mock the LLM/Docker/Solana boundary; mark anything making a live call `requires_ollama`/`requires_api_key`/`requires_docker` so `tests/conftest.py` auto-skips it headless. Verify new async-using test files both alone AND after another async test.

## 2026-04-19 — Repository initialized

- **What:** `/cms init` scaffolded the standard doc set.
- **Learned:** Creation-time enforcement is the strongest lever for doc hygiene (Nx, Kubernetes OWNERS, Backstage).
- **Apply:** Any new repo starts here. Retroactive audits drift; creation-time templates don't.
