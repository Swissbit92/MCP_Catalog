"""Tests for the lean persona system prompt (ADR-005 Phase B, flag-gated).

Hermetic: the full-prompt tests monkeypatch the persona loader + CV summarizer
so nothing hits Ollama or the on-disk persona cache. The flag-logic tests
construct PersonaPromptSettings directly so they are env-independent (the local
.env may flip the flag on).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.coordinator import prompt_builder as pb
from src.coordinator.config import PersonaPromptSettings
from src.coordinator.models.persona_schema import PersonaCard


# --------------------------------------------------------------------------
# Flag logic (env-independent — assert defaults + the use_lean_for matrix)
# --------------------------------------------------------------------------

def test_lean_flag_defaults_off():
    """Defaults must be OFF regardless of the ambient .env."""
    assert PersonaPromptSettings.model_fields["lean_enabled"].default is False
    assert PersonaPromptSettings.model_fields["lean_personas"].default == ""


def test_use_lean_for_global_flag():
    s = PersonaPromptSettings(lean_enabled=True, lean_personas="")
    assert s.use_lean_for("nephilim_eeva") is True
    assert s.use_lean_for("anything") is True
    assert s.use_lean_for(None) is True  # global flag wins even for empty key


def test_use_lean_for_allowlist_only():
    s = PersonaPromptSettings(lean_enabled=False, lean_personas="nephilim_eeva, nephilim_solace")
    assert s.use_lean_for("nephilim_eeva") is True
    assert s.use_lean_for("nephilim_solace") is True
    assert s.use_lean_for("nephilim_aegis") is False
    assert s.use_lean_for(None) is False


def test_lean_persona_set_parsing():
    s = PersonaPromptSettings(lean_personas="  a , b ,, c ,")
    assert s.lean_persona_set() == frozenset({"a", "b", "c"})
    assert PersonaPromptSettings(lean_personas="").lean_persona_set() == frozenset()


def test_default_settings_dispatch_to_legacy(monkeypatch):
    """With lean OFF, the public dispatcher returns the legacy prompt verbatim."""
    monkeypatch.setattr(pb, "get_settings", lambda: _settings(lean=False))
    pb.build_system_prompt.cache_clear()
    out = pb.build_system_prompt("Gojo")
    assert out == pb._build_system_prompt_legacy("Gojo")


def test_dispatch_to_lean_when_enabled(monkeypatch):
    monkeypatch.setattr(pb, "get_settings", lambda: _settings(lean=True))
    _patch_persona(monkeypatch, _ADVISORY_CARD)
    pb.build_system_prompt.cache_clear()
    out = pb.build_system_prompt("nephilim_test")
    assert out == pb._build_system_prompt_lean("nephilim_test")
    assert "<voice_examples>" in out


def test_cache_clear_present_and_clears_both():
    assert hasattr(pb.build_system_prompt, "cache_clear")
    # Should not raise; clears both underlying lru_caches.
    pb.build_system_prompt.cache_clear()


# --------------------------------------------------------------------------
# Lean block builders (pure — synthetic cards, no I/O)
# --------------------------------------------------------------------------

def test_voice_block_renders_signature():
    card = {
        "voice_signature": {
            "lexicon": ["triage", "objective", "discipline"],
            "cadence": "clipped declaratives, never trails off",
            "pattern": "always names the next single action",
            "anchor": "the 🛡️ before a hard call",
        }
    }
    block = pb._lean_voice_block(card)
    assert "triage" in block and "objective" in block
    assert "clipped declaratives" in block
    assert "next single action" in block
    assert "🛡️" in block


def test_voice_block_empty_without_signature():
    assert pb._lean_voice_block({}) == ""
    assert pb._lean_voice_block({"voice_signature": None}) == ""


def test_voice_examples_prefers_signature_exemplars():
    card = {
        "voice_signature": {
            "exemplars": [
                {"user": "hi", "response": "SIGNATURE REPLY"},
            ]
        },
        "example_dialogues": [
            {"user": "hi", "response": "LEGACY REPLY"},
        ],
    }
    block = pb._lean_voice_examples_block(card, "Tester")
    assert "SIGNATURE REPLY" in block
    assert "LEGACY REPLY" not in block


def test_voice_examples_falls_back_to_example_dialogues():
    card = {"example_dialogues": [{"user": "hi", "response": "FALLBACK REPLY"}]}
    block = pb._lean_voice_examples_block(card, "Tester")
    assert "FALLBACK REPLY" in block
    assert "match this voice exactly" in block


def test_voice_examples_caps_at_three():
    card = {"example_dialogues": [{"user": f"q{i}", "response": f"r{i}"} for i in range(8)]}
    block = pb._lean_voice_examples_block(card, "Tester")
    assert "r2" in block and "r3" not in block


def test_world_block_skips_non_nephilim():
    assert pb._lean_world_block({"key": "gojo"}) == ""


def test_world_block_no_wiki_dump():
    card = {
        "key": "nephilim_test",
        "title": "The Tester",
        "archetype": "The Probe",
        "domain": "testing",
        "nephilim_lore": {"origin": "x" * 500},
    }
    block = pb._lean_world_block(card)
    assert "Seeker" in block
    assert "The Tester" in block
    # The 500-char origin / wiki body must NOT be dumped into the lean prompt.
    assert "x" * 100 not in block
    assert "Extended Realm Context" not in block


def test_wallet_lean_block_keeps_hard_guards():
    block = pb._get_wallet_copilot_block_lean()
    assert "I cannot and will not" in block
    assert "Jupiter DEX" in block
    assert "Never invent" in block


# --------------------------------------------------------------------------
# Full lean prompt (hermetic via monkeypatch)
# --------------------------------------------------------------------------

def test_lean_prompt_is_smaller_and_keeps_guards(monkeypatch):
    _patch_persona(monkeypatch, _ADVISORY_CARD)
    pb._build_system_prompt_lean.cache_clear()
    pb._build_system_prompt_legacy.cache_clear()
    lean = pb._build_system_prompt_lean("nephilim_test")
    legacy = pb._build_system_prompt_legacy("nephilim_test")

    # Structurally leaner.
    assert len(lean.split()) < len(legacy.split())

    # Guards preserved.
    assert "first person" in lean.lower()
    assert "I cannot and will not" in lean
    assert "Seeker" in lean
    assert "<safety>" in lean and "<checklist>" in lean
    # Voice-last: exemplars are the final structured section.
    assert lean.index("<voice_examples>") > lean.index("<safety>")


def test_lean_prompt_drops_wiki_extended_context(monkeypatch):
    _patch_persona(monkeypatch, _ADVISORY_CARD)
    pb._build_system_prompt_lean.cache_clear()
    lean = pb._build_system_prompt_lean("nephilim_test")
    assert "Extended Realm Context" not in lean


def test_lean_prompt_wallet_section_only_for_wallet_personas(monkeypatch):
    _patch_persona(monkeypatch, {**_ADVISORY_CARD, "mcp_access": []})
    pb._build_system_prompt_lean.cache_clear()
    assert "<tools>" not in pb._build_system_prompt_lean("nephilim_test")

    _patch_persona(monkeypatch, {**_ADVISORY_CARD, "mcp_access": ["solana_wallet"]})
    pb._build_system_prompt_lean.cache_clear()
    assert "<tools>" in pb._build_system_prompt_lean("nephilim_test")


# --------------------------------------------------------------------------
# Helpers / fixtures
# --------------------------------------------------------------------------

_ADVISORY_CARD = {
    "key": "nephilim_test",
    "display_name": "Tester — The Probe",
    "style": "precise, calm",
    "title": "The Tester",
    "archetype": "The Probe",
    "domain": "testing",
    "mcp_access": [],
    "nephilim_lore": {"origin": "Born in the test harness.", "role_in_realm": "QA"},
    "behavior": {"traits": ["precise", "calm"], "pace": "moderate", "humor": "dry"},
    "emotional_profile": {"baseline": "steady and present"},
    "dialogue_prefs": {"reply_shape": "assess → answer"},
    "psychological_profile": {"contradiction_pairs": ["Confident | quietly unsure"]},
    "example_dialogues": [
        {"user": "Are you sure?", "response": "I am. Here is why."},
        {"user": "What now?", "response": "One step: start here."},
    ],
}


def _patch_persona(monkeypatch, card):
    monkeypatch.setattr(pb, "resolve_persona_to_card", lambda sel: card)
    monkeypatch.setattr(
        pb, "get_or_build_cv_summary", lambda sel: {"summary": "I am the Tester, a calm probe."}
    )


class _Prompt:
    def __init__(self, lean):
        self.lean_enabled = lean
        self.lean_personas = ""

    def lean_persona_set(self):
        return frozenset()

    def use_lean_for(self, key):
        return self.lean_enabled


class _Settings:
    def __init__(self, lean):
        self.prompt = _Prompt(lean)


def _settings(lean):
    return _Settings(lean)


# --------------------------------------------------------------------------
# Milestone 2 — authored voice_signature data for the advisory cluster
# --------------------------------------------------------------------------

_PERSONA_DIR = Path(__file__).resolve().parents[3] / "personas"
_ADVISORY = ["nephilim_eeva", "nephilim_aegis", "nephilim_solace"]


def _load_card(key):
    return json.loads((_PERSONA_DIR / f"{key}.json").read_text())


@pytest.mark.parametrize("key", _ADVISORY)
def test_advisory_persona_has_valid_voice_signature(key):
    card = _load_card(key)
    parsed = PersonaCard(**card)  # schema must accept the new field
    vs = parsed.voice_signature
    assert vs is not None
    assert vs.lexicon and vs.cadence and vs.pattern and vs.anchor
    assert len(vs.exemplars) == 3  # first 3 are injected voice-last


def test_voice_signature_excluded_from_cv_fingerprint():
    """Adding/removing voice_signature must NOT change the CV-summary hash.

    Otherwise every cached summary goes stale and the legacy <identity> text
    drifts on rebuild — invalidating the frozen baseline.
    """
    from src.coordinator.cv_summarizer import _fingerprint

    base = _load_card("nephilim_eeva")
    without = {k: v for k, v in base.items() if k != "voice_signature"}
    with_sig = {**without, "voice_signature": {"lexicon": ["x"], "cadence": "y"}}
    assert _fingerprint(without) == _fingerprint(with_sig)


def test_advisory_voice_blocks_are_distinct():
    """The three advisory personas must carry distinct anchors/diction."""
    blocks = {k: pb._lean_voice_block(_load_card(k)) for k in _ADVISORY}
    assert "Confluence" in blocks["nephilim_eeva"]
    assert "triage" in blocks["nephilim_aegis"]
    assert "Sanctuary" in blocks["nephilim_solace"] or "breath" in blocks["nephilim_solace"]
    # No two blocks identical.
    vals = list(blocks.values())
    assert len(set(vals)) == 3


def test_eeva_exemplars_no_longer_route_to_solace():
    """The de-collision fix: Eeva's injected exemplars stop deferring to Solace."""
    block = pb._lean_voice_examples_block(_load_card("nephilim_eeva"), "E.E.V.A.")
    assert "connect you with Solace" not in block
    assert "Confluence" in block  # her unique register instead


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
