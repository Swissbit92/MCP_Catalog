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
docker exec -it ai-companion-brain ollama pull nchapman/gemma-2-9b-it-abliterated:9b
docker exec -it ai-companion-brain ollama pull nomic-embed-text:latest

# Common operations
docker-compose logs -f backend       # View logs
docker-compose restart backend       # Restart
docker-compose down                  # Stop all
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
cd react-ui && npx playwright test phase6-filter      # Run specific test file

# Python tests (run from project root)
pytest tests/backend/                    # Backend unit tests
pytest tests/integration/                # Integration tests
pytest tests/evaluation/ -v              # RAGAS persona quality
```

### Ollama Setup

```bash
ollama serve                                               # Start service
ollama pull nchapman/gemma-2-9b-it-abliterated:9b         # Main model
ollama pull nomic-embed-text:latest                        # Embeddings (RAG memory)
```

## Project Structure

### Backend (`src/coordinator/`)

```
server.py, startup.py          # App entry, lifecycle
config.py, schemas.py          # Settings, API schemas
routes/                        # chat.py, sessions.py, personas.py, nephilim.py
services/                      # Business logic (llm_completion, tool_calling, citation, etc.)
repositories/                  # SQLite data access (session, message, summary, emotional_state, seeker_progression)
models/                        # persona_schema.py, sampling_presets.py, mcp_models.py
tools/                         # intent_classifier.py, synthesis_prompts.py, keywords.py, tool_generators.py, tool_utils.py
mongodb/                       # MongoDB MCP client
```

**Key files:**
- `llm_client.py` - LLM orchestration facade
- `prompt_builder.py` - System prompt construction from persona JSON
- `mcp_client_stdio.py` - Brave Search MCP client
- `persona_memory.py` - CV summary generation and caching
- `memory_manager.py`, `memory_rag.py` - RAG semantic search

### Frontend (`react-ui/src/`)

```
pages/                         # Chat.tsx, NephilimHome.tsx, NephilimOnboarding.tsx, CharacterCardV2Showcase.tsx, Dashboard.tsx
components/                    # UI components (Header, MessageBubble, CharacterCard, SessionList, etc.)
components/nephilim/           # NEPHILIM progression components (SeekerRankBadge, LoreCodex, etc.)
context/                       # PersonaContext.tsx, AudioContext.tsx
services/                      # API client (includes NEPHILIM progression API)
utils/                         # animations.ts, helpers, personaFilter.ts
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

## Environment Variables

Required in `.env`:
```bash
OLLAMA_BASE=http://127.0.0.1:11434
PERSONA_MODEL=nchapman/gemma-2-9b-it-abliterated:9b
PERSONA_TEMPERATURE=0.9
COORD_PORT=8000
PERSONA_DIR=personas
```

Optional (see `.env.docker` for full list):
- `BRAVE_API_KEY`, `BRAVE_ENABLED_RARITIES` - Web search (fallback; per-persona `mcp_access` takes priority)
- `MONGODB_URI`, `MONGODB_ENABLED_RARITIES` - Trading data (fallback; per-persona `mcp_access` takes priority)
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

### Chat Flow
1. Frontend POST `/greet` creates session
2. User message → POST `/chat` with session_id, persona, content
3. Backend builds system prompt from persona JSON + cached CV summary
4. Ollama generates response, stored in SQLite
5. Frontend renders with Celestial Order theming

### MCP Integration Patterns
- **Ephemeral (Brave):** `docker run -i --rm` per request, dies after 2-3s
- **Long-Running (MongoDB):** Container stays alive for multiple requests
- Feature access controlled per-persona via `mcp_access` field in persona JSON (fallback: rarity-based `.env` vars)

## Important Implementation Details

### Celestial Order & Per-Persona MCP Access
MCP access is now controlled per-persona via the `mcp_access` field in persona JSONs, with legacy rarity-based env var fallback:
- **E.E.V.A.** (Archon): Brave + MongoDB (all access)
- **Aegis** (Warden): Brave only (productivity needs web, not trading)
- **Aurora** (Warden): Brave + MongoDB (Oracle gazes into data)
- **Solace** (Warden): Brave only (empathy needs resources, not trading)
- **Cipher** (Sage): Brave + MongoDB (Maven's identity is data research)
- **Nyx** (Sage): None (creativity flows from imagination)
- **Legacy personas** (Wanderer): None (pure LLM)

### SQLite Concurrency
- Thread-safe locking via `_lock` in `repositories/base_repository.py`
- Connection uses `check_same_thread=False`
- Foreign key cascade deletes for cleanup

### React Performance
- `React.memo` for expensive components (MessageBubble, CharacterCard)
- Virtualized message list with react-window
- Hardware-accelerated Framer Motion animations

## Troubleshooting

### Backend won't start
- Verify Ollama running: `ollama serve`
- Check model pulled: `ollama list`
- Confirm `.env` has required vars

### MCP issues
- Verify Docker socket mounted
- Check API keys set in `.env`
- Test container spawn: `docker run -i --rm docker.io/mcp/brave-search`

### Database issues
- Backup and delete `chats.db` to reset
- Schema auto-migrates on startup

### Docker networking
```bash
docker-compose down && docker network prune -f
docker-compose --env-file .env.docker up -d
```

## NEPHILIM Worldbuilding System

The project includes a comprehensive immersive AI companion experience with worldbuilding, progression, and gamification.

### Lore Documents (`personas/`)
- `NEPHILIM_LORE.md` - World bible with creation myth, the Fall, and realm geography
- `NEPHILIM_FACTIONS.md` - Six Houses aligned with Nephilim patrons
- `NEPHILIM_RANKS.md` - Seeker progression system (Initiate → Nephilim)

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

### Prompt Integration
`prompt_builder.py` automatically injects NEPHILIM context for personas with:
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

### Persona Filter Toggle (Phase 6)

Filter system allowing users to switch between NEPHILIM and legacy persona views:

**Components** (`react-ui/src/`):
- `components/PersonaFilterToggle.tsx` - Animated toggle with three modes: All, NEPHILIM, Legacy
- `utils/personaFilter.ts` - Filter utilities with localStorage persistence

**Features**:
- Toggle between All (✦), NEPHILIM (⬡), and Legacy (◇) personas
- Counts displayed in each filter button
- Filter preference persists across sessions via localStorage (`persona_filter_mode`)
- Animated selection indicator using Framer Motion layoutId

**Filter Logic** (`personaFilter.ts`):
```typescript
// NEPHILIM personas identified by key prefix
isNephilimPersona(key: string) => key.startsWith('nephilim_')

// Filter functions
filterPersonas(personas, mode) // Returns filtered array
getPersonaCounts(personas)     // Returns { nephilim, legacy, total }
```

**Enhanced Components**:
- `CharacterCardV2.tsx` - NEPHILIM badge display for matching personas
- `CharacterSelector.tsx` - Gradient indicator bar on NEPHILIM persona thumbnails
- `CharacterCardV2Showcase.tsx` - Integrated filter toggle in header

**Test Coverage** (`react-ui/tests/phase6-filter.spec.ts`):
- 7 Playwright tests covering filter visibility, functionality, and persistence

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
| `/onboarding` | NephilimOnboarding | New user flow |
| `/select` | CharacterCardV2Showcase | Companion selection |
| `/chat` | Chat | Chat interface |
| `/chat/:sessionId` | Chat | Chat with specific session |
| `/dashboard` | Dashboard | Seeker's Sanctum |

**Tracking:** `docs/development/PHASE7_TRANSITION_PLAN.md`

## Documentation

- `README.md` - User setup guide, features
- `docs/setup/DOCKER_QUICKSTART.md` - Docker deployment
- `docs/development/ADDING_MCP_SERVERS.md` - MCP integration guide
- `docs/development/TESTING_GUIDE.md` - Testing guide
- `personas/NEPHILIM_*.md` - Worldbuilding lore documents
