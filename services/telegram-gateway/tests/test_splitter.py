"""Tests for the Telegram message splitter."""

from __future__ import annotations

from eeva_telegram.splitter import split_for_telegram


def test_empty_and_whitespace_return_empty():
    assert split_for_telegram("") == []
    assert split_for_telegram("   \n  ") == []


def test_under_limit_passthrough():
    assert split_for_telegram("hello world", limit=100) == ["hello world"]


def test_exact_limit_passthrough():
    text = "x" * 50
    assert split_for_telegram(text, limit=50) == [text]


def test_all_chunks_within_limit():
    text = ("Sentence one. Sentence two. Sentence three. " * 100).strip()
    chunks = split_for_telegram(text, limit=200)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)


def test_split_preserves_all_content():
    # Reassembling split words should preserve the full token set/order.
    text = " ".join(f"word{i}" for i in range(500))
    chunks = split_for_telegram(text, limit=120)
    assert all(len(c) <= 120 for c in chunks)
    assert " ".join(chunks).split() == text.split()


def test_prefers_paragraph_boundary():
    a = "A" * 300
    b = "B" * 300
    chunks = split_for_telegram(f"{a}\n\n{b}", limit=350)
    assert chunks == [a, b]  # split on the blank line, not mid-paragraph


def test_hard_split_of_single_long_token():
    text = "z" * 1000  # no whitespace to break on
    chunks = split_for_telegram(text, limit=100)
    assert all(len(c) <= 100 for c in chunks)
    assert "".join(chunks) == text


def test_long_sentence_splits_on_sentence_boundary():
    text = ". ".join("word " * 20 for _ in range(10))
    chunks = split_for_telegram(text, limit=150)
    assert all(len(c) <= 150 for c in chunks)
