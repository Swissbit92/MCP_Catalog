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

- [ ] **Persona architecture simplification (eval-first)** — [ADR-005](decisions/005-persona-architecture-simplification-eval-first.md). **Phase A BUILT + legacy baseline FROZEN 2026-06-27** (`tests/evaluation/persona_eval/`): distinctiveness attribution **0.393** vs 0.143 random; aurora/gojo most distinct (0.62), **eeva/aegis/solace blur at 0.25** (the Phase-B target); flatness low (1.8%). Phases B/C not started. Persona prompt is over-saturated: ~3,200–3,600 tokens / ~64 directives (a local 24B reliably follows ~3–5; exponential decay past that), rules repeated 4–5×, ~25% duplicated lore, and a keyword `persona_voice` scorer that can't see real voice — this is why the HERMES Phase 3 voice fix failed. Plan: **A)** replace the scorer with a trustworthy human + adversarial held-out eval (cross-persona distinctiveness); **B)** lean the prompt to ~900–1,200 tokens (dedupe, enable existing on-demand lore retrieval instead of static frontloading, psych labels→behavioral, promote examples, post-history re-anchor; fix voice via examples not specs); **C)** only if short — voice-exemplar RAG on bge-m3, per-persona LoRA (gated on safetensors), DRY sampling via backend swap. **Mandatory acceptance gate:** freeze a per-persona legacy baseline first, re-test every persona after simplification; any persona worse than baseline must reach parity or stay on the legacy prompt — no global default flip until ALL match-or-beat baseline; default-OFF flags make revert instant.
- [ ] Raise coverage of the live-LLM orchestration services (`query_handler_service`, `chat_session_service`, `tool_calling_service`) — either by mocking the LLM/tool boundary or by counting the `requires_ollama` suite. Main remaining dark area (overall 63%, gate 60%).

## Later (exploratory)

- [ ] **Known gap — strategy position tracking is a no-op** (surfaced 2026-06-23 during the MongoDB-removal doc reconciliation). When the MongoDB dual-write was removed, position open/close events and HITL approval decisions became **log-only** — the former `open_positions` / `approval_decisions` collections were not re-homed to SQLite. As a result `StrategyService.has_open_position()` always returns `False` (fail-open), so the double-entry guard is effectively disabled and the HITL audit trail isn't persisted. **Harmless while the wallet/strategy execution path isn't trading live** — but it MUST be wired to SQLite (a `wallet_positions` table + `record_trade`-style writes) before that path goes live. See the note in [architecture/WALLET_METADATA.md](architecture/WALLET_METADATA.md) (Trade Persistence) and [ADR-002](decisions/002-remove-mongodb-mcp.md).

## Shipped

See [CHANGELOG.md](../CHANGELOG.md).
