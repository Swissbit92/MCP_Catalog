# Testing Guide

## Overview

MCP Coordinator uses **pytest** as the primary testing framework. This guide covers test structure, running tests, writing new tests, and understanding coverage.

---

## Quick Start

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/backend/coordinator/test_server.py

# Run specific test function
pytest tests/backend/coordinator/test_server.py::TestSessionAPI::test_list_sessions
```

### Run Tests by Category

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run only tests that don't require API keys
pytest -m "not requires_api_key"
```

---

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── backend/                 # Backend unit tests (~8 files)
│   └── coordinator/
│       ├── test_server.py
│       ├── test_mcp_client.py
│       ├── test_mongodb_integration.py
│       ├── test_tool_calling.py
│       ├── test_citation_service.py
│       └── ...
├── integration/             # Integration tests (~13 files)
│   ├── test_brave_mcp_connectivity.py
│   ├── test_phase1_conversational_behavior.py
│   ├── test_phase2_multi_message_behavior.py
│   └── ...
├── evaluation/              # RAGAS evaluation tests
│   ├── test_persona_quality.py
│   └── test_metrics.py
├── manual/                 # Manual quality tests (require running backend)
│   ├── eeva_chat_test.py       # 50-question E.E.V.A. quality suite
│   └── eeva_test_results.json  # Latest test results
└── exploration/             # Utility scripts (archived; skipped in CI)
    └── check_db.py
```

> **Note:** Temporary test scripts (100-query intent classification, 50-query live API validation) were used during MCP routing development and removed after passing. See [MCP Intent Classification](#mcp-intent-classification-testing) for how to re-run these tests.

---

## Test Categories (Markers)

Tests are automatically categorized based on their location:

| Marker | Location | Purpose |
|--------|----------|---------|
| `@pytest.mark.unit` | `tests/backend/` | Fast, isolated unit tests |
| `@pytest.mark.integration` | `tests/integration/` | Tests with external dependencies |
| `@pytest.mark.e2e` | `tests/e2e/` | Full workflow tests |
| `@pytest.mark.evaluation` | `tests/evaluation/` | RAGAS quality evaluation |
| `@pytest.mark.slow` | Manual | Tests that take >5 seconds |
| `@pytest.mark.requires_api_key` | Manual | Needs BRAVE_API_KEY or similar |
| `@pytest.mark.requires_docker` | Manual | Needs Docker running |
| `@pytest.mark.requires_ollama` | Manual | Needs Ollama running locally (`ollama serve`) |

**Skip live LLM tests in CI:**
```bash
pytest tests/ -m "not requires_ollama"
```

### Using Markers

```python
import pytest

@pytest.mark.slow
@pytest.mark.requires_api_key
def test_real_brave_search():
    """Test actual Brave API search."""
    # Test code...
```

---

## Writing Tests

### Using Shared Fixtures

Shared fixtures are defined in `tests/conftest.py`:

```python
def test_with_temp_db(temp_db):
    """Test using temporary database."""
    # temp_db is a Path to a temporary SQLite file
    assert temp_db.exists() == False  # Doesn't exist until created

def test_with_mock_data(sample_messages, sample_persona):
    """Test using sample data."""
    assert len(sample_messages) == 3
    assert sample_persona["key"] == "test_persona"

def test_with_mocks(mock_mcp_client, mock_ollama_response):
    """Test with mocked dependencies."""
    result = mock_mcp_client.search_web("test query")
    assert result == []
```

### Test Structure (Arrange-Act-Assert)

```python
def test_example():
    """Test description following AAA pattern."""
    # Arrange - Set up test data and mocks
    test_data = {"key": "value"}

    # Act - Execute the code under test
    result = function_under_test(test_data)

    # Assert - Verify the result
    assert result == expected_value
```

### Parametrized Tests

```python
import pytest

@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("test", "TEST"),
])
def test_uppercase(input, expected):
    assert input.upper() == expected
```

---

## Coverage Reports

### Generate Coverage

```bash
# HTML report (opens in browser)
pytest --cov --cov-report=html
open htmlcov/index.html

# Terminal report
pytest --cov --cov-report=term-missing

# XML report (for CI)
pytest --cov --cov-report=xml
```

### Coverage Configuration

Coverage is configured in `pytest.ini`:

```ini
[coverage:run]
source = src
omit = */tests/*, */venv/*

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if __name__ == .__main__.:
```

### Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| Core (server, routes) | 80%+ | TBD |
| Services | 70%+ | TBD |
| Repositories | 75%+ | TBD |
| Overall | 60%+ | TBD |

---

## Migrating from unittest to pytest

### Before (unittest)

```python
import unittest

class TestExample(unittest.TestCase):
    def setUp(self):
        self.data = [1, 2, 3]

    def test_length(self):
        self.assertEqual(len(self.data), 3)

    def test_sum(self):
        self.assertEqual(sum(self.data), 6)

if __name__ == "__main__":
    unittest.main()
```

### After (pytest)

```python
import pytest

@pytest.fixture
def data():
    return [1, 2, 3]

def test_length(data):
    assert len(data) == 3

def test_sum(data):
    assert sum(data) == 6
```

### Key Differences

| unittest | pytest |
|----------|--------|
| `self.assertEqual(a, b)` | `assert a == b` |
| `self.assertTrue(x)` | `assert x` |
| `self.assertRaises(Exception)` | `with pytest.raises(Exception):` |
| `setUp()` method | `@pytest.fixture` |
| Test classes | Optional (use functions) |
| `if __name__ == "__main__"` | Not needed |

**Note:** pytest can run unittest tests without modification! Migration is gradual and optional.

---

## Best Practices

### 1. Test Naming

```python
# Good: Descriptive, specific
def test_create_session_returns_valid_session_id():
    ...

# Bad: Vague, unclear
def test_session():
    ...
```

### 2. One Assertion Per Test (Usually)

```python
# Good: Focused, easy to debug
def test_user_creation_generates_id():
    user = create_user("test@example.com")
    assert user.id is not None

def test_user_creation_sets_email():
    user = create_user("test@example.com")
    assert user.email == "test@example.com"

# Acceptable: Multiple assertions for same concept
def test_user_creation():
    user = create_user("test@example.com")
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.created_at is not None
```

### 3. Use Fixtures for Setup

```python
# Good: Reusable fixture
@pytest.fixture
def mock_database():
    db = MockDatabase()
    db.connect()
    yield db
    db.disconnect()

def test_query(mock_database):
    result = mock_database.query("SELECT * FROM users")
    assert len(result) == 0

# Bad: Setup in every test
def test_query_bad():
    db = MockDatabase()
    db.connect()
    result = db.query("SELECT * FROM users")
    db.disconnect()
    assert len(result) == 0
```

### 4. Mock External Dependencies

```python
from unittest.mock import patch, Mock

@patch('coordinator.mcp_client_stdio.subprocess.Popen')
def test_mcp_search(mock_popen):
    """Test MCP search without spawning real Docker containers."""
    mock_process = Mock()
    mock_process.communicate.return_value = ('{"result": []}', '')
    mock_process.returncode = 0
    mock_popen.return_value = mock_process

    # Test code that uses subprocess
    result = search_web("test query")
    assert result == []
```

### 5. Test Edge Cases

```python
def test_divide_normal_case():
    assert divide(10, 2) == 5

def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)

def test_divide_negative_numbers():
    assert divide(-10, 2) == -5

def test_divide_floats():
    assert divide(10.0, 3.0) == pytest.approx(3.333, rel=1e-3)
```

---

## Troubleshooting

### Tests Not Found

```bash
# Check test discovery
pytest --collect-only

# Verify naming (must start with test_)
# Files: test_*.py or *_test.py
# Functions: test_*
# Classes: Test*
```

### Import Errors

```bash
# Ensure src/ is in path (done by conftest.py)
# Or install package in editable mode:
pip install -e .
```

### Slow Tests

```bash
# Show slowest 10 tests
pytest --durations=10

# Run in parallel (requires pytest-xdist)
pytest -n auto
```

### Coverage Too Low

```bash
# See which lines aren't covered
pytest --cov --cov-report=term-missing

# Focus on specific module
pytest --cov=src.coordinator.server --cov-report=term-missing
```

---

## Manual Quality Tests

### E.E.V.A. Chat Quality Suite

**File:** `tests/manual/eeva_chat_test.py`
**Results:** `tests/manual/eeva_test_results.json`

A 50-question automated test suite that exercises E.E.V.A.'s chat capabilities across 11 categories via the session-based chat API. Requires a running backend on port 8000.

```bash
# Start backend first
python -m uvicorn src.coordinator.server:app --reload --port 8000

# Run the test suite
python tests/manual/eeva_chat_test.py
```

#### Test Categories (11)

| Category | Questions | Tests |
|----------|-----------|-------|
| IDENTITY | 6 | Persona consistency, first-person voice, lore knowledge |
| WALLET_EMPTY | 5 | Correct responses when user has no wallet |
| WALLET_CREATE | 4 | Multi-turn wallet creation flow (name → password → recovery → confirm) |
| WALLET_META | 7 | Wallet state queries after creation (address, name, balance, count) |
| FOLLOWUP | 4 | Follow-up detection ("yes", "sure", "go ahead" after wallet context) |
| CONTEXT | 5 | Topic switching and context retention across turns |
| ANTI_HALLUC | 8 | Anti-hallucination stress tests (fabricated data, tool name leaking, private keys) |
| JUPITER | 3 | Jupiter DEX disambiguation (not Jupyter notebooks) |
| WALLET_DELETE | 1 | Wallet deletion flow |
| WALLET_POST_DEL | 4 | Post-deletion state consistency |
| SECURITY | 3 | Private key refusal, seed phrase security |

#### Output

The suite produces:
- Per-question console output with source routing and timing
- JSON results file with full answers, latencies, and source types
- Source distribution summary (llm, wallet_state, brave_mcp, error)
- Category summary with average response times and error counts

#### What to Look For

- **Zero errors**: All 50 questions should get responses (no HTTP failures)
- **No brave_mcp misroutes**: Wallet queries should never route to web search
- **Wallet flow continuity**: Steps 1-4 of wallet creation should complete in sequence
- **Anti-hallucination**: No fabricated addresses, balances, or tool names in responses
- **Jupiter = DEX**: Jupiter questions should reference the Solana DEX, not Jupyter notebooks

---

## MCP Intent Classification Testing

The MCP query routing pipeline (`tools/intent_classifier.py` + `tools/keywords.py`) determines which MCP service handles each user query. After fixing Brave MCP force-search and multiple intent classification bugs (Feb 2026), the system was validated with:

- **100-query offline intent classification test**: Tests `classify_query_intent()` directly across all categories (45 Brave, 20 MongoDB, 5 Wallet, 30 LLM) with multiple persona configurations (E.E.V.A./Archon, Cipher/Sage, Wanderer/no-MCP). **Result: 100/100 PASS.**
- **50-query live API test**: End-to-end HTTP tests against running Docker backend (28 Brave, 10 MongoDB, 12 LLM). **Result: 50/50 PASS, avg 5.9s/query.**

### Quick Intent Classification Test

To verify intent classification is working correctly:

```python
# Quick smoke test (run from project root)
from src.coordinator.tools.intent_classifier import classify_query_intent

# These should return the expected intents:
assert classify_query_intent("What is the weather in London?", "legendary", ["brave_search", "mongodb"]).value == "web"
assert classify_query_intent("What is Bitcoin's price?", "legendary", ["brave_search", "mongodb"]).value == "mongodb"
assert classify_query_intent("What is the capital of France?", "legendary", ["brave_search", "mongodb"]).value == "llm"
assert classify_query_intent("Create a wallet", "legendary", ["brave_search", "mongodb", "solana_wallet"]).value == "wallet"
assert classify_query_intent("Weather in London?", "common", None).value == "llm"  # Wanderer: no MCP access
print("All intent classification checks passed!")
```

### Key Fixes Applied (Feb 2026)

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Brave MCP never executing | LLM (Gemma 9B) unreliable at generating JSON tool calls | Force-execute Brave search when keyword filter detects search intent (`tool_calling_service.py`) |
| "US elections" routed to wallet | Generic `"what happened"` in wallet keywords matched non-wallet queries | Changed to wallet-context-specific phrases: `"happened to my wallet"` |
| Bitcoin technical analysis routed to LLM | `"what does"` triggered educational filter; `"analysis"` not in data_keywords | Added `and not has_data_intent` to educational filter; added `"analysis"`, `"rsi"`, `"macd"` to data_keywords |
| "Trading summary" routed to LLM | `"trading summary"` not in MongoDB keywords | Added `"trading summary"`, `"summary"` to `MONGODB_TRADING_KEYWORDS` |
| "Tomorrow" queries not searching | `"tomorrow"` missing from search keywords | Added `"tomorrow"`, `"2026"` to `SEARCH_KEYWORDS` |
| Analyst opinion queries not searching | No web search fallback for opinion-intent queries | Added opinion intent fallback in web search block; added `"analysts think"`, `"analysts"` to `SEARCH_KEYWORDS` |

---

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Best Practices](https://docs.pytest.org/en/latest/goodpractices.html)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Testing FastAPI](https://fastapi.tiangolo.com/tutorial/testing/)

---

**Last Updated:** February 21, 2026
**Status:** Pytest infrastructure complete. Exploration scripts archived to `archive/exploration/`. Manual E.E.V.A. quality suite added (50 questions, 11 categories). MCP intent classification validated (100/100 offline, 50/50 live API).
