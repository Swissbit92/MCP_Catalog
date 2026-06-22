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
