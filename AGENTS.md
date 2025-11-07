# Agent Coding Guidelines

## Build/Test Commands
- **Python**: `pip install -r requirements.txt` • API: `uvicorn src.coordinator.server:app --reload --port 8000`
- **React**: `cd react-ui && npm install` • Dev: `npm start` • Build: `npm run build` • Test: `npm test`
- **Single test**: React: `npm test -- --testNamePattern="test name"` • Python: `python -m pytest tests/test_file.py::test_function`
- **Full app**: Set env vars, then `python run.py` (requires Ollama)

## Code Style Guidelines
- **Python**: PEP 8, 4-space indent, type hints. `snake_case` functions/modules, `PascalCase` classes. Relative imports.
- **React/TS**: `PascalCase` components, explicit TS types. Hooks: `useThing`. Module-local utilities.
- **Imports**: Group stdlib → third-party → local. No wildcards.
- **Error handling**: FastAPI: `HTTPException`. React: try/catch with user messages.
- **Formatting**: 4-space Python, consistent TS/JS. No semicolons in TS. Prefer async/await.
- **Naming**: Descriptive. Booleans: `isSelected`, `hasError`. Events: `onClick`, `handleSubmit`.

## Testing Guidelines
- **React**: Jest + RTL, `*.test.tsx` colocated. Mock APIs, test interactions.
- **Python**: pytest in `tests/`, `test_*.py`. Mock LLM/network. Fast unit tests.
- **Coverage**: Critical paths. Mock Ollama/APIs.

## Security & Best Practices
- Validate inputs with Pydantic. Never commit secrets; use `.env`.
- Handle errors gracefully; log without exposing sensitive info.
