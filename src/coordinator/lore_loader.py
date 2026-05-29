"""Loads and caches wiki entity content for system prompt injection."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Resolved at import time: src/coordinator/ -> src/ -> nephilim/ -> docs/lore/wiki/
_WIKI_DIR: Path = Path(__file__).parent.parent.parent / "docs" / "lore" / "wiki"

# Module-level in-memory cache keyed by entity_id
_cache: dict[str, str] = {}

# Mapping of persona key → (persona entity, house entity, location entity)
_PERSONA_ENTITIES: dict[str, tuple[str, str, str]] = {
    "nephilim_eeva":   ("persona-eeva",   "house-crown",   "location-central-nexus"),
    "nephilim_aegis":  ("persona-aegis",  "house-bastion", "location-bastion-of-order"),
    "nephilim_aurora": ("persona-aurora", "house-horizon", "location-horizon-spire"),
    "nephilim_cipher": ("persona-cipher", "house-key",     "location-archive-infinite"),
    "nephilim_nyx":    ("persona-nyx",    "house-veil",    "location-neon-labyrinth"),
    "nephilim_solace": ("persona-solace", "house-ember",   "location-sanctuary-of-stillness"),
}

# Frontmatter pattern: matches --- ... --- at the start of the file
_FRONTMATTER_RE = re.compile(r"^\s*---\s*\n.*?\n---\s*\n", re.DOTALL)

# Approximate word limit for the combined wiki context (~600 words)
_MAX_WORDS = 600


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter block (---...---) from the beginning of text."""
    return _FRONTMATTER_RE.sub("", text).strip()


def _find_entity_file(entity_id: str) -> Optional[Path]:
    """Search wiki subdirectories for a file named {entity_id}.md."""
    for candidate in _WIKI_DIR.rglob(f"{entity_id}.md"):
        return candidate
    return None


def load_entity_body(entity_id: str) -> Optional[str]:
    """Read wiki entity file, strip YAML frontmatter, and return the body.

    Results are cached so each file is read at most once per process lifetime.

    Args:
        entity_id: The entity identifier, e.g. ``"persona-eeva"``.

    Returns:
        Body text (frontmatter stripped), or ``None`` if the file does not exist.
    """
    if entity_id in _cache:
        return _cache[entity_id]

    path = _find_entity_file(entity_id)
    if path is None:
        logger.warning("[LoreLoader] Entity file not found for id=%r in %s", entity_id, _WIKI_DIR)
        _cache[entity_id] = None  # type: ignore[assignment]
        return None

    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("[LoreLoader] FileNotFoundError reading %s", path)
        _cache[entity_id] = None  # type: ignore[assignment]
        return None

    body = _strip_frontmatter(raw)
    _cache[entity_id] = body
    return body


def _truncate_to_word_limit(text: str, max_words: int) -> str:
    """Truncate text to at most max_words words, appending '...' if cut."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."


def get_persona_lore_context(persona_key: str) -> str:
    """Build a formatted wiki context string for a given persona.

    Loads the persona entity body, their house body, and their location body,
    concatenates them into a single block suitable for injection into
    ``<world_context>``, and truncates to ~600 words.

    Args:
        persona_key: The persona key, e.g. ``"nephilim_eeva"``.

    Returns:
        Formatted wiki context string, or empty string if persona_key is not
        in the mapping (Wanderer/Gojo personas have no lore wiki entries).
    """
    entities = _PERSONA_ENTITIES.get(persona_key)
    if entities is None:
        return ""

    persona_id, house_id, location_id = entities

    sections: list[str] = []

    persona_body = load_entity_body(persona_id)
    if persona_body:
        sections.append(f"### {persona_id}\n{persona_body}")

    house_body = load_entity_body(house_id)
    if house_body:
        sections.append(f"### {house_id}\n{house_body}")

    location_body = load_entity_body(location_id)
    if location_body:
        sections.append(f"### {location_id}\n{location_body}")

    if not sections:
        return ""

    combined = "\n\n".join(sections)
    return _truncate_to_word_limit(combined, _MAX_WORDS)
