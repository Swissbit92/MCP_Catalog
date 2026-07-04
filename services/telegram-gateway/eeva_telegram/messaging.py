"""Outbound Telegram send helpers.

Two hard rules enforced here for every outbound message:
  1. Link previews are ALWAYS disabled (LinkPreviewOptions(is_disabled=True)) —
     Telegram auto-fetches previewed URLs server-side, which is a data-exfil
     channel if a reply ever contains an attacker-influenced link.
  2. Plain text only (no parse_mode) — persona replies are arbitrary text; markup
     parsing would both break on stray characters and open a markup-injection path.

Messages over the char limit are split via splitter.split_for_telegram.
"""

from __future__ import annotations

from telegram import Bot, LinkPreviewOptions

from .splitter import split_for_telegram

_NO_PREVIEW = LinkPreviewOptions(is_disabled=True)


async def send_text(bot: Bot, chat_id: int, text: str, limit: int = 4000) -> int:
    """Send one logical message, split into <=limit chunks. Returns chunk count."""
    chunks = split_for_telegram(text, limit)
    for chunk in chunks:
        await bot.send_message(chat_id=chat_id, text=chunk, link_preview_options=_NO_PREVIEW)
    return len(chunks)


async def send_messages(bot: Bot, chat_id: int, messages: list[str], limit: int = 4000) -> int:
    """Send an ordered list of logical messages sequentially. Returns total chunks."""
    total = 0
    for message in messages:
        total += await send_text(bot, chat_id, message, limit)
    return total
