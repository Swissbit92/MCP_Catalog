# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP Coordinator is a **local-first persona-driven chat interface** combining a FastAPI backend with a React frontend. It enables conversations with AI personas powered by Ollama LLM models, featuring a summoning-style character collection system with persistent chat history.

**Key Architecture:**
- **Backend**: FastAPI coordinator (`src/coordinator/`) bridging persona definitions with Ollama LLM
- **Frontend**: React 19 + TypeScript with Framer Motion animations and Tailwind CSS
- **Persistence**: SQLite database (`chats.db`) for sessions, messages, and collections
- **Personas**: JSON-defined characters in `personas/` with lore, voice, behavior, and expertise
- **MCP Integration**: Brave Search (web) and MongoDB (trading data) via Docker STDIO containers

## Development Commands

### Docker (Recommended)

```bash
# One-command setup
.\scripts\docker\setup-docker.ps1    # Windows PowerShell
./scripts/docker/setup-docker.sh     # Linux/Mac

# Manual start
docker-compose --env-file .env.docker up -d

# Pull models (required on first run)
docker exec -it ai-companion-brain ollama pull gemma2:9b-instruct-q5_K_M
docker exec -it ai-companion-brain ollama pull nomic-embed-text:latest

# Common operations
docker-compose logs -f backend       # View logs
docker-compose restart backend       # Restart
docker-compose down                  # Stop all

# Rebuild backend (ALWAYS verify after rebuild)
docker-compose --env-file .env.docker build --no-cache backend
docker-compose --env-file .env.docker up -d backend
python scripts/docker/verify_startup.py          # Mandatory post-rebuild check
python scripts/docker/verify_startup.py --skip-queries  # Quick mode (subsystems only)
```

**Access:** Frontend `http://localhost:3000` | Backend `http://localhost:8000` | API Docs `http://localhost:8000/docs`

> **⚠️ Note:** Docker serves legacy UI unless rebuilt. For Phase 7 NEPHILIM UI, use local development.

### Local Development (Phase 7 NEPHILIM UI)

```bash
# Setup
pip install -r requirements.txt
cd react-ui && npm install

# Run Phase 7 NEPHILIM UI (Terminal 1)
python -m uvicorn src.coordinator.server:app --reload --port 8000

# Run Phase 7 NEPHILIM UI (Terminal 2)
cd react-ui && PORT=3001 npx react-scripts start

# Access at http://localhost:3001

# Run Legacy UI (unified - starts both on port 3000)
python scripts/utils/run_react.py

# Build
cd react-ui && npm run build
```

**CORS Configuration:** `src/coordinator/server.py:41` allows `localhost:3000` and `localhost:3001`

### Testing

```bash
# React tests
cd react-ui && npm test
cd react-ui && npm test -- --testNamePattern="MessageBubble" --watchAll=false

# Playwright E2E tests
cd react-ui && npx playwright test                    # Run all E2E tests
cd react-ui && npx playwright test --headed           # Run with browser visible

# Python tests (run from project root)
pytest tests/backend/                    # Backend unit tests
pytest tests/integration/                # Integration tests
pytest tests/evaluation/ -v              # RAGAS persona quality
```

### Comprehensive Persona Test Suite (primary quality gate)

**Do NOT create new persona tests** — the suite covers all 8 personas across all MCPs and behavioral dimensions.

```bash
# Full run — all 8 personas, ~1045 tests (~60 min, requires backend on port 8000)
python tests/manual/comprehensive_persona_test.py

# Single persona (fast, ~10-15 min)
python tests/manual/comprehensive_persona_test.py --persona nephilim_eeva

# Quick sanity check — 30 tests per persona, no MCP bank (~8 min)
python tests/manual/comprehensive_persona_test.py --quick
```

Results saved to `tests/manual/results/`. Pass threshold: composite >= 0.60. Suite pass: >= 70%.

> **Scoring dimensions, test bank structure, and baseline results:** See [`docs/NEPHILIM_REFERENCE.md`](docs/NEPHILIM_REFERENCE.md).

### Ollama Setup

```bash
ollama serve                                               # Start service
ollama pull gemma2:9b-instruct-q5_K_M                     # Main model (best storytelling + safety balance)
ollama pull nomic-embed-text:latest                        # Embeddings (RAG memory)
# Optional: ollama pull nchapman/gemma-2-9b-it-abliterated:9b  # Alt model (PERSONA_MODEL_B)
```

## Project Structure

### Backend (`src/coordinator/`)

```
server.py, startup.py          # App entry, lifecycle
config.py, schemas.py          # Settings, API schemas
routes/                        # chat.py, sessions.py, personas.py, nephilim.py, auth.py
services/                      # Business logic (llm_completion, tool_calling, citation, chat_session, query_handler, wallet_*, strategy, etc.)
repositories/                  # SQLite data access — ALL extend BaseRepository via db_adapter (connection pooling)
                               #   session, message, summary, emotional_state, seeker_progression,
                               #   user_profile, user (OAuth), trade_proposal, wallet
models/                        # persona_schema.py, sampling_presets.py, mcp_models.py
tools/                         # intent_classifier.py, synthesis_prompts.py, keywords.py, tool_generators.py, tool_utils.py
mongodb/                       # MongoDB MCP client
```

**Key files:**
- `llm_client.py` - LLM orchestration facade (passes per-persona sampling overrides)
- `prompt_builder.py` - System prompt construction from persona JSON (XML-tagged sections with bookend pattern)
- `mcp_client_stdio.py` - Brave Search MCP client
- `persona_memory.py` - CV summary generation and caching
- `memory_manager.py`, `memory_rag.py` - RAG semantic search
- `tools/intent_classifier.py` - Query intent classification (wallet, brave, mongodb, llm) with follow-up detection
- `tools/keywords.py` - Keyword dictionaries for intent classification routing

### Frontend (`react-ui/src/`)

```
pages/                         # Chat.tsx, NephilimHome.tsx, NephilimOnboarding.tsx, CharacterCardV2Showcase.tsx, Dashboard.tsx
components/                    # UI components (Header, MessageBubble, CharacterCard, SessionList, etc.)
components/nephilim/           # NEPHILIM progression components (SeekerRankBadge, LoreCodex, etc.)
context/                       # PersonaContext.tsx (composition wrapper), ChatContext.tsx, CollectionContext.tsx, AudioContext.tsx
services/api/                  # Domain-split API client: base.ts, auth.ts, sessions.ts, chat.ts, nephilim.ts, wallet.ts, personas.ts
services/api.ts                # Barrel re-export (backward compat: import from here as before)
types/                         # personas.ts (canonical Persona type), index.ts barrel
utils/                         # animations.ts, helpers, celestialOrder.ts
```

### Database Schema

**Core Tables:**
- `chat_sessions`: session_id, persona_key, title, timestamps
- `messages`: id, session_id, role, content, timestamp, latency_ms
- `conversation_summaries`: session_id, message_range, summary_text, emotional_developments

**NEPHILIM Progression Tables:**
- `seeker_profiles`: user_id, rank_name, total_resonance, faction_primary, faction_secondary
- `persona_affinity`: user_id, persona_key, messages_count, affinity_level
- `resonance_log`: user_id, amount, reason, persona_key, session_id
- `unlocked_lore`: user_id, persona_key, fragment_id, unlocked_at

> **Architecture details:** See `docs/architecture/SQLITE_ARCHITECTURE.md` for thread-safety pattern, migration guide, and backup procedures.

## Environment Variables

Required in `.env`:
```bash
OLLAMA_BASE=http://127.0.0.1:11434
PERSONA_MODEL=gemma2:9b-instruct-q5_K_M
PERSONA_TEMPERATURE=0.9
COORD_PORT=8000
PERSONA_DIR=personas
```

Optional (see `.env.docker` for full list):
- `BRAVE_API_KEY` - Web search (access controlled per-persona via `mcp_access` in persona JSON)
- `MONGODB_URI` - Trading data (access controlled per-persona via `mcp_access` in persona JSON)
- `MEMORY_EMBEDDING_MODEL` - RAG embeddings

## Code Style

### Python
- PEP 8, 4-space indent, type hints (`from __future__ import annotations`)
- `snake_case` functions/modules, `PascalCase` classes
- Async/await preferred, `HTTPException` for errors

### React/TypeScript
- `PascalCase` components, explicit types, strict mode
- No semicolons, 2-space indent (ESLint enforced)
- Tailwind for utilities, Framer Motion for animations
- Canonical `Persona` type lives in `react-ui/src/types/personas.ts` — import from there, never redefine locally
- New code should use `useChat()` / `useCollection()` hooks; `usePersona()` is kept for backward compat
- API functions: import from `'../services/api'` (barrel) or the specific domain module in `services/api/`

### Design System
- **Typography:** Outfit (display), Manrope (body), Space Mono (mono)
- **Celestial Order Colors:** Wanderer (silver `#C0C0C0`), Sage (cyan `#00BFFF`), Warden (purple `#DA70D6`), Archon (gold `#FFD700`)
- **Accessibility:** WCAG AA, 4.5:1 contrast, keyboard nav, `aria-label` on interactive elements

## Key Workflows

### Adding a Persona
1. Copy `personas/template.jsonc` to `personas/[name].json`
2. Fill in: key, display_name, rarity, celestial_order, mcp_access, lore, voice, behavior, expertise
3. Add images to `react-ui/public/images/personas/[name]/` (card.png, avatar.png, logo.png)
4. Persona auto-discovered on next load - no restart needed

> **Full field reference:** See `docs/development/PERSONA_SCHEMA.md` for all fields, valid values, and NEPHILIM-only extended schema.

### Chat Flow
1. Frontend POST `/greet` creates session
2. User message → POST `/sessions/{session_id}/chat` with persona, message
3. Backend builds system prompt from persona JSON + cached CV summary (XML-tagged sections)
4. For wallet-capable personas: ground-truth wallet state injected into system prompt (anti-hallucination)
5. Intent classifier routes query → wallet / brave / mongodb / pure LLM
6. Ollama generates response with per-persona sampling overrides (min_p, repeat_penalty), stored in SQLite
7. Post-processor strips leaked tool names via regex, enforces first-person
8. Frontend renders with Celestial Order theming

### MCP Integration Patterns
- **Ephemeral (Brave):** `docker run -i --rm` per request, dies after 2-3s
- **Long-Running (MongoDB):** Container stays alive for multiple requests
- Feature access controlled per-persona via `mcp_access` field in persona JSON (fallback: rarity-based `.env` vars)

### MCP Query Routing Pipeline
Queries flow through a two-layer classification system:

1. **Intent Classifier** (`tools/intent_classifier.py`): Keyword-based routing determines which MCP to use (web/mongodb/wallet/llm). Uses keyword dictionaries from `tools/keywords.py`.
2. **Tool Calling Service** (`services/tool_calling_service.py`): When Brave search is needed, force-executes the search directly via Docker instead of relying on the local LLM to generate JSON tool calls (small models are unreliable at structured tool calling). This "keyword force search" pattern bypasses the LLM tool-calling loop entirely.

**Anti-hallucination guards:**
- If keyword filter says search is needed but search returns no results → honest "I don't know" response
- If LLM somehow bypasses force-search and doesn't call the tool → honest "I don't know" response
- LLM-generated citations are stripped and replaced with verified citations from actual search results

## Important Implementation Details

### Celestial Order & Per-Persona MCP Access
MCP access is now controlled per-persona via the `mcp_access` field in persona JSONs, with legacy rarity-based env var fallback:
- **E.E.V.A.** (Archon): Brave + MongoDB (all access)
- **Aegis** (Warden): Brave only (productivity needs web, not trading)
- **Aurora** (Warden): Brave + MongoDB (Oracle gazes into data)
- **Solace** (Warden): Brave only (empathy needs resources, not trading)
- **Cipher** (Sage): Brave + MongoDB (Maven's identity is data research)
- **Nyx** (Sage): None (creativity flows from imagination)
- **Wanderer personas** (Gojo, Gwen, etc.): None (pure LLM)

### SQLite Concurrency
- Thread-safe locking via `_lock` in `repositories/base_repository.py`
- Connection uses `check_same_thread=False`
- Foreign key cascade deletes for cleanup

### Backend Configuration
- All config access via `get_settings()` returning a typed `AppSettings` Pydantic model
- Legacy `get_*()` getter functions have been removed — use `get_settings().subsystem.field` instead
- All repositories extend `BaseRepository` in `db_adapter.py` — never open raw `sqlite3.connect()` calls

### React Performance
- `React.memo` for expensive components (MessageBubble, CharacterCard)
- Virtualized message list with react-window
- Hardware-accelerated Framer Motion animations
- `useCallback` on all context CRUD functions (ChatContext) and event handlers (Chat.tsx, CharacterCardV2Showcase)
- `useMemo` for derived state (search filtering in CharacterCardV2Showcase)
- Authenticated API calls use `fetchWithAuth()` (auto-injects Bearer token, handles 401 refresh)

## Troubleshooting

See [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) for: backend startup, MCP issues, database reset, Docker networking, post-rebuild verification.

## NEPHILIM System

6 interconnected personas (E.E.V.A., Aegis, Solace, Nyx, Cipher, Aurora) with worldbuilding, progression (5 ranks), and gamification. Prompt construction via `prompt_builder.py` (XML-tagged bookend pattern). Anti-hallucination for wallet personas via ground-truth injection.

> **Full reference:** [`docs/NEPHILIM_REFERENCE.md`](docs/NEPHILIM_REFERENCE.md) — personas, schema, progression tables, visual theme, onboarding, Phase 7 details.
> **Lore documents:** [`docs/lore/README.md`](docs/lore/README.md) — worldbuilding, factions, ranks.

## Documentation

- `README.md` - User setup guide, features
- `docs/setup/DOCKER_QUICKSTART.md` - Docker deployment
- `docs/development/ADDING_MCP_SERVERS.md` - MCP integration guide
- `docs/development/TESTING_GUIDE.md` - Testing guide
- `docs/lore/` - All NEPHILIM worldbuilding and lore documents (see `docs/lore/README.md`)

### Protected Reference Files (do NOT delete)

These files have **no build dependency** and are never imported, so automated cleanup passes may flag them as dead code. **Do not delete them.** Open directly in a browser for visual reference during CSS iteration.

| File | Purpose |
|------|---------|
| `react-ui/rarity-effects-showcase.html` | **Canonical VFX reference** — gacha-quality card effect showcase (12 variants). Use this when iterating on card effects without needing the dev server. Uses legacy `.rarity-*` class names — see the file header for mapping to current `.order-*` equivalents. Live implementations: `CharacterCard.module.css` (V1) and `CharacterCardV2.module.css` (V2). |
