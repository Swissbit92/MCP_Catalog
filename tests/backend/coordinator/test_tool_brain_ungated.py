# test_tool_brain_ungated.py
"""Guards for TOOL_BRAIN_UNGATED_WEB (Hermes-style ungated web tools).

The flag lets the native tool-brain loop engage on NEEDS_NEITHER turns so the
model — not the bge-m3 router's 0.66 threshold — decides whether a lookup is
warranted. The tool-firing eval measured the router silently blocking real web
queries (0.49-0.61 vs the 0.66 threshold), which the model never got a chance
to correct because it was never offered a tool.

Two invariants matter more than the feature itself and are asserted here:
  1. WALLET is never ungated, in either mode. TB5's live failure was wallet
     fixation; a false positive there costs more than a missed search.
  2. Default OFF is byte-identical TB5 behaviour.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from coordinator.config import ToolBrainSettings  # noqa: E402
from coordinator.routes import chat as chat_mod  # noqa: E402
from coordinator.tools.intent_classifier import QueryIntent  # noqa: E402


def _settings(*, enabled=True, ungated=False):
    s = MagicMock()
    s.tool_brain.enabled = enabled
    s.tool_brain.ungated_web = ungated
    return s


def _call(intent, *, ungated):
    """Invoke _try_tool_brain far enough to observe the gate decision."""
    with patch.object(chat_mod, "get_settings", return_value=_settings(ungated=ungated)):
        return chat_mod._try_tool_brain(
            card={"key": "eeva"}, system="sys", body=MagicMock(message="hi"),
            history=[], intent=intent, metadata=MagicMock(),
            persona_name="EEVA", deps={},
        )


# --- flag declaration --------------------------------------------------------


def test_ungated_web_defaults_off():
    """Default OFF keeps TB5 behaviour — the flag is the revert path."""
    assert ToolBrainSettings.model_fields["ungated_web"].default is False


def test_ungated_web_alias():
    assert ToolBrainSettings.model_fields["ungated_web"].alias == "TOOL_BRAIN_UNGATED_WEB"


# --- the gate ----------------------------------------------------------------


def test_wallet_never_enters_native_surface_when_gated():
    assert _call(QueryIntent.NEEDS_WALLET, ungated=False) is None


def test_wallet_never_enters_native_surface_when_ungated():
    """The non-negotiable invariant: ungating web must NOT ungate wallet.

    If this ever fails, the TB5 wallet-fixation failure is back.
    """
    assert _call(QueryIntent.NEEDS_WALLET, ungated=True) is None


def test_needs_neither_short_circuits_when_gated():
    """Gated mode: NEEDS_NEITHER returns None before any model call."""
    assert _call(QueryIntent.NEEDS_NEITHER, ungated=False) is None


def test_needs_neither_proceeds_past_the_gate_when_ungated():
    """Ungated mode: NEEDS_NEITHER is no longer short-circuited at the gate.

    Asserted by observing that execution reaches the registry lookup — with a
    card that grants no web tools it still returns None, but for the DIFFERENT
    reason ("no web tools"), which proves the intent gate was passed.
    """
    with patch.object(chat_mod, "get_settings", return_value=_settings(ungated=True)), \
            patch("coordinator.tools.registry.registry.specs_for_persona") as specs:
        specs.return_value = []
        out = chat_mod._try_tool_brain(
            card={"key": "eeva"}, system="sys", body=MagicMock(message="hi"),
            history=[], intent=QueryIntent.NEEDS_NEITHER, metadata=MagicMock(),
            persona_name="EEVA", deps={},
        )
        assert out is None
        specs.assert_called_once()  # gate passed; it got as far as tool lookup


def test_gated_mode_does_not_reach_registry_on_needs_neither():
    """Counterpart to the above — proves the previous test's signal is real."""
    with patch.object(chat_mod, "get_settings", return_value=_settings(ungated=False)), \
            patch("coordinator.tools.registry.registry.specs_for_persona") as specs:
        chat_mod._try_tool_brain(
            card={"key": "eeva"}, system="sys", body=MagicMock(message="hi"),
            history=[], intent=QueryIntent.NEEDS_NEITHER, metadata=MagicMock(),
            persona_name="EEVA", deps={},
        )
        specs.assert_not_called()


# --- search-trigger guidance -------------------------------------------------


def test_guidance_block_names_concrete_triggers_not_vague_advice():
    """Vague "use tools when helpful" is what left the 24B answering from weights."""
    g = chat_mod._SEARCH_TRIGGER_GUIDANCE.lower()
    for trigger in ("current", "recent", "latest", "price"):
        assert trigger in g, f"guidance omits trigger: {trigger}"


def test_guidance_block_excludes_persona_and_conversation_topics():
    """Must tell the model NOT to search its own feelings/lore.

    "how are you feeling today?" scored 0.70 against a market-news anchor and
    triggered a real web search — the guidance has to push back on exactly that.
    """
    g = chat_mod._SEARCH_TRIGGER_GUIDANCE.lower()
    assert "do not search" in g
    for excluded in ("feel", "lore", "conversation"):
        assert excluded in g, f"guidance omits exclusion: {excluded}"


def test_guidance_carries_no_voice_language():
    """It steers tool choice only — persona voice is the ADR-005 prompt's job.

    Voice words here would compete with voice_signature for attention, which is
    the mechanism prompt bloat uses to flatten personas.
    """
    g = chat_mod._SEARCH_TRIGGER_GUIDANCE.lower()
    for banned in ("persona", "in character", "your voice", "roleplay"):
        assert banned not in g
