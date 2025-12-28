# src/coordinator/models/__init__.py
# Pydantic models for type-safe data structures

from .persona_schema import (
    Rarity,
    VoiceProfile,
    EmotionalProfile,
    BehaviorProfile,
    BoundaryConfig,
    DialoguePreferences,
    ExpertiseConfig,
    EscalationPolicy,
    SamplingPreset,
    PsychologicalProfile,
    ExampleDialogue,
    PersonaCard,
    validate_persona_file,
    load_persona_card,
)

from .sampling_presets import (
    SamplingConfig,
    PRESETS,
    get_preset,
    get_preset_or_default,
    build_sampling_config,
    get_sampling_for_persona,
    list_presets,
)

from .mcp_models import (
    SearchResult,
    MCPError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPResponseError,
)

__all__ = [
    # Persona schema
    "Rarity",
    "VoiceProfile",
    "EmotionalProfile",
    "BehaviorProfile",
    "BoundaryConfig",
    "DialoguePreferences",
    "ExpertiseConfig",
    "EscalationPolicy",
    "SamplingPreset",
    "PsychologicalProfile",
    "ExampleDialogue",
    "PersonaCard",
    "validate_persona_file",
    "load_persona_card",
    # Sampling presets
    "SamplingConfig",
    "PRESETS",
    "get_preset",
    "get_preset_or_default",
    "build_sampling_config",
    "get_sampling_for_persona",
    "list_presets",
    # MCP models
    "SearchResult",
    "MCPError",
    "MCPConnectionError",
    "MCPTimeoutError",
    "MCPResponseError",
]
