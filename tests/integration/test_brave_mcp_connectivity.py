#!/usr/bin/env python
# test_brave_mcp_connectivity.py
# Manual integration test for Brave MCP connectivity

import sys
import logging
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from coordinator.mcp_client_stdio import get_brave_client_stdio as get_brave_client
from coordinator.models.mcp_models import MCPError

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG to see response details
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Live end-to-end check: starts a real Brave MCP Docker container and calls the
# Brave API. Auto-skipped when the key/Docker are absent (tests/conftest.py's
# pytest_collection_modifyitems reads BRAVE_API_KEY from os.environ at collection),
# so a headless run skips instead of failing. Without these markers this test ran
# everywhere and silently "passed" by swallowing its own connection errors.
pytestmark = [pytest.mark.requires_api_key, pytest.mark.requires_docker]


@pytest.fixture
def brave_env(monkeypatch):
    """Load `.env` into the environment for THIS test only.

    `mcp_client_stdio` resolves the key as ``api_key or os.getenv("BRAVE_API_KEY")``,
    so a live connectivity check genuinely needs it in the environment. It is loaded
    via ``dotenv_values`` (which reads the file WITHOUT touching os.environ) and
    applied with ``monkeypatch.setenv``, so pytest restores everything at teardown.

    A module-scope ``load_dotenv()`` — what this file used to do — instead exported
    the whole prod `.env` into the process at COLLECTION time (pytest imports every
    test module before running any), which silently coupled unrelated tests to live
    prod config; that cost the suite 10 phantom failures, including search tests that
    bypassed their mocks to hit the real SearXNG. Keep env loading test-scoped.
    See tests/conftest.py::_hermetic_settings.
    """
    try:
        from dotenv import dotenv_values
    except ImportError:
        pytest.skip("python-dotenv not installed")
    for key, value in dotenv_values().items():
        if value is not None:
            monkeypatch.setenv(key, value)


def _run_search(query: str = "Bitcoin price 2024", count: int = 3):
    """Run one live Brave MCP search and return the results.

    Deliberately does NOT swallow exceptions: the pytest test asserts on the
    results, and script mode below wraps this in its own try/except for a
    human-readable exit code. (Previously the whole check lived inside a
    catch-everything block that returned False, so a total failure still reported
    as a passing test.)
    """
    client = get_brave_client()
    try:
        return client.search_web(query, count=count)
    finally:
        client.close()


def test_brave_connectivity(brave_env):
    """Live: the Brave MCP container starts and returns usable search results.

    Skipped automatically unless BRAVE_API_KEY is exported and Docker is up
    (see the requires_* markers + tests/conftest.py::pytest_collection_modifyitems).
    """
    results = _run_search(count=3)

    assert results, "Brave MCP returned no results for a common query"
    assert len(results) <= 3, f"requested 3 results, got {len(results)}"

    first = results[0]
    assert first.title and first.title.strip(), "first result has an empty title"
    assert first.url.startswith(("http://", "https://")), f"non-http result url: {first.url!r}"
    assert first.description is not None, "first result has no description field"


if __name__ == "__main__":
    print("\n>> Starting Brave MCP connectivity test...")
    print("This will test actual Docker container startup and API calls.")
    print("\nPrerequisites:")
    print("  [x] Docker installed and running")
    print("  [x] BRAVE_API_KEY set in .env")
    print("  [x] Internet connection available")

    input("\nPress Enter to continue...")

    # Script mode gets no pytest fixture, so load the env here instead (safe: this
    # block never runs under pytest, so it cannot pollute a test session).
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("Warning: python-dotenv not installed, using system environment only")

    print("\n[1/3] Creating client and searching...")
    try:
        results = _run_search(count=3)
    except MCPError as e:
        print(f"\n[ERROR] MCP Error: {e}")
        logger.error("MCP error occurred", exc_info=True)
        sys.exit(1)
    except Exception as e:  # noqa: BLE001 - script mode wants a readable exit, not a traceback
        print(f"\n[ERROR] Unexpected error: {e}")
        logger.error("Unexpected error", exc_info=True)
        sys.exit(1)

    print(f"[OK] Search completed: {len(results)} results")
    print("\n[2/3] Displaying results...")
    print("-" * 70)
    for i, result in enumerate(results, 1):
        # Handle Unicode properly for Windows console
        title = result.title.encode('ascii', 'ignore').decode('ascii')
        desc = result.description[:150].encode('ascii', 'ignore').decode('ascii')
        print(f"\n{i}. {title}")
        print(f"   URL: {result.url}")
        print(f"   Description: {desc}...")
        if result.age:
            print(f"   Age: {result.age}")

    print("\n[3/3] Done.")
    print("\n" + "=" * 70)
    print("[OK] Brave MCP integration is working correctly!")
    print("=" * 70 + "\n")
    sys.exit(0)
