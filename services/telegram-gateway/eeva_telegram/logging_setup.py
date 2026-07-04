"""Logging configuration with a bot-token redaction filter.

Defense in depth: the token should never be interpolated into a log string, but
a redaction filter guarantees it can't leak even if some dependency logs a URL
containing it (Telegram API URLs embed the token as /bot<token>/method).
"""

from __future__ import annotations

import logging
import re

_TOKEN_IN_URL = re.compile(r"/bot\d+:[A-Za-z0-9_-]+")


class RedactTokenFilter(logging.Filter):
    """Replace any Telegram bot-token-in-URL with /bot<redacted>."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str) and "/bot" in record.msg:
            record.msg = _TOKEN_IN_URL.sub("/bot<redacted>", record.msg)
        if record.args:
            record.args = tuple(
                _TOKEN_IN_URL.sub("/bot<redacted>", a) if isinstance(a, str) else a for a in record.args
            )
        return True


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logging with the redaction filter attached to every handler."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    redactor = RedactTokenFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(redactor)
    # httpx logs full request URLs (with the token) at INFO — quiet it to WARNING.
    logging.getLogger("httpx").setLevel(logging.WARNING)
