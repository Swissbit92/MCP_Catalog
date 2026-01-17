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
├── backend/                 # Backend unit tests
│   └── coordinator/
│       ├── test_server.py
│       ├── test_mcp_client.py
│       ├── test_repositories.py
│       └── ...
├── integration/             # Integration tests
│   ├── test_brave_mcp_connectivity.py
│   └── test_phase2_integration.py
├── e2e/                     # End-to-end tests
│   └── test_phase1_conversational_flow.py
├── evaluation/              # RAGAS evaluation tests
│   ├── test_persona_quality.py
│   └── test_metrics.py
└── exploration/             # Exploratory tests (skipped in CI)
    └── explore_mongodb_direct.py
```

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
| `@pytest.mark.requires_ollama` | Manual | Needs Ollama running |

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

## Running Tests in CI

Tests run automatically on every push via GitHub Actions:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    pytest -v --cov --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

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

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Best Practices](https://docs.pytest.org/en/latest/goodpractices.html)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Testing FastAPI](https://fastapi.tiangolo.com/tutorial/testing/)

---

**Last Updated:** January 17, 2026
**Status:** Pytest infrastructure complete, migration in progress
