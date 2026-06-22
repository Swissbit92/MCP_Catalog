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

def _ollama_reachable() -> bool:
    """Quick TCP check for a running Ollama (default 127.0.0.1:11434).

    Live LLM calls run at ~16 tok/s, so tests marked ``requires_ollama`` are
    skipped — not silently run for minutes — when Ollama is not up (e.g. headless
    CI). Honors OLLAMA_BASE for host/port.
    """
    import socket
    from urllib.parse import urlparse

    base = os.getenv("OLLAMA_BASE", "http://127.0.0.1:11434")
    parsed = urlparse(base)
    host, port = parsed.hostname or "127.0.0.1", parsed.port or 11434
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def _docker_available() -> bool:
    """True if the docker CLI is on PATH and the daemon answers."""
    import shutil
    import subprocess

    if shutil.which("docker") is None:
        return False
    try:
        return subprocess.run(
            ["docker", "info"], capture_output=True, timeout=5
        ).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location.

    Also auto-skips resource-gated tests when their resource is unavailable so
    the suite is green and fast on a headless macOS box (no live Ollama, no Brave
    key, no Docker) instead of hanging on live calls.
    """
    # Compute resource availability once per session.
    skip_ollama = (
        None if _ollama_reachable()
        else pytest.mark.skip(reason="Ollama not reachable (set OLLAMA_BASE / start `ollama serve`)")
    )
    skip_api_key = (
        None if os.getenv("BRAVE_API_KEY", "").strip()
        else pytest.mark.skip(reason="BRAVE_API_KEY not set")
    )
    skip_docker = (
        None if _docker_available()
        else pytest.mark.skip(reason="Docker not available")
    )

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

        # Auto-skip tests whose required external resource is unavailable.
        if skip_ollama is not None and "requires_ollama" in item.keywords:
            item.add_marker(skip_ollama)
        if skip_api_key is not None and "requires_api_key" in item.keywords:
            item.add_marker(skip_api_key)
        if skip_docker is not None and "requires_docker" in item.keywords:
            item.add_marker(skip_docker)
