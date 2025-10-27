# src/coordinator/persona_memory.py
# Persona memory and prompt construction for GraphRAG Local QA Chat with Personas
# Handles system prompt building and greeting message generation.
# Uses Ollama LLM via LangChain.

import os, json
from functools import lru_cache
from typing import Dict, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.llms import OllamaLLM
from ollama._types import ResponseError

from .config import (
    get_persona_dir, get_ollama_base, get_persona_model, get_persona_temperature
)
from .ollama_utils import assert_model_available

BASE_ROUTING_RULES = """Keep answers concise and structured.
If the user asks factual/grounded questions in the future, you may call tools.
For now, answer directly (no tools). If unsure, say so."""

def _llm() -> OllamaLLM:
    base = get_ollama_base()
    model = get_persona_model()
    assert_model_available(base, model)
    return OllamaLLM(base_url=base, model=model, temperature=get_persona_temperature())

@lru_cache(maxsize=8)
def _load_card(key: str) -> Dict:
    path = os.path.join(get_persona_dir(), f"{key.lower()}.json")
    if not os.path.exists(path):
        raise RuntimeError(f"Persona file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _summarize(display_name: str, style: str, lore: List[str]) -> str:
    lc = _llm()
    lore_text = "\n".join(lore or [])
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You condense biographies into short identity briefs."),
        ("user", "Create a compact identity summary (<= 180 tokens) for: {d}\nStyle: {s}\n\nLore:\n{l}\n\nReturn only the summary.")
    ]).format_prompt(d=display_name, s=style, l=lore_text).to_string()
    try:
        return lc.invoke(prompt).strip()
    except ResponseError as e:
        raise RuntimeError(str(e))

@lru_cache(maxsize=8)
def build_system_prompt(preset_name: str) -> str:
    mapping = {
        "Eeva (Nerdy Charming)": "eeva",
        "Cindy (Pragmatic Builder)": "cindy",
        "Eeva": "eeva", "Cindy": "cindy"
    }
    key = mapping.get(preset_name, "eeva")
    card = _load_card(key)
    identity = _summarize(card["display_name"], card["style"], card.get("lore", []))
    return (
        f"You are {card['display_name'].split(' — ')[0]}, a {card['style']} assistant.\n\n"
        f"Identity:\n{identity}\n\n"
        f"{BASE_ROUTING_RULES}"
    )

# ---------- NEW: greeting utilities ----------

def get_persona_card(preset_name: str) -> Dict:
    mapping = {
        "Eeva (Nerdy Charming)": "eeva",
        "Cindy (Pragmatic Builder)": "cindy",
        "Eeva": "eeva", "Cindy": "cindy"
    }
    key = mapping.get(preset_name, "eeva")
    return _load_card(key)

def build_greeting_user_prompt(preset_name: str) -> str:
    """Create a short, persona-shaped greeting instruction for the LLM."""
    card = get_persona_card(preset_name)
    greeting_hint = ""
    voice = card.get("voice") or {}
    if isinstance(voice, dict):
        greeting_hint = voice.get("greeting", "")

    # 1–2 sentences, warm, persona-toned, invites a question
    return (
        "Generate a short welcome message for the chat.\n"
        "Constraints:\n"
        "- 1 to 2 sentences max.\n"
        "- Reflect the persona's style.\n"
        "- Invite the user to ask a question.\n"
        "- No system or meta text, just the greeting.\n"
        f"Optional greeting hint: {greeting_hint or '(none)'}"
    )
