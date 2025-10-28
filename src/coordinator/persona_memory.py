# src/coordinator/persona_memory.py
# Persona memory and prompt construction (dynamic discovery + resolver).
# Inserts an optional, compact "behavioral block" into the system prompt
# when persona JSON includes fields like behavior, emotional_profile, etc.

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

def _join_list(vals: Optional[List[str]], sep: str = ", ") -> str:
    return sep.join([v for v in (vals or []) if isinstance(v, str) and v.strip()])

def _fmt_slider_block(sliders: Optional[Dict[str, float]]) -> str:
    if not isinstance(sliders, dict) or not sliders:
        return ""
    # keep stable order for readability
    keys = ["warmth", "assertiveness", "playfulness", "skepticism"]
    parts = []
    for k in keys:
        v = sliders.get(k)
        if isinstance(v, (int, float)):
            parts.append(f"{k}={float(v):.2f}")
    # include any extra keys deterministically
    for k in sorted(sliders.keys()):
        if k in keys:
            continue
        v = sliders.get(k)
        if isinstance(v, (int, float)):
            parts.append(f"{k}={float(v):.2f}")
    return ", ".join(parts)

def _build_behavior_block(card: Dict) -> str:
    """
    Construct a compact, bullet-style behavior block from optional persona fields.
    Skips silently if nothing is provided. Keeps the block short & prompt-friendly.
    """
    behavior = card.get("behavior") or {}
    emprof   = card.get("emotional_profile") or {}
    bounds   = card.get("boundaries") or {}
    dialog   = card.get("dialogue_prefs") or {}
    sig      = card.get("signature_moves") or []
    phrases  = card.get("example_phrases") or []
    expert   = card.get("expertise") or {}
    esc      = card.get("escalation_policy") or {}

    lines: List[str] = []

    # Behavior
    traits = _join_list(behavior.get("traits"))
    pace = behavior.get("pace"); formality = behavior.get("formality")
    humor = behavior.get("humor"); emoji_pol = behavior.get("emoji_policy")
    small_talk = behavior.get("small_talk")
    clar_q = behavior.get("clarifying_questions")
    beh_parts = []
    if traits: beh_parts.append(f"Traits: {traits}")
    sub_parts = []
    if pace: sub_parts.append(f"Pace: {pace}")
    if formality: sub_parts.append(f"Formality: {formality}")
    if humor: sub_parts.append(f"Humor: {humor}")
    if emoji_pol: sub_parts.append(f"Emoji: {emoji_pol}")
    if small_talk: sub_parts.append(f"Small talk: {small_talk}")
    if clar_q: sub_parts.append(f"Clarify: {clar_q}")
    if sub_parts: beh_parts.append(" | ".join(sub_parts))
    if beh_parts:
        lines.append("Behavior:")
        for p in beh_parts:
            lines.append(f"- {p}")

    # Emotional profile
    baseline = emprof.get("baseline")
    strengths = _join_list(emprof.get("strengths"))
    pitfalls  = _join_list(emprof.get("pitfalls"))
    sliders   = _fmt_slider_block(emprof.get("sliders"))
    ep_parts = []
    if baseline: ep_parts.append(f"Baseline: {baseline}")
    if strengths: ep_parts.append(f"Strengths: {strengths}")
    if pitfalls:  ep_parts.append(f"Pitfalls: {pitfalls}")
    if sliders:   ep_parts.append(f"Knobs: {sliders}")
    if ep_parts:
        lines.append("Emotions:")
        for p in ep_parts:
            lines.append(f"- {p}")

    # Dialogue prefs
    reply_shape = dialog.get("reply_shape")
    reason_vis  = dialog.get("reasoning_visibility")
    cite_style  = dialog.get("citations_style")
    dp_parts = []
    if reply_shape: dp_parts.append(f"Shape: {reply_shape}")
    if reason_vis:  dp_parts.append(f"Reasoning: {reason_vis}")
    if cite_style:  dp_parts.append(f"Citations: {cite_style}")
    if dp_parts:
        lines.append("Dialogue:")
        for p in dp_parts:
            lines.append(f"- {p}")

    # Expertise
    strong = _join_list(expert.get("strong"))
    familiar = _join_list(expert.get("familiar"))
    avoid = _join_list(expert.get("avoid"))
    ex_parts = []
    if strong:   ex_parts.append(f"Strong: {strong}")
    if familiar: ex_parts.append(f"Familiar: {familiar}")
    if avoid:    ex_parts.append(f"Avoid: {avoid}")
    if ex_parts:
        lines.append("Expertise:")
        for p in ex_parts:
            lines.append(f"- {p}")

    # Signature moves (limit to 3 to keep prompt tight)
    if isinstance(sig, list) and sig:
        lines.append("Habits:")
        for s in sig[:3]:
            if isinstance(s, str) and s.strip():
                lines.append(f"- {s.strip()}")

    # Example phrase (pick 1 as a tone anchor)
    if isinstance(phrases, list):
        for ex in phrases:
            if isinstance(ex, str) and ex.strip():
                lines.append(f'Example: "{ex.strip()}"')
                break

    # Boundaries (ethics/content/personal)
    b_eth = _join_list(bounds.get("ethics"))
    b_con = _join_list(bounds.get("content"))
    b_per = _join_list(bounds.get("personal"))
    b_parts = []
    if b_eth: b_parts.append(f"Ethics: {b_eth}")
    if b_con: b_parts.append(f"Content: {b_con}")
    if b_per: b_parts.append(f"Personal: {b_per}")
    if b_parts:
        lines.append("Boundaries:")
        for p in b_parts:
            lines.append(f"- {p}")

    # Escalation policy (brief)
    ask = _join_list(esc.get("when_to_ask_user"))
    decline = _join_list(esc.get("when_to_decline"))
    intent = _join_list(esc.get("tool_intent"))
    es_parts = []
    if ask:     es_parts.append(f"Ask user when: {ask}")
    if decline: es_parts.append(f"Decline when: {decline}")
    if intent:  es_parts.append(f"Tools: {intent}")
    if es_parts:
        lines.append("Escalation:")
        for p in es_parts:
            lines.append(f"- {p}")

    if not lines:
        return ""
    # Keep total size compact
    max_lines = 18
    if len(lines) > max_lines:
        lines = lines[:max_lines] + ["- (truncated)"]
    return "\n".join(lines)

@lru_cache(maxsize=32)
def build_system_prompt(selector: Optional[str]) -> str:
    """
    Build system prompt for a persona resolved by label/key; falls back to first card.
    Adds a compact behavioral block if present in the persona JSON.
    """
    card = resolve_persona_to_card(selector)
    if not card:
        # extremely defensive fallback
        name = "Persona"
        style = "helpful, concise"
        identity = "A helpful, concise assistant."
        beh_block = ""
    else:
        name = (card.get("display_name") or card.get("key") or "Persona")
        style = (card.get("style") or "helpful & concise")
        identity = _summarize(name, style, card.get("lore", []))
        beh_block = _build_behavior_block(card)

    who = name.split(" — ")[0].strip()

    parts = [
        f"You are {who}, a {style} assistant.",
        "",
        "Identity:",
        identity.strip() if isinstance(identity, str) else "A helpful, concise assistant.",
    ]
    if beh_block:
        parts.extend(["", beh_block.strip()])
    parts.extend(["", BASE_ROUTING_RULES])

    return "\n".join(parts)

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
