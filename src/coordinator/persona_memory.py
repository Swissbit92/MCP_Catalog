# src/coordinator/persona_memory.py
# Persona memory, prompt construction, and CV-style summary caching.
# Adds inter-process file locking for serialized summary builds.

from __future__ import annotations

import os, json, hashlib, datetime, time
from pathlib import Path
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

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
        if "key" not in card or not isinstance(card["key"], str) or not card["key"].strip():
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
    idx: Dict[str, Dict] = {}
    for c in _load_all_cards_cached():
        cand = set()
        for field in ("coordinator_label", "display_name", "key"):
            v = c.get(field)
            if isinstance(v, str) and v.strip():
                cand.add(v.strip()); cand.add(v.strip().lower())
        for k in cand:
            idx[k] = c
    return idx

def resolve_persona_to_card(selector: Optional[str]) -> Optional[Dict]:
    cards = _load_all_cards_cached()
    if not cards:
        return None
    if not selector:
        return cards[0]
    idx = _cards_by_all_names()
    hit = idx.get(selector) or idx.get(selector.lower())
    return hit or cards[0]

# ---------------- Summarization (for system prompt identity) ----------------

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
    keys = ["warmth", "assertiveness", "playfulness", "skepticism"]
    parts = []
    for k in keys:
        v = sliders.get(k)
        if isinstance(v, (int, float)):
            parts.append(f"{k}={float(v):.2f}")
    for k in sorted(sliders.keys()):
        if k in keys:
            continue
        v = sliders.get(k)
        if isinstance(v, (int, float)):
            parts.append(f"{k}={float(v):.2f}")
    return ", ".join(parts)

def _build_behavior_block(card: Dict) -> str:
    behavior = card.get("behavior") or {}
    emprof   = card.get("emotional_profile") or {}
    bounds   = card.get("boundaries") or {}
    dialog   = card.get("dialogue_prefs") or {}
    sig      = card.get("signature_moves") or []
    phrases  = card.get("example_phrases") or []
    expert   = card.get("expertise") or {}
    esc      = card.get("escalation_policy") or {}

    lines: List[str] = []

    traits = _join_list(behavior.get("traits"))
    pace = behavior.get("pace"); formality = behavior.get("formality")
    humor = behavior.get("humor"); emoji_pol = behavior.get("emoji_policy")
    small_talk = behavior.get("small_talk"); clar_q = behavior.get("clarifying_questions")
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

    if isinstance(sig, list) and sig:
        lines.append("Habits:")
        for s in sig[:3]:
            if isinstance(s, str) and s.strip():
                lines.append(f"- {s.strip()}")

    if isinstance(phrases, list):
        for ex in phrases:
            if isinstance(ex, str) and ex.strip():
                lines.append(f'Example: "{ex.strip()}"')
                break

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
    max_lines = 18
    if len(lines) > max_lines:
        lines = lines[:max_lines] + ["- (truncated)"]
    return "\n".join(lines)

@lru_cache(maxsize=32)
def build_system_prompt(selector: Optional[str]) -> str:
    card = resolve_persona_to_card(selector)
    if not card:
        name = "Persona"; style = "helpful, concise"
        identity = "A helpful, concise assistant."; beh_block = ""
    else:
        name = (card.get("display_name") or card.get("key") or "Persona")
        style = (card.get("style") or "helpful & concise")
        identity = _summarize(name, style, card.get("lore", []))
        beh_block = _build_behavior_block(card)

    who = name.split(" — ")[0].strip()
    parts = [
        f"You are {who}, a {style} assistant.",
        "", "Identity:",
        identity.strip() if isinstance(identity, str) else "A helpful, concise assistant.",
    ]
    if beh_block: parts.extend(["", beh_block.strip()])
    parts.extend(["", BASE_ROUTING_RULES])
    return "\n".join(parts)

def get_persona_card(selector: Optional[str]) -> Dict:
    card = resolve_persona_to_card(selector)
    return card or {"key": "Persona", "display_name": "Persona — Helpful", "style": "helpful & concise"}

# ---------------- CV-style Summary Cache ----------------

def _summary_dir() -> Path:
    return Path(get_persona_dir()) / "_summaries"

def _normalize_for_fingerprint(card: Dict) -> Dict:
    exclude = {"emoji"}  # add more if needed
    return {k: v for k, v in card.items() if k not in exclude}

def _fingerprint(card: Dict) -> str:
    normalized = _normalize_for_fingerprint(card)
    blob = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()

def _summary_file_for_key(key: str) -> Path:
    d = _summary_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{key}.json"

def _load_cached_summary(key: str) -> Optional[Dict]:
    fp = _summary_file_for_key(key)
    if not fp.is_file():
        return None
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "summary" in data and "hash" in data:
            return data
        return None
    except Exception:
        return None

def _save_summary(key: str, hash_: str, summary: str) -> Dict:
    payload = {
        "key": key,
        "hash": hash_,
        "updated": datetime.datetime.utcnow().isoformat() + "Z",
        "summary": summary.strip()
    }
    fp = _summary_file_for_key(key)
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload

def _make_cv_summary(card: Dict) -> str:
    name = (card.get("display_name") or card.get("key") or "Persona")
    style = card.get("style") or ""
    lore  = card.get("lore") or []
    voice = card.get("voice") or {}
    values = {
        "name": name,
        "style": style,
        "lore": "\n".join([str(x) for x in lore if isinstance(x, str)]),
        "tics": ", ".join(voice.get("tics", []) if isinstance(voice, dict) else []),
    }

    lc = _llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You write short, elegant, first-person CV bios that read like a story."),
        ("user",
         "Write a compact CV-style narrative (120–220 words) for {name}.\n"
         "Tone: consistent with '{style}'.\n"
         "Use full sentences (no bullet points). Prefer one cohesive paragraph.\n"
         "Use third person. Focus on strengths, style, and signature habits.\n"
         "You may draw lightly from the lore below, but keep it concise and vivid.\n"
         "If given quirks/tics, weave them subtly.\n\n"
         "Lore:\n{lore}\n\n"
         "Return only the paragraph."
        )
    ]).format_prompt(**values).to_string()

    try:
        return lc.invoke(prompt).strip()
    except ResponseError as e:
        raise RuntimeError(str(e))

# ---------------- Inter-process lock (simple PID file) ----------------

def _lock_path() -> Path:
    return _summary_dir() / ".lock"

def _lock_owned_by_me(pid: int) -> bool:
    lp = _lock_path()
    try:
        if not lp.exists():
            return False
        content = lp.read_text(encoding="utf-8").strip()
        return content == str(pid)
    except Exception:
        return False

def _acquire_lock(timeout_sec: float = 300.0, poll_sec: float = 0.25) -> bool:
    """
    Create a lock file with this process PID.
    Returns True if acquired, False if timeout elapsed.
    """
    lp = _lock_path()
    me = os.getpid()
    start = time.time()
    while True:
        try:
            # Exclusive create; fail if exists
            fd = os.open(str(lp), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(str(me))
            return True
        except FileExistsError:
            # Someone else holds the lock. If it's ours, consider acquired.
            if _lock_owned_by_me(me):
                return True
            if time.time() - start >= timeout_sec:
                return False
            time.sleep(poll_sec)
        except Exception:
            if time.time() - start >= timeout_sec:
                return False
            time.sleep(poll_sec)

def _release_lock():
    lp = _lock_path()
    try:
        if lp.exists():
            lp.unlink()
    except Exception:
        pass

# ---------------- Public summary API (lock-aware) ----------------

def get_or_build_cv_summary(selector: Optional[str]) -> Dict:
    """
    Returns {key, hash, updated, summary}. Rebuilds if missing or stale.
    Lock-aware to avoid races with preflight or concurrent requests.
    """
    card = resolve_persona_to_card(selector)
    if not card:
        raise RuntimeError("No personas available.")
    key = (card.get("key") or "Persona").split()[0].capitalize()
    want_hash = _fingerprint(card)
    cached = _load_cached_summary(key)
    if cached and cached.get("hash") == want_hash and isinstance(cached.get("summary"), str):
        return cached

    # Acquire lock briefly to build/update this one; avoid deadlock if we already own it
    me = os.getpid()
    need_release = False
    if not _lock_owned_by_me(me):
        if not _acquire_lock(timeout_sec=60.0, poll_sec=0.2):
            # Best-effort: if we couldn't get the lock quickly, re-check cache and bail
            cached = _load_cached_summary(key)
            if cached and cached.get("hash") == want_hash:
                return cached
            raise RuntimeError("Summary builder busy; please retry shortly.")
        need_release = True

    try:
        # Double-check cache after lock to avoid duplicate work
        cached = _load_cached_summary(key)
        if cached and cached.get("hash") == want_hash and isinstance(cached.get("summary"), str):
            return cached
        text = _make_cv_summary(card)
        return _save_summary(key, want_hash, text)
    finally:
        if need_release:
            _release_lock()

def cleanup_summary_store() -> None:
    """
    Remove summaries for personas that no longer exist.
    """
    dir_ = _summary_dir()
    if not dir_.exists():
        return
    live_keys = { (c.get("key") or "").split()[0].capitalize()
                  for c in _load_all_cards_cached() if isinstance(c.get("key"), str) }
    for f in dir_.glob("*.json"):
        key = f.stem
        if key not in live_keys and f.name != ".lock":
            try:
                f.unlink()
            except Exception:
                pass

def ensure_all_summaries() -> Tuple[int, int]:
    """
    Build/refresh summaries for all personas. Returns (built_count, skipped_count).
    Not lock-safe by itself — call ensure_all_summaries_serialized for inter-process safety.
    """
    cleanup_summary_store()
    built = 0
    skipped = 0
    for card in _load_all_cards_cached():
        selector = card.get("key")
        key = (card.get("key") or "Persona").split()[0].capitalize()
        want_hash = _fingerprint(card)
        cached = _load_cached_summary(key)
        if cached and cached.get("hash") == want_hash and isinstance(cached.get("summary"), str):
            skipped += 1
            continue
        text = _make_cv_summary(card)
        _save_summary(key, want_hash, text)
        built += 1
    return built, skipped

def ensure_all_summaries_serialized(timeout_sec: float = 300.0, poll_sec: float = 0.25) -> Tuple[int, int]:
    """
    Acquire global summary lock, then run ensure_all_summaries() once.
    Returns (built_count, skipped_count).
    """
    if not _acquire_lock(timeout_sec=timeout_sec, poll_sec=poll_sec):
        # Could not acquire — treat as "someone else is doing it"; give caller a benign result.
        return (0, 0)
    try:
        return ensure_all_summaries()
    finally:
        _release_lock()

# ---------------- Greeting prompt ----------------

def build_greeting_user_prompt(selector: Optional[str]) -> str:
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
