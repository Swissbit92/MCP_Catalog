# test_history_cap.py
# Regression test for the ChatBody.history>100 500 bug: token-budget message
# selection could exceed the ChatBody count guard, 500ing long sessions at
# internal ChatBody construction. _assemble_capped_history must bound the result.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from coordinator.schemas import ChatBody, ChatTurn, MAX_HISTORY_TURNS
from coordinator.services.chat_session_service import _assemble_capped_history


def _turns(n, prefix="m"):
    return [ChatTurn(role="user" if i % 2 == 0 else "assistant",
                     content=f"{prefix}{i}") for i in range(n)]


def test_no_cap_when_under_limit():
    raw = _turns(10)
    out = _assemble_capped_history(raw)
    assert len(out) == 10
    assert out == raw  # unchanged


def test_caps_to_max_without_summary():
    raw = _turns(150)
    out = _assemble_capped_history(raw)
    assert len(out) == MAX_HISTORY_TURNS
    # keeps the MOST RECENT turns
    assert out[-1].content == "m149"
    assert out[0].content == f"m{150 - MAX_HISTORY_TURNS}"


def test_caps_with_summary_reserves_one_slot():
    raw = _turns(150)
    summary = ChatTurn(role="assistant", content="[Context from earlier]")
    out = _assemble_capped_history(raw, summary)
    assert len(out) == MAX_HISTORY_TURNS  # summary + (MAX-1) raw
    assert out[0] is summary  # summary first (primacy)
    assert out[-1].content == "m149"  # most-recent raw last
    assert sum(1 for t in out if t is summary) == 1


def test_result_always_constructs_valid_chatbody():
    """The whole point: the capped history must never 500 ChatBody validation."""
    raw = _turns(500)  # far over the cap (the old bug: 105 already 500'd)
    summary = ChatTurn(role="assistant", content="[Context]")
    out = _assemble_capped_history(raw, summary)
    # Must not raise pydantic ValidationError (too_long)
    body = ChatBody(persona="nephilim_eeva", history=out, message="hi")
    assert len(body.history) <= MAX_HISTORY_TURNS


def test_exactly_at_limit_unchanged():
    raw = _turns(MAX_HISTORY_TURNS)
    out = _assemble_capped_history(raw)
    assert len(out) == MAX_HISTORY_TURNS
    assert out[-1].content == f"m{MAX_HISTORY_TURNS - 1}"


def test_chatbody_still_rejects_oversized_external_payload():
    """The external request guard is intact — a client can't send >MAX turns."""
    import pytest
    with pytest.raises(Exception):
        ChatBody(history=_turns(MAX_HISTORY_TURNS + 5), message="x")
