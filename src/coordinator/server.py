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
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager

from .config import get_ollama_base, get_persona_model, get_persona_temperature
from .ollama_utils import assert_model_available
from .llm_client import LC_OllamaClient
from .persona_memory import (
    build_system_prompt, build_greeting_user_prompt, get_persona_card,
    get_or_build_cv_summary, ensure_all_summaries_serialized, _load_all_cards_cached
)

app = FastAPI(title="Local Coordinator (Chat-only)", version="0.5.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

        # Create chat_sessions table (replaces old chats table)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            persona_key TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")

        # Create messages table linked to sessions
        cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            latency_ms INTEGER,
            FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
        )""")

        # Migration: If old tables exist, migrate data
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chats'")
        if cur.fetchone():
            print("Migrating old chat data to new schema...")
            # Migrate existing chats to sessions
            cur.execute("""
            INSERT OR IGNORE INTO chat_sessions (id, persona_key, title, created_at, updated_at)
            SELECT printf('session_%06d', id), persona, title, created_at, updated_at FROM chats
            """)
            # Migrate messages
            cur.execute("""
            INSERT OR IGNORE INTO messages (id, session_id, role, content, timestamp, latency_ms)
            SELECT printf('msg_%06d', id), printf('session_%06d', chat_id), role, content, ts, latency_ms FROM messages
            """)
            print("Migration completed.")

        # Create indexes for better performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_persona ON chat_sessions(persona_key)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON chat_sessions(created_at)")

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

def _cleanup_orphaned_sessions():
    """
    Remove chat sessions for personas that no longer exist.
    This should be called when personas are loaded to ensure cleanup.
    """
    try:
        # Get all current persona keys
        cards = _load_all_cards_cached()
        current_persona_keys = {card.get("key") for card in cards if card.get("key")}

        with _DB_LOCK:
            c = _conn()
            cur = c.cursor()

            # Find sessions with personas that no longer exist
            cur.execute("SELECT id, persona_key FROM chat_sessions")
            all_sessions = cur.fetchall()

            orphaned_sessions = []
            for session in all_sessions:
                session_id = session["id"]
                persona_key = session["persona_key"]
                if persona_key not in current_persona_keys:
                    orphaned_sessions.append((session_id, persona_key))

            # Delete orphaned sessions (messages will be cascade deleted)
            if orphaned_sessions:
                orphaned_ids = [s[0] for s in orphaned_sessions]
                orphaned_personas = list(set(s[1] for s in orphaned_sessions))  # Unique persona keys

                # Delete sessions (messages will be cascade deleted due to FOREIGN KEY)
                placeholders = ','.join('?' * len(orphaned_ids))
                cur.execute(f"DELETE FROM chat_sessions WHERE id IN ({placeholders})", orphaned_ids)

                c.commit()
                print(f"Cleaned up {len(orphaned_sessions)} orphaned sessions for removed personas: {orphaned_personas}")

            c.close()

    except Exception as e:
        print(f"Warning: Failed to cleanup orphaned sessions: {e}")
        # Don't raise - this is not critical for app startup



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

# New session-based models
class CreateSessionBody(BaseModel):
    persona_key: str
    title: str = "New Chat"

class UpdateSessionBody(BaseModel):
    title: str

class MessageModel(BaseModel):
    id: str
    role: str
    content: str
    timestamp: str
    latency_ms: Optional[int] = None

class SessionModel(BaseModel):
    id: str
    persona_key: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0

class SessionWithMessages(BaseModel):
    session: SessionModel
    messages: List[MessageModel]

# Export/Import models
class ExportData(BaseModel):
    version: str = "1.0"
    exported_at: str
    app_version: str = "1.0.0"
    persona: Dict[str, Any]
    session: Dict[str, Any]
    messages: List[Dict[str, Any]]

class ImportBody(BaseModel):
    data: ExportData
    create_new_session: bool = True

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

@app.post("/sessions/{session_id}/chat")
def chat_with_session(session_id: str, body: ChatBody):
    """Chat with a persona and automatically save to session."""
    # Get session info
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        cur.execute("SELECT persona_key FROM chat_sessions WHERE id = ?", (session_id,))
        row = cur.fetchone()
        c.close()
        if not row:
            raise HTTPException(status_code=404, detail="Session not found.")

    persona_key = row["persona_key"]

    # Perform chat
    chat_body = ChatBody(persona=persona_key, history=body.history, message=body.message)
    response = chat(chat_body)

    # Save user message to session
    user_msg_body = AppendMessageBody(
        role="user",
        content=body.message,
        ts=_now()
    )
    add_message(session_id, user_msg_body)

    # Save assistant response to session
    assistant_msg_body = AppendMessageBody(
        role="assistant",
        content=response["answer"],
        ts=_now()
    )
    add_message(session_id, assistant_msg_body)

    return response

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

@app.post("/sessions/{session_id}/greet")
def greet_with_session(session_id: str, body: GreetBody):
    """Generate a greeting and save it to the session."""
    # Get session info
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        cur.execute("SELECT persona_key FROM chat_sessions WHERE id = ?", (session_id,))
        row = cur.fetchone()
        c.close()
        if not row:
            raise HTTPException(status_code=404, detail="Session not found.")

    persona_key = row["persona_key"]

    # Generate greeting
    greet_body = GreetBody(persona=persona_key)
    response = greet(greet_body)

    # Save greeting to session
    greeting_msg_body = AppendMessageBody(
        role="assistant",
        content=response["answer"],
        ts=_now()
    )
    add_message(session_id, greeting_msg_body)

    return response

@app.get("/personas")
def list_personas():
    """Return list of available personas with metadata."""
    try:
        # Clean up orphaned sessions before returning personas
        _cleanup_orphaned_sessions()

        cards = _load_all_cards_cached()
        personas = []
        for card in cards:
            personas.append({
                "key": card.get("key"),
                "display_name": card.get("display_name") or card.get("key"),
                "style": card.get("style", ""),
                "rarity": card.get("rarity", "common"),
                "coordinator_label": card.get("coordinator_label"),
                "image": card.get("image"),
                "avatar": card.get("avatar"),
                "bg": card.get("bg"),
                "voice": card.get("voice"),
            })
        return personas
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list personas: {e}")

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

# ----------------- Session-based Persistence API -----------------

import uuid

def _generate_session_id() -> str:
    return f"session_{uuid.uuid4().hex[:16]}"

def _generate_message_id() -> str:
    return f"msg_{uuid.uuid4().hex[:16]}"

@app.get("/sessions")
def list_sessions():
    """List all chat sessions."""
    print("DEBUG: list_sessions called")
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        cur.execute("""
            SELECT s.id, s.persona_key, s.title, s.created_at, s.updated_at,
                   COUNT(m.id) as message_count
            FROM chat_sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            GROUP BY s.id
            ORDER BY s.updated_at DESC, s.created_at DESC
        """)
        sessions = []
        for row in cur.fetchall():
            sessions.append({
                "id": row["id"],
                "persona_key": row["persona_key"],
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "message_count": row["message_count"]
            })
        c.close()
    return sessions

@app.post("/sessions")
def create_session(body: CreateSessionBody):
    """Create a new chat session."""
    session_id = _generate_session_id()
    now = _now()
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        cur.execute("""
            INSERT INTO chat_sessions (id, persona_key, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, body.persona_key, body.title.strip() or "New Chat", now, now))
        c.commit()
        c.close()
    return {
        "id": session_id,
        "persona_key": body.persona_key,
        "title": body.title,
        "created_at": now,
        "updated_at": now,
        "message_count": 0
    }

@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    """Get a chat session with all its messages."""
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()

        # Get session info
        cur.execute("""
            SELECT s.id, s.persona_key, s.title, s.created_at, s.updated_at,
                   COUNT(m.id) as message_count
            FROM chat_sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            WHERE s.id = ?
            GROUP BY s.id
        """, (session_id,))
        session_row = cur.fetchone()
        if not session_row:
            c.close()
            raise HTTPException(status_code=404, detail="Session not found.")

        # Get messages
        cur.execute("""
            SELECT id, role, content, timestamp, latency_ms
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """, (session_id,))
        messages = []
        for msg_row in cur.fetchall():
            messages.append({
                "id": msg_row["id"],
                "role": msg_row["role"],
                "content": msg_row["content"],
                "timestamp": msg_row["timestamp"],
                "latency_ms": msg_row["latency_ms"]
            })

        c.close()

    return {
        "session": {
            "id": session_row["id"],
            "persona_key": session_row["persona_key"],
            "title": session_row["title"],
            "created_at": session_row["created_at"],
            "updated_at": session_row["updated_at"],
            "message_count": session_row["message_count"]
        },
        "messages": messages
    }

@app.put("/sessions/{session_id}")
def update_session(session_id: str, body: UpdateSessionBody):
    """Update a chat session (e.g., rename)."""
    title = (body.title or "").strip() or "Untitled"
    now = _now()
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        cur.execute("""
            UPDATE chat_sessions
            SET title = ?, updated_at = ?
            WHERE id = ?
        """, (title, now, session_id))
        if cur.rowcount == 0:
            c.close()
            raise HTTPException(status_code=404, detail="Session not found.")
        c.commit()
        c.close()
    return {"ok": True, "id": session_id, "title": title, "updated_at": now}

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """Delete a chat session and all its messages."""
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        # Check if session exists
        cur.execute("SELECT id FROM chat_sessions WHERE id = ?", (session_id,))
        if not cur.fetchone():
            c.close()
            raise HTTPException(status_code=404, detail="Session not found.")
        # Delete messages first (cascade should handle this, but being explicit)
        cur.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        # Delete session
        cur.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        c.commit()
        c.close()
    return {"ok": True}

@app.post("/sessions/{session_id}/messages")
def add_message(session_id: str, body: AppendMessageBody):
    """Add a message to a chat session."""
    message_id = _generate_message_id()
    timestamp = body.ts or _now()
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        # Verify session exists
        cur.execute("SELECT id FROM chat_sessions WHERE id = ?", (session_id,))
        if not cur.fetchone():
            c.close()
            raise HTTPException(status_code=404, detail="Session not found.")
        # Insert message
        cur.execute("""
            INSERT INTO messages (id, session_id, role, content, timestamp, latency_ms)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (message_id, session_id, body.role, body.content, timestamp, body.latency_ms))
        # Update session timestamp
        cur.execute("""
            UPDATE chat_sessions SET updated_at = ? WHERE id = ?
        """, (_now(), session_id))
        c.commit()
        c.close()
    return {"ok": True, "message_id": message_id}

@app.delete("/sessions/{session_id}/messages")
def clear_session_messages(session_id: str):
    """Clear all messages from a chat session (keep the session)."""
    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()
        # Check if session exists
        cur.execute("SELECT id FROM chat_sessions WHERE id = ?", (session_id,))
        if not cur.fetchone():
            c.close()
            raise HTTPException(status_code=404, detail="Session not found.")
        # Delete all messages for this session
        cur.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        # Update session updated_at timestamp
        cur.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (_now(), session_id))
        c.commit()
        c.close()
    return {"ok": True}

@app.get("/sessions/{session_id}/export")
def export_session(session_id: str):
    """Export a chat session as JSON."""
    session_data = get_session(session_id)

    # Get persona info
    persona_card = get_persona_card(session_data["session"]["persona_key"])
    if not persona_card:
        raise HTTPException(status_code=400, detail="Persona not found.")

    export_data = {
        "version": "1.0",
        "exported_at": _now(),
        "app_version": "1.0.0",
        "persona": {
            "key": persona_card.get("key"),
            "display_name": persona_card.get("display_name"),
            "style": persona_card.get("style")
        },
        "session": session_data["session"],
        "messages": session_data["messages"]
    }

    return export_data

@app.post("/sessions/import")
def import_session(body: ImportBody):
    """Import a chat session from exported JSON."""
    data = body.data

    # Validate data structure
    if not data.version or not data.persona or not data.session or not data.messages:
        raise HTTPException(status_code=400, detail="Invalid import data structure.")

    # Verify persona exists (data.persona is a dict from JSON)
    persona_key = data.persona.get("key") if isinstance(data.persona, dict) else getattr(data.persona, 'key', None)
    if not persona_key or not get_persona_card(persona_key):
        raise HTTPException(status_code=400, detail=f"Persona '{persona_key}' not found.")

    session_id = _generate_session_id() if body.create_new_session else data.session.get("id") if isinstance(data.session, dict) else getattr(data.session, 'id', None)
    now = _now()

    with _DB_LOCK:
        c = _conn()
        cur = c.cursor()

        # Create session
        session_title = data.session.get("title") if isinstance(data.session, dict) else getattr(data.session, 'title', 'Imported Chat')
        session_created_at = data.session.get("created_at") if isinstance(data.session, dict) else getattr(data.session, 'created_at', now)

        cur.execute("""
            INSERT INTO chat_sessions (id, persona_key, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session_id,
            persona_key,
            session_title or 'Imported Chat',
            session_created_at or now,
            now
        ))

        # Insert messages
        for msg in data.messages:
            message_id = _generate_message_id()
            cur.execute("""
                INSERT INTO messages (id, session_id, role, content, timestamp, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                message_id,
                session_id,
                msg.get("role") if isinstance(msg, dict) else getattr(msg, 'role', 'user'),
                msg.get("content") if isinstance(msg, dict) else getattr(msg, 'content', ''),
                msg.get("timestamp") if isinstance(msg, dict) else getattr(msg, 'timestamp', now),
                msg.get("latency_ms") if isinstance(msg, dict) else getattr(msg, 'latency_ms', None)
            ))

        c.commit()
        c.close()

    return {"ok": True, "session_id": session_id}

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

# ----------------- Initialize on startup -----------------
print("Initializing FastAPI server...")
try:
    assert_model_available(get_ollama_base(), get_persona_model())
    print("Model check passed.")
except Exception as e:
    print(f"Model check failed: {e}")
    raise

try:
    _init_db()
    print("Database initialized.")
except Exception as e:
    print(f"Database init failed: {e}")
    raise

# Best-effort no-op refresh (non-blocking). If another process holds the lock, we just skip.
try:
    result = ensure_all_summaries_serialized(timeout_sec=0.01, poll_sec=0.01)
    print(f"Summaries check completed: {result}")
except Exception as e:
    print(f"Summary check failed: {e}")
    # Don't raise here as it's non-critical

print("FastAPI server initialization complete.")
