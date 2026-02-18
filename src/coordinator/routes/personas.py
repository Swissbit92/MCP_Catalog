# src/coordinator/routes/personas.py
"""Persona-related API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..schemas import SummaryBody
from ..persona_memory import (
    get_persona_card,
    get_or_build_cv_summary,
    _load_all_cards_cached
)
from ..startup import cleanup_orphaned_sessions

router = APIRouter(tags=["personas"])

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
            personas.append({
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
            })
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
