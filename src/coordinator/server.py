# src/coordinator/server.py
# Local Coordinator server for GraphRAG Local QA Chat with Personas
# Provides endpoints for chat and model-generated greetings.

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

from .config import get_ollama_base, get_persona_model, get_persona_temperature
from .ollama_utils import assert_model_available
from .llm_client import LC_OllamaClient
from .persona_memory import build_system_prompt, build_greeting_user_prompt

app = FastAPI(title="Local Coordinator (Chat-only)", version="0.2.0")

# Preflight Ollama on startup
@app.on_event("startup")
def _startup():
    assert_model_available(get_ollama_base(), get_persona_model())

class ChatTurn(BaseModel):
    role: str
    content: str

class ChatBody(BaseModel):
    persona: str = "Eeva (Nerdy Charming)"
    history: List[ChatTurn] = []
    message: str

class GreetBody(BaseModel):
    persona: str = "Eeva (Nerdy Charming)"

@app.post("/persona/chat")
def chat(body: ChatBody):
    system = build_system_prompt(body.persona)
    client = LC_OllamaClient(
        base=get_ollama_base(),
        model=get_persona_model(),
        temperature=get_persona_temperature(),
    )
    history = body.history[-6:]
    lines = []
    for t in history:
        role = t.role.lower()
        if role == "assistant":
            lines.append(f"[Assistant]\n{t.content}")
        else:
            lines.append(f"[User]\n{t.content}")
    lines.append(f"[User]\n{body.message}")
    user_compiled = "\n\n".join(lines)

    answer = client.complete(system=system, user_prompt=user_compiled)
    return {"answer": answer}

# ---------- NEW: model-generated greeting on page load ----------
@app.post("/persona/greet")
def greet(body: GreetBody):
    system = build_system_prompt(body.persona)
    user_prompt = build_greeting_user_prompt(body.persona)
    client = LC_OllamaClient(
        base=get_ollama_base(),
        model=get_persona_model(),
        temperature=get_persona_temperature(),
    )
    answer = client.complete(system=system, user_prompt=user_prompt)
    return {"answer": answer}
