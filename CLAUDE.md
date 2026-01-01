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
- ✅ **RAGAS persona quality evaluation** (57 tests: metrics, golden Q&A validation, evaluator tests)
- ✅ Frontend tests (Jest with coverage reporting)
- ✅ Production build verification
- ✅ Code quality checks (syntax, naming, TODOs)
- ✅ Security scanning (npm audit, secret detection)

**Typical run time:** ~5 minutes (6 jobs in parallel)
**View results:** GitHub → Actions tab → See workflow runs

**RAGAS Evaluation:** Validates persona response quality using golden Q&A datasets (Eeva, Frieren, Gojo). Checks faithfulness, answer relevancy, context precision, and context recall metrics. Fast unit tests run in CI; slow integration tests (requiring OpenAI API) run manually.

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

# RAGAS Evaluation (Persona Quality) - 🚧 IN PROGRESS
# Quantifiable quality metrics using RAGAS framework (faithfulness, answer relevancy, context precision/recall)
# pytest tests/evaluation/test_persona_quality.py -v                    # All personas
# pytest tests/evaluation/test_persona_quality.py --persona=eeva -v     # Single persona
# pytest tests/evaluation/test_ragas_evaluator.py -v                    # Unit tests
# See: AI_documentation/01_implementation_history/RAGAS_EVALUATION_IMPLEMENTATION.md
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

**Core:** `server.py`, `startup.py`, `schemas.py`, `config.py`
**Routes:** `chat.py`, `sessions.py`, `personas.py`
**Services:** `llm_completion_service.py`, `tool_calling_service.py`, `citation_service.py`, `query_handler_service.py`, `first_person_service.py`, `message_processing_service.py`, `chat_session_service.py`, `mongodb_handlers.py`
**Business Logic:** `persona_memory.py`, `memory_manager.py`, `llm_client.py`, `tool_definitions.py`
**Infrastructure:** `ollama_utils.py`, `mcp_client_stdio.py`, `mongodb_mcp_client.py`, `cache.py`
**Models:** `persona_schema.py`, `sampling_presets.py`, `mcp_models.py`
**Repositories:** `session_repository.py`, `message_repository.py`, `summary_repository.py`, `emotional_state_repository.py`

### Shared (`src/shared/`)
- `persona_assets.py` - Shared utilities for persona asset paths and loading

### Frontend (`react-ui/src/`)
**Pages:** `Home.tsx`, `Chat.tsx`, `CharacterCardV2Showcase.tsx`
**Components:** `Header.tsx`, `CharacterCard.tsx`, `SessionList.tsx`, `MessageBubble.tsx`, `PullInterface.tsx`, etc.
**Services:** API client | **Context:** PersonaContext | **Utils:** Helper functions

### Personas (`personas/`)
JSON files with: `key`, `display_name`, `rarity`, `lore`, `voice`, `behavior`, `expertise`, `psychological_profile`, `model_preferences`, `example_dialogues`. Auto-generated summaries cached in `personas/_summaries/`. Schema: `src/coordinator/models/persona_schema.py`.

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

Optional - See `.env.docker` for complete list with defaults:
- Basic: `REACT_PORT`, `DEFAULT_PERSONA`, `APP_LOGO_PATH`, `COORDINATOR_DB_PATH`
- Memory/RAG: `MEMORY_EMBEDDING_MODEL`, `MEMORY_SUMMARIZATION_INTERVAL`, `MEMORY_FACT_EXTRACTION_INTERVAL`
- LLM Temps: `OLLAMA_TEMP_REWRITE`, `OLLAMA_TEMP_SUMMARIZATION`, `OLLAMA_TEMP_FACT_EXTRACTION`
- Brave MCP: `BRAVE_API_KEY` (required), `BRAVE_ENABLED_RARITIES`, `BRAVE_MAX_RESULTS`, `BRAVE_SEARCH_TIMEOUT`
- MongoDB: `MONGODB_URI`, `MONGODB_ENABLED_RARITIES`, cache TTLs

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

**Typography:** Outfit (display), Manrope (body), Space Mono (mono). Use `font-display`, `font-body`, `font-mono` classes.

**Background System (Option 6: Rarity-Adaptive Backgrounds):**
- **Status:** Partial implementation (Jan 1, 2026) - Background colors + interactions complete, glassmorphic polish deferred
- **Implemented:**
  - Rarity-adaptive background colors with dynamic theming
  - Home Page: Neutral slate gradient (no persona context)
  - Agent Selection & Chat: Rarity-based space backgrounds with nebula overlays
  - Clickable character cards with selection feedback and hover states
  - Continuous particle system (agent page + chat)
- **Deferred:** Full glassmorphic UI (translucent message bubbles, rarity-adaptive buttons, glass inputs)
- **CSS Classes:** `.space-background`, `.nebula-overlay`, `.glass-card` (defined but not widely applied)
- **Rarity Colors:**
  - Common (Blue): `#60a5fa` accent, `#0a0e27` space - AI trust
  - Rare (Cyan): `#06b6d4` accent, `#0a1628` space - Tech reliability
  - Epic (Purple): `#a78bfa` accent, `#1a0f2e` space - Premium magic
  - Legendary (Gold): `#fbbf24` accent, `#1f1a0a` space - Ultimate cosmic
- **Transitions:** Smooth 0.8s cubic-bezier animations between rarity switches
- **Implementation:** `react-ui/src/index.css` (40 CSS variables), `react-ui/src/App.tsx` (body class management)
- **Archive:** See `AI_documentation/01_implementation_history/OPTION6_GAP_ANALYSIS.md` for rejected Phase 1 details

**Character Card Hover Animation:**
- **Status:** Optimized (Jan 1-2, 2026) - Iteratively refined through 4 iterations based on user feedback
- **Final Implementation:** Scale-only animation (modern minimalist approach)
  - Scale: 1.0 → 1.05 (5% zoom)
  - Duration: 150ms symmetric (hover-in and hover-out)
  - Easing: Cubic-bezier [0.4, 0, 0.2, 1] (Material Design easeInOut)
  - Transform: Single property (scale only, no Y-axis movement)
- **Removed:** Rotation animation, Y-axis translation, CSS transform conflicts, floating particles
- **UX Goal:** Single smooth animation (no "two animation" perception)
- **Performance:** Single transform property = optimal GPU acceleration
- **Style:** Modern minimalist (Spotify/Netflix card aesthetic)
- **Research:** Nielsen Norman Group (150ms standard), Material Design 3, 2025 UI trends
- **Testing:** Playwright automated validation with transform matrix verification

**Animations:** See `react-ui/src/utils/animations.ts` - ANIMATION_DURATIONS, SPRING_CONFIGS
**Full Spec:** `UX_IMPROVEMENT_PLAN.md`, `AI_documentation/01_implementation_history/TYPOGRAPHY_SYSTEM_IMPLEMENTATION.md`

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
- ❌ System fonts (MUST use Outfit/Manrope/Space Mono)
- ❌ `<div>` for clickable elements (use `<button>`)
- ❌ Low contrast (<4.5:1 body, <3:1 large text)
- ❌ Animations without `prefers-reduced-motion` support

## Important Implementation Details

### MCP (Model Context Protocol) Integration
**Status:** ✅ Two Proven Patterns (Dec 2025)

MCP servers run as Docker containers via STDIO transport. Backend mounts `/var/run/docker.sock` to spawn containers on-demand.

**Patterns:**
- **Ephemeral** (Brave): `docker run -i --rm` per request, dies after 2-3s (stateless)
- **Long-Running** (MongoDB): Container stays alive for multiple requests (stateful)

**Implementation:** `mcp_client_stdio.py` (Brave), `mongodb/` (MongoDB), `tool_definitions.py`
**Guide:** See `docs/ADDING_MCP_SERVERS.md` for adding new MCP servers

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
**Status:** ✅ Implemented - Rare+ personas perform autonomous web searches with mandatory citations via ephemeral containers (2-3s lifecycle).

**Config:** `BRAVE_API_KEY` (required), `BRAVE_ENABLED_RARITIES=rare,epic,legendary`, `BRAVE_MAX_RESULTS=5`
**Rules:** Use only search results, synthesize naturally, stay in character, exact numbers, mandatory citations (🔍 Sources)
**Citation Deduplication:** Backend strips LLM citations, single clean verified block

### MongoDB MCP Integration (Trading Data)
**Status:** ✅ Implemented - Epic/Legendary personas query Bitcoin data (current price, historical, trading stats, technical analysis).

**Config:** `MONGODB_URI`, `MONGODB_ENABLED_RARITIES=epic,legendary`, `MONGODB_TIMEOUT=30`
**Caching:** 60s (current), 3600s (historical)
**Rules:** Use only DB data, exact numbers, persona voice, add interpretation

### Persona System Prompt Construction
- Prompt built from persona JSON fields: lore, voice, do/dont, behavior, expertise
- CV summary auto-generated and cached in `personas/_summaries/` for token efficiency
- File locking ensures serialized summary builds across processes
- Token truncation applied if lore exceeds limits
- **Phase 1**: Psychological profile integrated into system prompt for realistic behavior

### Persona Quality Enhancement (Phase 1 & 2)
**Status:** ✅ Complete - Pydantic validation, psychological profiles, emotional state tracking, sampling presets (creative/balanced/precise/chaotic/deterministic). API: `GET /sessions/{id}/emotional-state`.

### Memory Management (Phase 1, 2 & 3)
**Status:** ✅ Production - Importance scoring, auto-summarization (every 30 messages), FAISS semantic search, cross-session user profiles. Dependencies: `faiss-cpu`, `langchain-community`, `nomic-embed-text:latest`. See troubleshooting for issues.

### Prompt System Optimization (Dec 28, 2025)
**Status:** ✅ Deployed - Reduced tokens 3,543→2,523 (-28.8%), improved quality 74%→79%. Rollback: `prompt_builder.backup_20251228_155820.py`. See `AI_documentation/01_implementation_history/PROMPT_OPTIMIZATION_FINAL_REPORT.md`.

### Backend Core Refactoring (Phase 1 & 2)
**Status:** ✅ Complete (Dec 28, 2025) - Service layer extracted, DRY refactoring applied, architecture health improved 6.8→8.6/10. See `AI_documentation/01_implementation_history/PHASE2_COMPLETION_REPORT.md` for full details.

### SQLite Concurrency
- Thread-safe locking via `_lock` in `repositories/base_repository.py`
- Connection uses `check_same_thread=False`
- Foreign key cascade deletes for session cleanup

### React Performance
- `React.memo` for expensive components (MessageBubble, CharacterCard)
- Hardware-accelerated animations with Framer Motion
- Particle effects optimized for 60fps
- Reduced motion support for accessibility

### Typing Indicator Layout Fix (Dec 29, 2025)
**Status:** ✅ Resolved - Fixed layout collapse with typing indicators. Prevention: never add flex children with absolute/fixed positioning. See `AI_documentation/01_implementation_history/TYPING_INDICATOR_LAYOUT_FIX.md`.

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

### Docker Networking Issues

**Symptoms:**
- Error: "network f708feda4bed... not found"
- Containers fail to start with networking errors
- "Cannot start Docker Compose application" in Docker Desktop

**Cause:** Orphaned network references from improper shutdown or Docker daemon restart.

**Automated Fix (Recommended):**
```powershell
# PowerShell (full diagnostics)
.\fix-docker-network.ps1          # Quick fix (recommended)
.\fix-docker-network.ps1 -Nuclear # Full rebuild
.\fix-docker-network.ps1 -Verify  # Check status only

# Windows batch (simple fix)
.\fix-docker-network.bat
```

**Manual Fix:**
```powershell
# 1. Stop and clean
docker-compose down
docker network prune -f

# 2. Restart
docker-compose --env-file .env.docker up -d

# 3. Verify
docker-compose ps
```

**Prevention:** Always use `docker-compose down` instead of manually stopping containers in Docker Desktop.

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

**Current Status:** ✅ Score 10/10 (Perfect - Dec 29, 2025)

**Key Metrics:**
- Zero unused imports, dead code, log files, test artifacts ✅
- Type hints: 95%+ | Technical debt: 2 TODOs (both recent, not stale)
- routes/chat.py: 759 → 279 lines (63% reduction via service layer extraction)
- server.py: 1,645 → 85 lines (95% reduction via modular refactoring)

**Organization:**
- `tests/`: 12 backend, 23 integration, 10 exploration
- `src/coordinator/`: 3 routes, 7 services
- `AI_documentation/`: 74+ docs (5 categories: implementation_history, ux_design_specs, feature_specs, deprecated, roadmaps)

**Root Markdown Policy:** README, CLAUDE, DOCKER_QUICKSTART, NEXT_STEPS, CHANGELOG only - all others → `AI_documentation/`

**Full History:** `AI_documentation/01_implementation_history/PROJECT_HYGIENE_LOG.md`
