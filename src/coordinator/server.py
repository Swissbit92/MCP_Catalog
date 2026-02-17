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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],
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
        return JSONResponse(status_code=503, content={"status": "error", "detail": str(e)})


# ----------------- Initialization -----------------

# Run initialization on module load
initialize_all()
