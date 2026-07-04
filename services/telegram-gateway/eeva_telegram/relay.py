"""Core relay orchestration: Telegram chat <-> nephilim session.

This module is deliberately free of any python-telegram-bot types so it can be
unit-tested with a mocked NephilimClient and a real (temp-file) SessionStore.
The PTB handler layer (handlers.py) is a thin adapter over these functions.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from .nephilim_client import NephilimClient, NephilimSessionNotFoundError
from .session_store import SessionStore


def extract_messages(response: dict[str, Any]) -> list[str]:
    """Turn a nephilim chat/greet response into an ordered list of message strings.

    - message_flow == "multi" with a list answer -> each element is its own message
    - a list answer (any flow) -> non-empty elements, in order
    - a string answer -> single message
    Empty/whitespace-only pieces are dropped. Returns [] if nothing usable.
    """
    answer = response.get("answer")
    pieces: list[Any]
    if isinstance(answer, list):
        pieces = answer
    elif answer is None:
        pieces = []
    else:
        pieces = [answer]

    out: list[str] = []
    for piece in pieces:
        text = str(piece).strip()
        if text:
            out.append(text)
    return out


async def ensure_session(
    client: NephilimClient,
    store: SessionStore,
    chat_id: int,
    persona_key: str,
) -> tuple[str, bool]:
    """Return (session_id, created). Reuses a stored session or creates a new one.

    'created' is True only when a brand-new session was minted this call.
    """
    existing = store.get(chat_id, persona_key)
    if existing:
        return existing, False
    session_id = await client.create_session(persona_key)
    store.set(chat_id, persona_key, session_id)
    return session_id, True


async def _with_session_recreate(
    client: NephilimClient,
    store: SessionStore,
    chat_id: int,
    persona_key: str,
    action: Callable[[str], Awaitable[Any]],
) -> Any:
    """Run action(session_id); on 404 (stale session), recreate once and retry.

    Keeps the gateway resilient when a session row is deleted out-of-band on the
    backend (e.g. a DB reset). One retry only — a second 404 propagates.
    """
    session_id, _ = await ensure_session(client, store, chat_id, persona_key)
    try:
        return await action(session_id)
    except NephilimSessionNotFoundError:
        store.delete(chat_id, persona_key)
        new_id = await client.create_session(persona_key)
        store.set(chat_id, persona_key, new_id)
        return await action(new_id)


async def handle_user_message(
    client: NephilimClient,
    store: SessionStore,
    chat_id: int,
    persona_key: str,
    text: str,
) -> list[str]:
    """Relay one user message; return the ordered persona reply messages."""
    response = await _with_session_recreate(client, store, chat_id, persona_key, lambda sid: client.chat(sid, text))
    return extract_messages(response)


async def start_session(
    client: NephilimClient,
    store: SessionStore,
    chat_id: int,
    persona_key: str,
) -> tuple[list[str], bool]:
    """Handle /start.

    If no session exists yet, create one and greet in-character -> (greeting, True).
    If a session already exists, don't re-greet (avoids duplicate greetings on
    every /start or restart) -> ([], False); caller sends a short ack.
    """
    session_id, created = await ensure_session(client, store, chat_id, persona_key)
    if not created:
        return [], False
    greeting = await client.greet(session_id)
    return extract_messages(greeting), True


async def reset_session(
    client: NephilimClient,
    store: SessionStore,
    chat_id: int,
    persona_key: str,
) -> None:
    """Handle /reset: true history deletion on the existing session.

    Clears all messages + emotional state via the backend, preserving the
    session (and thus relationship progression). If the session is gone
    server-side, recreate a clean one.
    """
    await _with_session_recreate(client, store, chat_id, persona_key, lambda sid: client.clear_messages(sid))
