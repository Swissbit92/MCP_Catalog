# src/coordinator/services/conversation_control_service.py
"""Conversation-control verbs (ADR-011) shared by the Telegram gateway and React UI.

These operate on an existing session's message history and reuse the standard
turn pipeline (``handle_session_chat``) so regenerated/continued replies inherit
first-person post-processing, the ADR-007 groundedness gate, and multi-message
shaping — no parallel LLM plumbing. Client-agnostic: both clients call the same
endpoints that delegate here.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException

from ..persona_memory import get_persona_card
from ..repositories.base_repository import utc_now_iso
from ..schemas import AppendMessageBody, MessageRole
from .chat_session_service import handle_session_chat

logger = logging.getLogger(__name__)

# Fixed instruction that turns a stored narrator beat into a persona reaction. It
# becomes the turn's (non-stored) message; the narrator message itself is already
# in history for the model to react to.
NARRATE_RESPONSE_INSTRUCTION = (
    "[The message above is a scene/narration beat, not the user speaking to you. "
    "React in-character to what just happened — do not narrate as the user.]"
)

# The synthetic, non-stored instruction that drives ``/continue``. It becomes the
# turn's ``message`` (so it steers generation) but is never persisted — the prior
# assistant reply is already in history for the model to extend.
CONTINUE_INSTRUCTION = (
    "[Continue your previous message from exactly where it left off — same voice, "
    "same scene. Do not repeat what you already said, and do not restart.]"
)


def _split_last_exchange(
    messages: List[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split a session's ordered messages into (last_user_msg, [trailing_assistant_msgs]).

    ``trailing_assistant_msgs`` are the contiguous assistant-role messages at the
    very end (a single reply may be several rows when multi-message split). The
    ``last_user_msg`` is the user turn immediately before them, or ``None`` when
    there is none (e.g. a lone greeting).
    """
    trailing: List[Dict[str, Any]] = []
    i = len(messages) - 1
    while i >= 0 and messages[i].get("role") == "assistant":
        trailing.append(messages[i])
        i -= 1
    trailing.reverse()
    last_user = messages[i] if i >= 0 and messages[i].get("role") == "user" else None
    return last_user, trailing


def undo_last_exchange(session_repo, message_repo, session_id: str) -> Dict[str, Any]:
    """Delete the last exchange (last user turn + its trailing assistant reply).

    If there is no user turn (a lone greeting), deletes the trailing assistant
    message(s). No LLM call. Returns the deleted-count.
    """
    if not session_repo.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    messages = message_repo.get_messages_by_session(session_id)
    if not messages:
        return {"ok": True, "deleted": 0}

    last_user, trailing = _split_last_exchange(messages)
    to_delete = list(trailing)
    if last_user is not None:
        to_delete.append(last_user)
    if not to_delete:
        # Neither a trailing assistant reply nor a user turn (e.g. history ends on
        # a non-standard role) — drop the single most recent message.
        to_delete = [messages[-1]]

    for msg in to_delete:
        message_repo.delete_message(msg["id"])
    session_repo.update_session_timestamp(session_id)

    logger.info(
        "[ConvControl] undo: deleted %d message(s) for session %s",
        len(to_delete), session_id[:8],
    )
    return {"ok": True, "deleted": len(to_delete)}


def regenerate_last_reply(session_id: str, deps: dict, chat_function, add_message_function) -> Dict[str, Any]:
    """Reroll the last assistant reply: delete it, re-generate for the same user turn.

    Keeps the user message in place and re-runs the pipeline with
    ``persist_user=False`` + ``run_post_turn_updates=False`` (the exchange was
    already counted the first time). 400 if there is no user turn to reply to.
    """
    session_repo = deps["session_repo"]
    message_repo = deps["message_repo"]
    if not session_repo.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    messages = message_repo.get_messages_by_session(session_id)
    last_user, trailing = _split_last_exchange(messages)
    if last_user is None:
        raise HTTPException(status_code=400, detail="Nothing to regenerate — no user message to reply to.")

    for msg in trailing:
        message_repo.delete_message(msg["id"])

    logger.info(
        "[ConvControl] regenerate: dropped %d assistant msg(s), re-generating for session %s",
        len(trailing), session_id[:8],
    )
    return handle_session_chat(
        session_id=session_id,
        message=last_user["content"],
        deps=deps,
        chat_function=chat_function,
        add_message_function=add_message_function,
        persist_user=False,
        run_post_turn_updates=False,
    )


def continue_last_reply(session_id: str, deps: dict, chat_function, add_message_function) -> Dict[str, Any]:
    """Extend the last assistant reply. Appends the continuation as a new assistant turn.

    Runs the pipeline with a synthetic (non-stored) continue instruction as the
    turn message; ``persist_user=False`` keeps it out of history. 400 if there is
    no prior reply to continue.
    """
    session_repo = deps["session_repo"]
    message_repo = deps["message_repo"]
    if not session_repo.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    messages = message_repo.get_messages_by_session(session_id)
    _, trailing = _split_last_exchange(messages)
    if not trailing:
        raise HTTPException(status_code=400, detail="Nothing to continue — no previous reply.")

    logger.info("[ConvControl] continue: extending last reply for session %s", session_id[:8])
    return handle_session_chat(
        session_id=session_id,
        message=CONTINUE_INSTRUCTION,
        deps=deps,
        chat_function=chat_function,
        add_message_function=add_message_function,
        persist_user=False,
        run_post_turn_updates=False,
    )


def narrate(session_id: str, text: str, deps: dict, chat_function, add_message_function) -> Dict[str, Any]:
    """Inject a narrator/scene beat (ADR-011 /sys) and return the persona's in-world reaction.

    Persists ``text`` as a ``narrator``-role message, then runs a turn (with a
    synthetic, non-stored instruction) so the model reacts to the scene. The
    narrator beat is rendered as bracketed scene direction, never as user dialogue.
    """
    session_repo = deps["session_repo"]
    if not session_repo.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    add_message_function(
        session_id,
        AppendMessageBody(role=MessageRole.NARRATOR, content=text, ts=utc_now_iso()),
    )
    logger.info("[ConvControl] narrate: stored scene beat for session %s", session_id[:8])
    return handle_session_chat(
        session_id=session_id,
        message=NARRATE_RESPONSE_INSTRUCTION,
        deps=deps,
        chat_function=chat_function,
        add_message_function=add_message_function,
        persist_user=False,
        run_post_turn_updates=False,
    )


def _format_history_for_impersonate(messages: List[Dict[str, Any]], persona_name: str, limit: int = 12) -> str:
    """Render recent turns for the impersonation prompt (user='You', assistant=persona)."""
    lines: List[str] = []
    for m in messages[-limit:]:
        role = m.get("role")
        content = str(m.get("content", ""))[:500]
        if role == "assistant":
            lines.append(f"{persona_name}: {content}")
        elif role == "narrator":
            lines.append(f"[Scene: {content}]")
        else:
            lines.append(f"You: {content}")
    return "\n".join(lines)


def impersonate(session_id: str, deps: dict, hint: Optional[str] = None) -> Dict[str, Any]:
    """Draft the USER's next line (ADR-011 /impersonate). Returns {"draft": ...}; not stored."""
    session_repo = deps["session_repo"]
    message_repo = deps["message_repo"]
    if not session_repo.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    persona_key = session_repo.get_persona_key(session_id)
    card = get_persona_card(persona_key) or {}
    persona_name = card.get("display_name") or persona_key or "the character"
    messages = message_repo.get_messages_by_session(session_id)
    convo = _format_history_for_impersonate(messages, persona_name)

    system = (
        "You ghost-write the USER's side of a conversation/roleplay. Given the "
        f"exchange so far, write the user's next message in first person to {persona_name}. "
        "Return ONLY the message text — no quotes, no narration, no stage directions."
    )
    user_prompt = f"Conversation so far:\n{convo}\n\n"
    if hint:
        user_prompt += f"The user wants to convey: {hint}\n\n"
    user_prompt += "Write the user's next message:"

    from ..llm_client import create_llm_client  # lazy — avoid import cost/cycles

    try:
        draft = create_llm_client(card).complete(system=system, user_prompt=user_prompt).strip()
    except Exception as e:
        logger.error("[ConvControl] impersonate LLM failed: %s", e, exc_info=True)
        raise HTTPException(status_code=503, detail=f"LLM service temporarily unavailable: {type(e).__name__}")

    return {"draft": draft}


def get_session_meta(session_repo, message_repo, session_id: str) -> Dict[str, Any]:
    """Lean session metadata for ``/whoami`` — persona identity + counts, no messages."""
    session = session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    persona_key = session.get("persona_key")
    card = get_persona_card(persona_key) or {}
    return {
        "session_id": session_id,
        "persona_key": persona_key,
        "display_name": card.get("display_name") or persona_key,
        "nsfw": bool(card.get("nsfw", False)),
        "title": session.get("title"),
        "message_count": message_repo.count_messages_by_session(session_id),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
    }
