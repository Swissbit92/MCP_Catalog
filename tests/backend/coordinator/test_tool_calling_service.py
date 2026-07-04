# tests/backend/coordinator/test_tool_calling_service.py
"""Tests for ToolCallingService web-search query construction.

Regression coverage for the "search the web for it" follow-up bug: a deictic
follow-up turn was sent to Brave verbatim (losing the topic from prior turns),
which returned junk meta-results ("how to search the web" help pages). Because
those results are non-empty, the "no results -> I don't know" guard never fired
and the LLM confabulated over irrelevant grounding.

The fix (SEARCH_QUERY_RESOLUTION_ENABLED, default OFF) resolves the deictic
follow-up against the prior conversation before hitting Brave. These tests pin:
  1. flag ON  -> the query sent to Brave carries the resolved topic (World Cup)
  2. flag OFF -> byte-identical legacy behavior (raw latest turn passed through)

Headless-safe: LLM and MCP client are both mocked, so no Ollama/Brave/Docker.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.coordinator.config import get_settings
from src.coordinator.models.mcp_models import SearchResult
from src.coordinator.services.search_execution_service import SearchExecutionService
from src.coordinator.services.tool_calling_service import ToolCallingService


# A compiled multi-turn conversation exactly as chat.py assembles `user_compiled`:
# prior turns as "User:"/"Assistant:" lines, then the latest deictic follow-up.
# The topic ("Switzerland ... World Cup 2026") lives ONLY in the first user turn.
FOLLOWUP_CONVERSATION = "\n\n".join(
    [
        "User: how is the football world cup 2026 in the US going? "
        "is switzerland still in it and performing?",
        "Assistant: Ah, the beautiful game. I do not follow current events "
        "as they unfold, Seeker.",
        "[Remember: respond as E.E.V.A., following your guidelines.]\n"
        "User: search the web for it",
    ]
)

PERSONA_SYSTEM = "You are E.E.V.A., the Primarch."

BRAVE_TOOLS = [{"type": "function", "function": {"name": "brave_web_search"}}]


def _fake_complete(system: str, user: str) -> str:
    """Stand-in for LLMCompletionService.complete.

    Distinguishes the (future) query-rewrite call from the synthesis call by a
    marker the resolution prompt is required to contain ("standalone"/"rewrite").
    In M1 (feature absent) the rewrite branch is simply never reached.
    """
    blob = f"{system}\n{user}".lower()
    if "standalone" in blob or "rewrite" in blob:
        # The resolved, self-contained search query.
        return "Switzerland World Cup 2026 performance"
    # Synthesis pass.
    return "Switzerland has advanced in the tournament."


def _make_service(monkeypatch, *, resolution_enabled: bool):
    """Build a ToolCallingService wired to a mock LLM + mock Brave client.

    Returns (service, mock_mcp) so tests can assert the exact query string
    handed to `mcp_client.search_web`.
    """
    monkeypatch.setenv(
        "SEARCH_QUERY_RESOLUTION_ENABLED", "true" if resolution_enabled else "false"
    )
    # get_settings is lru_cached; drop the cached instance so the env flag takes.
    get_settings.cache_clear()

    mock_mcp = MagicMock()
    mock_mcp.search_web.return_value = [
        SearchResult(
            title="Switzerland at the 2026 FIFA World Cup",
            url="https://example.com/swiss-wc",
            description="Switzerland's results and standings.",
        )
    ]
    search_executor = SearchExecutionService(mcp_client=mock_mcp)

    mock_llm = MagicMock()
    mock_llm.complete.side_effect = _fake_complete

    service = ToolCallingService(
        llm_service=mock_llm,
        search_executor=search_executor,
    )
    return service, mock_mcp


@pytest.fixture(autouse=True)
def _restore_settings_cache():
    """Keep the global settings cache clean for other tests in the run."""
    yield
    get_settings.cache_clear()


def test_followup_query_resolved_when_enabled(monkeypatch):
    """flag ON: the deictic follow-up must be resolved before hitting Brave.

    RED until SEARCH_QUERY_RESOLUTION_ENABLED resolution (Milestone 2) lands.
    """
    service, mock_mcp = _make_service(monkeypatch, resolution_enabled=True)

    service.complete_with_tools(
        persona_system=PERSONA_SYSTEM,
        user_prompt=FOLLOWUP_CONVERSATION,
        tools=BRAVE_TOOLS,
    )

    mock_mcp.search_web.assert_called_once()
    sent_query = mock_mcp.search_web.call_args[0][0]

    # The topic must survive into the Brave query...
    assert "world cup" in sent_query.lower(), (
        f"resolved query lost the topic: {sent_query!r}"
    )
    # ...and the raw deictic turn must NOT be what we searched for.
    assert sent_query.strip().lower() != "search the web for it", (
        "deictic follow-up was passed to Brave verbatim (the original bug)"
    )


def test_followup_passthrough_when_disabled(monkeypatch):
    """flag OFF (default): byte-identical legacy behavior — raw latest turn.

    This guards the default path: resolution must be opt-in and must not change
    behavior until explicitly enabled.
    """
    service, mock_mcp = _make_service(monkeypatch, resolution_enabled=False)

    service.complete_with_tools(
        persona_system=PERSONA_SYSTEM,
        user_prompt=FOLLOWUP_CONVERSATION,
        tools=BRAVE_TOOLS,
    )

    mock_mcp.search_web.assert_called_once()
    sent_query = mock_mcp.search_web.call_args[0][0]
    assert sent_query.strip() == "search the web for it"
