# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP Coordinator is a **local-first persona-driven chat interface** combining a FastAPI backend coordinator with a React frontend. It enables conversations with AI personas (e.g., Eeva, Frieren, Gojo) powered by Ollama LLM models, featuring a gacha-style character collection system with persistent chat history.

**Key Architecture:**
- **Backend**: FastAPI coordinator (`src/coordinator/server.py`) that bridges persona definitions with Ollama LLM
- **Frontend**: React 19 + TypeScript UI with Framer Motion animations and Tailwind CSS
- **Persistence**: SQLite database (`chats.db`) for sessions, messages, and character collections
- **Personas**: JSON-defined characters in `personas/` with lore, voice, behavior, and expertise configs
- **LLM Integration**: Local Ollama server for inference, using models like `llama3.1:latest`

## Development Commands

### Docker Deployment (Recommended)

**🐳 Docker is the recommended setup method** for local development and testing. See [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) for full guide.

**One-Command Setup (Easiest):**
```bash
# Windows PowerShell
.\setup-docker.ps1

# Windows Command Prompt
setup-docker.bat

# Linux/Mac
./setup-docker.sh
```

**Manual Setup (Alternative):**
```bash
# Start services
docker-compose --env-file .env.docker up -d

# Pull AI models
docker exec -it ai-companion-brain ollama pull nchapman/gemma-2-9b-it-abliterated:9b
docker exec -it ai-companion-brain ollama pull nomic-embed-text:latest
```

**Access:**
```bash
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

**Common Commands:**
```bash
docker-compose logs -f backend    # View backend logs
docker-compose logs -f            # View all logs
docker-compose restart backend    # Restart backend
docker-compose down               # Stop all services

# Backup database
# Windows: Copy-Item data\chats.db backups\chats.db.backup
# Linux/Mac: cp data/chats.db backups/chats.db.backup
```

**Docker Stack:**
- 3 services: ai-companion-brain (Ollama LLM), ai-companion-api (FastAPI), ai-companion-web (React/Nginx)
- SQLite database: `./data/chats.db` (persists on host)
- Persona summaries: `./personas/_summaries/` (persists on host)
- Ollama models: Docker volume (9GB for gemma-2-9b)

**Documentation:**
- **[DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)** - Complete setup guide
- **[SQLITE_ARCHITECTURE.md](SQLITE_ARCHITECTURE.md)** - Technical decision record
- **[.env.docker](.env.docker)** - Configuration template

---

### Local Development Setup

For code modification and development (alternative to Docker):

**Setup:**
```bash
# Automated setup (installs Python + React dependencies)
./setup.sh          # Linux/macOS
setup.bat           # Windows

# Manual setup
pip install -r requirements.txt
cd react-ui && npm install
```

**Running the Application:**
```bash
# Unified startup (recommended) - starts both backend + frontend
python run_react.py

# Backend only (FastAPI on port 8000)
uvicorn src.coordinator.server:app --reload --port 8000

# Frontend only (React dev server on port 3000)
cd react-ui && npm run start:dev

# Production build
cd react-ui && npm run build
```

### CI/CD (Automated Testing)

**New to CI/CD?** See `.github/CICD_GETTING_STARTED.md` for a beginner-friendly introduction.

The project has **automated testing** via GitHub Actions that runs on every push:
- ✅ Backend tests (10 test files, ~360 test cases)
- ✅ Frontend tests (Jest with coverage reporting)
- ✅ Production build verification
- ✅ Code quality checks (syntax, naming, TODOs)
- ✅ Security scanning (npm audit, secret detection)

**Typical run time:** ~5 minutes (5 jobs in parallel)
**View results:** GitHub → Actions tab → See workflow runs

**Technical reference:** `.github/CICD_DOCUMENTATION.md`

---

### Testing (Manual/Local)
```bash
# React tests
cd react-ui && npm test
cd react-ui && npm test -- --testNamePattern="MessageBubble" --watchAll=false

# Python tests (standalone scripts in tests/ directory)
# Backend: test_server.py, test_mcp_client.py, test_tool_calling.py, test_citation_validation.py
# Backend: test_synthesis_prompt.py, test_summarization.py, test_persona_schema.py, test_repositories.py
# Integration: test_brave_mcp_connectivity.py, test_intent_classification.py, test_synthesis_integration.py
# Integration: test_phase2_integration.py, test_memory_phase1.py, test_memory_phase2.py
# MongoDB: test_mongodb_integration.py, test_mongodb_persona_flavor.py, test_mongodb_eeva_flavor.py
```

### Ollama Setup
```bash
# Start Ollama service
ollama serve

# Pull required model (from your .env PERSONA_MODEL)
ollama pull nchapman/gemma-2-9b-it-abliterated:9b

# For Phase 3 RAG memory (if needed)
ollama pull nomic-embed-text:latest
```

## Project Structure

### Backend (`src/coordinator/`)

**Core Modules:**
- `server.py` - FastAPI app entry point, CORS middleware, router assembly (~85 lines)
- `startup.py` - Application initialization, dependency injection, database setup
- `schemas.py` - Pydantic request/response models for API endpoints
- `config.py` - Pydantic Settings for centralized, validated configuration (Ollama, Brave, MongoDB)

**Route Handlers (`routes/`):**
- `chat.py` - Chat endpoints (`/persona/chat`, `/sessions/{id}/chat`, `/persona/greet`)
- `sessions.py` - Session CRUD (`/sessions`, `/sessions/{id}`, import/export)
- `personas.py` - Persona endpoints (`/personas`, `/persona/summary`)

**Services (`services/`):**
- `citation_service.py` - Web search citation validation
- `first_person_service.py` - First-person voice enforcement for persona responses
- `mongodb_handlers.py` - MongoDB tool handlers with caching (Bitcoin price, trading data)

**Business Logic:**
- `persona_memory.py` - Persona card loading, CV summary generation, prompt building
- `memory_manager.py` - MemoryManager for importance scoring, ConversationSummarizer
- `llm_client.py` - LangChain Ollama client wrapper with advanced sampling support
- `tool_definitions.py` - Tool/function definitions for LLM function calling

**Infrastructure:**
- `ollama_utils.py` - Ollama health checks, model availability assertions
- `mcp_client_stdio.py` - Ephemeral STDIO MCP client for Brave Search (official pattern)
- `mcp_client_exec.py` - Legacy exec-based MCP client (deprecated, use STDIO)
- `mcp_client_http.py` - Legacy HTTP-based MCP client (deprecated, use STDIO)
- `mongodb_mcp_client.py` - MongoDB MCP client for database operations (to be migrated to STDIO)
- `cache.py` - MongoDB caching layer with TTL support

**Data Models (`models/`):**
- `persona_schema.py` - PersonaCard, VoiceProfile, EmotionalProfile, PsychologicalProfile
- `sampling_presets.py` - SamplingConfig and preset library (creative, balanced, precise, etc.)

**Database Layer (`repositories/`):**
- `session_repository.py` - Chat session CRUD operations
- `message_repository.py` - Message persistence and retrieval
- `summary_repository.py` - Conversation summary management
- `emotional_state_repository.py` - Emotional state tracking (Phase 2.2)

### Shared (`src/shared/`)
- `persona_assets.py` - Shared utilities for persona asset paths and loading

### Frontend (`react-ui/src/`)
- `pages/` - Top-level routes: `Home.tsx`, `Chat.tsx`, `CharacterCardV2Showcase.tsx`
- `components/` - Reusable UI: `Header.tsx`, `CharacterCard.tsx`, `CharacterCardV2.tsx`, `SessionList.tsx`, `MessageBubble.tsx`, `PullInterface.tsx`, `CharacterCollection.tsx`, etc.
- `services/` - API client for backend communication
- `context/` - React contexts (e.g., PersonaContext for global state)
- `utils/` - Utility functions

### Personas (`personas/`)
Each persona is a JSON file defining:
- `key`, `display_name`, `rarity` (common/rare/epic/legendary)
- `lore` (background story array), `voice` (greeting, signoff, tics)
- `do`/`dont` lists, `behavior` traits, `emotional_profile`
- `expertise` (strong/familiar/avoid topics)
- `image`, `avatar`, `logo`, `bg` paths for UI assets
- **Phase 1 additions:**
  - `model_preferences` - Per-persona sampling config (temperature, preset)
  - `psychological_profile` - Deep characterization (core_wound, coping_mechanism, defense_style, growth_edge, contradiction_pairs)
  - `example_dialogues` - User/response pairs to teach LLM correct persona voice (max 20)

**Summary caching**: `personas/_summaries/` contains auto-generated CV-style persona summaries used in system prompts.

**Schema validation**: All persona JSON files are validated against Pydantic schema on load (`src/coordinator/models/persona_schema.py`).

### Database Schema (`chats.db`)
- `chat_sessions`: session_id, persona_key, title, created_at, updated_at
- `messages`: id, session_id, role (user/assistant), content, timestamp, latency_ms
- `conversation_summaries`: id, session_id, message_range, summary_text, emotional_developments, topics_discussed, created_at

### Test Organization (`tests/`)
- `backend/coordinator/` - Backend unit tests (server, MCP clients, tool calling, citation validation, synthesis prompts)
- `integration/` - End-to-end integration tests (Brave MCP, intent classification, long conversations)
- `exploration/` - Exploratory tests for new features and capabilities

## Key Workflows

### Adding a New Persona
1. Copy `personas/template.jsonc` to `personas/[name].json`
2. Fill in persona details (key, display_name, rarity, lore, voice, behavior, expertise)
3. Create image folder `react-ui/public/images/personas/[name]/` with:
   - `card.png` - Main character card image
   - `avatar.png` - Chat avatar
   - `logo.png` - Header/bio logo
   - `bg.png` or `bg.jpg` - Optional chat background
4. Set paths in JSON: `"image": "images/personas/[name]/card.png"`, etc.
5. Persona auto-discovered on next backend/frontend load - no restart needed
6. Summary auto-generated on first access via `persona_memory.py`

### Removing a Persona
1. Delete JSON file from `personas/`
2. Orphaned sessions and messages are automatically cleaned up by backend
3. Collections are synchronized on next app load

### Chat Flow
1. User selects persona via gacha pull or character browser
2. Frontend POST `/greet` to create new session (or load existing via `/sessions`)
3. User sends message → POST `/chat` with session_id, persona, content
4. Backend builds system prompt from persona JSON + CV summary
5. Ollama LLM generates response, stored in SQLite with latency tracking
6. Frontend renders with rarity-based theming, JSON/code highlighting, copy buttons

### Gacha System
- Multi-pull (1x/5x/10x) with particle effects and audio
- Persistent collection in localStorage + backend sync
- Pull history tracking with statistics
- Rarity-based visual effects (legendary=gold, epic=purple, rare=blue, common=grey)

## Environment Variables

Required in `.env` at project root (no .env.example exists - create from scratch):
```bash
OLLAMA_BASE=http://127.0.0.1:11434                     # Ollama API endpoint
PERSONA_MODEL=nchapman/gemma-2-9b-it-abliterated:9b   # LLM model (uncensored, great for personas)
PERSONA_TEMPERATURE=0.9                                # LLM sampling temperature (balanced creativity)
COORD_PORT=8000                                        # Backend port
COORD_URL=http://127.0.0.1:8000                        # Backend URL for frontend
PERSONA_DIR=personas                                   # Persona JSON directory
```

Optional - Basic:
- `REACT_PORT=3000` - React dev server port (default: 3000)
- `DEFAULT_PERSONA` - Preselect persona on load
- `APP_LOGO_PATH`, `USER_AVATAR` - UI branding paths
- `COORDINATOR_DB_PATH` - Custom SQLite path (default: `chats.db`)

Optional - Memory & RAG (Phase 3):
- `MEMORY_EMBEDDING_MODEL=nomic-embed-text:latest` - Ollama embedding model for semantic search
- `MEMORY_SUMMARIZATION_INTERVAL=30` - Messages before triggering auto-summarization
- `MEMORY_FACT_EXTRACTION_INTERVAL=10` - Messages before fact extraction for user profiles

Optional - LLM Temperature Overrides:
- `OLLAMA_TEMP_REWRITE=0.2` - Temperature for first-person voice rewrites
- `OLLAMA_TEMP_SUMMARIZATION=0.3` - Temperature for conversation summarization
- `OLLAMA_TEMP_FACT_EXTRACTION=0.3` - Temperature for fact extraction

Optional - Brave MCP (Ephemeral STDIO Pattern):
- `BRAVE_API_KEY` - Brave Search API key (required for web search)
- `BRAVE_MCP_IMAGE=docker.io/mcp/brave-search` - Docker image for Brave MCP server
- `BRAVE_MAX_RESULTS=5` - Maximum search results to return
- `BRAVE_ENABLED_RARITIES=rare,epic,legendary` - Persona rarities with search access
- `BRAVE_SEARCH_TIMEOUT=30` - Container spawn timeout in seconds
- `BRAVE_SAFESEARCH=moderate` - Safe search filter (off/moderate/strict)

Optional - MongoDB (Phase 3):
- `MONGODB_URI` - MongoDB connection URI
- `MONGODB_ENABLED=false` - Enable MongoDB integration
- `MONGODB_ENABLED_RARITIES=epic,legendary` - Rarities with MongoDB access
- `MONGODB_CACHE_CURRENT_PRICE=60` - Cache TTL for current price (seconds)
- `MONGODB_CACHE_TECHNICAL=60` - Cache TTL for technical analysis (seconds)
- `MONGODB_CACHE_HISTORICAL=3600` - Cache TTL for historical data (seconds)
- `MONGODB_CACHE_TRADING=300` - Cache TTL for trading stats (seconds)

## Code Style

### Python
- PEP 8, 4-space indent, type hints (`from __future__ import annotations`)
- `snake_case` for functions/modules, `PascalCase` for classes
- Relative imports from parent dirs
- Error handling via `HTTPException` in FastAPI
- Async/await preferred where applicable

### React/TypeScript
- `PascalCase` for components, explicit types, strict mode enabled
- Hooks: `useThing` naming convention, functional components only
- No semicolons, 2-space indent (enforced by ESLint)
- Imports: stdlib → third-party → local
- CSS: Tailwind for utilities, CSS modules for component-specific styles
- Layout: `h-screen flex flex-col` with Header and `flex-1 overflow-hidden` content

### Testing
- React: Jest + React Testing Library, `*.test.tsx` colocated with components
- Mock API calls, test user interactions
- Use `--watchAll=false` for CI
- Python: Limited test coverage currently, mock Ollama for critical paths

### UX & Design Guidelines

**Status:** UX Improvement Initiative (Dec 26-28, 2025) | Phase 1.1 Complete ✅
**Full Spec:** `UX_IMPROVEMENT_PLAN.md` (200+ pages)
**Implementation:** `AI_documentation/01_implementation_history/TYPOGRAPHY_SYSTEM_IMPLEMENTATION.md`

#### Design System

**Typography (✅ Implemented Dec 28, 2025):**
- **Display/Headings:** Orbitron (700, 900 weights) - Use `font-display` class or CSS var `--font-display`
- **Body Text:** Poppins (400, 600, 700 weights) - Use `font-body` class or CSS var `--font-body`
- **Monospace/Technical:** Space Mono (400, 700 weights) - Use `font-mono` class or CSS var `--font-mono`
- **Type Scale:** 0.75rem to 3rem (CSS vars: `--text-xs` through `--text-5xl`)
- **Implementation:** Fonts loaded via Google Fonts CDN in `react-ui/public/index.html`
- **Usage:** Tailwind classes (`font-display`, `font-body`, `font-mono`) or CSS variables

**Colors:** Deep space aesthetic (#0a0e27 base) with nebula accents and rarity overlays (legendary=#FFD700, epic=#DA70D6, rare=#00BFFF, common=#C0C0C0)
**Animations:** `react-ui/src/utils/animations.ts` - ANIMATION_DURATIONS (0.1-1.2s) and SPRING_CONFIGS (snappy/smooth/bouncy)
**Spacing:** 0.25-3rem scale (--space-1 to --space-12)

#### Accessibility (WCAG AA)

- 4.5:1 contrast for body text, 3:1 for large text (18px+)
- Keyboard nav: Tab/Shift+Tab, Enter/Space, Esc
- Screen reader: `aria-label`, `.sr-only` class, `role="status" aria-live="polite"`
- Focus indicators: 3px solid outline with 2px offset

#### Component Patterns

**Button Hierarchy:** Primary (gradient, xl), Secondary (outlined, base), Tertiary (text link)
**Animation:** Use `SPRING_CONFIGS` from utils/animations.ts, respect `prefers-reduced-motion`
**Performance:** Memoize with `React.memo`, reduce concurrent animations, use `will-change` only when animating
**Search:** Session search in SessionList.tsx, message search with highlight in Chat.tsx

#### Implementation Checklist

**Before Frontend Changes:**
- Check `UX_IMPROVEMENT_PLAN.md`
- Use design system values (CSS vars, animation constants)
- Test keyboard nav (Tab, Enter, Esc)
- Verify 4.5:1 contrast, add `aria-label` where needed

**Violations to Avoid:**
- ❌ System fonts (MUST use Orbitron for headings, Poppins for body, Space Mono for mono)
- ❌ `<div>` for clickable elements (MUST use `<button>` or semantic HTML)
- ❌ Low contrast ratios (<4.5:1 for body text, <3:1 for large text)
- ❌ Animations without `will-change` management or `prefers-reduced-motion` support

**Typography Usage Examples:**
```tsx
// Headings - use font-display
<h1 className="font-display font-black text-4xl">Title</h1>

// Body text - use font-body (default, can omit)
<p className="font-body text-base">Body text</p>

// Technical/stats - use font-mono
<span className="font-mono text-xs">{latency}ms</span>

// CSS modules - use CSS variables
.character-name {
  font-family: var(--font-display);
  font-weight: 900;
}
```

## Important Implementation Details

### MCP (Model Context Protocol) Integration
**Status:** ✅ Two Proven Patterns (Dec 2025)

MCP servers run as **Docker containers** using STDIO transport. We support two patterns based on MCP server behavior.

**Architecture Overview:**
```
Backend Container (mounts /var/run/docker.sock)
    │
    ├─> spawns: docker run -i --rm docker.io/mcp/brave-search
    │   (ephemeral: lives 2-3 seconds, processes request via STDIN/STDOUT, dies)
    │
    ├─> spawns: docker run -i --rm docker.io/mcp/mongodb
    │   (long-running: stays alive for multiple requests)
    │
    └─> spawns: docker run -i --rm docker.io/mcp/[any-mcp-server]
        (universal pattern for all MCP servers)
```

**Two Patterns:**

1. **Ephemeral STDIO (Brave Search):**
   - Spawns `docker run -i --rm` per request
   - Container lives 2-3 seconds
   - Dies automatically after response
   - Perfect for stateless operations

2. **Long-Running STDIO (MongoDB):**
   - Spawns container once
   - Stays alive for multiple requests
   - Must be manually terminated when done
   - Better for stateful operations

**Key Characteristics:**
- **STDIO Transport**: Communication via stdin/stdout pipes using JSON-RPC 2.0 protocol
- **Container Isolation**: Each MCP server is a separate Docker image with complete isolation
- **Scalable**: Universal pattern works for ANY MCP server (Brave, MongoDB, Neo4j, Google Calendar, etc.)
- **Container Orchestration**: Backend mounts Docker socket to spawn containers on-demand

**Implementation:**
- `mcp_client_stdio.py` - Ephemeral STDIO client for Brave Search (reference implementation)
- `mongodb/` - Long-running STDIO client for MongoDB (reference implementation)
- `tool_definitions.py` - Tool/function definitions for LLM function calling
- `startup.py` - MCP client initialization and dependency injection

**Docker Socket Mounting:**
Backend container requires Docker socket access to spawn MCP containers:
```yaml
backend:
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock  # Enables container orchestration
```
This is the standard pattern for container orchestration (used by CI/CD runners like GitHub Actions).

**Adding New MCP Servers:**
See **[docs/ADDING_MCP_SERVERS.md](docs/ADDING_MCP_SERVERS.md)** for comprehensive guide on:
- Choosing the right pattern (ephemeral vs long-running)
- Step-by-step implementation instructions
- Testing and troubleshooting
- Rarity-based feature gating
- Best practices and examples

### Rarity-Based Feature Gating

**MCP access is controlled by persona rarity**, not per-persona configuration. This provides clear feature tiers while keeping configuration simple.

**Feature Matrix:**

| Rarity | MCP Access | Features |
|--------|------------|----------|
| **Common** | None | Pure LLM responses only |
| **Rare** | Brave Search | Web search with mandatory citations |
| **Epic** | Brave Search + MongoDB | Web search + Bitcoin trading data access |
| **Legendary** | Brave Search + MongoDB | All MCP features (future: GraphRAG, etc.) |

**Configuration (.env):**
```bash
BRAVE_ENABLED_RARITIES=rare,epic,legendary   # Rarities with Brave Search access
MONGODB_ENABLED_RARITIES=epic,legendary      # Rarities with MongoDB access
```

**How it Works:**
1. Backend reads persona `rarity` from JSON (e.g., `"rarity": "epic"`)
2. Intent classifier checks rarity against `.env` config (`intent_classifier.py:55-56`)
3. Tools are dynamically injected based on rarity tier
4. Frontend shows rarity-based UI badges and styling

**Temperature Override:**
Personas can override the global temperature via `model_preferences`:
```json
{
  "model_preferences": {
    "temperature": 0.7
  }
}
```
Fallback to global `.env` setting: `PERSONA_TEMPERATURE=0.9`

**Why Not Per-Persona MCP Control?**
- Simplifies configuration (one place: `.env`)
- Aligns with gacha tier system (rarity = feature tier)
- Environment-driven (easy to change for dev/prod)
- Reduces JSON bloat and validation overhead

**Changing Rarity:**
Update `rarity` in persona JSON:
- Frontend updates instantly (card styling, UI badges)
- Backend respects new rarity on next request
- MCP access automatically adjusts based on new tier

### Brave MCP Integration (Web Search)
**Status:** ✅ Fully implemented with ephemeral STDIO pattern (Dec 2025)

Rare+ personas perform autonomous web searches with mandatory citations using ephemeral Docker containers.

**Architecture:**
- **Transport**: STDIO with ephemeral containers (`docker run -i --rm docker.io/mcp/brave-search`)
- **Client**: `mcp_client_stdio.py` - BraveMCPClientStdio class
- **Container Lifecycle**: Spawned on-demand, processes request via stdin/stdout, dies after response
- **Typical Duration**: 2-3 seconds per search request

**Key Features:**
- Autonomous search/answer decision-making with 85-90% UI prediction accuracy
- Mandatory citation format: `🔍 Sources:\n• [Title - Source](url)`
- Backend validation, rarity-based access (Rare/Epic/Legendary only)
- Stateless architecture with no long-running MCP service

**Config:**
- `BRAVE_API_KEY` - Brave Search API key (required)
- `BRAVE_MCP_IMAGE=docker.io/mcp/brave-search` - Docker image for MCP server
- `BRAVE_MAX_RESULTS=5` - Maximum search results
- `BRAVE_ENABLED_RARITIES=rare,epic,legendary` - Rarities with search access (see Rarity-Based Feature Gating)
- `BRAVE_SEARCH_TIMEOUT=30` - Container timeout in seconds

**Flow:** User query → Frontend predicts → Backend classifies → Spawns ephemeral container → LLM searches → Synthesizes with citations → Container dies → Validates → Renders

**Synthesis Rules (Anti-Hallucination):**
1. USE ONLY SEARCH RESULTS (no training data)
2. SYNTHESIZE NATURALLY (coherent narrative)
3. STAY IN CHARACTER (persona voice)
4. BE ACCURATE (exact numbers/dates)
5. MANDATORY CITATIONS (🔍 emoji + markdown links)

**Impl:** `mcp_client_stdio.py:55-314`, `llm_client.py:173-187` | **Tests:** `test_synthesis_*.py`, frontend citation tests

### MongoDB MCP Integration (Trading Data)
**Status:** ✅ Fully implemented (Dec 2025)

Epic/Legendary personas query Bitcoin data from MongoDB Atlas with 4 tools: `bitcoin_current_price` (RSI, MACD, Bollinger Bands, EMAs), `bitcoin_historical_prices` (OHLCV 2016-present), `bitcoin_trading_summary` (DCA stats), `bitcoin_technical_analysis` (multi-timeframe signals).

**Config:**
- `MONGODB_URI` - MongoDB Atlas connection string
- `MONGODB_TIMEOUT=30` - Operation timeout
- `MONGODB_ENABLED_RARITIES=epic,legendary` - Rarities with MongoDB access (see Rarity-Based Feature Gating)
**Caching:** 60s (current), 3600s (historical), per-tool TTL

**Flow:** User query → Backend classifies (`mongodb` intent) → Tools injected → MCP container query → LLM synthesizes → Frontend renders with 🗄️ badge

**Synthesis Rules (Persona Flavor):**
1. USE ONLY DB DATA (no estimates)
2. SYNTHESIZE NATURALLY (narrative not JSON)
3. STAY IN CHARACTER (persona voice)
4. BE ACCURATE (exact numbers: $87,855.80 not "~$88K")
5. ADD INTERPRETATION (explain indicators)

**Impl:** `query_handler_service.py` | **Tests:** `test_mongodb_*.py`

### Persona System Prompt Construction
- Prompt built from persona JSON fields: lore, voice, do/dont, behavior, expertise
- CV summary auto-generated and cached in `personas/_summaries/` for token efficiency
- File locking ensures serialized summary builds across processes
- Token truncation applied if lore exceeds limits
- **Phase 1**: Psychological profile integrated into system prompt for realistic behavior

### Persona Quality Enhancement (Phase 1 & 2)
**Status:** ✅ Phase 1 & 2 Complete (Dec 2025)

Type-safe persona system with advanced characterization and emotional tracking.

**Phase 1 Features:**
- **Pydantic Schema Validation**: All persona JSON validated on load with clear error messages
- **Centralized Configuration**: `config.py` uses `pydantic-settings` for validated env vars
- **Advanced Sampling**: Per-persona LLM sampling (temperature, top_k, top_p, repeat_penalty)
- **Sampling Presets**: Named presets (creative, balanced, precise, chaotic, deterministic)
- **Psychological Profiles**: Deep characterization with core_wound, coping_mechanism, defense_style, contradiction_pairs
- **Example Dialogues**: User/response pairs to teach correct persona voice

**Phase 2 Features:**
- **Emotional State Tracking**: Per-session trust_level, rapport, current_mood tracking
- **Dynamic Context Injection**: Emotional state injected into system prompts
- **Heuristic Emotion Detection**: Automatic mood updates from user sentiment signals
- **All Personas Enhanced**: 6/6 personas have psychological profiles + 50 total example dialogues
- **UI Integration**: Emotional state resets when clearing messages, deletes with session

**Emotional State Lifecycle:**
| UI Action | Emotional State |
|-----------|-----------------|
| Delete session | Deleted (DB cascade) |
| Clear messages | Reset to defaults |
| New message | Updated dynamically |

**Emotional State API:** `GET /sessions/{id}/emotional-state`, `POST /sessions/{id}/chat` (returns state), `DELETE /sessions/{id}/messages` (resets to defaults)

**Sampling Presets:** creative (1.2), balanced (0.9), precise (0.5), chaotic (1.5), deterministic (0.1)

**Testing:** `test_persona_schema.py` (16), `test_phase2_integration.py` (6), frontend `phase2PersonaQuality` tests (14)

### Memory Management (Phase 1, 2 & 3)
**Status:** ✅ All phases complete & production-ready (Dec 23, 2025)

Advanced AI memory with importance scoring, auto-summarization, semantic search (FAISS), and cross-session user profiles.

**Phase 1 (Infrastructure):** DB context loading, token budget monitoring, 4096 token limit enforcement
**Phase 2 (Intelligence):** Importance scoring (6x names/holdings, 4x personal info, 1.3x questions), auto-summarization every 30 messages, first 3 + last 10 messages always included
**Phase 3 (Advanced - PRODUCTION):** RAG semantic search (FAISS), cross-session profiles, automated fact extraction (every 10 messages), personas remember users by name

**Key Components:**
- `memory_manager.py` - Scoring, selection, summarization
- `memory_rag.py` - FAISS semantic search (Phase 3)
- `user_profile.py` - Cross-session memory (Phase 3)
- `fact_extractor.py` - LLM fact extraction (Phase 3)

**DB Schema (Phase 3):** `user_profiles` (user_id, profile_data JSON), `user_sessions` (links users to sessions)

**Dependencies:** `faiss-cpu`, `langchain-community`, `nomic-embed-text:latest` (Ollama embedding model)

**Usage:** Automatic - profiles created at 10 messages, personas remember users across sessions
**Tests:** `test_memory_phase*.py`, `test_phase3_*.py`

**Critical Bug Fix (Dec 23):** `routes/chat.py:590` - Remove `fact_extractor and` from conditional (enables Phase 3)

### SQLite Concurrency
- Thread-safe locking via `_lock` in `repositories/base_repository.py`
- Connection uses `check_same_thread=False`
- Foreign key cascade deletes for session cleanup

### React Performance
- `React.memo` for expensive components (MessageBubble, CharacterCard)
- Hardware-accelerated animations with Framer Motion
- Particle effects optimized for 60fps
- Reduced motion support for accessibility

### Mobile Optimization
- ChatGPT-style responsive layout: sidebar pushes content on desktop, overlays on mobile
- Touch gestures, swipe navigation
- Mobile-optimized input with proper keyboard handling
- Hamburger menu with slide-out navigation

### Security Considerations
- All LLM processing happens locally via Ollama (no external API calls)
- Validated user input via Pydantic models
- Never commit secrets (use `.env`)
- Known: 2 moderate npm vulnerabilities in dev dependencies (react-scripts 5.0.1 nested deps), fixed high-severity issues via package overrides

## Common Troubleshooting

### Backend won't start
- Verify Ollama is running: `ollama serve`
- Check model is pulled: `ollama list` / `ollama pull nchapman/gemma-2-9b-it-abliterated:9b`
- Confirm `.env` has required vars: `OLLAMA_BASE`, `PERSONA_MODEL`
- Verify model matches .env: Default uses `nchapman/gemma-2-9b-it-abliterated:9b` @ temp `0.9`

### Frontend build errors
- Clear node_modules: `cd react-ui && rm -rf node_modules && npm install`
- Check Node.js version: `node --version` (requires v16+)
- TypeScript errors: Run `npm run build` to see full compilation output

### Database issues
- Backup and delete `chats.db` to reset
- Schema auto-migrates on startup from old format if detected

### Persona not appearing
- Ensure JSON is valid (use `template.jsonc` as reference)
- Check `personas/` directory path matches `PERSONA_DIR` env var
- Look for errors in backend logs during persona discovery

### Phase 3 Memory Issues

**Profiles not created:** Verify 10+ messages sent, check `SELECT COUNT(*) FROM user_profiles;`, look for `[Phase3]` logs, ensure bug fix applied
**Cross-session memory failing:** Profiles must exist first, check `user_sessions` table links, verify name extraction
**RAG no results:** Expected (threshold 0.5), Phase 2 importance scoring handles most recall, tune `memory_rag.py` if needed
**FAISS errors:** Pull `nomic-embed-text:latest`, install `faiss-cpu langchain-community`, deprecation warnings are non-blocking

### MCP (Ephemeral Container) Issues

**Container spawn fails:**
- Verify Docker socket mounted: `docker exec ai-companion-api ls -l /var/run/docker.sock`
- Check Docker accessible from backend: `docker exec ai-companion-api docker version`
- Ensure MCP image exists: `docker pull docker.io/mcp/brave-search`
- Check API key set: `docker exec ai-companion-api env | grep BRAVE_API_KEY`

**Search returns no results:**
- Verify Brave API key is valid (test at api.search.brave.com)
- Check container logs: `docker logs ai-companion-api | grep -i brave`
- Test direct spawn: `echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"brave_web_search","arguments":{"query":"test","count":1}}}' | docker run -i --rm -e BRAVE_API_KEY=xxx docker.io/mcp/brave-search`

**Timeout errors:**
- Increase `BRAVE_SEARCH_TIMEOUT` (default: 30s)
- Check network connectivity from backend container
- Verify Docker daemon responding: `docker ps`

**Permission denied on Docker socket:**
- Ensure socket permissions: `ls -l /var/run/docker.sock` (should be srw-rw----)
- Backend user must have Docker group access
- On Windows: Verify Docker Desktop "Expose daemon on tcp://localhost:2375" is disabled (use socket instead)

## Additional Documentation

**Active Documentation (Root Directory):**
- `README.md` - User-facing setup guide, features, architecture diagram
- `NEXT_STEPS.md` - Current project status, decision points, roadmap
- `ASSESSMENT.md` - Comprehensive codebase quality assessment and scoring (Dec 2025)
- `AGENTS.md` - AI coding guidelines, tech stack, build commands, code style
- `CHANGELOG.md` - Version history, feature additions, security fixes
- `PRODUCTION_READINESS_PLAN.md` - Kubernetes production readiness assessment & 3-phase migration plan (Dec 2025)
- `DOCKER_QUICKSTART.md` - Docker deployment guide (recommended setup method)
- `DOCKER_README_UPDATE_SUMMARY.md` - Docker implementation log
- `DOCKER_SQLITE_OPTIMIZATION_SUMMARY.md` - SQLite technical decision
- `SQLITE_ARCHITECTURE.md` - Database architecture technical decision record
- `UI_MULTI_MESSAGE_TEST_GUIDE.md` - Frontend testing guide

**CI/CD Documentation (.github/):**
- `CICD_GETTING_STARTED.md` - Beginner-friendly CI/CD introduction (what, why, how)
- `CICD_DOCUMENTATION.md` - Technical reference for CI/CD pipeline configuration

**Historical Documentation (Archive):**
- `AI_documentation/` - Historical specs, completion summaries, feature details
  - `01_implementation_history/` - Phase completions, refactoring summaries, bug fixes
  - `02_ux_design_specs/` - UX design roadmaps
  - `03_feature_specs/` - Brave/MongoDB MCP specs, model recommendations
  - `04_deprecated/` - Obsolete docs (React migration complete)
  - `05_roadmaps/` - Persona quality, memory management roadmaps

## Dependencies

**Python:**
- fastapi, uvicorn - Web framework and server
- langchain-core, langchain-ollama - LLM orchestration
- langchain-community - FAISS integration and embeddings (Phase 3)
- faiss-cpu - Vector database for semantic search (Phase 3)
- pydantic, pydantic-settings - Data validation and configuration management
- python-dotenv - Environment variable loading

**React:**
- react 19, react-dom 19, react-router-dom - Core framework
- typescript 4.9.5 - Type safety
- framer-motion - Animation library
- tailwindcss - Utility-first CSS
- @tsparticles/react - Particle effects
- lucide-react - Icon library
- react-syntax-highlighter - Code highlighting

---

## Project Hygiene

**Current Status:** ✅ Score 10/10 (Perfect - Dec 26, 2025)

**Key Metrics:**
- Zero unused imports, dead code, log files, test artifacts ✅
- Type hints: 95%+ | Technical debt: 1 TODO
- routes/chat.py: 759 → 279 lines (63% reduction via service layer extraction)
- server.py: 1,645 → 85 lines (95% reduction via modular refactoring)

**Organization:**
- `tests/`: 12 backend, 23 integration, 10 exploration
- `src/coordinator/`: 3 routes, 7 services
- `AI_documentation/`: 43+ docs (5 categories: implementation_history, ux_design_specs, feature_specs, deprecated, roadmaps)

**Root Markdown Policy:** README, CLAUDE, DOCKER_QUICKSTART, NEXT_STEPS, CHANGELOG only - all others → `AI_documentation/`

**Full History:** `AI_documentation/01_implementation_history/PROJECT_HYGIENE_LOG.md`
