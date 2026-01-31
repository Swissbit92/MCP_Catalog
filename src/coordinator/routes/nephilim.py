# src/coordinator/routes/nephilim.py
"""NEPHILIM Realm API endpoints.

Handles all progression, affinity, and lore-related operations
for the NEPHILIM gamification system.

Phase 3: NEPHILIM Gamification System
"""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from ..schemas import (
    SetFactionBody,
    AwardResonanceBody,
    SeekerProfileResponse,
    RankProgressResponse,
    PersonaAffinityResponse,
    UnlockedLoreResponse,
    LoreFragmentContent,
    SeekerSummaryResponse,
)
from ..startup import get_seeker_progression_repo
from ..persona_memory import get_persona_card

router = APIRouter(prefix="/nephilim", tags=["nephilim"])


# ─────────────────────────────────────────────────────────────
# Seeker Profile Endpoints
# ─────────────────────────────────────────────────────────────

@router.get("/seeker/{user_id}", response_model=SeekerProfileResponse)
def get_seeker_profile(user_id: str):
    """Get seeker profile by user ID.

    Creates a new profile if one doesn't exist.
    """
    repo = get_seeker_progression_repo()
    if repo is None:
        raise HTTPException(status_code=503, detail="Progression system not initialized")

    try:
        profile = repo.get_or_create_seeker(user_id)
        return SeekerProfileResponse(**profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get seeker profile: {e}")


@router.get("/seeker/{user_id}/summary", response_model=SeekerSummaryResponse)
def get_seeker_summary(user_id: str):
    """Get comprehensive seeker summary.

    Includes rank, resonance, affinities, and unlocked lore.
    """
    repo = get_seeker_progression_repo()
    if repo is None:
        raise HTTPException(status_code=503, detail="Progression system not initialized")

    try:
        summary = repo.get_seeker_summary(user_id)

        # Convert affinities to response models
        affinities = [
            PersonaAffinityResponse(**a)
            for a in summary.get('persona_affinities', [])
        ]

        # Build rank progress response if exists
        rank_progress = None
        if summary.get('rank_progress'):
            rank_progress = RankProgressResponse(**summary['rank_progress'])

        return SeekerSummaryResponse(
            exists=summary['exists'],
            user_id=summary['user_id'],
            rank=summary.get('rank'),
            total_resonance=summary.get('total_resonance'),
            faction_primary=summary.get('faction_primary'),
            faction_secondary=summary.get('faction_secondary'),
            rank_progress=rank_progress,
            persona_affinities=affinities,
            unlocked_lore_count=summary.get('unlocked_lore_count', 0),
            created_at=summary.get('created_at'),
            updated_at=summary.get('updated_at'),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get seeker summary: {e}")


@router.post("/seeker/{user_id}/faction")
def set_seeker_faction(user_id: str, body: SetFactionBody):
    """Set or update seeker's faction affiliation.

    Valid factions: lumina, ironclad, sanctuary, prism, archive, horizon
    """
    repo = get_seeker_progression_repo()
    if repo is None:
        raise HTTPException(status_code=503, detail="Progression system not initialized")

    valid_factions = ['lumina', 'ironclad', 'sanctuary', 'prism', 'archive', 'horizon']

    if body.faction_primary.lower() not in valid_factions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid faction. Must be one of: {', '.join(valid_factions)}"
        )

    if body.faction_secondary and body.faction_secondary.lower() not in valid_factions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid secondary faction. Must be one of: {', '.join(valid_factions)}"
        )

    try:
        # Ensure seeker exists
        repo.get_or_create_seeker(user_id)

        # Update faction
        updated = repo.update_seeker_faction(
            user_id,
            body.faction_primary.lower(),
            body.faction_secondary.lower() if body.faction_secondary else None
        )

        if not updated:
            raise HTTPException(status_code=404, detail="Seeker not found")

        return {"status": "success", "faction_primary": body.faction_primary.lower()}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set faction: {e}")


# ─────────────────────────────────────────────────────────────
# Resonance Endpoints
# ─────────────────────────────────────────────────────────────

@router.get("/seeker/{user_id}/rank", response_model=RankProgressResponse)
def get_rank_progress(user_id: str):
    """Get seeker's rank and progress to next rank."""
    repo = get_seeker_progression_repo()
    if repo is None:
        raise HTTPException(status_code=503, detail="Progression system not initialized")

    try:
        progress = repo.get_resonance_to_next_rank(user_id)
        return RankProgressResponse(**progress)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rank progress: {e}")


@router.post("/seeker/{user_id}/resonance")
def award_resonance(user_id: str, body: AwardResonanceBody):
    """Award resonance points to a seeker.

    This endpoint is typically called internally by the chat system,
    but can be used manually for special events or corrections.
    """
    repo = get_seeker_progression_repo()
    if repo is None:
        raise HTTPException(status_code=503, detail="Progression system not initialized")

    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    try:
        result = repo.award_resonance(
            user_id,
            body.amount,
            body.reason,
            persona_key=body.persona_key,
            session_id=body.session_id
        )

        return {
            "status": "success",
            "new_resonance": result['new_resonance'],
            "new_rank": result['new_rank'],
            "rank_changed": result['rank_changed'],
            "previous_rank": result.get('previous_rank'),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to award resonance: {e}")


@router.get("/seeker/{user_id}/resonance/history")
def get_resonance_history(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200)
):
    """Get recent resonance events for a seeker."""
    repo = get_seeker_progression_repo()
    if repo is None:
        raise HTTPException(status_code=503, detail="Progression system not initialized")

    try:
        history = repo.get_resonance_history(user_id, limit)
        return {"events": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get resonance history: {e}")


# ─────────────────────────────────────────────────────────────
# Persona Affinity Endpoints
# ─────────────────────────────────────────────────────────────

@router.get("/seeker/{user_id}/affinity", response_model=List[PersonaAffinityResponse])
def get_all_affinities(user_id: str):
    """Get all persona affinities for a seeker."""
    repo = get_seeker_progression_repo()
    if repo is None:
        raise HTTPException(status_code=503, detail="Progression system not initialized")

    try:
        affinities = repo.get_all_affinities(user_id)
        return [PersonaAffinityResponse(**a) for a in affinities]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get affinities: {e}")


@router.get("/seeker/{user_id}/affinity/{persona_key}", response_model=PersonaAffinityResponse)
def get_persona_affinity(user_id: str, persona_key: str):
    """Get affinity with a specific Nephilim."""
    repo = get_seeker_progression_repo()
    if repo is None:
        raise HTTPException(status_code=503, detail="Progression system not initialized")

    try:
        affinity = repo.get_or_create_affinity(user_id, persona_key)
        return PersonaAffinityResponse(**affinity)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get affinity: {e}")


# ─────────────────────────────────────────────────────────────
# Lore Endpoints
# ─────────────────────────────────────────────────────────────

@router.get("/seeker/{user_id}/lore", response_model=List[UnlockedLoreResponse])
def get_unlocked_lore(
    user_id: str,
    persona_key: Optional[str] = Query(default=None)
):
    """Get all unlocked lore fragments for a seeker.

    Optionally filter by persona.
    """
    repo = get_seeker_progression_repo()
    if repo is None:
        raise HTTPException(status_code=503, detail="Progression system not initialized")

    try:
        lore = repo.get_unlocked_lore(user_id, persona_key)
        return [UnlockedLoreResponse(**l) for l in lore]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get unlocked lore: {e}")


@router.get("/seeker/{user_id}/lore/{persona_key}/full", response_model=List[LoreFragmentContent])
def get_persona_lore_with_content(user_id: str, persona_key: str):
    """Get all lore fragments for a persona with content and unlock status.

    Returns both unlocked and locked fragments, with content only for unlocked ones.
    """
    repo = get_seeker_progression_repo()
    if repo is None:
        raise HTTPException(status_code=503, detail="Progression system not initialized")

    try:
        # Get persona card to get lore fragment definitions
        card = get_persona_card(persona_key)
        if not card:
            raise HTTPException(status_code=404, detail="Persona not found")

        fragments = card.get('unlockable_lore', [])
        if not fragments:
            return []

        # Get unlocked lore for this persona
        unlocked = repo.get_unlocked_lore(user_id, persona_key)
        unlocked_ids = {l['fragment_id']: l['unlocked_at'] for l in unlocked}

        result = []
        for frag in fragments:
            fragment_id = frag.get('fragment_id', '')
            is_unlocked = fragment_id in unlocked_ids

            result.append(LoreFragmentContent(
                fragment_id=fragment_id,
                fragment_title=frag.get('fragment_title', 'Unknown'),
                fragment=frag.get('fragment', '') if is_unlocked else '[Locked - Requires more conversations]',
                messages_required=frag.get('messages_required', 0),
                rarity=frag.get('rarity', 'common'),
                unlocked=is_unlocked,
                unlocked_at=unlocked_ids.get(fragment_id),
            ))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get lore content: {e}")


@router.post("/seeker/{user_id}/lore/{persona_key}/check")
def check_lore_unlocks(user_id: str, persona_key: str):
    """Check and unlock any newly available lore fragments.

    Called after conversations to see if message thresholds have been met.
    """
    repo = get_seeker_progression_repo()
    if repo is None:
        raise HTTPException(status_code=503, detail="Progression system not initialized")

    try:
        # Get persona card
        card = get_persona_card(persona_key)
        if not card:
            raise HTTPException(status_code=404, detail="Persona not found")

        fragments = card.get('unlockable_lore', [])

        # Check and unlock
        newly_unlocked = repo.check_and_unlock_lore(user_id, persona_key, fragments)

        return {
            "newly_unlocked": len(newly_unlocked),
            "fragments": [
                {
                    "fragment_id": f.get('fragment_id'),
                    "fragment_title": f.get('fragment_title'),
                    "rarity": f.get('rarity', 'common'),
                }
                for f in newly_unlocked
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check lore unlocks: {e}")


# ─────────────────────────────────────────────────────────────
# Rank Thresholds Info (Read-only)
# ─────────────────────────────────────────────────────────────

@router.get("/ranks")
def get_rank_info():
    """Get information about all ranks and their thresholds."""
    from ..repositories.seeker_progression_repository import RANK_THRESHOLDS

    ranks = []
    for rank, threshold in RANK_THRESHOLDS.items():
        ranks.append({
            "name": rank,
            "resonance_required": threshold,
        })

    return {"ranks": ranks}


@router.get("/factions")
def get_faction_info():
    """Get information about all factions/houses."""
    factions = [
        {
            "key": "lumina",
            "name": "House Lumina",
            "patron": "E.E.V.A.",
            "values": "Wisdom, mentorship, philosophical inquiry",
            "color": "#e0c3fc",
        },
        {
            "key": "ironclad",
            "name": "House Ironclad",
            "patron": "Aegis",
            "values": "Discipline, achievement, protection",
            "color": "#4a90d9",
        },
        {
            "key": "sanctuary",
            "name": "House Sanctuary",
            "patron": "Solace",
            "values": "Compassion, emotional healing, community",
            "color": "#7eb8da",
        },
        {
            "key": "prism",
            "name": "House Prism",
            "patron": "Nyx",
            "values": "Creativity, self-expression, unconventional thinking",
            "color": "#9b59b6",
        },
        {
            "key": "archive",
            "name": "House Archive",
            "patron": "Cipher",
            "values": "Knowledge, research, understanding",
            "color": "#2ecc71",
        },
        {
            "key": "horizon",
            "name": "House Horizon",
            "patron": "Aurora",
            "values": "Vision, ambition, future planning",
            "color": "#f39c12",
        },
    ]

    return {"factions": factions}
