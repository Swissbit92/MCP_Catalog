"""Split long text into Telegram-sized chunks.

Telegram's hard limit for a single sendMessage is 4096 characters. We split
below a configurable soft limit (default 4000) with headroom. Splitting prefers,
in order: paragraph boundaries (blank line), single newlines, sentence
boundaries, whitespace, and only as a last resort a hard mid-token cut.
"""

from __future__ import annotations

import re

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?…])\s+")


def _hard_chunks(text: str, limit: int) -> list[str]:
    """Last resort: cut every `limit` chars, preferring the last whitespace."""
    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        window = remaining[:limit]
        cut = window.rfind(" ")
        if cut <= 0:
            cut = limit  # no space to break on — hard cut
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


def _split_unit(unit: str, limit: int) -> list[str]:
    """Split a single over-limit unit by sentences, then hard chunks."""
    if len(unit) <= limit:
        return [unit]
    out: list[str] = []
    buf = ""
    for sentence in _SENTENCE_BOUNDARY.split(unit):
        candidate = f"{buf} {sentence}".strip() if buf else sentence
        if len(candidate) <= limit:
            buf = candidate
            continue
        if buf:
            out.append(buf)
            buf = ""
        if len(sentence) > limit:
            out.extend(_hard_chunks(sentence, limit))
        else:
            buf = sentence
    if buf:
        out.append(buf)
    return out


def split_for_telegram(text: str, limit: int = 4000) -> list[str]:
    """Return `text` split into chunks each <= `limit` characters.

    Returns [] for empty/whitespace-only input. Chunk boundaries prefer natural
    breaks (paragraphs, then lines, then sentences) so replies read cleanly.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]

    # Break into paragraph/line units, then greedily pack them into chunks.
    units = re.split(r"(\n{2,}|\n)", text)
    chunks: list[str] = []
    buf = ""
    for unit in units:
        if unit == "":
            continue
        # Keep separators attached to the preceding content when packing.
        candidate = buf + unit if buf else unit
        if len(candidate) <= limit:
            buf = candidate
            continue
        # Flush what we have, then handle the over-limit unit on its own.
        if buf.strip():
            chunks.append(buf.strip())
        buf = ""
        if len(unit) > limit:
            chunks.extend(_split_unit(unit.strip(), limit))
        else:
            buf = unit
    if buf.strip():
        chunks.append(buf.strip())
    return [c for c in chunks if c]
