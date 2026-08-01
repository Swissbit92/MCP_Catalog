---
title: Architecture
status: active
created: 2026-04-19
last_reviewed_on: 2026-07-17
review_in: 6 months
applies_to: nephilim
published_url: https://claude.ai/code/artifact/335a787e-3444-4eb1-8b1b-b217319da38f
---

# Architecture

Reference-style: tables and diagrams, not prose narratives. A local-first,
persona-driven chat platform — FastAPI backend + React 19 frontend + local Ollama,
SQLite for persistence, FAISS for semantic memory.

## System context

Verified against the call graph, not sketched from memory — every edge below is
an import or call that exists in `src/coordinator/`.

```archview
{
  "caption": "routes/chat.py is the orchestrator; the turn pipeline, the tool brain and the legacy wallet path are its three siblings.",
  "nodes": [
    {"id":"ui","label":"React UI","sub":"chat · personas · wallet","tech":"React 19 · TS","kind":"external"},
    {"id":"tg","label":"telegram-gateway","sub":"allowlisted single user","tech":"own venv · launchd","kind":"external"},
    {"id":"routes","label":"routes/chat.py","sub":"orchestrator — picks the path","tech":"FastAPI","kind":"service"},
    {"id":"chat","label":"handle_session_chat","sub":"per-turn phase pipeline","tech":"ChatDeps / ChatTurnState","kind":"module"},
    {"id":"brain","label":"tool_brain_service","sub":"web intents only, never wallet","tech":"Ollama native tool-calling","kind":"module"},
    {"id":"qh","label":"query_handler_service","sub":"legacy wallet + force-search","tech":"bge-m3 semantic router","kind":"module"},
    {"id":"persona","label":"persona_memory","sub":"-> prompt_builder, lean prompt","tech":"lru_cache","kind":"module"},
    {"id":"facts","label":"memory_fact_retrieval","sub":"through the M1 frame","tech":"bi-temporal store","kind":"module"},
    {"id":"llm","label":"llm_client","sub":"per-persona sampling","tech":"Ollama","kind":"module"},
    {"id":"repos","label":"repositories/","sub":"all extend BaseRepository","tech":"SQLite · pooled","kind":"module"},
    {"id":"guard","label":"tool_interceptor","sub":"validate() only — gates, never executes","tech":"deterministic middleware","kind":"secret"},
    {"id":"exec","label":"executor_bindings","sub":"runs the tool the guard permitted","tech":"registry-bound","kind":"module"},
    {"id":"relevance","label":"search_relevance_service","sub":"per-result cosine floor","tech":"reuses the RAG embedder","kind":"module"},
    {"id":"rag","label":"memory_rag","sub":"EpisodicMemoryRAG · startup singleton","tech":"bge-m3","kind":"module"},
    {"id":"sqlite","label":"SQLite","sub":"chats · progression · facts · wallets","tech":"local file","kind":"store"},
    {"id":"faiss","label":"FAISS","sub":"session + lore vectors","tech":"local index","kind":"store"},
    {"id":"ollama","label":"Ollama","sub":"LLM + bge-m3 embeddings","tech":"on-device, Metal GPU","kind":"external"},
    {"id":"web","label":"SearXNG / Brave","sub":"ephemeral Docker","tech":"MCP","kind":"external"},
    {"id":"jupiter","label":"Jupiter / Solana","sub":"long-running Docker","tech":"MCP","kind":"external"}
  ],
  "edges": [
    {"from":"ui","to":"routes","label":"session API"},
    {"from":"tg","to":"routes","label":"the SAME API"},
    {"from":"routes","to":"chat","label":"handle_session_chat"},
    {"from":"routes","to":"brain","label":"_try_tool_brain"},
    {"from":"routes","to":"qh","label":"legacy fallthrough"},
    {"from":"chat","to":"persona"},
    {"from":"chat","to":"facts"},
    {"from":"chat","to":"llm"},
    {"from":"chat","to":"repos"},
    {"from":"brain","to":"guard","label":"every tool call"},
    {"from":"guard","to":"exec","label":"only if permitted"},
    {"from":"exec","to":"relevance"},
    {"from":"relevance","to":"rag","label":"reuses the embedder"},
    {"from":"exec","to":"web"},
    {"from":"qh","to":"jupiter","label":"propose -> confirm -> execute"},
    {"from":"llm","to":"ollama"},
    {"from":"repos","to":"sqlite"},
    {"from":"facts","to":"sqlite"},
    {"from":"rag","to":"faiss"}
  ]
}
```

**Wallet is never model-decided.** `_try_tool_brain` returns `None` on
`NEEDS_WALLET` unconditionally, so the wallet path stays on the deterministic
propose→confirm→execute flow. The tool brain is offered **web tools only** — a
live test showed the full 14-tool surface caused wallet fixation and
fabrication.

**The guard gates; it does not execute.** `ToolCallInterceptor` exposes
`validate()` and nothing else. Execution happens in `executor_bindings` *after*
the check passes, which is why the two are separate nodes above rather than one.

**Local-first is a constraint, not a preference.** Inference runs on-device
because the alternative leaks financial context to a third party. The two Docker
MCP servers are the only paths off the machine.

The Telegram gateway consumes the **same** session API as the React UI
([ADR-011](decisions/011-conversation-control-commands-as-shared-session-api-endpoints.md)),
which is why regenerate/continue/undo exist once rather than twice.

## The turn pipeline

The diagram above shows which modules exist. It does not show what happens when
someone actually sends a message, which is the thing most questions are really
about.

```archview
{
  "id": "turn",
  "caption": "One chat turn, from message to persisted reply.",
  "nodes": [
    {"id": "arrive", "label": "Message arrives", "sub": "React UI or Telegram", "kind": "external"},
    {"id": "identity", "label": "Load identity", "sub": "persona + cached CV", "kind": "module"},
    {"id": "route", "label": "Route the intent", "sub": "semantic, bge-m3", "kind": "module"},
    {"id": "prompt", "label": "Build the prompt", "sub": "lean, exemplar-first", "kind": "module"},
    {"id": "history", "label": "Select history", "sub": "token budget + RAG", "kind": "module"},
    {"id": "generate", "label": "Generate", "sub": "per-persona sampling", "kind": "external"},
    {"id": "guard", "label": "Post-process", "sub": "strip tool leaks, first person", "kind": "secret"},
    {"id": "persist", "label": "Persist", "sub": "SQLite", "kind": "store"},
    {"id": "after", "label": "Post-turn updates", "sub": "progression, facts, summaries", "kind": "module"}
  ],
  "edges": [
    {"from": "arrive", "to": "identity"},
    {"from": "identity", "to": "route"},
    {"from": "route", "to": "prompt"},
    {"from": "prompt", "to": "history"},
    {"from": "history", "to": "generate"},
    {"from": "generate", "to": "guard"},
    {"from": "guard", "to": "persist"},
    {"from": "persist", "to": "after"}
  ]
}
```

```archflow
{
  "view": "turn",
  "flows": [
    {
      "id": "chat-turn",
      "label": "A single chat turn",
      "steps": [
        {"node": "arrive", "note": "Both clients hit the same session API. That is the whole point of ADR-011 — regenerate, continue and undo exist once, not twice."},
        {"node": "identity", "note": "The persona JSON and its cached CV summary are loaded. The cache is why the voice signature must stay OUT of the fingerprint, or edits would not take."},
        {"node": "route", "note": "Intent routing is semantic-primary: follow-up detection, then a narrow keyword fast-path, then the bge-m3 router. Wallet is never model-decided."},
        {"node": "prompt", "note": "The lean prompt is built exemplar-first and voice-last. It is lru_cached, so anything per-turn (lore, author's note) must be appended AFTER it rather than baked in."},
        {"node": "history", "note": "Messages are selected against a token budget, with semantic recall over past sessions."},
        {"node": "generate", "note": "Ollama generates on-device with per-persona sampling overrides. Local-first is a constraint, not a preference — the alternative leaks financial context to a third party."},
        {"node": "guard", "note": "Leaked tool names are stripped, first person is enforced, and any tool call that ran had to pass the interceptor before execution."},
        {"node": "persist", "note": "The exchange is written to SQLite through the pooled BaseRepository — never a raw connection."},
        {"node": "after", "note": "Progression, resonance, fact extraction and summarisation run after the reply is already out, so none of them can slow the response."}
      ]
    }
  ]
}
```

## Components

Layered: **routes → services → repositories → models**, mirrored on the frontend.

| Component | Responsibility | Module |
|-----------|----------------|--------|
| API routes | HTTP endpoints: chat, sessions, personas, nephilim, auth, wallet | `src/coordinator/routes/` |
| Chat-turn orchestration | Per-turn phase pipeline (load identity → build prompt → select history → generate → persist → post-updates), typed `ChatDeps`/`ChatTurnState`; `persist_user`/`run_post_turn_updates` flags let regenerate/continue reuse it | `services/chat_session_service.py` |
| Conversation-control (ADR-011) | Shared session-API verbs consumed by BOTH the React UI and Telegram gateway: regenerate/continue/undo/narrate(`/sys`)/impersonate + session metadata + author's note. Reuses the standard finalize path (no parallel LLM plumbing) | `services/conversation_control_service.py` (routes in `routes/chat.py` + `routes/sessions.py`) |
| Query routing | Intent → wallet / brave / agentic / pure-LLM; wallet ground-truth injection | `services/query_handler_service.py` |
| Wallet-creation flow | Guided multi-turn onboarding, typed `WalletFlowStep`(IntEnum)/`WalletFlowState` + `match` dispatch | `services/wallet_creation_flow_service.py` |
| LLM orchestration | Ollama completion, per-persona sampling, forced tool-calling | `llm_client.py`, `services/llm_completion_service.py`, `services/tool_calling_service.py` |
| Prompt construction | Lean exemplar-first / voice-last system prompt (XML-tagged bookend); `lru_cache`d | `prompt_builder.py`, `persona_memory.py` |
| Memory / RAG | Token-budget message selection, bge-m3 semantic search, summaries, fact extraction | `memory_manager.py`, `memory_rag.py`, `cv_summarizer.py`, `fact_extractor.py` |
| Companion memory — framing (ADR-006 M1) | Wrap injected memory in a per-persona non-echoable `<remembered>` frame over prose narratives (anti-homogenization, the Gate-0/0.1 fix) | `context_framing.py` |
| Companion memory — fact store (ADR-006 M2–M4) | Two-table temporal ontology-lite store + async triplet extraction (abstention + quote-span guard, off the interactive path) + recency-wins write + inject-all/top-k retrieval through the M1 frame | `repositories/memory_fact_repository.py`, `triplet_extractor.py`, `fact_write_policy.py`, `fact_extraction_worker.py`, `memory_fact_retrieval.py` |
| Lore | On-demand hybrid lore retrieval over the typed wiki; rank/affinity-gated capabilities | `lore_loader.py`, `lore_retrieval.py` |
| Tool-call safety middleware | Deterministic pre-execution gating on every tool-brain call: `mcp_access` + argument allowlist + HITL; plus RAG memory-write sanitization | `services/tool_interceptor.py`, `services/injection_guard.py` |
| Persistence | SQLite repositories — ALL extend `BaseRepository` via `db_adapter` (connection pooling, thread-safe) | `repositories/` |
| Configuration | Per-subsystem settings package (llm/search/memory/wallet/auth/routing/lore/agent) + `get_settings()` | `config/` |
| Composition root | `startup.py` = init sequencer (builds singletons, publishes an `AppState` snapshot on `app.state.container`); `dependencies.py` = FastAPI `Depends` providers (`require_*`→503-on-uninit, `optional_*`→None) resolving `startup.get_X()` at call time | `app_state.py`, `dependencies.py`, `startup.py`, `server.py` |

## Data

| Source | Format | Writer | Readers |
|--------|--------|--------|---------|
| `chat_sessions`, `messages`, `conversation_summaries` | SQLite (`messages.role` ∈ user/assistant/**narrator**, ADR-011) | session / message / summary repos | `chat_session_service`, `memory_manager` |
| `session_notes` (ADR-011) | SQLite one-row-per-session author's note (FK-cascade to `chat_sessions`); alembic `5session_notes` + `_ensure_table` dual-cover | `session_note_repository` | `chat_session_service._append_author_note` (injected every turn via `extra_system_context`) |
| `emotional_state` | SQLite | `emotional_state_repository` | `chat_session_service` (trust/rapport/mood) |
| `seeker_profiles`, `persona_affinity`, `resonance_log`, `unlocked_lore` | SQLite | `seeker_progression_repository` | `chat_session_service`, nephilim routes |
| `user_profiles` | SQLite | `user_profile_repository` | cross-session memory injection |
| `memory_entities`, `memory_facts` (ADR-006) | SQLite S-P-O triples, bi-temporal `valid_from`/`valid_to`, confidence, provenance | fact worker (M3) | fact retrieval (M4) |
| wallet registry / summary / **flow** | SQLite | `wallet_registry` / `wallet_summary` / **`wallet_flow`** repos | `query_handler_service`, `wallet_creation_flow_service` |
| Session + lore vector indexes | FAISS | `memory_rag` | `chat_session_service` (semantic recall, on-demand lore) |

## Key invariants

- **nephilim is read-only** w.r.t. the trading MongoDB (`btc_data`) — it never writes trading data.
- **Wallet BIP39 mnemonic is NEVER persisted** — generated at the password step, displayed once, only wiped. `WalletFlowState` has no field for it and the `wallet_flow_state` table has no mnemonic column (structurally enforced).
- **Config import surface:** import `get_settings` / settings classes from `..config` (the package root), never the submodules — the `__init__` re-export + `src.coordinator.config.get_settings` patch-path is a contract.
- **All repositories extend `BaseRepository`** via `db_adapter` — never open a raw `sqlite3.connect()`.
- **Per-turn content must never enter the `lru_cache`d prompt builder** (`build_system_prompt`) — dynamic lore/memory is appended after the cached call.
- **Companion memory (ADR-006) is default OFF** (`MEMORY_CONTEXT_INJECT`, `MEMORY_FACTS_ENABLED`) — M5 gate passed 2026-07-05; kept OFF for a live soak + instant revert. Injected memory always goes through the per-persona `<remembered>` frame as prose (never an identical skeleton — Gate 0/0.1); facts are invalidated not deleted (`valid_to`); extraction runs off the interactive path (enqueue-and-return, a failing job never breaks a turn).
- **Image-search result quality (ADR-010)** is enforced in the bound search executor (`tools/executor_bindings.py`), the one choke point feeding both synthesis and citations: a deterministic junk denylist (`tools/result_filters.py`, always-on, images-only, never-empty fallback) plus a per-result bge-m3 relevance floor (`SEARCH_RELEVANCE_GATE_ENABLED`, code default OFF but enabled in the prod `.env`, so live on images at `min_cosine=0.36` — measured safe: 0% false-abstention across 39 post-denylist results, since the denylist strips junk before the floor runs). A spurious synthesis refusal (abliterated residual) triggers one prefill-steered retry and sets `ToolBrainResult.refused`; the route then never staples citations onto a refusal. The search `query` is length/control-char validated for all live tool names (`_SEARCH_QUERY_TOOLS`).
- **`PERSONA_TOOL_INTENT_IN_PROMPT` is default OFF** — the dead `escalation_policy.tool_intent` field can be injected as a `<tools>` block, but the full-7 eval showed it voice-neutral (0.786 = 0.786), so it stays off (no-regression ≠ improvement). `PersonaCard.emoji` `max_length` is 8 (code points, not emoji — accommodates variation selectors).

## Cross-repo contracts

See ecosystem-level contracts (nephilim is read-only; these apply to CRA / btc_price_tracker):
- [../../docs/shared/indicator_api.md](../../docs/shared/indicator_api.md)
- [../../docs/shared/launchd_schedule.md](../../docs/shared/launchd_schedule.md)

The Telegram gateway (`services/telegram-gateway/`) couples to nephilim only through the localhost HTTP session API — never SQLite/FAISS directly.

## Decisions

A pointer to a directory is not an index — it makes the reader open twelve files
to find out which one governs the thing they are looking at. ADR-008 in
particular decides the branch at the centre of the System context diagram above,
and this page previously never named it.

| ADR | Decides | Status |
|---|---|---|
| [001](decisions/001-lore-as-typed-markdown-wiki-not-a-graph-db.md) | Lore is a typed markdown wiki, not a graph DB | Accepted |
| [002](decisions/002-remove-mongodb-mcp.md) | MongoDB MCP removed from the persona path | Accepted |
| [003](decisions/003-on-demand-hybrid-lore-retrieval.md) | Lore is retrieved on demand, hybrid dense + lexical | Accepted |
| [004](decisions/004-persona-safe-agentic-tool-calls.md) | Persona-safe agentic tool calls | **Superseded** — by 008/009 |
| [005](decisions/005-persona-architecture-simplification-eval-first.md) | Persona simplification, gated eval-first | Accepted |
| [006](decisions/006-companion-memory-and-continuity-eval-first.md) | Companion memory and continuity | Accepted |
| [007](decisions/007-generation-time-groundedness-gate.md) | Groundedness gate at generation time | Proposed |
| [008](decisions/008-two-brain-split-tool-brain-voice-brain.md) | **Two-brain split: tool brain vs voice brain** — the branch the diagram above turns on | Proposed |
| [009](decisions/009-layered-toolkit-registry-generic-web-toolset-inner-wisdom-skills.md) | Layered toolkit registry | Accepted |
| [010](decisions/010-image-search-result-quality-and-spurious-refusal-handling.md) | Image-search quality and spurious refusals | Accepted |
| [011](decisions/011-conversation-control-commands-as-shared-session-api-endpoints.md) | Conversation control as shared session API — consumed by both the React UI and the Telegram gateway | Proposed |
| [012](decisions/012-persona-configurable-deterministic-word-substitutions.md) | Persona-configurable deterministic word substitutions | Accepted |

"Proposed" here does not mean unbuilt. Several of these are implemented behind
flags that are off, or on in production while the ADR is still open — the ADR
status tracks the *decision*, not the deployment. Which flags are actually live
is recorded in `CLAUDE.md`, deliberately not here: this page describes structure,
and runtime state on a structural page is the thing that goes stale first.
