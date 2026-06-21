#!/usr/bin/env python3
"""Serve the built React SPA (react-ui/build) + reverse-proxy API paths to the backend.

Used by the launchd always-on frontend service (com.nephilim.frontend). Stdlib
only — no node at serve time. Rebuild with `cd react-ui && npm run build`.

Two responsibilities:
  1. Serve the static SPA from react-ui/build (index.html fallback for routes).
  2. Reverse-proxy backend API paths (/auth, /sessions, /persona, ...) to
     http://127.0.0.1:8000 — the React dev server does this via package.json
     "proxy", and the frontend's auth calls use RELATIVE URLs that depend on it.
     Without this, /auth/refresh hits the static server and login fails.
"""
from __future__ import annotations

import os
import urllib.error
import urllib.request
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

BUILD_DIR = Path(__file__).resolve().parents[1] / "react-ui" / "build"
PORT = int(os.getenv("REACT_PORT") or os.getenv("PORT") or "3001")
BACKEND = os.getenv("COORD_URL") or "http://127.0.0.1:8000"

# Backend route prefixes that must be proxied (not served as static/SPA).
API_PREFIXES = (
    "/auth", "/sessions", "/persona", "/personas", "/nephilim",
    "/greet", "/ready", "/api", "/docs", "/openapi.json", "/health",
)
_HOP_BY_HOP = {"connection", "keep-alive", "transfer-encoding", "te",
               "trailer", "upgrade", "proxy-authorization", "content-encoding"}


def _is_api(path: str) -> bool:
    p = path.split("?", 1)[0]
    return any(p == pre or p.startswith(pre + "/") for pre in API_PREFIXES)


class SPAHandler(SimpleHTTPRequestHandler):
    """Static SPA handler + API reverse proxy."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BUILD_DIR), **kwargs)

    # ---- API proxy ----------------------------------------------------------
    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else None
        fwd = {k: v for k, v in self.headers.items()
               if k.lower() not in (_HOP_BY_HOP | {"host", "content-length", "accept-encoding"})}
        req = urllib.request.Request(BACKEND + self.path, data=body,
                                     method=self.command, headers=fwd)
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                self._relay(resp.status, resp.getheaders(), resp.read())
        except urllib.error.HTTPError as e:  # forward 4xx/5xx + body verbatim
            self._relay(e.code, list(e.headers.items()), e.read())
        except Exception as e:  # noqa: BLE001
            self.send_error(502, f"proxy error: {e}")

    def _relay(self, status: int, headers, payload: bytes) -> None:
        self.send_response(status)
        sent_len = False
        for k, v in headers:
            if k.lower() in _HOP_BY_HOP:
                continue
            if k.lower() == "content-length":
                sent_len = True
            self.send_header(k, v)
        if not sent_len:
            self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    # ---- HTTP methods -------------------------------------------------------
    def do_GET(self):  # noqa: N802
        if _is_api(self.path):
            return self._proxy()
        rel = self.path.split("?", 1)[0].lstrip("/")
        if self.path != "/" and not (BUILD_DIR / rel).is_file():
            self.path = "/index.html"  # SPA client-side routing
        return super().do_GET()

    def do_POST(self):  # noqa: N802
        return self._proxy() if _is_api(self.path) else self.send_error(404)

    def do_PUT(self):  # noqa: N802
        return self._proxy() if _is_api(self.path) else self.send_error(404)

    def do_DELETE(self):  # noqa: N802
        return self._proxy() if _is_api(self.path) else self.send_error(404)


def main() -> None:
    if not (BUILD_DIR / "index.html").is_file():
        raise SystemExit(f"Build not found at {BUILD_DIR}. Run: cd react-ui && npm run build")
    server = HTTPServer(("127.0.0.1", PORT), SPAHandler)
    print(f"Serving {BUILD_DIR} on http://127.0.0.1:{PORT} (API → {BACKEND})")
    server.serve_forever()


if __name__ == "__main__":
    main()
