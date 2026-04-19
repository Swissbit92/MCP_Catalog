---
title: Multi-Asset MongoDB + Bot State Integration
status: completed
created: 2026-04-04
last_reviewed_on: 2026-04-19
review_in: 24 months
applies_to: MCP_Catalog
---

# Multi-Asset MongoDB + Bot State Integration

**Status:** Phases 1-6 Complete, Phase 7 (Integration Verification) Pending Live Backend
**Started:** 2026-03-03
**Branch:** dev

## Overview

Upgrade the backend from querying 3 of 43 MongoDB collections and 1 of 14 tokens to full cluster coverage: 13 tokens × 3 timeframes + bot state database.

## Phase Checklist

### Phase 1: Token Registry & Indicator Catalog
- [x] Create `src/coordinator/tools/token_registry.py`
- [x] 13-token registry with aliases
- [x] `resolve_token()` — extract ticker from natural language
- [x] `get_collection()` — build collection name from token + timeframe
- [x] Indicator catalog (80 indicators, 10 categories)
- [x] Indicator interpretation helpers (thresholds/signals)
- **Gate test:** `from src.coordinator.tools.token_registry import resolve_token; assert resolve_token("what's the ethereum price") == "eth"`

### Phase 2: Intent Classifier Generalization
- [x] Add `BOT_STATE_KEYWORDS` to `keywords.py`
- [x] Import and use `resolve_token()` in `intent_classifier.py`
- [x] Replace hardcoded `"bitcoin"/"btc"` check with multi-token detection
- [x] Add `NEEDS_BOT_STATE` intent (or fold into NEEDS_MONGODB sub-type)
- [x] Pass resolved token as metadata through classification
- **Gate test:** `classify_query_intent("ETH RSI", "legendary", mcp_access=["mongodb"]) == NEEDS_MONGODB`

### Phase 3: Generalize MongoDB Handlers
- [x] Generalize `handle_bitcoin_current_price` → `handle_crypto_current_price(token, ...)`
- [x] Generalize `handle_bitcoin_historical_prices` → `handle_crypto_historical_prices(token, ...)`
- [x] Generalize `handle_bitcoin_trading_summary` → `handle_crypto_trading_summary(token, ...)`
- [x] Generalize `handle_bitcoin_technical_analysis` → `handle_crypto_technical_analysis(token, ...)`
- [x] Add backward-compat wrappers for old function names
- [x] Add 3 bot state handlers (`handle_bot_status`, `handle_bot_positions`, `handle_bot_trades`)
- [x] Add new indicator interpretation (ADX, Supertrend, Squeeze, HDPR, FnG, VWAP, Fibonacci, CCI, Williams_R, MFI, CHOP)
- [x] Update cache keys to include token
- **Gate test:** Handler accepts `token="eth"` and queries `eth_1h_price_data`; BTC backward compat wrapper still works

### Phase 4: Update Tool Definitions
- [x] Replace `bitcoin_current_price` → `crypto_current_price` (with token enum)
- [x] Replace `bitcoin_historical_prices` → `crypto_historical_prices`
- [x] Replace `bitcoin_trading_summary` → `crypto_trading_summary`
- [x] Replace `bitcoin_technical_analysis` → `crypto_technical_analysis`
- [x] Add `bot_status`, `bot_positions`, `bot_trade_history` tools
- [x] Update `get_mongodb_tools()` to return generalized tools
- [x] Add `get_bot_state_tools()` function
- [x] Update `AVAILABLE_TOOLS` registry
- **Gate test:** `get_mongodb_tools()` returns tools with `crypto_*` names; token enum has 13 values

### Phase 5: Query Handler Routing
- [x] Use `resolve_token(message)` in `handle_mongodb_query()` to extract token
- [x] Pass token to generalized handlers (default "btc" if unresolved)
- [x] Add bot state query routing
- [x] Update `_TOOL_NAME_PATTERN` regex to include new tool names
- [x] Parameterize synthesis prompt with token display name
- **Gate test:** "ETH price" routes to `handle_crypto_current_price("eth", ...)` not `handle_bitcoin_current_price`

### Phase 6: Prompt Builder & Persona Updates
- [x] Update prompt_builder.py — add MongoDB capability description in identity block
- [x] Parameterize `build_mongodb_synthesis_prompt()` with token name
- [x] Add `"bot_state"` to eeva's `mcp_access` in persona JSON
- [x] Add `"bot_state"` to aurora's `mcp_access` in persona JSON
- **Gate test:** eeva persona JSON has `"bot_state"` in `mcp_access`; synthesis prompt mentions token name

### Phase 7: Integration Verification (Completed 2026-03-03)
- [x] "ETH price" → ✅ Returns real ETH data ($1980.80) from `eth_1h_price_data` via `crypto_current_price`
- [x] "BTC price" → ✅ Backward compat, returns BTC data ($68,307.70) via `crypto_current_price`
- [x] "SOL technical analysis" → ✅ Full TA with ADX, Supertrend from `sol_1h_price_data`
- [x] "What's the Fear & Greed index?" → ✅ Returns FnG=14 "Extreme Fear" via `crypto_technical_analysis`
- [x] "What's my bot doing?" → ✅ Returns RsiMomentumStrategy + BollingerStrategy from `btc_bot_state.bot_state`
- [x] "LINK 4h analysis" (Aurora) → ✅ Returns Chainlink data ($8.8058) from `link_4h_price_data`
- [x] "ADA purchase history" → ✅ Graceful "No DCA data" response (routes to MongoDB, no crash)
- [ ] Run: `python tests/manual/comprehensive_persona_test.py --persona nephilim_eeva --quick`

**Note:** MongoDB STDIO Docker container has a pre-existing lifecycle issue — times out after ~3-5 sequential queries. All 7 verification queries pass individually on fresh container. This is an infrastructure issue, not a code bug.

## Files Modified

| File | Status | Phase |
|------|--------|-------|
| `src/coordinator/tools/token_registry.py` | Created | 1 |
| `src/coordinator/tools/keywords.py` | Modified | 2 |
| `src/coordinator/tools/intent_classifier.py` | Modified | 2 |
| `src/coordinator/services/mongodb_handlers.py` | Modified | 3 |
| `src/coordinator/tools/tool_generators.py` | Modified | 4 |
| `src/coordinator/tools/tool_utils.py` | Modified | 4, 5 |
| `src/coordinator/services/query_handler_service.py` | Modified | 5 |
| `src/coordinator/tools/synthesis_prompts.py` | Modified | 6 |
| `src/coordinator/prompt_builder.py` | Modified | 6 |
| `src/coordinator/routes/chat.py` | Modified | 5 |
| `personas/nephilim_eeva.json` | Modified | 6 |
| `personas/nephilim_aurora.json` | Modified | 6 |

## Architecture Notes

- **Token resolution** is centralized in `token_registry.py` — single source of truth
- **Collection naming convention**: `{token}_{timeframe}_price_data` (e.g., `sol_4h_price_data`)
- **Bot state** lives in separate database `btc_bot_state` (not `btc_data`)
- **DCA data** only exists for BTC (`BTC dayli buying` collection) — other tokens return graceful "no data"
- **Indicator coverage varies** by collection — handlers use `.get()` and only include available indicators
- **Cache keys** now include token: `{token}_current_price_{timeframe}` instead of `bitcoin_current_price`
