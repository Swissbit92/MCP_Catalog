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
- `mcp_client.py` - MCP (Model Context Protocol) client for Brave Search
- `mongodb_mcp_client.py` - MongoDB MCP client for database operations
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
Uses `build_synthesis_prompt()` to prevent hallucinations, ensure natural synthesis, and enforce citation formatting.

**5 Core Rules:**
1. USE ONLY SEARCH RESULTS - No training data/estimates
2. SYNTHESIZE NATURALLY - Combine sources coherently
3. STAY IN CHARACTER - Maintain persona voice
4. BE ACCURATE - Exact numbers/dates from search
5. MANDATORY CITATIONS - Bullet points with 🔍 emoji + markdown links

**Implementation:** `src/coordinator/llm_client.py` line 173-187
**Tests:** `test_synthesis_prompt.py`, `test_synthesis_integration.py`, frontend tests (SearchIndicator, MessageBubble.citations, searchHeuristics)

### MongoDB MCP Integration (Trading Data)
**Status:** ✅ Fully implemented and tested (Dec 2025)

Epic and Legendary personas can query real-time Bitcoin price and trading data from MongoDB Atlas.

**Features:**
- **Real-Time Data:** Live Bitcoin prices with 35+ technical indicators (RSI, MACD, Bollinger Bands, EMAs)
- **Historical Data:** Price history from 2016-07-18 to present (daily) and last 6 months (hourly)
- **Trading Stats:** DCA purchase history, total BTC acquired, average prices
- **Smart Caching:** TTL-based cache (60s for current price, 3600s for historical)
- **Rarity-Based Access:** Only Epic and Legendary personas can query MongoDB

**Configuration:**
```bash
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/btc_data
MONGODB_TIMEOUT=30                       # Query timeout in seconds
MONGODB_MAX_RESPONSE_BYTES=100000        # Max response size
MONGODB_ENABLED_RARITIES=epic,legendary  # Which rarities can query
```

**Available Tools (4 semantic tools):**
| Tool | Description |
|------|-------------|
| `bitcoin_current_price` | Latest price with RSI, MACD, Bollinger Bands, EMAs |
| `bitcoin_historical_prices` | Historical OHLCV data with date range filtering |
| `bitcoin_trading_summary` | DCA statistics: total BTC, spend, fees, avg price |
| `bitcoin_technical_analysis` | Multi-timeframe analysis with trend/momentum signals |

**Example Query Flow:**
1. User: "What is the current Bitcoin price?"
2. Backend classifies intent → `mongodb`
3. Tools injected: `['bitcoin_current_price', ...]`
4. MongoDB queried via Docker MCP container
5. LLM synthesizes response: "Bitcoin is $87,855.80 with RSI 42.04..."
6. Frontend displays with 🗄️ MongoDB badge

**Response Metadata:**
```json
{
  "source_type": "mongodb_mcp",
  "tools_used": ["bitcoin_current_price"],
  "cache_status": "hit",
  "data_timestamp": "2025-12-23T11:00:00Z"
}
```

**Testing:**
```bash
# End-to-end test (requires backend + Docker)
python tests/exploration/test_mongodb_phase4.py

# Unit tests
python tests/backend/coordinator/test_mongodb_integration.py
```

**Logging:**
- `[Intent]` - Query classification (mongodb/brave/llm)
- `[Tools]` - Tools injected for MongoDB queries
- `Cache HIT/MISS` - Cache status with age in seconds
- `MongoDB query completed` - Tool used and cache status
- `[MongoDB Synthesis]` - Synthesis prompt usage and length

**Synthesis Prompt (Persona Flavor Enhancement):**
Uses `build_mongodb_synthesis_prompt()` to ensure responses maintain persona flavor instead of emotionless data dumps.

**5 Core Rules:**
1. USE ONLY DATABASE DATA - No training data estimates
2. SYNTHESIZE NATURALLY - Narrative not JSON dump
3. STAY IN CHARACTER - Maintain persona voice
4. BE ACCURATE - Exact numbers ($87,855.80 not "around $88K")
5. ADD INTERPRETATION - Explain indicators, connect data points

**Implementation:** `src/coordinator/services/query_handler_service.py`
**Tests:** `test_mongodb_persona_flavor.py`, `test_mongodb_eeva_flavor.py`

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
**Status:** ✅ Phase 1 & 2 Complete | ✅ Phase 3 Complete & Production-Ready (Dec 23, 2025)

Advanced AI memory system with importance scoring, automatic summarization, semantic search, and cross-session user profiles.

**Test Results:**
- Phase 1-2: 5/7 tests passing (71%)
- Phase 3: ✅ All features validated with live conversations
- Fact Extraction: ✅ Working (profiles created after 10 messages)
- Cross-Session Memory: ✅ Working (personas remember users)
- RAG Indexing: ✅ Working (FAISS vector database operational)

**Phase 1 Features (Infrastructure):**
- **Database Context Loading**: Messages loaded from SQLite instead of request body
- **Token Budget Monitoring**: Real-time tracking with color-coded warnings at >90% usage
- **Model Context Verification**: Dynamic window sizing based on model's 4096 token limit

**Phase 2 Features (Intelligence):**
- **Importance Scoring**: Messages scored by personal info, questions, length, recency
- **Critical Message Detection**: Names/holdings (6x weight) - NEVER dropped from context
- **Memory Awareness Rules**: System prompt instructs LLM to use conversation history
- **Auto-Summarization**: Triggers every 30 messages, summaries injected as context
- **Smart Selection**: First 3 + last 10 messages always included, plus high-scoring middle messages

**Phase 3 Features (Advanced AI Memory - PRODUCTION READY):**
- **RAG-Based Semantic Search**: FAISS vector database for semantic similarity over conversation history
- **Cross-Session User Profiles**: Persistent memory across sessions with different personas
- **Automated Fact Extraction**: LLM-powered extraction at every 10 messages (name, preferences, holdings, facts)
- **User Profile Context**: Personas greet returning users by name, remember past discussions/holdings
- **Real-Time Vector Indexing**: Incremental FAISS indexing after each message (CPU backend, GPU optional)
- **Intelligent Profile Building**: Accumulates knowledge, deduplicates info, JSON storage for schema evolution

**Key Components:**
- `memory_manager.py` - `MessageImportanceScorer`, `MemoryManager`, `ConversationSummarizer`
- `persona_memory.py` - `MEMORY_AWARENESS_RULES` injected into system prompts
- `summary_repository.py` - Persistent storage for conversation summaries
- `memory_rag.py` - `EpisodicMemoryRAG` for semantic search with FAISS (Phase 3)
- `user_profile.py` - `UserProfile` class for cross-session memory (Phase 3)
- `fact_extractor.py` - `FactExtractor` for LLM-powered fact extraction (Phase 3)
- `user_profile_repository.py` - Database operations for user profiles (Phase 3)

**Importance Scoring Weights:**
| Content Type | Weight |
|--------------|--------|
| Name introduction ("my name is...") | 6x |
| Personal info (holdings, goals) | 4x |
| Questions | 1.3x |
| Long messages (>200 chars) | 1.2x |
| Recency (newer messages) | 1.0-3.0x |

**Database Schema (Phase 3):**
```sql
-- User profiles for cross-session memory
CREATE TABLE user_profiles (
    user_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    profile_data TEXT NOT NULL  -- JSON: name, background, preferences, holdings, topics, facts
);

-- Links users to their chat sessions
CREATE TABLE user_sessions (
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    PRIMARY KEY(user_id, session_id)
);
```

**Dependencies (Phase 3):**
- `faiss-cpu` - Vector database for semantic search
- `langchain-community` - Integration with FAISS and embeddings
- `nomic-embed-text:latest` - Ollama embedding model for vector search

**Phase 3 Production Usage:**
Automatic workflow: User chats naturally → Profile created at 10 messages → Subsequent sessions remember user (no config needed)

**Testing:** `test_memory_phase1.py`, `test_memory_phase2.py`, `test_phase3_simple.py`, `test_phase3_live.py`

**Important Note (Dec 23, 2025):**
A critical bug fix was applied to enable fact extraction. If using code before this date, apply this fix to `src/coordinator/routes/chat.py` line 590:

```python
# OLD (broken):
if fact_extractor and user_profile_repo and len(db_messages) % 10 == 0:

# NEW (working):
if user_profile_repo and len(db_messages) % 10 == 0:
```

This single-line change enables all Phase 3 features.

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

**Current Status:** ✅ Hygiene Score 10/10 (Perfect cleanliness - Dec 26, 2025)

**Recent Improvements:**
- **Dec 26, 2025:** Hygiene Session #5 (6 logs deleted, 7 docs archived, 2 test artifacts removed)
- **Dec 25, 2025:** Hygiene Session #4 (8 test files moved, 9 docs archived, venv cleaned, chats.db untracked)
- **Dec 24, 2025:** Phase 1 Configuration Externalization (7 values → `.env`)
- **Dec 24, 2025:** MongoDB Persona Flavor Enhancement (synthesis prompt fix)
- **Dec 24, 2025:** Hygiene Session #3 (4 files moved, 11 archived, zero issues)
- **Dec 23, 2025:** Phase 3 Advanced Memory System (RAG, user profiles, fact extraction)
- **Dec 23, 2025:** Modular Refactoring (server.py 1,645 → 85 lines, 95% reduction)
- **Dec 23, 2025:** Hygiene Sessions #1 & #2 (major cleanup, file organization)

**Code Quality Metrics:**
- Unused imports: **0** ✅
- Dead code: **0** ✅
- Log files in repo: **0** ✅
- Test artifacts in root: **0** ✅
- Technical debt: **1 TODO** (performance optimization note)
- Type hints coverage: **95%+**
- Root Python files: **1** (run_react.py only)
- Largest backend file: **534 lines** (routes/chat.py)

**Project Organization:**
- `tests/backend/coordinator/`: 12 test files
- `tests/integration/`: 23 test files (+5 from root)
- `tests/exploration/`: 10 test files (+3 from root)
- `src/coordinator/routes/`: 3 route modules
- `src/coordinator/services/`: 3 service modules
- `AI_documentation/`: 38+ docs across 5 categories (+16 from root)

**Full History:** See `AI_documentation/01_implementation_history/PROJECT_HYGIENE_LOG.md` for complete hygiene session details, refactoring summaries, and architectural improvements.
