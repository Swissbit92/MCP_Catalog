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
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .startup import initialize_all, get_session_repo
from .routes.chat import router as chat_router
from .routes.sessions import router as sessions_router
from .routes.personas import router as personas_router
from .routes.nephilim import router as nephilim_router
from .routes.wallet import router as wallet_router
from .routes.auth import auth_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ----------------- Lifespan -----------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    initialize_all()
    yield
    # Shutdown — stop strategy scheduler gracefully
    from .startup import get_strategy_scheduler
    scheduler = get_strategy_scheduler()
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Strategy scheduler stopped")


# ----------------- FastAPI App -----------------

app = FastAPI(title="Local Coordinator (Chat-only)", version="0.7.0", lifespan=lifespan)

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
app.include_router(wallet_router)
app.include_router(auth_router)


# ----------------- Health & Debug Endpoints -----------------

@app.get("/health")
def health():
    """Health check endpoint."""
    try:
        model = get_settings().ollama.model
        # DB ping
        get_session_repo().get_all_sessions()
        return {"status": "ok", "model": model, "db": "ok"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "error", "detail": str(e)})


# Note: initialization is handled by the lifespan context manager above.
