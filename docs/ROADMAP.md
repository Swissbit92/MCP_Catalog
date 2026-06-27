---
title: Roadmap
status: active
created: 2026-04-19
last_reviewed_on: 2026-06-23
review_in: 3 months
applies_to: nephilim
---

# Roadmap

Near-term dated items only. Strategic direction lives in the ecosystem [VISION.md](../../VISION.md).

## Next (this month)

- [x] **MongoDB MCP removal — stale-artifact cleanup** (2026-06-22): the core removal landed earlier (commit `642d1ed3`, [ADR-002](decisions/002-remove-mongodb-mcp.md)); this pass cleared the leftover debt — corrected the `solana_trade_history` tool description (was "Reads from MongoDB"), de-mongodb'd the two legacy manual test harnesses (`test_all_personas_intent.py`, `test_live_all_personas.py`: 30→20 queries, dropped the crypto/mongodb rows; offline 120/120 PASS), repointed `test_bank_core.py`/`scoring_engine.py`/`api_client.py`/`comprehensive_persona_test.py` off `mongodb_mcp`, repurposed the frontend `searchHeuristics` "MongoDB" test (Bitcoin price now web-searches; 11/11 PASS), and refreshed `NEPHILIM_REFERENCE.md`/`development/API_REFERENCE.md`/`development/TESTING_GUIDE.md` + removed stale `.pyc`.
- [x] Fixed 3 latent bugs surfaced by the coverage push (2026-06-22): `seeker_progression_repository.get_resonance_history` tie ordering (added `, id DESC`); `wallet_registry_repository.soft_delete_wallet` + `soft_delete_by_address` double-delete (now use `cursor.rowcount`); `message_processing_service` 3-message split (regex made greedy). All previously `xfail`-documented tests now pass normally.

## Soon (next quarter)

- [x] **Persona architecture simplification (eval-first)** — [ADR-005](decisions/005-persona-architecture-simplification-eval-first.md). **Phase A BUILT + legacy baseline FROZEN 2026-06-27**, then **Phase B SHIPPED 2026-06-27 — acceptance gate PASSED 7/7.** The lean exemplar-first / voice-last builder (`PERSONA_LEAN_PROMPT`, default OFF + per-persona `PERSONA_LEAN_PROMPT_PERSONAS` allowlist) + a per-persona `voice_signature` for all 7 personas; prompts **65–69% smaller** (eeva 2935→1040, aegis 2501→827, solace 2432→840 tok). Candidate vs frozen legacy: overall distinctiveness attribution **0.393 → 0.732** (random 0.143), flatness 1.8%→0% / grounding 4.8%→0%; per-persona every persona match-or-beat (the blur cluster eeva/aegis 0.25→0.75, solace 0.25→0.625), 0 regressions. The legacy builder stays intact behind the flag (instant revert). **Phase C not needed.** **Blind A/B confirmed 2026-06-27** (`blind_judge.py`, 7 arm-blinded judges, 84 pairs): candidate 67/84 (79.8%, p≈0), no persona regressed — a second independent instrument agreeing with the attribution metric.
- [ ] **Companion memory & continuity (eval-first)** — [ADR-006](decisions/006-companion-memory-and-continuity-eval-first.md). **The next nephilim track** — persona *voice* is treated as done (ADR-005); the frontier is the companion-depth layer (memory, emotional-state persistence, cross-session continuity) that defines the P1 vision. Scoped 2026-06-27 from a 3-agent research pass (1 internal map + 2 external SOTA). Eval-first, staged, flag-gated default-OFF, A/B'd, reusing bge-m3+SQLite+FAISS (no new infra, local-first). Phases: **0)** prereqs+observability (persist the in-memory FAISS store across restarts; log *assembled*-prompt token size; align committed flag defaults to the validated prod config; extend the eval harness with factual-recall/contradiction(PICon)/continuity probes; freeze baselines) → **1)** two-level memory (rolling narrative summary + SQLite fact/triplet store, dedup-on-write recency-wins, FAISS retrieval; `MEMORY_FACTS_ENABLED`) → **2)** persistent PAD emotional state per (persona,user), independent stance not mirroring (`EMOTION_STATE_ENABLED`) → **3)** end-of-session reflection + unresolved-thread bridging, no proactive outreach (`REFLECTION_ENABLED`) → **4)** ethical friction (anti-sycophancy core-beliefs, graceful exit, crisis→resource routing per NY law). **Out of scope:** control vectors / persona LoRA / llama-server migration (blocked or unproven for named-character voice), full MemGPT/Letta (overkill), per-turn reflection, engagement-maxing/love-bombing/proactive-clinging. Latency-budgeted (generation is the bottleneck; reflection async, emotion-classify cheap). Same acceptance gate as ADR-005: freeze baselines first, per-feature match-or-beat-or-keep-OFF, instant revert.
- [ ] Raise coverage of the live-LLM orchestration services (`query_handler_service`, `chat_session_service`, `tool_calling_service`) — either by mocking the LLM/tool boundary or by counting the `requires_ollama` suite. Main remaining dark area (overall 63%, gate 60%).

## Later (exploratory)

- [ ] **Retire the legacy persona prompt builder** (`_build_system_prompt_legacy` + dispatcher in `prompt_builder.py`) — ADR-005 Phase B soak-exit. **Do NOT remove before the soak gate passes.** Earliest review ~2026-07-11 (≥2 weeks live on `PERSONA_LEAN_PROMPT=true`). Exit criteria, ALL required: (a) ≥2 weeks live-stable with no voice/quality complaints; (b) no rise in the first-person LLM-repair trigger rate or deterministic-guard catches (tool-leak/fabrication) vs the legacy era; (c) the blind A/B + attribution gates still hold on a re-run. Until then the legacy builder stays as the instant-revert path. When retiring: delete the legacy builder + the flag dispatch, make lean unconditional, drop the now-dead `PERSONA_LEAN_PROMPT*` settings, and re-baseline.

- [ ] **Known gap — strategy position tracking is a no-op** (surfaced 2026-06-23 during the MongoDB-removal doc reconciliation). When the MongoDB dual-write was removed, position open/close events and HITL approval decisions became **log-only** — the former `open_positions` / `approval_decisions` collections were not re-homed to SQLite. As a result `StrategyService.has_open_position()` always returns `False` (fail-open), so the double-entry guard is effectively disabled and the HITL audit trail isn't persisted. **Harmless while the wallet/strategy execution path isn't trading live** — but it MUST be wired to SQLite (a `wallet_positions` table + `record_trade`-style writes) before that path goes live. See the note in [architecture/WALLET_METADATA.md](architecture/WALLET_METADATA.md) (Trade Persistence) and [ADR-002](decisions/002-remove-mongodb-mcp.md).

## Shipped

See [CHANGELOG.md](../CHANGELOG.md).
