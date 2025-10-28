# ui/personas.py
# Persona data & asset helpers (no Streamlit imports here)

from __future__ import annotations
import os
import json
import base64
from typing import List, Dict, Optional

# Optional shared resolver (preferred)
try:
    from src.shared.persona_assets import resolve_all_assets, DEFAULTS
except Exception:
    # Fallback tiny defaults if src not importable (still works)
    DEFAULTS = {
        "image": "ui/images/default_card.png",
        "avatar": "ui/images/default_avatar.png",
        "logo": "ui/images/default_logo.png",
        "bg": "ui/images/default_bg.jpg",
    }
    def resolve_all_assets(card: dict, env_lookup, persona_key: Optional[str]) -> dict:
        # Minimal fallback: just return defaults, JSON wins if present
        out = {}
        for k in ("image", "avatar", "logo", "bg"):
            v = card.get(k) or DEFAULTS[k]
            out[k] = v
        return out

def coord_url() -> str:
    return os.getenv("COORD_URL", "http://127.0.0.1:8000")

def persona_model() -> str:
    return os.getenv("PERSONA_MODEL", "llama3.1:8b")

def persona_dir() -> str:
    return os.getenv("PERSONA_DIR", "personas")

# Visual asset envs (app-level)
APP_LOGO     = os.getenv("APP_LOGO_PATH", "")
USER_AVATAR  = os.getenv("USER_AVATAR", "🧑")

# Legacy per-persona envs kept for backward-compatibility (optional)
EEVA_LOGO    = os.getenv("EEVA_LOGO", "")
CINDY_LOGO   = os.getenv("CINDY_LOGO", "")
EEVA_AVATAR  = os.getenv("EEVA_AVATAR", "🧠")
CINDY_AVATAR = os.getenv("CINDY_AVATAR", "🛠️")

# ---------------- Persona discovery ----------------

def _list_json_files(p_dir: str) -> List[str]:
    try:
        files = [f for f in os.listdir(p_dir) if f.endswith(".json")]
    except FileNotFoundError:
        files = []
    return sorted(files, key=lambda s: s.lower())

def load_persona_cards(p_dir: str) -> List[Dict]:
    """Load all persona JSONs dynamically; ensure 'key' exists; stable order."""
    cards: List[Dict] = []
    for name in _list_json_files(p_dir):
        path = os.path.join(p_dir, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                card = json.load(f)
            if "key" not in card or not isinstance(card["key"], str) or not card["key"].strip():
                stem = os.path.splitext(name)[0]
                card["key"] = stem.capitalize()
            cards.append(card)
        except Exception:
            # Skip malformed files; you could log here if needed
            continue
    return cards

# ---------------- Labels & display helpers ----------------

def build_coordinator_label(card: dict, fallback_key: str) -> str:
    """
    Coordinator-compatible persona label:
      1) card['coordinator_label'] if present
      2) 'Name (Style)' built from display_name (splitting on —/–/-)
      3) stable key-based fallback ('Key (Style)')
    """
    if card.get("coordinator_label"):
        return str(card["coordinator_label"])

    display = card.get("display_name")
    style = card.get("style", "").strip()
    if isinstance(display, str) and any(sep in display for sep in ["—", "–", "-"]):
        base, maybe_style = [s.strip() for s in display.split("—" if "—" in display else ("–" if "–" in display else "-"), 1)]
        if base and (maybe_style or style):
            return f"{base} ({maybe_style or style})"

    # fallback by key + style
    if style:
        return f"{fallback_key} ({style})"
    # last resort defaults similar to old behavior
    if fallback_key.lower().startswith("cindy"):
        return "Cindy (Pragmatic Builder)"
    return "Eeva (Nerdy Charming)"

def display_name_to_tag(display_name: Optional[str], key: str) -> str:
    """Produce 'Name — Style' for header chip."""
    if isinstance(display_name, str) and any(sep in display_name for sep in ["—", "–", "-"]):
        return display_name
    style = "Pragmatic Builder" if key.lower().startswith("cindy") else "Nerdy Charming"
    return f"{key} — {style}"

# ---------------- Image helpers ----------------

def _file_to_data_uri(path: str) -> Optional[str]:
    """Return data:image/*;base64,... for a local file; None if missing."""
    try:
        if not path:
            return None
        p = path
        if not os.path.exists(p):
            alt = os.path.join("ui", path) if not path.startswith("ui/") else path
            if os.path.exists(alt):
                p = alt
            else:
                return None
        mime = "image/png"
        pl = p.lower()
        if pl.endswith(".jpg") or pl.endswith(".jpeg"):
            mime = "image/jpeg"
        elif pl.endswith(".gif"):
            mime = "image/gif"
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None

def resolve_card_image(card: dict, key: str) -> Optional[str]:
    """
    Prefer card['image'] (if it points to a local file) → logo (env/JSON/default) → default card.
    Always return a data URI if a local file exists; otherwise None (UI shows emoji tile).
    """
    # 1) explicit 'image' field from card
    if isinstance(card.get("image"), str):
        uri = _file_to_data_uri(card["image"])
        if uri:
            return uri

    # 2) fall back to logo asset (resolved below)
    assets = persona_assets_by_key(key)
    for candidate in [assets.get("logo"), DEFAULTS["image"]]:
        uri = _file_to_data_uri(candidate or "")
        if uri:
            return uri
    return None

# ---------------- Asset aggregation for UI ----------------

def _find_card_by_key(cards: List[Dict], key: str) -> Optional[Dict]:
    lk = key.lower()
    for c in cards:
        ck = (c.get("key") or "").lower()
        if lk == ck or ck.startswith(lk):
            return c
    return None

def persona_assets_by_key(key: str) -> Dict[str, str]:
    """
    Return {"logo": <path_or_url>, "avatar": <emoji_or_path_or_url>, "tag": "..."}.
    Priority for logo/avatar/bg is JSON → .env legacy → defaults.
    If no avatar image, we fall back to emoji if present in JSON, else initials.
    """
    p_dir = persona_dir()
    cards = load_persona_cards(p_dir)
    card = _find_card_by_key(cards, key)
    persona_key = (card.get("key") if card else key) if isinstance(key, str) else None

    assets = resolve_all_assets(card or {}, os.getenv, persona_key)

    # Avatar: if default image and card carries emoji, prefer emoji (nice UX)
    avatar = assets.get("avatar", DEFAULTS["avatar"])
    if (not str(avatar).startswith(("http://", "https://")) and avatar == DEFAULTS["avatar"]):
        emoji = (card or {}).get("emoji")
        if isinstance(emoji, str) and emoji.strip():
            avatar = emoji.strip()
        else:
            # initials fallback
            disp = (card or {}).get("display_name") or (persona_key or "AI")
            initials = "".join([w[0] for w in disp.split() if w][:2]).upper()
            avatar = initials or "🤖"

    tag = display_name_to_tag((card or {}).get("display_name"), persona_key or key)
    return {"logo": assets.get("logo"), "avatar": avatar, "tag": tag}
