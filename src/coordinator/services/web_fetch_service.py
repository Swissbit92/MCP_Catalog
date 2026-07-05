# src/coordinator/services/web_fetch_service.py
"""fetch_url executor — ADR-009 Phase W (W2).

Fetches a page over HTTP and returns its main content as clean text/markdown.
Extraction chain: trafilatura (when installed) -> stdlib HTML strip fallback,
so the tool works without the optional dependency and improves with it.

Single-user, local: one consent/age-gate redirect is followed (httpx default),
no crawling, hard size + timeout caps.
"""

from __future__ import annotations

import html
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

_MAX_BYTES = 2_000_000       # 2 MB page cap
_MAX_OUTPUT_CHARS = 20_000   # cap returned text (local model context budget)
_TIMEOUT_S = 15

_SCRIPT_STYLE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>",
                           re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t]+")
_BLANKLINES = re.compile(r"\n\s*\n\s*\n+")


def _stdlib_extract(raw_html: str) -> str:
    """Dependency-free fallback: strip scripts/tags, unescape, collapse space."""
    text = _SCRIPT_STYLE.sub(" ", raw_html)
    text = re.sub(r"</(p|div|br|li|h[1-6]|tr)>", "\n", text, flags=re.IGNORECASE)
    text = _TAG.sub("", text)
    text = html.unescape(text)
    text = _WS.sub(" ", text)
    text = _BLANKLINES.sub("\n\n", text)
    return text.strip()


def _trafilatura_extract(raw_html: str, url: str, as_markdown: bool) -> Optional[str]:
    try:
        import trafilatura  # optional dependency
    except ImportError:
        return None
    try:
        return trafilatura.extract(
            raw_html, url=url, output_format=("markdown" if as_markdown else "txt"),
            include_comments=False, include_tables=True,
        )
    except Exception as e:  # noqa: BLE001 - never fail the turn on extraction
        logger.warning(f"[fetch_url] trafilatura extract failed: {e}")
        return None


def fetch_url(url: str, mode: str = "markdown") -> str:
    """Fetch `url` and return cleaned content. Returns an error sentinel string
    (never raises) so a tool-calling loop can react without a crash."""
    if not url or not url.strip():
        return "ERROR: fetch_url requires a non-empty url."
    url = url.strip()
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url

    import httpx

    try:
        with httpx.Client(
            follow_redirects=True, timeout=_TIMEOUT_S,
            headers={"User-Agent": "Mozilla/5.0 (nephilim-coordinator)"},
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
            raw = resp.content[:_MAX_BYTES].decode(resp.encoding or "utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[fetch_url] fetch failed for {url}: {e}")
        return f"ERROR: could not fetch {url}: {e}"

    if mode == "raw":
        return raw[:_MAX_OUTPUT_CHARS]

    text = _trafilatura_extract(raw, url, as_markdown=(mode != "text"))
    if not text:
        text = _stdlib_extract(raw)
    if not text:
        return f"ERROR: fetched {url} but could not extract readable content."
    return text[:_MAX_OUTPUT_CHARS]
