# 🧠 MCP Coordinator - Persona Chat Interface

> **Local Persona-Driven Chat Interface for GraphRAG & MCP Servers**
> _Private • Local-First • React + FastAPI Coordinator_

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-18+-61dafb.svg)](https://reactjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com)
[![Ollama](https://img.shields.io/badge/Ollama-Latest-orange.svg)](https://ollama.ai)

**🚀 One-Command Setup • 🎭 Multiple Personas • 💬 Persistent Chat**

[Quick Start](#-quick-start) • [Installation](#-installation) • [Usage](#-usage)

</div>

---

## 📋 Table of Contents
- [✨ Features](#-features)
- [🔧 System Requirements](#-system-requirements)
- [⚡ Quick Start](#-quick-start)
- [🧩 Installation](#-installation)
- [🚀 Usage](#-usage)
- [🎭 Managing Personas](#-managing-personas)
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
| 🤖 **AI-Powered** | Powered by Ollama LLM models |
| 🔄 **Dynamic Persona Management** | Automatic persona discovery, orphaned session cleanup, collection synchronization, and chat history updates |

## 🔧 System Requirements

| Component | Requirement | Installation |
|-----------|-------------|--------------|
| **OS** | Windows 10/11 or macOS 13+ | - |
| **Python** | 3.11 or higher | [python.org](https://python.org) |
| **Node.js** | v16+ with npm | [nodejs.org](https://nodejs.org) |
| **Ollama** | Latest version | [ollama.ai](https://ollama.ai) |
| **GPU** | NVIDIA RTX 30/40 series (optional) | For CUDA acceleration |
| **VRAM** | ≥ 12 GB (recommended) | For optimal performance |

## ⚡ Quick Start

> **Prerequisites**: Python 3.11+, Node.js 16+, and Ollama installed

```bash
# 1. Clone and setup
git clone https://github.com/Swissbit92/MCP_Catalog.git
cd MCP_Catalog
./setup.sh  # Linux/macOS (includes npm install)
# or
setup.bat   # Windows (includes npm install)

# 2. Configure environment
cp .env.example .env  # Edit with your settings

# 3. Start Ollama and pull model
ollama serve &  # In background
ollama pull llama3.1:latest

# 4. Launch the app
python run_react.py
```

**🎉 That's it!** Your app will be running at `http://localhost:3000`

> **Note**: The setup script automatically installs both Python and React dependencies. If you prefer manual setup, run `pip install -r requirements.txt && cd react-ui && npm install`.

## 🤝 Contributing

See Repository Guidelines in `AGENTS.md` for:
- Project structure overview and entrypoints
- Setup and run commands (Python, FastAPI, React)
- Coding style and test conventions
- Commit/PR expectations and environment variables

See `CHANGELOG.md` for recent updates and project evolution.

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

## 🧩 Installation

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
# Python dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# React dependencies
cd react-ui && npm install && cd ..
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
# Pull the Llama 3.1 model (required for chat)
ollama pull llama3.1:latest
```

### ⚙️ Step 4: Configure Environment

Create a `.env` file in the root directory:

```bash
# Copy and edit this configuration
COORD_PORT=8000
COORD_URL=http://127.0.0.1:8000
OLLAMA_BASE=http://127.0.0.1:11434
PERSONA_MODEL=llama3.1:latest
PERSONA_DIR=personas
```

**Environment Variables:**
- `COORD_PORT`: Port for the FastAPI backend (default: 8000)
- `OLLAMA_BASE`: Ollama API endpoint (default: http://127.0.0.1:11434)
- `PERSONA_MODEL`: LLM model to use (default: llama3.1:latest)

---

## 🚀 Usage

### ▶️ Starting the Application

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

### 🛑 Stopping the Application
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
     "image": "ui/images/your_card.png",
     "avatar": "ui/images/your_avatar.png",
     "logo": "ui/images/your_logo.png"
   }
   ```
3. **Auto-discovery**: The new persona appears automatically in the React UI without restart
4. **Summary generation**: CV-style summary is auto-generated on first access

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

## **The run_react.py script will:**

- Check that Node.js and npm are installed
- Launch the FastAPI Coordinator (backend) on port 8000
- Launch the React UI (frontend) on port 3000
- Verify the local Ollama model is available
- Handle graceful shutdown of both services

---

## ⚠️ Important Notes

- **Local AI Only**: All conversations run locally via Ollama - no data leaves your device
- **GPU Recommended**: For best performance, use a GPU with ≥12GB VRAM
- **First Launch**: Initial model loading may take a few minutes
- **Experimental**: This is a prototype - use responsibly

---

## 📄 License

© 2025 GraphRAG Coordinator UI – All rights reserved.

This project is provided "as is", without any warranty or guarantee. Use responsibly and at your own discretion.

---
