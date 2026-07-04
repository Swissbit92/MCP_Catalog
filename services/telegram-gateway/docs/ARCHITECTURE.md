---
title: Architecture
status: active
created: 2026-07-04
last_reviewed_on: 2026-07-04
review_in: 6 months
applies_to: services/telegram-gateway
---

# Architecture

Reference-style: tables and the request flow, not prose narratives.

## System context

```
Telegram app  <--long polling-->  telegram-gateway  --HTTP-->  coordinator (127.0.0.1:8000)  -->  Ollama (local 24B)
```

The bot is a stateless relay. All conversation state (history, emotional state, progression) lives in the coordinator's own SQLite; the bot keeps only a tiny local map of which coordinator session belongs to which Telegram chat. There is no code import between this subfolder and `../../src/coordinator/` — all coupling is the HTTP session API.

## Request flow (one text turn)

1. `text_message` handler receives an update.
2. **Allowlist gate** — non-allowlisted `chat_id` → silent return (no reply, no content log, no backend call).
3. **Forwarded guard** — `is_forwarded` → refuse, never call the LLM.
4. Resolve persona for the chat (`config.persona_for_chat`).
5. Acquire the global `llm_lock` (serialise — `OLLAMA_NUM_PARALLEL=1`) and start the typing indicator.
6. `relay.handle_user_message` → ensure/reuse session → `POST /sessions/{id}/chat`. On 404 (stale session) recreate once and retry.
7. `extract_messages` turns the response into an ordered list (`message_flow: "multi"` → multiple messages).
8. `messaging.send_messages` → split at the char limit, send each chunk with link previews disabled.

## Components

| Component | Responsibility | Module |
|-----------|----------------|--------|
| Config | Fail-fast `.env` load, allowlist, per-chat persona overrides | `eeva_telegram/config.py` |
| Coordinator client | Async HTTP wrapper + typed error hierarchy | `eeva_telegram/nephilim_client.py` |
| Session store | `(chat_id, persona_key) → session_id` sqlite map | `eeva_telegram/session_store.py` |
| Relay | Session lifecycle, 404-recreate retry, response→messages | `eeva_telegram/relay.py` |
| Splitter | Paragraph/sentence-aware 4096-char splitting | `eeva_telegram/splitter.py` |
| Messaging | Outbound sends (link previews off, plain text) | `eeva_telegram/messaging.py` |
| Typing indicator | Repeating `typing…` chat action while generating | `eeva_telegram/typing_indicator.py` |
| Handlers | PTB glue: allowlist, forwarded guard, error mapping, `/start` `/reset` | `eeva_telegram/handlers.py` |
| Bot factory | Wire handlers + gateway + shutdown cleanup | `eeva_telegram/bot.py` |
| Entrypoint | flock singleton guard, logging, `run_polling` | `bin/run_telegram_bot.py` |

## Data

| Source | Format | Writer | Readers |
|--------|--------|--------|---------|
| `data/sessions.sqlite3` | SQLite `chat_sessions(chat_id, persona_key, session_id, …)` | this bot | this bot |
| `data/bot.lock` | flock advisory lock file | this bot (entrypoint) | this bot |
| Coordinator SQLite (`chats.db`) | sessions/messages/progression | coordinator | coordinator |

The bot never writes to the coordinator's database — only through its HTTP API.

## Key invariants

- Zero coordinator changes; all coupling is the HTTP session API — see [../CLAUDE.md](../CLAUDE.md).
- The security boundary is the Telegram allowlist + a loopback-only backend (coordinator chat routes have no auth).
- No secrets in the launchd plist; this subfolder's own `.env` (chmod 600) is the only secret source.
- No exec/file/trading access in this process.
- One in-flight LLM call (`llm_lock`); one poller per bot token (`flock`).

## Cross-repo contracts

- Coordinator session API (consumed, not owned): `POST /sessions`, `POST /sessions/{id}/greet`, `POST /sessions/{id}/chat`, `DELETE /sessions/{id}/messages`. See `../../src/coordinator/routes/sessions.py` and `routes/chat.py`.
