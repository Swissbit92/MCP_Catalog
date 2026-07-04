"""Tests for the nephilim HTTP client, using respx to mock the backend."""

from __future__ import annotations

import httpx
import pytest
import respx

from eeva_telegram.nephilim_client import (
    NephilimClient,
    NephilimServerError,
    NephilimSessionNotFoundError,
    NephilimUnavailableError,
)

BASE = "http://127.0.0.1:8000"


@pytest.fixture
async def client():
    c = NephilimClient(BASE, timeout_seconds=2.0)
    yield c
    await c.aclose()


@respx.mock
async def test_create_session_returns_id(client):
    respx.post(f"{BASE}/sessions").mock(
        return_value=httpx.Response(200, json={"session_id": "sess-1", "title": "Telegram"})
    )
    assert await client.create_session("nephilim_eeva") == "sess-1"


@respx.mock
async def test_create_session_missing_id_is_server_error(client):
    respx.post(f"{BASE}/sessions").mock(return_value=httpx.Response(200, json={"title": "x"}))
    with pytest.raises(NephilimServerError):
        await client.create_session("nephilim_eeva")


@respx.mock
async def test_chat_returns_body(client):
    respx.post(f"{BASE}/sessions/sess-1/chat").mock(
        return_value=httpx.Response(200, json={"answer": "hello", "message_flow": "single"})
    )
    body = await client.chat("sess-1", "hi")
    assert body["answer"] == "hello"


@respx.mock
async def test_chat_404_raises_session_not_found(client):
    respx.post(f"{BASE}/sessions/gone/chat").mock(
        return_value=httpx.Response(404, json={"detail": "Session not found."})
    )
    with pytest.raises(NephilimSessionNotFoundError):
        await client.chat("gone", "hi")


@respx.mock
async def test_chat_500_raises_server_error(client):
    respx.post(f"{BASE}/sessions/sess-1/chat").mock(return_value=httpx.Response(500, text="boom"))
    with pytest.raises(NephilimServerError):
        await client.chat("sess-1", "hi")


@respx.mock
async def test_connection_error_raises_unavailable(client):
    respx.post(f"{BASE}/sessions/sess-1/chat").mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(NephilimUnavailableError):
        await client.chat("sess-1", "hi")


@respx.mock
async def test_read_timeout_raises_unavailable(client):
    respx.post(f"{BASE}/sessions/sess-1/chat").mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(NephilimUnavailableError):
        await client.chat("sess-1", "hi")


@respx.mock
async def test_greet_returns_body(client):
    respx.post(f"{BASE}/sessions/sess-1/greet").mock(
        return_value=httpx.Response(200, json={"answer": "Welcome, seeker."})
    )
    body = await client.greet("sess-1")
    assert "answer" in body


@respx.mock
async def test_clear_messages_ok(client):
    route = respx.delete(f"{BASE}/sessions/sess-1/messages").mock(return_value=httpx.Response(200, json={"ok": True}))
    await client.clear_messages("sess-1")
    assert route.called


@respx.mock
async def test_clear_messages_404_raises(client):
    respx.delete(f"{BASE}/sessions/gone/messages").mock(return_value=httpx.Response(404))
    with pytest.raises(NephilimSessionNotFoundError):
        await client.clear_messages("gone")


@respx.mock
async def test_malformed_json_is_server_error(client):
    respx.post(f"{BASE}/sessions/sess-1/chat").mock(
        return_value=httpx.Response(200, content=b"not json", headers={"content-type": "application/json"})
    )
    with pytest.raises(NephilimServerError):
        await client.chat("sess-1", "hi")
