# src/coordinator/routes/sessions.py
"""Session management API endpoints."""

from __future__ import annotations

from datetime import datetime
import logging

from fastapi import APIRouter, HTTPException

from ..schemas import (
    CreateSessionBody,
    UpdateSessionBody,
    AppendMessageBody,
    ImportBody,
    GreetBody,
    ChatBody,
)
from ..persona_memory import get_persona_card

router = APIRouter(tags=["sessions"])
logger = logging.getLogger(__name__)


def _get_repos():
    """Get repository instances from startup module."""
    from ..startup import (
        get_session_repo,
        get_message_repo,
        get_emotional_state_repo,
    )
    return get_session_repo(), get_message_repo(), get_emotional_state_repo()


@router.get("/sessions")
def list_sessions():
    """List all chat sessions."""
    session_repo, _, _ = _get_repos()
    return session_repo.get_all_sessions()


@router.post("/sessions")
def create_session(body: CreateSessionBody):
    """Create a new chat session."""
    session_repo, _, _ = _get_repos()
    title = body.title.strip() or "New Chat"
    session_id = session_repo.create_session(body.persona_key, title)
    session = session_repo.get_session(session_id)
    return {
        **session,
        "message_count": 0
    }


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    """Get a chat session with all its messages."""
    session_repo, message_repo, _ = _get_repos()

    # Get session info
    session = session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Get messages
    messages = message_repo.get_messages_by_session(session_id)
    message_count = len(messages)

    return {
        "session": {
            **session,
            "message_count": message_count
        },
        "messages": messages
    }


@router.put("/sessions/{session_id}")
def update_session(session_id: str, body: UpdateSessionBody):
    """Update a chat session (e.g., rename)."""
    session_repo, _, _ = _get_repos()

    # Check if session exists
    if not session_repo.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    title = (body.title or "").strip() or "Untitled"
    session_repo.update_session_title(session_id, title)

    # Get updated session
    session = session_repo.get_session(session_id)
    return {"ok": True, "id": session_id, "title": session["title"], "updated_at": session["updated_at"]}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """Delete a chat session and all its messages."""
    session_repo, _, _ = _get_repos()

    # Check if session exists
    if not session_repo.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    # Delete session (messages will be cascade deleted)
    session_repo.delete_session(session_id)
    return {"ok": True}


@router.post("/sessions/{session_id}/messages")
def add_message(session_id: str, body: AppendMessageBody):
    """Add a message to a chat session."""
    session_repo, message_repo, _ = _get_repos()

    # Verify session exists
    if not session_repo.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    # Insert message
    message_id = message_repo.create_message(
        session_id=session_id,
        role=body.role,
        content=body.content,
        latency_ms=body.latency_ms,
        timestamp=body.ts,
        source_type=body.source_type,
        multi_message_id=body.multi_message_id,
        multi_message_index=body.multi_message_index
    )

    # Update session timestamp
    session_repo.update_session_timestamp(session_id)

    return {"ok": True, "message_id": message_id}


@router.delete("/sessions/{session_id}/messages")
def clear_session_messages(session_id: str):
    """Clear all messages from a chat session (keep the session)."""
    session_repo, message_repo, emotional_state_repo = _get_repos()

    # Check if session exists
    if not session_repo.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    # Delete all messages for this session
    message_repo.delete_messages_by_session(session_id)

    # Phase 2.2: Reset emotional state when clearing messages
    emotional_state_repo.delete(session_id)
    logger.info(f"[EmotionalState] Reset emotional state for session {session_id[:8]} (messages cleared)")

    # Update session updated_at timestamp
    session_repo.update_session_timestamp(session_id)

    return {"ok": True}


@router.get("/sessions/{session_id}/export")
def export_session(session_id: str):
    """Export a chat session as JSON."""
    session_data = get_session(session_id)

    # Get persona info
    persona_card = get_persona_card(session_data["session"]["persona_key"])
    if not persona_card:
        raise HTTPException(status_code=400, detail="Persona not found.")

    export_data = {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
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


@router.post("/sessions/import")
def import_session(body: ImportBody):
    """Import a chat session from exported JSON."""
    session_repo, message_repo, _ = _get_repos()
    data = body.data

    # Validate data structure
    if not data.version or not data.persona or not data.session or not data.messages:
        raise HTTPException(status_code=400, detail="Invalid import data structure.")

    # Verify persona exists
    persona_key = data.persona.get("key") if isinstance(data.persona, dict) else getattr(data.persona, 'key', None)
    if not persona_key or not get_persona_card(persona_key):
        raise HTTPException(status_code=400, detail=f"Persona '{persona_key}' not found.")

    # Get session data
    session_id = None if body.create_new_session else (
        data.session.get("id") if isinstance(data.session, dict) else getattr(data.session, 'id', None)
    )
    session_title = data.session.get("title") if isinstance(data.session, dict) else getattr(data.session, 'title', 'Imported Chat')
    session_created_at = data.session.get("created_at") if isinstance(data.session, dict) else getattr(data.session, 'created_at', None)
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    # Create session
    created_session_id = session_repo.create_session(
        persona_key=persona_key,
        title=session_title or 'Imported Chat',
        session_id=session_id,
        created_at=session_created_at,
        updated_at=now
    )

    # Insert messages
    for msg in data.messages:
        message_repo.create_message(
            session_id=created_session_id,
            role=msg.get("role") if isinstance(msg, dict) else getattr(msg, 'role', 'user'),
            content=msg.get("content") if isinstance(msg, dict) else getattr(msg, 'content', ''),
            timestamp=msg.get("timestamp") if isinstance(msg, dict) else getattr(msg, 'timestamp', now),
            latency_ms=msg.get("latency_ms") if isinstance(msg, dict) else getattr(msg, 'latency_ms', None),
            source_type=msg.get("source_type") if isinstance(msg, dict) else getattr(msg, 'source_type', 'llm')
        )

    return {"ok": True, "session_id": created_session_id}


@router.get("/sessions/{session_id}/emotional-state")
def get_emotional_state(session_id: str):
    """Get the emotional state for a session (Phase 2.2)."""
    session_repo, _, emotional_state_repo = _get_repos()

    if not session_repo.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    state = emotional_state_repo.get_or_create(session_id)
    return {
        "session_id": session_id,
        "trust_level": state.trust_level,
        "rapport": state.rapport,
        "current_mood": state.current_mood,
        "mood_intensity": state.mood_intensity,
        "last_emotional_event": state.last_emotional_event,
        "updated_at": state.updated_at
    }


@router.post("/sessions/{session_id}/greet")
def greet_with_session(session_id: str, body: GreetBody):
    """Generate a greeting and save it to the session."""
    session_repo, _, _ = _get_repos()

    # Get session info
    persona_key = session_repo.get_persona_key(session_id)
    if not persona_key:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Import greet function from chat routes to avoid circular import
    from .chat import greet

    # Generate greeting
    greet_body = GreetBody(persona=persona_key)
    response = greet(greet_body)

    # Save greeting to session
    greeting_msg_body = AppendMessageBody(
        role="assistant",
        content=response["answer"],
        ts=datetime.utcnow().isoformat(timespec="seconds") + "Z"
    )
    add_message(session_id, greeting_msg_body)

    return response
