# tests/backend/coordinator/test_tool_brain_settings.py
"""ToolBrainSettings config (ADR-008 TB1)."""
from __future__ import annotations

import pytest

from src.coordinator.config import ToolBrainSettings, get_settings


@pytest.fixture(autouse=True)
def _clean_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _tb(monkeypatch, **env):
    for k in ("TOOL_BRAIN_ENABLED", "TOOL_BRAIN_MAX_ITERATIONS",
              "TOOL_BRAIN_DETERMINISTIC_FALLBACK"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    return get_settings().tool_brain


class TestDefaults:
    def test_disabled_by_default(self, monkeypatch):
        # model_fields default is authoritative (env-independent).
        assert ToolBrainSettings.model_fields["enabled"].default is False

    def test_defaults_when_env_absent(self, monkeypatch):
        tb = _tb(monkeypatch)
        assert tb.enabled is False
        assert tb.max_iterations == 3
        assert tb.deterministic_fallback is True

    def test_registered_on_coordinator_settings(self, monkeypatch):
        tb = _tb(monkeypatch)
        assert isinstance(tb, ToolBrainSettings)


class TestEnvOverride:
    def test_enable(self, monkeypatch):
        assert _tb(monkeypatch, TOOL_BRAIN_ENABLED="true").enabled is True

    def test_iterations(self, monkeypatch):
        assert _tb(monkeypatch, TOOL_BRAIN_MAX_ITERATIONS="5").max_iterations == 5

    def test_iterations_bounds(self, monkeypatch):
        with pytest.raises(Exception):
            _tb(monkeypatch, TOOL_BRAIN_MAX_ITERATIONS="99")

    def test_fallback_toggle(self, monkeypatch):
        assert _tb(monkeypatch, TOOL_BRAIN_DETERMINISTIC_FALLBACK="false").deterministic_fallback is False
