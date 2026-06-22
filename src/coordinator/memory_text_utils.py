"""Text preparation helpers for the embedding layer.

The RAG memory (``memory_rag.py``) and the semantic router both feed raw chat
text to an Ollama embedding model. Embedding models have a fixed input window
(e.g. ``nomic-embed-text`` ≈ 2048 tokens, ``bge-m3`` ≈ 8192). Recent Ollama
versions return HTTP 500 — not a silent truncation — when input exceeds the
window, which silently broke semantic memory on every chat. This module is the
single guard that normalizes, drops empty, and chunks/truncates text *before* it
ever reaches the embedder.

Kept dependency-light on purpose (no imports from ``llm_client`` / services) so
both the memory layer and the router can use it without import cycles.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

# ``estimate_tokens`` below uses tiktoken's ``cl100k_base`` as a portable proxy.
# Real embedding tokenizers (bge-m3 = SentencePiece/XLM-R, nomic = WordPiece)
# produce MORE tokens for the same English text — roughly up to ~1.5x. We size
# the working budget at 60% of the model window so that even worst-case
# tokenizer inflation stays comfortably under the true limit. For normal chat
# messages (well under 1k tokens) the guard never fires; only pathological long
# pastes get chunked.
_SAFETY_MARGIN = 0.6

_WS_RE = re.compile(r"\s+")


def estimate_tokens(text: str) -> int:
    """Estimate token count for ``text`` (portable, tokenizer-agnostic).

    Mirrors ``llm_client.estimate_tokens`` but without the heavy import chain so
    the embedding layer can depend on it freely. Uses tiktoken when available,
    falling back to a 4-chars-per-token approximation.
    """
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except (ImportError, Exception):
        return max(1, len(text) // 4)


def safe_token_budget(max_tokens: int) -> int:
    """Return the conservative per-chunk token budget for a model window.

    Applies ``_SAFETY_MARGIN`` to absorb tokenizer drift between our cl100k
    estimate and the embedder's real tokenizer. Floored at 256 so a
    misconfigured tiny window never degenerates to zero-length chunks.
    """
    return max(256, int(max_tokens * _SAFETY_MARGIN))


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace and strip ends.

    Excess whitespace (e.g. from pasted documents) both wastes tokens and is a
    known cause of severe Ollama embedding slowdowns.
    """
    return _WS_RE.sub(" ", text).strip()


def _encoder():
    """Return a tiktoken encoder, or ``None`` if unavailable."""
    try:
        import tiktoken
        return tiktoken.get_encoding("cl100k_base")
    except (ImportError, Exception):
        return None


def chunk_text(text: str, max_tokens: int, overlap_tokens: int = 128) -> List[str]:
    """Split ``text`` into chunks that each fit ``safe_token_budget(max_tokens)``.

    Returns ``[text]`` unchanged when it already fits — the common case, so
    normal messages keep exactly their current single-vector behaviour. Only
    oversized text is split, with ``overlap_tokens`` of overlap to preserve
    context across chunk boundaries. Token-accurate when tiktoken is present,
    with a character-based fallback otherwise.
    """
    budget = safe_token_budget(max_tokens)
    if estimate_tokens(text) <= budget:
        return [text]

    overlap = max(0, min(overlap_tokens, budget // 2))
    step = max(1, budget - overlap)

    enc = _encoder()
    if enc is not None:
        token_ids = enc.encode(text)
        chunks: List[str] = []
        for start in range(0, len(token_ids), step):
            window = token_ids[start:start + budget]
            if not window:
                break
            chunks.append(enc.decode(window).strip())
            if start + budget >= len(token_ids):
                break
        return [c for c in chunks if c]

    # Fallback: approximate token windows by characters (~4 chars/token).
    char_budget = budget * 4
    char_step = step * 4
    chunks = []
    for start in range(0, len(text), char_step):
        window = text[start:start + char_budget].strip()
        if window:
            chunks.append(window)
        if start + char_budget >= len(text):
            break
    return chunks


def truncate_for_embedding(text: str, max_tokens: int) -> str:
    """Normalize and hard-cap ``text`` to one embeddable chunk.

    Used for *query* embedding, where a single vector is required (a query must
    not fan out into multiple chunks). Returns the first chunk's worth of text.
    """
    normalized = normalize_whitespace(text)
    if not normalized:
        return ""
    chunks = chunk_text(normalized, max_tokens)
    return chunks[0] if chunks else ""


def prepare_for_embedding(
    pairs: List[Tuple[str, Dict[str, Any]]],
    max_tokens: int,
    overlap_tokens: int = 128,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Prepare ``(text, metadata)`` pairs for indexing into the vector store.

    For each pair: normalize whitespace, drop empty/whitespace-only text, and
    split any oversized text into multiple chunks. When a text is chunked, its
    metadata is replicated per chunk with ``chunk`` (0-based) and ``n_chunks``
    markers so callers can trace a vector back to its source message.

    Returns parallel ``(texts, metadatas)`` lists ready for
    ``FAISS.from_texts`` / ``add_texts``.
    """
    out_texts: List[str] = []
    out_metas: List[Dict[str, Any]] = []

    for raw_text, metadata in pairs:
        normalized = normalize_whitespace(raw_text)
        if not normalized:
            continue
        chunks = chunk_text(normalized, max_tokens, overlap_tokens)
        n_chunks = len(chunks)
        for chunk_idx, chunk in enumerate(chunks):
            meta = dict(metadata)
            meta["chunk"] = chunk_idx
            meta["n_chunks"] = n_chunks
            out_texts.append(chunk)
            out_metas.append(meta)

    return out_texts, out_metas
