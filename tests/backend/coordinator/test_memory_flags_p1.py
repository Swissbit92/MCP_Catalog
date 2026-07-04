"""ADR-006 Phase 1 — memory flag defaults must be OFF (env-independent).

Asserts model_fields defaults so an ambient .env can't mask the committed value.
Both the framed injection (M1) and the fact store (M3/M4) stay OFF until the M5
acceptance gate passes.
"""

from __future__ import annotations

from src.coordinator.config import MemorySettings


def test_context_inject_default_off():
    assert MemorySettings.model_fields["context_inject_enabled"].default is False


def test_facts_enabled_default_off():
    assert MemorySettings.model_fields["facts_enabled"].default is False


def test_fact_retrieval_defaults():
    assert MemorySettings.model_fields["facts_retrieval_k"].default == 5
    assert MemorySettings.model_fields["facts_inject_all_threshold"].default == 15
