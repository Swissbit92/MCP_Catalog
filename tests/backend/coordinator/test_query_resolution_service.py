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
        "User: what about it",  # deictic, but NOT a bare search command
    )
    assert svc.resolve(prompt) == "what about it"


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


# --------------------------------------------------- bare-command hardening (turn-2)

def test_bare_command_garbage_rewrite_falls_back_to_prior_turn(enable_resolution):
    """Bare 'search the web' + a whiffed rewrite must fall back to the prior
    substantive turn (the topic), NOT the useless bare command."""
    svc, llm = _svc(complete_return="word " * 40)  # garbage rewrite, rejected
    prompt = _prompt(
        "User: how is the world cup 2026 going and is switzerland performing",
        "Assistant: I do not follow current events.",
        "User: search the web",
    )
    out = svc.resolve(prompt)
    assert out == "how is the world cup 2026 going and is switzerland performing"
    assert out != "search the web"


def test_bare_command_rewrite_echoing_command_uses_fallback(enable_resolution):
    """If the model echoes the command ('search the web') the guard rejects it."""
    svc, llm = _svc(complete_return="search the web")
    prompt = _prompt(
        "User: latest ethereum price and news",
        "Assistant: ...",
        "User: search the web for it",
    )
    out = svc.resolve(prompt)
    assert out == "latest ethereum price and news"


def test_bare_command_good_rewrite_is_used(enable_resolution):
    """A good rewrite of a bare command is still used (fallback only on failure)."""
    svc, llm = _svc(complete_return="Switzerland World Cup 2026 performance")
    prompt = _prompt(
        "User: how is switzerland doing at the world cup",
        "Assistant: ...",
        "User: search the web",
    )
    assert svc.resolve(prompt) == "Switzerland World Cup 2026 performance"


# --------------------------------------------- 2026-07-04 incident regressions (M3)

def test_near_verbatim_echo_of_contextual_phrase_is_rejected(enable_resolution):
    """A rewrite that echoes the input almost unchanged, using words that only make
    sense with prior context ('the next match'), must not reach Brave verbatim.

    Fixed by extending _COMMAND_FILLER_TOKENS to include context-dependent-but-
    non-pronoun placeholder phrases ("next", "match", "last", "game", "fixture")
    — these now correctly count as "bare" filler, same as the existing deictic-
    token handling, so both the prior-substantive-turn fallback trigger AND the
    post-rewrite echo-guard now catch this case.
    """
    svc, llm = _svc(complete_return="search the web for the next match")
    prompt = _prompt(
        "User: against whom is switzerland playing in the next match in the fifa world cup 2026",
        "Assistant: I cannot and will not predict or speculate about future sports events.",
        "User: search the web for the next match",
    )
    resolved = svc.resolve(prompt)
    assert llm.complete.called, "test setup sanity check: resolution should have engaged"
    assert resolved != "search the web for the next match", (
        "the near-verbatim echo reached Brave unchanged — this is the exact junk-"
        "result-inducing query from the 2026-07-04 incident"
    )


def test_natural_correction_phrasing_still_triggers_resolution(enable_resolution):
    """A natural 'no, I meant X' correction, even when it pushes word count over
    the short-turn/command-turn thresholds, must still be recognized as a
    follow-up needing resolution — not passed through raw.

    Fixed by stripping a leading correction preamble ("no, I meant...") before
    the word-count check in _looks_like_followup — the preamble carries no
    topic content and was inflating the count past _COMMAND_TURN_MAX_WORDS.
    """
    svc, llm = _svc(complete_return="Switzerland World Cup 2026 next match")
    prompt = _prompt(
        "User: against whom is switzerland playing in the next match in the fifa world cup 2026",
        "Assistant: I cannot and will not predict or speculate about future sports events.",
        "User: no, I meant search the web for the next match",
    )
    svc.resolve(prompt)
    assert llm.complete.called, (
        "the 10-word correction phrasing never triggered _looks_like_followup, "
        "so resolve() returned the raw turn (with 'no, I meant' still attached) "
        "without ever attempting resolution"
    )


@pytest.mark.parametrize(
    "turn",
    ["search the web", "search the web for it", "look it up online", "google it", "web search"],
)
def test_is_bare_search_command_true(turn):
    assert QueryResolutionService._is_bare_search_command(turn) is True


@pytest.mark.parametrize(
    "turn",
    [
        "search the web for switzerland world cup",  # command + real topic
        "and Geneva?",                                # not a command
        "how is the world cup going",                 # no command phrase
        "",                                           # empty
    ],
)
def test_is_bare_search_command_false(turn):
    assert QueryResolutionService._is_bare_search_command(turn) is False


def test_prior_substantive_user_turn_skips_bare_commands():
    prompt = _prompt(
        "User: tell me about the webb telescope exoplanet finding",
        "Assistant: ...",
        "User: search the web",
        "Assistant: what do you seek?",
        "User: look it up",
    )
    got = QueryResolutionService._prior_substantive_user_turn(prompt, "look it up")
    assert got == "tell me about the webb telescope exoplanet finding"


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
