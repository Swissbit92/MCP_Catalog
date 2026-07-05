# src/coordinator/routes/personas.py
"""Persona-related API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..schemas import SummaryBody
from ..persona_memory import (
    get_or_build_cv_summary,
    _load_all_cards_cached
)
from ..startup import cleanup_orphaned_sessions

router = APIRouter(tags=["personas"])


def _find_card(persona_key: str):
    """Return the persona card whose key matches (case-insensitive), else None."""
    key = (persona_key or "").strip().lower()
    for card in _load_all_cards_cached():
        if str(card.get("key", "")).lower() == key:
            return card
    return None


@router.get("/personas/{persona_key}/toolkit")
def persona_toolkit(persona_key: str):
    """Registry-driven toolkit summary for a persona (ADR-009 W3).

    Lists the toolsets and tools this persona is granted, with one-line
    descriptions + the nsfw flag. Backs the Telegram `/tools` command and any
    UI toolkit view. Generic — works for any persona, not just E.E.V.A.
    """
    card = _find_card(persona_key)
    if card is None:
        raise HTTPException(status_code=404, detail=f"Unknown persona '{persona_key}'")
    # Lazy import: ensure registry is populated (registrations side-effect).
    from ..tools.registry import registry
    from ..tools import registrations  # noqa: F401

    desc = registry.describe_for_persona(card)
    desc["display_name"] = card.get("display_name") or card.get("key")
    return JSONResponse(content=desc)

_last_persona_keys: set = set()


@router.get("/personas")
def list_personas():
    """Return list of available personas with metadata."""
    try:
        cards = _load_all_cards_cached()
        global _last_persona_keys
        current_keys = {c.get("key") for c in cards if c.get("key")}
        if current_keys != _last_persona_keys:
            _last_persona_keys = current_keys
            cleanup_orphaned_sessions()
        personas = []
        for card in cards:
            # Roster filter (2026-07-05): personas with `active: false` are HIDDEN
            # from the UI/summoning roster but intentionally still loaded by
            # _load_all_cards_cached() — so they remain resolvable by key (direct
            # chat, the full-persona eval gate) and, critically, are NOT treated
            # as orphaned by cleanup_orphaned_sessions (which keys off all cards).
            if card.get("active", True) is False:
                continue
            persona = {
                "key": card.get("key"),
                "display_name": card.get("display_name") or card.get("key"),
                "style": card.get("style", ""),
                "rarity": card.get("rarity", "common"),
                "celestial_order": card.get("celestial_order", card.get("rarity", "common")),
                "mcp_access": card.get("mcp_access", []),
                "coordinator_label": card.get("coordinator_label"),
                "image": card.get("image"),
                "avatar": card.get("avatar"),
                "bg": card.get("bg"),
                "voice": card.get("voice"),
            }
            # Include slim nephilim_lore (relationships + realm_domain only)
            nephilim_lore = card.get("nephilim_lore")
            if nephilim_lore:
                persona["nephilim_lore"] = {
                    "relationships": nephilim_lore.get("relationships", {}),
                    "realm_domain": nephilim_lore.get("realm_domain"),
                }
            personas.append(persona)
        return JSONResponse(content=personas)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list personas: {e}")


@router.post("/persona/summary")
def summary(body: SummaryBody):
    """
    Returns the cached or freshly built CV-style summary for a persona.
    { key, hash, updated, summary }
    """
    try:
        data = get_or_build_cv_summary(body.persona)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary error: {e}")
