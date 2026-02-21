# src/coordinator/schemas.py
"""Pydantic models for API request/response schemas."""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ----------------- Chat Schemas -----------------

class ChatTurn(BaseModel):
    """A single turn in a conversation."""
    role: str
    content: str


class ChatBody(BaseModel):
    """Request body for chat endpoint."""
    persona: Optional[str] = None
    history: List[ChatTurn] = Field(default=[], max_length=100)
    message: str = Field(..., max_length=10_000)
    session_id: Optional[str] = None  # Set by handle_session_chat for wallet flow continuity


class GreetBody(BaseModel):
    """Request body for greeting endpoint."""
    persona: Optional[str] = None


class SummaryBody(BaseModel):
    """Request body for persona summary endpoint."""
    persona: Optional[str] = None  # label/key; None resolves to first card


# ----------------- Session Schemas -----------------

class CreateSessionBody(BaseModel):
    """Request body for creating a new session."""
    persona_key: str
    title: str = "New Chat"


class UpdateSessionBody(BaseModel):
    """Request body for updating a session."""
    title: str


class AppendMessageBody(BaseModel):
    """Request body for appending a message to a session."""
    role: str
    content: str
    ts: Optional[str] = None
    latency_ms: Optional[int] = None
    source_type: str = "llm"
    multi_message_id: Optional[str] = None
    multi_message_index: Optional[int] = None


class MessageModel(BaseModel):
    """A message in a session."""
    id: str
    role: str
    content: str
    timestamp: str
    latency_ms: Optional[int] = None
    source_type: str = "llm"


class SessionModel(BaseModel):
    """A chat session."""
    id: str
    persona_key: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0


class SessionWithMessages(BaseModel):
    """A session with its messages."""
    session: SessionModel
    messages: List[MessageModel]


# ----------------- Export/Import Schemas -----------------

class ExportData(BaseModel):
    """Exported session data structure."""
    version: str = "1.0"
    exported_at: str
    app_version: str = "1.0.0"
    persona: Dict[str, Any]
    session: Dict[str, Any]
    messages: List[Dict[str, Any]]


class ImportBody(BaseModel):
    """Request body for importing a session."""
    data: ExportData
    create_new_session: bool = True


class ImportChatBody(BaseModel):
    """Legacy: Import a chat."""
    persona: str
    chat: Dict[str, Any] = Field(..., description="JSON with {title, messages: [{role,content,ts?}]}")


# ----------------- Response Metadata -----------------

class ResponseMetadata(BaseModel):
    """Metadata about the response source."""
    source_type: str = "llm"  # "llm", "brave_mcp", "mongodb_mcp", "multi_mcp"
    tools_used: List[str] = []
    cache_status: Optional[str] = None  # "hit", "miss", None
    data_timestamp: Optional[str] = None
    latency_breakdown: Optional[Dict[str, int]] = None  # {"llm": 3000, "mongodb": 500}
    # PHASE 2: Multi-message response fields
    is_multi_message: bool = False
    message_count: int = 1
    # WALLET: Proposal card injection
    proposal_type: Optional[str] = None  # "trade_proposal", "strategy_proposal", "wallet_deletion"
    proposal: Optional[Dict] = None


# ----------------- NEPHILIM Progression Schemas -----------------

class SetFactionBody(BaseModel):
    """Request body for setting seeker faction."""
    faction_primary: str
    faction_secondary: Optional[str] = None


class AwardResonanceBody(BaseModel):
    """Request body for awarding resonance."""
    amount: int
    reason: str
    persona_key: Optional[str] = None
    session_id: Optional[str] = None


class SeekerProfileResponse(BaseModel):
    """Response containing seeker profile data."""
    user_id: str
    rank_name: str
    total_resonance: int
    faction_primary: Optional[str] = None
    faction_secondary: Optional[str] = None
    rank_achieved_at: Optional[str] = None
    created_at: str
    updated_at: str


class RankProgressResponse(BaseModel):
    """Response containing rank progress info."""
    current_rank: str
    current_resonance: int
    next_rank: Optional[str] = None
    resonance_needed: int
    progress_percent: int


class PersonaAffinityResponse(BaseModel):
    """Response containing persona affinity data."""
    user_id: str
    persona_key: str
    messages_count: int
    affinity_level: int
    first_conversation: Optional[str] = None
    last_conversation: Optional[str] = None


class UnlockedLoreResponse(BaseModel):
    """Response containing unlocked lore fragment info."""
    id: int
    user_id: str
    persona_key: str
    fragment_id: str
    unlocked_at: str


class LoreFragmentContent(BaseModel):
    """Full lore fragment with content."""
    fragment_id: str
    fragment_title: str
    fragment: str
    messages_required: int
    rarity: str
    unlocked: bool
    unlocked_at: Optional[str] = None


class SeekerSummaryResponse(BaseModel):
    """Comprehensive seeker summary response."""
    exists: bool
    user_id: str
    rank: Optional[str] = None
    total_resonance: Optional[int] = None
    faction_primary: Optional[str] = None
    faction_secondary: Optional[str] = None
    rank_progress: Optional[RankProgressResponse] = None
    persona_affinities: List[PersonaAffinityResponse] = []
    unlocked_lore_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
