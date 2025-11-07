# Agent Coding Guidelines

## Build/Test Commands
- **Python**: `pip install -r requirements.txt` • Run API: `uvicorn src.coordinator.server:app --reload --port 8000`
- **React**: `cd react-ui && npm install` • Dev: `npm start` • Build: `npm run build` • Test: `npm test`
- **Single test**: React: `npm test -- --testNamePattern="test name"` • Python: `python -m pytest tests/test_file.py::test_function`
- **Full app**: Set env vars, then `python run.py` (requires Ollama)
- **Note**: React app uses react-scripts for simplified development workflow

## Code Style Guidelines
- **Python**: PEP 8, 4-space indent, type hints. `snake_case` functions/modules, `PascalCase` classes. Relative imports.
- **React/TS**: `PascalCase` components, explicit TypeScript types. Hooks: `useThing`. Module-local utilities.
- **Imports**: Group stdlib, then third-party, then local. No wildcard imports.
- **Error handling**: FastAPI uses `HTTPException`, React uses try/catch with user-friendly messages.
- **Formatting**: 4-space Python, consistent TS/JS. No semicolons in TS. Async/await preferred.
- **Naming**: Descriptive, consistent. Boolean props: `isSelected`, `hasError`. Events: `onClick`, `handleSubmit`.

## Testing Guidelines
- **React**: Jest + RTL, colocated `*.test.tsx` files. Mock API calls, test user interactions.
- **Python**: pytest under `tests/` dir, `test_*.py` files. Mock LLM/network calls. Fast unit tests only.
- **Coverage**: Aim for critical paths. Mock external dependencies (Ollama, APIs).

## Security & Best Practices
- Validate all inputs, especially persona data. Use Pydantic models for API validation.
- Never commit secrets or API keys. Use `.env` files.
- Handle errors gracefully, log appropriately but don't expose sensitive info.

