---
title: Remove MongoDB MCP from nephilim
status: Accepted
created: 2026-06-22
last_reviewed_on: 2026-06-22
review_in: 12 months
applies_to: nephilim
---

# ADR-002: Remove MongoDB MCP from nephilim

## Status

Accepted

## Context

nephilim previously integrated a MongoDB MCP layer (`src/coordinator/mongodb/`) to serve live crypto-price data (Bitcoin prices, RSI/MACD/Bollinger indicators, DCA stats) and bot state inside companion chat. The data came from the shared `btc_data` MongoDB instance populated by `btc_price_tracker`.

This integration became obsolete for two reasons:

1. **Data moved to local Docker**: The trading stack (`eeva-exec`, `Crypto_Research_Assistant`) moved to a local Docker MongoDB instance in early 2026; the Atlas URI that backed the MCP was no longer the source of truth.
2. **Dead-end routing**: "bitcoin price" and similar queries routed to `NEEDS_MONGODB` (a now-obsolete `QueryIntent` value), took ~39 s to execute, and frequently returned stale or empty results — a worse user experience than routing to Brave web search.

Additional bloat: `bot_state` capability (also MongoDB-backed) was never meaningfully used at runtime; a dormant `MONGODB_WRITE_URI` pymongo write-path existed in `JupiterSettings` but was never called; `cache.py` implemented a TTL cache solely for MongoDB responses.

The Atlas `Eeva_Admin` connection URI had previously been committed in a tracked `.env` file and pushed to GitHub — a credential exposure requiring rotation regardless of the removal decision. (The credential value is deliberately omitted here; it must be treated as compromised and rotated.)

## Decision

**Fully remove the MongoDB MCP integration from nephilim.** Scope:

- Delete `mongodb_mcp_client.py`, `src/coordinator/mongodb/` package, `cache.py`, `mongodb_handlers.py`, `token_registry.py`
- Remove `MongoDBSettings` from `config.py` and `pymongo` from `requirements.txt`
- Remove `NEEDS_MONGODB` and `NEEDS_BOTH` from `QueryIntent`; enum is now `NEEDS_WEB_SEARCH | NEEDS_NEITHER | NEEDS_WALLET`
- Remove all MongoDB keyword sets (`MONGODB_PRICE_KEYWORDS`, etc.) from `tools/keywords.py`
- Remove `mongodb` and `bot_state` from `mcp_access` in all persona JSONs (EEVA, Aurora, Cipher); Cipher becomes Brave-only
- Remove frontend MongoDB types (`mongodb_mcp`, `multi_mcp` from `source_type`, tool indicator, source badge, narrative)
- Delete MongoDB-specific test files; rewrite `tests/manual/test_bank_mcp.py` as Brave + Wallet-only (138 tests)
- Delete leaked credentials from `.env` (rotate externally)

**HERMES-Agents** (a planned skill framework for MCP routing, persona optimization, and image generation) is the intended successor for sophisticated routing decisions. It is parked as a major roadmap track for future development.

## Consequences

**Positive:**
- "Bitcoin price" queries now route to Brave (web search) — real-time web results instead of a stale DB dead-end
- ~39 s MongoDB dead-end eliminated; crypto-price queries now resolve in ~13 s (Brave search)
- Leaked Atlas credential surface eliminated from tracked files
- ~96 files simplified; `QueryIntent` enum is clean
- `pymongo` removed from the dependency tree

**Neutral / to watch:**
- Cipher (Sage) is now Brave-only; users expecting live indicator data from Cipher must use web search phrasing
- Aurora is now Brave-only (was `["brave_search", "mongodb"]`)
- The `bot_state` capability is gone; it was never meaningfully surfaced to users
- The dormant pymongo write-path (trade proposals → Atlas fallback) is gone; trade proposals are SQLite-only

**Future:**
- HERMES-Agents will provide a principled skill-routing framework once scoped; see `docs/ROADMAP.md`
- If live indicator data ever re-enters nephilim, it should arrive via a dedicated read-only REST endpoint or a new MCP, not the deleted MongoDB client
