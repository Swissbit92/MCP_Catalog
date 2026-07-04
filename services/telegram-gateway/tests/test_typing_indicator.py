"""Tests for the typing indicator context manager."""

from __future__ import annotations

import asyncio

from eeva_telegram.typing_indicator import TypingIndicator


class FakeBot:
    def __init__(self):
        self.actions = []

    async def send_chat_action(self, chat_id, action):
        self.actions.append((chat_id, action))


async def test_sends_action_on_enter_and_stops_on_exit():
    bot = FakeBot()
    async with TypingIndicator(bot, 111, interval_seconds=0.01):
        await asyncio.sleep(0.03)  # allow a couple of ticks
    count_at_exit = len(bot.actions)
    assert count_at_exit >= 1
    # After exit, the loop is cancelled — no further actions accumulate.
    await asyncio.sleep(0.03)
    assert len(bot.actions) == count_at_exit


async def test_swallows_send_errors():
    class ErroringBot:
        async def send_chat_action(self, chat_id, action):
            raise RuntimeError("telegram down")

    # Should not raise despite the bot erroring on every action.
    async with TypingIndicator(ErroringBot(), 111, interval_seconds=0.01):
        await asyncio.sleep(0.02)
