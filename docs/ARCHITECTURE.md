---
title: Architecture
status: active
created: 2026-04-19
last_reviewed_on: 2026-07-04
review_in: 6 months
applies_to: nephilim
---

# Architecture

Reference-style: tables and diagrams, not prose narratives.

## System context

```
[External input] → nephilim → [Output / downstream consumer]
```

## Components

(Companion-memory subsystem — ADR-006 Phase 1. Other subsystems TBD.)

| Component | Responsibility | Module |
|-----------|----------------|--------|
| Context framing | Wrap injected memory in a per-persona non-echoable `<remembered>` frame (anti-homogenization, the Gate-0/0.1 fix) | `src/coordinator/context_framing.py` |
| Fact store | Two-table temporal ontology-lite store (entities + bi-temporal facts) | `src/coordinator/repositories/memory_fact_repository.py` |
| Fact extraction | Async triplet extraction off the interactive path (abstention few-shot + quote-span guard + recency-wins write) | `triplet_extractor.py`, `fact_write_policy.py`, `fact_extraction_worker.py` |
| Fact retrieval | Inject-all (<threshold) / cosine top-k, rendered to prose through the frame | `src/coordinator/memory_fact_retrieval.py` |
| Injection assembly | Combine profile+emotional (M1) + fact store (M4) into one framed block, token-capped | `services/chat_session_service.py` |

## Data

| Source | Format | Writer | Readers |
|--------|--------|--------|---------|
| `memory_entities` | SQLite (user + mentioned people/things) | fact worker (M3) | fact retrieval (M4) |
| `memory_facts` | SQLite S-P-O triples, bi-temporal `valid_from`/`valid_to`, confidence, provenance | fact worker (M3) | fact retrieval (M4) |
| FAISS session index | in-memory vectors (bge-m3) | RAG update | semantic recall |

## Key invariants

- **Companion memory is default OFF.** `MEMORY_CONTEXT_INJECT` and `MEMORY_FACTS_ENABLED` stay OFF until the ADR-006 Phase 1 (M5) eval gate passes (full 7-persona attribution match-or-beat).
- **Injected memory must never homogenize voice.** All injected memory goes through the per-persona `<remembered>` frame as prose — never an identical `**Header**\n- field: value` skeleton across personas (Gate 0/0.1).
- **Facts are invalidated, not deleted** — supersede via `valid_to` + `superseded_by`; retrieval filters `valid_to IS NULL`.
- **Extraction is off the interactive path** — enqueue-and-return; a failing extraction job never blocks or breaks a chat turn.

## Cross-repo contracts

See ecosystem-level contracts (nephilim is read-only; these apply to CRA / btc_price_tracker):
- [../../docs/shared/indicator_api.md](../../docs/shared/indicator_api.md)
- [../../docs/shared/launchd_schedule.md](../../docs/shared/launchd_schedule.md)

## Decisions

Architectural decisions affecting this repo live in [decisions/](decisions/).
