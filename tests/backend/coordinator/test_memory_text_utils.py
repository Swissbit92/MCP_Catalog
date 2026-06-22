# tests/backend/coordinator/test_memory_text_utils.py
"""Unit tests for src/coordinator/memory_text_utils.py.

These are pure-Python tests with no Ollama / network dependency — they guard the
embedding-overflow fix: text must be normalized, empties dropped, and oversized
text chunked/truncated below the model window before it ever reaches the
embedder (Ollama returns HTTP 500 on overflow).
"""

from __future__ import annotations

from src.coordinator.memory_text_utils import (
    estimate_tokens,
    safe_token_budget,
    normalize_whitespace,
    chunk_text,
    truncate_for_embedding,
    prepare_for_embedding,
)

# A model window to test against (mirrors bge-m3's native context).
MAX_TOKENS = 8192


def _make_long_text(n_words: int) -> str:
    """Build text with a known, large token count from distinct words."""
    return " ".join(f"word{i}" for i in range(n_words))


class TestSafeBudget:
    def test_margin_below_window(self):
        # Budget must stay strictly below the raw window (tokenizer drift margin).
        assert safe_token_budget(MAX_TOKENS) < MAX_TOKENS

    def test_floor(self):
        # Tiny windows never produce a zero/negative budget.
        assert safe_token_budget(1) >= 256


class TestNormalizeWhitespace:
    def test_collapses_runs(self):
        assert normalize_whitespace("a   b\n\n\tc  ") == "a b c"

    def test_empty(self):
        assert normalize_whitespace("   \n\t ") == ""


class TestChunkText:
    def test_short_text_unchanged(self):
        # The common case: normal messages stay a single chunk (no behaviour change).
        text = "user: what's the weather like today?"
        assert chunk_text(text, MAX_TOKENS) == [text]

    def test_oversized_text_is_split(self):
        budget = safe_token_budget(MAX_TOKENS)
        # ~2x the budget worth of tokens guarantees a split.
        long_text = _make_long_text(budget * 2)
        chunks = chunk_text(long_text, MAX_TOKENS)
        assert len(chunks) > 1

    def test_every_chunk_within_budget(self):
        budget = safe_token_budget(MAX_TOKENS)
        long_text = _make_long_text(budget * 3)
        chunks = chunk_text(long_text, MAX_TOKENS)
        for chunk in chunks:
            # The whole point: no chunk may exceed the safe budget (so it can
            # never exceed the true model window after tokenizer inflation).
            assert estimate_tokens(chunk) <= budget

    def test_chunks_are_nonempty(self):
        long_text = _make_long_text(safe_token_budget(MAX_TOKENS) * 2)
        for chunk in chunk_text(long_text, MAX_TOKENS):
            assert chunk.strip()


class TestTruncateForEmbedding:
    def test_query_capped_to_one_chunk(self):
        budget = safe_token_budget(MAX_TOKENS)
        long_query = _make_long_text(budget * 3)
        result = truncate_for_embedding(long_query, MAX_TOKENS)
        # A query must map to a single vector — one chunk, within budget.
        assert estimate_tokens(result) <= budget
        assert result  # non-empty

    def test_empty_query(self):
        assert truncate_for_embedding("   \n ", MAX_TOKENS) == ""

    def test_short_query_normalized_only(self):
        assert truncate_for_embedding("  hello   world  ", MAX_TOKENS) == "hello world"


class TestPrepareForEmbedding:
    def test_drops_empty_text(self):
        pairs = [("   ", {"index": 0}), ("real content", {"index": 1})]
        texts, metas = prepare_for_embedding(pairs, MAX_TOKENS)
        assert texts == ["real content"]
        assert len(metas) == 1
        assert metas[0]["index"] == 1

    def test_normal_messages_one_vector_each(self):
        pairs = [
            ("user: hi", {"index": 0}),
            ("assistant: hello there", {"index": 1}),
        ]
        texts, metas = prepare_for_embedding(pairs, MAX_TOKENS)
        assert len(texts) == 2
        # Single-chunk markers on unsplit messages.
        assert all(m["n_chunks"] == 1 and m["chunk"] == 0 for m in metas)

    def test_oversized_message_expands_with_metadata(self):
        budget = safe_token_budget(MAX_TOKENS)
        long_text = _make_long_text(budget * 2)
        pairs = [(long_text, {"index": 5, "role": "assistant"})]
        texts, metas = prepare_for_embedding(pairs, MAX_TOKENS)
        assert len(texts) > 1
        # Source metadata preserved + chunk markers added, consistent n_chunks.
        assert all(m["index"] == 5 and m["role"] == "assistant" for m in metas)
        assert all(m["n_chunks"] == len(texts) for m in metas)
        assert [m["chunk"] for m in metas] == list(range(len(texts)))
        # And the guarantee that motivates the whole fix:
        for chunk in texts:
            assert estimate_tokens(chunk) <= budget

    def test_empty_input(self):
        assert prepare_for_embedding([], MAX_TOKENS) == ([], [])
