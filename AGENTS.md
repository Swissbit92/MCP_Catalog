# Agent Coding Guidelines

## Tech Stack
Backend: Python 3.8+, FastAPI, Pydantic, SQLite, Ollama. Frontend: React 19, TypeScript 4.9.5, Tailwind CSS, Framer Motion.

## Build/Test Commands
- Setup: `./setup.sh` (Linux/macOS) or `setup.bat` (Windows). Manual: `pip install -r requirements.txt && cd react-ui && npm install`
- Python API: `uvicorn src.coordinator.server:app --reload --port 8000`
- React Dev: `cd react-ui && npm run start:dev`. Build: `npm run build` (includes ESLint). Lint: `npm run build` (ESLint integrated)
- Single test: `cd react-ui && npm test -- --testNamePattern="test name"`
- Full app: Set env vars, then `python run.py` + `cd react-ui && npm run start:dev` (requires Ollama)

## Code Style Guidelines
- **Python**: PEP 8, 4-space indent, type hints. `snake_case` functions/modules, `PascalCase` classes. Relative imports.
- **React/TS**: `PascalCase` components, explicit TS types, strict mode. Hooks: `useThing`. Absolute imports. Functional components with hooks.
- **Imports**: Group stdlib → third-party → local. No wildcards.
- **Error handling**: FastAPI uses `HTTPException`. React uses try/catch with user messages.
- **Formatting**: 4-space Python, consistent TS/JS. No semicolons in TS. Prefer async/await.
- **Naming**: Descriptive names. Booleans: `isSelected`, `hasError`. Events: `onClick`, `handleSubmit`.
- **Layout**: `h-screen flex flex-col` with Header and `flex-1 overflow-hidden` content. CSS modules for components, Tailwind for utilities.

## Testing & Security
- **React**: Jest + RTL, `*.test.tsx` colocated. Mock APIs, test interactions.
- **Python**: No tests implemented. Mock Ollama/APIs for critical paths.
- **Security**: Validate with Pydantic. Never commit secrets; use `.env`. Handle errors gracefully without exposing sensitive info.
