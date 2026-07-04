"""ADR-006 M1 — per-persona-framed session-context injection.

Gate 0 (2026-06-28) and Gate 0.1 (2026-07-03) showed that injecting the
identically-formatted `[User Profile]` / `[Emotional State]` blocks homogenizes
persona voice (distinctiveness 0.768→0.643/0.679). M1 reframes the injected memory:
PROSE narrative variants (`get_narrative_context` / `to_narrative_context`) capped
by priority, then wrapped once in a non-echoable per-persona frame
(`context_framing.frame_injected_context`). These tests drive handle_session_chat
with fake deps and a capturing chat_function to assert exactly what reaches
ChatBody.extra_system_context — the framed narrative, and NOT the NEPHILIM
rank/lore vocabulary.

Hermetic: build_system_prompt is patched (the real one calls the CV-summariser LLM),
so the suite runs headless without Ollama. The fake chat_function raises a sentinel
after capture, so the persistence tail never runs.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.coordinator.config import get_settings
from src.coordinator.services.chat_session_service import (
    _build_seeker_rank_context,
    handle_session_chat,
)

# Old bullet-skeleton blocks (still built for the legacy token-budget estimate).
PROFILE_CTX = "**Your history with this user:**\n- User's name: Raphael"
EMOTIONAL_CTX = "Current Emotional Context:\n- Current mood: contemplative"
# New prose narratives (what the M1 injection path actually consumes).
PROFILE_NAR = "You've spoken with this seeker as Raphael 4 times before, 37 messages in all."
EMOTIONAL_NAR = "The bond between you is comfortable and warm. Right now they seem contemplative."

_FRAME_MARKER = "quietly carry from earlier conversations"


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

    def to_narrative_context(self):
        return EMOTIONAL_NAR


class _FakeEmotionalStateRepo:
    def get_or_create(self, session_id):
        return _FakeEmotionalState()


class _FakeMemoryManager:
    def select_messages(self, messages, token_budget, system_prompt_tokens):
        return []


class _FakeUserProfile:
    def get_context_summary(self, max_facts, max_topics):
        return PROFILE_CTX

    def get_narrative_context(self, max_facts, max_topics):
        return PROFILE_NAR


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


def _run_and_capture(settings, deps=None, session_id="sess-m1-framed"):
    """Run handle_session_chat until chat_function fires; return the ChatBody.

    Patches build_system_prompt (real one needs Ollama for CV summary) so the test
    is hermetic — it exercises the injection assembly, not prompt content.
    """
    captured = {}

    def fake_chat(body):
        captured["body"] = body
        raise _StopAfterCapture()

    with patch(
        "src.coordinator.services.chat_session_service.get_settings",
        return_value=settings,
    ), patch(
        "src.coordinator.services.chat_session_service.build_system_prompt",
        return_value="<identity>base persona prompt</identity>",
    ):
        with pytest.raises(_StopAfterCapture):
            handle_session_chat(
                session_id=session_id,
                message="Do you remember what I tend?",
                deps=deps or _deps(),
                chat_function=fake_chat,
                add_message_function=lambda *a, **k: None,
            )
    return captured["body"]


def _settings(inject: bool, rank_enabled: bool = True):
    s = get_settings().model_copy(deep=True)
    s.memory.context_inject_enabled = inject
    s.lore.rank_context_enabled = rank_enabled
    return s


def test_flag_on_injects_framed_narrative():
    body = _run_and_capture(_settings(inject=True))
    ctx = body.extra_system_context or ""
    # Wrapped in the non-echoable frame with the non-imitation preamble.
    assert ctx.startswith("<remembered>")
    assert ctx.rstrip().endswith("</remembered>")
    assert _FRAME_MARKER in ctx
    # Both prose narratives are carried.
    assert PROFILE_NAR in ctx
    assert EMOTIONAL_NAR in ctx
    # The old bullet-skeleton blocks are NOT what gets injected.
    assert PROFILE_CTX not in ctx
    assert EMOTIONAL_CTX not in ctx


def test_flag_on_excludes_nonempty_rank_block():
    # The rank block IS built (Adept -> non-empty) but must never reach the
    # injected context — that shared NEPHILIM vocabulary is what homogenized voice.
    rank_block = _build_seeker_rank_context("Adept")
    assert rank_block  # precondition: the excluded block is genuinely non-empty
    body = _run_and_capture(_settings(inject=True, rank_enabled=True))
    ctx = body.extra_system_context or ""
    assert rank_block not in ctx
    assert "<seeker_rank>" not in ctx


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

        def to_narrative_context(self):
            return ""

    class _MuteEmotionalRepo(_FakeEmotionalStateRepo):
        def get_or_create(self, session_id):
            return _MuteEmotionalState()

    deps["user_profile_repo"] = _NoProfileRepo()
    deps["emotional_state_repo"] = _MuteEmotionalRepo()

    body = _run_and_capture(_settings(inject=True), deps=deps, session_id="sess-m1-empty")
    assert body.extra_system_context is None
