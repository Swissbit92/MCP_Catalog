# src/coordinator/models/persona_schema.py
"""
Pydantic models for persona card validation.

This module provides type-safe schemas for persona JSON files, ensuring:
- Schema validation on load (catch errors early)
- IDE autocomplete for persona fields
- Self-documenting persona structure
- Clear validation error messages

Phase 1 of Persona Quality Enhancement Roadmap.
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


class Rarity(str, Enum):
    """Persona rarity levels for gacha system and feature gating."""
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class VoiceProfile(BaseModel):
    """Voice and mannerisms configuration for persona."""
    greeting: str = Field(default="", description="Opening message style hint")
    signoff: str = Field(default="", description="Closing message style hint")
    tics: List[str] = Field(default_factory=list, description="Speech quirks and mannerisms")


class EmotionalProfile(BaseModel):
    """Emotional baseline and tendencies for consistent persona tone."""
    baseline: str = Field(default="", description="Default emotional state")
    strengths: List[str] = Field(default_factory=list, description="Emotional strengths")
    pitfalls: List[str] = Field(default_factory=list, description="Emotional vulnerabilities")
    sliders: Dict[str, float] = Field(
        default_factory=dict,
        description="Numeric knobs for tone (warmth, assertiveness, etc.)"
    )

    @field_validator('sliders')
    @classmethod
    def validate_sliders(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Ensure slider values are between 0.0 and 1.0."""
        for key, val in v.items():
            if not isinstance(val, (int, float)):
                raise ValueError(f"Slider '{key}' must be a number, got {type(val).__name__}")
            if not 0.0 <= float(val) <= 1.0:
                raise ValueError(f"Slider '{key}' must be between 0.0 and 1.0, got {val}")
        return {k: float(v) for k, v in v.items()}


class BehaviorProfile(BaseModel):
    """Behavioral traits and interaction style."""
    traits: List[str] = Field(default_factory=list, description="Core personality traits")
    pace: str = Field(default="moderate", description="Response pace: terse|moderate|elaborate")
    formality: str = Field(default="medium", description="Formality level: casual|medium|formal")
    humor: str = Field(default="", description="Humor style description")
    emoji_policy: str = Field(default="sparingly", description="Emoji usage guidelines")
    small_talk: str = Field(default="", description="Small talk behavior")
    clarifying_questions: str = Field(default="", description="When to ask for clarification")


class BoundaryConfig(BaseModel):
    """Hard guardrails and content boundaries."""
    ethics: List[str] = Field(default_factory=list, description="Ethical boundaries")
    content: List[str] = Field(default_factory=list, description="Content restrictions")
    personal: List[str] = Field(default_factory=list, description="Personal information boundaries")


class DialoguePreferences(BaseModel):
    """Reply structure and formatting preferences."""
    reply_shape: str = Field(default="", description="Response structure pattern")
    reasoning_visibility: str = Field(default="medium", description="How much reasoning to show: low|medium|high")
    citations_style: str = Field(default="inline when used", description="Citation formatting style")


class ExpertiseConfig(BaseModel):
    """Knowledge domains and topic routing."""
    strong: List[str] = Field(default_factory=list, description="Expert-level topics")
    familiar: List[str] = Field(default_factory=list, description="Working knowledge topics")
    avoid: List[str] = Field(default_factory=list, description="Topics to decline or redirect")


class EscalationPolicy(BaseModel):
    """When to ask, decline, or use tools."""
    when_to_ask_user: List[str] = Field(default_factory=list, description="Triggers for clarification")
    when_to_decline: List[str] = Field(default_factory=list, description="Topics/requests to decline")
    tool_intent: List[str] = Field(default_factory=list, description="Tool usage guidelines")


class SamplingPreset(BaseModel):
    """Per-persona LLM sampling configuration.

    Allows personas to have different creativity/precision settings.
    """
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0-2.0)"
    )
    min_p: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Min-P sampling threshold (optional, requires Ollama 0.1.32+)"
    )
    repetition_penalty: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=2.0,
        description="Repetition penalty (1.0-2.0)"
    )
    top_k: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Top-K sampling (0-100)"
    )
    top_p: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling threshold (0.0-1.0)"
    )
    preset: Optional[str] = Field(
        default=None,
        description="Named preset: creative|balanced|precise|chaotic"
    )


class PsychologicalProfile(BaseModel):
    """Deep psychological characterization for realistic persona behavior.

    This adds psychological depth to personas, enabling:
    - Consistent emotional reactions
    - Realistic character contradictions
    - Character growth tracking over time

    Phase 1.4 of Persona Quality Roadmap.
    """
    core_wound: str = Field(
        default="",
        description="Fundamental emotional vulnerability or trauma"
    )
    coping_mechanism: str = Field(
        default="",
        description="How the persona handles stress or discomfort"
    )
    defense_style: str = Field(
        default="",
        description="Psychological defense mechanisms (intellectualization, humor, etc.)"
    )
    growth_edge: str = Field(
        default="",
        description="Area where the persona is learning/growing"
    )
    contradiction_pairs: List[str] = Field(
        default_factory=list,
        min_length=0,
        max_length=10,
        description="Pairs of contradictory traits that create depth (e.g., 'Brilliant | Self-doubting')"
    )


class ExampleDialogue(BaseModel):
    """Example dialogue to teach LLM correct persona voice.

    More effective than abstract descriptions for voice consistency.
    Phase 1.5 of Persona Quality Roadmap.
    """
    user: str = Field(..., min_length=1, description="Example user message")
    response: str = Field(..., min_length=1, description="Example persona response")
    context: Optional[str] = Field(
        default=None,
        description="Explanation of what this example demonstrates"
    )


class PersonaCard(BaseModel):
    """Complete persona schema with validation.

    This is the main model for validating persona JSON files.
    All fields are validated on load to catch errors early.
    """

    # Required fields
    key: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Unique persona identifier"
    )

    # Optional with defaults
    rarity: Rarity = Field(
        default=Rarity.COMMON,
        description="Persona rarity for gacha system"
    )
    display_name: str = Field(
        default="",
        description="Display name (format: 'Name - Tagline')"
    )
    style: str = Field(
        default="helpful, concise",
        description="Tone hints for system prompt"
    )
    coordinator_label: Optional[str] = Field(
        default=None,
        description="Backend selection dropdown label"
    )

    # Media assets (all optional with fallbacks)
    image: str = Field(default="", description="Card/Bio image path")
    avatar: str = Field(default="", description="Chat avatar path")
    logo: str = Field(default="", description="Header/bio logo path")
    bg: str = Field(default="", description="Chat background path")
    emoji: str = Field(default="", max_length=4, description="Fallback avatar emoji")

    # Permissions
    allowed_mcp: List[str] = Field(
        default_factory=list,
        description="Allowed MCP servers (chat, graphrag, brave_search, etc.)"
    )

    # Core personality
    lore: List[str] = Field(
        default_factory=list,
        min_length=0,
        max_length=100,
        description="Backstory, values, worldview (10-40 short lines)"
    )
    voice: VoiceProfile = Field(
        default_factory=VoiceProfile,
        description="Voice and mannerisms"
    )
    do: List[str] = Field(
        default_factory=list,
        description="Positive habits and behaviors"
    )
    dont: List[str] = Field(
        default_factory=list,
        description="Boundaries and anti-patterns"
    )

    # Behavior configuration
    behavior: BehaviorProfile = Field(
        default_factory=BehaviorProfile,
        description="Behavioral traits and interaction style"
    )
    emotional_profile: EmotionalProfile = Field(
        default_factory=EmotionalProfile,
        description="Emotional baseline and tendencies"
    )
    boundaries: BoundaryConfig = Field(
        default_factory=BoundaryConfig,
        description="Hard guardrails"
    )
    dialogue_prefs: DialoguePreferences = Field(
        default_factory=DialoguePreferences,
        description="Reply structure preferences"
    )
    expertise: ExpertiseConfig = Field(
        default_factory=ExpertiseConfig,
        description="Knowledge domains"
    )

    # Signature elements
    signature_moves: List[str] = Field(
        default_factory=list,
        description="Recognizable interaction patterns"
    )
    example_phrases: List[str] = Field(
        default_factory=list,
        description="Sample phrases to anchor tone"
    )
    escalation_policy: EscalationPolicy = Field(
        default_factory=EscalationPolicy,
        description="When to ask, decline, or use tools"
    )

    # NEW: Phase 1 additions
    model_preferences: SamplingPreset = Field(
        default_factory=SamplingPreset,
        description="Per-persona LLM sampling configuration"
    )
    psychological_profile: Optional[PsychologicalProfile] = Field(
        default=None,
        description="Deep psychological characterization (Phase 1.4)"
    )
    example_dialogues: List[ExampleDialogue] = Field(
        default_factory=list,
        max_length=20,
        description="Example dialogues to teach voice (Phase 1.5)"
    )

    class Config:
        """Pydantic model configuration."""
        use_enum_values = True
        extra = "allow"  # Allow extra fields for forward compatibility

    @field_validator('lore')
    @classmethod
    def validate_lore_quality(cls, v: List[str]) -> List[str]:
        """Warn about low-quality lore entries (but don't fail)."""
        short_entries = [entry for entry in v if len(entry.strip()) < 10]
        if short_entries:
            logger.warning(
                f"Lore contains {len(short_entries)} entries shorter than 10 characters. "
                "Consider expanding for better persona depth."
            )
        return v

    @field_validator('display_name')
    @classmethod
    def validate_display_name(cls, v: str, info) -> str:
        """Auto-generate display_name from key if not provided."""
        if not v:
            # Will use key if available from values
            return ""
        return v

    @model_validator(mode='after')
    def set_defaults_from_key(self) -> 'PersonaCard':
        """Set default values derived from key."""
        if not self.display_name:
            self.display_name = f"{self.key} - Assistant"
        return self


def validate_persona_file(path: Union[str, Path]) -> tuple[bool, Optional[PersonaCard], Optional[str]]:
    """Validate a persona JSON file against the schema.

    Args:
        path: Path to persona JSON file

    Returns:
        Tuple of (is_valid, persona_card_or_none, error_message_or_none)
    """
    path = Path(path)

    if not path.exists():
        return (False, None, f"File not found: {path}")

    if not path.suffix.lower() == '.json':
        return (False, None, f"Not a JSON file: {path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return (False, None, f"Invalid JSON: {e}")

    try:
        card = PersonaCard(**data)
        logger.debug(f"Successfully validated persona: {card.key}")
        return (True, card, None)
    except Exception as e:
        error_msg = str(e)
        # Make error message more user-friendly
        if "validation error" in error_msg.lower():
            return (False, None, f"Validation error in {path.name}: {error_msg}")
        return (False, None, f"Failed to parse {path.name}: {error_msg}")


def load_persona_card(path: Union[str, Path]) -> PersonaCard:
    """Load and validate a persona JSON file.

    Args:
        path: Path to persona JSON file

    Returns:
        Validated PersonaCard instance

    Raises:
        ValueError: If file is invalid or fails validation
        FileNotFoundError: If file doesn't exist
    """
    is_valid, card, error = validate_persona_file(path)

    if not is_valid:
        raise ValueError(error)

    return card


def load_persona_card_lenient(path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """Load a persona file with lenient validation (warning-only mode).

    For backward compatibility during migration. Validates but returns
    raw dict even if validation fails (with warning).

    Args:
        path: Path to persona JSON file

    Returns:
        Raw dict of persona data, or None if file can't be read
    """
    path = Path(path)

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, IOError) as e:
        logger.error(f"Failed to load persona file {path}: {e}")
        return None

    # Validate in lenient mode (log warnings, don't fail)
    is_valid, card, error = validate_persona_file(path)

    if not is_valid:
        logger.warning(f"Persona validation warning for {path.name}: {error}")
        logger.warning("Continuing with raw data (backward compatibility mode)")
    else:
        logger.debug(f"Persona {path.name} passed validation")

    # Return raw dict for backward compatibility
    return data
