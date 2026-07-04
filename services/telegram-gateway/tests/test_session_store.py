"""Tests for the SQLite session store."""

from __future__ import annotations

from eeva_telegram.session_store import SessionStore


def test_get_miss_returns_none(store: SessionStore):
    assert store.get(111, "nephilim_eeva") is None


def test_set_then_get(store: SessionStore):
    store.set(111, "nephilim_eeva", "sess-abc")
    assert store.get(111, "nephilim_eeva") == "sess-abc"


def test_upsert_overwrites_session(store: SessionStore):
    store.set(111, "nephilim_eeva", "sess-old")
    store.set(111, "nephilim_eeva", "sess-new")
    assert store.get(111, "nephilim_eeva") == "sess-new"


def test_persona_scoping_is_independent(store: SessionStore):
    store.set(111, "nephilim_eeva", "sess-eeva")
    store.set(111, "nephilim_nyx", "sess-nyx")
    assert store.get(111, "nephilim_eeva") == "sess-eeva"
    assert store.get(111, "nephilim_nyx") == "sess-nyx"


def test_chat_scoping_is_independent(store: SessionStore):
    store.set(111, "nephilim_eeva", "sess-a")
    store.set(222, "nephilim_eeva", "sess-b")
    assert store.get(111, "nephilim_eeva") == "sess-a"
    assert store.get(222, "nephilim_eeva") == "sess-b"


def test_delete(store: SessionStore):
    store.set(111, "nephilim_eeva", "sess-abc")
    store.delete(111, "nephilim_eeva")
    assert store.get(111, "nephilim_eeva") is None


def test_persistence_across_reopen(tmp_path):
    db = tmp_path / "sessions.sqlite3"
    s1 = SessionStore(db)
    s1.set(111, "nephilim_eeva", "sess-persist")
    s1.close()
    s2 = SessionStore(db)
    assert s2.get(111, "nephilim_eeva") == "sess-persist"
    s2.close()
