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


def test_split_narrator_is_a_stimulus():
    """ADR-011 fix A: a /sys beat prompts the reply, so it counts as the stimulus."""
    msgs = [
        {"id": "u1", "role": "user"},
        {"id": "a1", "role": "assistant"},
        {"id": "n1", "role": "narrator"},
        {"id": "a2", "role": "assistant"},
    ]
    stimulus, trailing = ccs._split_last_exchange(msgs)
    assert stimulus["id"] == "n1"
    assert [m["id"] for m in trailing] == ["a2"]


def test_regenerate_after_sys_uses_narrate_instruction():
    """Fix A: /regen right after /sys must reroll the reaction, not 400."""
    sr, mr = _repos([
        {"id": "n1", "role": "narrator", "content": "A storm hits."},
        {"id": "a1", "role": "assistant", "content": "old reaction"},
    ])
    deps = {"session_repo": sr, "message_repo": mr}
    with patch.object(ccs, "handle_session_chat", return_value={"answer": "new reaction"}) as h:
        out = ccs.regenerate_last_reply("s1", deps, MagicMock(), MagicMock())
    assert out == {"answer": "new reaction"}
    mr.delete_message.assert_called_once_with("a1")   # only the reply dropped
    kwargs = h.call_args.kwargs
    assert kwargs["message"] == ccs.NARRATE_RESPONSE_INSTRUCTION  # not the beat text
    assert kwargs["persist_user"] is False


def test_undo_after_sys_removes_beat_and_reply():
    """Fix A: /undo after /sys must not orphan the narrator beat."""
    sr, mr = _repos([
        {"id": "u1", "role": "user"},
        {"id": "a0", "role": "assistant"},
        {"id": "n1", "role": "narrator"},
        {"id": "a1", "role": "assistant"},
    ])
    out = ccs.undo_last_exchange(sr, mr, "s1")
    assert out == {"ok": True, "deleted": 2}
    deleted = {c.args[0] for c in mr.delete_message.call_args_list}
    assert deleted == {"n1", "a1"}  # beat + its reply; earlier turn untouched


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


# ═══ M2: Tier 3 director verbs + session_notes ═══════════════════════════════

from src.coordinator.repositories.session_note_repository import SessionNoteRepository
from src.coordinator.services.chat_session_service import (
    ChatDeps, ChatTurnState, _append_author_note,
)


# ─── SessionNoteRepository ───────────────────────────────────────────────────

def test_session_note_repo_crud():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    try:
        repo = SessionNoteRepository(db_path)
        assert repo.get_note("s1") is None
        repo.set_note("s1", "be playful")
        assert repo.get_note("s1") == "be playful"
        repo.set_note("s1", "be shy")           # upsert
        assert repo.get_note("s1") == "be shy"
        assert repo.clear_note("s1") is True
        assert repo.get_note("s1") is None
        assert repo.clear_note("s1") is False   # already gone
    finally:
        os.path.exists(db_path) and os.unlink(db_path)


# ─── _append_author_note (injection seam) ────────────────────────────────────

def _chat_deps(note_repo=None):
    keys = ["session_repo", "message_repo", "summary_repo", "emotional_state_repo",
            "memory_manager", "user_profile_repo", "episodic_memory_rag", "fact_extractor"]
    d = {k: MagicMock() for k in keys}
    d["session_note_repo"] = note_repo
    return ChatDeps.from_dict(d)


def test_append_author_note_injects_when_set():
    note_repo = MagicMock()
    note_repo.get_note.return_value = "keep it slow and teasing"
    state = ChatTurnState(session_id="s1", message="hi", persona_key="gwen")
    _append_author_note(state, _chat_deps(note_repo))
    assert "<author_note>" in state.extra_system_context
    assert "keep it slow and teasing" in state.extra_system_context


def test_append_author_note_appends_to_existing_context():
    note_repo = MagicMock()
    note_repo.get_note.return_value = "be bold"
    state = ChatTurnState(session_id="s1", message="hi", persona_key="gwen")
    state.extra_system_context = "PRE-EXISTING"
    _append_author_note(state, _chat_deps(note_repo))
    assert "PRE-EXISTING" in state.extra_system_context
    assert "be bold" in state.extra_system_context


def test_append_author_note_noop_when_unset():
    note_repo = MagicMock()
    note_repo.get_note.return_value = None
    state = ChatTurnState(session_id="s1", message="hi", persona_key="gwen")
    _append_author_note(state, _chat_deps(note_repo))
    assert state.extra_system_context is None


def test_append_author_note_noop_when_no_repo():
    state = ChatTurnState(session_id="s1", message="hi", persona_key="gwen")
    _append_author_note(state, _chat_deps(None))
    assert state.extra_system_context is None


# ─── narrate / impersonate (service) ─────────────────────────────────────────

def test_narrate_stores_beat_and_reacts():
    sr, mr = _repos([{"id": "u1", "role": "user", "content": "hi"}])
    deps = {"session_repo": sr, "message_repo": mr}
    add = MagicMock()
    with patch.object(ccs, "handle_session_chat", return_value={"answer": "reacts"}) as h:
        out = ccs.narrate("s1", "A storm knocks the power out.", deps, MagicMock(), add)
    assert out == {"answer": "reacts"}
    stored = add.call_args.args[1]  # AppendMessageBody
    assert stored.role == "narrator"
    assert stored.content == "A storm knocks the power out."
    kwargs = h.call_args.kwargs
    assert kwargs["message"] == ccs.NARRATE_RESPONSE_INSTRUCTION
    assert kwargs["persist_user"] is False


def test_narrate_missing_session_404():
    sr, mr = _repos(exists=False)
    deps = {"session_repo": sr, "message_repo": mr}
    with pytest.raises(Exception) as e:
        ccs.narrate("bad", "x", deps, MagicMock(), MagicMock())
    assert getattr(e.value, "status_code", None) == 404


def test_impersonate_returns_trimmed_draft():
    sr, mr = _repos([{"id": "a1", "role": "assistant", "content": "Hey you"}])
    sr.get_persona_key.return_value = "gwen"
    deps = {"session_repo": sr, "message_repo": mr}
    llm = MagicMock()
    llm.complete.return_value = "  I missed you today  "
    with patch.object(ccs, "get_persona_card", return_value={"display_name": "Gwen"}), \
         patch("src.coordinator.llm_client.create_llm_client", return_value=llm):
        out = ccs.impersonate("s1", deps, hint="be flirty")
    assert out == {"draft": "I missed you today"}


def test_impersonate_missing_session_404():
    sr, mr = _repos(exists=False)
    deps = {"session_repo": sr, "message_repo": mr}
    with pytest.raises(Exception) as e:
        ccs.impersonate("bad", deps)
    assert getattr(e.value, "status_code", None) == 404


def test_format_history_for_impersonate_labels_roles():
    msgs = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "narrator", "content": "night falls"},
    ]
    out = ccs._format_history_for_impersonate(msgs, "Gwen")
    assert "You: hi" in out
    assert "Gwen: hello" in out
    assert "[Scene: night falls]" in out


# ─── Routes: note CRUD, narrate, impersonate ─────────────────────────────────

def test_route_note_set_get_clear():
    sr, _ = _repos()
    note_repo = MagicMock()
    note_repo.get_note.return_value = "be bold"
    note_repo.clear_note.return_value = True
    with patch("src.coordinator.routes.sessions._get_repos", return_value=(sr, MagicMock(), MagicMock())), \
         patch("src.coordinator.startup.get_session_note_repo", return_value=note_repo):
        r_set = client.put("/sessions/s1/note", json={"note": "be bold"})
        r_get = client.get("/sessions/s1/note")
        r_clr = client.delete("/sessions/s1/note")
    assert r_set.status_code == 200 and r_set.json()["note"] == "be bold"
    note_repo.set_note.assert_called_once_with("s1", "be bold")
    assert r_get.json()["note"] == "be bold"
    assert r_clr.status_code == 200 and r_clr.json()["cleared"] is True


def test_route_note_missing_body_422():
    sr, _ = _repos()
    with patch("src.coordinator.routes.sessions._get_repos", return_value=(sr, MagicMock(), MagicMock())):
        resp = client.put("/sessions/s1/note", json={})
    assert resp.status_code == 422


def test_route_note_404():
    sr, _ = _repos(exists=False)
    with patch("src.coordinator.routes.sessions._get_repos", return_value=(sr, MagicMock(), MagicMock())):
        resp = client.get("/sessions/bad/note")
    assert resp.status_code == 404


def test_route_narrate_happy():
    sr, mr = _repos([{"id": "u1", "role": "user", "content": "hi"}])
    deps = {"session_repo": sr, "message_repo": mr}
    with patch("src.coordinator.routes.chat._get_dependencies", return_value=deps), \
         patch("src.coordinator.routes.sessions.add_message", MagicMock()), \
         patch.object(ccs, "handle_session_chat", return_value={"answer": "reacts", "message_flow": "single"}):
        resp = client.post("/sessions/s1/narrate", json={"text": "A storm hits."})
    assert resp.status_code == 200 and resp.json()["answer"] == "reacts"


def test_route_impersonate_happy():
    sr, mr = _repos([{"id": "a1", "role": "assistant", "content": "hey"}])
    sr.get_persona_key.return_value = "gwen"
    deps = {"session_repo": sr, "message_repo": mr}
    llm = MagicMock()
    llm.complete.return_value = "draft line"
    with patch("src.coordinator.routes.chat._get_dependencies", return_value=deps), \
         patch.object(ccs, "get_persona_card", return_value={"display_name": "Gwen"}), \
         patch("src.coordinator.llm_client.create_llm_client", return_value=llm):
        resp = client.post("/sessions/s1/impersonate", json={"hint": "flirty"})
    assert resp.status_code == 200 and resp.json()["draft"] == "draft line"
