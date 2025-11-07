# 🧠 MCP Coordinator - Persona Chat Interface (Chat only for now)

> **Local Persona-Driven Chat Interface for GraphRAG & MCP Servers**  
> _Private • Local-First • Streamlit-Based Coordinator_

  ---

## Contributing & Guidelines
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
The chat interface is responsive, centered, and styled like a modern messaging app.

### Current Status
- ✅ **Home Page**: Gacha-style character pulls with card reveal animations
- ✅ **Character Selection**: Grid browsing with search functionality
- ✅ **Chat Interface**: Persona-driven conversations
- ✅ **Backend Integration**: FastAPI coordinator with Ollama LLM support
- ✅ **Production Ready**: Optimized React build (116KB gzipped)

---

## 🧩 High level Architecture

    ```bash
                          🧠  GraphRAG Coordinator UI
                  ╔═══════════════════════════════════════╗
                  ║          React Frontend               ║
                  ║     (Gacha-style Persona Selection)   ║
                  ╚═══════════════════════════════════════╝
                                  │  🔗  HTTP / WebSocket
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
| **React** | v18+ (with TypeScript) |
| **FastAPI + Uvicorn** | For Coordinator backend |
| **LangChain Ollama** | For persona LLM clients |

---

## 🧩 Installation

### 1. **Clone the repository**

   ```bash
git clone https://github.com/Swissbit92/MCP_Catalog.git
   ```

### 2. **Create a virtual environment**

**macOS / Linux:**

   ```bash
python3.11 -m venv MCP_Catalog
# Activate the virtual environment
cd MCP_Catalog
source venv/bin/activate
   ```

**Windows Powershell:**

   ```bash
py -3.11 -m venv MCP_Catalog
# Activate the virtual environment
cd MCP_Catalog
.//scripts/activate
   ```

### 3. **Install dependencies**

    **Option A: Manual installation**
    ```bash
    # Python dependencies
    python -m pip install --upgrade pip
    pip install -r requirements.txt

    # React dependencies
    cd react-ui && npm install && cd ..
    ```

    **Option B: Automated setup**
    ```bash
    # Linux/macOS
    chmod +x setup.sh
    ./setup.sh

    # Windows
    setup.bat
    ```

### 4. **Create a .env file**

#### Example .env file

   ```bash
COORD_PORT=8000
COORD_URL=http://127.0.0.1:8000
OLLAMA_BASE=http://127.0.0.1:11434
PERSONA_MODEL=llama3.1:latest
PERSONA_DIR=personas
   ```

---

## 🚀 **Usage**

### **Start the Coordinator + UI**

    ```bash
# Start the backend coordinator
python run.py

# In a separate terminal, start the React UI
cd react-ui && npm start
    ```

### **Stop the Coordinator + UI**

CTRL + C in both terminals to stop.

---

## **How to Add & Remove Persona**

### 🪄 **To ADD a new persona:**

- Place a new [NAME].json file in /personas directory (e.g. personas/gojo.json) and restart the app — it auto-detects and loads the persona card.
- with keys: key, emoji, rarity, style, welcome, do[], dont[], and optional lore or few_shot examples.
- Use the template in /personas/template.jsonc as a starting point.
  
### 🗑️ **To REMOVE a persona:**

- Delete its corresponding JSON file (e.g. personas/gojo.json)
- and restart the app — it will be automatically removed from the Characters tab.

---

## **The script will:**

- Launch the FastAPI Coordinator (backend) on port 8000
- Verify the local Ollama model is available

### 1. Start the React UI

In a separate terminal:
```bash
cd react-ui && npm start
```
This opens the React UI at [http://localhost:3000](http://localhost:3000)

### 2. In the UI

- **Home Page (/)**: "Ready to Pull?" interface with options to pull a random character or browse the collection
- **Character Selection (/select)**: Grid view of all available characters with search functionality
- **Chat (/chat)**: Chat interface with your selected persona

### 2. Use the interface

- **Pull Character**: Click "🎯 Pull Character" on the home page for exciting random reveals with card animations
- **Pull Again**: After a successful pull, use "🔄 Pull Again" to immediately pull another character
- **Browse Collection**: Click "📚 Browse Collection" to view all characters in a searchable grid
- **Start Chat**: Click "💬 Start Chat" after selecting any character to begin chatting

⚠️ Disclaimer
This project is a local experimental prototype.
It is provided “as is”, without any warranty or guarantee.
All LLM interactions run locally via Ollama — no data leaves your device.
Use responsibly and at your own discretion.

© 2025 GraphRAG Coordinator UI – All rights reserved.

---
