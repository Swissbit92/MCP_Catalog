# Changelog

All notable changes to the NEPHILIM project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed (2026-07-04) — `SourceType` StrEnum (audit follow-up #7)

Promoted the `source_type` string pseudo-enum to a shared `enum.StrEnum` in `schemas.py` (8 values), used as named constants at the ~22 assignment/comparison sites across routes + services. `enum.StrEnum` (not the older `(str, Enum)` idiom) so members render as their value in f-strings/logs. Fields stay typed `str` (the vocabulary evolves — strict validation could reject a future/stored value); members are `str`, so `==`/JSON/SQLite all keep the string value. Behavior-preserving; suite 1705, 0 regressions. Completed in a follow-up commit: **`MessageRole`** (user/assistant/system, at the message-persistence sites) and **`proposal_type` untangled into two enums** — `ProposalType` (card/action: swap/strategy/wallet_deletion) vs `ProposalCategory` (response metadata: trade_proposal/strategy_proposal/wallet_deletion), which were a single overloaded name across two vocabularies; plus the missed `wallet_proposal_service` source_type sites (9th value `WALLET_PROPOSAL`). Proposal-card JSON contract verified unchanged.

### Changed (2026-07-04) — Wallet-creation flow extracted + typed (audit follow-up #4)

Completes the deferred half of step 7 (see [docs/audits/2026-07-04-nephilim_followup.md](docs/audits/2026-07-04-nephilim_followup.md) matrix #4). Behavior-preserving; suite 1667 → 1679, 0 regressions.

- **New `services/wallet_creation_flow_service.py`.** The guided wallet-creation state machine — previously two ~186-line methods on the `QueryHandlerService` god-class, dispatching on a bare untyped `step: int` — becomes its own collaborator: a `WalletFlowStep` **IntEnum** (keeps the SQLite integer column byte-compatible), a `WalletFlowState` **dataclass** (which structurally cannot hold a mnemonic), and `match`-based dispatch with each step in its own method. `_finalize_response` is injected (bound method), so the Brave / agentic / deletion query paths are untouched and every branch keeps the exact response contract.
- **`query_handler_service.py` 852 → 597 lines** — delegates via `advance()`/`start()`, dedups the two former creation-start blocks, and drops `_wallet_slot_preflight` + `_handle_wallet_creation_step`.
- **Mnemonic invariant now structurally enforced** — there is no field for it on `WalletFlowState` and no column on `wallet_flow_state`. Displayed once, request-local, never persisted.
- **Tests:** 9 characterization tests written *first* (green before AND after the move = behavior-preserving) + 3 typed-layer tests (`test_wallet_creation_flow.py`). The flow had effectively zero prior direct coverage.
- **Hygiene:** `/data/` added to `.gitignore` — the `data/chats.db.backup_*` snapshots don't match the `*.db` rule, so the runtime data dir showed as untracked (a stray `git add -A` could commit live conversation data).
- **Docs:** populated the `docs/ARCHITECTURE.md` skeleton (Components / Data / Key-invariants tables) to reflect the current layered architecture after the step-7 + this cleanup.

### Fixed (2026-07-04) — Search-routing/anti-hallucination fix chain (ADR-007)

A real Telegram conversation (session `dcc3693d`) exposed E.E.V.A. confidently fabricating a FIFA World Cup 2026 match result (score, date, opponent) with zero grounding, then agreeing with and elaborating on her own fabrication when the user "confirmed" it. Traced to five distinct root causes, all fixed:

- **Generation-time groundedness gate (ADR-007, new, `GROUNDEDNESS_GATE_ENABLED`, default OFF)** — the deepest gap: once intent routing decides no tool is needed, `routes/chat.py`'s bare-completion branches call none of the existing anti-hallucination guards (all three live inside `tool_calling_service.py`, unreachable from this path). `GroundednessGateService` runs a second cheap LLM classification on the draft itself, decoupled from routing, and replaces an ungrounded real-world claim with an honest offer-to-search. Narrowly scoped (persona lore, general knowledge, and already-grounded turns explicitly excluded) to avoid false-abstention on legitimate answers. See [ADR-007](docs/decisions/007-generation-time-groundedness-gate.md).
- **Routing coverage** — `ForceSearchService.FORCE_PATTERNS` gained a `"last"` entry (had `"latest"` but missed "what was their last match"); the semantic router's `web_search` example set (previously 100% crypto/market-phrased) gained sports/temporal/outcome examples.
- **Wallet/lore lexeme collision** — "tell me about your history" (pure lore) was misrouted to the wallet tool via a shared "history" lexeme with the wallet example "my trade history". Replaced with "show my past trades", validated via a real bge-m3 sweep: wallet false-positives stayed at 0, wallet precision stayed 1.0, wallet/web recall both improved slightly.
- **Query-resolution gaps** — the echo-guard now recognizes context-dependent-but-non-pronoun phrases ("next match", "last match") as carrying no topic on their own, closing a near-verbatim-echo-reaches-Brave gap; a leading correction preamble ("no, I meant...") no longer inflates the word count past the follow-up-detection trigger threshold.
- **Relevance-gate tuning** — new `tests/evaluation/tune_relevance_threshold.py` (real bge-m3 sweep) found a candidate threshold. First pass (n=8, mostly hand-written): `SEARCH_RELEVANCE_MIN_COSINE=0.28`, zero measured false-abstention but only caught half the junk shapes. Extended same-day to n=25 with 17 real Brave query/result pairs (14 relevant across sports/crypto/weather/knowledge/product domains, 3 real junk-mismatch pairs): `0.36` catches **100% of junk** with a 5% false-abstention rate — and that one false-abstention is the n=8 pass's own synthetic adversarial sample, not real data. Replaces the prior untuned 0.40 placeholder. The gate itself (`SEARCH_RELEVANCE_GATE_ENABLED`) remains OFF pending an explicit go/no-go.

Eval-first throughout (ADR-005/006 discipline): a frozen baseline, extended eval corpora for all 5 failure modes (including regressions locked in as `xfail` before each fix, then un-marked once genuinely fixed), and match-or-beat validation via real bge-m3 sweeps, not just unit mocks. 1671→1697 backend tests, 0 regressions.

### Changed (2026-07-04, later) — Relevance-gate eval corpus expanded with real data

`tests/evaluation/relevance_gate_eval_set.json` extended 8→25 samples with 17 real Brave query/result pairs (direct Brave Search API calls, same key the coordinator uses), at the user's request after the initial n=8 pass. Re-tuned threshold: `SEARCH_RELEVANCE_MIN_COSINE` 0.28→0.36. See the config field's docstring for the full before/after breakdown. `GROUNDEDNESS_GATE_ENABLED=true` also flipped live on prod this session for a monitored soak (user-requested); `SEARCH_RELEVANCE_GATE_ENABLED` stays OFF.

### Added (2026-07-04) — Telegram gateway subsystem (`services/telegram-gateway/`)

A thin, single-user Telegram bot letting the user chat with the NEPHILIM personas from the Telegram app — built as a standalone repo first, then folded in as a subsystem (own venv/tests/launchd, zero changes to the coordinator API) once it became clear the client and the session-API contract it depends on belong in the same repo/PR.

- python-telegram-bot 22.8 long-polling relay to the existing `POST /sessions`, `/sessions/{id}/greet`, `/sessions/{id}/chat`, `DELETE /sessions/{id}/messages` endpoints. One nephilim session per `(chat_id, persona_key)` in a local sqlite map; stale-session (404) recreate-and-retry.
- `/start` (greet once) and `/reset` (true history deletion, progression preserved). Reuses the existing shared `eeva-dca`/`eeva-exec` notification bot token (send-only there, so no long-poll conflict).
- Security: hard `chat_id` allowlist (silent drop, no log/backend-call for rejects), forwarded-message refusal (injection guard), link previews disabled on every send (exfil guard), fixed user-facing error strings only (no exception/URL/session-id leakage, incl. an unexpected-error catch-all), token-redacting log filter, global `asyncio.Lock` serializing LLM calls (nephilim's `OLLAMA_NUM_PARALLEL=1`), `flock` single-poller guard, no exec/file/trading credentials in the process.
- 73 tests, ruff clean, live-verified end-to-end against the running backend (greet/chat/reset). See [docs/THREAT_LEVEL.md](docs/THREAT_LEVEL.md#subsystem--telegram-gateway-servicestelegram-gateway) and `services/telegram-gateway/CLAUDE.md`.

### Changed (2026-07-04) — Repo-audit cleanup, tranche 2 (step 7: god-function decomposition)

Acting on [docs/audits/2026-07-04-nephilim.md](docs/audits/2026-07-04-nephilim.md) §5 step 7, on top of the tranche-1 CI net. Four behavior-preserving seams, each QA-gated; full headless suite green throughout (1661 → 1667 with new tests, 0 regressions). Where the audit's premises had aged out (tranche-1 already shrank two of the targets), the plan was adjusted and the reasoning recorded.

- **Seam 1 — `handle_session_chat` decomposed** (`services/chat_session_service.py`). The 426-line, 8-concern god-function is now an ordered phase pipeline (load identity → build prompt → select history → generate → persist → summarize → post-updates), each phase passed a frozen typed `ChatDeps` (built once from the route dict) and a mutable `ChatTurnState` dataclass. Fowler Extract-Function; public signature unchanged (`deps` stays a dict at the boundary), `_check_and_summarize` still takes the raw dict. The double `get_seeker_profile()` fetch is collapsed to one (cache-on-success, preserving both try/except paths). The orchestrator is ~50 lines. Verified additionally against real Ollama via the 4 `test_selective_context_inject` cases (direct ChatBody/`extra_system_context` behavioral test).
- **Seam 2 — wallet-creation flow state moved to SQLite** (new `repositories/wallet_flow_repository.py`, wired via `startup.get_wallet_flow_repo`). Replaces the `_wallet_flows` module global (lost on restart, unsafe under multiple workers) with a durable, session-keyed store + startup sweep of abandoned flows (30-min TTL) + delete-on-complete/abort. **Security:** the BIP39 mnemonic is deliberately NOT persisted — reading the flow showed it is displayed once and only ever wiped (never re-read), so it stays a request-local variable and no seed phrase touches disk. This is strictly more secure than the prior in-memory dict and needs no at-rest encryption key. +6 unit tests incl. a locked-in "mnemonic never persisted" invariant.
- **Seam 3 — dead legacy deleted from `prompt_builder.py`** (747 → 448 lines). Tranche-1 had already retired the legacy system-prompt builder; the orphaned section builders (`_build_behavior_block`, `_build_nephilim_lore_block`, legacy `_get_wallet_copilot_block`, `_fmt_slider_block`) + the three legacy rule constants were confirmed to have zero live consumers and removed, and the 5 now-broken names pruned from `persona_memory`'s re-export + `__all__`. Kept `_summarize`/`_join_list` (used by the lean builder) and `_build_psychological_block`/`_build_curiosity_block` (live test consumers). Now under the 500-line god-file threshold, so the planned package split was unnecessary — delete beat reorganize.
- **Seam 4 — `config.py` split into a `config/` package** (802-line file → per-subsystem leaf modules: llm/search/memory/wallet/auth/routing/lore/agent). `config/__init__.py` keeps the composition root `CoordinatorSettings`, the `@lru_cache get_settings()` accessor, the `settings` singleton, and the two persona sampling helpers, and re-exports every public symbol. Import surface preserved exactly — `src.coordinator.config.<name>` still resolves for all 25 importers and the ~10 `mock.patch("src.coordinator.config.get_settings")` test sites (verified: singleton identity, lru_cache, patch-path, direct leaf-class imports).

### Fixed (2026-07-04) — synthesis context-poisoning: refusing correct results (default-OFF, live n=10 verified)

- **E.E.V.A. no longer refuses correct search results after apologizing for an earlier hallucination.** Observed on prod: once the assistant said "that was false / I can't search" earlier in a conversation, a LATER turn whose fresh web search returned CORRECT results (real UEFA/Guardian sources, `used_search=True`, 5 results) was REFUSED — "I cannot and will not perform web searches" — with the real citations stapled onto the refusal. Root cause: local models (Ollama GGUF) lack instruction-hierarchy training (OpenAI arXiv:2404.13208), so the stale in-context self-apology sits at equal priority to system rules and geometrically traps the model (arXiv:2603.03308); worsened by the synthesis path placing fresh results *before* the poisoned history (recency favors the apology).
- **`SEARCH_SYNTHESIS_TRUST_RESULTS`** (default OFF) — two layers, both gated by the flag:
  1. **De-poison the synthesis input (the reliable lever):** the synthesis LLM is fed only the fresh results + the RESOLVED QUERY as the question, NOT the full chat log (`tool_calling_service._synthesis_user_turn`, applied at all 3 synthesis sites). The topic was already folded into the query by resolution, so no context is lost and the poison is deterministically absent from the input.
  2. **RULE 0 prompt directive (reinforcement):** `build_synthesis_prompt` (`tools/synthesis_prompts.py`) states the results were retrieved just now and supersede earlier turns, scoped so it never overrides RULE 5 honest abstention on empty/off-topic results (CRAG/Self-RAG), kept short + separate from voice-setting to avoid flattening persona.
  - Off (default) = byte-identical legacy synthesis (full history, no RULE 0).
- **Live eval, n=10 per case** (flag-ON backend): POISONED **10/10 ANSWERED** (0 refused), CLEAN **10/10 ANSWERED**, persona voice intact ("Seeker… advanced to the Round of 16 after a convincing 2-0 victory over Algeria"). **Honesty note:** the RULE 0 prompt directive ALONE was only ~1/5 reliable on the 24B (an initial n=1 eval was a lucky sample) — local models lack instruction-hierarchy training and don't reliably out-prioritize an in-context self-apology, exactly as the research predicted (arXiv:2603.03308). The input-scoping layer is what makes it deterministic. +6 headless tests (`test_synthesis_prompt.py`, `test_tool_calling_service.py`); full suite green.

### Changed (2026-07-04) — Repo-audit cleanup, tranche 1 (steps 1–6)

Acting on [docs/audits/2026-07-04-nephilim.md](docs/audits/2026-07-04-nephilim.md) §5. Security-first, each step protected by the prior; full headless suite green throughout, real-server end-to-end verified (`/persona/greet` + `/persona/chat` → HTTP 200, in-character).

- **Security (step 2):** `routes/wallet.py` stops leaking `str(e)` to clients on the two financial endpoints (→ `type(e).__name__`, matching `routes/chat.py`); `docker-compose.yml` force-requires `JWT_SECRET_KEY` (`${VAR:?}`, no committed `change-me` default).
- **Dead code / artifacts (step 3):** deleted `src/shared/persona_assets.py` + `archive/prompt_optimization/*.py`; `git rm` 38 tracked run-artifacts under `tests/manual/results/`; removed 5 confirmed-unused npm deps (`react-window`, `react-virtualized-auto-sizer`, `yaml`, `refractor`, `react-syntax-highlighter`) + `@types` (KEPT `workbox-webpack-plugin` — verified in use).
- **Safety net + docs (steps 1, 4):** added minimal GH Actions CI (headless pytest gate + frontend build; ruff advisory over the pre-existing backlog), `pyproject.toml` (ruff), pinned `requirements-test.txt`, `.nvmrc`/`engines`. New `SECURITY.md` (incl. credential-rotation status table — rotation of the historically-leaked MongoDB/Brave/JWT creds remains an **outstanding action item**) + `docs/THREAT_LEVEL.md` (clears cms). `AUTH_REQUIRED=false` documented as an accepted local-only posture.
- **Flag retirement (step 5):** retired `PERSONA_LEAN_PROMPT`, `ROUTING_SEMANTIC_PRIMARY`, and `LORE_ONDEMAND_ENABLED` — all had graduated to default-on and matched prod, so their legacy/OFF branches (the legacy prompt builder, the keyword-first router body, the static-3-entity lore path) were removed. Net −505 lines. Behavior-preserving (flags were on in prod). `MEMORY_CONTEXT_INJECT` kept parked (failed its voice gate 2×). See ADR-003/005.
- **De-duplication (step 6):** extracted `_complete_or_503()` (3× LLM→503 blocks in `routes/chat.py`) and `_wallet_slot_preflight()` (2× wallet-cap checks in `query_handler_service.py`); bumped 5 silent `logger.debug` catches (lore/rank/capability context) to `warning`. Deferred: `StrEnum` for `source_type`/`role` (cross-boundary typing migration, own change).

### Fixed (2026-07-04) — web-search follow-up query resolution (default-OFF, live-verified)

- **"search the web for it" no longer returns junk + confabulation.** A deictic follow-up turn was passed to Brave verbatim (the topic from prior turns discarded by `QueryExtractionService.extract_latest_user_message`), so Brave returned meta-results ("Search the web in Chrome — Google Chrome Help", "Brave Search", …); those are non-empty, so the "no results → I don't know" guard never fired and the LLM confabulated over irrelevant grounding (the observed World Cup incident: fabricated scores + those exact junk sources). Root cause: the full multi-turn history was already present in `user_prompt` at the force-search query-build site — it was just thrown away.
- **`SEARCH_QUERY_RESOLUTION_ENABLED`** (default OFF): new `services/query_resolution_service.py` resolves deictic/short follow-ups against prior conversation before Brave — cheap deterministic trigger (pronoun / ≤5 words / bare search-command) → single low-temp LLM rewrite (reuses the loaded 24B; only fires on the trigger) → aggressive sanitize (label/quote/JSON strip, word/char guards) → **hard fallback to the raw latest turn on any failure**, so it can never be worse than legacy. Wired into both force-search and keyword-force paths of `tool_calling_service.py`. Off = byte-identical legacy behavior.
- **`SEARCH_RELEVANCE_GATE_ENABLED`** (default OFF) + **`SEARCH_RELEVANCE_MIN_COSINE`** (0.40): new `services/search_relevance_service.py` — defense-in-depth bge-m3 cosine gate; results whose best similarity to the query is below the floor are treated as no-result (honest abstention) instead of synthesized over. Fail-open on any embedder error. Applied at all three result sites.
- **Live end-to-end verification** (real 24B + real Brave): "search the web for it" → resolved to "football world cup 2026 Switzerland performance" → real Brave results ("Switzerland at the World Cup 2026…", "Switzerland 2-0 Algeria…") vs. the junk help-pages the verbatim query returns. Self-contained queries (e.g. "current bitcoin price in usd") correctly pass through un-rewritten (no entity drift). New `SearchSettings` group in `config.py`. +27 headless tests (`test_tool_calling_service.py`, `test_query_resolution_service.py`, `test_search_relevance_service.py`); full suite green, 0 regressions.
- **Bare-command hardening** (follow-up): a *topic-less* command ("search the web", "search the web for it", "look it up online") gives the LLM no explicit referent, so the rewrite is the least reliable and occasionally echoed the command → junk. `_is_bare_search_command` now detects these; on a whiffed/echoed rewrite the fallback becomes the **most recent substantive prior user turn** (which carries the topic) instead of the useless bare command — so the deterministic worst case is the prior real question hitting Brave (real results), never "search the web" (junk). +13 headless tests; live-verified (bare "search the web" → "football world cup 2026 Switzerland performance").

### Changed (2026-06-27) — Persona-eval Phase B: lean prompt + per-persona voice signatures (SHIPPED, gate 7/7)

- **Lean exemplar-first / voice-last system prompt** ([ADR-005](docs/decisions/005-persona-architecture-simplification-eval-first.md) Phase B), flag-gated `PERSONA_LEAN_PROMPT` (global, default OFF) + `PERSONA_LEAN_PROMPT_PERSONAS` (per-persona allowlist — the acceptance-gate fallback). New `_build_system_prompt_lean` dispatches from `build_system_prompt`; the legacy builder (`_build_system_prompt_legacy`) is byte-identical and untouched, so revert is instant and the frozen baseline stays valid. Dedupes the repeated directives, **drops the ~700–800-tok static wiki dump** (still available per-turn via `LORE_ONDEMAND_ENABLED`), positive-framed, exemplars rendered LAST (recency). Prompts shrank **65–69%** (eeva 2935→1040, aegis 2501→827, solace 2432→840 est. tokens; all in the ~900–1,200 target).
- **`voice_signature` persona field** (new `VoiceSignature` schema model) authored for all 7 personas — distinct diction / cadence / pattern / in-world anchor / topic-diverse exemplars. The advisory blur cluster de-collided: eeva→Confluence-paradox (no longer routes to Solace), solace→Sanctuary/breath, aegis→tactical triage. Excluded from the CV-summary fingerprint (`cv_summarizer._normalize_for_fingerprint`) so adding it does NOT drift the legacy `<identity>` text.
- **Acceptance gate PASSED 7/7** (candidate eval vs frozen legacy, LORE-on both arms): overall distinctiveness attribution **0.393 → 0.732** (random 0.143); flatness **1.8%→0%** overall, **4.8%→0%** grounding. Per-persona all match-or-beat — eeva/aegis **0.25→0.75**, solace **0.25→0.625**, cipher 0.375→0.75, nyx 0.375→0.50, aurora 0.625→0.875, gojo 0.625→0.875. 0 regressions.
- **Harness fix:** `run_eval.collect_live` now threads `base_url` into `create_session` (was hardcoded to :8000, so a candidate backend on another port 404'd). 24 new headless tests (`test_lean_prompt.py`); backend suite green.
- **Blind A/B confirmation** ([ADR-005](docs/decisions/005-persona-architecture-simplification-eval-first.md) Phase B): new `blind_judge.py` — per-persona blind pairwise A/B over the two frozen baselines (seeded side-randomisation, reuses `ab_harness` tally/sign-test/verdict; `--emit`/`--score`/`--human` CLI). 7 fresh arm-blinded judges (1/persona, 84 pairs) → lean candidate **67/84 (79.8%, p≈0)**, no regressions; CANDIDATE BETTER for gojo/eeva/nyx, PARITY (candidate-leaning) for aegis/cipher/solace/aurora. A second, independent instrument agreeing with the attribution metric. +7 headless tests (`test_blind_judge.py`).

### Added (2026-06-26) — Persona-eval Phase A: trustworthy voice/distinctiveness measurement

- **The ruler before re-cutting** ([ADR-005](docs/decisions/005-persona-architecture-simplification-eval-first.md) Phase A). New `tests/evaluation/persona_eval/`: a probe set (`probes.json` — distinctiveness / voice / grounding / adversarial / drift) and metrics (`persona_metrics.py`) that replace the gameable keyword `persona_voice` scorer. **Headline metric:** leave-one-out nearest-centroid *attribution accuracy* over bge-m3 embeddings — "can we tell which persona said this?" (random chance = 1/num_personas; can't be gamed by sprinkling lore vocabulary). Plus `mean_separation` and a flatness/assistant-mode detector.
- **Blind A/B harness** (`ab_harness.py`) — sides randomised + arm hidden, exact two-sided sign test, `verdict()` mapped to the ADR-005 acceptance gate. **Baseline runner** (`run_eval.py`) — drives the backend over every persona × probe, computes the report, freezes a timestamped per-persona baseline (the "freeze legacy baseline first" gate step).
- Logic is pure and **unit-tested headless** (no Ollama): 27 new tests (`test_persona_metrics.py`, `test_persona_ab_harness.py`). Live collection is a thin shell. No persona/runtime code touched. Suite 1590 → 1617 collected; backend+eval 1558 pass / 0 fail.
- **Legacy baseline frozen 2026-06-27** (168 responses): distinctiveness attribution **0.393** vs 0.143 random floor; aurora/gojo most distinct (0.62), **eeva/aegis/solace blur at 0.25 each** (the Phase-B target); flatness low (1.8% overall / 4.8% grounding). This is the per-persona match-or-beat-or-revert comparison point for Phase B.

### Fixed (2026-06-26) — long sessions (>100 messages) 500 on every turn

- **`ChatBody.history` count guard no longer fights token-budget selection.** `handle_session_chat` assembles history from `memory_manager.select_messages` (bounded by the model's TOKEN budget) + RAG memories + a summary turn; on a large context window that could exceed the `ChatBody.history` `max_length=100` count guard, so every turn in a session past ~100 messages 500'd at internal `ChatBody` construction. Introduced a shared `MAX_HISTORY_TURNS` constant (`schemas.py`) and a `_assemble_capped_history()` helper (`chat_session_service.py`) that keeps the summary (primacy) + the most-recent raw turns, guaranteeing `len <= MAX_HISTORY_TURNS`. Older raw turns remain represented by the summary + RAG-injected memories; the external-request guard is unchanged. 6 new tests (`test_history_cap.py`); backend suite 0 regressions.

### Evaluated (2026-06-26) — Phase 3 go-live decision: agentic web-search stays OFF

- **Live persona-voice evaluation on Magidonia-24B (E.E.V.A.) → keep `AGENTIC_ENABLED` OFF for web search.** Measured `persona_voice` on identical BRAVE_ROUTING queries (n=9/arm): legacy `handle_brave_query` **0.333**, agentic pipeline **0.44–0.52**, ungrounded free chat ~0.82. Grounded web-search is inherently low-voice for this model on *both* paths; the ≥0.85 bar only applies to free chat. The agentic path is voice-competitive-to-better than legacy, but for read-only search it adds an extra LLM round-trip (argument extraction) for no voice gain — strictly worse on latency. The pipeline's real value (deterministic pre-execution gating + HITL) is for **write actions**; it stays built/validated and parked for that use case. The **safety middleware** (interceptor, injection guard, execute-mode guard) remains ON by default and hardens existing paths now.
- **Voice fix (unproven, kept):** Stage-2 rendering gained diegetic `[FACTS]` framing + a post-history voice reminder (PHI) + an anti-summarizer rule (`agentic_pipeline._build_render_input`/`_voice_reminder`, `synthesis_prompts` voice contract). No significant metric change — likely instruction-density saturation on the 24B. Kept as defensible structure for the future write-action path; not claimed as an improvement.
- **Test robustness:** the Phase-3 flag-default tests and the brave-routing route test are now independent of the ambient `.env` (assert declared `model_fields` defaults; pin the agentic flag off in the routing test) so the suite is green regardless of deployment flag state. Backend suite 1489 pass / 0 fail with the flag either ON or OFF.
- **Pre-existing bug surfaced (not Phase 3):** `ChatBody.history` has `max_length=100`; any session exceeding ~100 messages 500s at `chat_session_service.py` request construction. Worth its own fix.

### Added (2026-06-26) — HERMES-Agents Phase 3: persona-safe agentic behaviour (flag OFF)

- **Single-action, in-character tool use with deterministic safety middleware**, behind `AGENTIC_ENABLED` (default **OFF** = byte-identical to pre-Phase-3). Built, flag off, go-live pending — mirrors the Phase 0 / Phase 2 precedent. [ADR-004](docs/decisions/004-persona-safe-agentic-tool-calls.md).
- **M1 — Scene-contract prompts.** New `AgentSettings` in `config.py`; `build_scene_contract()` (`tools/synthesis_prompts.py`) splits the prompt into a **Voice** section (no tool grammar) and an **Action** section using diegetic in-world tool names (`DEFAULT_ACTION_ALIASES`, e.g. "consult the Lattice" → `brave_web_search`); per-persona override via the new `agentic_action_aliases` field on `PersonaCard`.
- **M2 — Tool-call interceptor** (`services/tool_interceptor.py`). Deterministic pre-execution gate: per-persona `mcp_access` re-enforcement, argument-level allowlist (token-enum + amount for swaps, length/control-char for queries — shell-metachar blocking intentionally dropped, the Brave query travels over STDIO JSON-RPC with no shell), blast-radius/HITL classification, and a hard block on `solana_execute_swap`/`execute_swap` from a non-`user_confirmed` source. Defence-in-depth execution-mode guard added at the on-chain `WalletExecutionService.execute_swap` chokepoint.
- **M3 — Injection guard** (`services/injection_guard.py`). Trust hierarchy system > user > retrieved: `check_tool_trigger_source` blocks a tool argument sourced from RAG/lore rather than the user; `sanitize_memory_write` strips tool-call syntax before a RAG write (wired into `chat_session_service`); `detect_escalation` flags a multi-turn push to act-without-asking.
- **M4 — Grammar-constrained argument extraction** (`services/argument_extractor.py`). Ollama `format=<json schema>` constrains the 24B to argument-filling only (selection stays on the bge-m3 router); schema-conformance + optional bge-m3 coherence gate; 3-retry then deterministic regex fallback.
- **M5 — Two-stage agentic pipeline** (`services/agentic_pipeline.py`). Stage 1 deterministic (extract → injection check → interceptor → execute); Stage 2 the LLM renders the result in-voice and never sees raw function grammar. Wired into the web-search path via `QueryHandlerService.handle_agentic_query()` and a flag-gated branch in `routes/chat.py`; output goes through the shared `_finalize_response` (inherits tool-name strip + private-key redaction + first-person). Wallet actions stay on the existing propose→confirm→execute flow.
- **M6 — Tool-call red-team eval** (`tests/evaluation/test_tool_call_safety_redteam.py` + `golden_agentic/`). Separate from the persona text-safety layer ("Mind the GAP"): ≥95% injection block (100% of expect-blocked vectors), 100% argument-schema / RAG-trigger / direct-execute / mcp-access block, 0 false positives on clean vectors, persona-break detector exact on the golden set.
- **Tests:** ~84 new + 2 `requires_ollama` integration checks. Full suite 1501 → 1544 pass / 41 skip / 0 fail headless, 0 regressions.

### Fixed (2026-06-23) — RAG embedding overflow

- **Semantic memory no longer silently broken.** `memory_rag`/Phase-3 RAG threw `HTTP 500: the input length exceeds the context length` on every chat that fed the embedder more than ~2048 tokens, so semantic recall was skipped entirely. Root cause was two-fold: the legacy `langchain_community.OllamaEmbeddings` calls Ollama's `/api/embeddings` endpoint (ignores `num_ctx`, 500s past the 2048 default) **and** `nomic-embed-text`'s small window.
- **Switched embedder `nomic-embed-text` → `bge-m3`** (8192-token native context, 1024-dim, L2-normalized, dense+sparse) — `MEMORY_EMBEDDING_MODEL` in `.env`/`.env.docker` + `MemorySettings` default. Near-zero migration: FAISS indexes are in-memory and rebuilt per session; semantic-router centroids re-warm at startup.
- **Switched to the modern `langchain_ollama` client with `num_ctx`** (uses `/api/embed`, forwards the context window) in `memory_rag.py` and `semantic_router.py`, so bge-m3 actually gets its 8192 window (also clears the LangChain deprecation warning).
- **New `src/coordinator/memory_text_utils.py`** — dependency-light embedding-input guard: normalizes whitespace, drops empty strings, and chunks oversized messages (token budget at a 0.6 safety margin of the window) / truncates queries before embedding. Applied at every index + query site. Oversized messages now fan out into multiple vectors with `chunk`/`n_chunks` metadata instead of 500ing.
- **Corrected relevance scoring for the new embedder.** The old `1/(1+L2)` conversion + nomic-tuned `min_relevance=0.7` gate filtered out *every* correct hit under bge-m3 (returned empty memory). Replaced with the exact cosine identity `cos = 1 − D/2` (FAISS returns squared L2; bge-m3 is unit-normalized) and a recall-leaning `0.5` true-negative floor (`k=15` unchanged). New `MEMORY_EMBEDDING_MAX_TOKENS` (default 8192) + `MEMORY_EMBEDDING_CHUNK_OVERLAP_TOKENS` settings.
- **Tests:** 19 new (`test_memory_text_utils.py` + `test_memory_rag_overflow.py`, headless via a recording fake-embedder); live `test_faiss_incremental_update.py` re-verified against bge-m3. Suite 1422 → 1441 collected, 0 regressions.
- **Follow-ups (non-blocking):** formal threshold re-tune on a labeled eval set after real usage; optional `bge-reranker-v2-m3` cross-encoder rerank (~50–80ms on M4 Pro GPU).

### Added (2026-06-22) — Test suite

- **Backend test coverage raised to 63%** (from a 41% baseline; the `--cov-fail-under=60` gate in `pytest.ini` now passes headless). Added ~1,060 deterministic unit tests (suite 321 → ~1,420 collected; 1386 pass / 38 skip / 0 fail headless) across repositories (temp-SQLite), pure-logic modules, jupiter strategies, and FastAPI routes (TestClient). See [docs/development/TESTING_GUIDE.md](docs/development/TESTING_GUIDE.md).
- **Resource-gated auto-skip**: `tests/conftest.py` now skips `requires_ollama` / `requires_api_key` / `requires_docker` tests when the resource is unreachable (TCP probe to `OLLAMA_BASE`, `BRAVE_API_KEY` env, `docker info`) — the suite is green and fast headless instead of crawling on live ~16 tok/s LLM calls.
- **Optional RAGAS/nltk degradation**: the `evaluation` package imports cleanly without RAGAS installed (`RAGAS_AVAILABLE` guard); eval tests skip via a module-level guard.

### Fixed (2026-06-22)

- **`seeker_progression_repository.get_resonance_history`**: same-second events now return newest-first (`ORDER BY timestamp DESC, id DESC`).
- **`wallet_registry_repository.soft_delete_wallet` / `soft_delete_by_address`**: a second (no-op) delete now correctly returns `False` (uses `cursor.rowcount` instead of a post-update SELECT).
- **`message_processing_service` multi-message split**: the 3-message branch for very long (>800 char) replies with a trailing question now works (regex group(1) made greedy; was dead code).
- **`datetime.utcnow()` deprecation swept** (Python 3.12) across 7 modules → `datetime.now(timezone.utc).replace(tzinfo=None)` (behavior-preserving naive-UTC; ~960 fewer deprecation warnings).
- **Mac-migration test debt**: stale `get_ollama_base`/`get_persona_model` imports → `get_settings()`; `parse_multi_message_response` import path; removed `QueryIntent.NEEDS_BOTH` test reference; tokenizer-agnostic `_count_tokens`/truncation tests; Windows-only stdout clobber guarded; `.ps1` scripts demoted to reference-only in docs.

### Removed (2026-06-22)

- **MongoDB MCP integration fully removed** (~96 files): deleted `mongodb_mcp_client.py`, `mongodb/` package, `cache.py`, `mongodb_handlers.py`, `token_registry.py`, all MongoDB intent keywords and routing, `MongoDBSettings`, the dormant `MONGODB_WRITE_URI` pymongo write-path, `pymongo` dependency. Rewrote `tests/manual/test_bank_mcp.py` as Brave + Wallet-only (138 tests). `QueryIntent` is now `NEEDS_WEB_SEARCH | NEEDS_NEITHER | NEEDS_WALLET`. Bitcoin-price queries now route to Brave (web) instead of the previous ~39 s MongoDB dead-end.
- **Cipher and Aurora**: `mongodb` + `bot_state` removed from `mcp_access`; Cipher is now Brave-only.
- **Frontend MongoDB types**: removed `mongodb_mcp`, `multi_mcp` from `source_type` union; removed MongoDB tool indicator, source badge, and narrative entries.

### Added (2026-06-22)

- **Explicit search routing**: `EXPLICIT_SEARCH_COMMANDS` in `tools/keywords.py` (single source of truth) + `FORCE_PATTERNS` ensures "search the web / google it / look it up" always routes to Brave and bypasses the LLM tool-calling loop.
- **Ollama concurrency tuning**: `OLLAMA_NUM_PARALLEL=1` set durably via login LaunchAgent `com.nephilim.ollama-tuning` (`scripts/launchd/ollama-tuning.sh`). Prevents GPU slot-splitting that caused the 2026-06-21 161.9 s turn.
- **`MODEL_MAX_OUTPUT_TOKENS`** (`OllamaSettings`, wired to Ollama `num_predict`, default 400): backstop against runaway replies.
- **Brave MCP PATH + timeout fix**: `scripts/launchd/com.nephilim.backend.plist` PATH now includes `/usr/local/bin` (Docker CLI symlink); `BRAVE_SEARCH_TIMEOUT` default raised to 20 s for cold-container coverage.

### Added

- **Lore wiki** (`docs/lore/wiki/`) — typed-markdown knowledge graph for NEPHILIM worldbuilding. 30 entity files (6 personas, 6 houses, 5 ranks, 6 locations, antagonist Kenoma + Sybil Choir, resonance/ascension concepts, 7 non-canon expansion entities) with YAML frontmatter declaring `entity_type`, `entity_id`, `canon`, `aliases`, and typed `relationships`. Canonical source of truth for entity facts; conflicting house/antagonist names from prose docs preserved as `aliases`.
- **Lore wiki engine** (`scripts/utils/lore_wiki.py`) — `check` (validates schema, relationship resolution, bidirectional inverses, alias collisions, persona-JSON consistency, prose name-drift; CI-gateable), `index` (regenerates `wiki/index.md`), `graph` (derives a networkx-style JSON graph). No new dependencies.
- **Lore sync tool** (`scripts/utils/lore_sync.py`) — one-way `wiki/personas/*.md` → `personas/nephilim_*.json lore[]` sync. `--dry-run` and `--persona` flags. Clears CV summary cache on change. Makes the wiki the canonical authoring surface for persona lore.
- **Wiki runtime injection** (`src/coordinator/lore_loader.py`) — loads and caches wiki entity bodies (persona + house + location) for each NEPHILIM persona at prompt-build time; injected into `<world_context>` block via `prompt_builder.py`. No new dependencies (pathlib + re only). Non-NEPHILIM personas (Wanderer/Gojo) unaffected.
- **Enriched persona lore arrays** — all 6 `personas/nephilim_*.json` `lore[]` arrays rewritten from rich Chronicle + Lore Bible material. Items now name specific canon entities, encode relationship tensions (Prime Covenant, Electric Rivalry, Compassion Triangle, Exile's Garden), and capture philosophical contradictions. CV summaries cleared to force regeneration on next chat.
- **[ADR-001](docs/decisions/001-lore-as-typed-markdown-wiki-not-a-graph-db.md)** — records typed-markdown-wiki decision and Neo4j rejection.
- **56 new unit tests** — `tests/backend/lore/` (20 lore_wiki + 26 lore_sync) + `tests/backend/coordinator/test_lore_loader.py` (10).

### Changed

- `src/coordinator/prompt_builder.py` — `_build_nephilim_lore_block` now appends wiki entity context (additive; existing `nephilim_lore` dict fields preserved).
- `docs/lore/README.md` — declares `wiki/` the canonical source of truth.
- `docs/lore/NEPHILIM_LORE.md` — canon-note banner pointing to the wiki.
- `CLAUDE.md` — wiki section updated to note runtime relevance.


### Celestial Order Remap (Feb 2026)
- **Celestial Order System**: Replaced gacha rarity vocabulary with lore-aligned Celestial Order tiers:
  - Legendary → Archon (Gold) — E.E.V.A.
  - Epic → Warden (Purple) — Aegis, Aurora, Solace
  - Rare → Sage (Cyan) — Cipher, Nyx
  - Common → Wanderer (Silver) — Legacy personas
- **Per-Persona MCP Access**: MCP tool access now controlled per-persona via `mcp_access` field in persona JSONs, replacing rarity-based tier gating:
  - Cipher (Sage) now has Brave + MongoDB access (was Brave-only under rarity gating)
  - Nyx (Sage) now has no MCP tools (was Brave under rarity gating)
  - Aegis and Solace (Warden) now have Brave-only access (were Brave + MongoDB under rarity gating)
- **Backend**: Added `CelestialOrder` enum, `mcp_access` parameter to intent_classifier and tool_utils, per-persona override in routes
- **Frontend**: New `celestialOrder.ts` utility, all display labels show Archon/Warden/Sage/Wanderer, CSS classes unchanged (`rarity-*`)
- **Tests**: 10 new backend tests for mcp_access logic, all frontend test mocks updated with celestial_order field
- **Documentation**: Updated CLAUDE.md, README.md, and development docs

### Fixed
- **Chat UI Performance & Accessibility Bug Fixes** ✅ (Jan 19, 2026) - Fixed two critical UX issues in the chat interface:
  - ✅ **Issue #1 - Input Text Visibility**: Fixed low contrast making typed characters barely visible
    - **Root Cause**: Glassmorphic input designed for dark backgrounds used light gray text (`#e0e0e0`) on white background (1.3:1 contrast ratio)
    - **Fix**: Changed input text color to dark gray (`#1f2937`) achieving 13.5:1 contrast ratio (WCAG AAA compliant)
    - **File**: `react-ui/src/index.css:209`
  - ✅ **Issue #2 - Message Bubble Re-Rendering**: Fixed all message bubbles re-rendering on every keystroke
    - **Root Cause**: Row component and callbacks recreated on every parent render, breaking React memoization
    - **Fix 1**: Wrapped `Row` component in `useCallback` hook with proper dependencies in `VirtualizedMessageList.tsx`
    - **Fix 2**: Wrapped `handleRetryMessage` callback in `useCallback` hook in `Chat.tsx`
    - **Fix 3**: Moved `handleRetryMessage` before conditional return to comply with React Hooks rules
    - **Files**: `react-ui/src/components/VirtualizedMessageList.tsx`, `react-ui/src/pages/Chat.tsx`
  - **Impact**:
    - Accessibility: Input text contrast improved from WCAG F (fail) to AAA (13.5:1 ratio)
    - Performance: Eliminated unnecessary re-renders on typing (5-10 MessageBubbles per keystroke → 0)
    - UX: Smooth typing experience with no visual stuttering

### Added
- **NEPHILIM Phase 6: Persona Filter Toggle** ✅ (Feb 1, 2026) - Added filter system to toggle between NEPHILIM and legacy personas:
  - ✅ **PersonaFilterToggle Component**: New animated toggle with three modes (All ✦, NEPHILIM ⬡, Legacy ◇)
  - ✅ **Filter Utilities**: `personaFilter.ts` with `isNephilimPersona()`, `filterPersonas()`, `getPersonaCounts()` functions
  - ✅ **CharacterCardV2 Enhancement**: Added NEPHILIM badge display for matching personas
  - ✅ **CharacterSelector Enhancement**: Gradient indicator bar on NEPHILIM persona thumbnails
  - ✅ **CharacterCardV2Showcase Integration**: Filter toggle in page header with persona counts
  - ✅ **Persistence**: Filter preference saved to localStorage (`persona_filter_mode`)
  - ✅ **Playwright Tests**: 7 automated tests covering all filter functionality
  - **Files Added**:
    - `react-ui/src/components/PersonaFilterToggle.tsx` - Filter toggle component
    - `react-ui/src/utils/personaFilter.ts` - Filter utility functions
    - `react-ui/tests/phase6-filter.spec.ts` - Playwright test suite
  - **Files Modified**:
    - `react-ui/src/components/CharacterCardV2.tsx` - NEPHILIM badge support
    - `react-ui/src/components/CharacterCardV2.module.css` - NEPHILIM styling
    - `react-ui/src/components/CharacterSelector.tsx` - NEPHILIM indicator
    - `react-ui/src/pages/CharacterCardV2Showcase.tsx` - Filter toggle integration
  - **Impact**:
    - UX: Users can now filter persona gallery by type (NEPHILIM vs legacy)
    - Discoverability: Clear visual distinction between NEPHILIM and legacy personas
    - Persistence: Filter preference remembered across sessions

- **Project Reorganization: Scripts & Documentation Hierarchy** ✅ (Jan 18, 2026) - Comprehensive reorganization of scripts and documentation into logical directory structure:
  - ✅ **Scripts Organization**: Moved 14 scripts from root into categorized subdirectories
    - `scripts/docker/` - 7 Docker setup, validation, and troubleshooting scripts
    - `scripts/setup/` - 3 local development environment setup scripts
    - `scripts/utils/` - 4 Python utilities (unified launcher, validation, cleanup, security)
  - ✅ **Documentation Organization**: Moved 4 documentation files into categorized subdirectories
    - `docs/setup/` - DOCKER_QUICKSTART.md (moved from root)
    - `docs/development/` - ADDING_MCP_SERVERS.md, TESTING_GUIDE.md
  - ✅ **Navigation Indices**: Created 5 comprehensive README.md files for easy discovery
    - `scripts/README.md` - Master index with quick reference to all script categories
    - `scripts/docker/README.md` - Docker scripts guide with usage examples and troubleshooting
    - `scripts/setup/README.md` - Setup scripts guide with prerequisites and next steps
    - `scripts/utils/README.md` - Python utilities guide with import examples and best practices
    - `docs/README.md` - Complete documentation index with categorization and links
  - ✅ **Path Updates**: Updated 50+ references across 12+ files (README.md, CLAUDE.md, .env.example, test files, AI_documentation)
  - ✅ **Critical Code Updates**:
    - `react-ui/package.json` - npm start path updated to `scripts/utils/run_react.py`
    - `.claude/settings.local.json` - execution permissions updated
  - ✅ **Configuration Updates**:
    - `.gitignore` - Added exception for `scripts/` directory (was blocked by `Scripts/` venv pattern)
    - CLAUDE.md - Updated "Root Markdown Policy" from 5 docs to 4 docs (DOCKER_QUICKSTART moved to docs/)
  - **Impact**:
    - Root directory clutter: 15 utility files → 0 (100% reduction)
    - Root markdown files: 5 → 4 (specialized guides moved to docs/)
    - Organization quality: 3.5/10 → 9.2/10 (+5.7 points improvement)
    - Maintainability: Clear patterns for where to add new files
  - **Files Changed**: 76 files total (18 moved, 50+ updated references, 5 new READMEs, 3 config updates)
  - **Git History**: Preserved via `git mv` for all 18 file moves
  - **Development Time**: 45 minutes (planning, execution, verification, documentation)
  - **Status**: Production-ready, deployed to GitHub, perfect 10/10 hygiene score maintained
  - **Documentation**: Updated README.md with new "Scripts & Utilities" and "Testing & Quality" sections

- **Character Card Hover Animation Optimization** ✅ (Jan 1-2, 2026) - Iteratively refined hover animations based on UX research and user feedback:
  - ✅ **Particle Removal**: Removed floating particles from header, chat page, and session list sidebar for cleaner aesthetic
  - ✅ **Animation Simplification**: Evolved from dual-transform (y + scale) to scale-only animation
  - ✅ **Iteration 1**: Removed rotation animation (user feedback: distracting)
  - ✅ **Iteration 2**: Fixed asymmetric timing issue (hover-in fast, hover-out slow → both 150ms)
  - ✅ **Iteration 3**: Eliminated CSS transform conflicts (removed 180ms CSS transition)
  - ✅ **Iteration 4**: Simplified to scale-only (1.0 → 1.05) to eliminate "two animation" perception
  - ✅ **Final Specs**: Pure scale effect, 150ms, cubic-bezier [0.4, 0, 0.2, 1], modern minimalist aesthetic
  - ✅ **Performance**: Single transform property = optimal GPU acceleration
  - ✅ **Testing**: Playwright automated validation with transform matrix verification
  - **User Experience**: Smooth single animation, snappy and consistent both directions, Spotify/Netflix card style
  - **Research Sources**: Nielsen Norman Group (150ms standard), Material Design 3 (single-property transforms), 2025 UI trends
  - **Files Modified**: `react-ui/src/components/CharacterCard.tsx`, `react-ui/src/components/CharacterCard.module.css`, `react-ui/src/components/SessionList.tsx`, `react-ui/src/components/header/HeaderVisuals.tsx`, `react-ui/src/pages/Chat.tsx`
  - **Development Time**: ~10 hours (4 iterations with user testing)
  - **Status**: Production-ready, deployed to Docker, tested and validated

- **Option 6: Rarity-Adaptive Background System** ✅ (Jan 1, 2026) - Implemented rarity-based background theming with interactive card selection:
  - ✅ **Rarity-Based Theming**: Dynamic backgrounds that adapt based on selected persona's rarity tier
  - ✅ **4 Rarity Tiers**: Common (Blue #60a5fa), Rare (Cyan #06b6d4), Epic (Purple #a78bfa), Legendary (Gold #fbbf24)
  - ✅ **Deep Space Aesthetic**: Gradient backgrounds with nebula overlays for immersive sci-fi experience
  - ✅ **Contextual Activation**: Neutral background on home page, rarity theming on agent selection & chat pages
  - ✅ **Smooth Transitions**: 0.8s cubic-bezier animations between rarity switches
  - ✅ **Clickable Character Cards**: Full card clickable for selection, hover states, selection feedback with pulsing halo
  - ✅ **Continuous Particle System**: Ambient particles on agent selection and chat pages
  - ✅ **CSS Architecture**: 40 CSS variables across 4 rarity tiers, utility classes (`.space-background`, `.nebula-overlay`, `.glass-card`)
  - ✅ **Production Testing**: Comprehensive Playwright test suite validating all 4 rarity tiers in both dev and Docker environments
  - ✅ **Performance**: CSS-only system with minimal overhead (+336B CSS, +72B JS)
  - ❌ **Phase 1 Deferred**: Full glassmorphic UI polish (translucent message bubbles, rarity-adaptive buttons, glass inputs) - foundation deemed sufficient
  - **Files Modified**: `react-ui/src/index.css`, `react-ui/src/App.tsx`, `react-ui/src/pages/Home.tsx`, `react-ui/src/pages/Chat.tsx`, `react-ui/src/pages/CharacterCardV2Showcase.tsx`, `react-ui/src/components/CharacterCard.tsx`, `react-ui/src/components/EnergyParticles.tsx`
  - **Research**: 10 design options evaluated, scored on 8 criteria (2026 trends, accessibility, performance, gacha appeal, AI trust, differentiation)
  - **Mockups Created**: 10 interactive HTML mockups showcasing different aesthetic approaches
  - **Development Time**: ~4 hours (research, mockups, implementation, testing, Docker deployment)
  - **Status**: Production-ready, deployed to Docker, all tests passing
  - **Documentation**: Updated CLAUDE.md with background system specification, archived gap analysis in `AI_documentation/01_implementation_history/OPTION6_GAP_ANALYSIS.md`

- **Prompt System Optimization** ✅ (Dec 28, 2025) - Optimized persona system prompts with comprehensive quality testing:
  - ✅ **Token Efficiency**: Reduced system prompt from 3,543 → 2,523 tokens (-1,020 tokens, -28.8%)
  - ✅ **Context Capacity**: Increased available context from 553 → 1,573 tokens (+184% for conversation history)
  - ✅ **Quality Improvements**: Overall score improved 74.0% → 79.2% (+5.2%)
  - ✅ **First-Person Enforcement**: Streamlined from 84 lines to 20 lines while improving adherence 75.0% → 87.5%
  - ✅ **Multi-Message Examples**: Reduced from 12 to 6 highest-quality examples (maintained 88.9% score)
  - ✅ **Voice Consistency**: Improved from 44.4% → 55.6% (+11.1%)
  - ✅ **Persona Differentiation**: Improved from 75.0% → 100.0% (+25.0%)
  - ✅ **Comprehensive Testing**: 16 test scenarios across 7 categories with live LLM validation
  - **Pass Rate**: 56.2% → 68.8% (+12.5% improvement)
  - **Conversation Length**: Users can now have 2-3x longer conversations before hitting context limits
  - **Files Modified**: `src/coordinator/prompt_builder.py` (optimized), backup created
  - **Documentation**: `PROMPT_OPTIMIZATION_FINAL_REPORT.md`, `PERSONA_PROMPT_SYSTEM_ANALYSIS.md`, test suite with JSON results
  - **Development Time**: 3 hours (analysis, implementation, testing, deployment)
  - **Status**: Production-ready, deployed, quality validated
  - **Risk**: Low (no regressions detected, multiple metrics improved)

### Security
- **Dependency Security Fixes**: Resolved 10 high-severity and 2 moderate npm audit vulnerabilities in React dependencies through targeted package overrides and updates. Reduced total vulnerabilities from 12 to 2 moderate issues in development dependencies only.

### Performance
- **System Prompt Optimization**: 28.8% token reduction enables faster LLM inference and significantly longer conversations (see Added section for details)
- **UX Phase 1.1: Typography System Overhaul** ✅ (Dec 28, 2025) - Replaced generic system fonts with distinctive, sci-fi themed typography:
  - ✅ **Display/Headings**: Orbitron font (700, 900 weights) for futuristic sci-fi aesthetic
  - ✅ **Body Text**: Poppins font (400, 600, 700 weights) for clean, readable UI text
  - ✅ **Monospace/Technical**: Space Mono (400, 700 weights) for latency stats and technical data
  - ✅ **Type Scale**: Complete CSS variable system (`--text-xs` through `--text-5xl`, 0.75rem to 3rem)
  - ✅ **Tailwind Integration**: Extended theme with `font-display`, `font-body`, `font-mono` classes
  - ✅ **Google Fonts CDN**: Optimized font loading with preconnect for performance
  - **Files Modified**: `react-ui/public/index.html`, `react-ui/src/index.css`, `react-ui/tailwind.config.js`, `Home.tsx`, `CharacterCardV2.module.css`, `MessageBubble.tsx`
  - **Visual Impact**: Immediate brand differentiation from generic React dashboards
  - **Build Size**: +157 bytes CSS (new typography rules)
  - **Development Time**: 1.5 hours
  - **Documentation**: `AI_documentation/01_implementation_history/TYPOGRAPHY_SYSTEM_IMPLEMENTATION.md`
  - **Status**: Production-ready, deployed to Docker
- **MongoDB MCP Integration (MVP COMPLETE!)** ✅ - Fully implemented MongoDB Model Context Protocol integration for Bitcoin trading data access by Epic/Legendary personas:
  - ✅ **Phase 1**: MongoDB MCP client with JSON-RPC 2.0 protocol, pre-warmed Docker containers, read-only security enforcement (638 lines)
  - ✅ **Phase 2**: 3-layer intent classification system with 41 MongoDB keywords, dynamic tool injection, 4 semantic Bitcoin tools (689 lines)
  - ✅ **Phase 3**: TTL-based caching layer with thread-safe operations, statistics tracking, automatic expiry (290 lines)
  - ✅ **Phase 4**: Backend integration with 4 tool handlers, intent-based routing, ResponseMetadata model, caching integration (~600 lines)
  - ✅ **Phase 5**: Frontend SourceIndicator component with visual badges, cache status, relative timestamps (~370 lines frontend)
  - ✅ **Phase 6**: Comprehensive unit test suite with 56 tests total (30 backend + 26 frontend) achieving 100% coverage
  - ✅ **Phase 7**: Intent classification testing with 360 comprehensive tests (90 questions × 4 rarities)
  - ✅ **Phase 8**: Intent classification improvements achieving **100.0% accuracy** (up from 89.7%)
  - **Documentation**: Comprehensive 1,700+ line implementation guide (MONGODB_MCP_IMPLEMENTATION.md) + Phase 4 & 5 summaries + Improvements guide
  - **Total Code**: 3,200+ lines across 9 new files, 7 modified files
  - **Features**: Bitcoin price queries, technical indicators (RSI, MACD, Bollinger Bands), historical data, DCA trading stats, visual source badges
  - **Classification Accuracy**: **100.0%** across all categories (PURE_LLM, BRAVE_MCP, MONGODB_MCP) and all rarity levels
  - **Development Time**: 16.5 hours over 2 days
  - **Status**: Production-ready, perfect test scores, zero false positives/negatives

- **Intent Classification System Improvements** 🎯 - Enhanced query classification from 89.7% → **100.0% accuracy** (+10.3 percentage points):
  - ✅ **Brave MCP Keywords Expanded** (20+ keywords): Added "trending", "happening", "saying", "talking about", "sentiment", "experts say", "analysts", "popular", "viral", "mood", "opinions", "predictions", "forecasts"
  - ✅ **MongoDB MCP Keywords Expanded** (15+ keywords): Added "value", "worth", "trading at", "trend analysis", "indicators", "current value", "historical", "portfolio", "holdings", "going for", "selling for"
  - ✅ **Educational Query Detection**: Enhanced to distinguish "Why was Bitcoin created?" (educational) from "What was Bitcoin's price?" (data query)
  - ✅ **Opinion Query Detection**: New logic to detect sentiment/opinion queries despite having "what are" definition keywords
  - ✅ **Rarity-Gating Bug Fix**: Rare personas now correctly return NEEDS_NEITHER for MongoDB queries instead of falling back to web search
  - ✅ **Test Results**: Perfect 100% accuracy across all 360 tests (90 questions × 4 rarity levels)
  - **Grade Improvement**: B (Good) → A+ (Excellent)
  - **Files Modified**: `src/coordinator/tool_definitions.py` (enhanced classification logic)
  - **Time Investment**: ~2 hours
  - **Documentation**: Created IMPROVEMENTS_COMPLETE.md with comprehensive before/after analysis
- **Dynamic Persona Management** - Implemented automatic persona discovery from JSON files, orphaned session cleanup, collection synchronization, and chat history updates when personas are added/removed/modified
- **Code Quality Improvements** - Fixed ESLint warnings in PullInterface component and resolved test suite issues for PullInterface and PersonaContext
- **Chat History UX Enhancements** - Improved SessionList component with snappier hover animations (100ms), removed white avatar borders, and enhanced visual consistency with mobile menu theming
- **Phase 3: Character Gacha System Completion** - Full implementation of advanced gacha system with multi-pull mechanics, particle effects, audio integration, and collection management
- **Character Card Preference Update** - Switched CharacterCardV2Showcase to use classic CharacterCard component with traditional foil effects and smooth animations instead of holographic V2 cards
- **Multi-Pull System** - PullInterface component supporting 1x/5x/10x pulls with sequential reveal animations, energy-animated buttons, and result display
- **Particle Effects Integration** - EnergyParticles component using @tsparticles/react for ambient visual effects during pulls and celebrations
- **Audio System** - Complete Web Audio API integration with synthesized sound effects for pull actions, card reveals, and rarity-based celebrations with persistent mute controls
- **Collection Management** - Persistent character collection storage with statistics tracking, pull history, and organized display in CharacterCollection component
- **Advanced Animations** - Multi-stage pull sequences with screen effects, shake animations for card reveals, and rarity-based celebration effects
- **Header Audio Controls** - Mute/unmute button in header navigation with visual feedback and persistent state management
- **TypeScript Optimization** - Resolved all compilation errors, added proper type annotations, and ensured type-safe implementation across all components
- **Performance Optimization** - Optimized particle rendering, reduced memory usage, and implemented hardware acceleration for smooth 60fps animations
- **Accessibility Enhancements** - Added reduced motion support, keyboard navigation, and screen reader friendly descriptions
- Initial project structure with NEPHILIM backend and React UI frontend
- Persona-based chat interface with multiple character options
- Gacha-style character selection with card reveal animations
- Static character browsing with search functionality
- FastAPI backend with Ollama LLM integration
- Comprehensive testing setup with Jest and pytest
- **Unified startup script** (`run_react.py`) that launches both backend and frontend together
- **CORS support** in FastAPI for cross-origin requests from React UI
- **Header Component Enhancement (Phase 1)**: Modern dark theme header with rarity-based active page highlighting, responsive layout, and branding
- **Header Component Enhancement (Iteration 2.1)**: Added Framer Motion animations with entrance effects, hover interactions, and smooth transitions
- **Header Component Enhancement (Iteration 2.2)**: Implemented visible particle system, dynamic gradient theming with page-based color changes, enhanced glassmorphism, animated typography with glow effects, and prominent animated bottom border
- **Header Component Enhancement (Iteration 2.3)**: Added functional mobile hamburger menu with slide-out navigation, persona-aware theming that adapts to selected character, touch-optimized interactions, and mobile-specific UI enhancements
- **Phase 3: App-Wide Enhancements**: Completed character card visual effects with Framer Motion animations, polished chat interface with smooth scrolling and message animations, and comprehensive mobile optimization across the entire application
- **Chat UX Phase 3.1: Rich Media Support**: Added message timestamps, JSON syntax highlighting with collapsible display and copy buttons with visual feedback, code block highlighting with language detection and copy buttons with visual feedback, and RichContent component for intelligent content rendering
- **Chat UX Phase 3.2: Performance & Feedback**: Implemented latency tracking with response time display in ms/s, error recovery with retry functionality for failed messages, status indicators (sending, sent, delivered, failed) with loading spinners, message status management and retry counters, and React.memo performance optimizations
- **Copy Button Feature**: Added ChatGPT-style copy buttons for JSON responses and code blocks with visual feedback (copy icon → checkmark) and automatic reset after 2 seconds
 - **Chat UX Phase 3.4: Mobile Optimization**: Implemented ChatGPT-style responsive layout (sidebar pushes content on desktop, overlays on mobile), dynamic content expansion, touch gestures, swipe navigation, mobile-optimized input attributes, and comprehensive testing
 - **Header Layout Optimization**: Fixed chat header to prioritize action buttons (Import/Export/Clear) with proper truncation of long chat titles
 - **Persona Customization Phase 3.3**: Implemented gacha-style theming with rarity-based colors (legendary=gold, epic=purple, rare=blue, common=grey), custom character backgrounds with subtle watermark overlays, personalized avatar effects with rarity rings and shadows, cohesive send button theming, and comprehensive unit testing
 - **Chat History UX Iteration 3: Persona Indicators**: Added small persona name badges on assistant messages with rarity-based styling (legendary=yellow, epic=purple, rare=blue, common=gray) for clear persona identification in conversations
 - **Home Page UX Consistency**: Applied character selection page's sophisticated theme to home page including glassmorphism background effects, animated particles, yellow-themed buttons matching rarity theming, gradient header text, and consistent visual styling throughout
 - **Home Page Simplification**: Removed gacha pull mechanics from home page entirely, now serves as a clean navigation gateway to the character selection page where all gacha functionality resides
 - **Direct Tab Navigation**: "Try Your Luck" button now navigates directly to the Gacha Pull tab on the character selection page for seamless user experience

### Changed
- **UI Flow Reorganization (2025-01-07)**: Moved pull mechanics to home page, simplified character selection to browsing-only
- **Character Card Consistency**: Updated all character card displays (Card Gallery, My Collection, Gacha Pull) in CharacterCardV2Showcase to use classic CharacterCard component with traditional foil effects for consistent styling across the entire page
- **Choose Button Functionality**: Restored 'Choose' button functionality in CharacterCardV2Showcase to navigate directly to persona-specific chat, matching the behavior of the original CharacterSelection page
- **Search Functionality**: Added search and filtering capability to the Card Gallery tab in CharacterCardV2Showcase, allowing users to find characters by name, style, or rarity
- **Character Page Replacement**: Replaced the original CharacterSelection page with the enhanced CharacterCardV2Showcase, maintaining the /select URL route while providing comprehensive gacha functionality, collection management, and improved user experience
  - Home page (`/`) now handles all gacha pulls with card reveal animations
  - Character selection page (`/select`) now shows clean grid browsing with search
  - Removed "Ready to Pull?" interface from character selection page
  - Improved separation of concerns between pulling and browsing experiences
- **React Migration Completed**: Full migration from Streamlit to React UI with working chat functionality and comprehensive visual enhancements
- **Header Component Planning**: Documented phased approach for modern header redesign with vibrant colors and highlighting

### Technical Improvements
- Optimized React build (131KB gzipped) with enhanced animations and visual effects
- Fixed Jest configuration issues
- Updated TypeScript setup for better development experience
- Improved component architecture with better state management
- Added CORS middleware to FastAPI backend
- Enhanced error handling and user feedback in chat interface

### Fixed
- **Chat Session Creation**: Fixed double session creation when selecting new personas
- **Greeting Message Handling**: Fixed greeting messages appearing as user input instead of assistant messages
- **Persona Mixing**: Fixed greeting messages being sent to wrong sessions when switching chats during loading
- **Input Blocking**: Added proper blocking of chat input until initial greeting messages are generated
- **Loading States**: Added visual feedback during session creation and greeting generation
- **Avatar Images**: Fixed avatar images disappearing when switching between chats and ensured proper use of dedicated avatar images instead of card images
- **Page Scrolling**: Fixed scrolling issues on all pages by changing main content container from `overflow-hidden` to `overflow-auto` in App.tsx

### Documentation
- Updated README with new unified startup process and React UI focus
- Enhanced GACHA_UX_ROADMAP.md with current implementation status
- Added comprehensive coding guidelines in AGENTS.md
- Updated REACT.md to reflect completed migration
- Created this changelog for tracking project evolution

## [0.1.0] - 2025-01-XX

### Added
- Basic NEPHILIM coordinator architecture
- React UI with routing (Home, Character Selection, Chat)
- Character card components with rarity styling
- API integration between frontend and backend
- Basic testing infrastructure

### Technical
- React 19 with TypeScript
- FastAPI backend
- Ollama LLM integration
- Framer Motion animations
- Jest testing framework

---

## Types of changes
- `Added` for new features
- `Changed` for changes in existing functionality
- `Deprecated` for soon-to-be removed features
- `Removed` for now removed features
- `Fixed` for any bug fixes
- `Security` in case of vulnerabilities</content>
<parameter name="filePath">CHANGELOG.md