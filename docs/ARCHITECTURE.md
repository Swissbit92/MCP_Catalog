---
title: Architecture
status: active
created: 2026-04-19
last_reviewed_on: 2026-07-04
review_in: 6 months
applies_to: nephilim
---

# Architecture

Reference-style: tables and diagrams, not prose narratives. A local-first,
persona-driven chat platform — FastAPI backend + React 19 frontend + local Ollama,
SQLite for persistence, FAISS for semantic memory.

## System context

```
[User: web UI / Telegram gateway]
        │  HTTP (session API)
        ▼
   nephilim FastAPI coordinator ──▶ Ollama (local LLM + bge-m3 embeddings)
        │            │
        │            ├──▶ Brave Search (ephemeral Docker, per-persona mcp_access)
        │            └──▶ Jupiter DEX / Solana wallet (long-running Docker)
        ▼
   SQLite (chats, progression, wallets)  +  FAISS (session/lore vectors)
```

## Components

Layered: **routes → services → repositories → models**, mirrored on the frontend.

| Component | Responsibility | Module |
|-----------|----------------|--------|
| API routes | HTTP endpoints: chat, sessions, personas, nephilim, auth, wallet | `src/coordinator/routes/` |
| Chat-turn orchestration | Per-turn phase pipeline (load identity → build prompt → select history → generate → persist → post-updates), typed `ChatDeps`/`ChatTurnState` | `services/chat_session_service.py` |
| Query routing | Intent → wallet / brave / agentic / pure-LLM; wallet ground-truth injection | `services/query_handler_service.py` |
| Wallet-creation flow | Guided multi-turn onboarding, typed `WalletFlowStep`(IntEnum)/`WalletFlowState` + `match` dispatch | `services/wallet_creation_flow_service.py` |
| LLM orchestration | Ollama completion, per-persona sampling, forced tool-calling | `llm_client.py`, `services/llm_completion_service.py`, `services/tool_calling_service.py` |
| Prompt construction | Lean exemplar-first / voice-last system prompt (XML-tagged bookend); `lru_cache`d | `prompt_builder.py`, `persona_memory.py` |
| Memory / RAG | Token-budget message selection, bge-m3 semantic search, summaries, fact extraction | `memory_manager.py`, `memory_rag.py`, `cv_summarizer.py`, `fact_extractor.py` |
| Lore | On-demand hybrid lore retrieval over the typed wiki; rank/affinity-gated capabilities | `lore_loader.py`, `lore_retrieval.py` |
| Persona-safe agentic middleware | Deterministic pre-execution gating: interceptor + injection guard + grammar-constrained arg extraction | `services/agentic_pipeline.py`, `tool_interceptor.py`, `injection_guard.py`, `argument_extractor.py` |
| Persistence | SQLite repositories — ALL extend `BaseRepository` via `db_adapter` (connection pooling, thread-safe) | `repositories/` |
| Configuration | Per-subsystem settings package (llm/search/memory/wallet/auth/routing/lore/agent) + `get_settings()` | `config/` |
| Composition root | Lifecycle + singleton wiring (hand-rolled DI hub — slated for FastAPI `Depends`) | `startup.py`, `server.py` |

## Data

| Source | Format | Writer | Readers |
|--------|--------|--------|---------|
| `chat_sessions`, `messages`, `conversation_summaries` | SQLite | session / message / summary repos | `chat_session_service`, `memory_manager` |
| `emotional_state` | SQLite | `emotional_state_repository` | `chat_session_service` (trust/rapport/mood) |
| `seeker_profiles`, `persona_affinity`, `resonance_log`, `unlocked_lore` | SQLite | `seeker_progression_repository` | `chat_session_service`, nephilim routes |
| `user_profiles` | SQLite | `user_profile_repository` | cross-session memory injection |
| wallet registry / summary / **flow** | SQLite | `wallet_registry` / `wallet_summary` / **`wallet_flow`** repos | `query_handler_service`, `wallet_creation_flow_service` |
| Session + lore vector indexes | FAISS | `memory_rag` | `chat_session_service` (semantic recall, on-demand lore) |

## Key invariants

- **nephilim is read-only** w.r.t. the trading MongoDB (`btc_data`) — it never writes trading data.
- **Wallet BIP39 mnemonic is NEVER persisted** — generated at the password step, displayed once, only wiped. `WalletFlowState` has no field for it and the `wallet_flow_state` table has no mnemonic column (structurally enforced).
- **Config import surface:** import `get_settings` / settings classes from `..config` (the package root), never the submodules — the `__init__` re-export + `src.coordinator.config.get_settings` patch-path is a contract.
- **All repositories extend `BaseRepository`** via `db_adapter` — never open a raw `sqlite3.connect()`.
- **Per-turn content must never enter the `lru_cache`d prompt builder** (`build_system_prompt`) — dynamic lore/memory is appended after the cached call.

## Cross-repo contracts

See ecosystem-level contracts (nephilim is read-only; these apply to CRA / btc_price_tracker):
- [../../docs/shared/indicator_api.md](../../docs/shared/indicator_api.md)
- [../../docs/shared/launchd_schedule.md](../../docs/shared/launchd_schedule.md)

The Telegram gateway (`services/telegram-gateway/`) couples to nephilim only through the localhost HTTP session API — never SQLite/FAISS directly.

## Decisions

Architectural decisions affecting this repo live in [decisions/](decisions/).
