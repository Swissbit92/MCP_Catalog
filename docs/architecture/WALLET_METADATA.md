# Wallet Metadata & AI Context Layer

Architecture reference for the multi-wallet metadata system that gives AI companions reliable, deterministic awareness of wallet state, trading activity, and hard-enforced guardrails.

---

## Why This Exists

The AI companion manages Solana/Jupiter wallets for users — creating, funding, trading, and deleting. Before this layer, the AI had significant blind spots:

- Could not see how many wallets a user had (binary "has wallet?" check only)
- Did not know if a wallet was locked or unlocked
- Lost context across sessions (wallet state recomputed per-message)
- Could not enforce wallet count limits (no multi-wallet support)
- Never showed the user their recovery phrase
- Trade history was lost when MongoDB was unavailable

The Wallet Metadata Layer solves all of these by extending the existing SQLite + BaseRepository pattern with three new tables, an enriched prompt injection, and a 4-step wallet creation ceremony.

---

## What the Companion Can See

Every message, the companion receives a ground-truth context block injected into the system prompt. This is what it looks like:

```
## SEEKER WALLET STATE (GROUND TRUTH — use ONLY these values)
- Active wallets: 2 of 3 slots used
- Wallet 1: "Trading Wallet" (7xKQ...4nPm) — UNLOCKED, 2.3400 SOL, checked 2026-02-21T12:05:00Z
- Wallet 2: "Savings" (9bRw...7mKp) — LOCKED, unknown, checked never
- Available slots: 1 remaining
- Trading activity: 12 trades, $847.50 total volume
- Last trade: Buy SOL/USDC (2026-02-21T10:15:00Z)

RULES:
- The Seeker can create 1 more wallet(s) (max 3).
- For CURRENT balances, ALWAYS call wallet_get_balances. Above values are cached.
- If a wallet shows LOCKED, tell the Seeker to unlock it before trading.
- Never invent wallet addresses, names, balances, or trade history.
```

### Full Data Point Reference

#### Wallet Inventory & Limits

| Data Point | Source Table | Injected into Prompt? |
|---|---|---|
| Active wallet count | `wallet_registry` | Yes — "2 of 3 slots used" |
| Available slot count | `wallet_registry` | Yes — "1 remaining" |
| Slot number per wallet (1, 2, or 3) | `wallet_registry` | Yes — ordering |
| Wallet name | `wallet_registry` | Yes |
| Public address (full + shortened) | `wallet_registry` | Yes |
| Wallet status (active / deleted / creating) | `wallet_registry` | Yes (active only) |
| Creation timestamp | `wallet_registry` | No (available via repo query) |
| Deletion timestamp (soft-delete) | `wallet_registry` | No (available via repo query) |
| Full wallet history (including deleted) | `wallet_registry` | No (available via repo query) |

#### Wallet Session State

| Data Point | Source | Injected into Prompt? |
|---|---|---|
| Lock/unlock state (per session) | `_session_keys` cache + `wallet_balance_cache.is_unlocked` | Yes — "UNLOCKED" / "LOCKED" |
| All wallets reset to LOCKED on restart | `wallet_balance_cache` (reset in `startup.py`) | Implicit |

#### Cached Balances (Per-Wallet)

| Data Point | Source Table | Injected into Prompt? |
|---|---|---|
| SOL balance (cached) | `wallet_balance_cache` | Yes |
| Token count | `wallet_balance_cache` | No (available via repo query) |
| Last balance check timestamp | `wallet_balance_cache` | Yes — "checked {timestamp}" |

#### Live Data (On-Demand Tool Calls — unchanged)

| Data Point | Source | Method |
|---|---|---|
| Real-time SOL + token balances | Jupiter MCP | `wallet_get_balances` tool call |
| Swap quote (price, impact, fees) | Jupiter MCP | `wallet_get_quote` tool call |
| RSI signal for a token | Jupiter MCP | `wallet_check_rsi` tool call |

#### Trading Activity Summary (Cross-Session)

| Data Point | Source Table | Injected into Prompt? |
|---|---|---|
| Total trades (lifetime) | `wallet_activity_summary` | Yes |
| Total USDC volume traded | `wallet_activity_summary` | Yes |
| Last trade pair (e.g. SOL/USDC) | `wallet_activity_summary` | Yes |
| Last trade action (buy/sell) | `wallet_activity_summary` | Yes |
| Last trade timestamp | `wallet_activity_summary` | Yes |
| Active strategy count | `wallet_activity_summary` | No (available via repo query) |
| Total wallets ever created | `wallet_activity_summary` | No (available via repo query) |

#### Trade History (Per-Trade Detail)

| Data Point | Source Table | Injected into Prompt? |
|---|---|---|
| Transaction signature | `wallet_trades_local` | No (available via repo query) |
| Trading pair | `wallet_trades_local` | No |
| Action (buy/sell) | `wallet_trades_local` | No |
| Amount in (+ token symbol) | `wallet_trades_local` | No |
| Amount out (+ token symbol) | `wallet_trades_local` | No |
| Slippage (bps) | `wallet_trades_local` | No |
| Execution mode (ad-hoc vs strategy) | `wallet_trades_local` | No |
| Strategy ID (if strategy-driven) | `wallet_trades_local` | No |
| Which wallet was used | `wallet_trades_local` | No |
| Timestamp | `wallet_trades_local` | No |

> **Note:** Trade history details are not injected into every prompt (too verbose). The summary (count + volume + last trade) is injected. Full history is available via the `solana_trade_history` tool call or direct repo query.

#### Secret Key Ceremony (One-Time)

| Data Point | Source | Persisted? |
|---|---|---|
| 12-word BIP39 recovery phrase | Generated in memory | Shown ONCE in chat (step 3), permanently wiped after confirmation (step 4) |
| User confirmation of saving | Flow state machine | Tracked in `_wallet_flows` dict, cleared after step 4 |

---

## Hard Guardrails (Backend-Enforced)

These constraints are enforced in Python code, not by LLM prompting. Even if the LLM hallucinates, the backend rejects the operation.

| Guardrail | Where Enforced | Behavior |
|---|---|---|
| Max 3 active wallets per user | `WalletRegistryRepository.can_create_wallet()` | Returns `(False, count, 0)` → creation rejected |
| Wallet count check on every creation path | `query_handler_service.py` (both keyword + LLM tool-call paths) | Pre-flight check before entering flow |
| Mnemonic shown exactly once | `_handle_wallet_creation_step()` step 3→4 transition | Mnemonic zeroed with `\x00` then deleted from `_wallet_flows` |
| Mnemonic never persisted to disk | Flow state only (in-memory dict) | Not in SQLite, not in chat messages content |
| Password minimum 8 characters | `_handle_wallet_creation_step()` step 2 | Rejects with user-friendly message |
| Deleted wallets don't count toward limit | `wallet_registry WHERE status = 'active'` | Only active rows counted |

---

## SQLite Tables

### `wallet_registry`

Per-user wallet registry tracking ALL wallets (active + deleted) with slot management.

```sql
CREATE TABLE IF NOT EXISTS wallet_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    wallet_id TEXT NOT NULL UNIQUE,          -- UUID, stable identifier
    wallet_name TEXT NOT NULL DEFAULT 'My Wallet',
    public_address TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',   -- 'active', 'deleted', 'creating'
    slot_number INTEGER NOT NULL,            -- 1, 2, or 3
    created_at TEXT NOT NULL,
    deleted_at TEXT,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_registry_user ON wallet_registry(user_id);
CREATE INDEX IF NOT EXISTS idx_registry_status ON wallet_registry(user_id, status);
```

### `wallet_activity_summary`

Pre-computed per-user activity summary, updated on every trade.

```sql
CREATE TABLE IF NOT EXISTS wallet_activity_summary (
    user_id TEXT PRIMARY KEY,
    active_wallet_count INTEGER DEFAULT 0,
    total_wallets_ever INTEGER DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    total_volume_usdc REAL DEFAULT 0.0,
    last_trade_timestamp TEXT,
    last_trade_pair TEXT,
    last_trade_action TEXT,
    active_strategies INTEGER DEFAULT 0,
    updated_at TEXT NOT NULL
);
```

### `wallet_balance_cache`

Per-wallet cached balance, updated on every `wallet_get_balances` call.

```sql
CREATE TABLE IF NOT EXISTS wallet_balance_cache (
    wallet_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    sol_balance REAL,
    token_count INTEGER DEFAULT 0,
    is_unlocked INTEGER DEFAULT 0,
    last_checked TEXT,
    FOREIGN KEY(wallet_id) REFERENCES wallet_registry(wallet_id)
);
```

### `wallet_trades_local`

Local SQLite trade history — dual-write fallback so records are never lost when MongoDB is unavailable.

```sql
CREATE TABLE IF NOT EXISTS wallet_trades_local (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    wallet_id TEXT NOT NULL,
    tx_signature TEXT,
    pair TEXT NOT NULL,
    action TEXT NOT NULL,
    amount_in REAL NOT NULL,
    amount_in_token TEXT NOT NULL,
    amount_out REAL,
    amount_out_token TEXT NOT NULL,
    slippage_bps INTEGER,
    execution_mode TEXT,
    strategy_id TEXT,
    timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trades_user ON wallet_trades_local(user_id);
CREATE INDEX IF NOT EXISTS idx_trades_wallet ON wallet_trades_local(wallet_id);
```

---

## Wallet Creation Flow (4-Step Ceremony)

```
User: "Create a wallet"
  │
  ├─ Pre-flight: wallet_registry.can_create_wallet(user_id)
  │   └─ If count >= 3 → REJECT ("You've reached the max of 3 wallets")
  │
  ▼
Step 1: "What would you like to name your wallet?" (slot N of 3)
  │ User: "My Trading Wallet"
  ▼
Step 2: "Choose a strong password (min 8 chars)"
  │ User: "mypassword123"
  │   ├─ generate_mnemonic() → 12-word BIP39 phrase
  │   ├─ generate_keypair_from_mnemonic(phrase) → {public_address, private_key_b58}
  │   ├─ encrypt_private_key(key, password) → AES-256-GCM ciphertext
  │   ├─ wallet_repo.create_wallet(...) → user_wallets row
  │   ├─ wallet_registry.register_wallet(...) → wallet_registry row
  │   ├─ wallet_summary.upsert_summary(...) → activity summary update
  │   └─ cache_session_key(user_id, key) → wallet unlocked
  ▼
Step 3: "Your recovery phrase is ready" (shown ONCE)
  │   ┌─────────────────────────────────┐
  │   │ abandon ability able about ...  │  ← 12-word mnemonic in code block
  │   └─────────────────────────────────┘
  │   metadata: { ephemeral: true, secret_displayed: true }
  │ User: "I saved it" / "confirm"
  ▼
Step 4: Mnemonic zeroed (\x00) and deleted from _wallet_flows
  │ "Wallet Created! Recovery phrase permanently deleted."
  └─ DONE
```

**BIP39 derivation path:** `m/44'/501'/0'/0'` (Solana standard, matches Phantom/Solflare).

---

## Dual-Write Trade Pattern

```
Trade Executed (WalletExecutionService.execute_swap)
  │
  ├─ _persist_trade(trade_doc)          → MongoDB wallet_trades (if configured)
  ├─ _persist_trade_local(trade_doc)    → SQLite wallet_trades_local (always)
  └─ _update_summary(trade_doc)         → SQLite wallet_activity_summary (always)
```

MongoDB is the primary trade store when available. SQLite is the safety net — trade records are **never lost** regardless of MongoDB configuration.

---

## Multi-Companion Access

The metadata layer is companion-agnostic by design:

- **Repository layer** (registry, summary, balance cache) — shared via `BaseRepository`, any companion can read/write
- **Tool injection** — per-persona via `mcp_access` field in persona JSON; add `"solana_wallet"` to grant access
- **Prompt injection** (`_build_wallet_state_context`) — called with `user_id`, not persona key; any companion seeing that user gets the same context
- **No architectural changes needed** — just add `"solana_wallet"` to a new companion's `mcp_access` array

---

## Repository Classes

| Repository | File | Tables Managed |
|---|---|---|
| `WalletRegistryRepository` | `repositories/wallet_registry_repository.py` | `wallet_registry` |
| `WalletSummaryRepository` | `repositories/wallet_summary_repository.py` | `wallet_activity_summary`, `wallet_balance_cache` |
| `TradeHistoryRepository` | `repositories/trade_history_repository.py` | `wallet_trades_local` |
| `WalletRepository` (existing) | `repositories/wallet_repository.py` | `user_wallets` (encrypted keys) |

All extend `BaseRepository` and are initialized in `startup.py` → `init_repositories()`.

**Getters** (from `startup.py`):
- `get_wallet_registry_repo()` → `WalletRegistryRepository`
- `get_wallet_summary_repo()` → `WalletSummaryRepository`
- `get_trade_history_repo()` → `TradeHistoryRepository`
- `get_wallet_repo()` → `WalletRepository` (existing)

---

## Startup Behavior

On server startup (`init_repositories()`):
1. All three new repos are initialized (tables auto-created via `_ensure_tables()`)
2. `wallet_summary_repo.reset_all_unlock_states()` is called — all wallets set to LOCKED
3. Users must unlock wallets with their password after each restart

---

## Dependencies

- `mnemonic>=0.21` — BIP39 mnemonic phrase generation (added to `requirements.txt`)
- `solders==0.26.0` — Solana keypair primitives (existing)
- `cryptography>=42.0.0` — AES-GCM encryption (existing)

---

## Key Files

| File | Role |
|---|---|
| `src/coordinator/repositories/wallet_registry_repository.py` | Multi-wallet CRUD, 3-wallet limit |
| `src/coordinator/repositories/wallet_summary_repository.py` | Activity summary + balance cache |
| `src/coordinator/repositories/trade_history_repository.py` | Local SQLite trade fallback |
| `src/coordinator/jupiter/wallet_manager.py` | BIP39 mnemonic + keypair derivation |
| `src/coordinator/services/query_handler_service.py` | Enriched context injection, 4-step creation flow |
| `src/coordinator/services/wallet_proposal_service.py` | Step message templates (4 steps) |
| `src/coordinator/services/wallet_execution_service.py` | Dual-write trades + summary update |
| `src/coordinator/startup.py` | Repo initialization + unlock state reset |

---

## Related Documentation

- [SQLITE_ARCHITECTURE.md](SQLITE_ARCHITECTURE.md) — Thread safety, base repository, migrations
- [../development/JUPITER_WALLET_IMPLEMENTATION.md](../development/JUPITER_WALLET_IMPLEMENTATION.md) — Jupiter MCP integration, tools, strategies
