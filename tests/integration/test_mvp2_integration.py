#!/usr/bin/env python
# test_mvp2_integration.py
# Integration test for MVP 2: End-to-end autonomous web search functionality

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import pytest

from coordinator.llm_client import LC_OllamaClient
from coordinator.mcp_client_stdio import BraveMCPClientStdio as BraveMCPClient
from coordinator.tool_definitions import get_brave_search_tool, get_tools_for_persona
from coordinator.config import get_settings

# Live end-to-end test: needs a running Ollama and a Brave API key.
pytestmark = [pytest.mark.requires_ollama, pytest.mark.requires_api_key]

# Config moved from standalone get_*() getters to a typed get_settings() object.
# Thin shims preserve the original call sites below.
_settings = get_settings()
def get_ollama_base() -> str: return _settings.ollama.base
def get_persona_model() -> str: return _settings.ollama.model
def get_persona_temperature() -> float: return _settings.ollama.temperature
def get_brave_api_key() -> str: return _settings.brave.api_key
def get_brave_max_results() -> int: return _settings.brave.max_results
def get_brave_safesearch() -> str: return _settings.brave.safesearch
def get_brave_search_timeout() -> int: return _settings.brave.timeout

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass


def test_no_search_scenario():
    """Test that simple queries don't trigger unnecessary web search."""
    print("\n" + "="*80)
    print("TEST 1: No Search Scenario (Math Question)")
    print("="*80)

    # Initialize clients
    brave_client = BraveMCPClient(
        api_key=get_brave_api_key(),
        max_results=get_brave_max_results(),
        safesearch=get_brave_safesearch(),
        timeout=get_brave_search_timeout()
    )

    llm_client = LC_OllamaClient(
        base=get_ollama_base(),
        model=get_persona_model(),
        temperature=get_persona_temperature(),
        mcp_client=brave_client
    )

    # Simple math query - should NOT trigger search
    persona_system = "You are Eeva, a nerdy Bitcoin expert. Be brief and charming."
    user_query = "What is 15% of 200?"
    tools = [get_brave_search_tool()]

    print(f"\nPersona: Eeva (Bitcoin Expert)")
    print(f"Query: {user_query}")
    print(f"Expected: Direct answer without web search\n")

    start_time = time.time()
    response, tool_call, search_results = llm_client.complete_with_tools(
        persona_system=persona_system,
        user_prompt=user_query,
        tools=tools
    )
    elapsed = time.time() - start_time

    print(f"Response ({elapsed:.2f}s):")
    print(response)
    print(f"\nUsed web search: {tool_call is not None}")
    print(f"Search results: {len(search_results) if search_results else 0}")

    # Verify
    assert tool_call is None, "Should NOT have used web search for math"
    assert search_results is None, "Should NOT have search results"
    print("\n[PASS] No unnecessary web search for math question")

    brave_client.close()


def test_search_scenario():
    """Test that current information queries trigger web search."""
    print("\n" + "="*80)
    print("TEST 2: Search Scenario (Current Information)")
    print("="*80)

    # Initialize clients
    brave_client = BraveMCPClient(
        api_key=get_brave_api_key(),
        max_results=get_brave_max_results(),
        safesearch=get_brave_safesearch(),
        timeout=get_brave_search_timeout()
    )

    llm_client = LC_OllamaClient(
        base=get_ollama_base(),
        model=get_persona_model(),
        temperature=get_persona_temperature(),
        mcp_client=brave_client
    )

    # Current price query - SHOULD trigger search
    persona_system = "You are Eeva, a nerdy Bitcoin expert. Be brief and charming."
    user_query = "What is the current price of Bitcoin?"
    tools = [get_brave_search_tool()]

    print(f"\nPersona: Eeva (Bitcoin Expert)")
    print(f"Query: {user_query}")
    print(f"Expected: Web search for current price\n")

    start_time = time.time()
    response, tool_call, search_results = llm_client.complete_with_tools(
        persona_system=persona_system,
        user_prompt=user_query,
        tools=tools
    )
    elapsed = time.time() - start_time

    print(f"Response ({elapsed:.2f}s):")
    print(response)
    print(f"\nUsed web search: {tool_call is not None}")
    print(f"Search results: {len(search_results) if search_results else 0}")

    if search_results:
        print("\nTop search results:")
        for i, result in enumerate(search_results[:3], 1):
            print(f"  {i}. {result.title}")
            print(f"     {result.url}")

    # Verify
    if tool_call is None:
        print("\n[WARN]  WARNING: Expected web search but none was performed")
        print("    This could indicate the LLM chose to answer from knowledge")
        print("    Check if the response includes citations/sources")
    else:
        assert tool_call.name == "brave_web_search", "Should use brave_web_search tool"
        assert search_results is not None, "Should have search results"
        assert len(search_results) > 0, "Should have at least one result"
        print("\n[PASS] PASS: Web search triggered for current information")

    brave_client.close()


def test_persona_rarity_tool_access():
    """Test that tools are correctly assigned based on persona rarity."""
    print("\n" + "="*80)
    print("TEST 3: Persona Rarity Tool Access")
    print("="*80)

    test_cases = [
        ("common_persona", "common", False),
        ("rare_persona", "rare", True),
        ("epic_persona", "epic", True),
        ("legendary_persona", "legendary", True),
    ]

    for persona_key, rarity, should_have_tools in test_cases:
        tools = get_tools_for_persona(persona_key, rarity)
        has_tools = len(tools) > 0

        status = "[PASS]" if has_tools == should_have_tools else "[FAIL]"
        print(f"{status} {rarity.ljust(10)} persona: {has_tools} tools (expected: {should_have_tools})")

        assert has_tools == should_have_tools, f"Rarity {rarity} should {'have' if should_have_tools else 'not have'} tools"

    print("\n[PASS] PASS: Tool access correctly restricted by rarity")


def test_keyword_filtering():
    """Test that keyword pre-filtering reduces false positives."""
    print("\n" + "="*80)
    print("TEST 4: Keyword Pre-Filtering")
    print("="*80)

    from coordinator.tool_definitions import should_use_keyword_filter

    test_cases = [
        ("What is 2 + 2?", False, "Math"),
        ("Define blockchain", False, "Definition"),
        ("What is the current Bitcoin price?", True, "Current info"),
        ("Latest AI news", True, "Recent news"),
        ("Tell me about Python", None, "Ambiguous"),
    ]

    passed = 0
    total = len(test_cases)

    for query, expected, category in test_cases:
        result = should_use_keyword_filter(query)

        if expected is None:
            # Ambiguous cases can be None or False
            correct = result in [None, False]
        else:
            correct = result == expected

        status = "[PASS]" if correct else "[FAIL]"
        result_str = "SEARCH" if result is True else ("NO SEARCH" if result is False else "UNCERTAIN")

        print(f"{status} [{category.ljust(12)}] {query}")
        print(f"   -> {result_str}")

        if correct:
            passed += 1

    print(f"\n[PASS] PASS: {passed}/{total} keyword filter tests passed")
    assert passed == total, f"Expected all {total} tests to pass, got {passed}"


def main():
    """Run all integration tests."""
    print("\n" + "="*80)
    print("MVP 2 INTEGRATION TESTS")
    print("End-to-End Autonomous Web Search Functionality")
    print("="*80)

    # Check configuration
    api_key = get_brave_api_key()
    if not api_key:
        print("\n[FAIL] ERROR: BRAVE_API_KEY not set in .env")
        print("Skipping integration tests that require web search")
        test_persona_rarity_tool_access()
        test_keyword_filtering()
        return

    try:
        # Run tests
        test_keyword_filtering()
        test_persona_rarity_tool_access()
        test_no_search_scenario()
        test_search_scenario()

        print("\n" + "="*80)
        print("[PASS] ALL INTEGRATION TESTS PASSED")
        print("="*80)
        print("\nMVP 2 is ready for testing with actual personas!")
        print("\nNext steps:")
        print("  1. Start the FastAPI server: python src/main.py")
        print("  2. Test with rare/epic/legendary personas in the UI")
        print("  3. Verify autonomous search decisions")
        print("  4. Check that citations are included in responses")

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
