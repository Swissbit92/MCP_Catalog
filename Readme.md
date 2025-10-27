# GraphRAG Coordinator UI (Chat-only)

Local Streamlit QA chatbot with personas (Eeva, Cindy). Built on LangChain + Ollama.
MCP-ready: later add tool routing to call your dockerized rag/kg MCPs.

## Quick start

```bash
# 1) Create and activate venv (Windows PowerShell)
python -m venv .venv
. .venv/Scripts/Activate.ps1

# 2) Install deps
pip install -r requirements.txt

# 3) Configure environment
copy .env.example .env
# ensure OLLAMA_BASE and PERSONA_MODEL exist locally:
#   ollama pull llama3.1:8b

# 4) Run Coordinator (FastAPI)
uvicorn src.coordinator.server:app --reload --port 8000

# 5) In another terminal, run the UI
streamlit run ui/app.py