# src/coordinator/persona_loader.py
# Persona file loading and validation with Pydantic schema support.
# Part of modular refactor from persona_memory.py.

from __future__ import annotations

import os
import logging
from typing import Dict, List, Optional

from .config import get_settings
from .models.persona_schema import load_persona_card_lenient

# Setup logger
logger = logging.getLogger(__name__)


# ---------------- Persona discovery ----------------

def _iter_persona_files() -> List[str]:
    """Return absolute paths to all *.json in PERSONA_DIR (sorted, stable)."""
    pdir = get_settings().persona_dir
    try:
        files = [os.path.join(pdir, f) for f in os.listdir(pdir) if f.endswith(".json")]
    except FileNotFoundError:
        files = []
    return sorted(files, key=lambda s: os.path.basename(s).lower())


def _load_card_file(path: str) -> Optional[Dict]:
    """Load and validate a persona card from JSON file.

    Uses Pydantic validation in lenient mode (warnings, not failures) for
    backward compatibility during migration to typed schemas.

    Args:
        path: Path to persona JSON file

    Returns:
        Validated persona dict, or None if file cannot be loaded
    """
    # Use lenient validation - logs warnings but returns dict for compatibility
    card = load_persona_card_lenient(path)

    if card is None:
        return None

    # Ensure key exists (backward compatibility)
    if "key" not in card or not isinstance(card["key"], str) or not card["key"].strip():
        stem = os.path.splitext(os.path.basename(path))[0]
        card["key"] = stem.capitalize()
        logger.debug(f"Auto-generated key '{card['key']}' for persona at {path}")

    return card


def _load_all_cards_cached() -> List[Dict]:
    """Load all persona cards with caching."""
    cards: List[Dict] = []
    for fp in _iter_persona_files():
        card = _load_card_file(fp)
        if card:
            cards.append(card)
    return cards


def _cards_by_all_names() -> Dict[str, Dict]:
    """Build index mapping all persona name variants to their cards."""
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
    """Resolve persona selector to a card.

    Args:
        selector: Persona key/name, or None for default

    Returns:
        Persona card dict, or None if no personas exist
    """
    cards = _load_all_cards_cached()
    if not cards:
        return None
    if not selector:
        return cards[0]
    idx = _cards_by_all_names()
    hit = idx.get(selector) or idx.get(selector.lower())
    return hit or cards[0]


def get_persona_card(selector: Optional[str]) -> Dict:
    """Get persona card with fallback to default.

    Args:
        selector: Persona key/name

    Returns:
        Persona card dict (never None, falls back to default)
    """
    card = resolve_persona_to_card(selector)
    return card or {
        "key": "Persona",
        "display_name": "Persona — Helpful",
        "style": "helpful & concise"
    }
