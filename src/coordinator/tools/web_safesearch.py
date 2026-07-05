# src/coordinator/tools/web_safesearch.py
"""Per-persona safesearch clamp — ADR-009 Phase W (NSFW capability flag).

A persona's `nsfw` flag sets a safesearch *floor*: a non-nsfw persona can never
drop below "moderate", regardless of what the model requests per call or the
global default. An nsfw persona has no floor ("off" allowed). The clamp only
tightens (never loosens) and is enforced in the executor, never the prompt.
"""

from __future__ import annotations

from typing import Optional

# Ordered from most permissive to most restrictive.
_ORDER = {"off": 0, "moderate": 1, "strict": 2}
_INV = {v: k for k, v in _ORDER.items()}


def clamp_safesearch(
    requested: Optional[str],
    persona_nsfw: bool,
    global_default: str = "off",
) -> str:
    """Return the effective safesearch level after the per-persona floor.

    - requested: the model's per-call value (None -> global_default).
    - persona_nsfw: True lifts the floor to "off" (no clamp); False floors at
      "moderate".
    """
    level = (requested or global_default or "off").strip().lower()
    level = level if level in _ORDER else "off"
    floor = "off" if persona_nsfw else "moderate"
    # Effective = the more restrictive of (level, floor).
    return _INV[max(_ORDER[level], _ORDER[floor])]
