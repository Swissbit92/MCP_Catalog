# src/coordinator/server.py
# Local Coordinator server for GraphRAG Local QA Chat with Personas
# Provides endpoints for chat, greetings, and persona CV summaries.

from __future__ import annotations
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import get_ollama_base, get_persona_model, get_persona_temperature
from .ollama_utils import assert_model_available
from .llm_client import LC_OllamaClient
from .persona_memory import (
    build_system_prompt, build_greeting_user_prompt, get_persona_card,
    get_or_build_cv_summary, ensure_all_summaries_serialized
)

app = FastAPI(title="Local Coordinator (Chat-only)", version="0.4.1")

# Preflight Ollama (do not block on summaries here — run.py already did a blocking preflight)
@app.on_event("startup")
def _startup():
    assert_model_available(get_ollama_base(), get_persona_model())
    # Best-effort no-op refresh (non-blocking). If another process holds the lock, we just skip.
    try:
        ensure_all_summaries_serialized(timeout_sec=0.01, poll_sec=0.01)  # tiny timeout → effectively no-op
    except Exception:
        pass

class ChatTurn(BaseModel):
    role: str
    content: str

class ChatBody(BaseModel):
    persona: Optional[str] = None
    history: List[ChatTurn] = []
    message: str

class GreetBody(BaseModel):
    persona: Optional[str] = None

class SummaryBody(BaseModel):
    persona: Optional[str] = None  # label/key; None resolves to first card

@app.post("/persona/chat")
def chat(body: ChatBody):
    card = get_persona_card(body.persona)
    if not card:
        raise HTTPException(status_code=400, detail="Unknown persona.")
    system = build_system_prompt(body.persona)

    client = LC_OllamaClient(
        base=get_ollama_base(),
        model=get_persona_model(),
        temperature=get_persona_temperature(),
    )
    history = body.history[-6:]
    lines = []
    for t in history:
        role = (t.role or "").lower()
        lines.append(f"[Assistant]\n{t.content}" if role == "assistant" else f"[User]\n{t.content}")
    lines.append(f"[User]\n{body.message}")
    user_compiled = "\n\n".join(lines)

    answer = client.complete(system=system, user_prompt=user_compiled)
    return {"answer": answer}

@app.post("/persona/greet")
def greet(body: GreetBody):
    card = get_persona_card(body.persona)
    if not card:
        raise HTTPException(status_code=400, detail="Unknown persona.")
    system = build_system_prompt(body.persona)
    user_prompt = build_greeting_user_prompt(body.persona)

    client = LC_OllamaClient(
        base=get_ollama_base(),
        model=get_persona_model(),
        temperature=get_persona_temperature(),
    )
    answer = client.complete(system=system, user_prompt=user_prompt)
    return {"answer": answer}

@app.post("/persona/summary")
def summary(body: SummaryBody):
    """
    Returns the cached or freshly built CV-style summary for a persona.
    { key, hash, updated, summary }
    This endpoint is lock-aware to avoid races if a preflight is running.
    """
    try:
        data = get_or_build_cv_summary(body.persona)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary error: {e}")
