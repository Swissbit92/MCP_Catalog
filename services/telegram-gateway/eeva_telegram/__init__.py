"""eeva-telegram — Telegram gateway to the NEPHILIM companion personas.

A thin, single-user (allowlisted) bridge: relays Telegram messages to the
existing nephilim FastAPI backend on localhost and relays persona replies back.
No agent framework, no tool access, no trading credentials — see docs/SECURITY.md.
"""

from __future__ import annotations

__version__ = "0.1.0"
