"""Tests for the bot-token redaction logging filter."""

from __future__ import annotations

import logging

from eeva_telegram.logging_setup import RedactTokenFilter


def _record(msg, *args):
    return logging.LogRecord("t", logging.INFO, __file__, 1, msg, args, None)


def test_redacts_token_in_message():
    rec = _record("GET https://api.telegram.org/bot123456:AAbb-cc_dd/getUpdates")
    RedactTokenFilter().filter(rec)
    assert "123456:AAbb-cc_dd" not in rec.getMessage()
    assert "/bot<redacted>" in rec.getMessage()


def test_redacts_token_in_args():
    rec = _record("calling %s", "https://api.telegram.org/bot999:ZZ_tok/sendMessage")
    RedactTokenFilter().filter(rec)
    assert "999:ZZ_tok" not in rec.getMessage()


def test_leaves_ordinary_messages_untouched():
    rec = _record("handled chat_id=%s ok", 111)
    RedactTokenFilter().filter(rec)
    assert rec.getMessage() == "handled chat_id=111 ok"


def test_filter_always_returns_true():
    # A logging filter must not drop records — it only rewrites them.
    assert RedactTokenFilter().filter(_record("anything")) is True
