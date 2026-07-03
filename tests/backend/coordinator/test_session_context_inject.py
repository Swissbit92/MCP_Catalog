"""ADR-006 M0 — _assemble_capped_context (the session-context budgeter).

Headless. The helper joins non-empty context blocks (highest priority first)
within a token budget, dropping lower-priority blocks first. estimate_tokens is
patched to 1-token-per-char for deterministic budget assertions.
"""

from __future__ import annotations

from unittest.mock import patch

from src.coordinator.services.chat_session_service import _assemble_capped_context


def test_priority_order_joined_no_cap():
    assert _assemble_capped_context(["A", "B", "C"], 0) == "A\n\nB\n\nC"


def test_skips_empty_and_none_blocks():
    assert _assemble_capped_context(["A", "", "B", None, "C"], 0) == "A\n\nB\n\nC"


def test_all_empty_returns_none():
    assert _assemble_capped_context(["", "", None], 0) is None
    assert _assemble_capped_context([], 100) is None


@patch("src.coordinator.llm_client.estimate_tokens", side_effect=lambda s: len(s))
def test_cap_drops_lower_priority_first(_mock):
    # 1 token/char: AAA=3, BBB=3 -> 6 fits; CCC would make 9 > 6 -> dropped (strict priority)
    out = _assemble_capped_context(["AAA", "BBB", "CCC"], 6)
    assert out == "AAA\n\nBBB"


@patch("src.coordinator.llm_client.estimate_tokens", side_effect=lambda s: len(s))
def test_cap_keeps_highest_priority_when_first_overflows(_mock):
    # strict priority: the first block that doesn't fit stops assembly
    out = _assemble_capped_context(["AAAAA", "B"], 3)
    assert out is None  # even the top block (5) exceeds budget (3)


@patch("src.coordinator.llm_client.estimate_tokens", side_effect=lambda s: len(s))
def test_cap_zero_disables_budget(_mock):
    out = _assemble_capped_context(["A" * 50, "B" * 50], 0)
    assert out == ("A" * 50) + "\n\n" + ("B" * 50)
