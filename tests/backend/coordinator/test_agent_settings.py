# test_agent_settings.py
# Declared-default tests for AgentSettings — the deterministic tool-call safety
# flags that outlived the ADR-004 two-stage pipeline (retired 2026-07-19).
# The scene-contract tests that used to live here went with build_scene_contract,
# whose only caller was that pipeline.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from coordinator.config import AgentSettings, get_settings


# --- AgentSettings flag tests ---

def test_agent_settings_defaults():
    """Declared field DEFAULTS: the surviving safety flags are ON.

    Asserts the code-level defaults via model_fields so the test is independent
    of the ambient .env.
    """
    f = AgentSettings.model_fields
    assert f["argument_allowlist"].default is True
    assert f["injection_guard"].default is True


def test_agent_settings_drops_retired_pipeline_fields():
    """The ADR-004 pipeline's own settings are gone, not merely defaulted off.

    Guards against a silent re-introduction: `enabled` (AGENTIC_ENABLED) and the
    argument-extraction knobs were retired with the two-stage pipeline.
    """
    f = AgentSettings.model_fields
    for retired in (
        "enabled",
        "trigger_similarity_threshold",
        "extraction_coherence_threshold",
        "extraction_max_retries",
    ):
        assert retired not in f, f"retired AgentSettings field reappeared: {retired}"


def test_agent_settings_nested_in_coordinator():
    """The agent subsystem is wired into CoordinatorSettings (structure, not env value)."""
    from coordinator.config import CoordinatorSettings
    assert "agent" in CoordinatorSettings.model_fields
    settings = get_settings()
    assert hasattr(settings, "agent")
    assert isinstance(settings.agent, AgentSettings)
