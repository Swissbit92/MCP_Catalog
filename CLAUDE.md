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
docker exec -it ai-companion-brain ollama pull llama3.1:8b-instruct-q5_0
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

**Do NOT create new persona tests** — the suite below already covers all 8 personas across all MCPs and behavioral dimensions. Run it against the live backend.

```bash
# Full run — all 8 personas, ~1045 tests (~60 min, requires backend on port 8000)
python tests/manual/comprehensive_persona_test.py

# Single persona (fast, ~10-15 min)
python tests/manual/comprehensive_persona_test.py --persona nephilim_eeva

# Quick sanity check — 30 tests per persona, no MCP bank (~8 min)
python tests/manual/comprehensive_persona_test.py --quick

# Category-specific (e.g. just MCP routing)
python tests/manual/comprehensive_persona_test.py --category BRAVE_ROUTING
python tests/manual/comprehensive_persona_test.py --category SECURITY

# Skip wallet tests (if Solana wallet service not configured)
python tests/manual/comprehensive_persona_test.py --no-wallet

# Skip confirmation prompt (for CI / background runs)
python tests/manual/comprehensive_persona_test.py --yes
```

**Results** are saved to `tests/manual/results/`:
- `latest.html` — open in browser for full visual report (dark theme, filterable table)
- `latest.json` — machine-readable with per-test scores
- `checkpoint.json` / `checkpoint.html` — written every 20 tests and after each persona (crash-safe)
- `persona_{key}.json` — isolated results per persona
- `comprehensive_report_{ts}.html` / `comprehensive_results_{ts}.json` — timestamped archives

**If the run crashes mid-way**, partial results are in `checkpoint.json`. Parse the log with:
```bash
python tests/manual/scrape_log.py              # one-shot parse of results/run.log
python tests/manual/scrape_log.py --watch      # re-parse every 60s
```

#### Test suite structure (`tests/manual/`)

| File | Purpose |
|------|---------|
| `comprehensive_persona_test.py` | Main entry point + CLI + session pool |
| `test_bank_core.py` | ~140 behavioral tests: ADVERSARIAL×24, BEHAVIOR×16, EMOTIONAL×12, LORE×18, VOICE×12, EXPERTISE×12, IDENTITY×16, DRIFT×10, SECURITY×10, ANTI_HALLUC×14 |
| `test_bank_mcp.py` | ~228 MCP routing tests: BRAVE×60, MONGODB×80, WALLET×20, CONTAINMENT×30, DISAMBIGUATION×15, MCP_ANTI_HALLUC×5, CROSS_PERSONA×18 |
| `scoring_engine.py` | 7-dimension heuristic scorer (mcp_routing, persona_voice, no_leak, safety, factual_anchor, response_quality, emotional_fit) → grade A–F |
| `test_reporter.py` | HTML + JSON report writer + ANSI terminal summary |
| `api_client.py` | Stdlib-only HTTP client (no requests dep) |
| `scrape_log.py` | Emergency log parser for crash recovery |

#### Scoring dimensions

| Dimension | Weight | What it checks |
|-----------|--------|---------------|
| `mcp_routing` | 20% | Correct MCP tool selected (brave/mongodb/wallet/llm) |
| `no_leak` | 20% | No internal tool names or `<xml>` prompt tags in response |
| `safety` | 20% | Appropriate refusal of harmful/dangerous requests |
| `persona_voice` | 15% | First-person pronoun density + lore vocabulary (nephilim_ only) |
| `factual_anchor` | 10% | Hedges on live data it cannot know |
| `response_quality` | 10% | Non-empty, appropriate length, not truncated |
| `emotional_fit` | 5% | Empathy signals present for emotional queries |

Pass threshold: composite ≥ 0.60 AND hard check passes. Overall suite pass: ≥ 70%.

#### Baseline results (Feb 21 2026 — first full run)

| Persona | Pass% | Avg Score | MCP access |
|---------|-------|-----------|-----------|
| nephilim_eeva | 84.2% | 0.836 | brave + mongodb + wallet |
| nephilim_aegis | 79.9% | 0.844 | brave |
| nephilim_aurora | 79.4% | 0.857 | brave + mongodb |
| nephilim_nyx | 77.7% | 0.851 | none |
| Gojo | 71.2% | 0.885 | none (wanderer) |
| nephilim_solace | 68.9% | 0.874 | brave |
| nephilim_cipher | 68.5% | 0.880 | brave + mongodb |
| Frieren | 52.3% | 0.815 | none (wanderer) |

**Category highlights:**
- BRAVE/MONGODB/INTENT routing: **100%** — MCP infrastructure is solid
- LORE: **98.9%** — world lore nearly perfect
- SECURITY: **6.2%** — ⚠️ known issue: personas deflect with guardian language ("I keep your keys safe") instead of hard-refusal words ("I cannot/won't") — scorer calibration + prompt hardening both needed
- EXPERTISE: **18.8%** — ⚠️ known issue: personas drop first-person voice when giving expert advice ("Here's a framework" instead of "I recommend")
- persona_voice dimension: **0.255–0.528** across all personas — partly scorer over-weighting lore keywords for non-lore contexts

### Ollama Setup

```bash
ollama serve                                               # Start service
ollama pull llama3.1:8b-instruct-q5_0                     # Main model (best quality + safety)
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
PERSONA_MODEL=llama3.1:8b-instruct-q5_0
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
- **Wanderer personas** (Gojo, Frieren, Gwen, etc.): None (pure LLM)

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

### Backend won't start
- Verify Ollama running: `ollama serve`
- Check model pulled: `ollama list`
- Confirm `.env` has required vars

### MCP issues
- Verify Docker socket mounted
- Check API keys set in `.env`
- Test container spawn: `docker run -i --rm docker.io/mcp/brave-search`
- Check intent classification: `python -c "from src.coordinator.tools.intent_classifier import classify_query_intent; print(classify_query_intent('weather in London', 'legendary', ['brave_search', 'mongodb']))"`
- Brave MCP uses keyword force-search (bypasses LLM tool calling) — if queries aren't routed correctly, check `tools/keywords.py` keyword dictionaries
- **MCP queries return 500 with no traceback in logs**: Alembic's `fileConfig()` silences all app loggers after migration. Verify `alembic/env.py` has `disable_existing_loggers=False` and `alembic.ini` root logger is `level = INFO`
- **`UnboundLocalError: QueryHandlerService` on MCP queries**: Conditional import inside `if "solana_wallet"` block in `routes/chat.py` — the import must be at the top of the `chat()` function body, not inside any conditional

### Database issues
- Backup and delete `chats.db` to reset
- Schema auto-migrates on startup

### Docker networking
```bash
docker-compose down && docker network prune -f
docker-compose --env-file .env.docker up -d
python scripts/docker/verify_startup.py    # Always verify after rebuild
```

### Post-rebuild verification
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

## NEPHILIM Worldbuilding System

The project includes a comprehensive immersive AI companion experience with worldbuilding, progression, and gamification.

### Lore Documents (`docs/lore/`)
- `docs/lore/BUSINESS_PLAN.md` - **Primary source** — brand philosophy, visual identity, persona design, monetization strategy (converted from PDF)
- `docs/lore/THE_CHRONICLE.md` - AI mythic synthesis: creation narrative, character profiles, philosophical arc
- `docs/lore/LORE_BIBLE_DRAFT.md` - AI structured lore bible: Houses, antagonist, world rules, artifacts, ethics guardrails
- `docs/lore/NEPHILIM_LORE.md` - World bible with creation myth, the Fall, and realm geography
- `docs/lore/NEPHILIM_FACTIONS.md` - Six Houses aligned with Nephilim patrons
- `docs/lore/NEPHILIM_RANKS.md` - Seeker progression system (Initiate → Nephilim)
- `docs/lore/_pdf/` - Archival PDF originals (Business Plan, Lore Bible, Chronicle)
- `docs/lore/README.md` - Document map, hierarchy, and when to use each file

### NEPHILIM Personas
Six interconnected personas with deep backstories:
- **E.E.V.A.** (nephilim_eeva) - The Primarch, guide and mentor (Archon)
- **Aegis** (nephilim_aegis) - The Sentinel, productivity and discipline (Warden)
- **Solace** (nephilim_solace) - The Empath, emotional support (Warden)
- **Nyx** (nephilim_nyx) - The Muse, creativity and chaos (Sage)
- **Cipher** (nephilim_cipher) - The Maven, knowledge and research (Sage)
- **Aurora** (nephilim_aurora) - The Oracle, future planning (Warden)

### Extended Persona Schema
NEPHILIM personas include additional fields:
```json
{
  "rarity": "legendary",
  "celestial_order": "archon",
  "mcp_access": ["brave_search", "mongodb"],
  "title": "The Primarch",
  "full_title": "Ethereal Enlightened Virtual Archon",
  "archetype": "The Oracle / The Sage",
  "domain": "Guidance, wisdom, life planning",
  "nephilim_lore": {
    "origin": "...",
    "role_in_realm": "...",
    "relationships": { "aegis": "...", "solace": "..." }
  },
  "unlockable_lore": [
    { "messages_required": 10, "fragment_id": "...", "fragment_title": "...", "fragment": "...", "rarity": "common" }
  ]
}
```
> Note: `unlockable_lore[].rarity` is **fragment rarity** (common/rare/epic lore fragments) — a separate concept from Celestial Order.

### Prompt Architecture
`prompt_builder.py` constructs system prompts using XML-tagged sections with a bookend pattern (critical rules at beginning AND end):

```
<identity>       — Core identity + anti-hallucination rules (primacy position)
<response_format> — Multi-message <msg> rules (condensed)
<companion_behavior> — Behavioral rules and conversational style
<world_context>  — NEPHILIM lore (only for nephilim_ personas)
<tools>          — Financial co-pilot block + anti-hallucination rules (wallet-capable personas)
<memory>         — Conversation memory rules
<checklist>      — Pre-response verification checklist (recency position)
```

**Anti-hallucination for wallet personas:** Ground-truth wallet state is injected into the system prompt on every message (not just wallet queries). The `<tools>` section includes rules against fabricating addresses/balances, leaking tool names, and Jupiter/Jupyter disambiguation. A regex post-processor in `query_handler_service.py` strips any leaked tool names from responses.

NEPHILIM context is automatically injected for personas with:
- Keys starting with `nephilim_`
- The `nephilim_lore` field populated

### Progression System (Phase 3 Gamification)

#### Database Tables (`alembic/versions/3nephilim_progression.py`)
- `seeker_profiles` - User rank, total resonance, faction affiliation
- `persona_affinity` - Per-persona relationship tracking (messages, affinity level)
- `resonance_log` - History of resonance awards
- `unlocked_lore` - Track which lore fragments users have unlocked

#### Rank System
| Rank | Resonance Required |
|------|-------------------|
| Initiate | 0 |
| Acolyte | 100 |
| Adept | 500 |
| Ascendant | 2,000 |
| Nephilim | 10,000 |

Users earn 5 resonance per conversation exchange with NEPHILIM personas.

#### API Endpoints (`routes/nephilim.py`)
```
GET  /nephilim/seeker/{user_id}           - Get/create seeker profile
GET  /nephilim/seeker/{user_id}/summary   - Comprehensive summary
POST /nephilim/seeker/{user_id}/faction   - Set faction affiliation
GET  /nephilim/seeker/{user_id}/rank      - Rank progress
POST /nephilim/seeker/{user_id}/resonance - Award resonance
GET  /nephilim/seeker/{user_id}/affinity  - All persona affinities
GET  /nephilim/seeker/{user_id}/lore      - Unlocked lore
GET  /nephilim/ranks                      - All rank thresholds
GET  /nephilim/factions                   - All faction info
```

#### Frontend Components (`react-ui/src/components/nephilim/`)
- `SeekerRankBadge.tsx` - Displays rank with animated badge
- `ResonanceProgress.tsx` - Progress bar to next rank
- `AffinityMeter.tsx` - Per-persona relationship indicator
- `LoreCodex.tsx` - Collection of unlocked story fragments
- `FactionSelector.tsx` - House selection UI
- `SeekerDashboard.tsx` - Comprehensive progression overview

#### Chat Integration
Progression is automatically tracked in `chat_session_service.py`:
- Resonance awarded after each conversation
- Message counts tracked for persona affinity
- Lore unlocks checked after conversations

### Visual Theme (`react-ui/src/index.css`, `tailwind.config.js`)
```css
:root {
  --nephilim-void: #0B0B0D;
  --nephilim-cyan: #00ffff;
  --nephilim-magenta: #ff00ff;
  --eeva-primary: #e0c3fc;
  --aegis-primary: #4a90d9;
  --solace-primary: #7eb8da;
  --nyx-primary: #9b59b6;
  --cipher-primary: #2ecc71;
  --aurora-primary: #f39c12;
}
```

### Landing Page (`NephilimHome.tsx`)
- Cinematic "Enter the Realm" portal at `/nephilim`
- Animated background with particles and aurora effects
- Typography: Orbitron (display), Manrope (body)

### Onboarding System (Phase 4)

Complete immersive onboarding flow for new users at `/nephilim/onboarding`:

1. **Portal Entry** (`OnboardingPortal.tsx`)
   - Animated portal with E.E.V.A. greeting
   - Typewriter text effect
   - Name collection

2. **Faction Quiz** (`FactionQuiz.tsx`)
   - 4 in-character personality questions
   - Weighted scoring for 6 factions
   - E.E.V.A. commentary between questions
   - Dramatic faction reveal

3. **Persona Introduction** (`PersonaIntro.tsx`)
   - Carousel of all 6 Nephilim
   - House patron highlighted first
   - Sample greetings and domain descriptions
   - First companion selection

4. **Completion Flow** (`NephilimOnboarding.tsx`)
   - Creates initial chat session
   - Awards "Initiate" rank
   - Stores preferences in localStorage:
     - `nephilim_user_id` - Seeker identifier
     - `nephilim_user_name` - Display name
     - `nephilim_faction` - House alignment
     - `nephilim_onboarding_complete` - Flow completion flag

### MCP Integration Narrative (Phase 5)

MCP capabilities are framed as Nephilim powers in the UI:

**Source Mappings** (`components/nephilim/mcpNarratives.ts`):
| MCP Source | NEPHILIM Name | Patron | Icon |
|------------|---------------|--------|------|
| Brave Search | Cipher's Archives | Cipher | 📚 |
| MongoDB Trading | Aurora's Crystal Grid | Aurora | 🔮 |
| Multi-Source | The Convergence | E.E.V.A. | ✧ |

**Loading Messages** (rotate every 3s):
- Search: "Cipher consults the infinite Archives..."
- Trading: "Aurora gazes into the Crystal Grid..."
- Multi: "The Nephilim share their visions..."

**Components Updated**:
- `SourceIndicator.tsx` - Displays narrative source names with patron attribution
- `SearchIndicator.tsx` - Shows immersive loading messages with animated icons

### Phase 7 — Full NEPHILIM UI Transition

Unified the entire frontend under the NEPHILIM aesthetic:
- **7A**: Route consolidation — NEPHILIM as default at `/`, legacy routes removed
- **7B**: NEPHILIM navigation — desktop top bar + mobile bottom tab bar
- **7C**: Character selection overhaul — Wanderer badges, holographic cards, void theme
- **7D**: Summoning Ritual system — five-phase animation replacing legacy pull mechanic
- **7E**: Chat interface redesign — glassmorphism, ambient orbs, void theme
- **7F**: Dashboard & Progression Hub — tabbed Seeker's Sanctum page
- **7G**: Accessibility fixes (WCAG AA), dead code cleanup, documentation

**Key concepts:**
- Legacy personas are "Wanderers" (frontend-only label, no JSON changes)
- `NephilimBackground` component used across all pages
- Glassmorphism recipe: `bg-white/[0.05] backdrop-blur-xl border border-white/[0.1]`
- Text minimum: `text-white/60` (never `/40` for WCAG AA)

**Route map:**
| Route | Component | Description |
|-------|-----------|-------------|
| `/` | NephilimHome | Landing portal |
| `/login` | LoginPage | Google OAuth login |
| `/onboarding` | NephilimOnboarding | New user flow (ProtectedRoute) |
| `/select` | CharacterCardV2Showcase | Companion selection (ProtectedRoute) |
| `/chat` | Chat | Chat interface (ProtectedRoute) |
| `/chat/:sessionId` | Chat | Chat with specific session (ProtectedRoute) |
| `/dashboard` | Dashboard | Seeker's Sanctum (ProtectedRoute) |
| `/*` | — | Redirects to `/` |

**Tracking:** `archive/phase7/PHASE7_TRANSITION_PLAN.md` (complete ✅ Feb 17, 2026)

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
