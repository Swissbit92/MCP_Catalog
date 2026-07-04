---
title: Development, Deployment & Operations
status: active
created: 2026-07-04
last_reviewed_on: 2026-07-04
review_in: 6 months
applies_to: services/telegram-gateway
---

# Development, Deployment & Operations

## Setup

```bash
cd services/telegram-gateway
python3.12 -m venv venv            # dedicated venv, Python 3.12 (never system 3.14)
./venv/bin/pip install -e ".[dev]"
# .env already exists (chmod 600) — reuses the shared eeva-dca/eeva-exec bot token.
```

## Configuration (.env)

| Var | Required | Default | Notes |
|-----|----------|---------|-------|
| `TG_BOT_TOKEN` | yes | — | Reuses the shared E.E.V.A. notification bot token (eeva-dca/eeva-exec). Safe: those notifiers are send-only, and only one process may long-poll a token — this gateway is the sole poller. Bearer secret — chmod 600, never logged. |
| `TG_ALLOWED_CHAT_IDS` | yes | — | Comma-separated numeric chat ids. Everyone else is silently ignored. |
| `NEPHILIM_BASE_URL` | no | `http://127.0.0.1:8000` | MUST stay loopback (coordinator has no auth). |
| `EEVA_PERSONA_KEY` | no | `nephilim_eeva` | Default persona for chats without an override. |
| `TG_CHAT_PERSONAS` | no | (empty) | Per-chat overrides: `chat_id:persona_key,…`. Lets a second person use a different persona. |
| `NEPHILIM_TIMEOUT_SECONDS` | no | `180` | Read timeout for a chat turn (local 24B is slow). |
| `TG_TYPING_INTERVAL_SECONDS` | no | `4.5` | Re-send interval for the typing action (<5s). |
| `TG_MESSAGE_CHAR_LIMIT` | no | `4000` | Soft split cap (hard Telegram limit is 4096). |
| `TG_LOG_CONTENT` | no | `false` | DEBUG only — logs raw message text. Leave false in prod. |

## Tests

```bash
./venv/bin/pytest tests/ -q                         # all unit tests
./venv/bin/pytest tests/ -q --cov=eeva_telegram     # with coverage
./venv/bin/ruff check . && ./venv/bin/ruff format --check .
```

Telegram and the coordinator are fully mocked (no network). What only the live smoke test can cover — allowlist rejection against a real second account, real typing indicator, launchd supervision — is listed in `scripts/smoke_test.sh`.

## Live smoke test

`scripts/smoke_test.sh` checks `.env` + coordinator reachability (`GET /health`), then runs the bot in the foreground and prints a 7-point manual checklist (greeting, typing, >4096 split, forwarded refusal, non-allowlisted silence, `/reset` amnesia, backend-down graceful degradation). Nothing here spends money.

## Deployment (launchd, always-on)

The bot is a long-polling daemon (`RunAtLoad` + `KeepAlive`), independent of the coordinator's own `com.nephilim.backend`/`com.nephilim.frontend` launchd jobs.

```bash
ln -sf "$(pwd)/launchd/com.eeva.telegram.plist" ~/Library/LaunchAgents/
launchctl load   ~/Library/LaunchAgents/com.eeva.telegram.plist
launchctl list | grep com.eeva.telegram        # expect a live PID
launchctl unload ~/Library/LaunchAgents/com.eeva.telegram.plist   # kill switch
```

Conventions (shared with eeva-dca/eeva-exec):
- The plist calls this subfolder's venv python binary **directly** — never bash (macOS TCC blocks bash under launchd).
- The plist carries **no secrets** (only `PATH`). It is world-readable under `~/Library/LaunchAgents`; the token lives only in this subfolder's `.env`.
- Logs: `logs/launchd-telegram.stdout.log` / `.stderr.log` (local to this subfolder, not the coordinator's `logs/`).

## Operations

- **Kill switch:** `launchctl unload …`. The ultimate one is revoking the bot token in @BotFather (this stops eeva-dca/eeva-exec notifications too, since the token is shared — be aware before rotating).
- **Single poller:** only ONE process may poll a given bot token (Telegram 409 otherwise). The `flock` guard in `bin/run_telegram_bot.py` makes a second instance exit cleanly, but never run the smoke test while the launchd daemon is loaded.
- **Backend restart mid-chat:** the bot returns a generic "having trouble connecting" reply and keeps polling; no crash.
- **Session growth:** `/reset` clears history in place (same session, progression preserved) — it does not create orphan sessions.
- **Adding a person:** add their numeric `chat_id` to `TG_ALLOWED_CHAT_IDS` (and optionally a `TG_CHAT_PERSONAS` entry for a different persona), then reload the daemon. No code change.
