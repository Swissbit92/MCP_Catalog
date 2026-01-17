# 🧠 MCP Coordinator - AI Companion Interface

> **Local AI Companion Chat with Advanced Memory & Live Data**
> _Private • Local-First • Docker-Ready • React + FastAPI Coordinator_

<div align="center">

[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker)](https://docker.com)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-19-61dafb.svg)](https://reactjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com)
[![Ollama](https://img.shields.io/badge/Ollama-Latest-orange.svg)](https://ollama.ai)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57.svg?logo=sqlite)](https://sqlite.org)

**🐳 Docker Quick Start (Recommended) • 🤖 Multiple AI Companions • 💬 Persistent Chat**
[What Can This Do?](#-what-can-this-do) • [Docker Setup](#-quick-start-docker) • [Local Setup](#-alternative-local-development-setup)

</div>

---

## 📋 Table of Contents

- [🚀 What Can This Do?](#-what-can-this-do)
- [🔍 How Does It Compare?](#-how-does-it-compare)
- [✨ Features](#-features)
- [🛠️ Tech Stack](#️-tech-stack)
- [🔧 System Requirements](#-system-requirements)
- [⚡ Quick Start (Docker)](#-quick-start-docker)
- [🧩 Alternative: Local Development Setup](#-alternative-local-development-setup)
- [🏗️ Architecture](#️-architecture)
- [🎭 Available Personas](#-available-personas)
- [🚀 Usage](#-usage)
- [✅ Testing & Quality](#-testing--quality)
- [📚 Documentation](#-documentation)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

---

## 🚀 What Can This Do?

**5-Second Pitch:** Local AI companions with personality-driven conversations, web search, trading data, and advanced memory - all running on your machine.

### Key Capabilities

- 🤖 **4 AI Companions** with psychological depth and emotional tracking
- 💬 **Natural Multi-Message Conversations** (2-4 messages per response, like texting a real person)
- 🧠 **Advanced Memory System** - remembers you across sessions, extracts facts automatically
- 🔍 **Web Search with Citations** - personas autonomously search Brave API with mandatory sources
- 📊 **Real-Time Trading Data** - Bitcoin prices, technical indicators (RSI, MACD), DCA stats via MongoDB
- 🎲 **Gacha Collection System** - pull cards, build collections, unlock personas
- 💾 **100% Local & Private** - all conversations stay on your device (no data transmission)
- 🐳 **One-Command Docker Setup** - automated script handles everything

### Who Is This For?

- **Developers** wanting a local ChatGPT alternative with customizable AI companions
- **Crypto Enthusiasts** needing a research assistant with live Bitcoin data
- **Privacy-Conscious Users** who want full control over their AI conversations
- **AI Experimenters** interested in companion-driven conversational AI with advanced memory

---

## 🔍 How Does It Compare?

**vs. Other Local AI Chat Solutions**

| Feature | MCP Coordinator | Open WebUI | LM Studio | Jan | LibreChat | ChatGPT |
|---------|----------------|------------|-----------|-----|-----------|---------|
| **100% Local & Private** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ Cloud |
| **Multi-Message Conversations** | ✅ 2-4 msgs | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Dynamic AI Companion System** | ✅ 4 companions | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Advanced Memory (RAG)** | ✅ FAISS + profiles | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Emotional Tracking** | ✅ Trust/rapport | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Psychological Depth** | ✅ Core wound/defense | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Web Search Integration** | ✅ Brave API | ✅ Plugins | ❌ | ❌ | ✅ Plugins | ✅ Bing |
| **Live Data (MongoDB)** | ✅ Bitcoin/trading | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Gacha/Gamification** | ✅ Collection system | ❌ | ❌ | ❌ | ❌ | ❌ |
| **One-Command Setup** | ✅ Docker script | ⚠️ Manual | ✅ GUI installer | ✅ GUI installer | ⚠️ Manual | N/A |
| **Citation Validation** | ✅ Mandatory | ❌ | ❌ | ❌ | ❌ | ⚠️ Optional |
| **Persistent Chat** | ✅ SQLite | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Open Source** | ✅ | ✅ | ❌ Proprietary | ❌ Proprietary | ✅ | ❌ Proprietary |
| **Cross-Session User Profiles** | ✅ Auto-extract facts | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Cost** | Free | Free | Free | Free | Free | $20/mo |

### 🎯 What Makes MCP Coordinator Unique?

1. **Natural Conversations** - Multi-message responses (2-4 messages with staggered rendering) simulate texting a real person, not a chatbot
2. **AI Companion System** - Deep psychological profiles with emotional tracking create genuinely different companions
3. **Advanced Memory** - Only solution with RAG semantic search + automatic user profile building across sessions
4. **Live Data Integration** - Real-time Bitcoin prices and technical indicators via MongoDB MCP
5. **Transparent Data Sources** - Mandatory citations for web search, visible source tags (pure LLM/Brave/MongoDB) on every message
6. **Gamified UX** - Gacha collection system makes discovering personas engaging

### 📊 When to Choose MCP Coordinator?

**Choose MCP Coordinator if you want:**
- Conversations that feel like texting a friend, not querying a database
- AI companions that remember you across sessions and adapt their responses
- Live crypto/trading data integrated naturally into conversations
- Complete transparency about where answers come from
- A fun, engaging way to interact with local AI

**Choose alternatives if you need:**
- **Open WebUI** - Maximum compatibility with all Ollama models, extensive plugin ecosystem
- **LM Studio** - Simple drag-and-drop model management with polished GUI
- **Jan** - Easiest setup for non-technical users with GUI installer
- **LibreChat** - Support for multiple LLM providers (OpenAI, Anthropic, Google, etc.)

---

## ✨ Features

### 🤖 AI & Conversational Intelligence

| Feature | Description |
|---------|-------------|
| 🤖 **Dynamic AI Companions** | Chat with Eeva, Frieren, Gojo, Hitler - each with unique personality, expertise, and voice |
| 🧠 **Advanced Memory System** | Multi-phase memory with importance scoring, auto-summarization, RAG semantic search, and cross-session user profiles |
| 💬 **Multi-Message Conversations** | Natural conversational flow with 2-4 messages per response, staggered rendering (1.2s delays) |
| 🎨 **Psychological Depth** | Each persona has core_wound, defense_style, growth_edge, contradiction_pairs for realistic behavior |
| 📊 **Emotional State Tracking** | Personas track trust_level, rapport, and current_mood across conversations |
| 🎯 **Context Management** | Token budget monitoring with 90% warnings, critical message detection (names 6x weight, never dropped) |
| 📝 **Example Dialogues** | 50 training examples across all personas to teach correct voice and style |
| 🔧 **Advanced Sampling** | Per-persona temperature, top_k, top_p, repeat_penalty with presets (creative, balanced, precise, chaotic) |

### 🌐 External Integrations

| Feature | Description |
|---------|-------------|
| 🔍 **Brave Web Search** | Rare/Epic/Legendary personas autonomously search the web with mandatory citation validation |
| 🗄️ **MongoDB MCP Integration** | Epic/Legendary personas query real-time Bitcoin prices, technical indicators (RSI, MACD, Bollinger Bands), and DCA trading stats |
| 📈 **Live Trading Data** | Historical price data (2016-present), hourly charts (6 months), technical analysis signals |
| 🔗 **Smart Caching** | TTL-based cache (60s current price, 3600s historical) for optimal performance |
| 📚 **Synthesis Prompts** | Anti-hallucination prompts ensure accurate data usage and persona flavor retention |

### 🎮 User Experience

| Feature | Description |
|---------|-------------|
| 🎯 **Advanced Gacha System** | Classic character pulls with 1x/5x/10x multi-pull, particle effects, and audio feedback |
| 💎 **Classic Card Collection** | Elegant collectible cards with foil effects, smooth animations, and rarity-based styling |
| 🔊 **Audio Integration** | Synthesized sound effects for pulls, reveals, and celebrations with mute controls |
| 📊 **Collection Management** | Persistent character collection with statistics, pull history, and organized display |
| 💬 **Persistent Chat History** | Conversations saved across sessions with automatic cleanup of orphaned chats |
| 🔄 **Session Switching** | Seamlessly switch between different persona chats |
| 🎨 **Modern UI** | Beautiful React interface with premium animations and mobile optimization |
| 📋 **Copy Functionality** | ChatGPT-style copy buttons for JSON and code blocks |
| 📱 **Mobile Optimization** | ChatGPT-style responsive layout, touch gestures, swipe navigation |

### 🔒 Privacy & Architecture

| Feature | Description |
|---------|-------------|
| 🔒 **Local-First** | All AI processing and data storage happens on your device |
| 🛡️ **Secure Dependencies** | Regular security audits |
| 🤖 **Ollama LLM** | Powered by local LLM models (nchapman/gemma-2-9b-it-abliterated:9b - validated Dec 2025) |
| 🐳 **Docker Ready** | Containerized deployment with automated setup scripts |
| 📊 **Type Safety** | TypeScript strict mode + Pydantic validation throughout |
| 🔄 **Dynamic Persona Management** | Automatic discovery, orphaned session cleanup, collection synchronization |

---

## 🛠️ Tech Stack

**Current as of December 2025**

### Frontend
- **React 19** with TypeScript 4.9.5
- **Framer Motion** for 60fps animations
- **Tailwind CSS** for utility-first styling
- **Lucide React** for icon library

### Backend
- **FastAPI 0.100+** with Uvicorn ASGI server
- **Python 3.11+** with type hints
- **Pydantic 2.x** for schema validation and settings
- **SQLite 3** for persistent storage

### AI/ML
- **Ollama** local LLM server
- **nchapman/gemma-2-9b-it-abliterated:9b** (9GB model, validated Dec 2025)
  - 75% multi-message usage, 0% garbled output, 100% technical accuracy
- **nomic-embed-text:latest** for embeddings (Phase 3 memory)
- **FAISS CPU** for vector search and semantic retrieval
- **LangChain** for LLM orchestration

### Integrations
- **Brave Search API** for web search (Rare+ personas)
- **MongoDB Atlas** for Bitcoin trading data (Epic+ personas)
- **Docker + Docker Compose** for deployment

---

## 🔧 System Requirements

### Docker Setup (Recommended)

| Component | Requirement | Installation |
|-----------|-------------|--------------|
| **OS** | Windows 10/11, macOS 13+, or Linux | - |
| **Docker Desktop** | v24.0+ with Docker Compose v2.0+ | [docker.com](https://docker.com) |
| **Disk Space** | 15GB free (for images + models) | - |
| **RAM** | 8GB minimum, 16GB recommended | For running Ollama LLM |
| **GPU** | NVIDIA RTX (optional) | For CUDA acceleration |

### Local Development Setup

| Component | Requirement | Installation |
|-----------|-------------|--------------|
| **Python** | 3.11 or higher | [python.org](https://python.org) |
| **Node.js** | v16+ with npm | [nodejs.org](https://nodejs.org) |
| **Ollama** | Latest version | [ollama.ai](https://ollama.ai) |
| **GPU** | NVIDIA RTX 30/40 series (optional) | For CUDA acceleration |
| **VRAM** | ≥ 8 GB (recommended) | For optimal performance |

---

## ⚡ Quick Start (Docker)

> **🐳 Recommended**: Docker provides the easiest setup with all dependencies containerized.

**Prerequisites**: [Docker Desktop](https://docker.com) installed and running

### One-Command Setup (Easiest)

```bash
# 1. Clone the repository
git clone https://github.com/Swissbit92/MCP_Catalog.git
cd MCP_Catalog

# 2. Run the setup script
# Windows (PowerShell):
.\scripts\docker\setup-docker.ps1

# Windows (Command Prompt):
scripts\docker\setup-docker.bat

# Linux/Mac:
chmod +x scripts/docker/setup-docker.sh
./scripts/docker/setup-docker.sh
```

**🎉 That's it!** The script will:
- ✅ Start all Docker containers
- ✅ Download the 9GB AI model (with progress bar)
- ✅ Download the embedding model (for memory features)
- ✅ Verify everything is running
- ✅ Open your browser automatically

**App will be ready at:** `http://localhost:3000`

---

### Manual Setup (Alternative)

If you prefer to run commands manually:

```bash
# 1. Clone the repository
git clone https://github.com/Swissbit92/MCP_Catalog.git
cd MCP_Catalog

# 2. Start all services (downloads ~2GB of images on first run)
docker-compose --env-file .env.docker up -d

# 3. Pull LLM model (~9GB download, takes 5-10 minutes)
docker exec -it ai-companion-brain ollama pull nchapman/gemma-2-9b-it-abliterated:9b

# 4. Pull embedding model (optional, for Phase 3 memory)
docker exec -it ai-companion-brain ollama pull nomic-embed-text:latest

# 5. Open your browser
start http://localhost:3000  # Windows
open http://localhost:3000   # Mac/Linux
```

**🎉 Done!** Your app is running at `http://localhost:3000`

### Quick Commands

```bash
# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Restart a service
docker-compose restart backend

# Backup your database
# Windows: Copy-Item data\chats.db data\chats.db.backup
# Linux/Mac: cp data/chats.db data/chats.db.backup
```

### Validation (Optional)

Test your Docker setup:

```bash
# Windows
.\scripts\docker\test_docker_setup.ps1

# Linux/Mac
chmod +x scripts/docker/test_docker_setup.sh
./scripts/docker/test_docker_setup.sh
```

**📖 Detailed Guide**: See [docs/setup/DOCKER_QUICKSTART.md](docs/setup/DOCKER_QUICKSTART.md) for full documentation, troubleshooting, and advanced configuration.

---

## 🧩 Alternative: Local Development Setup

> **Note**: Docker setup (above) is recommended for most users. Use local setup if you need to modify code or prefer running services directly.

### 📥 Step 1: Clone the Repository

```bash
git clone https://github.com/Swissbit92/MCP_Catalog.git
cd MCP_Catalog
```

### 🔧 Step 2: Install Dependencies

#### **Option A: Automated Setup (Recommended)**

```bash
# Linux/macOS
chmod +x scripts/setup/setup.sh
./scripts/setup/setup.sh

# Windows
scripts\setup\setup.bat
```

#### **Option B: Manual Setup**

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# Install Python dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# Install React dependencies
cd react-ui
npm install
cd ..
```

### 🤖 Step 3: Setup Ollama

#### **Install Ollama**

Visit [ollama.ai](https://ollama.ai) and download the installer for your OS.

#### **Start Ollama Service**

```bash
# Start Ollama in the background
ollama serve
```

#### **Pull Required Model**

```bash
# Pull the RECOMMENDED model (validated Dec 25, 2025)
# nchapman: 9B params, uncensored, excellent multi-message performance
# Test results: 75% multi-message usage, 0% garbled output, 100% technical accuracy
ollama pull nchapman/gemma-2-9b-it-abliterated:9b

# Pull embedding model (optional, for Phase 3 memory features)
ollama pull nomic-embed-text:latest

# Alternative models (NOT recommended):
# ollama pull dolphin-llama3:8b      # Previous default, replaced due to reliability issues
# ollama pull llama3.1:latest        # Formal, censored, doesn't follow <msg> tag instructions
```

### ⚙️ Step 4: Configure Environment

Create a `.env` file in the root directory:

```bash
# Ollama configuration
OLLAMA_BASE=http://127.0.0.1:11434
PERSONA_MODEL=nchapman/gemma-2-9b-it-abliterated:9b
PERSONA_TEMPERATURE=0.9

# Server configuration
COORD_PORT=8000
COORD_URL=http://127.0.0.1:8000
PERSONA_DIR=personas

# Database (SQLite)
COORDINATOR_DB_PATH=chats.db

# Optional: Brave Search API
BRAVE_API_KEY=
BRAVE_ENABLED_RARITIES=rare,epic,legendary

# Optional: MongoDB MCP
MONGODB_URI=
MONGODB_ENABLED=false

# Optional: Memory & RAG
MEMORY_EMBEDDING_MODEL=nomic-embed-text:latest
MEMORY_SUMMARIZATION_INTERVAL=30
MEMORY_FACT_EXTRACTION_INTERVAL=10
```

**Key Environment Variables:**

- `OLLAMA_BASE`: Ollama API endpoint (default: http://127.0.0.1:11434)
- `PERSONA_MODEL`: LLM model to use (default: nchapman/gemma-2-9b-it-abliterated:9b)
- `PERSONA_TEMPERATURE`: LLM creativity (0.0-1.5, default: 0.9)
- `COORDINATOR_DB_PATH`: SQLite database location (default: chats.db)

---

## 🏗️ Architecture

```
                           🧠  MCP Coordinator
                   ╔═══════════════════════════════════════╗
                   ║         React Frontend (19)           ║
                   ║   (Gacha System • Multi-Message UI)   ║
                   ╚═══════════════════════════════════════╝
                                   │  🔗  HTTP / CORS
                                   ▼
                   ╔═══════════════════════════════════════╗
                   ║     🧩 FastAPI Coordinator (0.100+)   ║
                   ║  (Persona Router • MCP Bridge • LLM)  ║
                   ╚═══════════════════════════════════════╝
                    │                   │                  │
        ┌───────────┴───────┬───────────┴────────┬─────────┴───────┐
        ▼                   ▼                    ▼                 ▼
  ╔═══════════╗     ╔═══════════╗      ╔═══════════╗     ╔═══════════╗
  ║ 🔍 Brave  ║     ║ 🗄️ MongoDB ║      ║ 💾 SQLite ║     ║ 🧠 FAISS  ║
  ║  Search   ║     ║    MCP     ║      ║  Database ║     ║  Vectors  ║
  ║ (Rare+)   ║     ║ (Epic+)    ║      ║  (Chats)  ║     ║ (Memory)  ║
  ╚═══════════╝     ╚═══════════╝      ╚═══════════╝     ╚═══════════╝
                                   │
                                   ▼
                  ╔═══════════════════════════════════════╗
                  ║ 🤖 Ollama LLM (Local Inference)       ║
                  ║  • nchapman/gemma-2-9b (9B params)    ║
                  ║  • nomic-embed-text (embeddings)      ║
                  ╚═══════════════════════════════════════╝
```

### Component Breakdown

- **React Frontend**: TypeScript 4.9.5, Framer Motion animations, mobile-optimized
- **FastAPI Backend**: Persona routing, MCP client orchestration, LLM integration
- **Brave Search**: Web search with citation validation (Rare/Epic/Legendary)
- **MongoDB MCP**: Bitcoin trading data with technical indicators (Epic/Legendary)
- **SQLite**: Persistent chat history, sessions, summaries, user profiles
- **FAISS**: Vector database for semantic memory search (Phase 3)
- **Ollama**: Local LLM server with nchapman model + nomic embeddings

### MCP Server Integration

The MCP Coordinator uses two proven patterns for integrating external data sources:

- **Ephemeral STDIO (Brave Search)**: Spawns containers per request, dies after response (2-3 seconds)
- **Long-Running STDIO (MongoDB)**: Single container stays alive for multiple requests

Both patterns use Docker containers with STDIO transport (JSON-RPC 2.0 via stdin/stdout pipes).

**Want to add your own MCP server?** See **[docs/development/ADDING_MCP_SERVERS.md](docs/development/ADDING_MCP_SERVERS.md)** for:
- Choosing the right pattern for your use case
- Step-by-step implementation guide with examples
- Testing, troubleshooting, and best practices
- Rarity-based feature gating configuration

---

## 🤖 Available AI Companions

**Current Roster (December 2025):**

| Companion | Style | Rarity | Special Access |
|---------|-------|--------|----------------|
| **Eeva** | Nerdy, charming, concise | Legendary | Brave + MongoDB |
| **Frieren** | Wise, analytical, methodical | Legendary | Brave + MongoDB |
| **Gojo** | Confident, powerful, playful | Legendary | Brave + MongoDB |
| **Hitler** | Authoritative, ideological | Legendary | Brave + MongoDB |

### Companion Features

- **Psychological Profiles**: Each companion has core_wound, defense_style, growth_edge, contradiction_pairs
- **Emotional Tracking**: Companions track trust_level, rapport, current_mood per session
- **Example Dialogues**: 50 training examples (10-15 per companion) teach correct voice
- **Custom Sampling**: Per-companion temperature and sampling presets (creative, balanced, precise)
- **Special Access**: All current companions are Legendary with full Brave + MongoDB access

### Managing AI Companions

#### ➕ Adding a New Companion

1. **Create persona file**: Copy `personas/template.jsonc` to `personas/[name].json`
2. **Configure persona**: Edit the JSON with character details (see template for schema)
3. **Add images**: Place card, avatar, logo, and background images in `react-ui/public/images/personas/[name]/`
4. **Auto-discovery**: Persona appears automatically without restart

#### 🗑️ Removing a Companion

1. **Delete persona file**: Remove JSON from `personas/` directory
2. **Automatic cleanup**: Sessions, chats, and collections auto-cleanup on next load

#### 🔄 Modifying a Companion

1. **Edit persona file**: Update JSON with new details
2. **Auto-update**: Summary regenerates on next access, UI updates immediately

---

## 🚀 Usage

### Docker Usage

**Start the application:**
```bash
docker-compose --env-file .env.docker up -d
```

**Access the application:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

**View logs:**
```bash
docker-compose logs -f backend  # Backend logs
docker-compose logs -f          # All services
```

**Stop the application:**
```bash
docker-compose down
```

**Backup your data:**
```bash
# Windows
Copy-Item data\chats.db backups\chats.db.$(Get-Date -Format 'yyyyMMdd')

# Linux/Mac
cp data/chats.db backups/chats.db.$(date +%Y%m%d)
```

### Local Development Usage

#### **Option A: Unified Startup (Recommended)**

```bash
python scripts/utils/run_react.py
```

**🎯 This starts both backend and frontend automatically!**

#### **Option B: Manual Startup**

```bash
# Terminal 1: Backend
python run.py

# Terminal 2: Frontend
cd react-ui && npm start
```

#### **Stopping the Application**

Press `Ctrl+C` in the terminal running `python scripts/utils/run_react.py` to stop both services gracefully.

---

### 🎯 How to Use the App

#### **Home Page (`/`)**

- 🎲 **Try Your Luck**: Navigate to Gacha Pull for companion pulls
- 📚 **Browse All Agents**: View all available AI companions
- 🎨 **Sophisticated UI**: Glassmorphism effects, animated particles

#### **Agent Selection (`/select`)**

- 🎴 **Card Gallery**: Browse with search and rarity filtering
- 🎲 **Gacha Pull**: 1x/5x/10x pulls with audio and particle effects
- 📚 **My Collection**: View collected companions with stats
- 📊 **Pull History**: Track pulling statistics
- 🎯 **Choose Agents**: Click "Choose" to jump to chat

#### **Chat Interface (`/chat`)**

- 💬 **Start Conversations**: Chat with selected AI companion
- 🔄 **Switch Sessions**: Use sidebar to change chats
- 💾 **Export Chats**: Save conversations as JSON
- 🎨 **Rarity Theming**: Companion-specific colors and backgrounds
- 📋 **Copy Functionality**: Copy JSON/code blocks with one click

---

## ✅ Testing & Quality

### Automated Testing

- **Backend Tests**: 37 test files, ~360 test cases
  - Unit tests for all core modules
  - Integration tests for Phase 1-3 features
  - End-to-end tests for Brave/MongoDB MCPs
- **Frontend Tests**: 40+ Jest tests with React Testing Library
  - Component tests for all major UI elements
  - Integration tests for multi-message rendering
  - Phase 2 persona quality validation

### Code Quality Metrics

- **Type Safety**: TypeScript strict mode + Pydantic validation throughout
- **Hygiene Score**: 10/10
  - Zero unused imports
  - Zero dead code
  - Zero TODO comments (all tracked in docs)
- **Security**: npm audit passing
  - 2 moderate dev-only issues (react-scripts nested deps)
  - Zero production vulnerabilities
  - Regular dependency updates
- **Documentation**: 20+ docs in `AI_documentation/`
  - Implementation summaries for all phases
  - Roadmaps and feature specs
  - Architectural decision records

### Production Readiness

- **Docker Build**: Tested with automated validation scripts
- **Model Validation**: Comparison testing (nchapman vs. alternatives)
  - See `MODEL_SWITCH_VALIDATION_RESULTS.md`
- **Performance**: 60fps animations, <500ms API responses
- **Reliability**: 100% test pass rate, zero critical bugs
- **Monitoring**: Comprehensive logging with structured formats

### Quality Assurance Process

1. **Pre-Commit**: Local testing before commits
2. **Code Review**: Documentation-first approach
3. **Validation**: Manual testing for major features
4. **Hygiene Sessions**: Regular cleanup and refactoring

---

## 📚 Documentation

### Docker Deployment

| Document | Description |
|----------|-------------|
| **[docs/setup/DOCKER_QUICKSTART.md](docs/setup/DOCKER_QUICKSTART.md)** | Complete Docker setup guide with troubleshooting |
| **[SQLITE_ARCHITECTURE.md](SQLITE_ARCHITECTURE.md)** | Technical decision record for SQLite architecture |
| **[.env.docker](.env.docker)** | Environment configuration template |
| **[scripts/docker/test_docker_setup.ps1](scripts/docker/test_docker_setup.ps1)** | Windows validation script |
| **[scripts/docker/test_docker_setup.sh](scripts/docker/test_docker_setup.sh)** | Linux/Mac validation script |

### Development & Architecture

| Document | Description |
|----------|-------------|
| **[CLAUDE.md](CLAUDE.md)** | Developer guide, project structure, testing (most up-to-date) |
| **[AGENTS.md](AGENTS.md)** | Repository guidelines, coding style, setup commands |
| **[ASSESSMENT.md](ASSESSMENT.md)** | Codebase quality assessment (Dec 2025) |
| **[CHANGELOG.md](CHANGELOG.md)** | Version history and feature additions |
| **[docs/development/ADDING_MCP_SERVERS.md](docs/development/ADDING_MCP_SERVERS.md)** | Guide for integrating new MCP servers (ephemeral & long-running patterns) |
| **[docs/development/TESTING_GUIDE.md](docs/development/TESTING_GUIDE.md)** | Testing setup, organization, and best practices |

### Testing & Quality

| Document | Description |
|----------|-------------|
| **[docs/testing/PYTEST_BASELINE_REPORT.md](docs/testing/PYTEST_BASELINE_REPORT.md)** | Pytest configuration and coverage baseline |

### Scripts & Utilities

| Directory | Description |
|-----------|-------------|
| **[scripts/](scripts/)** | Organized collection of development and deployment scripts |
| **[scripts/docker/](scripts/docker/)** | Docker setup, validation, and troubleshooting scripts |
| **[scripts/setup/](scripts/setup/)** | Local development environment setup scripts |
| **[scripts/utils/](scripts/utils/)** | Python utilities (unified launcher, validation, cleanup) |

See each directory's README.md for usage examples and detailed documentation.

### Production & Scaling

| Document | Description |
|----------|-------------|
| **[PRODUCTION_READINESS_PLAN.md](PRODUCTION_READINESS_PLAN.md)** | 3-phase migration plan for PostgreSQL/K8s (future) |
| **[PHASE1_IMPLEMENTATION_PLAN.md](PHASE1_IMPLEMENTATION_PLAN.md)** | Detailed PostgreSQL migration guide (if needed) |

### Feature Documentation

| Document | Description |
|----------|-------------|
| **AI_documentation/** | Historical specs, implementation summaries, feature docs |
| **AI_documentation/05_roadmaps/** | Memory enhancement, persona quality, conversational AI roadmaps |
| **AI_documentation/01_implementation_history/** | Phase 1-3 completion summaries and validation results |
| **MODEL_SWITCH_VALIDATION_RESULTS.md** | nchapman model selection rationale (Dec 2025) |
| **MSG_TAG_ANALYSIS_RECOMMENDATION.md** | Multi-message architecture analysis |

---

## 🤝 Contributing

See Repository Guidelines in `AGENTS.md` and `CLAUDE.md` for:

- Project structure overview and entrypoints
- Setup and run commands (Python, FastAPI, React, Docker)
- Coding style and test conventions
- Commit/PR expectations and environment variables

See `CHANGELOG.md` for recent updates and project evolution.

### 📋 Development Roadmap

**Completed (Dec 2025):**
- ✅ Phase 1-2 Persona Quality (psychological depth, emotional tracking)
- ✅ Phase 1-3 Memory System (RAG, user profiles, fact extraction)
- ✅ Phase 2 Conversational AI (multi-message architecture)
- ✅ Brave MCP Integration (web search with citations)
- ✅ MongoDB MCP Integration (trading data with technical indicators)
- ✅ Docker deployment with automated setup

**Future Enhancements:**
- Phase 3 Conversational AI (response timing analysis, follow-up generation)
- Phase 4 Conversational AI (reflection loops, meta-cognition)
- Phase 5 Conversational AI (multi-turn planning)
- PostgreSQL migration (optional, for scaling beyond local use)
- Kubernetes deployment (optional, for production at scale)

Contributions are welcome. Please read `AGENTS.md` before opening a PR.

---

## 🛡️ Security & Privacy

### Docker Deployment
- **Container Isolation**: Services run in isolated containers with minimal attack surface
- **Non-Root User**: Backend container runs as non-root user for security
- **Local Network**: Services communicate via private Docker network
- **Volume Security**: Data persists in host-mounted volumes you control
- **No External Dependencies**: All processing happens locally (except optional web search/MongoDB)

### General Security
- **Dependency Audits**: Regular npm audit checks with minimal vulnerabilities (2 moderate issues in dev dependencies only)
- **Local-First Architecture**: All AI processing and data storage happens locally
- **No Data Transmission**: Conversations never leave your device (unless you use optional Brave/MongoDB features)
- **Package Overrides**: Security fixes applied via package.json overrides for transitive dependency vulnerabilities
- **Production Ready**: Optimized build with no security issues affecting production runtime

---

## ⚠️ Important Notes

### Docker Setup
- **Data Persistence**: All data stored in `./data/` directory on your machine
- **First Launch**: Docker image download and model pull takes 10-20 minutes initially
- **Resource Usage**: Ollama LLM requires ~4-8GB RAM when running
- **Disk Space**: LLM models are 4-10GB each, plan accordingly
- **Backups**: Simply copy `data/chats.db` file to backup your conversations

### Local Development Setup
- **Local AI Only**: All conversations run locally via Ollama - no data leaves your device
- **GPU Recommended**: For best performance, use a GPU with ≥8GB VRAM
- **First Launch**: Initial model loading may take a few minutes
- **SQLite Database**: All data stored in `chats.db` file in project root

### General
- **Privacy First**: Your conversations are 100% private and local
- **Experimental**: This is a prototype - use responsibly
- **Optional Features**: Web search (Brave) and MongoDB features require external APIs
- **Model Validation**: nchapman model validated Dec 2025 with comprehensive testing

---

## 📄 License

© 2025 GraphRAG Coordinator UI – All rights reserved.

This project is provided "as is", without any warranty or guarantee. Use responsibly and at your own discretion.

---
