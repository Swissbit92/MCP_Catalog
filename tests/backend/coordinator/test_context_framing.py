"""ADR-006 M1 — unit tests for per-persona context framing + prose narratives.

Pure/hermetic: no Ollama, no DB. Covers context_framing.frame_injected_context and
the narrative variants on UserProfile / EmotionalState.
"""

from __future__ import annotations

from src.coordinator.context_framing import frame_injected_context
from src.coordinator.user_profile import UserProfile
from src.coordinator.repositories.emotional_state_repository import EmotionalState


def test_frame_none_on_empty_body():
    assert frame_injected_context("nephilim_eeva", {"display_name": "E.E.V.A."}, "") is None
    assert frame_injected_context("nephilim_eeva", {"display_name": "E.E.V.A."}, "   ") is None
    assert frame_injected_context("nephilim_eeva", {"display_name": "E.E.V.A."}, None) is None


def test_frame_wraps_and_names_persona():
    out = frame_injected_context(
        "nephilim_eeva", {"display_name": "E.E.V.A. — The Primarch"}, "You remember them."
    )
    assert out.startswith("<remembered>")
    assert out.rstrip().endswith("</remembered>")
    assert "E.E.V.A. — The Primarch" in out          # per-persona name in the frame
    assert "never recite it back as a list" in out    # non-imitation instruction
    assert "You remember them." in out                # body preserved


def test_frame_falls_back_to_key_without_card():
    out = frame_injected_context("nephilim_nyx", None, "Body.")
    assert "nephilim_nyx" in out


def test_frame_differs_by_persona():
    a = frame_injected_context("nephilim_eeva", {"display_name": "E.E.V.A."}, "X")
    b = frame_injected_context("nephilim_nyx", {"display_name": "Nyx"}, "X")
    # Same body, different persona → different framed text (breaks the uniform block).
    assert a != b


def test_profile_narrative_is_prose_not_bullets():
    up = UserProfile("u1")
    up.data["name"] = "Raphael"
    up.data["total_sessions"] = 4
    up.data["total_messages"] = 37
    up.data["facts"] = ["tends the trading engine"]
    up.data["topics_discussed"] = {"crypto": 5, "memory": 2}
    nar = up.get_narrative_context()
    assert "Raphael" in nar
    assert "tends the trading engine" in nar
    # Prose, not the bullet skeleton.
    assert "\n- " not in nar
    assert "**" not in nar


def test_profile_narrative_empty_when_nothing_known():
    up = UserProfile("u2")
    assert up.get_narrative_context() == ""


def test_emotional_narrative_is_prose():
    es = EmotionalState(session_id="s1")
    es.trust_level = 0.7
    es.current_mood = "contemplative"
    es.mood_intensity = 0.5
    nar = es.to_narrative_context()
    assert "contemplative" in nar
    assert "\n- " not in nar
    # No accidental double "between you".
    assert "between you between you" not in nar
    assert "warm between you" not in nar


def test_emotional_narrative_trust_tiers():
    es = EmotionalState(session_id="s2")
    es.current_mood = "calm"
    for lvl in (0.05, 0.25, 0.45, 0.65, 0.85):
        es.trust_level = lvl
        assert es.to_narrative_context().startswith("The bond between you is")
