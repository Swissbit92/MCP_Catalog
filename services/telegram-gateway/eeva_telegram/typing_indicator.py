"""Async 'typing…' indicator that repeats until the reply is ready.

Telegram's typing action decays after ~5s, so we re-send it on an interval
while a (potentially slow) LLM generation is in flight. Use as an async context
manager wrapping the nephilim call.
"""

from __future__ import annotations

import asyncio
import contextlib

from telegram import Bot
from telegram.constants import ChatAction


class TypingIndicator:
    """Keeps a chat's 'typing…' status alive for the duration of the `async with`."""

    def __init__(self, bot: Bot, chat_id: int, interval_seconds: float = 4.5) -> None:
        self._bot = bot
        self._chat_id = chat_id
        self._interval = interval_seconds
        self._task: asyncio.Task | None = None

    async def _loop(self) -> None:
        while True:
            with contextlib.suppress(Exception):
                await self._bot.send_chat_action(chat_id=self._chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(self._interval)

    async def __aenter__(self) -> TypingIndicator:
        self._task = asyncio.create_task(self._loop())
        return self

    async def __aexit__(self, *_exc: object) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
