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


# ------------------------------------------------- classifier prompt (2026-08-12)

from src.coordinator.services.groundedness_gate_service import (  # noqa: E402
    _classifier_system,
)


def test_live_state_clause_is_present_by_default_and_removable():
    """The measured blind spot: the gate passed 'your position is currently
    unhedged' 5/5 because that is not a score/date/statistic about a real-world
    EVENT. The clause closes it; the flag keeps the old trigger reachable."""
    on = _classifier_system(live_state=True)
    off = _classifier_system(live_state=False)
    assert "hedged or unhedged" in on and "balance" in on
    assert "hedged or unhedged" not in off
    # Everything else must be identical — the flag isolates one clause.
    assert len(on) > len(off)


def test_reasoning_over_user_supplied_numbers_is_explicitly_excluded():
    """The measured false-abstain: interpretive sentences over the USER's own
    figures. Two of the destroyed answers had no digits, so a numeral rule
    would not have helped — the exclusion has to name the concept."""
    for s in (_classifier_system(True), _classifier_system(False)):
        assert "THE USER SUPPLIED" in s
        assert "0.7" in s  # the concrete anchor example
        assert "mechanism" in s


def test_classifier_is_told_to_judge_the_premise_not_the_argument():
    """The adversarial case: valid reasoning from an invented figure. Without
    this the judge grades 'is this reasoning?' and waves the premise through."""
    s = _classifier_system(True)
    assert "PREMISE" in s
    assert "fabricated figure" in s


def test_check_honours_the_live_state_flag(gate_enabled, monkeypatch):
    monkeypatch.setenv("GROUNDEDNESS_LIVE_STATE_CLAIMS", "false")
    get_settings.cache_clear()
    client = MagicMock()
    client.complete.return_value = "NO"
    GroundednessGateService(llm_client=client).check("q", "draft")
    system_arg = client.complete.call_args[0][0]
    assert "hedged or unhedged" not in system_arg


def test_full_draft_is_logged_when_the_gate_destroys_it(gate_enabled, caplog):
    """Until 2026-08-12 only 80 chars were kept, so when the gate was found to
    be binning good analysis the evidence had to be reconstructed from a
    separate run. An unauditable safety control cannot be tuned."""
    import logging

    long_draft = "The mechanism is fee drag. " * 20  # ~540 chars
    client = MagicMock()
    client.complete.return_value = "YES"
    with caplog.at_level(logging.WARNING,
                         logger="src.coordinator.services.groundedness_gate_service"):
        GroundednessGateService(llm_client=client).check("why?", long_draft)
    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert long_draft in logged, "the destroyed draft must be recoverable from logs"


def test_classifier_temperature_defaults_to_zero():
    """A safety classifier that returns different verdicts for identical input
    cannot be tuned. Measured: flip_rate 0.10 -> 0.00."""
    assert get_settings().groundedness.classifier_temperature == 0.0
