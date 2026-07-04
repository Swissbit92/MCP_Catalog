"""Async HTTP client for the nephilim FastAPI backend.

Wraps exactly the four endpoints the gateway needs:
  - POST /sessions                       create a session
  - POST /sessions/{id}/greet            generate + store an in-character greeting
  - POST /sessions/{id}/chat             one chat turn
  - DELETE /sessions/{id}/messages       clear history + emotional state (true reset)

Errors are normalised into a small typed hierarchy so the handler layer can map
them to user-facing messages WITHOUT ever leaking URLs, stack traces, or JSON
internals into a Telegram chat.
"""

from __future__ import annotations

from typing import Any

import httpx


class NephilimError(Exception):
    """Base class for all nephilim client failures."""


class NephilimUnavailableError(NephilimError):
    """Backend unreachable or timed out (connection error / read timeout)."""


class NephilimSessionNotFoundError(NephilimError):
    """The session id is unknown to the backend (HTTP 404).

    Signals the caller to drop its stale mapping and recreate a session.
    """


class NephilimServerError(NephilimError):
    """Backend returned an unexpected non-2xx status, or a malformed body."""


class NephilimClient:
    """Thin async wrapper around the nephilim session API.

    One long-lived httpx.AsyncClient is reused for keep-alive. Call aclose()
    on shutdown (or use as an async context manager).
    """

    def __init__(self, base_url: str, timeout_seconds: float = 180.0) -> None:
        self._base_url = base_url.rstrip("/")
        # Connect quickly (backend is local); allow a long read for slow LLM gen.
        timeout = httpx.Timeout(timeout_seconds, connect=5.0)
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=timeout)

    async def __aenter__(self) -> NephilimClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = await self._client.request(method, path, json=json)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.NetworkError) as exc:
            raise NephilimUnavailableError(str(exc)) from exc
        except httpx.HTTPError as exc:  # catch-all for any other transport error
            raise NephilimServerError(str(exc)) from exc

        if response.status_code == 404:
            raise NephilimSessionNotFoundError(path)
        if response.status_code >= 400:
            raise NephilimServerError(f"HTTP {response.status_code} for {path}")

        # DELETE returns {"ok": true}; tolerate empty/non-JSON gracefully.
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise NephilimServerError(f"malformed JSON from {path}") from exc

    async def create_session(self, persona_key: str, title: str = "Telegram") -> str:
        """Create a session and return its session_id."""
        data = await self._request("POST", "/sessions", json={"persona_key": persona_key, "title": title})
        session_id = data.get("session_id") or data.get("id")
        if not session_id:
            raise NephilimServerError("create_session response missing session_id")
        return str(session_id)

    async def greet(self, session_id: str) -> dict[str, Any]:
        """Generate and store an in-character greeting for the session."""
        return await self._request("POST", f"/sessions/{session_id}/greet", json={})

    async def chat(self, session_id: str, message: str) -> dict[str, Any]:
        """Send one chat turn. Returns the raw nephilim response dict."""
        return await self._request("POST", f"/sessions/{session_id}/chat", json={"message": message})

    async def clear_messages(self, session_id: str) -> None:
        """Delete all messages + emotional state for the session (true reset)."""
        await self._request("DELETE", f"/sessions/{session_id}/messages")
