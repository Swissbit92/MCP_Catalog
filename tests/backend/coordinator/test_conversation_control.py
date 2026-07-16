"""
Unit tests for ADR-011 conversation-control verbs (M1: Tier 2 + session metadata).

Covers:
- MessageRepository.delete_message (real tmp SQLite)
- services/conversation_control_service.py logic (mocked repos + handle_session_chat)
- routes: POST /sessions/{id}/regenerate|continue|undo, GET /sessions/{id}/meta
"""
from __future__ import annotations

import sys
import tempfile
import os
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from fastapi.testclient import TestClient
from src.coordinator.server import app
from src.coordinator.repositories.message_repository import MessageRepository
from src.coordinator.services import conversation_control_service as ccs

client = TestClient(app)


# ─── MessageRepository.delete_message ────────────────────────────────────────

def _fresh_message_repo():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE messages (
            id TEXT PRIMARY KEY, session_id TEXT NOT NULL, role TEXT NOT NULL,
            content TEXT NOT NULL, timestamp TEXT NOT NULL, latency_ms INTEGER,
            source_type TEXT DEFAULT 'llm', multi_message_id TEXT, multi_message_index INTEGER
        )""")
    conn.commit()
    conn.close()
    return MessageRepository(db_path), db_path


def test_delete_message_removes_one_row():
    repo, db_path = _fresh_message_repo()
    try:
        mid1 = repo.create_message("s1", "user", "hi")
        mid2 = repo.create_message("s1", "assistant", "hello")
        assert repo.delete_message(mid2) is True
        remaining = repo.get_messages_by_session("s1")
        assert [m["id"] for m in remaining] == [mid1]
    finally:
        os.path.exists(db_path) and os.unlink(db_path)


def test_delete_message_missing_returns_false():
    repo, db_path = _fresh_message_repo()
    try:
        assert repo.delete_message("does-not-exist") is False
    finally:
        os.path.exists(db_path) and os.unlink(db_path)


# ─── _split_last_exchange ────────────────────────────────────────────────────

def test_split_user_then_single_assistant():
    msgs = [{"id": "u1", "role": "user"}, {"id": "a1", "role": "assistant"}]
    last_user, trailing = ccs._split_last_exchange(msgs)
    assert last_user["id"] == "u1"
    assert [m["id"] for m in trailing] == ["a1"]


def test_split_user_then_multi_assistant():
    msgs = [
        {"id": "u1", "role": "user"},
        {"id": "a1", "role": "assistant"},
        {"id": "a2", "role": "assistant"},
    ]
    last_user, trailing = ccs._split_last_exchange(msgs)
    assert last_user["id"] == "u1"
    assert [m["id"] for m in trailing] == ["a1", "a2"]


def test_split_lone_greeting_has_no_user():
    msgs = [{"id": "a1", "role": "assistant"}]
    last_user, trailing = ccs._split_last_exchange(msgs)
    assert last_user is None
    assert [m["id"] for m in trailing] == ["a1"]


def test_split_trailing_user_no_reply():
    msgs = [{"id": "u1", "role": "user"}]
    last_user, trailing = ccs._split_last_exchange(msgs)
    assert last_user["id"] == "u1"
    assert trailing == []


# ─── undo_last_exchange ──────────────────────────────────────────────────────

def _repos(messages=None, exists=True, session=None, persona_key="gwen"):
    sr = MagicMock()
    sr.session_exists.return_value = exists
    sr.get_session.return_value = session if session is not None else {
        "id": "s1", "persona_key": persona_key, "title": "T",
        "created_at": "2026-01-01", "updated_at": "2026-01-01",
    }
    mr = MagicMock()
    mr.get_messages_by_session.return_value = messages or []
    mr.count_messages_by_session.return_value = len(messages or [])
    return sr, mr


def test_undo_deletes_user_and_reply():
    sr, mr = _repos([
        {"id": "u1", "role": "user"}, {"id": "a1", "role": "assistant"},
    ])
    out = ccs.undo_last_exchange(sr, mr, "s1")
    assert out == {"ok": True, "deleted": 2}
    deleted = {c.args[0] for c in mr.delete_message.call_args_list}
    assert deleted == {"u1", "a1"}


def test_undo_empty_session_noop():
    sr, mr = _repos([])
    out = ccs.undo_last_exchange(sr, mr, "s1")
    assert out == {"ok": True, "deleted": 0}
    mr.delete_message.assert_not_called()


def test_undo_missing_session_404():
    sr, mr = _repos(exists=False)
    with pytest.raises(Exception) as e:
        ccs.undo_last_exchange(sr, mr, "bad")
    assert getattr(e.value, "status_code", None) == 404


# ─── get_session_meta ────────────────────────────────────────────────────────

def test_get_session_meta_shape():
    sr, mr = _repos([{"id": "u1", "role": "user"}], persona_key="gwen")
    with patch.object(ccs, "get_persona_card", return_value={"display_name": "Gwen", "nsfw": True}):
        meta = ccs.get_session_meta(sr, mr, "s1")
    assert meta["persona_key"] == "gwen"
    assert meta["display_name"] == "Gwen"
    assert meta["nsfw"] is True
    assert meta["message_count"] == 1


def test_get_session_meta_missing_404():
    sr, mr = _repos(session=False)
    sr.get_session.return_value = None
    with pytest.raises(Exception) as e:
        ccs.get_session_meta(sr, mr, "bad")
    assert getattr(e.value, "status_code", None) == 404


# ─── regenerate / continue (service, handle_session_chat mocked) ─────────────

def test_regenerate_drops_reply_and_reruns():
    sr, mr = _repos([
        {"id": "u1", "role": "user", "content": "hi"},
        {"id": "a1", "role": "assistant", "content": "old"},
    ])
    deps = {"session_repo": sr, "message_repo": mr}
    with patch.object(ccs, "handle_session_chat", return_value={"answer": "new"}) as h:
        out = ccs.regenerate_last_reply("s1", deps, MagicMock(), MagicMock())
    assert out == {"answer": "new"}
    mr.delete_message.assert_called_once_with("a1")
    kwargs = h.call_args.kwargs
    assert kwargs["message"] == "hi"
    assert kwargs["persist_user"] is False
    assert kwargs["run_post_turn_updates"] is False


def test_regenerate_no_user_message_400():
    sr, mr = _repos([{"id": "a1", "role": "assistant", "content": "greeting"}])
    deps = {"session_repo": sr, "message_repo": mr}
    with pytest.raises(Exception) as e:
        ccs.regenerate_last_reply("s1", deps, MagicMock(), MagicMock())
    assert getattr(e.value, "status_code", None) == 400


def test_continue_uses_synthetic_instruction():
    sr, mr = _repos([
        {"id": "u1", "role": "user", "content": "hi"},
        {"id": "a1", "role": "assistant", "content": "reply"},
    ])
    deps = {"session_repo": sr, "message_repo": mr}
    with patch.object(ccs, "handle_session_chat", return_value={"answer": "more"}) as h:
        out = ccs.continue_last_reply("s1", deps, MagicMock(), MagicMock())
    assert out == {"answer": "more"}
    kwargs = h.call_args.kwargs
    assert kwargs["message"] == ccs.CONTINUE_INSTRUCTION
    assert kwargs["persist_user"] is False
    mr.delete_message.assert_not_called()


def test_continue_no_reply_400():
    sr, mr = _repos([{"id": "u1", "role": "user", "content": "hi"}])
    deps = {"session_repo": sr, "message_repo": mr}
    with pytest.raises(Exception) as e:
        ccs.continue_last_reply("s1", deps, MagicMock(), MagicMock())
    assert getattr(e.value, "status_code", None) == 400


# ─── Routes (TestClient) ─────────────────────────────────────────────────────

def test_route_undo_happy():
    sr, mr = _repos([{"id": "u1", "role": "user"}, {"id": "a1", "role": "assistant"}])
    with patch("src.coordinator.routes.sessions._get_repos", return_value=(sr, mr, MagicMock())):
        resp = client.post("/sessions/s1/undo")
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 2


def test_route_undo_404():
    sr, mr = _repos(exists=False)
    with patch("src.coordinator.routes.sessions._get_repos", return_value=(sr, mr, MagicMock())):
        resp = client.post("/sessions/bad/undo")
    assert resp.status_code == 404


def test_route_meta_happy():
    sr, mr = _repos([{"id": "u1", "role": "user"}], persona_key="gwen")
    with patch("src.coordinator.routes.sessions._get_repos", return_value=(sr, mr, MagicMock())), \
         patch.object(ccs, "get_persona_card", return_value={"display_name": "Gwen", "nsfw": True}):
        resp = client.get("/sessions/s1/meta")
    assert resp.status_code == 200
    body = resp.json()
    assert body["persona_key"] == "gwen" and body["nsfw"] is True


def test_route_regenerate_happy():
    sr, mr = _repos([
        {"id": "u1", "role": "user", "content": "hi"},
        {"id": "a1", "role": "assistant", "content": "old"},
    ])
    deps = {"session_repo": sr, "message_repo": mr}
    with patch("src.coordinator.routes.chat._get_dependencies", return_value=deps), \
         patch.object(ccs, "handle_session_chat", return_value={"answer": "new", "message_flow": "single"}):
        resp = client.post("/sessions/s1/regenerate")
    assert resp.status_code == 200
    assert resp.json()["answer"] == "new"
    mr.delete_message.assert_called_once_with("a1")


def test_route_continue_happy():
    sr, mr = _repos([
        {"id": "u1", "role": "user", "content": "hi"},
        {"id": "a1", "role": "assistant", "content": "reply"},
    ])
    deps = {"session_repo": sr, "message_repo": mr}
    with patch("src.coordinator.routes.chat._get_dependencies", return_value=deps), \
         patch.object(ccs, "handle_session_chat", return_value={"answer": "more", "message_flow": "single"}):
        resp = client.post("/sessions/s1/continue")
    assert resp.status_code == 200
    assert resp.json()["answer"] == "more"


def test_route_regenerate_no_user_400():
    sr, mr = _repos([{"id": "a1", "role": "assistant", "content": "greeting"}])
    deps = {"session_repo": sr, "message_repo": mr}
    with patch("src.coordinator.routes.chat._get_dependencies", return_value=deps):
        resp = client.post("/sessions/s1/regenerate")
    assert resp.status_code == 400
