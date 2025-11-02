# 🧠 MCP Coordinator - Persona Chat Interface (Chat only for now)

> **Local Persona-Driven Chat Interface for GraphRAG & MCP Servers**  
> _Private • Local-First • Streamlit-Based Coordinator_

---

## 📖 Overview

The **GraphRAG Coordinator UI** provides a local chat interface for interacting with multiple MCP (Modular Computation Process) servers — such as `rag`, `kg`, and others — through a **persona-driven** experience.

It runs entirely **locally**, connects to a **FastAPI Coordinator** (the backend), and communicates with **Ollama** for local LLM inference.  
Personas such as **Eeva**, **Cindy**, and others can be selected via an interactive card-based interface.  
The chat interface is responsive, centered, and styled like a modern messaging app.

---

## 🧩 High level Architecture

   ```bash
                         🧠  GraphRAG Coordinator UI
                 ╔═══════════════════════════════════════╗
                 ║          Streamlit Frontend           ║
                 ║     (Persona-driven Chat Interface)   ║
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
| **VRAM** | ≥ 16 GB VRAM (or unified memory on macOS or) recommended |
| **Ollama** | Installed and **running** locally |
| **Streamlit** | v1.35+ |
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

   ```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
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
python run.py
   ```

### **Stop the Coordinator + UI**

CTRL + C in the terminal to stop.

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

- Launch the FastAPI Coordinator (backend)
- Open the Streamlit UI ([http://localhost:8501](http://localhost:8501))
- Verify the local Ollama model is available

### 1. In the UI

- Go to the Characters tab → choose a persona
- Switch to the Chat tab → start chatting

### 2. Use the toolbar

| Button | Function |
|------------|-------------|
| 🧹 | **Clear Chat** |
| 📥 | **Export conversation** (JSON) |

⚠️ Disclaimer
This project is a local experimental prototype.
It is provided “as is”, without any warranty or guarantee.
All LLM interactions run locally via Ollama — no data leaves your device.
Use responsibly and at your own discretion.

© 2025 GraphRAG Coordinator UI – All rights reserved.

---
