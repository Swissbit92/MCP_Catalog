# AI Agent Coding Guidelines

> **Purpose**: Guidelines for AI assistants (Claude, Gemini, etc.) working with this codebase.

## Project Overview

**MCP Coordinator** is a local, persona-driven chat interface for interacting with GraphRAG and other MCP (Modular Computation Process) servers. It features:
- **Backend**: Python + FastAPI + Ollama for local LLM inference
- **Frontend**: React 19 + TypeScript with gacha-style character selection
- **Architecture**: Modular design with persona-based routing and MCP integration
- **Key Features**: Advanced gacha system, persistent chat, character collection, web search (Brave MCP), Bitcoin data queries (MongoDB MCP)

### Project Structure

- `run_react.py` - Main entry point (starts both backend and frontend)
- `src/coordinator/server.py` - FastAPI backend with chat, sessions, persona management
- `react-ui/` - React frontend with modern UI and animations
- `personas/` - JSON persona definitions (auto-discovered)
- `requirements.txt` - Python dependencies

## Tech Stack
Backend: Python 3.8+, FastAPI, Pydantic, SQLite, Ollama. Frontend: React 19, TypeScript 4.9.5, Tailwind CSS, Framer Motion.

## Build/Test Commands
- Setup: `./setup.sh` (Linux/macOS) or `setup.bat` (Windows). Manual: `pip install -r requirements.txt && cd react-ui && npm install`
- Python API: `uvicorn src.coordinator.server:app --reload --port 8000`
- React Dev: `cd react-ui && npm run start:dev`. Build: `cd react-ui && npm run build` (includes ESLint)
- Single test: `cd react-ui && npm test -- --testNamePattern="test name" --watchAll=false`
- Full app: Set env vars, then `python run.py` + `cd react-ui && npm run start:dev` (requires Ollama)

## Code Style Guidelines
- **Python**: PEP 8, 4-space indent, type hints. `snake_case` functions/modules, `PascalCase` classes. Relative imports from parent dirs.
- **React/TS**: `PascalCase` components, explicit TS types, strict mode. Hooks: `useThing`. Functional components. No semicolons.
- **Imports**: Group stdlib → third-party → local. No wildcards. Use absolute imports in React, relative in Python.
- **Error handling**: FastAPI uses `HTTPException`. React uses try/catch with user messages.
- **Formatting**: 4-space Python, consistent TS/JS. Prefer async/await. Use `from __future__ import annotations` in Python.
- **Naming**: Descriptive names. Booleans: `isSelected`, `hasError`. Events: `onClick`, `handleSubmit`.
- **Layout**: `h-screen flex flex-col` with Header and `flex-1 overflow-hidden` content. CSS modules for components, Tailwind for utilities.

## Testing & Security
- **React**: Jest + RTL, `*.test.tsx` colocated. Mock APIs, test interactions. Use `--watchAll=false` for CI.
- **Python**: No tests implemented. Mock Ollama/APIs for critical paths.
- **Security**: Validate with Pydantic. Never commit secrets; use `.env`. Handle errors gracefully without exposing sensitive info.
- **Known Issues**: React-scripts 5.0.1 has 2 moderate npm audit vulnerabilities in nested dev dependencies. Fixed high-severity issues via package overrides. These don't affect production builds.

## Development Conventions

- **Architecture**: Modular design with clear separation between frontend and backend
- **Configuration**: All config via `.env` file (never commit secrets)
- **Personas**: JSON files in `personas/` directory - auto-discovered on startup
- **Entry Point**: `run_react.py` launches both backend and frontend together
- **UI System**: Gacha-style character selection with classic cards, audio integration, and collection management
- **Testing**: TypeScript strict mode with comprehensive Jest + React Testing Library coverage
- **Documentation**: See `AI_documentation/` for historical specs, completion summaries, and feature implementation details
