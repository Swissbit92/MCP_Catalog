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
    history: List[ChatTurn] = []
    message: str


class GreetBody(BaseModel):
    """Request body for greeting endpoint."""
    persona: Optional[str] = None


class SummaryBody(BaseModel):
    """Request body for persona summary endpoint."""
    persona: Optional[str] = None  # label/key; None resolves to first card


# ----------------- Legacy Chat Schemas (Deprecated) -----------------

class CreateChatBody(BaseModel):
    """Legacy: Create a new chat."""
    persona: str
    title: str = "New Chat"


class RenameChatBody(BaseModel):
    """Legacy: Rename a chat."""
    title: str


class SelectChatBody(BaseModel):
    """Legacy: Select a chat."""
    persona: str


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
