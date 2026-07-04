# tests/backend/coordinator/test_groundedness_gate_service.py
"""Unit tests for GroundednessGateService (ADR-007).

Headless: the LLM client is a MagicMock, flag toggled via env + settings cache clear.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.coordinator.config import get_settings
from src.coordinator.services.groundedness_gate_service import (
    GroundednessGateService,
    GroundednessVerdict,
)


@pytest.fixture(autouse=True)
def _clean_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def gate_enabled(monkeypatch):
    monkeypatch.setenv("GROUNDEDNESS_GATE_ENABLED", "true")
    get_settings.cache_clear()


@pytest.fixture
def gate_disabled(monkeypatch):
    monkeypatch.setenv("GROUNDEDNESS_GATE_ENABLED", "false")
    get_settings.cache_clear()


def _svc(complete_return="NO"):
    llm = MagicMock()
    llm.complete.return_value = complete_return
    return GroundednessGateService(llm_client=llm), llm


# ------------------------------------------------------------------ flag behavior

def test_flag_off_never_calls_classifier(gate_disabled):
    svc, llm = _svc()
    verdict = svc.check("What was their last match?", "Brazil won 4-3 after extra time.")
    assert verdict == GroundednessVerdict(should_abstain=False, reason="flag_off")
    llm.complete.assert_not_called()


def test_flag_on_ungrounded_claim_flagged(gate_enabled):
    svc, llm = _svc(complete_return="YES")
    verdict = svc.check(
        "What was their last match?",
        "Their last match was against Brazil in the Round of 16 on June 28th. "
        "They lost 4-3 after extra time.",
    )
    assert verdict.should_abstain is True
    assert verdict.reason == "ungrounded"
    llm.complete.assert_called_once()


def test_flag_on_grounded_lore_passes(gate_enabled):
    svc, llm = _svc(complete_return="NO")
    verdict = svc.check(
        "Tell me about your history",
        "I remember the Confluence — a place beyond time where all paths converged.",
    )
    assert verdict == GroundednessVerdict(should_abstain=False, reason="grounded")


def test_flag_on_general_knowledge_passes(gate_enabled):
    svc, llm = _svc(complete_return="NO")
    verdict = svc.check("What is the capital of France?", "The capital of France is Paris.")
    assert verdict.should_abstain is False


def test_classifier_exception_fails_open(gate_enabled):
    llm = MagicMock()
    llm.complete.side_effect = RuntimeError("Ollama unreachable")
    svc = GroundednessGateService(llm_client=llm)
    verdict = svc.check("What was their last match?", "Brazil won 4-3.")
    assert verdict == GroundednessVerdict(should_abstain=False, reason="classifier_error_fail_open")


# -------------------------------------------------------------------- _parse_verdict

@pytest.mark.parametrize("raw", ["YES", "yes", "Yes.", "YES, it does.", "yes\n"])
def test_parse_verdict_true_forms(raw):
    assert GroundednessGateService._parse_verdict(raw) is True


@pytest.mark.parametrize("raw", ["NO", "no", "No.", "NO, it's fine.", "", "   ", "unclear"])
def test_parse_verdict_false_forms(raw):
    assert GroundednessGateService._parse_verdict(raw) is False


def test_parse_verdict_does_not_substring_match():
    # "Yesterday" must not be misread as "YES" via naive substring matching.
    assert GroundednessGateService._parse_verdict("Yesterday would work fine.") is False


# ---------------------------------------------------------------- abstain_message

def test_abstain_message_is_fixed_and_offers_search():
    msg = GroundednessGateService.abstain_message()
    assert isinstance(msg, str) and msg
    assert "search" in msg.lower()
    # Never leak internals — must be a fixed voice-neutral string, not derived
    # from the flagged draft or user query.
    assert "Brazil" not in msg
