"""ADR-006 M4 — hermetic integration test: fact-store narrative reaches the LLM.

Drives handle_session_chat with MEMORY_FACTS_ENABLED and a real (tmp) fact store
seeded with facts; asserts the framed <remembered> block carries the rendered fact
narrative. build_system_prompt is mocked (no Ollama).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.coordinator.config import get_settings
from src.coordinator.services.chat_session_service import handle_session_chat
from src.coordinator.repositories.memory_fact_repository import MemoryFactRepository


class _Stop(Exception):
    pass


class _SessionRepo:
    def get_persona_key(self, session_id):
        return "nephilim_eeva"


class _MsgRepo:
    def get_messages_by_session(self, session_id):
        return []


class _SummaryRepo:
    def get_summaries_by_session(self, session_id):
        return []


class _EmoState:
    trust_level = 0.7
    current_mood = "calm"
    mood_intensity = 0.5

    def to_prompt_context(self):
        return ""

    def to_narrative_context(self):
        return ""


class _EmoRepo:
    def get_or_create(self, session_id):
        return _EmoState()


class _MemMgr:
    def select_messages(self, messages, token_budget, system_prompt_tokens):
        return []


class _ProfileRepo:
    def get_session_user(self, session_id):
        return "user-raphael"

    def get_profile(self, user_id):
        return None  # rely on the fact store, not the legacy blob


@pytest.fixture()
def deps(tmp_path):
    repo = MemoryFactRepository(db_path=str(tmp_path / "facts.db"))
    subj = repo.get_or_create_entity("user-raphael", "self", "self")
    repo.add_fact("user-raphael", subj, "has_name", "Raphael")
    repo.add_fact("user-raphael", subj, "is_learning", "Rust")
    return {
        "session_repo": _SessionRepo(),
        "message_repo": _MsgRepo(),
        "summary_repo": _SummaryRepo(),
        "emotional_state_repo": _EmoRepo(),
        "memory_manager": _MemMgr(),
        "user_profile_repo": _ProfileRepo(),
        "episodic_memory_rag": None,
        "fact_extractor": None,
        "fact_extraction_worker": None,
        "memory_fact_repo": repo,
        "seeker_progression_repo": None,
    }


def _settings(facts_enabled):
    s = get_settings().model_copy(deep=True)
    s.memory.facts_enabled = facts_enabled
    s.memory.context_inject_enabled = False  # isolate the M4 path
    return s


def _run(settings, deps):
    captured = {}

    def fake_chat(body):
        captured["body"] = body
        raise _Stop()

    with patch("src.coordinator.services.chat_session_service.get_settings", return_value=settings), \
         patch("src.coordinator.services.chat_session_service.build_system_prompt", return_value="<identity>x</identity>"):
        with pytest.raises(_Stop):
            handle_session_chat("sess-m4", "What am I learning?", deps, fake_chat, lambda *a, **k: None)
    return captured["body"]


def test_facts_narrative_injected_when_enabled(deps):
    body = _run(_settings(facts_enabled=True), deps)
    ctx = body.extra_system_context or ""
    assert ctx.startswith("<remembered>")
    assert "their name is Raphael" in ctx
    assert "they're learning Rust" in ctx


def test_no_injection_when_facts_disabled(deps):
    body = _run(_settings(facts_enabled=False), deps)
    assert body.extra_system_context is None
