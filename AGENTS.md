# Agent Coding Guidelines

## Build/Test Commands
- **Setup**: `./setup.sh` (Linux/macOS) or `setup.bat` (Windows) • Manual: `pip install -r requirements.txt && cd react-ui && npm install`
- **Python API**: `uvicorn src.coordinator.server:app --reload --port 8000`
- **React Dev**: `cd react-ui && npm start` • **Build**: `npm run build` (includes ESLint)
- **Single test**: `cd react-ui && npm test -- --testNamePattern="test name"` • Python: No tests
- **Full app**: Set env vars, then `python run.py` + `cd react-ui && npm start` (requires Ollama)

## Code Style Guidelines
- **Python**: PEP 8, 4-space indent, type hints. `snake_case` functions/modules, `PascalCase` classes. Relative imports.
- **React/TS**: `PascalCase` components, explicit TS types. Hooks: `useThing`. Module-local utilities.
- **Imports**: Group stdlib → third-party → local. No wildcards.
- **Error handling**: FastAPI: `HTTPException`. React: try/catch with user messages.
- **Formatting**: 4-space Python, consistent TS/JS. No semicolons in TS. Prefer async/await.
- **Naming**: Descriptive. Booleans: `isSelected`, `hasError`. Events: `onClick`, `handleSubmit`.

## Testing Guidelines
- **React**: Jest + RTL, `*.test.tsx` colocated. Mock APIs, test interactions.
- **Python**: No tests implemented. **Coverage**: Critical paths. Mock Ollama/APIs.

## Security & Best Practices
- Validate inputs with Pydantic. Never commit secrets; use `.env`.
- Handle errors gracefully; log without exposing sensitive info.

## Chat System Implementation

### Session Management
- **Automatic Session Loading**: Character selection automatically loads the most recent chat for that persona
- **New Session Creation**: Creates new chat sessions with personalized greetings when no existing chats exist
- **Session Switching**: Seamless switching between different persona conversations via sidebar
- **Persistent Storage**: All messages and sessions saved to backend database

### Persona Integration
- **Dynamic Greetings**: API-generated greetings instead of static text
- **Persona Context**: Each chat maintains persona-specific context and behavior
- **Key-Based Mapping**: Uses persona `key` field for consistent session identification
- **Avatar Support**: Persona images displayed in chat interface

### UI/UX Features
- **Responsive Design**: Works on desktop and mobile devices
- **Loading States**: Proper feedback during API calls and session loading
- **Error Handling**: Graceful error recovery for failed requests
- **Export Functionality**: Save chat transcripts as JSON files
