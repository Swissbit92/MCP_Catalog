# Agent Coding Guidelines

## Build/Test Commands
- **Setup**: `./setup.sh` (Linux/macOS) or `setup.bat` (Windows)` • Manual: `pip install -r requirements.txt && cd react-ui && npm install`
- **Python API**: `uvicorn src.coordinator.server:app --reload --port 8000`
- **React Dev**: `cd react-ui && npm start` • **Build**: `npm run build` (includes ESLint)
- **Lint**: `cd react-ui && npm run build` (ESLint via build) • Python: No linter
- **Single test**: `cd react-ui && npm test -- --testNamePattern="test name"` • Python: No tests
- **Full app**: Set env vars, then `python run.py` + `cd react-ui && npm start` (requires Ollama)

## Code Style Guidelines
- **Python**: PEP 8, 4-space indent, type hints. `snake_case` functions/modules, `PascalCase` classes. Relative imports.
- **React/TS**: `PascalCase` components, explicit TS types. Hooks: `useThing`. Module-local utilities.
- **Imports**: Group stdlib → third-party → local. No wildcards.
- **Error handling**: FastAPI: `HTTPException`. React: try/catch with user messages.
- **Formatting**: 4-space Python, consistent TS/JS. No semicolons in TS. Prefer async/await.
- **Naming**: Descriptive. Booleans: `isSelected`, `hasError`. Events: `onClick`, `handleSubmit`.
- **Layout**: App uses `h-screen flex flex-col` with Header and `flex-1 overflow-hidden` content area. Chat pages use `h-full` to fit remaining space without scrolling.

## Testing Guidelines
- **React**: Jest + RTL, `*.test.tsx` colocated. Mock APIs, test interactions.
- **Python**: No tests implemented. **Coverage**: Critical paths. Mock Ollama/APIs.

## Security & Best Practices
- Validate inputs with Pydantic. Never commit secrets; use `.env`.
- Handle errors gracefully; log without exposing sensitive info.
