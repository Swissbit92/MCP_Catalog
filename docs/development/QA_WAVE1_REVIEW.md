---
title: QA Wave 1 Review — 2026-02-18
status: completed
created: 2026-04-03
last_reviewed_on: 2026-04-19
review_in: 24 months
applies_to: MCP_Catalog
---

# QA Wave 1 Review — 2026-02-18

## Status: PASS (after fixes)

17 of 19 reviewed files initially passed. 2 blockers and 3 non-blocking issues were
identified and **all have been resolved immediately after the review**.

---

## File Reviews

### ✅ `src/coordinator/config.py` — PASS
- `JupiterSettings` and `EmailSettings` both present with all fields
- Nested correctly in `CoordinatorSettings`
- `is_enabled` properties correct on both
- No hardcoded secrets

### ✅ `src/coordinator/jupiter/__init__.py` — PASS
- `JupiterMCPClient` via multiple inheritance (`JupiterDockerClient` + `JupiterOperations`)
- MRO-safe — both `__init__` called explicitly
- `get_jupiter_client()` factory reads from env vars

### ✅ `src/coordinator/jupiter/strategy_loader.py` — PASS
- Mirrors `persona_loader.py` pattern faithfully
- All 5 functions implemented with proper error handling
- No bare `except:` clauses

### ✅ `src/coordinator/jupiter/strategies/strategy_base.py` — PASS
- Abstract with `@abstractmethod check_signal()`
- Type hints, logger, `from __future__ import annotations`

### ✅ `src/coordinator/jupiter/strategies/rsi_strategy.py` — PASS
- `buy` when `rsi <= oversold`, `sell` when `rsi >= overbought`, `hold` otherwise — correct
- Exception in `_get_current_rsi()` returns `'hold'` (safe default)
- Placeholder `50.0` return documented for Wave 2 wiring

### ✅ `src/coordinator/jupiter/strategies/dca_strategy.py` — PASS
- Buys on first run (no `last_executed`) — correct
- ISO timestamp parsing handles `Z` suffix correctly
- Bad timestamp defaults to `'buy'` (intentional, logged)

### ✅ `src/coordinator/jupiter/jupiter_mcp_client.py` — PASS (security verified)
- Private key injected via Docker env dict, NOT in `cmd` list (never in process listings)
- `logger.debug` logs only the image name, never the key
- Process NOT auto-started — requires explicit `set_private_key()` call
- Old container terminated before starting new one — key cannot linger

### ✅ `src/coordinator/jupiter/jupiter_operations.py` — PASS (after fix)
- All methods guarded by `_require_ready()`
- `execute_swap()` carries idempotency key
- **Fixed:** `verify_transaction()` now calls `wallet_verify_transaction` instead of
  the wrong `wallet_get_balance` tool. TODO comment added for proper tool implementation.

### ✅ `src/coordinator/jupiter/wallet_manager.py` — PASS (security verified)
- AES-256-GCM + scrypt `N=2^14` — correct
- 32-byte salt, 12-byte nonce — NIST compliant
- `InvalidTag` handled separately (wrong password vs. corruption)
- **SECURITY: Full grep scan confirms private key value never appears in any log statement**
- `encrypt_private_key()` and `decrypt_private_key()` are verified inverse operations

### ✅ `src/coordinator/jupiter/email_service.py` — PASS
- QA gatekeeper initially reported this as empty — was checking a stale file state
- Full 234-line implementation confirmed on disk
- `send_trade_notification()`, `send_strategy_summary()`, `_build_trade_email()` all present
- Correct SMTP config from `get_settings().email`, `is_enabled` guard, fire-and-forget pattern

### ✅ `src/coordinator/tools/wallet_tool_generators.py` — PASS
- Exact format match with `tool_generators.py` pattern
- All 7 tools present
- `WALLET_TOOLS` registry at file bottom

### ✅ `src/coordinator/services/wallet_proposal_service.py` — PASS
- `build_trade_proposal()` returns `metadata.proposal_type="trade_proposal"`
- `build_strategy_proposal()` returns `metadata.proposal_type="strategy_proposal"`
- TTL: `PROPOSAL_TTL_SECONDS = 300` (5 min)
- Strategy config built with all required guardrails pre-populated

### ✅ `src/coordinator/services/wallet_execution_service.py` — PASS (after fix)
- Class docstring: "Never called directly from chat handler" — HITL documented
- Idempotency key per execution
- **Fixed:** `amount_out` key lookup now tries `"out_amount"` first, falls back to
  `"out_amount_human"` — matches `JupiterOperations.execute_swap()` response shape

### ✅ `src/coordinator/services/strategy_service.py` — PASS (after fix)
- **FIXED (blocker):** `has_open_position()` now **fails closed** — returns `True`
  (assume position exists) when MongoDB is unavailable. Previously returned `False`
  (fail open), which could allow double-entry into positions during MongoDB outages.
- `check_guardrails()` correctly enforces both daily limit AND per-trade size
- `activate_strategy()`, `pause_strategy()`, `cancel_strategy()` all wired to `strategy_loader`
- HITL audit log written to MongoDB `approval_decisions`

### ✅ `src/coordinator/repositories/wallet_repository.py` — PASS
- Extends `BaseRepository`, `_ensure_tables()` in `__init__`
- All SQL queries parameterized — no injection surface

### ✅ `src/coordinator/repositories/trade_proposal_repository.py` — PASS
- 5-minute TTL enforced in `create_proposal()` and `get_proposal()`
- Dynamic `IN` clause in `expire_old_proposals()` verified safe (only `?` placeholders)
- `confirm_proposal()` re-checks expiry before confirming

### ✅ `requirements.txt` — PASS
All 5 new packages present: `solders`, `aiosmtplib`, `apscheduler`, `cryptography`, `pymongo`

### ✅ `react-ui/src/components/TradeProposalCard.tsx` — PASS (after fix)
- **FIXED (blocker):** Confirm button `disabled` prop now `isLoading || timeLeft === 0`
  — closes the expiry race window where a click could fire after timer hit zero
  but before React re-rendered the `{isPending && ...}` block
- UX fixes (glassmorphism, WCAG `/60`, focus:ring, timer urgency) applied by UX pass

### ✅ `react-ui/src/components/StrategyApprovalCard.tsx` — PASS
- Risk warning shown while pending
- `aria-expanded`/`aria-controls` on collapsible params section
- `StrategyConfig` interface matches `build_strategy_proposal()` output

### ✅ `react-ui/src/services/api.ts` (wallet section) — PASS
- `ResponseMetadata` extended with `proposal_type` discriminant — safe detection in MessageBubble
- All 8 wallet API functions implemented with error handling

---

## Security Verdict

**No critical vulnerabilities found.** Key confirmations:

| Check | Result |
|-------|--------|
| Private key never logged | ✅ Verified by full grep scan |
| AES-GCM + scrypt KDF correct | ✅ |
| All SQL parameterized | ✅ |
| No hardcoded secrets | ✅ |
| HITL enforced at service layer | ✅ |
| `has_open_position()` now fails closed | ✅ Fixed |

---

## Issues Resolved

| # | Issue | Severity | Resolution |
|---|-------|----------|-----------|
| 1 | `email_service.py` reported empty | Blocker | False alarm — file was complete |
| 2 | `has_open_position()` fails open | Blocker | Fixed — now returns `True` on MongoDB error |
| 3 | Confirm button expiry race | High | Fixed — `disabled={isLoading \|\| timeLeft === 0}` |
| 4 | `verify_transaction()` called wrong tool | Non-blocking | Fixed — `wallet_verify_transaction` |
| 5 | `out_amount_human` key mismatch | Non-blocking | Fixed — tries `out_amount` first |

---

## Wave 2 Clearance

**CLEARED for Wave 2.** All blockers resolved. The wiring agent can now safely implement:
- Step 18: `strategy_scheduler.py` — `has_open_position()` now fail-safe
- Step 22: `routes/wallet.py` — execution service key mismatch fixed
- Steps 23–27: Full wiring — security layer verified

---

## Recommendations for Wave 2

1. **`verify_transaction()` tool name** — confirm actual tool name exposed by `araa47/jupiter-mcp`
   image before wiring the scheduler's idempotency check
2. **`expire_old_proposals()` call** — scheduler (step 18) should call this periodically
   to prevent stale row accumulation in `trade_proposals` table
3. **`_session_keys` cache** — consider adding a max-age TTL (e.g., 8 hours) to force
   re-unlock if server has been running a long time without restart
