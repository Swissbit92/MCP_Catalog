"""Loads and caches wiki entity content for system prompt injection."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

try:
    import yaml  # PyYAML (transitive dep via langchain); used for frontmatter parsing
except ImportError:  # pragma: no cover - yaml is expected to be present
    yaml = None  # type: ignore[assignment]

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
# Capturing variant: grabs the YAML body between the --- fences.
_FRONTMATTER_CAPTURE_RE = re.compile(r"^\s*---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Approximate word limit for the combined wiki context (~600 words)
_MAX_WORDS = 600

# Phase-2 caches (on-demand lore retrieval)
_meta_cache: dict[str, Optional[dict]] = {}   # entity_id -> {body, entity_type, aliases, ...}
_alias_index: Optional[dict[str, str]] = None  # alias_lowercase -> entity_id
_all_entity_ids: Optional[list[str]] = None


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter block (---...---) from the beginning of text."""
    return _FRONTMATTER_RE.sub("", text).strip()


def _parse_frontmatter(raw: str) -> dict:
    """Parse the YAML frontmatter block of a wiki file into a dict ({} if none/unparseable)."""
    if yaml is None:
        return {}
    m = _FRONTMATTER_CAPTURE_RE.match(raw)
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1))
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError as e:  # pragma: no cover - malformed frontmatter
        logger.warning("[LoreLoader] Frontmatter parse failed: %s", e)
        return {}


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


# ---------------------------------------------------------------------------
# Phase-2: on-demand lore retrieval helpers
# ---------------------------------------------------------------------------
def load_entity_with_metadata(entity_id: str) -> Optional[dict]:
    """Load a wiki entity's body plus parsed frontmatter metadata.

    Returns a dict with keys: ``entity_id``, ``body``, ``entity_type``,
    ``aliases`` (list[str]), ``relationships`` (list), ``canon`` (bool, default
    True), or ``None`` if the file does not exist. Cached per process.
    """
    if entity_id in _meta_cache:
        return _meta_cache[entity_id]

    path = _find_entity_file(entity_id)
    if path is None:
        _meta_cache[entity_id] = None
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        _meta_cache[entity_id] = None
        return None

    fm = _parse_frontmatter(raw)
    aliases = fm.get("aliases") or []
    if not isinstance(aliases, list):
        aliases = [aliases]
    meta = {
        "entity_id": fm.get("entity_id", entity_id),
        "body": _strip_frontmatter(raw),
        "entity_type": fm.get("entity_type", ""),
        "aliases": [str(a) for a in aliases],
        "relationships": fm.get("relationships") or [],
        "canon": bool(fm.get("canon", True)),
        "frontmatter": fm,  # full parsed frontmatter (capability activation_* fields etc.)
    }
    _meta_cache[entity_id] = meta
    return meta


def get_capability_ids() -> list[str]:
    """Return entity_ids whose entity_type is 'capability' (Phase-2 internal skills)."""
    out: list[str] = []
    for eid in get_all_entity_ids():
        meta = load_entity_with_metadata(eid)
        if meta and meta.get("entity_type") == "capability":
            out.append(eid)
    return out


def get_all_entity_ids() -> list[str]:
    """Return sorted entity_ids for every wiki entity (files with an entity_id frontmatter).

    Excludes non-entity files (index.md, README) which have no entity_id. Cached.
    """
    global _all_entity_ids
    if _all_entity_ids is not None:
        return _all_entity_ids
    ids: list[str] = []
    for path in _WIKI_DIR.rglob("*.md"):
        if path.stem in {"index", "README", "readme"}:
            continue
        try:
            fm = _parse_frontmatter(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        eid = fm.get("entity_id")
        if eid:
            ids.append(str(eid))
    _all_entity_ids = sorted(set(ids))
    return _all_entity_ids


def build_alias_index() -> dict[str, str]:
    """Build a lowercase alias/name -> entity_id lookup over all wiki entities.

    Each entity maps its own entity_id and every declared alias (lowercased) to
    its entity_id. Used by the deterministic keyword tier of lore retrieval.
    """
    index: dict[str, str] = {}
    for entity_id in get_all_entity_ids():
        meta = load_entity_with_metadata(entity_id)
        if not meta:
            continue
        index[entity_id.lower()] = entity_id
        for alias in meta["aliases"]:
            alias_norm = str(alias).strip().lower()
            if alias_norm:
                index.setdefault(alias_norm, entity_id)
    return index


def get_alias_index() -> dict[str, str]:
    """Return the cached alias index, building it on first call."""
    global _alias_index
    if _alias_index is None:
        _alias_index = build_alias_index()
        logger.info("[LoreLoader] Alias index built: %d aliases over %d entities",
                    len(_alias_index), len(get_all_entity_ids()))
    return _alias_index


def get_static_core_ids(persona_key: str) -> set[str]:
    """Return the 3 static-core entity_ids for a persona (to dedup against dynamic lore)."""
    entities = _PERSONA_ENTITIES.get(persona_key)
    return set(entities) if entities else set()
