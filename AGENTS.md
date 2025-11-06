# Repository Guidelines

## Project Structure & Module Organization
- `run.py` — starts the FastAPI coordinator (Uvicorn) and Streamlit UI.
- `src/coordinator` — API, model and orchestration code (`server.py`, config, LLM/Ollama utils).
- `src/shared` — shared Python modules and assets.
- `ui` — Streamlit app (`ui/app.py`) and UI helpers.
- `react-ui` — optional React/TypeScript UI (Create React App).
- `personas` — persona JSONs and `_summaries` cache; update via the app.
- `catalog` — YAML configs (e.g., `catalog/graph_rag_mcp.yaml`).
- `requirements.txt` — Python dependencies.

## Build, Test, and Development Commands
- Python env
  - Create venv: `python -m venv .venv`
  - Activate: `source .venv/bin/activate` (bash) or `.\.venv\Scripts\Activate.ps1` (PowerShell)
  - Install deps: `pip install -r requirements.txt`
- Run full app (requires Ollama running):
  - Set env: `$env:OLLAMA_BASE="http://localhost:11434"; $env:PERSONA_MODEL="llama3"`
  - Start: `python run.py`
- Run parts separately
  - API only: `uvicorn src.coordinator.server:app --reload --port 8000`
  - Streamlit UI only: `streamlit run ui/app.py`
- React UI
  - `cd react-ui && npm install`
  - Dev server: `npm start`  • Tests: `npm test`  • Build: `npm run build`

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indent, type hints where practical. Modules/functions `snake_case`; classes `PascalCase`. Keep files small and cohesive.
- React/TS: Components and files `PascalCase` (`ChatMessage.tsx`), hooks `useThing.ts`. Prefer explicit types and module-local utilities.
- Config/paths: Do not change directory names or public entrypoints without discussion (`run.py`, `src.coordinator.server:app`).

## Testing Guidelines
- React: colocated tests `*.test.tsx`/`*.test.ts` (see `react-ui/src`). Run with `npm test`.
- Python: If adding tests, prefer `pytest` with files under `tests/` named `test_*.py`. Keep unit tests fast; mock network/LLM calls.

## Commit & Pull Request Guidelines
- Commits: present tense, concise scope prefix when helpful (e.g., `ui: fix persona card overflow`). Reference issues (`#123`).
- PRs: include summary, rationale, screenshots (UI), and steps to reproduce/verify. Link issues, note config/env changes, and include test coverage for changed behavior.

## Security & Configuration Tips
- Required env: `OLLAMA_BASE`, `PERSONA_MODEL` (use a `.env`; never commit secrets).
- Ensure Ollama is running and the model is pulled: `ollama pull <model>`.
- Persona data may be user-provided; validate inputs and avoid committing sensitive content.

