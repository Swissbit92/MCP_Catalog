# 🧠 MCP Coordinator - Persona Chat Interface

> **Local Persona-Driven Chat Interface for GraphRAG & MCP Servers**
> _Private • Local-First • Docker-Ready • React + FastAPI Coordinator_

<div align="center">

[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker)](https://docker.com)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-19-61dafb.svg)](https://reactjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com)
[![Ollama](https://img.shields.io/badge/Ollama-Latest-orange.svg)](https://ollama.ai)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57.svg?logo=sqlite)](https://sqlite.org)

**🐳 Docker Quick Start (Recommended) • 🎭 Multiple Personas • 💬 Persistent Chat**
[Docker Setup](#-quick-start-docker) • [Local Setup](#-alternative-local-development-setup) • [Usage](#-usage)

</div>

---

## 📋 Table of Contents

- [✨ Features](#-features)
- [🔧 System Requirements](#-system-requirements)
- [⚡ Quick Start (Docker)](#-quick-start-docker)
- [🧩 Alternative: Local Development Setup](#-alternative-local-development-setup)
- [🚀 Usage](#-usage)
- [🎭 Managing Personas](#-managing-personas)
- [📚 Documentation](#-documentation)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎭 **Dynamic Personas** | Chat with Eeva, Frieren, Gojo, Hitler, Itachi, and more - add/remove personas seamlessly |
| 🎯 **Advanced Gacha System** | Classic character pulls with 1x/5x/10x multi-pull, particle effects, and audio feedback |
| 💎 **Classic Cards** | Elegant collectible cards with foil effects, smooth animations, and rarity-based styling |
| 🔊 **Audio Integration** | Synthesized sound effects for pulls, reveals, and celebrations with mute controls |
| 📊 **Collection Management** | Persistent character collection with statistics, pull history, and organized display |
| 💬 **Persistent Chat** | Conversations saved across sessions with automatic cleanup |
| 🔄 **Session Switching** | Seamlessly switch between different persona chats |
| 🎨 **Modern UI** | Beautiful React interface with premium animations and mobile optimization |
| 🎭 **Persona Customization** | Rarity-based theming with custom backgrounds, colors, and avatar effects |
| 📋 **Copy Functionality** | ChatGPT-style copy buttons for JSON and code blocks |
| 🔒 **Local-First** | All data stays on your device |
| 🛡️ **Secure Dependencies** | Regular security audits with minimal vulnerabilities in production |
| 🤖 **AI-Powered** | Powered by Ollama LLM models |
| 🔍 **Web Search with Citations** | Rare/Epic/Legendary personas autonomously search the web (Brave API) with mandatory source citations |
| 🗄️ **MongoDB MCP** | Epic/Legendary personas can query Bitcoin price & trading data (70% complete) |
| 🔄 **Dynamic Persona Management** | Automatic persona discovery, orphaned session cleanup, collection synchronization, and chat history updates |

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
.\setup-docker.ps1

# Windows (Command Prompt):
setup-docker.bat

# Linux/Mac:
chmod +x setup-docker.sh
./setup-docker.sh
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
.\test_docker_setup.ps1

# Linux/Mac
chmod +x test_docker_setup.sh
./test_docker_setup.sh
```

**📖 Detailed Guide**: See [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) for full documentation, troubleshooting, and advanced configuration.

---

---

## 📚 Documentation

### Docker Deployment

| Document | Description |
|----------|-------------|
| **[DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)** | Complete Docker setup guide with troubleshooting |
| **[SQLITE_ARCHITECTURE.md](SQLITE_ARCHITECTURE.md)** | Technical decision record for SQLite architecture |
| **[.env.docker](.env.docker)** | Environment configuration template |
| **[test_docker_setup.ps1](test_docker_setup.ps1)** | Windows validation script |
| **[test_docker_setup.sh](test_docker_setup.sh)** | Linux/Mac validation script |

### Development & Architecture

| Document | Description |
|----------|-------------|
| **[CLAUDE.md](CLAUDE.md)** | Developer guide, project structure, testing |
| **[AGENTS.md](AGENTS.md)** | Repository guidelines, coding style, setup commands |
| **[ASSESSMENT.md](ASSESSMENT.md)** | Codebase quality assessment (Dec 2025) |
| **[CHANGELOG.md](CHANGELOG.md)** | Version history and feature additions |

### Production & Scaling

| Document | Description |
|----------|-------------|
| **[PRODUCTION_READINESS_PLAN.md](PRODUCTION_READINESS_PLAN.md)** | 3-phase migration plan for PostgreSQL/K8s (future) |
| **[PHASE1_IMPLEMENTATION_PLAN.md](PHASE1_IMPLEMENTATION_PLAN.md)** | Detailed PostgreSQL migration guide (if needed) |

### Feature Documentation

| Document | Description |
|----------|-------------|
| **AI_documentation/** | Historical specs, implementation summaries, feature docs |
| **PERSONA_MEMORY_ROADMAP.md** | 3-phase memory enhancement roadmap |

---

## 🤝 Contributing

See Repository Guidelines in `AGENTS.md` and `CLAUDE.md` for:

- Project structure overview and entrypoints
- Setup and run commands (Python, FastAPI, React, Docker)
- Coding style and test conventions
- Commit/PR expectations and environment variables

See `CHANGELOG.md` for recent updates and project evolution.

### 📋 Development Roadmap

**Future Enhancements**: See [`PERSONA_QUALITY_ROADMAP.md`](PERSONA_QUALITY_ROADMAP.md) for planned improvements:
- Advanced Pydantic schema validation for type safety
- Enhanced persona psychological depth and consistency
- Improved context management and long-term memory
- Advanced sampling parameters for response quality

**Target**: 25-30% improvement in persona realism and user engagement (80-100 hour implementation plan).

Contributions are welcome. Please read `AGENTS.md` before opening a PR.

## 📖 Overview

The **GraphRAG Coordinator UI** provides a local chat interface for interacting with multiple MCP (Modular Computation Process) servers — such as `rag`, `kg`, and others — through a **persona-driven** experience.

It runs entirely **locally**, connects to a **FastAPI Coordinator** (the backend), and communicates with **Ollama** for local LLM inference.
Personas such as **Eeva**, **Frieren**, **Gojo**, and others can be selected via an interactive dual-mode interface: exciting gacha-style random pulls on the home page or convenient static browsing with search on the character selection page.
The chat interface is responsive, centered, and styled like a modern messaging app with premium visual effects.

### 🎨 React UI Enhancements (Completed)

 The React application features comprehensive visual polish and mobile optimization:

 - **Header Component**: Modern dark theme with particle effects, dynamic theming, glassmorphism, animated typography, and functional mobile hamburger menu
 - **Character Cards**: Framer Motion animations with staggered entrance effects, interactive hover states, and rarity-based styling
 - **Chat Interface**: Smooth auto-scrolling, animated message bubbles, enhanced typing indicators, rich media support (JSON highlighting with copy buttons and visual feedback, code blocks with copy buttons and visual feedback), latency tracking, error recovery with retry functionality, and polished input interactions
 - **Persona Customization**: Gacha-style theming with rarity-based colors (legendary=gold, epic=purple, rare=blue, common=grey), custom character backgrounds, personalized avatar effects with rarity rings and shadows, and cohesive send button theming
 - **Mobile Optimization**: ChatGPT-style responsive layout (sidebar pushes content on desktop, overlays on mobile), touch gestures, swipe navigation, and mobile-optimized input
 - **Performance**: Optimized animations with 60fps performance, React.memo optimizations, and efficient React patterns
 - **Testing**: Comprehensive unit test coverage (40 tests) with type-safe implementation

  ### Current Status

   - ✅ **Home Page**: Welcome page with navigation to character selection, featuring sophisticated glassmorphism theming matching the character selection interface
  - ✅ **Character Selection**: Grid browsing with search functionality and collection showcase
  - ✅ **Chat Interface**: Persona-driven conversations with LLM responses
  - ✅ **Persona Customization**: Rarity-based theming with custom backgrounds, colors, and avatar effects
  - ✅ **Session Management**: Automatic loading of recent chats or creation of new conversations
  - ✅ **Persona Switching**: Seamless switching between different persona chats
  - ✅ **Backend Integration**: FastAPI coordinator with Ollama LLM support
  - ✅ **Unified Startup**: Single command launches both backend and React UI
  - ✅ **Production Ready**: Optimized React build (162.47KB gzipped) with TypeScript safety
   - ✅ **Dynamic Persona Management**: Automatic persona discovery, session cleanup, collection synchronization, and chat history updates
   - ✅ **Phase 3 Complete**: Classic card system, audio integration, collection management, and performance optimization
   - ✅ **Advanced Features**: Pull history tracking, persistent collections, accessibility support, and mobile optimization
   - ✅ **Testing Complete**: All component tests passing, lint warnings resolved, production build verified
   - ✅ **Deployment Ready**: Final documentation updated, changelog maintained, ready for production deployment

---

## 🧩 High level Architecture

```bash
                           🧠  GraphRAG Coordinator UI
                   ╔═══════════════════════════════════════╗
                   ║          React Frontend               ║
                   ║     (Gacha-style Persona Selection)   ║
                   ╚═══════════════════════════════════════╝
                                   │  🔗  HTTP / CORS
                                   ▼
                   ╔═══════════════════════════════════════╗
                   ║         🧩 FastAPI Coordinator        ║
                   ║    (Persona router & MCP bridge)      ║
                   ╚═══════════════════════════════════════╝
                                  │
          ┌───────────────────────┼────────────────────────────┐
          ▼                       ▼                            ▼
  ╔═══════════════╗       ╔═══════════════╗            ╔═══════════════╗
  ║ 📚 RAG MCP   ║       ║ 🕸️ KG MCP     ║            ║ ⚙️ Other MCPs ║
  ║ (Chroma + LLM)║       ║ (GraphDB)     ║            ║ (Brave, Mongo)║
  ╚═══════════════╝       ╚═══════════════╝            ╚═══════════════╝
                                  │
                                  ▼
                  ╔═══════════════════════════════════════╗
                  ║ 🤖 Ollama LLM Engine (Local Models)   ║
                  ╚═══════════════════════════════════════╝
```

---

## ⚙️ System Requirements

| Component | Requirement |
|------------|-------------|
| **OS** | Windows 10 / 11 or macOS 13+ |
| **Python** | 3.11 or higher |
| **GPU (optional)** | NVIDIA RTX 30/40 series for CUDA acceleration (or Apple Silicon GPU on macOS) |
| **VRAM** | ≥ 12 GB VRAM (or unified memory on macOS) recommended |
| **Ollama** | Installed and **running** locally |
| **Node.js** | v16+ (with npm) for React UI |
| **React** | v18+ (with TypeScript) |
| **FastAPI + Uvicorn** | For Coordinator backend |
| **LangChain Ollama** | For persona LLM clients |

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
chmod +x setup.sh
./setup.sh

# Windows
setup.bat
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
# Pull the model specified in your .env file
# Default: nchapman/gemma-2-9b-it-abliterated:9b (uncensored, great for personas)
ollama pull nchapman/gemma-2-9b-it-abliterated:9b

# Alternative models:
# ollama pull dolphin-llama3:8b      # Smaller, faster (4.7GB)
# ollama pull llama3.1:latest        # More formal, censored (4.7GB)
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
python run_react.py
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

Press `Ctrl+C` in the terminal running `python run_react.py` to stop both services gracefully.

---

## 🎭 Managing Personas

### ➕ Adding a New Persona

1. **Create persona file**: Copy `personas/template.jsonc` to `personas/[name].json`
2. **Configure persona**: Edit the JSON with character details:

   ```json
   {
     "key": "your_persona",
     "display_name": "Your Persona Name",
     "style": "personality description",
     "rarity": "legendary",
     "image": "images/your_card.png",
     "avatar": "images/your_avatar.png",
     "logo": "images/your_logo.png"
   }
   ```

3. **Auto-discovery**: The new persona appears automatically in the React UI without restart
4. **Single source of truth**: All persona data is managed from the `personas/` directory

### 🗑️ Removing a Persona

1. **Delete persona file**: Remove the JSON file from `/personas/` directory
2. **Automatic cleanup**: Sessions and chats for removed personas are automatically deleted from the database
3. **Collection cleanup**: Removed personas are automatically cleaned from user collections on next app load
4. **Chat history update**: The chat history panel immediately reflects the removal - orphaned chats disappear

### 🔄 Modifying a Persona

1. **Edit persona file**: Update the JSON file with new details
2. **Auto-update**: Summary is regenerated automatically on next access
3. **UI refresh**: Changes appear immediately in the React interface

### 📋 Available Personas

| Persona | Style | Rarity |
|---------|-------|--------|
| **Eeva** | Nerdy, charming, concise | ⭐⭐⭐⭐⭐ |
| **Frieren** | Wise, analytical, methodical | ⭐⭐⭐⭐⭐ |
| **Gojo** | Confident, powerful, playful | ⭐⭐⭐⭐⭐ |
| **Hitler** | Authoritative, ideological | ⭐⭐⭐⭐⭐ |
| **Itachi** | Calm, strategic, philosophical | ⭐⭐⭐⭐⭐ |

---

## 🎯 How to Use the App

### **Home Page (`/`)**

- 🎲 **Try Your Luck**: Navigate directly to the Gacha Pull section for character pulls with classic card reveals and particle effects
- 📚 **Browse All Characters**: Navigate to the character selection page to view all available characters
- 🎨 **Sophisticated Theming**: Glassmorphism background effects, animated particles, and yellow-themed buttons matching the character selection interface

### **Character Selection (`/select`)**

- 🎴 **Card Gallery**: Browse all characters with search and filtering by name, style, or rarity
- 🎲 **Gacha Pull**: Experience 1x/5x/10x pulls with sequential reveals and audio feedback
- 📚 **My Collection**: View collected characters with statistics and management
- 📊 **Pull History**: Track pulling statistics and session history
- 🎯 **Choose Characters**: Click "Choose" button on any card to jump directly to chat

### **Classic Cards Showcase (`/cards-v2`)**

- 🎴 **Card Gallery**: Browse all characters with search and filtering by name, style, or rarity
- 🎲 **Gacha Pull**: Experience 1x/5x/10x pulls with sequential reveals and audio feedback
- 📚 **My Collection**: View collected characters with statistics and management
- 📊 **Pull History**: Track pulling statistics and session history
- 🎯 **Choose Characters**: Click "Choose" button on any card to jump directly to chat

### **Chat Interface (`/chat`)**

- 💬 **Start Conversations**: Chat with your selected persona
- 🔄 **Switch Sessions**: Use sidebar to switch between chats
- 💾 **Export Chats**: Save conversations as JSON files
- 🎨 **Persistent Avatars**: Each persona has unique avatar images

---

---

## 🛡️ Security & Privacy

### Docker Deployment
- **Container Isolation**: Services run in isolated containers with minimal attack surface
- **Non-Root User**: Backend container runs as non-root user for security
- **Local Network**: Services communicate via private Docker network
- **Volume Security**: Data persists in host-mounted volumes you control
- **No External Dependencies**: All processing happens locally (except optional web search)

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

---

## 📄 License

© 2025 GraphRAG Coordinator UI – All rights reserved.

This project is provided "as is", without any warranty or guarantee. Use responsibly and at your own discretion.

---
