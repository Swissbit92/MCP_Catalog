# SQLite Architecture

Architecture decision record and operational guide for the SQLite persistence layer.

---

## ADR: Why SQLite

**Decision:** Use SQLite as the primary datastore.

**Context:** MCP Coordinator is a local-first, single-user application running on a developer machine or personal server. It requires persistent chat history, session management, and progression tracking.

**Rationale:**
- **Zero infrastructure:** No separate database process to run or Docker service to manage
- **Single file:** The entire database is `chats.db` — easy to back up, copy, or reset
- **Python built-in:** `sqlite3` is in the standard library, no driver dependencies
- **Performance sufficient:** Sequential reads/writes with <100 concurrent requests never saturate SQLite
- **Trade-off accepted:** Not suitable for multi-user deployment or horizontal scaling

**Rejected alternatives:**
- PostgreSQL: Requires a running server, overkill for local-first use case
- MongoDB: Reserved for trading data via MCP integration, not application state
- Redis: Ephemeral by default, would need persistence config for state

---

## Thread Safety Pattern

All database access goes through `BaseRepository` (`src/coordinator/repositories/base_repository.py`), which enforces thread safety via a threading lock.

```python
class BaseRepository:
    def __init__(self, ...):
        self._lock = threading.Lock()

    def _execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:              # Serializes all writes
            return self._adapter.execute(query, params)

    def _fetchone_dict(self, query, params=()):
        with self._lock:              # Also serializes reads
            return self._adapter.fetchone(query, params)
```

**Connection flags:**
```python
conn = sqlite3.connect(db_path, check_same_thread=False)
```

`check_same_thread=False` allows a connection created in one thread to be used in another. The `_lock` above serializes all access, so this is safe.

---

## Schema Overview

### Core Tables

**`chat_sessions`**
```sql
CREATE TABLE chat_sessions (
    session_id    TEXT PRIMARY KEY,
    persona_key   TEXT NOT NULL,
    title         TEXT,
    created_at    TEXT,
    updated_at    TEXT
);
```

**`messages`**
```sql
CREATE TABLE messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role          TEXT NOT NULL,      -- 'user' | 'assistant'
    content       TEXT NOT NULL,
    timestamp     TEXT,
    latency_ms    INTEGER
);
```

**`conversation_summaries`**
```sql
CREATE TABLE conversation_summaries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    message_range   TEXT,             -- e.g. "1-20"
    summary_text    TEXT,
    emotional_developments TEXT
);
```

### NEPHILIM Progression Tables

**`seeker_profiles`** — User rank and faction affiliation
**`persona_affinity`** — Per-persona relationship tracking (message counts, affinity level)
**`resonance_log`** — History of all resonance point awards
**`unlocked_lore`** — Which lore fragments each user has unlocked

See `alembic/versions/3nephilim_progression.py` for full DDL.

### Wallet Metadata Tables

**`wallet_registry`** — Per-user multi-wallet registry with 3-wallet limit enforcement and slot management
**`wallet_activity_summary`** — Pre-computed trading activity summary (trade count, volume, last trade)
**`wallet_balance_cache`** — Per-wallet cached SOL balance, token count, and lock/unlock state
**`wallet_trades_local`** — SQLite trade history fallback (dual-write with MongoDB)

See [WALLET_METADATA.md](WALLET_METADATA.md) for full DDL, data flow, and what the AI companion can see.

### Cascade Deletes

Foreign keys use `ON DELETE CASCADE` so deleting a session automatically removes all associated messages, summaries, and emotional state records. This keeps cleanup simple.

---

## Alembic Migrations

Schema changes use Alembic for versioned migrations:

```
alembic/
├── env.py                              # Alembic environment config
└── versions/
    ├── 1init_schema.py                 # Initial tables
    ├── 2emotional_state.py             # Emotional state tracking
    └── 3nephilim_progression.py        # NEPHILIM gamification tables
```

**Apply migrations:**
```bash
alembic upgrade head
```

**Create a new migration:**
```bash
alembic revision --autogenerate -m "description"
```

**Auto-migration on startup:**
`startup.py` calls schema initialization at app start, which creates missing tables if they don't exist (idempotent `CREATE TABLE IF NOT EXISTS`).

---

## Backup Procedures

**Simple backup:**
```bash
cp chats.db chats.db.backup
```

**Reset database:**
```bash
rm chats.db   # Schema recreates automatically on next startup
```

**Export sessions:**
```bash
sqlite3 chats.db ".dump" > backup.sql
```

---

## Concurrency Limits

SQLite serializes all writes. Under normal usage (single user, sequential chat messages), this is not a bottleneck. However:

- Do **not** run multiple backend instances against the same `chats.db` — WAL mode would be needed for that
- Async endpoints use `asyncio.to_thread` for blocking SQLite calls to prevent event loop starvation
- The `_lock` in `BaseRepository` is per-repository-instance; each repository has its own lock

---

## References

- `src/coordinator/repositories/base_repository.py` — Thread-safe base class
- `src/coordinator/repositories/db_adapter.py` — Connection management
- `src/coordinator/startup.py` — Schema initialization on startup
- `alembic/` — Migration history
