"""Shared pytest fixtures and configuration for MCP Coordinator tests."""
import sys
import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, MagicMock
import pytest

# Add src to path for all tests
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

# This allows imports like: from coordinator.server import app


# ============================================================================
# Environment Configuration
# ============================================================================

@pytest.fixture(scope="session")
def test_env():
    """Set up test environment variables."""
    os.environ.setdefault("OLLAMA_BASE", "http://localhost:11434")
    os.environ.setdefault("PERSONA_MODEL", "test-model")
    os.environ.setdefault("PERSONA_TEMPERATURE", "0.7")
    os.environ.setdefault("COORD_PORT", "8000")
    return os.environ


# ============================================================================
# Temporary Resources
# ============================================================================

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_db(temp_dir) -> Generator[Path, None, None]:
    """Provide a temporary SQLite database."""
    db_path = temp_dir / "test.db"
    yield db_path
    # Cleanup happens automatically via temp_dir


# ============================================================================
# Mock Objects
# ============================================================================

@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response."""
    return {
        "model": "test-model",
        "created_at": "2026-01-17T10:00:00Z",
        "response": "This is a test response from the mock LLM.",
        "done": True
    }


@pytest.fixture
def mock_search_results():
    """Mock Brave search results."""
    return [
        {
            "title": "Test Result 1",
            "url": "https://example.com/1",
            "description": "First test result",
            "age": "1 day ago"
        },
        {
            "title": "Test Result 2",
            "url": "https://example.com/2",
            "description": "Second test result",
            "age": "2 days ago"
        }
    ]


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing."""
    client = Mock()
    client.search_web = Mock(return_value=[])
    client.health_check = Mock(return_value=True)
    return client


# ============================================================================
# Test Data
# ============================================================================

@pytest.fixture
def sample_messages():
    """Sample conversation messages for testing."""
    return [
        {
            "id": 1,
            "role": "user",
            "content": "Hello, what is Bitcoin?",
            "timestamp": "2026-01-17T10:00:00Z"
        },
        {
            "id": 2,
            "role": "assistant",
            "content": "Bitcoin is a decentralized digital currency.",
            "timestamp": "2026-01-17T10:00:05Z"
        },
        {
            "id": 3,
            "role": "user",
            "content": "What is its current price?",
            "timestamp": "2026-01-17T10:00:10Z"
        }
    ]


@pytest.fixture
def sample_persona():
    """Sample persona configuration for testing."""
    return {
        "key": "test_persona",
        "display_name": "Test Persona",
        "rarity": "common",
        "lore": "A test persona for unit testing.",
        "voice": {
            "do": ["Be helpful", "Be concise"],
            "dont": ["Be verbose", "Be rude"]
        },
        "behavior": {
            "greeting": "Hello! I'm a test persona.",
            "response_style": "friendly"
        },
        "expertise": ["testing", "qa"],
        "psychological_profile": {
            "personality_traits": ["helpful", "precise"]
        },
        "model_preferences": {
            "temperature": 0.7
        }
    }


# ============================================================================
# Skip Markers
# ============================================================================

def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "requires_api_key: marks tests that need API keys"
    )
    config.addinivalue_line(
        "markers", "requires_docker: marks tests that need Docker"
    )
    config.addinivalue_line(
        "markers", "requires_ollama: marks tests that need Ollama"
    )


# ============================================================================
# Test Collection
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add markers based on test file location
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        elif "evaluation" in str(item.fspath):
            item.add_marker(pytest.mark.evaluation)
        elif "exploration" in str(item.fspath):
            item.add_marker(pytest.mark.skip(reason="Exploration test - not for CI"))
        else:
            item.add_marker(pytest.mark.unit)
