"""Tests for outbound messaging: link-preview disabled, splitting, ordering."""

from __future__ import annotations

import pytest

from eeva_telegram import messaging


class FakeBot:
    def __init__(self):
        self.sent = []  # list of (chat_id, text, link_preview_options)

    async def send_message(self, chat_id, text, link_preview_options=None):
        self.sent.append((chat_id, text, link_preview_options))


@pytest.fixture
def bot():
    return FakeBot()


async def test_send_text_disables_link_preview(bot):
    await messaging.send_text(bot, 111, "hi", limit=100)
    assert len(bot.sent) == 1
    _, text, lpo = bot.sent[0]
    assert text == "hi"
    assert lpo is not None
    assert lpo.is_disabled is True


async def test_send_text_splits_long_message(bot):
    n = await messaging.send_text(bot, 111, "z" * 250, limit=100)
    assert n == 3
    assert len(bot.sent) == 3
    assert all(len(t) <= 100 for _, t, _ in bot.sent)
    assert all(lpo.is_disabled for _, _, lpo in bot.sent)


async def test_send_text_empty_sends_nothing(bot):
    n = await messaging.send_text(bot, 111, "   ", limit=100)
    assert n == 0
    assert bot.sent == []


async def test_send_messages_preserves_order(bot):
    await messaging.send_messages(bot, 111, ["first", "second", "third"], limit=100)
    assert [t for _, t, _ in bot.sent] == ["first", "second", "third"]


async def test_send_messages_all_disable_preview(bot):
    await messaging.send_messages(bot, 111, ["a", "b"], limit=100)
    assert all(lpo.is_disabled for _, _, lpo in bot.sent)
