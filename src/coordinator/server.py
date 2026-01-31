# src/coordinator/server.py
"""
Local Coordinator server for GraphRAG Local QA Chat with Personas.

This is the main entry point that assembles the FastAPI application
from modular components. Business logic is organized into:
- routes/ - API endpoint handlers
- services/ - Business logic services
- repositories/ - Database access layer
- schemas.py - Pydantic models

Provides endpoints for chat, greetings, persona CV summaries, and chat persistence (SQLite).
"""

from __future__ import annotations

import logging
import inspect

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_ollama_base, get_persona_model
from .startup import initialize_all, get_session_repo
from .routes.chat import router as chat_router
from .routes.sessions import router as sessions_router
from .routes.personas import router as personas_router
from .routes.nephilim import router as nephilim_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ----------------- FastAPI App -----------------

app = FastAPI(title="Local Coordinator (Chat-only)", version="0.6.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat_router)
app.include_router(sessions_router)
app.include_router(personas_router)
app.include_router(nephilim_router)


# ----------------- Health & Debug Endpoints -----------------

@app.get("/health")
def health():
    """Health check endpoint."""
    try:
        base = get_ollama_base()
        model = get_persona_model()
        # DB ping
        get_session_repo().get_all_sessions()
        return {"status": "ok", "model": model, "db": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/debug/code-version")
def code_version():
    """Debug endpoint to verify which code version is running."""
    from .routes.chat import chat_with_session
    source = inspect.getsource(chat_with_session)
    has_memory_loading = "db_messages = message_repo.get_messages_by_session" in source
    has_modular_design = "deps = _get_dependencies()" in source
    return {
        "memory_loading_code_present": has_memory_loading,
        "modular_design": has_modular_design,
        "version": "0.6.0-modular",
        "function_first_line": source.split('\n')[1][:100] if '\n' in source else "unknown"
    }


# ----------------- Initialization -----------------

# Run initialization on module load
initialize_all()
