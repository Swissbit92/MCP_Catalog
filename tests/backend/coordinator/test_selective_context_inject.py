"""ADR-006 M0.1 — selective session-context injection.

Gate 0 (2026-06-28) showed that injecting the shared NEPHILIM lore/rank/capability
vocabulary into every persona homogenizes voice (distinctiveness 0.768→0.643), while
user-profile facts + emotional state are persona-neutral relationship state. M0.1
therefore injects ONLY those two blocks. These tests drive handle_session_chat with
fake deps and a capturing chat_function to assert exactly what reaches ChatBody's
extra_system_context — including that a non-empty rank block is NOT injected.

Headless: chat_function raises a sentinel after capturing, so the persistence tail
(message saves, fact extraction, summarization) never runs.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.coordinator.config import get_settings
from src.coordinator.services.chat_session_service import (
    _build_seeker_rank_context,
    handle_session_chat,
)

PROFILE_CTX = "[User Profile]\nThe seeker's name is Raphael; he tends the trading engine."
EMOTIONAL_CTX = "[Emotional State]\nTrust is warm and steady; mood: contemplative."


class _StopAfterCapture(Exception):
    """Sentinel: raised by the fake chat_function once ChatBody is captured."""


class _FakeSessionRepo:
    def get_persona_key(self, session_id):
        return "nephilim_eeva"


class _FakeMessageRepo:
    def get_messages_by_session(self, session_id):
        return []


class _FakeSummaryRepo:
    def get_summaries_by_session(self, session_id):
        return []


class _FakeEmotionalState:
    trust_level = 0.7
    current_mood = "contemplative"

    def to_prompt_context(self):
        return EMOTIONAL_CTX


class _FakeEmotionalStateRepo:
    def get_or_create(self, session_id):
        return _FakeEmotionalState()


class _FakeMemoryManager:
    def select_messages(self, messages, token_budget, system_prompt_tokens):
        return []


class _FakeUserProfile:
    def get_context_summary(self, max_facts, max_topics):
        return PROFILE_CTX


class _FakeUserProfileRepo:
    def get_session_user(self, session_id):
        return "user-raphael"

    def get_profile(self, user_id):
        return _FakeUserProfile()


class _FakeSeekerProgressionRepo:
    """Non-Initiate rank so _build_seeker_rank_context returns a NON-empty block."""

    def get_seeker_profile(self, user_id):
        return {"rank_name": "Adept"}

    def get_or_create_affinity(self, user_id, persona_key):
        return {"affinity_level": 2}


def _deps():
    return {
        "session_repo": _FakeSessionRepo(),
        "message_repo": _FakeMessageRepo(),
        "summary_repo": _FakeSummaryRepo(),
        "emotional_state_repo": _FakeEmotionalStateRepo(),
        "memory_manager": _FakeMemoryManager(),
        "user_profile_repo": _FakeUserProfileRepo(),
        "episodic_memory_rag": None,
        "fact_extractor": None,
        "seeker_progression_repo": _FakeSeekerProgressionRepo(),
    }


def _run_and_capture(settings):
    """Run handle_session_chat until chat_function fires; return the ChatBody."""
    captured = {}

    def fake_chat(body):
        captured["body"] = body
        raise _StopAfterCapture()

    with patch(
        "src.coordinator.services.chat_session_service.get_settings",
        return_value=settings,
    ):
        with pytest.raises(_StopAfterCapture):
            handle_session_chat(
                session_id="sess-m01-selective",
                message="Do you remember what I tend?",
                deps=_deps(),
                chat_function=fake_chat,
                add_message_function=lambda *a, **k: None,
            )
    return captured["body"]


def _settings(inject: bool, rank_enabled: bool = True):
    s = get_settings().model_copy(deep=True)
    s.memory.context_inject_enabled = inject
    s.lore.rank_context_enabled = rank_enabled
    return s


def test_flag_on_injects_profile_and_emotional_only():
    body = _run_and_capture(_settings(inject=True))
    assert body.extra_system_context == f"{PROFILE_CTX}\n\n{EMOTIONAL_CTX}"


def test_flag_on_excludes_nonempty_rank_block():
    # The rank block IS built (Adept -> non-empty) and appended to the legacy
    # system_prompt estimate, but must never reach extra_system_context.
    rank_block = _build_seeker_rank_context("Adept")
    assert rank_block  # precondition: the excluded block is genuinely non-empty
    body = _run_and_capture(_settings(inject=True, rank_enabled=True))
    assert rank_block not in (body.extra_system_context or "")
    assert "<seeker_rank>" not in (body.extra_system_context or "")


def test_flag_off_injects_nothing():
    body = _run_and_capture(_settings(inject=False))
    assert body.extra_system_context is None


def test_flag_on_empty_blocks_yields_none():
    deps = _deps()

    class _NoProfileRepo(_FakeUserProfileRepo):
        def get_profile(self, user_id):
            return None

    class _MuteEmotionalState(_FakeEmotionalState):
        def to_prompt_context(self):
            return ""

    class _MuteEmotionalRepo(_FakeEmotionalStateRepo):
        def get_or_create(self, session_id):
            return _MuteEmotionalState()

    deps["user_profile_repo"] = _NoProfileRepo()
    deps["emotional_state_repo"] = _MuteEmotionalRepo()

    captured = {}

    def fake_chat(body):
        captured["body"] = body
        raise _StopAfterCapture()

    with patch(
        "src.coordinator.services.chat_session_service.get_settings",
        return_value=_settings(inject=True),
    ):
        with pytest.raises(_StopAfterCapture):
            handle_session_chat(
                session_id="sess-m01-empty",
                message="hello",
                deps=deps,
                chat_function=fake_chat,
                add_message_function=lambda *a, **k: None,
            )
    assert captured["body"].extra_system_context is None
