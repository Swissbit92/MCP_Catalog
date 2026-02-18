# MCP Coordinator Test Suite

## Overview

This directory contains all Python tests for the MCP Coordinator project. React/TypeScript tests remain colocated with components in `react-ui/src/` following Jest conventions.

## Structure

```
tests/
├── backend/              # Unit tests for Python backend
│   └── coordinator/      # FastAPI, MCP clients, tool calling
├── integration/          # End-to-end integration tests
└── exploration/          # Archived exploratory/one-time scripts
```

### Backend Unit Tests (`backend/`)

Unit tests for core backend components with mocked dependencies (18 files):

- **test_citation_service.py** - Citation generation and validation (14 tests, pytest)
- **test_mongodb_integration.py** - MongoDB MCP unit tests (30+ tests, pytest)
- **test_repositories.py** - SQLite repository layer tests
- **test_mongodb_handlers.py** - MongoDB service handler tests
- **test_llm_completion_service.py** - LLM completion service tests
- **test_persona_schema.py** - Persona schema validation tests
- And more in `tests/backend/coordinator/`

**Run backend tests:**
```bash
pytest tests/backend/ -v
```

### Integration Tests (`integration/`)

End-to-end tests with real external dependencies (~13 files):

- **test_brave_mcp_connectivity.py** - Manual Brave MCP connectivity validation
- **test_mvp2_integration.py** - Complete autonomous web search workflow
- **test_intent_classification.py** - Comprehensive intent classification (360 tests, 100% accuracy)

**Run integration tests:**
```bash
pytest tests/integration/ -v
```

**Note:** Integration tests require:
- Ollama running locally
- Brave API key (for Brave MCP tests)
- MongoDB connection (for MongoDB MCP tests)
- Docker (for MCP servers)

### Exploration Scripts (`exploration/`)

Non-test utility scripts for development inspection. Test scripts have been archived to `archive/exploration/`:

- **check_db.py** - Inspect SQLite database contents
- **check_import.py** - Verify module imports
- **explore_mongodb_direct.py** - Direct MongoDB connection exploration
- **simulate_ui_flow.py** - Simulate frontend API call sequences
- **validate_model_switch.py** - Validate model switching behavior

Archived test scripts (moved to `archive/exploration/`):
- `model_comparison_test.py`, `test_function_calling.py`, `test_model_persona_capability.py`

**Note:** `@pytest.mark.requires_ollama` is applied to integration tests that need a locally running Ollama instance (`ollama serve`). Skip them in CI with `pytest -m "not requires_ollama"`.

## Running Tests

### All Backend Tests
```bash
# Unit tests only
pytest tests/backend/ -v

# Integration tests only
pytest tests/integration/ -v

# All tests (excluding exploration)
pytest tests/ -v --ignore=tests/exploration

# With coverage
pytest tests/ --cov=src/coordinator --cov-report=html
```

### React Tests
React tests use Jest and are located in `react-ui/src/`:
```bash
cd react-ui
npm test                                    # Interactive mode
npm test -- --watchAll=false                # Single run
npm test -- --testNamePattern="MessageBubble"  # Specific test
```

## Test Conventions

### Python Tests

**Naming:**
- Test files: `test_*.py`
- Test functions: `test_*`
- Test classes: `Test*`

**Fixtures:**
- Shared fixtures in `conftest.py`
- Test-specific fixtures in test files

**Imports:**
- Use absolute imports: `from coordinator.server import app`
- conftest.py adds `src/` to path automatically

**Markers:**
- `@pytest.mark.requires_ollama` applied to tests that need Ollama running

### React Tests

**Naming:**
- Test files: `*.test.tsx` or `*.test.ts`
- Colocated with components

**Framework:**
- Jest + React Testing Library
- Run with: `npm test`

## Writing New Tests

### Backend Unit Test Example
```python
# tests/backend/coordinator/test_something.py
import pytest
from coordinator.something import my_function

def test_my_function():
    result = my_function("input")
    assert result == "expected"
```

### Integration Test Example
```python
# tests/integration/test_new_feature.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from coordinator.client import MyClient

def test_end_to_end():
    client = MyClient()
    # Test real interactions
```

## Troubleshooting

### Import Errors
If you see `ModuleNotFoundError`, ensure:
1. You're running from project root: `cd /path/to/MCP_Catalog`
2. conftest.py is present in tests/
3. src/ directory exists

### Integration Test Failures
Check:
1. Ollama is running: `ollama serve`
2. Environment variables set in `.env`
3. Docker daemon running (for MCP servers)
4. API keys configured

## Test Coverage

Current coverage (as of 2026-02-18):
- **Backend Unit Tests**: ~80% coverage (server, MCP clients, tool calling)
- **Integration Tests**: 100% accuracy on intent classification (360 tests)
- **React Tests**: 40+ component tests, comprehensive coverage

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [React Testing Library](https://testing-library.com/react)
- Project documentation in `docs/`
