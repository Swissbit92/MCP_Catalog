# src/coordinator/server.py
# Local Coordinator server for GraphRAG Local QA Chat with Personas
# Provides endpoints for chat and model-generated greetings.

from __future__ import annotations
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import get_ollama_base, get_persona_model, get_persona_temperature
from .ollama_utils import assert_model_available
from .llm_client import LC_OllamaClient
from .persona_memory import build_system_prompt, build_greeting_user_prompt, get_persona_card

app = FastAPI(title="Local Coordinator (Chat-only)", version="0.3.0")

# Preflight Ollama on startup
@app.on_event("startup")
def _startup():
    assert_model_available(get_ollama_base(), get_persona_model())

class ChatTurn(BaseModel):
    role: str
    content: str

class ChatBody(BaseModel):
    persona: Optional[str] = None  # dynamic resolution (first card if None)
    history: List[ChatTurn] = []
    message: str

class GreetBody(BaseModel):
    persona: Optional[str] = None  # dynamic resolution (first card if None)

@app.post("/persona/chat")
def chat(body: ChatBody):
    # Resolve persona implicitly to confirm it exists
    card = get_persona_card(body.persona)
    if not card:
        raise HTTPException(status_code=400, detail="Unknown persona.")
    system = build_system_prompt(body.persona)

    client = LC_OllamaClient(
        base=get_ollama_base(),
        model=get_persona_model(),
        temperature=get_persona_temperature(),
    )
    # keep last 6 turns to stay snappy
    history = body.history[-6:]
    lines = []
    for t in history:
        role = (t.role or "").lower()
        if role == "assistant":
            lines.append(f"[Assistant]\n{t.content}")
        else:
            lines.append(f"[User]\n{t.content}")
    lines.append(f"[User]\n{body.message}")
    user_compiled = "\n\n".join(lines)

    answer = client.complete(system=system, user_prompt=user_compiled)
    return {"answer": answer}

@app.post("/persona/greet")
def greet(body: GreetBody):
    # Resolve persona (first card if None)
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
