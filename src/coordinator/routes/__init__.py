# src/coordinator/routes/__init__.py
"""API route modules."""

from .chat import router as chat_router
from .sessions import router as sessions_router
from .personas import router as personas_router

__all__ = ["chat_router", "sessions_router", "personas_router"]
