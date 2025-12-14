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

### Setup
```bash
# Automated setup (installs Python + React dependencies)
./setup.sh          # Linux/macOS
setup.bat           # Windows

# Manual setup
pip install -r requirements.txt
cd react-ui && npm install
```

### Running the Application
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

### Testing
```bash
# React tests (full suite)
cd react-ui && npm test

# Single test pattern
cd react-ui && npm test -- --testNamePattern="MessageBubble" --watchAll=false

# Python backend tests
python src/coordinator/test_server.py
python src/coordinator/test_mcp_client.py
python src/coordinator/test_tool_calling.py

# Note: Python tests are standalone scripts, not pytest-based
```

### Ollama Setup
```bash
# Start Ollama service
ollama serve

# Pull required model
ollama pull llama3.1:latest
# or whatever model is specified in PERSONA_MODEL env var
```

## Project Structure

### Backend (`src/coordinator/`)
- `server.py` - FastAPI app with CORS, chat endpoints, session management, SQLite persistence
- `persona_memory.py` - Persona card loading, CV summary generation, prompt building, file locking for summary serialization
- `llm_client.py` - LangChain Ollama client wrapper
- `ollama_utils.py` - Ollama health checks, model availability assertions
- `config.py` - Environment variable helpers for Ollama base, model, temperature, persona dir
- `mcp_client.py` - MCP (Model Context Protocol) client for connecting to MCP servers
- `tool_definitions.py` - Tool/function definitions for LLM function calling
- `test_server.py`, `test_mcp_client.py`, `test_tool_calling.py` - Backend test files

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

**Summary caching**: `personas/_summaries/` contains auto-generated CV-style persona summaries used in system prompts.

### Database Schema (`chats.db`)
- `chat_sessions`: session_id, persona_key, title, created_at, updated_at
- `messages`: id, session_id, role (user/assistant), content, timestamp, latency_ms

## Key Workflows

### Adding a New Persona
1. Copy `personas/template.jsonc` to `personas/[name].json`
2. Fill in persona details (key, display_name, rarity, lore, voice, behavior, expertise)
3. Add persona images to `react-ui/public/images/` with paths like `"image": "images/[name]_card.png"`
4. Persona auto-discovered on next backend/frontend load - no restart needed
5. Summary auto-generated on first access via `persona_memory.py`

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
OLLAMA_BASE=http://127.0.0.1:11434     # Ollama API endpoint
PERSONA_MODEL=llama3.1:latest          # LLM model to use
PERSONA_TEMPERATURE=0.1                # LLM sampling temperature
COORD_PORT=8000                        # Backend port
COORD_URL=http://127.0.0.1:8000        # Backend URL for frontend
PERSONA_DIR=personas                   # Persona JSON directory
```

Optional:
- `REACT_PORT=3000` - React dev server port (default: 3000)
- `DEFAULT_PERSONA` - Preselect persona on load
- `APP_LOGO_PATH`, `USER_AVATAR` - UI branding paths
- `COORDINATOR_DB_PATH` - Custom SQLite path (default: `chats.db`)

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

## Important Implementation Details

### MCP (Model Context Protocol) Integration
- The coordinator can connect to external MCP servers (e.g., RAG, knowledge graph, Brave search, MongoDB)
- MCP client in `mcp_client.py` handles server discovery and tool invocation
- Tool definitions in `tool_definitions.py` define available functions for LLM function calling
- Architecture supports multiple MCP servers bridged through the coordinator

### Brave MCP Integration (Web Search)
**Status:** ✅ Fully implemented (MVP 2-4 complete)

Rare, Epic, and Legendary personas can perform autonomous web searches using the Brave Search API.

**Features:**
- **Autonomous Decision-Making:** Personas intelligently decide when to search vs. answer directly
- **Mandatory Citations:** All web search responses must include properly formatted source citations
- **Smart UI Indicators:** SearchIndicator shown for predicted searches, TypingIndicator for direct answers
- **Citation Validation:** Backend validates that responses include "🔍 Sources:" section with markdown links
- **Client-Side Prediction:** ~85-90% accuracy predicting when search will be used (for optimal UX)
- **Rarity-Based Access:** Common personas blocked, Rare+ have web search enabled

**Configuration:**
```bash
BRAVE_API_KEY=your_api_key_here           # Required for web search
BRAVE_MAX_RESULTS=5                        # Number of search results (default: 5)
BRAVE_SAFESEARCH=moderate                  # moderate|strict|off
BRAVE_SEARCH_TIMEOUT=10                    # Timeout in seconds
BRAVE_ENABLED_RARITIES=rare,epic,legendary # Which rarities can search
```

**Persona Configuration:**
```json
{
  "key": "Eeva",
  "rarity": "legendary",
  "allowed_mcp": ["chat", "graphrag", "brave_search"],
  ...
}
```

**Citation Format (Enforced):**
```
🔍 Sources:
• [Article Title - Source Name](https://url1.com)
• [Article Title - Source Name](https://url2.com)
• [Article Title - Source Name](https://url3.com)
```

**Usage:**
Users simply ask questions requiring current info. Personas automatically search when needed.

**Example Flow:**
1. User: "What is the current Bitcoin price?"
2. Frontend predicts search needed → shows SearchIndicator 🔍
3. Backend classifies query → injects `brave_web_search` tool
4. LLM decides to search → executes Brave API call
5. LLM synthesizes response with mandatory citations
6. Backend validates citations → returns with `citation_valid` flag
7. Frontend renders answer with citation section styled separately

**Synthesis Prompt (Anti-Hallucination):**
The system uses a dedicated synthesis prompt (`build_synthesis_prompt()` in `tool_definitions.py`) when generating answers from web search results. This prevents three critical issues:

1. **Hallucination Prevention:** Explicitly instructs LLM to "ONLY use information from web search results" and "Do NOT use training data"
   - Example: Prevents using outdated $1,850 Ethereum price from training data when search returns $3,245

2. **Natural Synthesis:** Instructs LLM to combine information from multiple sources into cohesive answer
   - Prevents raw dumps of search result titles

3. **Citation Formatting:** Enforces bullet point format with specific examples
   - Prevents inline citations `[Source](url)[Source](url)`

**Synthesis Rules (5 Core Rules):**
- **RULE 1: USE ONLY SEARCH RESULTS** - No training data, no estimates
- **RULE 2: SYNTHESIZE NATURALLY** - Combine sources, don't list
- **RULE 3: STAY IN CHARACTER** - Maintain persona voice
- **RULE 4: BE ACCURATE** - Exact numbers, dates, facts from search
- **RULE 5: MANDATORY CITATIONS** - Bullet points with emoji + markdown links

**Implementation:** `src/coordinator/llm_client.py` line 173-187 builds synthesis prompt before final response generation.

**Testing:**
```bash
# Backend synthesis prompt tests (10 unit tests)
python src/coordinator/test_synthesis_prompt.py

# Backend integration tests (3 end-to-end tests)
# Requires backend running on port 8000
python test_synthesis_integration.py

# Backend citation validation
python -c "from server import validate_citations; ..."

# Frontend SearchIndicator tests
cd react-ui && npm test -- SearchIndicator --watchAll=false

# Frontend citation rendering tests
cd react-ui && npm test -- MessageBubble.citations --watchAll=false

# Search heuristics tests
cd react-ui && npm test -- searchHeuristics --watchAll=false
```

**Logging:**
- `[Chat]` - Request received with query preview
- `[Intent]` - Query classification result
- `[Tools]` - Tools injected for this request
- `[Brave]` - Workflow status, timing, results count
- `[Citations]` - Validation results (✅/❌)
- `[Synthesis]` - Synthesis prompt usage, length, answer generation (NEW)

### Persona System Prompt Construction
- Prompt built from persona JSON fields: lore, voice, do/dont, behavior, expertise
- CV summary auto-generated and cached in `personas/_summaries/` for token efficiency
- File locking ensures serialized summary builds across processes
- Token truncation applied if lore exceeds limits

### SQLite Concurrency
- Thread-safe locking via `_DB_LOCK` in `server.py`
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
- Check model is pulled: `ollama list` / `ollama pull llama3.1:latest`
- Confirm `.env` has required vars: `OLLAMA_BASE`, `PERSONA_MODEL`

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

## Additional Documentation

**Active Documentation (Root Directory):**
- `README.md` - User-facing setup guide, features, architecture diagram
- `ASSESSMENT.md` - Comprehensive codebase quality assessment and scoring (Dec 2025)
- `AGENTS.md` - AI coding guidelines, tech stack, build commands, code style
- `CHANGELOG.md` - Version history, feature additions, security fixes

**Historical Documentation (Archive):**
- `AI_documentation/` - Historical specs, completion summaries, feature implementation details
  - `01_implementation_history/` - MVP and phase completion summaries
  - `02_ux_design_specs/` - UX design roadmaps (Home, Chat, Character pages, Gacha)
  - `03_feature_specs/` - Feature specs (Brave MCP, MongoDB MCP, model recommendations)
  - `04_deprecated/` - Obsolete docs kept for reference (React migration complete)

## Dependencies

**Python:**
- fastapi, uvicorn - Web framework and server
- langchain-core, langchain-ollama - LLM orchestration
- pydantic - Data validation
- python-dotenv - Environment variable loading

**React:**
- react 19, react-dom 19, react-router-dom - Core framework
- typescript 4.9.5 - Type safety
- framer-motion - Animation library
- tailwindcss - Utility-first CSS
- @tsparticles/react - Particle effects
- lucide-react - Icon library
- react-syntax-highlighter - Code highlighting
