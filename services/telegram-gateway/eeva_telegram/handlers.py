"""python-telegram-bot handlers: the thin adapter over relay + messaging.

Security posture enforced here:
  - Allowlist gate on EVERY update: non-allowlisted chats are silently ignored
    (no reply, content never logged, nephilim never called).
  - Forwarded messages are refused, never relayed to the LLM (injection guard).
  - Only fixed, hardcoded user-facing strings — exception text/URLs/internals are
    NEVER interpolated into an outbound message. Full detail is logged locally.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from telegram import Message, Update
from telegram.ext import ContextTypes

from . import messaging, relay
from .config import TelegramConfig
from .nephilim_client import NephilimClient, NephilimError, NephilimUnavailableError
from .session_store import SessionStore
from .typing_indicator import TypingIndicator

logger = logging.getLogger(__name__)

# Fixed user-facing strings. Persona-neutral (a chat may be routed to a persona
# other than E.E.V.A.). NEVER interpolate exception detail into these.
MSG_UNAVAILABLE = "I'm having trouble connecting right now — give it a moment and try again."
MSG_ERROR = "Something went wrong on my end. Try again in a moment."
MSG_EMPTY = "Hm — nothing came through. Try rephrasing?"
MSG_FORWARD_REFUSED = "I only read messages you write to me directly — forwarded messages are ignored for safety."
MSG_TEXT_ONLY = "I can only handle text messages right now."
MSG_START_ACK = (
    "We're already mid-conversation. Say anything to continue, or /reset to wipe our history and start fresh."
)
MSG_RESET_DONE = "Done — our conversation history is wiped. We're starting fresh."
MSG_TOOLKIT_EMPTY = "I don't have any tools available right now — just conversation."

# Human-friendly toolset labels for the /tools listing.
_TOOLSET_LABELS = {
    "web": "🔎 Web",
    "wallet": "💰 Wallet",
    "memory": "🧠 Memory",
    "terminal": "⌨️ Terminal",
}


def format_toolkit(toolkit: dict) -> str:
    """Render a persona toolkit dict (from GET /personas/{key}/toolkit) into a
    Telegram message. Only structured fields from our OWN backend are used —
    tool names/descriptions are developer-authored, not user/LLM content."""
    name = toolkit.get("display_name") or toolkit.get("persona_key") or "This persona"
    tools_by_set = toolkit.get("tools") or {}
    if not tools_by_set:
        return MSG_TOOLKIT_EMPTY

    lines = [f"🧰 {name} — available tools:"]
    if toolkit.get("nsfw"):
        lines.append("🔞 Unrestricted (adult) mode is on.")
    for toolset, tools in tools_by_set.items():
        label = _TOOLSET_LABELS.get(toolset, toolset.capitalize())
        lines.append(f"\n{label}")
        for t in tools:
            desc = t.get("description") or ""
            hitl = " (asks first)" if t.get("requires_hitl") else ""
            lines.append(f"• {t.get('name')} — {desc}{hitl}")
    return "\n".join(lines)


async def tools_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List the tools/skills available to the persona for this chat (ADR-009 W3).

    Generic: uses the chat's configured persona, so it works for any persona,
    not just E.E.V.A.
    """
    gateway = get_gateway(context)
    chat_id = _allowed_chat_id(update, gateway)
    if chat_id is None:
        return
    persona = gateway.config.persona_for_chat(chat_id)
    bot = context.bot
    limit = gateway.config.message_char_limit
    try:
        toolkit = await gateway.client.get_toolkit(persona)
    except NephilimUnavailableError:
        await messaging.send_text(bot, chat_id, MSG_UNAVAILABLE, limit)
        return
    except NephilimError:
        logger.exception("get_toolkit failed for chat_id=%s persona=%s", chat_id, persona)
        await messaging.send_text(bot, chat_id, MSG_ERROR, limit)
        return
    except Exception:
        logger.exception("Unexpected error in /tools for chat_id=%s", chat_id)
        await messaging.send_text(bot, chat_id, MSG_ERROR, limit)
        return
    await messaging.send_text(bot, chat_id, format_toolkit(toolkit), limit)


@dataclass
class Gateway:
    """Shared per-process state, stashed in Application.bot_data['gateway']."""

    config: TelegramConfig
    client: NephilimClient
    store: SessionStore
    llm_lock: object  # asyncio.Lock — typed loosely to avoid import at module load


def is_forwarded(message: Message | None) -> bool:
    """True if the message was forwarded from elsewhere (Bot API 7.0 forward_origin)."""
    if message is None:
        return False
    return getattr(message, "forward_origin", None) is not None


def get_gateway(context: ContextTypes.DEFAULT_TYPE) -> Gateway:
    return context.application.bot_data["gateway"]


def _allowed_chat_id(update: Update, gateway: Gateway) -> int | None:
    """Return chat_id iff this update is from an allowlisted chat, else None.

    Silent by design: a rejected update produces no reply and logs only the id.
    """
    chat = update.effective_chat
    if chat is None:
        return None
    if not gateway.config.is_allowed(chat.id):
        logger.info("Ignoring update from non-allowlisted chat_id=%s", chat.id)
        return None
    return chat.id


def _log_content(gateway: Gateway, chat_id: int, text: str) -> None:
    if gateway.config.log_content:
        logger.debug("chat_id=%s text=%r", chat_id, text)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    gateway = get_gateway(context)
    chat_id = _allowed_chat_id(update, gateway)
    if chat_id is None:
        return
    persona = gateway.config.persona_for_chat(chat_id)
    bot = context.bot
    limit = gateway.config.message_char_limit
    try:
        async with gateway.llm_lock, TypingIndicator(bot, chat_id, gateway.config.typing_interval_seconds):
            messages, greeted = await relay.start_session(gateway.client, gateway.store, chat_id, persona)
    except NephilimUnavailableError:
        await messaging.send_text(bot, chat_id, MSG_UNAVAILABLE, limit)
        return
    except NephilimError:
        logger.exception("start_session failed for chat_id=%s", chat_id)
        await messaging.send_text(bot, chat_id, MSG_ERROR, limit)
        return
    except Exception:
        # Unexpected (e.g. sqlite) — never leak detail; reply with the fixed string.
        logger.exception("Unexpected error in /start for chat_id=%s", chat_id)
        await messaging.send_text(bot, chat_id, MSG_ERROR, limit)
        return
    if greeted and messages:
        await messaging.send_messages(bot, chat_id, messages, limit)
    else:
        await messaging.send_text(bot, chat_id, MSG_START_ACK, limit)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    gateway = get_gateway(context)
    chat_id = _allowed_chat_id(update, gateway)
    if chat_id is None:
        return
    persona = gateway.config.persona_for_chat(chat_id)
    bot = context.bot
    limit = gateway.config.message_char_limit
    try:
        async with gateway.llm_lock:
            await relay.reset_session(gateway.client, gateway.store, chat_id, persona)
    except NephilimUnavailableError:
        await messaging.send_text(bot, chat_id, MSG_UNAVAILABLE, limit)
        return
    except NephilimError:
        logger.exception("reset_session failed for chat_id=%s", chat_id)
        await messaging.send_text(bot, chat_id, MSG_ERROR, limit)
        return
    except Exception:
        logger.exception("Unexpected error in /reset for chat_id=%s", chat_id)
        await messaging.send_text(bot, chat_id, MSG_ERROR, limit)
        return
    await messaging.send_text(bot, chat_id, MSG_RESET_DONE, limit)


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    gateway = get_gateway(context)
    chat_id = _allowed_chat_id(update, gateway)
    if chat_id is None:
        return
    message = update.message
    if message is None or not message.text:
        return
    bot = context.bot
    limit = gateway.config.message_char_limit

    # Injection guard: never relay forwarded content to the LLM.
    if is_forwarded(message):
        logger.info("Refusing forwarded message from chat_id=%s", chat_id)
        await messaging.send_text(bot, chat_id, MSG_FORWARD_REFUSED, limit)
        return

    _log_content(gateway, chat_id, message.text)
    persona = gateway.config.persona_for_chat(chat_id)
    try:
        # Single global lock: OLLAMA_NUM_PARALLEL=1 means one LLM call at a time.
        async with gateway.llm_lock, TypingIndicator(bot, chat_id, gateway.config.typing_interval_seconds):
            messages = await relay.handle_user_message(gateway.client, gateway.store, chat_id, persona, message.text)
    except NephilimUnavailableError:
        await messaging.send_text(bot, chat_id, MSG_UNAVAILABLE, limit)
        return
    except NephilimError:
        logger.exception("handle_user_message failed for chat_id=%s", chat_id)
        await messaging.send_text(bot, chat_id, MSG_ERROR, limit)
        return
    except Exception:
        logger.exception("Unexpected error handling message for chat_id=%s", chat_id)
        await messaging.send_text(bot, chat_id, MSG_ERROR, limit)
        return

    if not messages:
        messages = [MSG_EMPTY]
    await messaging.send_messages(bot, chat_id, messages, limit)


async def non_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Photos/voice/docs/etc.: text-only in v1 — acknowledge, don't process."""
    gateway = get_gateway(context)
    chat_id = _allowed_chat_id(update, gateway)
    if chat_id is None:
        return
    await messaging.send_text(context.bot, chat_id, MSG_TEXT_ONLY, gateway.config.message_char_limit)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch-all for exceptions escaping handlers (bugs, not expected failures)."""
    logger.exception("Unhandled error in handler", exc_info=context.error)
