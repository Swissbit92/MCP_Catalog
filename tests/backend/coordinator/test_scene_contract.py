# test_scene_contract.py
# Unit tests for the Phase-3 agentic scene-contract prompt builder (M1).

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from coordinator.tool_definitions import build_scene_contract, DEFAULT_ACTION_ALIASES
from coordinator.config import AgentSettings, get_settings


PERSONA = "You are Eeva, the Archon. Sardonic, precise."

BRAVE_TOOL = {
    "type": "function",
    "function": {
        "name": "brave_web_search",
        "description": "Reach beyond the veil for current, real-world knowledge.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
    },
}


def test_voice_only_when_no_tools():
    """Rendering stage (tools=[]) gets a pure Voice contract, no action vocab."""
    out = build_scene_contract(PERSONA, [], persona_card={})
    assert PERSONA in out
    assert "<voice_contract>" in out
    assert "<action_contract>" not in out


def test_no_raw_function_grammar_in_voice():
    """The Voice contract must never embed JSON / function-call grammar."""
    out = build_scene_contract(PERSONA, [], persona_card={})
    assert "function_call" not in out
    assert '"name"' not in out
    assert "parameters" not in out


def test_action_contract_uses_diegetic_names_not_tool_names():
    """With tools, the action list uses in-world phrases, not raw tool names."""
    out = build_scene_contract(PERSONA, [BRAVE_TOOL], persona_card={})
    assert "<action_contract>" in out
    assert "consult the Lattice" in out  # default diegetic alias
    assert "brave_web_search" not in out  # raw tool name must not leak
    assert "CHANCE TO ACT" in out  # action-first sequencing rule
    assert "AT MOST ONE action per turn" in out


def test_persona_override_alias_wins():
    """Per-persona agentic_action_aliases override the ecosystem default."""
    card = {"agentic_action_aliases": {"brave_web_search": "peer into the Aether"}}
    out = build_scene_contract(PERSONA, [BRAVE_TOOL], persona_card=card)
    assert "peer into the Aether" in out
    assert "consult the Lattice" not in out


def test_default_aliases_cover_core_tools():
    """Sanity: the default alias map covers the Phase-3 tool surface."""
    for tool in ("brave_web_search", "wallet_get_balances", "solana_propose_swap"):
        assert tool in DEFAULT_ACTION_ALIASES


def test_unknown_tool_falls_back_to_name():
    """A tool with no alias falls back to its raw name (no crash)."""
    weird = {"type": "function", "function": {"name": "mystery_tool", "description": "x"}}
    out = build_scene_contract(PERSONA, [weird], persona_card={})
    assert "mystery_tool" in out


# --- AgentSettings flag tests ---

def test_agent_settings_defaults():
    """Declared field DEFAULTS: AGENTIC_ENABLED off; safety flags on.

    Asserts the code-level defaults via model_fields so the test is independent
    of the ambient .env (a deployment may flip AGENTIC_ENABLED=true).
    """
    f = AgentSettings.model_fields
    assert f["enabled"].default is False
    assert f["argument_allowlist"].default is True
    assert f["injection_guard"].default is True
    assert 0.5 <= f["trigger_similarity_threshold"].default <= 1.0
    assert f["extraction_max_retries"].default >= 1


def test_agent_settings_nested_in_coordinator():
    """The agent subsystem is wired into CoordinatorSettings (structure, not env value)."""
    from coordinator.config import CoordinatorSettings
    assert "agent" in CoordinatorSettings.model_fields
    settings = get_settings()
    assert hasattr(settings, "agent")
    assert isinstance(settings.agent, AgentSettings)
