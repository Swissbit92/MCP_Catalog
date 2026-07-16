"""ADR-011 conversation-control commands — gateway client, relay, and handlers."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import httpx
import pytest
import respx

from eeva_telegram import handlers, relay
from eeva_telegram.config import TelegramConfig
from eeva_telegram.handlers import Gateway
from eeva_telegram.nephilim_client import (
    NephilimBadRequestError,
    NephilimClient,
    NephilimUnavailableError,
)
from eeva_telegram.session_store import SessionStore

BASE = "http://127.0.0.1:8000"


# ─── Client (respx) ──────────────────────────────────────────────────────────


@pytest.fixture
def client():
    return NephilimClient(BASE, timeout_seconds=5.0)


@respx.mock
async def test_client_regenerate_posts(client):
    respx.post(f"{BASE}/sessions/s1/regenerate").mock(
        return_value=httpx.Response(200, json={"answer": "new", "message_flow": "single"})
    )
    out = await client.regenerate("s1")
    assert out["answer"] == "new"


@respx.mock
async def test_client_400_raises_bad_request(client):
    respx.post(f"{BASE}/sessions/s1/regenerate").mock(return_value=httpx.Response(400))
    with pytest.raises(NephilimBadRequestError):
        await client.regenerate("s1")


@respx.mock
async def test_client_note_roundtrip(client):
    respx.put(f"{BASE}/sessions/s1/note").mock(return_value=httpx.Response(200, json={"ok": True, "note": "x"}))
    respx.get(f"{BASE}/sessions/s1/note").mock(return_value=httpx.Response(200, json={"note": "x"}))
    await client.set_note("s1", "x")
    assert (await client.get_note("s1"))["note"] == "x"


@respx.mock
async def test_client_meta(client):
    respx.get(f"{BASE}/sessions/s1/meta").mock(
        return_value=httpx.Response(200, json={"display_name": "Gwen", "nsfw": True, "message_count": 2})
    )
    meta = await client.get_session_meta("s1")
    assert meta["display_name"] == "Gwen" and meta["nsfw"] is True


# ─── Fakes for relay + handler tests ─────────────────────────────────────────


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
        self._n = 0
        self.regen_resp = {"answer": "rerolled", "message_flow": "single"}
        self.continue_resp = {"answer": "more", "message_flow": "single"}
        self.narrate_resp = {"answer": "reacts", "message_flow": "single"}
        self.meta_resp = {"display_name": "Nyx", "nsfw": False, "message_count": 3, "persona_key": "nephilim_nyx"}
        self.impersonate_resp = {"draft": "hey you"}
        self.note = None
        self.set_note_calls = []
        self.cleared_note = False
        self.undone = []
        self.narrated = None
        self.impersonate_hint = "unset"
        self.raise_on: Exception | None = None

    async def create_session(self, persona_key, title="Telegram"):
        self._n += 1
        return f"sess-{self._n}"

    async def regenerate(self, sid):
        if self.raise_on:
            raise self.raise_on
        return self.regen_resp

    async def continue_reply(self, sid):
        if self.raise_on:
            raise self.raise_on
        return self.continue_resp

    async def undo(self, sid):
        self.undone.append(sid)
        return {"ok": True, "deleted": 2}

    async def narrate(self, sid, text):
        self.narrated = (sid, text)
        return self.narrate_resp

    async def impersonate(self, sid, hint=None):
        self.impersonate_hint = hint
        return self.impersonate_resp

    async def get_session_meta(self, sid):
        return self.meta_resp

    async def set_note(self, sid, note):
        self.set_note_calls.append((sid, note))
        return {"ok": True, "note": note}

    async def get_note(self, sid):
        return {"note": self.note}

    async def clear_note(self, sid):
        self.cleared_note = True
        return {"ok": True, "cleared": True}


@pytest.fixture
def fake_client():
    return FakeClient()


@pytest.fixture
def gateway(cfg: TelegramConfig, store: SessionStore, fake_client: FakeClient):
    return Gateway(config=cfg, client=fake_client, store=store, llm_lock=asyncio.Lock())


def make_update(chat_id, text=None):
    message = SimpleNamespace(text=text, forward_origin=None)
    return SimpleNamespace(effective_chat=SimpleNamespace(id=chat_id), message=message)


def make_context(gateway, bot, args=None):
    app = SimpleNamespace(bot_data={"gateway": gateway})
    return SimpleNamespace(application=app, bot=bot, error=None, args=args or [])


# ─── Relay ───────────────────────────────────────────────────────────────────


async def test_relay_regenerate_extracts(fake_client, store):
    out = await relay.regenerate_reply(fake_client, store, 111, "nephilim_eeva")
    assert out == ["rerolled"]


async def test_relay_impersonate_returns_draft(fake_client, store):
    out = await relay.impersonate(fake_client, store, 111, "nephilim_eeva", "flirty")
    assert out == "hey you"


async def test_relay_note_set_and_get(fake_client, store):
    await relay.set_note(fake_client, store, 111, "nephilim_eeva", "be bold")
    assert fake_client.set_note_calls[0][1] == "be bold"
    fake_client.note = "be bold"
    assert await relay.get_note(fake_client, store, 111, "nephilim_eeva") == "be bold"


# ─── Handlers ────────────────────────────────────────────────────────────────


async def test_help_lists_commands(gateway):
    bot = FakeBot()
    await handlers.help_command(make_update(111, "/help"), make_context(gateway, bot))
    assert any("/regen" in t and "/note" in t for t in bot.texts)


async def test_help_silent_when_not_allowed(gateway):
    bot = FakeBot()
    await handlers.help_command(make_update(999, "/help"), make_context(gateway, bot))
    assert bot.sent == []


async def test_whoami_formats_metadata(gateway):
    bot = FakeBot()
    await handlers.whoami_command(make_update(111, "/whoami"), make_context(gateway, bot))
    assert any("Nyx" in t and "3 messages" in t for t in bot.texts)


async def test_regen_happy(gateway):
    bot = FakeBot()
    await handlers.regen_command(make_update(111, "/regen"), make_context(gateway, bot))
    assert bot.texts == ["rerolled"]


async def test_regen_nothing_to_reroll(gateway, fake_client):
    fake_client.raise_on = NephilimBadRequestError("400")
    bot = FakeBot()
    await handlers.regen_command(make_update(111, "/regen"), make_context(gateway, bot))
    assert bot.texts == [handlers.MSG_NOTHING_TO_REGEN]


async def test_regen_unavailable_maps(gateway, fake_client):
    fake_client.raise_on = NephilimUnavailableError("down")
    bot = FakeBot()
    await handlers.regen_command(make_update(111, "/regen"), make_context(gateway, bot))
    assert bot.texts == [handlers.MSG_UNAVAILABLE]


async def test_continue_happy(gateway):
    bot = FakeBot()
    await handlers.continue_command(make_update(111, "/continue"), make_context(gateway, bot))
    assert bot.texts == ["more"]


async def test_undo_confirms(gateway, fake_client):
    bot = FakeBot()
    await handlers.undo_command(make_update(111, "/undo"), make_context(gateway, bot))
    assert bot.texts == [handlers.MSG_UNDO_DONE]
    assert fake_client.undone  # backend was called


async def test_sys_usage_without_args(gateway):
    bot = FakeBot()
    await handlers.sys_command(make_update(111, "/sys"), make_context(gateway, bot, args=[]))
    assert bot.texts == [handlers.MSG_SYS_USAGE]


async def test_sys_narrates_with_args(gateway, fake_client):
    bot = FakeBot()
    await handlers.sys_command(make_update(111, "/sys"), make_context(gateway, bot, args=["it's", "raining"]))
    assert bot.texts == ["reacts"]
    assert fake_client.narrated[1] == "it's raining"


async def test_note_show_none(gateway, fake_client):
    fake_client.note = None
    bot = FakeBot()
    await handlers.note_command(make_update(111, "/note"), make_context(gateway, bot, args=[]))
    assert bot.texts == [handlers.MSG_NOTE_NONE]


async def test_note_show_existing(gateway, fake_client):
    fake_client.note = "be shy tonight"
    bot = FakeBot()
    await handlers.note_command(make_update(111, "/note"), make_context(gateway, bot, args=[]))
    assert any("be shy tonight" in t for t in bot.texts)


async def test_note_set(gateway, fake_client):
    bot = FakeBot()
    await handlers.note_command(make_update(111, "/note"), make_context(gateway, bot, args=["be", "bold"]))
    assert fake_client.set_note_calls[0][1] == "be bold"
    assert bot.texts == [handlers.MSG_NOTE_SET]


async def test_note_clear(gateway, fake_client):
    bot = FakeBot()
    await handlers.note_command(make_update(111, "/note"), make_context(gateway, bot, args=["clear"]))
    assert fake_client.cleared_note is True
    assert bot.texts == [handlers.MSG_NOTE_CLEARED]


async def test_impersonate_returns_draft(gateway, fake_client):
    bot = FakeBot()
    await handlers.impersonate_command(make_update(111, "/impersonate"), make_context(gateway, bot, args=["flirty"]))
    assert any("hey you" in t for t in bot.texts)
    assert fake_client.impersonate_hint == "flirty"


async def test_conversation_verbs_silent_when_not_allowed(gateway, fake_client):
    bot = FakeBot()
    await handlers.regen_command(make_update(999, "/regen"), make_context(gateway, bot))
    await handlers.note_command(make_update(999, "/note"), make_context(gateway, bot, args=["x"]))
    assert bot.sent == []
    assert fake_client.set_note_calls == []
