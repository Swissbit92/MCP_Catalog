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

## 2026-07-16 — ADR-011 conversation-control commands: one contract, two clients

- **What:** Added companion/RP verbs (regenerate, continue, undo, /sys narrate, /note, /impersonate, /whoami, /help) required to work identically in BOTH the Telegram gateway and the React UI. Built as shared coordinator session-API endpoints; both clients are thin callers. 5 QA-gated phases, one branch, merged to dev (coordinator 2030 / gateway 113 / React build green).
- **Learned:** "Works in both clients" is an architecture constraint, not a feature detail — it forces the stateful logic into the *server*, and reframes the gateway's "zero coordinator changes" invariant into "thin client of a session API the coordinator may extend for all clients." The spirit (no logic/secrets/tool-surface in the gateway) survives; the letter doesn't.
- **Learned:** The cleanest reuse seam was adding two default-True flags to `handle_session_chat` (`persist_user`, `run_post_turn_updates`) so regenerate/continue re-run the exact pipeline (first-person, groundedness gate, multi-message shaping) without re-persisting the user turn or double-counting progression — zero change for the 25 existing callers, no parallel LLM path.
- **Learned (mistake caught):** An alembic migration smoke-test that set `sqlalchemy.url` via `Config.set_main_option` silently ran against the LIVE `data/chats.db`, because `alembic/env.py` hardcodes the path from `COORDINATOR_DB_PATH` (env var) and ignores the config URL. The upgrade landed on prod; caught immediately via a post-run version check, downgraded prod back to `4memory_facts`, and re-tested correctly by setting `COORDINATOR_DB_PATH` to a temp file. **Always drive this repo's alembic tests through `COORDINATOR_DB_PATH`, never `sqlalchemy.url`** — and verify prod DB version after any migration command that could have hit it.
- **Learned:** A new `messages.role` value ('narrator') is a cross-cutting change — four separate sites did a binary `== "assistant" else "user"` collapse (chat history render, fact extractor, triplet extractor, tool-brain) that would silently mislabel it. Grep every role-switch before adding a role.
- **Apply:** For any "same behavior across clients" feature, put the logic behind the shared API and make clients dumb. Gate migration tests on the repo's real DB-path mechanism. Live enablement here still OWES: `alembic upgrade head` + restart backend + restart gateway + rebuild/redeploy frontend (nothing deploys on merge).

## 2026-07-16 — Editing an existing persona JSON needs a backend restart to take effect

- **What:** User edited `personas/gwen.json` (new lore wording — "cock" replacing the old "shaft") but Gwen kept speaking in her pre-edit persona. The edit was correctly on disk; the running always-on backend just never re-read it.
- **Learned:** Two process/disk caches shadow a live persona edit. (1) `prompt_builder._build_system_prompt_lean()` is `@lru_cache(maxsize=32)` keyed only on the persona selector — the fully-assembled system prompt is memoized for the life of the process, and nothing in production calls `build_system_prompt.cache_clear()` (only tests do). `persona_loader` re-reads the JSON fresh every request, but that fresh card never reaches the cached builder. (2) The `<identity>` block is filled from a disk-cached CV summary (`personas/_summaries/{Key}.json`) keyed by a SHA1 fingerprint of the card (excluding `emoji`/`voice_signature`); it self-invalidates on hash mismatch, but is only ever regenerated *inside* the lru_cached builder, so while the process runs it never refreshes either. Since the backend runs under launchd `KeepAlive`, neither cache clears on its own.
- **Learned:** CLAUDE.md's "persona auto-discovered on next load — no restart needed" applies to *discovering a new* persona file, NOT to *editing an existing* one whose prompt is already memoized. Easy to misread as "all persona changes are hot."
- **Apply:** After editing any existing persona JSON, restart the backend: `launchctl kickstart -k gui/$(id -u)/com.nephilim.backend`. That clears the lru_cache and, because the edited card's fingerprint no longer matches the cached summary, forces the CV summary to regenerate from the new lore at boot (`startup.ensure_all_summaries_serialized`). Optionally `rm personas/_summaries/{Key}.json` first as belt-and-suspenders. The Telegram gateway relays to this same backend, so the one restart covers both web and Telegram. Verify: new PID + the regenerated `_summaries/{Key}.json` `hash` matches the current card's fingerprint.

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
