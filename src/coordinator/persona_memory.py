# src/coordinator/persona_memory.py
# Persona memory and prompt construction (dynamic discovery + resolver).

from __future__ import annotations

import os, json
from functools import lru_cache
from typing import Dict, List, Optional

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

# ---------------- LLM client ----------------

def _llm() -> OllamaLLM:
    base = get_ollama_base()
    model = get_persona_model()
    assert_model_available(base, model)
    return OllamaLLM(base_url=base, model=model, temperature=get_persona_temperature())

# ---------------- Persona discovery ----------------

def _iter_persona_files() -> List[str]:
    """Return absolute paths to all *.json in PERSONA_DIR (sorted, stable)."""
    pdir = get_persona_dir()
    try:
        files = [os.path.join(pdir, f) for f in os.listdir(pdir) if f.endswith(".json")]
    except FileNotFoundError:
        files = []
    return sorted(files, key=lambda s: os.path.basename(s).lower())

def _load_card_file(path: str) -> Optional[Dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            card = json.load(f)
        # ensure key exists
        if "key" not in card or not isinstance(card["key"], str) or not card["key"].strip():
            # fallback to stem (Capitalized)
            stem = os.path.splitext(os.path.basename(path))[0]
            card["key"] = stem.capitalize()
        return card
    except Exception:
        return None

@lru_cache(maxsize=1)
def _load_all_cards_cached() -> List[Dict]:
    cards: List[Dict] = []
    for fp in _iter_persona_files():
        card = _load_card_file(fp)
        if card:
            cards.append(card)
    return cards

def _cards_by_all_names() -> Dict[str, Dict]:
    """
    Build an index mapping potential selectors to cards:
      - coordinator_label (if present)
      - display_name
      - key
      - lowercased variants
    """
    idx: Dict[str, Dict] = {}
    for c in _load_all_cards_cached():
        cand = set()
        for field in ("coordinator_label", "display_name", "key"):
            v = c.get(field)
            if isinstance(v, str) and v.strip():
                cand.add(v.strip())
                cand.add(v.strip().lower())
        for k in cand:
            idx[k] = c
    return idx

def resolve_persona_to_card(selector: Optional[str]) -> Optional[Dict]:
    """
    Resolve a persona by coordinator label, display name, or key (case-insensitive).
    If selector is None/empty, return the first discovered card (stable order).
    """
    cards = _load_all_cards_cached()
    if not cards:
        return None
    if not selector:
        return cards[0]
    idx = _cards_by_all_names()
    hit = idx.get(selector) or idx.get(selector.lower())
    return hit or cards[0]

# ---------------- Identity summary & prompts ----------------

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

@lru_cache(maxsize=32)
def build_system_prompt(selector: Optional[str]) -> str:
    """
    Build system prompt for a persona resolved by label/key; falls back to first card.
    """
    card = resolve_persona_to_card(selector)
    if not card:
        # extremely defensive fallback
        name = "Persona"
        style = "helpful, concise"
        identity = "A helpful, concise assistant."
    else:
        name = (card.get("display_name") or card.get("key") or "Persona")
        style = (card.get("style") or "helpful & concise")
        identity = _summarize(name, style, card.get("lore", []))
    who = name.split(" — ")[0].strip()
    return (
        f"You are {who}, a {style} assistant.\n\n"
        f"Identity:\n{identity}\n\n"
        f"{BASE_ROUTING_RULES}"
    )

def get_persona_card(selector: Optional[str]) -> Dict:
    card = resolve_persona_to_card(selector)
    return card or {"key": "Persona", "display_name": "Persona — Helpful", "style": "helpful & concise"}

def build_greeting_user_prompt(selector: Optional[str]) -> str:
    """Create a short, persona-shaped greeting instruction for the LLM."""
    card = get_persona_card(selector)
    voice = card.get("voice") or {}
    greeting_hint = voice.get("greeting", "") if isinstance(voice, dict) else ""
    return (
        "Generate a short welcome message for the chat.\n"
        "Constraints:\n"
        "- 1 to 2 sentences max.\n"
        "- Reflect the persona's style.\n"
        "- Invite the user to ask a question.\n"
        "- No system or meta text, just the greeting.\n"
        f"Optional greeting hint: {greeting_hint or '(none)'}"
    )
