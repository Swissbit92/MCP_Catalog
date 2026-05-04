---
title: Troubleshooting Guide
status: active
created: 2026-04-04
last_reviewed_on: 2026-04-19
review_in: 6 months
applies_to: nephilim
---

# Troubleshooting Guide

> Extracted from CLAUDE.md for token optimization.

## Backend won't start
- Verify Ollama running: `ollama serve`
- Check model pulled: `ollama list`
- Confirm `.env` has required vars

## MCP issues
- Verify Docker socket mounted
- Check API keys set in `.env`
- Test container spawn: `docker run -i --rm docker.io/mcp/brave-search`
- Check intent classification: `python -c "from src.coordinator.tools.intent_classifier import classify_query_intent; print(classify_query_intent('weather in London', 'legendary', ['brave_search', 'mongodb']))"`
- Brave MCP uses keyword force-search (bypasses LLM tool calling) — if queries aren't routed correctly, check `tools/keywords.py` keyword dictionaries
- **MCP queries return 500 with no traceback in logs**: Alembic's `fileConfig()` silences all app loggers after migration. Verify `alembic/env.py` has `disable_existing_loggers=False` and `alembic.ini` root logger is `level = INFO`
- **`UnboundLocalError: QueryHandlerService` on MCP queries**: Conditional import inside `if "solana_wallet"` block in `routes/chat.py` — the import must be at the top of the `chat()` function body, not inside any conditional

## Database issues
- Backup and delete `chats.db` to reset
- Schema auto-migrates on startup

## Docker networking
```bash
docker-compose down && docker network prune -f
docker-compose --env-file .env.docker up -d
python scripts/docker/verify_startup.py    # Always verify after rebuild
```

## Post-rebuild verification
**Mandatory after every Docker rebuild.** The `verify_startup.py` script checks:
- `/ready` endpoint returns 200 (DB + Ollama healthy)
- Brave MCP and MongoDB MCP match `.env.docker` config
- Live test queries (LLM greet, Brave search, MongoDB query) return valid responses

```bash
python scripts/docker/verify_startup.py              # Full check (subsystems + test queries)
python scripts/docker/verify_startup.py --skip-queries  # Quick check (subsystems only)
python scripts/docker/verify_startup.py --timeout 120   # Custom timeout for slow starts
```
If any check fails, investigate `docker logs ai-companion-api` before proceeding.
