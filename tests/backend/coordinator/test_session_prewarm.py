"""Tests for ADR-006 M1 session-index pre-warm (startup.prewarm_session_indexes).

Headless — mocks the rag + repos. Verifies the pre-warm re-indexes the most
recent sessions from SQLite, respects the limit, skips empty/failed sessions,
and is a no-op when disabled.
"""

from __future__ import annotations

from unittest.mock import Mock

from src.coordinator.startup import prewarm_session_indexes


def _session(sid, count):
    return {"id": sid, "message_count": count}


def test_noop_when_rag_none():
    repo = Mock()
    assert prewarm_session_indexes(None, repo, repo, 10) == 0
    repo.get_all_sessions.assert_not_called()


def test_noop_when_limit_zero():
    rag = Mock()
    session_repo = Mock()
    msg_repo = Mock()
    assert prewarm_session_indexes(rag, session_repo, msg_repo, 0) == 0
    rag.index_session.assert_not_called()


def test_warms_recent_nonempty_sessions_up_to_limit():
    rag = Mock()
    session_repo = Mock()
    session_repo.get_all_sessions.return_value = [
        _session("s1", 4), _session("s2", 2), _session("s3", 6),
    ]
    msg_repo = Mock()
    msg_repo.get_messages_by_session.side_effect = lambda sid: [
        {"id": f"{sid}-1", "role": "user", "content": "hi", "timestamp": "t"}
    ]

    warmed = prewarm_session_indexes(rag, session_repo, msg_repo, 2)

    assert warmed == 2  # limited to first 2 sessions
    assert rag.index_session.call_count == 2
    called_sids = [c.args[0] for c in rag.index_session.call_args_list]
    assert called_sids == ["s1", "s2"]


def test_skips_empty_sessions():
    rag = Mock()
    session_repo = Mock()
    session_repo.get_all_sessions.return_value = [
        _session("empty", 0), _session("full", 3),
    ]
    msg_repo = Mock()
    msg_repo.get_messages_by_session.return_value = [
        {"id": "full-1", "role": "user", "content": "hi", "timestamp": "t"}
    ]

    warmed = prewarm_session_indexes(rag, session_repo, msg_repo, 10)

    assert warmed == 1
    rag.index_session.assert_called_once()
    assert rag.index_session.call_args.args[0] == "full"


def test_one_failing_session_does_not_abort_rest():
    rag = Mock()
    session_repo = Mock()
    session_repo.get_all_sessions.return_value = [
        _session("bad", 2), _session("good", 2),
    ]
    msg_repo = Mock()

    def _msgs(sid):
        if sid == "bad":
            raise RuntimeError("db hiccup")
        return [{"id": "good-1", "role": "user", "content": "hi", "timestamp": "t"}]

    msg_repo.get_messages_by_session.side_effect = _msgs

    warmed = prewarm_session_indexes(rag, session_repo, msg_repo, 10)

    assert warmed == 1
    assert rag.index_session.call_args.args[0] == "good"
