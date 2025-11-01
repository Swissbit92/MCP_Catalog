# src/coordinator/server.py
# Local Coordinator server for GraphRAG Local QA Chat with Personas
# Provides endpoints for chat, greetings, persona CV summaries, and chat persistence (SQLite).

from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime
import sqlite3
import os
import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .config import get_ollama_base, get_persona_model, get_persona_temperature
from .ollama_utils import assert_model_available
from .llm_client import LC_OllamaClient
from .persona_memory import (
    build_system_prompt, build_greeting_user_prompt, get_persona_card,
    get_or_build_cv_summary, ensure_all_summaries_serialized
)

app = FastAPI(title="Local Coordinator (Chat-only)", version="0.5.0")

# ----------------- SQLite persistence (tiny DAO) -----------------
_DB_PATH = os.environ.get("COORDINATOR_DB_PATH", "chats.db")
_DB_LOCK = threading.Lock()

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db():
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            persona TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            ts TEXT NOT NULL,
            latency_ms INTEGER,
            FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS persona_last_chat (
            persona TEXT PRIMARY KEY,
            chat_id INTEGER
        )""")
        c.commit()
        c.close()

def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

def _fetchone_dict(cur) -> Optional[Dict[str, Any]]:
    row = cur.fetchone()
    if not row:
        return None
    return dict(row)

def _fetchall_list(cur) -> List[Dict[str, Any]]:
    return [dict(r) for r in cur.fetchall()]

# ----------------- Startup -----------------
@app.on_event("startup")
def _startup():
    assert_model_available(get_ollama_base(), get_persona_model())
    _init_db()
    # Best-effort no-op refresh (non-blocking). If another process holds the lock, we just skip.
    try:
        ensure_all_summaries_serialized(timeout_sec=0.01, poll_sec=0.01)
    except Exception:
        pass

# ----------------- Schemas -----------------
class ChatTurn(BaseModel):
    role: str
    content: str

class ChatBody(BaseModel):
    persona: Optional[str] = None
    history: List[ChatTurn] = []
    message: str

class GreetBody(BaseModel):
    persona: Optional[str] = None

class SummaryBody(BaseModel):
    persona: Optional[str] = None  # label/key; None resolves to first card

class CreateChatBody(BaseModel):
    persona: str
    title: str = "New Chat"

class RenameChatBody(BaseModel):
    title: str

class AppendMessageBody(BaseModel):
    role: str
    content: str
    ts: Optional[str] = None
    latency_ms: Optional[int] = None

class SelectChatBody(BaseModel):
    persona: str

class ImportChatBody(BaseModel):
    persona: str
    chat: Dict[str, Any] = Field(..., description="JSON with {title, messages: [{role,content,ts?}]}")

# ----------------- Chat Inference -----------------
@app.post("/persona/chat")
def chat(body: ChatBody):
    card = get_persona_card(body.persona)
    if not card:
        raise HTTPException(status_code=400, detail="Unknown persona.")
    system = build_system_prompt(body.persona)

    client = LC_OllamaClient(
        base=get_ollama_base(),
        model=get_persona_model(),
        temperature=get_persona_temperature(),
    )
    history = body.history[-6:]
    lines = []
    for t in history:
        role = (t.role or "").lower()
        lines.append(f"[Assistant]\n{t.content}" if role == "assistant" else f"[User]\n{t.content}")
    lines.append(f"[User]\n{body.message}")
    user_compiled = "\n\n".join(lines)

    answer = client.complete(system=system, user_prompt=user_compiled)
    return {"answer": answer}

@app.post("/persona/greet")
def greet(body: GreetBody):
    card = get_persona_card(body.persona)
    if not card:
        raise HTTPException(status_code=400, detail="Unknown persona.")
    system = build_system_prompt(body.persona)
    user_prompt = build_greeting_user_prompt(body.persona)

    client = LC_OllamaClient(
        base=get_ollama_base(),
        model=get_persona_model(),
        temperature=get_persona_temperature(),
    )
    answer = client.complete(system=system, user_prompt=user_prompt)
    return {"answer": answer}

@app.post("/persona/summary")
def summary(body: SummaryBody):
    """
    Returns the cached or freshly built CV-style summary for a persona.
    { key, hash, updated, summary }
    """
    try:
        data = get_or_build_cv_summary(body.persona)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary error: {e}")

# ----------------- Persistence API -----------------

@app.get("/chats")
def list_chats(persona: str):
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        cur.execute("SELECT id, persona, title, created_at, updated_at FROM chats WHERE persona=? ORDER BY updated_at DESC, id DESC", (persona,))
        items = _fetchall_list(cur)
        c.close()
    return {"items": items}

@app.post("/chats")
def create_chat(body: CreateChatBody):
    now = _now()
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        cur.execute("INSERT INTO chats (persona, title, created_at, updated_at) VALUES (?,?,?,?)",
                    (body.persona, body.title.strip() or "New Chat", now, now))
        chat_id = cur.lastrowid
        # mark as last chat for persona
        cur.execute("INSERT INTO persona_last_chat (persona, chat_id) VALUES (?, ?) ON CONFLICT(persona) DO UPDATE SET chat_id=excluded.chat_id",
                    (body.persona, chat_id))
        c.commit()
        c.close()
    return {"id": chat_id, "persona": body.persona, "title": body.title, "created_at": now, "updated_at": now}

@app.get("/chats/{chat_id}/messages")
def get_messages(chat_id: int):
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        # verify chat exists
        cur.execute("SELECT id, persona, title, created_at, updated_at FROM chats WHERE id=?", (chat_id,))
        chat = _fetchone_dict(cur)
        if not chat:
            c.close()
            raise HTTPException(status_code=404, detail="Chat not found.")
        cur.execute("SELECT id, chat_id, role, content, ts, latency_ms FROM messages WHERE chat_id=? ORDER BY id ASC", (chat_id,))
        messages = _fetchall_list(cur)
        c.close()
    return {"chat": chat, "messages": messages}

@app.post("/chats/{chat_id}/messages")
def append_message(chat_id: int, body: AppendMessageBody):
    ts = body.ts or _now()
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        # verify chat exists
        cur.execute("SELECT persona FROM chats WHERE id=?", (chat_id,))
        row = cur.fetchone()
        if not row:
            c.close()
            raise HTTPException(status_code=404, detail="Chat not found.")
        cur.execute("INSERT INTO messages (chat_id, role, content, ts, latency_ms) VALUES (?,?,?,?,?)",
                    (chat_id, body.role, body.content, ts, body.latency_ms))
        cur.execute("UPDATE chats SET updated_at=? WHERE id=?", (_now(), chat_id))
        c.commit()
        c.close()
    return {"ok": True}

@app.patch("/chats/{chat_id}")
def rename_chat(chat_id: int, body: RenameChatBody):
    title = (body.title or "").strip() or "Untitled"
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        cur.execute("UPDATE chats SET title=?, updated_at=? WHERE id=?", (title, _now(), chat_id))
        c.commit()
        c.close()
    return {"ok": True, "id": chat_id, "title": title}

@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: int):
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        # discover persona so we can clean last selection if needed
        cur.execute("SELECT persona FROM chats WHERE id=?", (chat_id,))
        row = cur.fetchone()
        persona = row["persona"] if row else None
        cur.execute("DELETE FROM messages WHERE chat_id=?", (chat_id,))
        cur.execute("DELETE FROM chats WHERE id=?", (chat_id,))
        if persona:
            # if last chat was this, unset
            cur.execute("SELECT chat_id FROM persona_last_chat WHERE persona=?", (persona,))
            r2 = cur.fetchone()
            if r2 and r2["chat_id"] == chat_id:
                cur.execute("DELETE FROM persona_last_chat WHERE persona=?", (persona,))
        c.commit()
        c.close()
    return {"ok": True}

@app.post("/chats/{chat_id}/select")
def mark_selected(chat_id: int, body: SelectChatBody):
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        # verify chat
        cur.execute("SELECT id FROM chats WHERE id=? AND persona=?", (chat_id, body.persona))
        row = cur.fetchone()
        if not row:
            c.close()
            raise HTTPException(status_code=404, detail="Chat not found for persona.")
        cur.execute("INSERT INTO persona_last_chat (persona, chat_id) VALUES (?, ?) ON CONFLICT(persona) DO UPDATE SET chat_id=excluded.chat_id",
                    (body.persona, chat_id))
        c.commit()
        c.close()
    return {"ok": True}

@app.get("/chats/restore_last")
def restore_last(persona: str):
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        cur.execute("SELECT chat_id FROM persona_last_chat WHERE persona=?", (persona,))
        row = cur.fetchone()
        if row and row["chat_id"]:
            chat_id = int(row["chat_id"])
            c.close()
            return {"chat_id": chat_id, "restored": True}
        # else choose most recent if exists
        cur = _conn().cursor()
        cur.execute("SELECT id FROM chats WHERE persona=? ORDER BY updated_at DESC, id DESC LIMIT 1", (persona,))
        row2 = cur.fetchone()
        c.close()
        if row2:
            return {"chat_id": int(row2["id"]), "restored": True}
    return {"chat_id": None, "restored": False}

@app.get("/chats/{chat_id}/export")
def export_chat(chat_id: int):
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        cur.execute("SELECT id, persona, title, created_at, updated_at FROM chats WHERE id=?", (chat_id,))
        chat = _fetchone_dict(cur)
        if not chat:
            c.close()
            raise HTTPException(status_code=404, detail="Chat not found.")
        cur.execute("SELECT role, content, ts, latency_ms FROM messages WHERE chat_id=? ORDER BY id ASC", (chat_id,))
        messages = _fetchall_list(cur)
        c.close()
    return {"chat": chat, "messages": messages}

@app.post("/chats/import")
def import_chat(body: ImportChatBody):
    persona = body.persona
    chat_obj = body.chat or {}
    title = (chat_obj.get("title") or "Imported Chat").strip() or "Imported Chat"
    msgs = chat_obj.get("messages") or []

    now = _now()
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        cur.execute("INSERT INTO chats (persona, title, created_at, updated_at) VALUES (?,?,?,?)",
                    (persona, title, now, now))
        chat_id = cur.lastrowid
        for m in msgs:
            role = (m.get("role") or "user").strip()
            content = m.get("content") or ""
            ts = (m.get("ts") or now)
            latency_ms = m.get("latency_ms")
            cur.execute("INSERT INTO messages (chat_id, role, content, ts, latency_ms) VALUES (?,?,?,?,?)",
                        (chat_id, role, content, ts, latency_ms))
        # mark as last
        cur.execute("INSERT INTO persona_last_chat (persona, chat_id) VALUES (?, ?) ON CONFLICT(persona) DO UPDATE SET chat_id=excluded.chat_id",
                    (persona, chat_id))
        c.commit()
        c.close()
    return {"id": chat_id, "persona": persona, "title": title}

# ----------------- Optional tiny health check (roadmap "Now") -----------------
@app.get("/health")
def health():
    try:
        base = get_ollama_base()
        model = get_persona_model()
        # DB ping
        with _DB_LOCK:
            c = _conn()
            cur = c.cursor()
            cur.execute("SELECT 1")
            c.close()
        return {"status": "ok", "model": model, "db": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
