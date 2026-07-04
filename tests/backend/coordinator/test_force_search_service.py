# tests/backend/coordinator/test_force_search_service.py
"""
Unit tests for ForceSearchService and explicit-search routing.

Background: a user typing an explicit command like "search the web to confirm"
previously matched NEITHER the intent classifier's SEARCH_KEYWORDS nor the
force-search FORCE_PATTERNS, so it fell through to the RP model which refused
("I cannot and will not perform web searches for you"). The fix wires a single
shared constant (EXPLICIT_SEARCH_COMMANDS) into both layers so an explicit
command (a) routes intent -> NEEDS_WEB_SEARCH (Brave tool offered) and
(b) bypasses the unreliable LLM tool-calling loop (forced direct execution).

These tests lock in both layers and guard against keyword over-triggering.
"""

from __future__ import annotations

import pytest

from src.coordinator.services.force_search_service import ForceSearchService
from src.coordinator.tools.keywords import EXPLICIT_SEARCH_COMMANDS, SEARCH_KEYWORDS
from src.coordinator.tools.intent_classifier import classify_query_intent, QueryIntent


# Persona with Brave access (E.E.V.A. = Archon: brave_search + mongodb)
BRAVE_ACCESS = ["brave_search"]


class TestForceSearchExplicitCommands:
    """ForceSearchService.should_force_search must catch explicit search commands."""

    def test_users_exact_phrase_forces_search(self):
        # The literal phrase from the bug report.
        assert ForceSearchService.should_force_search("search the web to confirm") is True

    @pytest.mark.parametrize("command", EXPLICIT_SEARCH_COMMANDS)
    def test_each_explicit_command_forces_search(self, command):
        # Each shared command, embedded in a natural sentence, forces a search.
        assert ForceSearchService.should_force_search(f"please {command} for me") is True

    def test_case_insensitive(self):
        assert ForceSearchService.should_force_search("SEARCH THE WEB please") is True


class TestForceSearchRegression:
    """Pre-existing price/current patterns must still force search."""

    @pytest.mark.parametrize("query", [
        "what is the bitcoin price right now",
        "eth cost today",
        "what's bitcoin trading at",
        "latest crypto news",
    ])
    def test_existing_patterns_still_force(self, query):
        assert ForceSearchService.should_force_search(query) is True


class TestForceSearchLastPhrasingGap:
    """2026-07-04 incident (session dcc3693d): FORCE_PATTERNS' 'latest' entry did
    not cover 'last' phrasing, so a clear temporal/outcome follow-up like "what
    was their last match" never force-searched — see tests/evaluation/force_search_eval_set.json
    for the full corpus. Fixed alongside the groundedness gate (both target the
    same failure #5 root cause); the groundedness gate remains the safety net
    for phrasings this keyword pattern still can't reasonably cover (e.g. "were
    they eliminated" — no explicit last/latest keyword at all)."""

    @pytest.mark.parametrize("query", [
        "what was their last match",
        "who won the last game",
        "what happened in their last fixture",
        "what was the score of the last match",
    ])
    def test_last_phrasing_forces_search(self, query):
        assert ForceSearchService.should_force_search(query) is True


class TestForceSearchNoOverTrigger:
    """High-precision phrases must NOT fire on benign queries (no bare 'search')."""

    @pytest.mark.parametrize("query", [
        "what is the meaning of life",
        "how does blockchain work",
        "tell me about your research background",   # 'research' must not match bare 'search'
        "who was the first president",
        "explain the concept of entropy",
    ])
    def test_benign_queries_do_not_force(self, query):
        assert ForceSearchService.should_force_search(query) is False


class TestExplicitCommandsRouteToWebIntent:
    """The intent classifier must offer the Brave tool for explicit commands.

    Without this, complete_with_tools receives an empty tools list and the
    force-search branch is never reached (tool_calling_service.py:103).
    """

    def test_explicit_command_routes_to_web_search(self):
        intent = classify_query_intent("search the web to confirm", "legendary", mcp_access=BRAVE_ACCESS)
        assert intent == QueryIntent.NEEDS_WEB_SEARCH

    @pytest.mark.parametrize("command", EXPLICIT_SEARCH_COMMANDS)
    def test_each_command_routes_to_web(self, command):
        intent = classify_query_intent(f"can you {command}", "legendary", mcp_access=BRAVE_ACCESS)
        # NEEDS_BOTH was removed when QueryIntent was simplified (MongoDB MCP removal, ADR-002).
        assert intent == QueryIntent.NEEDS_WEB_SEARCH

    def test_no_brave_access_does_not_route_web(self):
        # A persona without brave_search must not be routed to web search.
        intent = classify_query_intent("search the web", "common", mcp_access=[])
        assert intent != QueryIntent.NEEDS_WEB_SEARCH


class TestSingleSourceOfTruth:
    """The shared constant must actually be folded into SEARCH_KEYWORDS."""

    def test_explicit_commands_in_search_keywords(self):
        for command in EXPLICIT_SEARCH_COMMANDS:
            assert command in SEARCH_KEYWORDS

    def test_explicit_commands_in_force_patterns(self):
        primaries = {primary for primary, _ in ForceSearchService.FORCE_PATTERNS}
        for command in EXPLICIT_SEARCH_COMMANDS:
            assert command in primaries
