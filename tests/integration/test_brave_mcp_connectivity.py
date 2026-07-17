#!/usr/bin/env python
# test_brave_mcp_connectivity.py
# Manual integration test for Brave MCP connectivity

import sys
import os
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


def test_brave_connectivity(brave_env):
    """Test actual Brave MCP server connectivity."""
    print("\n" + "=" * 70)
    print("BRAVE MCP CONNECTIVITY TEST")
    print("=" * 70)

    try:
        # Create client
        print("\n[1/4] Creating Brave MCP client...")
        client = get_brave_client()
        print(f"[OK] Client created: timeout={client.timeout}s, max_results={client.max_results}")

        # Test search
        print("\n[2/4] Testing web search...")
        query = "Bitcoin price 2024"
        print(f"   Query: '{query}'")

        results = client.search_web(query, count=3)

        print(f"[OK] Search completed: {len(results)} results")

        # Display results
        print("\n[3/4] Displaying results...")
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

        # Cleanup
        print("\n[4/4] Cleaning up...")
        client.close()
        print("[OK] Client closed successfully")

        print("\n" + "=" * 70)
        print("[OK] ALL TESTS PASSED")
        print("=" * 70)
        print("\n>> Brave MCP integration is working correctly!\n")
        return True

    except MCPError as e:
        print(f"\n[ERROR] MCP Error: {e}")
        logger.error("MCP error occurred", exc_info=True)
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        logger.error("Unexpected error", exc_info=True)
        return False


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

    success = test_brave_connectivity(None)  # fixture arg unused by the body

    sys.exit(0 if success else 1)
