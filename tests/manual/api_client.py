"""
Thin stdlib HTTP client for the MCP Coordinator backend.

Uses only urllib (no requests) so it runs without extra deps.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any


def check_backend(base_url: str = "http://localhost:8000") -> tuple[bool, str]:
    """GET /ready — returns (ok, message)."""
    try:
        req = urllib.request.Request(f"{base_url}/ready", method="GET")
        with urllib.request.urlopen(req, timeout=10) as r:
            body = json.loads(r.read())
            return True, body.get("status", "ok")
    except Exception as e:
        return False, str(e)


def create_session(
    persona_key: str,
    base_url: str = "http://localhost:8000",
) -> str:
    """POST /sessions — returns session id string."""
    payload = json.dumps({"persona_key": persona_key}).encode()
    req = urllib.request.Request(
        f"{base_url}/sessions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    return data["id"]


def chat(
    session_id: str,
    persona_key: str,
    message: str,
    base_url: str = "http://localhost:8000",
    timeout: int = 120,
) -> tuple[str, float, str, list[str]]:
    """POST /sessions/{id}/chat — returns (answer, elapsed_s, source_type, tools_used).

    answer is always a flat string (joined if backend returns list).
    source_type: "llm" | "brave_mcp" | "mongodb_mcp" | "wallet" | "?"
    """
    payload = json.dumps({"persona": persona_key, "message": message}).encode()
    req = urllib.request.Request(
        f"{base_url}/sessions/{session_id}/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data: dict[str, Any] = json.loads(r.read())
    elapsed = time.time() - t0

    answer = data.get("answer", "")
    if isinstance(answer, list):
        answer = "\n---\n".join(answer)

    meta = data.get("metadata", {})
    source = meta.get("source_type", "?")
    tools = meta.get("tools_used", [])
    if not isinstance(tools, list):
        tools = []

    return answer, elapsed, source, tools


def greet(
    persona_key: str,
    base_url: str = "http://localhost:8000",
    timeout: int = 60,
) -> tuple[str, str]:
    """POST /greet — create session and get opening message.
    Returns (session_id, greeting_text).
    """
    payload = json.dumps({"persona": persona_key}).encode()
    req = urllib.request.Request(
        f"{base_url}/greet",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data: dict[str, Any] = json.loads(r.read())
    sid = data.get("session_id", data.get("id", ""))
    greeting = data.get("answer", data.get("message", ""))
    if isinstance(greeting, list):
        greeting = "\n---\n".join(greeting)
    return sid, greeting
