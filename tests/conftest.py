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

# Snapshot of the REAL process environment, taken at conftest import — i.e. before
# pytest collects (imports) any test module. Two integration modules call
# `load_dotenv()` at module scope, which exports the developer's whole prod `.env`
# into os.environ during collection; `_hermetic_settings` diffs against this
# snapshot to undo exactly that, while preserving vars genuinely exported by the
# shell/CI (which are in the snapshot and must survive).
_ENV_SNAPSHOT = dict(os.environ)


# ============================================================================
# Environment Configuration
# ============================================================================

@pytest.fixture(autouse=True, scope="session")
def _hermetic_settings():
    """Never read the developer's real `.env` during tests.

    The suite was silently coupled to live prod config through TWO channels, and
    both must be closed — closing either alone leaves the other winning:

    1. **os.environ** (highest priority). ``tests/integration/`` modules call
       ``load_dotenv()`` at MODULE scope, and pytest imports every test module
       during collection — so the whole prod `.env` is exported into the process
       environment before the first test runs. Undone here by diffing against
       ``_ENV_SNAPSHOT`` (captured at conftest import, pre-collection) and removing
       only what collection injected; shell/CI-exported vars survive.
    2. **the dotenv file**. Every settings class declares
       ``model_config["env_file"] = ".env"``, which pydantic-settings reads as a
       source in addition to os.environ (priority: os.environ > dotenv > defaults).
       So ``monkeypatch.delenv`` could not simulate "env absent" — it just fell
       back to the file. Disabled here.

    Net effect: settings resolve from os.environ + field defaults only, so tests are
    deterministic and monkeypatch behaves as written. Symptoms this prevents: search
    tests bypassing their Brave mocks to issue REAL requests against the local
    SearXNG, and default-assertion tests seeing prod flags (TOOL_BRAIN_ENABLED=true).

    Session-scoped; everything is restored on teardown. New settings modules and new
    dotenv-loading test modules are covered automatically.

    NOTE: this conftest puts BOTH ``src/`` and the repo root on ``sys.path``, so
    ``coordinator.config`` and ``src.coordinator.config`` are two DISTINCT module
    objects holding two distinct copies of each settings class. Both trees must be
    patched — patching only one leaves the other reading the real `.env`, which
    reproduces exactly the bug this fixture exists to prevent.
    """
    import importlib
    import inspect
    import pkgutil

    from pydantic_settings import BaseSettings

    # (1) Undo the prod `.env` that a module-scope load_dotenv() exported into
    # os.environ during collection. Only keys ADDED since conftest import are
    # removed, so genuinely-exported vars (e.g. OLLAMA_BASE from the CI command)
    # are left untouched.
    injected = {k: v for k, v in os.environ.items() if k not in _ENV_SNAPSHOT}
    for key in injected:
        del os.environ[key]

    # (2) Stop pydantic-settings reading the `.env` FILE as a source.
    modules = []
    for root in ("src.coordinator.config", "coordinator.config"):
        try:
            pkg = importlib.import_module(root)
        except ImportError:  # tree not importable in this layout — skip
            continue
        modules.append(pkg)
        for info in pkgutil.iter_modules(pkg.__path__):
            try:
                modules.append(importlib.import_module(f"{root}.{info.name}"))
            except ImportError:
                continue

    patched = []
    seen = set()
    for module in modules:
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if id(obj) in seen or not issubclass(obj, BaseSettings):
                continue
            seen.add(id(obj))
            cfg = obj.__dict__.get("model_config")
            if isinstance(cfg, dict) and cfg.get("env_file") is not None:
                patched.append((obj, cfg["env_file"]))
                cfg["env_file"] = None

    caches = []
    for module in modules:
        get_settings = getattr(module, "get_settings", None)
        if get_settings is not None and hasattr(get_settings, "cache_clear"):
            caches.append(get_settings)
    for fn in caches:
        fn.cache_clear()

    yield

    os.environ.update(injected)
    for obj, original in patched:
        obj.model_config["env_file"] = original
    for fn in caches:
        fn.cache_clear()


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
