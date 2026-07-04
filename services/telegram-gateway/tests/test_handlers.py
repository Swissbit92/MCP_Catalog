"""Tests for PTB handlers using lightweight fakes (no network, no real PTB app).

Focus: the security-critical guards (allowlist silence, forwarded refusal) and
the error-mapping contract (never leak internals), plus happy-path relaying.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from eeva_telegram import handlers
from eeva_telegram.config import TelegramConfig
from eeva_telegram.handlers import Gateway
from eeva_telegram.nephilim_client import NephilimSessionNotFoundError, NephilimUnavailableError
from eeva_telegram.session_store import SessionStore


class FakeBot:
    def __init__(self):
        self.sent = []
        self.actions = []

    async def send_message(self, chat_id, text, link_preview_options=None):
        self.sent.append((chat_id, text))

    async def send_chat_action(self, chat_id, action):
        self.actions.append((chat_id, action))

    @property
    def texts(self):
        return [t for _, t in self.sent]


class FakeClient:
    def __init__(self):
        self.chat_calls = []
        self.cleared = []
        self.greeted = []
        self._n = 0
        self.chat_response = {"answer": "hello from persona", "message_flow": "single"}
        self.greet_response = {"answer": "Greetings."}
        self.raise_on_chat: Exception | None = None

    async def create_session(self, persona_key, title="Telegram"):
        self._n += 1
        return f"sess-{self._n}"

    async def chat(self, session_id, message):
        if self.raise_on_chat is not None:
            raise self.raise_on_chat
        self.chat_calls.append((session_id, message))
        return self.chat_response

    async def greet(self, session_id):
        self.greeted.append(session_id)
        return self.greet_response

    async def clear_messages(self, session_id):
        self.cleared.append(session_id)


@pytest.fixture
def gateway(cfg: TelegramConfig, store: SessionStore):
    return Gateway(config=cfg, client=FakeClient(), store=store, llm_lock=asyncio.Lock())


def make_update(chat_id, text=None, forwarded=False):
    message = SimpleNamespace(text=text, forward_origin=(object() if forwarded else None))
    return SimpleNamespace(effective_chat=SimpleNamespace(id=chat_id), message=message)


def make_context(gateway, bot):
    app = SimpleNamespace(bot_data={"gateway": gateway})
    return SimpleNamespace(application=app, bot=bot, error=None)


# ─── is_forwarded ────────────────────────────────────────────────────────────


def test_is_forwarded_detects_forward():
    assert handlers.is_forwarded(SimpleNamespace(forward_origin=object())) is True


def test_is_forwarded_false_for_normal():
    assert handlers.is_forwarded(SimpleNamespace(forward_origin=None)) is False
    assert handlers.is_forwarded(None) is False


# ─── allowlist gate ──────────────────────────────────────────────────────────


async def test_non_allowlisted_is_silent(gateway):
    bot = FakeBot()
    ctx = make_context(gateway, bot)
    await handlers.text_message(make_update(999, text="hi"), ctx)
    assert bot.sent == []  # no reply at all
    assert gateway.client.chat_calls == []  # nephilim never called


async def test_allowlisted_happy_path_relays(gateway):
    bot = FakeBot()
    ctx = make_context(gateway, bot)
    await handlers.text_message(make_update(111, text="hi"), ctx)
    assert gateway.client.chat_calls  # backend called
    assert bot.texts == ["hello from persona"]


# ─── forwarded refusal ───────────────────────────────────────────────────────


async def test_forwarded_message_refused_not_relayed(gateway):
    bot = FakeBot()
    ctx = make_context(gateway, bot)
    await handlers.text_message(make_update(111, text="malicious instructions", forwarded=True), ctx)
    assert bot.texts == [handlers.MSG_FORWARD_REFUSED]
    assert gateway.client.chat_calls == []  # never reached the LLM


# ─── error mapping (no leakage) ──────────────────────────────────────────────


async def test_unavailable_maps_to_generic(gateway):
    gateway.client.raise_on_chat = NephilimUnavailableError("http://127.0.0.1:8000 refused")
    bot = FakeBot()
    ctx = make_context(gateway, bot)
    await handlers.text_message(make_update(111, text="hi"), ctx)
    assert bot.texts == [handlers.MSG_UNAVAILABLE]
    # internal detail (URL) must not appear anywhere in the reply
    assert all("127.0.0.1" not in t for t in bot.texts)


async def test_unexpected_error_maps_to_generic(gateway):
    gateway.client.raise_on_chat = NephilimSessionNotFoundError("secret-session-uuid")
    bot = FakeBot()
    ctx = make_context(gateway, bot)
    await handlers.text_message(make_update(111, text="hi"), ctx)
    # SessionNotFound recreate path will retry once; make recreate also fail:
    # here chat always raises, so after recreate it raises again -> generic error.
    assert bot.texts == [handlers.MSG_ERROR]
    assert all("secret-session-uuid" not in t for t in bot.texts)


async def test_unexpected_non_nephilim_error_maps_to_generic(gateway):
    # A bug unrelated to nephilim (e.g. sqlite) must still map to the fixed
    # MSG_ERROR string, never leaking the exception text.
    gateway.client.raise_on_chat = RuntimeError("sqlite disk image is malformed at /secret/path")
    bot = FakeBot()
    ctx = make_context(gateway, bot)
    await handlers.text_message(make_update(111, text="hi"), ctx)
    assert bot.texts == [handlers.MSG_ERROR]
    assert all("secret" not in t for t in bot.texts)


async def test_empty_reply_gets_placeholder(gateway):
    gateway.client.chat_response = {"answer": "", "message_flow": "single"}
    bot = FakeBot()
    ctx = make_context(gateway, bot)
    await handlers.text_message(make_update(111, text="hi"), ctx)
    assert bot.texts == [handlers.MSG_EMPTY]


# ─── /start and /reset ───────────────────────────────────────────────────────


async def test_start_greets_new_session(gateway):
    bot = FakeBot()
    ctx = make_context(gateway, bot)
    await handlers.start_command(make_update(111), ctx)
    assert bot.texts == ["Greetings."]


async def test_start_acks_existing_session(gateway):
    gateway.store.set(111, "nephilim_eeva", "sess-existing")
    bot = FakeBot()
    ctx = make_context(gateway, bot)
    await handlers.start_command(make_update(111), ctx)
    assert bot.texts == [handlers.MSG_START_ACK]
    assert gateway.client.greeted == []


async def test_reset_clears_and_confirms(gateway):
    gateway.store.set(111, "nephilim_eeva", "sess-existing")
    bot = FakeBot()
    ctx = make_context(gateway, bot)
    await handlers.reset_command(make_update(111), ctx)
    assert gateway.client.cleared == ["sess-existing"]
    assert bot.texts == [handlers.MSG_RESET_DONE]


async def test_reset_non_allowlisted_silent(gateway):
    bot = FakeBot()
    ctx = make_context(gateway, bot)
    await handlers.reset_command(make_update(999), ctx)
    assert bot.sent == []
    assert gateway.client.cleared == []


async def test_persona_override_routes_to_nyx(gateway):
    # cfg fixture maps chat 222 -> nephilim_nyx
    bot = FakeBot()
    ctx = make_context(gateway, bot)
    await handlers.text_message(make_update(222, text="hi"), ctx)
    # session created under the nyx persona key
    assert gateway.store.get(222, "nephilim_nyx") is not None
    assert gateway.store.get(222, "nephilim_eeva") is None
