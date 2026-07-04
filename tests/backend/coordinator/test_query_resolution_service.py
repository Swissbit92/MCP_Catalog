# tests/backend/coordinator/test_query_resolution_service.py
"""Unit tests for QueryResolutionService (follow-up search query resolution).

Headless: the LLM is a MagicMock, flag toggled via env + settings cache clear.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.coordinator.config import get_settings
from src.coordinator.services.query_resolution_service import QueryResolutionService


def _prompt(*turns: str) -> str:
    """Compile turns into the 'User: ...\\n\\nAssistant: ...' form chat.py uses."""
    return "\n\n".join(turns)


@pytest.fixture(autouse=True)
def _clean_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def enable_resolution(monkeypatch):
    monkeypatch.setenv("SEARCH_QUERY_RESOLUTION_ENABLED", "true")
    get_settings.cache_clear()


@pytest.fixture
def disable_resolution(monkeypatch):
    monkeypatch.setenv("SEARCH_QUERY_RESOLUTION_ENABLED", "false")
    get_settings.cache_clear()


def _svc(complete_return="resolved standalone query"):
    llm = MagicMock()
    llm.complete.return_value = complete_return
    return QueryResolutionService(llm_service=llm), llm


# ------------------------------------------------------------- flag behavior

def test_flag_off_passes_through_verbatim(disable_resolution):
    svc, llm = _svc()
    prompt = _prompt(
        "User: how is switzerland doing at the world cup",
        "Assistant: I do not follow current events.",
        "User: search the web for it",
    )
    assert svc.resolve(prompt) == "search the web for it"
    llm.complete.assert_not_called()  # no LLM cost when disabled


def test_flag_on_resolves_followup(enable_resolution):
    svc, llm = _svc(complete_return="Switzerland World Cup 2026 performance")
    prompt = _prompt(
        "User: how is switzerland doing at the world cup",
        "Assistant: I do not follow current events.",
        "User: search the web for it",
    )
    assert svc.resolve(prompt) == "Switzerland World Cup 2026 performance"
    llm.complete.assert_called_once()


def test_flag_on_first_turn_no_history_passes_through(enable_resolution):
    """A deictic-looking FIRST turn has no context to resolve; pass through."""
    svc, llm = _svc()
    prompt = _prompt("User: search the web for it")
    assert svc.resolve(prompt) == "search the web for it"
    llm.complete.assert_not_called()


def test_flag_on_self_contained_query_skips_rewrite(enable_resolution):
    """A long, self-contained latest turn should not trigger an LLM rewrite."""
    svc, llm = _svc()
    prompt = _prompt(
        "User: hi there",
        "Assistant: Hello, Seeker.",
        "User: what were the main causes of the fall of the western roman empire",
    )
    out = svc.resolve(prompt)
    assert out == "what were the main causes of the fall of the western roman empire"
    llm.complete.assert_not_called()


# ------------------------------------------------------------- fallback safety

def test_rewrite_garbage_falls_back_to_latest(enable_resolution):
    """An over-long rewrite is rejected; resolve returns the raw latest turn."""
    svc, llm = _svc(complete_return="word " * 40)  # 40 words > guard
    prompt = _prompt(
        "User: tell me about the webb telescope finding",
        "Assistant: ...",
        "User: look it up",
    )
    assert svc.resolve(prompt) == "look it up"


def test_llm_exception_falls_back_to_latest(enable_resolution):
    svc, llm = _svc()
    llm.complete.side_effect = RuntimeError("ollama down")
    prompt = _prompt(
        "User: tell me about the webb telescope finding",
        "Assistant: ...",
        "User: look it up",
    )
    assert svc.resolve(prompt) == "look it up"


def test_empty_rewrite_falls_back_to_latest(enable_resolution):
    svc, llm = _svc(complete_return="   ")
    prompt = _prompt(
        "User: bitcoin news today",
        "Assistant: ...",
        "User: and ethereum?",
    )
    assert svc.resolve(prompt) == "and ethereum?"


# ------------------------------------------------------------- follow-up detector

@pytest.mark.parametrize(
    "turn",
    [
        "search the web for it",
        "look it up",
        "and Geneva?",
        "is that true",
        "what about them",
        "google it",
    ],
)
def test_looks_like_followup_true(turn):
    assert QueryResolutionService._looks_like_followup(turn) is True


@pytest.mark.parametrize(
    "turn",
    [
        "what were the main causes of the fall of the western roman empire",
        "current bitcoin price and market capitalization figures please",
    ],
)
def test_looks_like_followup_false(turn):
    assert QueryResolutionService._looks_like_followup(turn) is False


# ------------------------------------------------------------- sanitizer

def test_sanitize_strips_label_and_quotes():
    out = QueryResolutionService._sanitize(
        'Rewritten: "Geneva weather this week"', fallback="x"
    )
    assert out == "Geneva weather this week"


def test_sanitize_parses_json_wrapper():
    out = QueryResolutionService._sanitize(
        '{"query": "James Webb exoplanet finding"}', fallback="x"
    )
    assert out == "James Webb exoplanet finding"


def test_sanitize_takes_first_line():
    out = QueryResolutionService._sanitize(
        "Geneva weather\nHere is why I chose that.", fallback="x"
    )
    assert out == "Geneva weather"


def test_sanitize_empty_falls_back():
    assert QueryResolutionService._sanitize("", fallback="orig") == "orig"
