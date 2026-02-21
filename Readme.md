# NEPHILIM — AI Companion Platform

> **Local AI Companions with Personality, Memory, Live Data & Wallet Integration**
> _Private · Local-First · Docker-Ready · React 19 + FastAPI_

<div align="center">

[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker)](https://docker.com)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-19-61dafb.svg)](https://reactjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com)
[![Ollama](https://img.shields.io/badge/Ollama-Latest-orange.svg)](https://ollama.ai)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57.svg?logo=sqlite)](https://sqlite.org)

**[What Can This Do?](#-what-can-this-do) · [Docker Setup](#-quick-start-docker) · [Local Setup](#-local-development-setup) · [Architecture](#-architecture)**

</div>

---

## Table of Contents

- [What Can This Do?](#-what-can-this-do)
- [How Does It Compare?](#-how-does-it-compare)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [System Requirements](#-system-requirements)
- [Quick Start (Docker)](#-quick-start-docker)
- [Local Development Setup](#-local-development-setup)
- [Architecture](#-architecture)
- [Available AI Companions](#-available-ai-companions)
- [NEPHILIM Worldbuilding System](#-nephilim-worldbuilding-system)
- [Usage](#-usage)
- [Testing & Quality](#-testing--quality)
- [Documentation](#-documentation)
- [Contributing](#-contributing)
- [License](#-license)

---

## What Can This Do?

**5-Second Pitch:** Local AI companions with personality-driven conversations, web search, trading data, Solana wallet integration, and advanced memory — all running on your machine.

### Key Capabilities

- **10 AI Companions** (4 Legacy + 6 NEPHILIM) with psychological depth and emotional tracking
- **Natural Multi-Message Conversations** (2-4 messages per response, like texting a real person)
- **Advanced Memory System** — remembers you across sessions, extracts facts automatically
- **Web Search with Citations** — personas autonomously search Brave API with mandatory sources
- **Real-Time Trading Data** — Bitcoin prices, technical indicators (RSI, MACD), DCA stats via MongoDB
- **Jupiter Wallet Integration** — Solana DEX trading, autonomous strategies, trade proposals (Phase 8)
- **Google OAuth Authentication** — secure login with JWT access/refresh tokens
- **Summoning Ritual System** — five-phase animated card pulls with audio feedback
- **Seeker Progression** — ranks, resonance, faction affinity, unlockable lore fragments
- **100% Local & Private** — all conversations stay on your device (no data transmission)
- **One-Command Docker Setup** — Nginx reverse proxy, full NEPHILIM UI out of the box

### Who Is This For?

- **Developers** wanting a local ChatGPT alternative with customizable AI companions
- **Crypto Enthusiasts** needing a research assistant with live Bitcoin data and Solana wallet
- **Privacy-Conscious Users** who want full control over their AI conversations
- **AI Experimenters** interested in companion-driven conversational AI with advanced memory

---

## How Does It Compare?

| Feature | NEPHILIM | Open WebUI | LM Studio | Jan | LibreChat | ChatGPT |
|---------|----------|------------|-----------|-----|-----------|---------|
| **100% Local & Private** | Yes | Yes | Yes | Yes | Yes | No (Cloud) |
| **Multi-Message Conversations** | Yes (2-4 msgs) | No | No | No | No | No |
| **AI Companion System** | Yes (10 companions) | No | No | No | No | No |
| **Advanced Memory (RAG)** | Yes (FAISS + profiles) | No | No | No | No | No |
| **Emotional Tracking** | Yes (trust/rapport) | No | No | No | No | No |
| **Web Search Integration** | Yes (Brave API) | Yes (Plugins) | No | No | Yes (Plugins) | Yes (Bing) |
| **Live Trading Data** | Yes (MongoDB) | No | No | No | No | No |
| **Wallet / DEX Trading** | Yes (Jupiter/Solana) | No | No | No | No | No |
| **OAuth Authentication** | Yes (Google) | Yes | No | No | Yes | Yes |
| **Gamification / Progression** | Yes (Seeker ranks) | No | No | No | No | No |
| **One-Command Docker Setup** | Yes | Partial | Yes (GUI) | Yes (GUI) | Partial | N/A |
| **Open Source** | Yes | Yes | No | No | Yes | No |
| **Cost** | Free | Free | Free | Free | Free | $20/mo |

---

## Features

### AI & Conversational Intelligence

| Feature | Description |
|---------|-------------|
| **Dynamic AI Companions** | 10 companions with unique personality, expertise, and voice |
| **Advanced Memory System** | Importance scoring, auto-summarization, RAG semantic search, cross-session user profiles |
| **Multi-Message Conversations** | 2-4 messages per response with staggered rendering (1.2s delays) |
| **Psychological Depth** | core_wound, defense_style, growth_edge, contradiction_pairs per persona |
| **Emotional State Tracking** | trust_level, rapport, and current_mood across conversations |
| **Advanced Sampling** | Per-persona temperature, top_k, top_p, repeat_penalty with presets |

### External Integrations

| Feature | Description |
|---------|-------------|
| **Brave Web Search** | Autonomous web search with mandatory citation validation |
| **MongoDB MCP** | Real-time Bitcoin prices, technical indicators (RSI, MACD, Bollinger), DCA stats |
| **Jupiter / Solana Wallet** | DEX swap proposals, autonomous DCA/RSI strategies, AES-encrypted key storage |
| **Email Notifications** | Optional SMTP alerts for executed trades |
| **Smart Caching** | TTL-based cache (60s current price, 3600s historical) |

### Authentication & Security

| Feature | Description |
|---------|-------------|
| **Google OAuth** | Sign in with Google via `@react-oauth/google` SDK |
| **JWT Tokens** | Short-lived access tokens (1h) + HttpOnly refresh cookies (30d) |
| **Auth Middleware** | FastAPI dependency injection guards all protected routes |
| **Local Bypass** | Set `AUTH_REQUIRED=false` for dev/offline use without Google |
| **Protected Routes** | Frontend `ProtectedRoute` wrapper redirects unauthenticated users to `/login` |

### User Experience

| Feature | Description |
|---------|-------------|
| **Summoning Ritual System** | Five-phase animated card pulls with 1x/5x/10x multi-pull |
| **Seeker Progression** | Ranks (Initiate → Nephilim), resonance, faction affiliation, unlockable lore |
| **Persistent Chat History** | SQLite-backed sessions with automatic orphan cleanup |
| **Session Switching** | Sidebar navigation between persona chats |
| **Glassmorphic UI** | Dark void theme (`#0B0B0D`), `backdrop-blur-xl`, cyan/magenta accents |
| **Mobile Optimization** | Responsive layout, touch gestures, bottom tab navigation |
| **WCAG AA Compliance** | 4.5:1 contrast ratios, keyboard navigation, `aria-label` on interactive elements |

---

## Tech Stack

**Current as of February 2026**

### Frontend
- **React 19** with TypeScript 4.9.5
- **Framer Motion** for 60fps animations
- **Tailwind CSS** for utility-first styling
- **@react-oauth/google** for Google Sign-In
- **Lucide React** for icons
- **Playwright** for E2E testing

### Backend
- **FastAPI 0.100+** with Uvicorn ASGI server
- **Python 3.11+** with type hints
- **Pydantic 2.x** + `pydantic-settings` for validated configuration
- **SQLite 3** for persistent storage
- **Alembic** for database migrations
- **google-auth** + **PyJWT** for OAuth/JWT authentication
- **APScheduler** for autonomous strategy execution

### AI/ML
- **Ollama** local LLM server
- **nchapman/gemma-2-9b-it-abliterated:9b** (9GB, validated Dec 2025)
- **nomic-embed-text:latest** for embeddings
- **FAISS CPU** for vector search and semantic retrieval
- **LangChain** for LLM orchestration

### Integrations
- **Brave Search API** for web search (per-persona `mcp_access`)
- **MongoDB Atlas** for Bitcoin trading data
- **Jupiter DEX** for Solana token swaps (via Docker MCP)
- **Docker + Docker Compose** with Nginx reverse proxy

---

## System Requirements

### Docker Setup (Recommended)

| Component | Requirement | Notes |
|-----------|-------------|-------|
| **OS** | Windows 10/11, macOS 13+, or Linux | — |
| **Docker Desktop** | v24.0+ with Compose v2.0+ | [docker.com](https://docker.com) |
| **Disk Space** | 15GB free | Images + models |
| **RAM** | 8GB min, 16GB recommended | Ollama LLM inference |
| **GPU** | NVIDIA RTX (optional) | CUDA acceleration |

### Local Development

| Component | Requirement | Notes |
|-----------|-------------|-------|
| **Python** | 3.11+ | [python.org](https://python.org) |
| **Node.js** | v16+ with npm | [nodejs.org](https://nodejs.org) |
| **Ollama** | Latest | [ollama.ai](https://ollama.ai) |
| **GPU** | NVIDIA RTX 30/40 (optional) | 8GB+ VRAM recommended |

---

## Quick Start (Docker)

> Docker provides the easiest setup with all dependencies containerized, including Nginx reverse proxy for API routing and cookie-based authentication.

**Prerequisites**: [Docker Desktop](https://docker.com) installed and running.

### One-Command Setup

```bash
# 1. Clone the repository
git clone https://github.com/Swissbit92/MCP_Catalog.git
cd MCP_Catalog

# 2. Run the setup script
# Windows (PowerShell):
.\scripts\docker\setup-docker.ps1

# Linux/Mac:
chmod +x scripts/docker/setup-docker.sh
./scripts/docker/setup-docker.sh
```

The script will start all containers, download the 9GB AI model, and open your browser.

**App ready at:** `http://localhost:3000`

### Manual Setup

```bash
# 1. Start all services
docker compose --env-file .env.docker up -d

# 2. Pull LLM model (~9GB, takes 5-10 minutes)
docker exec -it ai-companion-brain ollama pull nchapman/gemma-2-9b-it-abliterated:9b

# 3. Pull embedding model (for memory features)
docker exec -it ai-companion-brain ollama pull nomic-embed-text:latest

# 4. Verify all subsystems are healthy
python scripts/docker/verify_startup.py

# 5. Open browser
start http://localhost:3000    # Windows
open http://localhost:3000     # Mac/Linux
```

### Docker Architecture

The Docker deployment runs three containers behind an Nginx reverse proxy:

```
Browser (localhost:3000)
    │
    ▼
┌──────────────────────────────────┐
│  Nginx (ai-companion-web)        │
│  - Serves React static build     │
│  - Proxies /auth/* → backend     │
│  - Proxies /chat, /sessions, etc │
│  - React Router catch-all        │
└──────────┬───────────────────────┘
           │ proxy_pass
           ▼
┌──────────────────────────────────┐
│  FastAPI (ai-companion-api)      │
│  - OAuth + JWT auth              │
│  - Chat, personas, wallet routes │
│  - Spawns ephemeral MCP containers│
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│  Ollama (ai-companion-brain)     │
│  - Local LLM inference (GPU)     │
│  - Embedding model               │
└──────────────────────────────────┘
```

### Docker Commands

```bash
# View logs
docker compose logs -f backend

# Stop all services
docker compose down

# Restart a service
docker compose restart backend

# Rebuild after code changes
docker compose --env-file .env.docker build --no-cache
docker compose --env-file .env.docker up -d
python scripts/docker/verify_startup.py    # Always verify after rebuild

# Backup database
cp data/chats.db data/chats.db.backup
```

### Docker Environment Variables

Key variables in `.env.docker`:

| Variable | Default | Description |
|----------|---------|-------------|
| `PERSONA_MODEL` | `nchapman/gemma-2-9b-it-abliterated:9b` | Ollama LLM model |
| `AUTH_REQUIRED` | `true` | Require Google OAuth login |
| `AUTH_ENV` | `development` | `development` for HTTP, `production` for HTTPS |
| `GOOGLE_CLIENT_ID` | — | Google OAuth Client ID |
| `JWT_SECRET_KEY` | (dev default) | JWT signing secret (change in production) |
| `BRAVE_API_KEY` | — | Brave Search API key (optional) |
| `MONGODB_URI` | — | MongoDB Atlas connection string (optional) |
| `MONGODB_ENABLED` | `false` | Enable MongoDB integration |
| `JUPITER_ENABLED` | `false` | Enable Jupiter wallet features |
| `SOLANA_RPC_URL` | `https://api.devnet.solana.com` | Solana RPC endpoint |
| `EMAIL_ENABLED` | `false` | Enable trade email notifications |

See [`.env.docker`](.env.docker) for the full list with documentation.

---

## Local Development Setup

> Use this if you need to modify code or prefer running services directly.

### Step 1: Install Dependencies

```bash
git clone https://github.com/Swissbit92/MCP_Catalog.git
cd MCP_Catalog

# Python backend
pip install -r requirements.txt

# React frontend
cd react-ui && npm install && cd ..
```

### Step 2: Setup Ollama

```bash
ollama serve                                               # Start service
ollama pull nchapman/gemma-2-9b-it-abliterated:9b         # Main model (9GB)
ollama pull nomic-embed-text:latest                        # Embeddings (RAG memory)
```

### Step 3: Configure Environment

Create a `.env` file in the project root:

```bash
# Required
OLLAMA_BASE=http://127.0.0.1:11434
PERSONA_MODEL=nchapman/gemma-2-9b-it-abliterated:9b
PERSONA_TEMPERATURE=0.9
COORD_PORT=8000
PERSONA_DIR=personas

# Authentication
AUTH_REQUIRED=true                    # Set false for no-login dev mode
GOOGLE_CLIENT_ID=your-client-id      # From Google Cloud Console

# Optional: Brave Search
BRAVE_API_KEY=
BRAVE_ENABLED_RARITIES=rare,epic,legendary

# Optional: MongoDB
MONGODB_URI=
MONGODB_ENABLED=false

# Optional: Jupiter Wallet
JUPITER_ENABLED=false
SOLANA_RPC_URL=https://api.devnet.solana.com

# Optional: Memory & RAG
MEMORY_EMBEDDING_MODEL=nomic-embed-text:latest
```

### Step 4: Run

```bash
# Terminal 1: Backend
python -m uvicorn src.coordinator.server:app --reload --port 8000

# Terminal 2: Frontend
cd react-ui && PORT=3001 npx react-scripts start
```

**Access at:** `http://localhost:3001`

---

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │         React 19 Frontend                │
                    │  (OAuth • Glassmorphic UI • Framer Motion)│
                    └───────────────────┬─────────────────────┘
                                        │ HTTP / CORS
                                        ▼
                    ┌─────────────────────────────────────────┐
                    │     FastAPI Coordinator (0.100+)         │
                    │  (Auth Middleware • Persona Router • LLM) │
                    └──┬──────┬──────┬──────┬──────┬──────────┘
                       │      │      │      │      │
         ┌─────────────┤      │      │      │      └──────────────┐
         ▼             ▼      ▼      ▼      ▼                    ▼
   ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  ┌──────────────┐
   │  Brave    │ │ MongoDB  │ │  SQLite  │ │  FAISS   │  │   Jupiter    │
   │  Search   │ │   MCP    │ │ Database │ │ Vectors  │  │  DEX / MCP   │
   │(web search)│ │(trading) │ │ (Chats)  │ │ (Memory) │  │(Solana swaps)│
   └───────────┘ └──────────┘ └──────────┘ └──────────┘  └──────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────────────┐
                    │   Ollama LLM (Local Inference)           │
                    │  • nchapman/gemma-2-9b (9B params)       │
                    │  • nomic-embed-text (embeddings)          │
                    └─────────────────────────────────────────┘
```

### Component Breakdown

- **React Frontend**: TypeScript, Framer Motion animations, Google OAuth, mobile-optimized
- **FastAPI Backend**: Auth middleware, persona routing, MCP orchestration, wallet routes
- **Brave Search**: Web search with citation validation (per-persona `mcp_access`)
- **MongoDB MCP**: Bitcoin trading data with technical indicators
- **Jupiter MCP**: Solana DEX swaps via Docker container, autonomous strategies (DCA, RSI)
- **SQLite**: Chat sessions, messages, summaries, user accounts, wallets, trade proposals
- **FAISS**: Vector database for semantic memory search
- **Ollama**: Local LLM server with GPU acceleration

### Authentication Flow

```
Browser                    Nginx (Docker)              FastAPI Backend
  │                            │                            │
  │  GET /login                │                            │
  │  ← LoginPage (React)      │                            │
  │                            │                            │
  │  Google Sign-In popup      │                            │
  │  ← credential (ID token)  │                            │
  │                            │                            │
  │  POST /auth/google ───────►│ proxy_pass ───────────────►│
  │                            │                            │ verify Google token
  │                            │                            │ upsert user in SQLite
  │                            │                            │ issue access_token (JWT)
  │  ◄─ { access_token, user } │ ◄──────────────────────── │ set refresh_token cookie
  │                            │                            │
  │  GET /personas (Bearer) ──►│ ─────────────────────────►│ validate JWT
  │  ◄─ persona list           │ ◄──────────────────────── │
```

### Route Map

| Route | Component | Auth Required | Description |
|-------|-----------|:---:|-------------|
| `/` | NephilimHome | No | Cinematic landing portal |
| `/login` | LoginPage | No | Google OAuth / local bypass |
| `/select` | CharacterCardV2Showcase | Yes | Companion selection & summoning |
| `/chat` | Chat | Yes | Chat interface |
| `/chat/:sessionId` | Chat | Yes | Chat with specific session |
| `/dashboard` | Dashboard | Yes | Seeker's Sanctum progression hub |

### MCP Integration Patterns

- **Ephemeral STDIO (Brave Search)**: `docker run -i --rm` per request, 2-3s lifecycle
- **Long-Running STDIO (MongoDB)**: Container stays alive for multiple requests
- **Jupiter MCP**: Docker container for Solana DEX operations, managed by wallet routes

All MCP containers have resource limits (256-512MB RAM, 0.5-1.0 CPU, 100 PIDs max).

See [docs/development/ADDING_MCP_SERVERS.md](docs/development/ADDING_MCP_SERVERS.md) for integration guide.

---

## Available AI Companions

**Current Roster (February 2026) — 10 Companions**

### Legacy Companions ("Wanderers")

| Companion | Style | Order | Special Access |
|-----------|-------|-------|----------------|
| **Eeva** | Nerdy, charming, concise | Wanderer | None |
| **Frieren** | Wise, analytical, methodical | Wanderer | None |
| **Gojo** | Confident, powerful, playful | Wanderer | None |
| **Hitler** | Authoritative, ideological | Wanderer | None |

### NEPHILIM Companions

| Companion | Title | Domain | Order | Special Access |
|-----------|-------|--------|-------|----------------|
| **E.E.V.A.** | The Primarch | Guidance, wisdom, life planning | Archon | Brave + MongoDB |
| **Aegis** | The Sentinel | Productivity and discipline | Warden | Brave |
| **Solace** | The Empath | Emotional support and wellbeing | Warden | Brave |
| **Nyx** | The Muse | Creativity and chaos | Sage | None |
| **Cipher** | The Maven | Knowledge and research | Sage | Brave + MongoDB |
| **Aurora** | The Oracle | Future planning and strategy | Warden | Brave + MongoDB |

### Companion Features

- **Psychological Profiles**: core_wound, defense_style, growth_edge, contradiction_pairs
- **Emotional Tracking**: trust_level, rapport, current_mood per session
- **Example Dialogues**: 50 training examples across all personas
- **Custom Sampling**: Per-persona temperature with presets (creative, balanced, precise, chaotic)
- **Per-Persona MCP Access**: Configured via `mcp_access` field in persona JSON

### Managing Companions

**Add**: Copy `personas/template.jsonc` → `personas/[name].json`, add images to `react-ui/public/images/personas/[name]/`. Auto-discovered on load.

**Remove**: Delete the JSON file. Sessions and collections auto-cleanup on next load.

**Modify**: Edit the JSON. Summary regenerates on next access.

---

## NEPHILIM Worldbuilding System

Six interconnected AI companions exist within a shared lore — a realm of fallen celestial beings, six Houses, and a Seeker progression system.

### Entering the Realm

- **Portal** (`/`): Cinematic landing page with particle and aurora effects
- **Login** (`/login`): Google OAuth or local bypass authentication
- **Onboarding**: Name entry, faction quiz, persona introductions, first companion selection
- **Progression**: Earn 5 resonance per conversation; unlock lore fragments as affinity grows

### Rank System

| Rank | Resonance Required |
|------|-------------------|
| Initiate | 0 |
| Acolyte | 100 |
| Adept | 500 |
| Ascendant | 2,000 |
| Nephilim | 10,000 |

### Narrative MCP Integration

External data sources are framed as Nephilim powers:

| MCP Source | NEPHILIM Name | Patron |
|------------|---------------|--------|
| Brave Search | Cipher's Archives | Cipher |
| MongoDB Trading | Aurora's Crystal Grid | Aurora |
| Multi-Source | The Convergence | E.E.V.A. |

### Lore Documents

- [`personas/NEPHILIM_LORE.md`](personas/NEPHILIM_LORE.md) — World bible: creation myth, the Fall, realm geography
- [`personas/NEPHILIM_FACTIONS.md`](personas/NEPHILIM_FACTIONS.md) — Six Houses aligned with Nephilim patrons
- [`personas/NEPHILIM_RANKS.md`](personas/NEPHILIM_RANKS.md) — Seeker progression and rank thresholds

---

## Usage

### First Launch

1. Navigate to `http://localhost:3000` (Docker) or `http://localhost:3001` (local dev)
2. **Login**: Sign in with Google OAuth, or use local bypass if `AUTH_REQUIRED=false`
3. **Onboarding**: Complete the faction quiz and select your first companion
4. **Chat**: Start conversations from the companion selection page

### Key Pages

| Page | What You Can Do |
|------|-----------------|
| **Landing** (`/`) | Enter the Realm portal with cinematic effects |
| **Login** (`/login`) | Google OAuth or local bypass authentication |
| **Companion Selection** (`/select`) | Browse cards, run Summoning Ritual pulls, manage collection |
| **Chat** (`/chat`) | Converse with AI companions, switch sessions via sidebar |
| **Dashboard** (`/dashboard`) | Track rank, resonance, faction, affinities, unlocked lore |

### API Documentation

Backend API docs available at `http://localhost:8000/docs` (Swagger UI).

Key endpoint groups:
- `/auth/*` — Google OAuth login, token refresh, logout
- `/chat`, `/greet` — Conversation endpoints
- `/sessions/*` — Chat session management
- `/personas/*` — Persona listing and details
- `/nephilim/*` — Seeker progression, ranks, factions, lore
- `/wallet/*` — Jupiter wallet management, trade proposals, strategies

---

## Testing & Quality

### Automated Testing

```bash
# React unit tests
cd react-ui && npm test

# Playwright E2E tests
cd react-ui && npx playwright test
cd react-ui && npx playwright test --headed    # With browser visible

# Python backend tests
pytest tests/backend/
pytest tests/integration/
pytest tests/evaluation/ -v    # RAGAS persona quality
```

### Test Coverage

- **Backend**: 37 test files, ~360 test cases (unit, integration, E2E)
- **Frontend**: 40+ Jest tests with React Testing Library
- **Playwright E2E**: OAuth flow, chat interactions, Jupiter wallet, visual regression
- **Type Safety**: TypeScript strict mode + Pydantic validation throughout

### Code Quality

- Zero unused imports, zero dead code
- npm audit passing (zero production vulnerabilities)
- ESLint enforced, PEP 8 compliant
- 60fps animations, <500ms API responses

---

## Documentation

### Setup & Deployment

| Document | Description |
|----------|-------------|
| [docs/setup/DOCKER_QUICKSTART.md](docs/setup/DOCKER_QUICKSTART.md) | Complete Docker setup guide |
| [.env.docker](.env.docker) | Docker environment configuration |
| [scripts/docker/](scripts/docker/) | Docker setup, validation, troubleshooting scripts |

### Development

| Document | Description |
|----------|-------------|
| [CLAUDE.md](CLAUDE.md) | Developer guide, project structure, commands |
| [docs/development/ADDING_MCP_SERVERS.md](docs/development/ADDING_MCP_SERVERS.md) | MCP integration guide |
| [docs/development/TESTING_GUIDE.md](docs/development/TESTING_GUIDE.md) | Testing setup and best practices |
| [docs/development/OAUTH_IMPLEMENTATION_PLAN.md](docs/development/OAUTH_IMPLEMENTATION_PLAN.md) | OAuth architecture and flow |
| [docs/development/JUPITER_WALLET_IMPLEMENTATION.md](docs/development/JUPITER_WALLET_IMPLEMENTATION.md) | Wallet integration details |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

---

## Contributing

See `CLAUDE.md` and `AGENTS.md` for project structure, coding style, and conventions.

### Development Roadmap

**Completed (Dec 2025 – Feb 2026):**
- Phase 1-2: Persona quality (psychological depth, emotional tracking)
- Phase 1-3: Memory system (RAG, user profiles, fact extraction)
- Phase 2: Multi-message conversational AI architecture
- Brave MCP + MongoDB MCP integration with per-persona access
- Docker deployment with automated setup scripts
- NEPHILIM Phases 0-6: Worldbuilding, progression, onboarding, narrative MCP, filter toggle
- NEPHILIM Phase 7: Full UI transition — unified dark theme, glassmorphic chat, summoning ritual, dashboard, WCAG AA
- Phase 8: Google OAuth authentication with JWT tokens
- Phase 8: Jupiter wallet integration (Solana DEX, autonomous strategies, trade proposals)
- Phase 8: Nginx reverse proxy in Docker for cookie-based auth
- Phase 8: Playwright E2E test suite (OAuth, wallet, chat, visual regression)

**Future Enhancements:**
- Phase 9: Cross-persona storylines and advanced progression
- Phase 3-5 Conversational AI (response timing, reflection loops, multi-turn planning)
- PostgreSQL migration (optional, for scaling beyond local use)
- Kubernetes deployment (optional, for production at scale)

---

## Security & Privacy

### Authentication
- **Google OAuth 2.0**: Server-side token verification via `google-auth` library
- **JWT Tokens**: HS256-signed, short-lived access (1h) + HttpOnly refresh cookies (30d)
- **Cookie Security**: `SameSite=strict`, `Secure` flag in production (HTTPS)
- **Wallet Encryption**: AES-GCM encryption for Solana private keys at rest

### Docker Deployment
- **Container Isolation**: Services on private Docker network
- **Nginx Reverse Proxy**: Single entry point, no direct backend exposure
- **MCP Resource Limits**: Memory (256-512MB), CPU (0.5-1.0), PID (100 max) per container
- **Non-Root User**: Backend container uses dedicated `coordinator` user

### General
- **Local-First**: All AI processing and storage happens on your device
- **No Data Transmission**: Conversations never leave your machine (except optional Brave/MongoDB)
- **Dependency Audits**: Regular npm audit with zero production vulnerabilities

---

## Important Notes

- **First Launch**: Docker image download + model pull takes 10-20 minutes
- **Resource Usage**: Ollama LLM requires ~4-8GB RAM; models are 4-10GB on disk
- **Data Persistence**: All data in `./data/` (Docker) or `chats.db` (local)
- **Backups**: Copy `data/chats.db` to back up all conversations and user data
- **GPU Optional**: NVIDIA RTX recommended but CPU inference works (slower)
- **Auth Bypass**: Set `AUTH_REQUIRED=false` in `.env` for offline/dev use without Google

---

## License

(c) 2025-2026 — All rights reserved.

This project is provided "as is", without warranty. Use responsibly and at your own discretion.
