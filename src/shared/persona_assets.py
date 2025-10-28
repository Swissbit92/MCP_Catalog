# src/shared/persona_assets.py
# Shared, UI/Coordinator-agnostic persona asset resolver.

from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple

DEFAULTS = {
    "image": "ui/images/default_card.png",
    "avatar": "ui/images/default_avatar.png",
    "logo": "ui/images/default_logo.png",
    "bg": "ui/images/default_bg.jpg",
}

def _is_url(val: str) -> bool:
    return val.startswith(("http://", "https://", "data:image/"))

def _exists_local(path_or_rel: str) -> bool:
    p = Path(path_or_rel)
    if p.is_file():
        return True
    # Try relative to project root /ui for convenience
    if not path_or_rel.startswith("ui/"):
        alt = Path("ui") / path_or_rel
        return alt.is_file()
    return False

def _normalize_local(path_or_rel: str) -> str:
    """Ensure we return a usable local path (prefer under ui/ if present)."""
    p = Path(path_or_rel)
    if p.is_file():
        return str(p.as_posix())
    if not path_or_rel.startswith("ui/"):
        alt = Path("ui") / path_or_rel
        if alt.is_file():
            return str(alt.as_posix())
    return path_or_rel  # may be bad; caller/UI can handle gracefully

def resolve_asset(
    card: dict,
    env_lookup,
    key: str,
    *,
    persona_key: Optional[str] = None
) -> Tuple[str, bool]:
    """
    Resolve one asset such as 'image' | 'avatar' | 'logo' | 'bg'.
    Returns (value, is_default).
    Priority:
      1) Persona JSON field
      2) Legacy .env (EEVA_AVATAR, CINDY_LOGO, etc.) — optional
      3) Built-in DEFAULTS
    URLs are accepted without validation (frontend will fetch).
    """
    # 1) JSON
    v = (card or {}).get(key)
    if isinstance(v, str) and v.strip():
        v = v.strip()
        if _is_url(v) or _exists_local(v):
            return (_normalize_local(v), False)

    # 2) .env legacy
    if persona_key:
        env_key = f"{persona_key.upper()}_{key.upper()}"  # e.g., EEVA_AVATAR
        v = env_lookup(env_key)
        if isinstance(v, str) and v.strip():
            v = v.strip()
            if _is_url(v) or _exists_local(v):
                return (_normalize_local(v), False)

    # 3) default
    d = DEFAULTS[key]
    return (d, True)

def resolve_all_assets(card: dict, env_lookup, persona_key: Optional[str]) -> dict:
    out = {}
    for k in ("image", "avatar", "logo", "bg"):
        out[k], _ = resolve_asset(card, env_lookup, k, persona_key=persona_key)
    return out
