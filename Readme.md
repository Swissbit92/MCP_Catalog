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
                     ┌────────────────────────────┐
                     │        Streamlit UI        │
                     │ (GraphRAG Coordinator Chat) │
                     └──────────────┬─────────────┘
                                    │  (HTTP API)
                                    ▼
                     ┌────────────────────────────┐
                     │      FastAPI Coordinator   │
                     │  /persona, /chat, /tools   │
                     └──────────────┬─────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌────────────────┐       ┌────────────────┐         ┌────────────────┐
│   RAG MCP      │       │   KG MCP       │         │  Other MCPs    │
│ (Chroma, LLM)  │       │ (GraphDB)      │         │ (Brave, Mongo) │
└────────────────┘       └────────────────┘         └────────────────┘
                                    │
                                    ▼
                     ┌────────────────────────────┐
                     │        Ollama LLM          │
                     │ (Local inference engine)   │
                     └────────────────────────────┘

   ```

---

## ⚙️ System Requirements

| Component | Requirement |
|------------|-------------|
| **OS** | Windows 10 / 11 or macOS 13+ |
| **Python** | 3.11 or higher |
| **GPU (optional)** | NVIDIA RTX 30/40 series for CUDA acceleration (or Apple Silicon GPU on macOS) |
| **RAM** | ≥ 16 GB recommended |
| **Ollama** | Installed and running locally |
| **Streamlit** | v1.35+ |
| **FastAPI + Uvicorn** | For Coordinator backend |
| **LangChain Ollama** | For persona LLM clients |

---

## 🧩 Installation

### 1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/graph_rag_coordinator_ui.git
   cd graph_rag_coordinator_ui
Create a virtual environment
   ```

   ```bash
python -m venv venv
source venv/bin/activate     # (macOS / Linux)
venv\Scripts\activate        # (Windows)
   ```

### 2. **Install dependencies**

   ```bash
pip install -r requirements.txt
   ```

### 3. **Create a .env file**

### 4. **Example .env file**

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

---

**The script will:**

- Launch the FastAPI Coordinator (backend)
- Open the Streamlit UI (http://localhost:8501)
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
