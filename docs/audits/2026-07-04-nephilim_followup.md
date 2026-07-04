---
title: "Repo Audit — nephilim — 2026-07-04 (follow-up, post tranche-1 + step 7)"
status: active
created: 2026-07-04
last_reviewed_on: 2026-07-04
review_in: 3 months
applies_to: nephilim
---

# Repo Health Audit — nephilim (follow-up)

**Date:** 2026-07-04 (2nd pass) · **Lens version:** 1 · **Metrics:** 590 tracked files, 81,582 source lines (was 83,014 → −1,432)

> This is a **same-day re-audit** run after tranche-1 (audit steps 1–6) and step 7 (god-function decomposition) landed on `dev`. It supersedes the morning baseline [`2026-07-04-nephilim.md`](2026-07-04-nephilim.md) as the head-of-trend; the next quarterly run diffs against *this* file. Lens ruler unchanged (v1) — the trend is honest.

## 1. Score

| | This audit | Last audit (2026-07-04 AM) | Δ |
|---|---|---|---|
| **Anchor score** (deterministic, trend-grade) | **45/100** | 42/100 | **+3** |
| Lens quality read (coarse, directional) | ~74/100 | ~70/100 | +4 |

> The **anchor** is reproducible from hard facts; trend it. The **lens read** is holistic judgment (±5). The +3 anchor move *understates* the real work done — see the bottleneck note.

**Anchor breakdown:** start 100 − god_files 40 (capped) − artifacts 0 − gitignore_gaps 2 − large_files 10 − dead_candidates 3 = **45**

**Primary bottleneck — why the anchor moved only +3 despite two real cleanup tranches:** the entire +3 came from `dead_candidate_penalty` (6→3, from tranche-1's dead-code deletions). The **god-file penalty stayed capped at 40** because god-files only dropped 29→25 — still far above the cap threshold. Two nuances the anchor can't see:
> 1. **`config.py` (802 lines) and `prompt_builder.py` (920→448) left the god-file list** (config split into a package; prompt_builder had its dead legacy deleted) — real wins, but not enough to uncap the penalty.
> 2. **`chat_session_service.py` GREW 949 → 1035 lines** and is now the *single largest* god-file. Decomposing `handle_session_chat` into ~9 phase functions + two dataclasses *in the same file* eliminated the god-**function** (a genuine quality win the lens read credits) but added line count — the anchor measures file size, not function complexity. The follow-up is to extract the phases into a `services/chat_session/` **package**.
>
> Net: the honest structural debt is now concentrated in **three files that need file-level (not just function-level) splits** — `chat_session_service.py` (1035), `query_handler_service.py` (852), `startup.py` (636) — and `startup.py` (the DI hub) is the keystone. The anchor will move meaningfully once several of the 25 god-files drop under 500.

## 2. Since last audit

- **Closed (11):**
  - Security `str(e)` leak on `routes/wallet.py` financial endpoints → `type(e).__name__` (tranche-1 #1).
  - `docker-compose.yml` committed default JWT secret → force-required `${VAR:?}` (tranche-1 #3, DevOps-verified).
  - `tests/manual/results/` 38 tracked artifacts (~11 MB) `git rm`'d (tranche-1 #4, confirmed 0 tracked).
  - Minimal CI (`.github/workflows/ci.yml`: pytest + frontend build), `pyproject.toml`/ruff, pinned `requirements-test.txt`, `.nvmrc`/`engines` (tranche-1 #5).
  - 3 graduated flags retired (`PERSONA_LEAN_PROMPT`, `ROUTING_SEMANTIC_PRIMARY`, `LORE_ONDEMAND_ENABLED`), −505 lines (tranche-1 #6, grep-confirmed).
  - Dead code: `src/shared/persona_assets.py`, `archive/prompt_optimization/*`, 5 unused npm deps (tranche-1).
  - **`handle_session_chat` god-function decomposed** (step 7 seam 1 — function-level; file-level split still pending).
  - **`prompt_builder.py` dead legacy deleted** 747→448, dropped under the god-file threshold (step 7 seam 3).
  - **`config.py` split into a `config/` package** (step 7 seam 4 — off the god-file list).
  - **`_wallet_flows` module global → SQLite `WalletFlowRepository`** (step 7 seam 2), mnemonic never persisted.
  - **`SECURITY.md` + `docs/THREAT_LEVEL.md` added** → cms check now **0 errors / 0 warnings** (was 2 errors).
- **New (5):**
  - **[MED] `data/` directory is untracked AND not gitignored** — contains live `data/chats.db` (274 KB) + a 1.3 MB backup; slips through the top-level `*.db`/`chats.db` rules because it's nested. A stray `git add -A` would commit live conversation data. *(Not the metrics' `dist` flag — that one is inert.)*
  - **[LOW] `dist` gitignore gap** (from metrics) — inert (no `dist/` produced today; `react-ui/build/` is already ignored). Cheap to close preemptively.
  - **[LOW-MED] `.env.example` drift** — 3 flags in `.env` missing from `.env.example` (`LORE_ONDEMAND_ENABLED`, `PERSONA_LEAN_PROMPT`, `ROUTING_SEMANTIC_PRIMARY`); several keys in example missing from real `.env`. No secrets leaked.
  - **[MED] `test_selective_context_inject` has zero CI coverage** — the CI `--ignore`s it (non-hermetic/order-dependent, hits a live embedder), so a slice of `MEMORY_CONTEXT_INJECT` behavior is a silent blind spot.
  - **[LOW] 2 dead exports** — `cleanup_summary_store()` + `ensure_all_summaries()` in `cv_summarizer.py`, zero call sites (grep-confirmed), trivially deletable.
- **Still open / deferred (10):**
  - **[HIGH] Credential rotation** (MongoDB Atlas URI + Brave key) — SECURITY.md still records "unconfirmed"; **user-deferred**, the single most important outstanding item.
  - **Step 8 — dissolve `startup.py` DI hub** — deferred to its own session; *slightly worse* now (a 24th getter, `get_wallet_flow_repo`, was added). 16-file fan-in, 10 function-local imports in `query_handler_service.py` (2 marked `# lazy: avoid import cycle`).
  - **`handle_wallet_query` / `_handle_wallet_creation_step` decomposition** — the deferred half of step 7; flow state is now durable but the ~186-line functions + untyped `step: int` state machine remain.
  - **`chat_session_service.py` file-level split** — extract the phase pipeline to a `services/chat_session/` package (reverses the 949→1035 growth).
  - **`StrEnum` for `role`/`source_type`/`proposal_type`** — idiom already used in `persona_schema.py`/`intent_classifier.py`, not applied to the schema layer.
  - **`except Exception` count 91→117, inconsistent log levels** (warning vs error, `exc_info` ad hoc).
  - **No shared backend↔frontend API contract** — `react-ui/src/types/personas.ts` hand-duplicates `PersonaCard`; no OpenAPI/codegen.
  - **Overlapping Playwright suites** — 5 `phase8-*.spec.ts` + 3 `celestial-order-*.spec.ts`, unconsolidated.
  - **`MEMORY_CONTEXT_INJECT`** — failed its gate twice (Gate 0 + 0.1), no scheduled re-gate date; decide: commit ADR-006 Phase 1 or retire.
  - **Persona PNGs ~40 MB** (`react-ui/public/images/personas/`) — largest byte contributor, not addressed.

## 3. Lens reports

### 🧹 Janitor — dead code & bloat
- **2 trivially-dead exports:** `cleanup_summary_store()` (`cv_summarizer.py:424`), `ensure_all_summaries()` (`:466`) — zero call sites across src/scripts/tests (only the `persona_memory` `__all__` re-export). `[low, high]`
- **`validate_persona_file()`/`load_persona_card()` strict variants** (`persona_schema.py:513,548`) — production-unreachable (loader uses `_lenient` only); test-only surface, not delete-safe. `[low, med]`
- **Deps clean:** re-verified — no unused npm or Python deps (tranche-1's 5 npm removals confirmed gone). `[verified]`
- **alembic 3 candidates cleared** (framework magic — CLI-discovered migrations). `[verified]`
- **Flag graveyard:** `MEMORY_CONTEXT_INJECT` is the standout — failed twice, no re-gate date (flag-gate failure-branch case). `AGENTIC_ENABLED` = intentionally parked (documented), not graveyard. The 3 graduated flags are confirmed retired. `[med]`
- **Biggest remaining bloat wins:** decompose `handle_wallet_query`; consolidate the 8 overlapping Playwright specs; delete the 2 dead exports; decide `MEMORY_CONTEXT_INJECT`; split `startup.py`.

### 🏛️ Architect — structure & modularity
- **Verdict: in-between** — a real layered app (routes → services → repositories → models, mirrored on the frontend) whose *center* has calcified: the 24-getter `startup.py` hub + two still-multi-responsibility god services.
- **`chat_session_service.py` (1035)** — 4 responsibility clusters in one file (context assembly / turn pipeline / progression / summarization). The function decomposition did the conceptual work; **extract to a `services/chat_session/` package** to reverse the line growth. `[high]`
- **`startup.py` (636) — the keystone.** 24 globals/24 getters, fan-in from 16 files (all routes, 2 services, server.py); 10 function-local imports in `query_handler_service.py` alone (2 marked `# lazy: avoid import cycle`), 9 in `routes/wallet.py`. Gained a 24th getter this cycle instead of shrinking. `[high]`
- **`query_handler_service.py` (852)** — one class mixing Brave-search, agentic tool-calling, and the wallet-creation flow machine. Extract a `WalletCreationFlowService` (the repository half is already done). `[med-high]`
- **`persona_schema.py` (600, 17 classes)** / **`memory_manager.py` (548, 3 classes)** — volume not tangle; low-risk mechanical splits. `[low]`
- **No shared API contract** (backend Pydantic ↔ frontend `personas.ts`) — drift risk, unchanged. `[med]`
- **Loose top-level cluster:** 16 memory/LLM/persona modules sit flat under `coordinator/` with no `memory/`/`llm/` subpackage. `[low-med]`
- **3 highest-value:** (1) dissolve `startup.py` → `Depends` (step 8); (2) extract `chat_session/` package; (3) split the wallet-flow service.

### 🔬 Clean Code — refactoring
- **`_handle_wallet_creation_step` (query_handler_service.py:666-852)** — hand-rolled state machine on an **untyped `step: int`**; 3 nested try/except, `_finalize_response` repeated 6×. Fix: `WalletFlowStep` enum + `match` + a `WalletFlowState` dataclass. `[high]`
- **Duplicated non-fatal repo-call boilerplate** (`query_handler_service.py:85-101, 531-546, 755-782`) — same `try/from ..startup import.../except→warning` shape 3+×; collapse into `_safe_repo_call(getter, fn, ctx)`. `[med]`
- **`startup.py` 9 near-identical `get_X_repo` getters** + ~20 mutable module globals — collapse into a `_require(_x, "X")` helper. `[low-med]`
- **String pseudo-enums** `role`/`source_type`/`proposal_type` (`schemas.py`, `message_repository.py`, `trade_proposal_repository.py`) — codebase already uses `str, Enum` elsewhere; not applied here. `[med]`
- **`_apply_post_turn_updates` / `_track_nephilim_progression`** — step 7 pushed remaining complexity into these Phase-6 helpers (106 / 127 lines, 4 nested try/except); split + normalize log-level policy. `[med]`
- **Flag branching is NOT combinatorial** — the retirements helped; remaining hot-path flags are independent boolean gates. `[low]`

### ⚙️ DevOps — config & hygiene
- **[HIGH] Credential rotation still unconfirmed** — MongoDB Atlas URI + Brave key; SECURITY.md carries it forward as an open item. Rotate + record dates. (User-deferred.)
- **[MED, NEW] `data/` untracked + un-gitignored** — live `chats.db` + 1.3 MB backup; add `/data/` to `.gitignore` now.
- **[LOW] Confirmed closed:** docker-compose JWT default (`${JWT_SECRET_KEY:?}`); `tracked_artifacts: []`; `.env`/`.env.docker` gitignored.
- **[LOW-MED] `.env.example` drift** (3 flags missing) — regenerate from the real key set (placeholders).
- **[MED] `test_selective_context_inject` = zero CI coverage** (the `--ignore`); make it hermetic or gate a hermetic subset.
- **CI:** real gate (pytest + frontend build); **ruff is advisory** (`continue-on-error`, ~1500-issue backlog) — visibility only; coverage gate is local-only. `dist` gitignore gap is inert.

### 📄 Docs — cms health (`/crucible:cms check`)
- **0 errors / 0 warnings / 1 info.** The prior audit's 2 errors (missing `SECURITY.md`, `docs/THREAT_LEVEL.md`) are **closed** — both added in tranche-1. CLAUDE.md is 237 lines (steady). The `docs/` tree remains rich and well-organized.

## 4. Refactor priority matrix

| # | Task / File | Issue | Effort | Impact | Actionable fix |
|---|---|---|---|---|---|
| 1 | Credential rotation (SECURITY.md) | Leaked MongoDB/Brave creds, rotation unconfirmed | **Low** | **High** | Rotate Atlas URI + Brave key; record dates (user action) |
| 2 | `.gitignore` + `data/` | Live chats.db + backup untracked & un-ignored | **Low** | **Med-High** | Add `/data/` to `.gitignore` (one line) |
| 3 | `startup.py` DI hub (step 8) | 24 globals/getters, 16-file fan-in, lazy-import cycles | **High** | **High** | Dissolve to typed `AppState`/FastAPI `Depends`; its own session |
| 4 | `query_handler_service.py` wallet flow | Untyped `step:int` machine; ~186-line functions | **Med** | **Med-High** | `WalletFlowStep` enum + `match` + `WalletFlowState`; extract `WalletCreationFlowService` |
| 5 | `chat_session_service.py` (1035) | Phases decomposed but all in one file (grew 949→1035) | **Med** | **Med** | Extract `services/chat_session/` package (context/pipeline/progression/summarization) |
| 6 | `MEMORY_CONTEXT_INJECT` | Failed gate 2×, no re-gate date | **Low-Med** | **Med** | Commit ADR-006 Phase 1 date, or retire flag + plumbing |
| 7 | `StrEnum` + dedup helpers | `role`/`source_type`/`proposal_type`; repo-call + getter boilerplate | **Low** | **Med** | Promote to `StrEnum`; `_safe_repo_call` + `_require` helpers |
| — | Dead exports + Playwright consolidation | 2 dead `cv_summarizer` exports; 8 overlapping specs | **Low** | **Low-Med** | Delete exports; merge phase8/celestial suites |

## 5. Cleanup plan

Sequenced so each step is protected by the CI net now in place. All actionable via `/crucible:develop`.

1. **Two zero-risk safety fixes (no logic):** add `/data/` to `.gitignore` (matrix #2); regenerate `.env.example`; add the inert `dist/` line. Close the credential-rotation loop (matrix #1 — user action + record dates in SECURITY.md).
2. **Step 8 — dissolve `startup.py` (its own focused FULL cycle).** Typed `AppState`/`Depends`; migrate the 16 importers incrementally; delete the lazy in-function imports as the `llm_client ↔ services` cycle dissolves. Highest-leverage structural fix — it also stops the hub from absorbing every new repository.
3. **Finish the deferred half of step 7:** decompose `handle_wallet_query`/`_handle_wallet_creation_step` (matrix #4) with a `WalletFlowStep` enum + `match` + `WalletFlowState` dataclass, backed by the already-durable `WalletFlowRepository`; and extract `chat_session_service.py`'s phases into a `services/chat_session/` package (matrix #5).
4. **Mechanical wins:** `StrEnum` for `role`/`source_type`/`proposal_type`; `_safe_repo_call` + `_require` helpers; delete the 2 dead `cv_summarizer` exports; normalize the non-fatal-catch log-level policy (matrix #7).
5. **Coverage + flags:** make `test_selective_context_inject` hermetic (close the CI blind spot); decide `MEMORY_CONTEXT_INJECT`'s fate (matrix #6); begin burning down the ruff backlog toward a gating lint.
6. **Larger, lower-urgency:** shared API contract (OpenAPI/codegen backend↔frontend); consolidate the 8 Playwright suites; compress/relocate the ~40 MB persona PNGs.

---
*Generated by `/crucible:repo-audit`. Lenses are frozen (version 1); the anchor score is deterministic. Raw per-lens agent output is gitignored under `docs/audits/.raw/` — only this synthesized report is versioned.*
