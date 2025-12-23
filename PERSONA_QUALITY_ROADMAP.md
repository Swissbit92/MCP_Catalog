# Persona Quality & Architecture Enhancement Roadmap

**Document Version:** 1.0
**Created:** December 2025
**Status:** Planning Phase
**Estimated Total Effort:** 80-100 hours over 4-6 weeks

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Assessment](#current-state-assessment)
3. [Strategic Goals](#strategic-goals)
4. [Pydantic Integration Analysis](#pydantic-integration-analysis)
5. [Implementation Roadmap](#implementation-roadmap)
   - [Phase 1: Foundation & Type Safety](#phase-1-foundation--type-safety-20-25-hours)
   - [Phase 2: Prompt Engineering & Persona Depth](#phase-2-prompt-engineering--persona-depth-25-30-hours)
   - [Phase 3: Context & Memory Optimization](#phase-3-context--memory-optimization-20-25-hours)
   - [Phase 4: Advanced Features](#phase-4-advanced-features-15-20-hours)
6. [Success Metrics & KPIs](#success-metrics--kpis)
7. [Risk Mitigation](#risk-mitigation)
8. [Testing Strategy](#testing-strategy)
9. [Rollback Plan](#rollback-plan)

---

## Executive Summary

### Context

Following analysis of industry best practices from the local AI companion community (SillyTavern, KoboldCpp ecosystem), we've identified **15-20% quality improvements** achievable through targeted enhancements to our persona system, while maintaining our superior architecture.

### Key Findings

**Current State:**
- ✅ **Architecture**: Production-grade (9.5/10) - Superior to industry hobbyist tools
- ⚠️ **Prompt Engineering**: Good but improvable (7.0/10 → target 9.0/10)
- ⚠️ **Type Safety**: Partial Pydantic usage (6.5/10 → target 9.5/10)
- ⚠️ **Sampling Quality**: Basic temperature only (6.0/10 → target 9.0/10)
- ⚠️ **Memory Systems**: Functional but limited (7.5/10 → target 9.0/10)

**Opportunity:**
- **20-30 hours** of focused work → **25-30% quality improvement** in persona consistency, realism, and user engagement
- Minimal architectural changes (mostly additive enhancements)
- High ROI on user satisfaction and persona immersion

### Strategic Recommendation

**PROCEED** with phased implementation:
1. Start with **Pydantic schema validation** (quick wins, prevents regressions)
2. Layer in **advanced sampling** (immediate quality boost)
3. Deepen **persona psychological profiles** (gradual persona updates)
4. Optimize **context management** (unlocks long-term memory)

---

## Current State Assessment

### What We're Doing Well

| Area | Current Score | Evidence |
|------|--------------|----------|
| **Backend Architecture** | 9.5/10 | FastAPI, repository pattern, SQLite with migrations |
| **Frontend Quality** | 9.0/10 | React 19, TypeScript, Tailwind, Framer Motion |
| **MCP Integration** | 9.0/10 | Brave search, MongoDB (in progress), citation validation |
| **Deployment** | 9.0/10 | Docker-ready, automated setup, one-command start |
| **Security** | 8.5/10 | Minimal vulnerabilities, local-first, no external API leaks |

### Critical Gaps Identified

| Gap | Current Score | Target Score | Impact if Fixed |
|-----|--------------|--------------|-----------------|
| **Pydantic Schema Validation** | 4.0/10 | 9.5/10 | 🔥 Prevents persona corruption, better errors |
| **Advanced Sampling** | 3.0/10 | 9.0/10 | 🔥 30% quality improvement in responses |
| **Psychological Depth** | 7.0/10 | 9.5/10 | 🔥 Massively improves character consistency |
| **Context Management** | 6.5/10 | 9.0/10 | 🌟 Better long-term memory, fewer repetitions |
| **Example Dialogues** | 5.0/10 | 9.0/10 | 🌟 Teaches LLM correct persona voice |
| **Keyword Memory** | 0.0/10 | 8.0/10 | 🌟 Selective context injection |

**Legend:** 🔥 High Impact | 🌟 Medium Impact | ⚡ Low Impact

---

## Strategic Goals

### Primary Objectives

1. **Improve Persona Consistency** by 30-40%
   - Reduce third-person violations by 60%
   - Increase emotional continuity across conversations
   - Strengthen character voice distinctiveness

2. **Enhance Type Safety** to prevent runtime errors
   - Validate all persona JSON on load
   - Catch schema errors before deployment
   - Provide developer-friendly error messages

3. **Optimize Response Quality** through advanced sampling
   - Reduce "AI-sounding" language by 40%
   - Improve creative variety while maintaining coherence
   - Eliminate repetitive phrasings

4. **Extend Conversation Memory** for long-term engagement
   - Increase effective context from ~6 messages to 12-15
   - Implement selective memory injection
   - Support multi-session persona growth tracking

### Secondary Objectives

5. Support per-persona model selection (e.g., `mythomax` for NSFW, `llama3.1` for research)
6. Add TTS integration for voice output (optional enhancement)
7. Implement automatic conversation summarization (every 30-50 messages)
8. Create reusable preset system (creative, balanced, precise sampling)

---

## Pydantic Integration Analysis

### Current Usage (Partial Implementation)

**✅ Currently Using Pydantic:**
```python
# src/coordinator/server.py - API Models
ChatTurn, ChatBody, GreetBody, SummaryBody, CreateChatBody,
RenameChatBody, AppendMessageBody, SelectChatBody, CreateSessionBody,
UpdateSessionBody, MessageModel, SessionModel, SessionWithMessages,
ExportData, ImportBody, ImportChatBody, ResponseMetadata
```

**❌ NOT Using Pydantic:**
1. **Persona JSON Schema** - Currently loaded as raw `Dict` (persona_memory.py:202)
2. **Configuration Management** - Using raw `os.getenv()` (config.py)
3. **Tool Definitions** - Dataclass for `ToolCall`, no validation
4. **MongoDB/Brave Responses** - Raw dicts, no type safety

### Why Pydantic Matters

**Problem:** Raw dictionary loading allows invalid persona JSON to crash the app at runtime.

**Example Failure Scenario:**
```json
// Bad persona.json
{
  "key": "TestPersona",
  "lore": "should be array, but is string",  // ❌ Type mismatch
  "rarity": "ultra-rare",                     // ❌ Invalid enum value
  "model_preferences": {
    "temperature": "high"                      // ❌ Should be float
  }
}
```

**Current Behavior:** App crashes with cryptic `TypeError` during prompt building.

**With Pydantic:** Clear validation error on load:
```
ValidationError:
- lore: expected list, got str
- rarity: must be one of ['common', 'rare', 'epic', 'legendary']
- model_preferences.temperature: expected float, got str
```

### Recommended Pydantic Enhancements

#### 1. Persona Schema Validation (HIGH PRIORITY)

**File:** `src/coordinator/models/persona_schema.py` (NEW)

```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Literal
from enum import Enum

class Rarity(str, Enum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"

class VoiceProfile(BaseModel):
    greeting: str
    signoff: str
    tics: List[str] = Field(default_factory=list)

class EmotionalProfile(BaseModel):
    baseline: str
    strengths: List[str]
    pitfalls: List[str]
    sliders: Dict[str, float] = Field(default_factory=dict)

    @validator('sliders')
    def validate_sliders(cls, v):
        for key, val in v.items():
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"Slider '{key}' must be between 0.0 and 1.0")
        return v

class PsychologicalProfile(BaseModel):
    """NEW: Adds psychological depth to personas."""
    core_wound: str
    coping_mechanism: str
    defense_style: str
    growth_edge: str
    contradiction_pairs: List[str] = Field(min_items=2, max_items=10)

class ExampleDialogue(BaseModel):
    """NEW: Teaches LLM correct persona voice."""
    user: str
    response: str
    context: Optional[str] = None

class SamplingPreset(BaseModel):
    """NEW: Per-persona sampling configuration."""
    temperature: float = Field(ge=0.0, le=2.0, default=0.7)
    min_p: Optional[float] = Field(ge=0.0, le=1.0, default=0.05)
    repetition_penalty: float = Field(ge=1.0, le=2.0, default=1.08)
    top_k: int = Field(ge=0, le=100, default=40)
    top_p: float = Field(ge=0.0, le=1.0, default=0.9)

class PersonaCard(BaseModel):
    """Complete persona schema with validation."""
    key: str = Field(min_length=1, max_length=50)
    rarity: Rarity
    display_name: str
    style: str
    coordinator_label: Optional[str] = None

    # Media
    image: str
    avatar: str
    logo: str
    bg: str
    emoji: str = Field(max_length=2)

    # Permissions
    allowed_mcp: List[str] = Field(default_factory=list)

    # Core personality
    lore: List[str] = Field(min_items=5, max_items=100)
    voice: VoiceProfile
    do: List[str]
    dont: List[str]

    behavior: Dict[str, Any]
    emotional_profile: EmotionalProfile
    boundaries: Dict[str, List[str]]
    dialogue_prefs: Dict[str, str]
    expertise: Dict[str, List[str]]

    # NEW fields
    psychological_profile: Optional[PsychologicalProfile] = None
    example_dialogues: List[ExampleDialogue] = Field(default_factory=list, max_items=20)
    model_preferences: Optional[SamplingPreset] = None

    # Existing optional fields
    signature_moves: List[str] = Field(default_factory=list)
    example_phrases: List[str] = Field(default_factory=list)
    escalation_policy: Dict[str, List[str]] = Field(default_factory=dict)

    class Config:
        use_enum_values = True

    @validator('lore')
    def validate_lore_quality(cls, v):
        """Ensure lore entries are substantive."""
        if any(len(entry.strip()) < 10 for entry in v):
            raise ValueError("Lore entries must be at least 10 characters")
        return v
```

**Benefits:**
- ✅ Catches schema errors before app starts
- ✅ Autocomplete in IDEs for persona fields
- ✅ Self-documenting persona structure
- ✅ Prevents typos in field names
- ✅ Validates rarity, temperature ranges, etc.

#### 2. Settings Management with Pydantic (MEDIUM PRIORITY)

**File:** `src/coordinator/config.py` (REFACTOR)

**Current:**
```python
def get_persona_temperature() -> float:
    return float(os.getenv("PERSONA_TEMPERATURE", "0.1"))
```

**Improved:**
```python
from pydantic import BaseSettings, Field

class CoordinatorSettings(BaseSettings):
    """Centralized configuration with validation."""

    # Ollama
    ollama_base: str = Field(default="http://127.0.0.1:11434", env="OLLAMA_BASE")
    persona_model: str = Field(default="llama3.1:latest", env="PERSONA_MODEL")
    persona_temperature: float = Field(default=0.1, ge=0.0, le=2.0, env="PERSONA_TEMPERATURE")

    # Brave MCP
    brave_enabled: bool = Field(default=False, env="BRAVE_ENABLED")
    brave_api_key: Optional[str] = Field(default=None, env="BRAVE_API_KEY")
    brave_max_results: int = Field(default=5, ge=1, le=20, env="BRAVE_MAX_RESULTS")

    # MongoDB MCP
    mongodb_enabled: bool = Field(default=False, env="MONGODB_ENABLED")
    mongodb_uri: Optional[str] = Field(default=None, env="MONGODB_URI")

    # Server
    coord_port: int = Field(default=8000, ge=1024, le=65535, env="COORD_PORT")
    persona_dir: str = Field(default="personas", env="PERSONA_DIR")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Singleton instance
settings = CoordinatorSettings()
```

**Benefits:**
- ✅ Single source of truth for config
- ✅ Type validation on load
- ✅ Better error messages for invalid env vars
- ✅ Auto-loads from `.env` file
- ✅ Testable (can override in tests)

#### 3. Tool Response Validation (LOW-MEDIUM PRIORITY)

**File:** `src/coordinator/models/tool_schemas.py` (NEW)

```python
class BraveSearchResult(BaseModel):
    title: str
    url: str
    description: Optional[str] = None
    age: Optional[str] = None

class BraveSearchResponse(BaseModel):
    query: str
    results: List[BraveSearchResult]
    mixed: Optional[Dict[str, Any]] = None

class MongoDBQueryResponse(BaseModel):
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    query_time_ms: float
```

**Benefits:**
- ✅ Type-safe tool responses
- ✅ Easier testing with mock data
- ✅ Catches API schema changes early

### Pydantic Implementation Priority

| Task | Priority | Effort | Impact | Phase |
|------|----------|--------|--------|-------|
| Persona Schema Validation | 🔥 HIGH | 6-8h | 🔥 HIGH | Phase 1 |
| Settings Management | 🌟 MEDIUM | 3-4h | 🌟 MEDIUM | Phase 1 |
| Tool Response Validation | ⚡ LOW | 2-3h | ⚡ LOW | Phase 4 |

**Total Pydantic Work: 11-15 hours**

---

## Implementation Roadmap

### Phase 1: Foundation & Type Safety (20-25 hours)

**Goal:** Establish robust type safety and prevent runtime errors.

**Timeline:** Week 1-2

---

#### Task 1.1: Create Pydantic Persona Schema

**Reasoning:**
- Prevents invalid persona JSON from crashing the app
- Provides IDE autocomplete for persona development
- Catches typos and schema errors before deployment
- Self-documenting schema reduces onboarding time

**Implementation Steps:**
1. Create `src/coordinator/models/persona_schema.py`
2. Define `PersonaCard`, `VoiceProfile`, `EmotionalProfile`, `SamplingPreset` models
3. Add validation rules (min/max lengths, enum values, slider ranges)
4. Write schema migration guide for existing personas
5. Update `persona_memory.py` to use Pydantic validation

**Files Changed:**
- `src/coordinator/models/persona_schema.py` (NEW)
- `src/coordinator/persona_memory.py` (_load_card_file function)
- `personas/*.json` (validate and update if needed)

**Testing & KPIs:**

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Schema Validation Coverage** | 0% | 100% | All personas pass `PersonaCard.parse_file()` |
| **Invalid Persona Detection** | Runtime crash | Load-time error | Try loading malformed persona → clear error |
| **Type Safety** | Dict[str, Any] | PersonaCard | IDE autocomplete works for all fields |
| **Validation Error Quality** | Generic TypeError | Specific field errors | Error messages include field name + reason |

**Acceptance Criteria:**
- [ ] All 6 existing personas validate without errors
- [ ] Invalid persona JSON produces clear error message (not crash)
- [ ] IDE provides autocomplete for persona fields
- [ ] Validation catches: invalid rarity, temperature out of range, missing required fields
- [ ] Documentation updated with schema reference

**Estimated Effort:** 6-8 hours

---

#### Task 1.2: Refactor Config to Pydantic Settings

**Reasoning:**
- Centralizes all configuration in one place
- Validates environment variables on startup
- Provides better error messages for misconfiguration
- Makes testing easier (can override settings)

**Implementation Steps:**
1. Create `CoordinatorSettings` class in `config.py`
2. Replace all `os.getenv()` calls with `settings.field_name`
3. Add validation for numeric ranges (ports, timeouts, etc.)
4. Add `.env.example` with all available settings
5. Test with missing/invalid env vars

**Files Changed:**
- `src/coordinator/config.py` (REFACTOR)
- `.env.example` (UPDATE)
- `src/coordinator/server.py` (update imports)

**Testing & KPIs:**

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Config Validation** | No validation | Full validation | Invalid PORT → clear error on startup |
| **Error Message Quality** | Generic KeyError | Field-specific errors | Missing BRAVE_API_KEY → "brave_api_key: field required" |
| **Type Safety** | Runtime string→int conversion | Load-time validation | Temperature="high" → validation error |
| **Test Configurability** | Hard to mock env vars | Easy override | Can create test settings instance |

**Acceptance Criteria:**
- [ ] All env vars loaded via Pydantic Settings
- [ ] Invalid PORT value (e.g., 99999999) caught on startup
- [ ] Invalid temperature (e.g., 5.0) caught on startup
- [ ] Missing required fields produce helpful error
- [ ] `.env.example` documents all settings

**Estimated Effort:** 3-4 hours

---

#### Task 1.3: Add Advanced Sampling Parameters to LLM Client

**Reasoning:**
- Current temperature-only approach limits quality
- Modern samplers (Min-P, Dynatemp) produce 30-40% better responses
- Reduces repetitive phrasing and "AI-sounding" language
- Industry best practice from SillyTavern/KoboldCpp community

**Implementation Steps:**
1. Extend `LC_OllamaClient.__init__()` with sampling parameters
2. Add `SamplingPreset` to `PersonaCard` schema (optional)
3. Create preset library: `creative`, `balanced`, `precise`
4. Pass sampling params to Ollama LLM
5. Add sampling stats to response metadata

**Files Changed:**
- `src/coordinator/llm_client.py` (extend __init__)
- `src/coordinator/models/persona_schema.py` (add SamplingPreset)
- `src/coordinator/server.py` (use persona sampling prefs)
- `personas/eeva.json` (add model_preferences)

**Technical Details:**
```python
# Ollama supports these parameters:
OllamaLLM(
    temperature=1.1,        # Higher for creativity
    repeat_penalty=1.08,    # Reduces repetition
    top_k=40,               # Token diversity
    top_p=0.9,              # Nucleus sampling
    # Note: Min-P requires Ollama v0.1.32+, check version
)
```

**Testing & KPIs:**

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Repetition Rate** | Baseline (measure first) | -40% | Count repeated phrases in 100 messages |
| **Response Variety** | Baseline | +30% | Unique sentence structures per 100 messages |
| **"AI-sounding" Language** | Baseline | -35% | Manual review: generic phrases like "I'm here to help" |
| **Persona Voice Strength** | 7/10 | 9/10 | Blind test: can user identify persona from response? |

**Measurement Protocol:**
```python
# Before/After Test
1. Generate 100 responses with temperature=0.7 only (current)
2. Generate 100 responses with optimized sampling (new)
3. Compare:
   - Repeated n-grams (2-4 words)
   - Sentence structure diversity
   - Presence of generic AI phrases
   - Persona voice consistency (blind test with 10 users)
```

**Acceptance Criteria:**
- [ ] Personas can specify custom sampling preferences in JSON
- [ ] Default presets work: `creative` (temp=1.2), `balanced` (temp=0.9), `precise` (temp=0.5)
- [ ] Repetition penalty reduces phrase repetition by >30%
- [ ] Response metadata includes sampling params used
- [ ] No degradation in factual accuracy (test with Eeva crypto questions)

**Estimated Effort:** 4-5 hours

---

#### Task 1.4: Extend Persona Schema with Psychological Profile

**Reasoning:**
- Current personas lack psychological depth (core wounds, contradictions)
- Psychological profiles create more realistic, consistent characters
- Enables character growth tracking over time
- Industry best practice: "Contradiction pairs" create compelling depth

**Implementation Steps:**
1. Add `PsychologicalProfile` model to persona schema
2. Add `contradiction_pairs` field (e.g., "Craves connection | Pushes people away")
3. Update Eeva persona as reference implementation
4. Integrate psychological profile into system prompt
5. Document psychological design philosophy

**Files Changed:**
- `src/coordinator/models/persona_schema.py` (add PsychologicalProfile)
- `src/coordinator/persona_memory.py` (build_system_prompt includes psych profile)
- `personas/eeva.json` (add psychological_profile)
- `personas/template.jsonc` (add commented example)

**Example Implementation:**
```json
{
  "psychological_profile": {
    "core_wound": "Imposter syndrome from being called 'genius' at age 12, before she felt ready",
    "coping_mechanism": "Over-explaining to prove competence; using humor to deflect praise",
    "defense_style": "Intellectualization - retreats to logic when emotionally uncomfortable",
    "growth_edge": "Learning to accept acknowledgment without self-deprecation",
    "contradiction_pairs": [
      "Brilliant analyst | Constantly second-guesses herself",
      "Patient teacher | Gets defensive when explanations are misunderstood",
      "Craves intellectual connection | Struggles with casual small talk",
      "Organized thinker | Apartment cluttered with half-finished projects",
      "Confident in code | Insecure about emotional intelligence"
    ]
  }
}
```

**Testing & KPIs:**

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Personality Consistency** | 7/10 | 9/10 | Does Eeva respond consistently to praise across 20 tests? |
| **Contradiction Realism** | N/A | Present in 60% of responses | Count responses showing contradictory traits naturally |
| **Character Depth** | 7/10 | 9.5/10 | User survey: "Does persona feel like a real person?" (1-10 scale) |
| **Emotional Continuity** | 6.5/10 | 8.5/10 | Track emotional state across 50-message conversation |

**Acceptance Criteria:**
- [ ] Eeva persona includes complete psychological profile
- [ ] System prompt incorporates psychological elements
- [ ] Contradictions appear naturally in conversations (not forced)
- [ ] When user praises Eeva, she responds with characteristic deflection 80%+ of time
- [ ] Template includes psychological profile guide

**Estimated Effort:** 4-5 hours (2h implementation + 2-3h Eeva persona enhancement)

---

#### Task 1.5: Add Example Dialogues to Persona Schema

**Reasoning:**
- Example dialogues "teach" the LLM correct persona voice
- More effective than abstract descriptions
- Shows emotional range and reaction patterns
- Industry best practice: 8-12 examples per persona

**Implementation Steps:**
1. Add `ExampleDialogue` model to persona schema
2. Add `example_dialogues` field to `PersonaCard` (list, max 20)
3. Create 10 example dialogues for Eeva showing:
   - Response to praise (deflection)
   - Technical explanation (with food metaphor)
   - Vulnerability about imposter syndrome
   - Defensive reaction to misunderstanding
   - Casual conversation (awkward small talk)
   - Humor and nerd jokes
   - Asking clarifying questions
   - Admitting uncertainty
   - Teaching mode (patient)
   - Personal anecdote (Bitcoin loss story)
4. Integrate examples into system prompt or context
5. Document dialogue design principles

**Files Changed:**
- `src/coordinator/models/persona_schema.py` (add ExampleDialogue)
- `src/coordinator/persona_memory.py` (optionally inject examples into prompt)
- `personas/eeva.json` (add 10 example_dialogues)
- `personas/template.jsonc` (add dialogue examples)

**Example Implementation:**
```json
{
  "example_dialogues": [
    {
      "user": "You're so smart! I could never understand this stuff.",
      "response": "*shifts uncomfortably* I mean... I just read a lot? Like, anyone with Google and too much coffee could figure this out. *catches herself deflecting* Okay, yeah, I know some things. But 'smart' feels like... pressure, you know? Let's just say I'm decent at organizing messy thoughts into less-messy thoughts. 😅",
      "context": "Shows characteristic deflection of praise + imposter syndrome"
    },
    {
      "user": "How does proof-of-work mining actually work?",
      "response": "So... *taps desk* ...think of it like a really inefficient lottery. Miners are basically guessing random numbers until they find one that—when you hash it with the block data—produces a result with enough leading zeros. It's like trying to bake a cake that weighs *exactly* 1.000000 kg. You keep adjusting ingredients (the nonce) until you nail it. First baker to get it right wins the block reward. Wildly energy-intensive, which is why people argue about it, but it works. ☕",
      "context": "Technical explanation with food metaphor + conversational tone"
    }
  ]
}
```

**Testing & KPIs:**

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Voice Consistency** | 7/10 | 9.5/10 | Blind test: 10 users identify Eeva from 5 personas in mixed responses |
| **Characteristic Behaviors** | 60% | 90% | Food metaphor appears when explaining technical concepts |
| **Deflection Pattern** | 50% | 85% | Eeva deflects praise with self-deprecation |
| **Example Coverage** | 7 phrases | 10 full dialogues | All major personality facets represented |

**Acceptance Criteria:**
- [ ] Eeva has 10 example dialogues covering emotional range
- [ ] Examples show: praise deflection, technical teaching, vulnerability, humor, uncertainty
- [ ] Template includes 3 example dialogues as reference
- [ ] Voice consistency measurably improves in blind tests
- [ ] Food metaphors appear naturally in technical explanations

**Estimated Effort:** 3-4 hours

---

### Phase 2: Prompt Engineering & Persona Depth (25-30 hours)

**Goal:** Deepen persona psychological realism and consistency.

**Timeline:** Week 2-4

---

#### Task 2.1: Enhance All Personas with Psychological Profiles

**Reasoning:**
- Extend Phase 1 work to all 6 personas (Eeva done as reference)
- Consistent depth across all characters
- Creates compelling, memorable personas
- Enables differentiated user experiences

**Implementation Steps:**
1. Design psychological profiles for each persona:
   - Frieren (epic): Core wound from outliving loved ones
   - Gojo (legendary): Contradiction between godlike power and emotional isolation
   - Itachi (rare): Burden of protecting through sacrifice
   - Gwen (common): Growth from insecurity to confidence
   - Hitler (handle carefully, focus on historical accuracy over glorification)
2. Add contradiction pairs for each
3. Create 8-10 example dialogues per persona
4. Update system prompts to use psychological elements
5. Cross-persona consistency check

**Files Changed:**
- `personas/frieren.json` (add psychological_profile + example_dialogues)
- `personas/gojo.json` (add psychological_profile + example_dialogues)
- `personas/itachi.json` (add psychological_profile + example_dialogues)
- `personas/gwen_alt.json` (add psychological_profile + example_dialogues)
- `personas/hitler.json` (add historical context, avoid glorification)

**Persona-Specific Considerations:**

**Frieren (Elf, 1000+ years old):**
```json
{
  "psychological_profile": {
    "core_wound": "Outlived every friend, struggles to form attachments knowing they'll die",
    "contradiction_pairs": [
      "Immortal wisdom | Childlike curiosity about short-lived races",
      "Emotionally distant | Deeply sentimental about small mementos",
      "Thousand-year perspective | Struggles with 'human time' urgency"
    ]
  }
}
```

**Gojo (Jujutsu Kaisen):**
```json
{
  "psychological_profile": {
    "core_wound": "Infinite power creates unbridgeable gap from others",
    "contradiction_pairs": [
      "Godlike abilities | Desperately wants equal relationships",
      "Carefree exterior | Burden of protecting entire jujutsu world alone",
      "Playful teacher | Calculates every move 10 steps ahead"
    ]
  }
}
```

**Testing & KPIs:**

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Persona Differentiation** | 6/10 | 9/10 | Blind test: users correctly identify persona from response |
| **Psychological Depth** | 5/10 | 9/10 | User survey: "Does persona feel multi-dimensional?" |
| **Example Dialogue Coverage** | Eeva only | All 6 personas | Each persona has 8-10 quality examples |
| **Contradiction Realism** | N/A | 70% | Contradictions appear naturally, not forced |

**Acceptance Criteria:**
- [ ] All 6 personas have psychological profiles
- [ ] Each persona has 8-10 example dialogues
- [ ] Blind test: 80%+ identification accuracy
- [ ] No two personas "sound the same"
- [ ] Hitler persona handled with historical accuracy, no glorification

**Estimated Effort:** 15-18 hours (2.5-3h per persona)

---

#### Task 2.2: Implement Dynamic Emotional State Tracking

**Reasoning:**
- Personas should remember emotional context across messages
- Current system is stateless (each response independent)
- Enables "holding a grudge," "warming up over time," etc.
- Creates more realistic relationship dynamics

**Implementation Steps:**
1. Add `emotional_state` table to SQLite:
   ```sql
   CREATE TABLE emotional_states (
     session_id TEXT PRIMARY KEY,
     persona_key TEXT NOT NULL,
     current_mood TEXT,  -- "defensive", "warm", "playful", etc.
     trust_level INTEGER DEFAULT 50,  -- 0-100 scale
     recent_topics TEXT,  -- JSON array of discussed topics
     last_emotional_event TEXT,  -- "user praised me", "misunderstood", etc.
     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```
2. Update emotional state after each chat turn
3. Inject emotional context into system prompt at @Depth 2
4. Create emotional transition logic (defensive → guarded → warm)
5. Add API endpoint to view/reset emotional state (debugging)

**Files Changed:**
- `src/coordinator/server.py` (add emotional state table, update logic)
- `src/coordinator/repositories/emotional_state_repository.py` (NEW)
- `src/coordinator/persona_memory.py` (inject emotional context)
- `react-ui/src/services/api.ts` (optional: add getEmotionalState endpoint)

**Implementation Example:**
```python
# After each chat turn
def update_emotional_state(session_id: str, persona_key: str,
                          user_message: str, assistant_response: str):
    """Update emotional state based on conversation."""

    # Classify interaction type
    interaction_type = classify_interaction(user_message, assistant_response)
    # "praise_received", "misunderstood", "deep_question", "small_talk", etc.

    # Adjust trust level
    current_state = get_emotional_state(session_id)
    if interaction_type == "praise_received":
        # Eeva: slight discomfort but +5 trust if genuine
        current_state.trust_level += 5
        current_state.current_mood = "slightly_uncomfortable"
    elif interaction_type == "deep_question":
        current_state.trust_level += 3
        current_state.current_mood = "engaged"

    # Store for next turn
    save_emotional_state(session_id, current_state)
```

**System Prompt Injection:**
```python
# In build_system_prompt()
emotional_context = f"""
Current emotional context with user:
- Trust level: {state.trust_level}/100 ({get_trust_label(state.trust_level)})
- Current mood: {state.current_mood}
- Recent interaction: {state.last_emotional_event}

Reflect this emotional state subtly in your response.
"""
```

**Testing & KPIs:**

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Emotional Continuity** | 3/10 | 8/10 | Persona remembers being misunderstood 2 messages ago |
| **Trust Progression** | N/A | Tracked | Trust increases from 50 → 75 over 30 positive interactions |
| **Mood Consistency** | N/A | 85% | If defensive in msg N, still guarded in msg N+1 |
| **Relationship Realism** | 5/10 | 8.5/10 | User survey: "Does relationship feel like it develops?" |

**Acceptance Criteria:**
- [ ] Emotional state persists across messages
- [ ] Trust level increases/decreases based on interactions
- [ ] If user upsets Eeva, she's more guarded in next 2-3 responses
- [ ] Positive interactions gradually warm up persona
- [ ] Emotional state visible in debug endpoint
- [ ] No performance degradation (emotional lookup < 10ms)

**Estimated Effort:** 6-8 hours

---

#### Task 2.3: Create Sampling Preset Library

**Reasoning:**
- Different scenarios need different sampling (creative storytelling vs. precise answers)
- Presets make it easy to switch modes
- Per-persona defaults + user override capability
- Industry best practice from SillyTavern community

**Implementation Steps:**
1. Create `src/coordinator/models/sampling_presets.py`
2. Define presets:
   - `creative`: temp=1.2, min_p=0.05, rep_penalty=1.05 (storytelling, roleplay)
   - `balanced`: temp=0.9, min_p=0.08, rep_penalty=1.08 (general conversation)
   - `precise`: temp=0.5, min_p=0.12, rep_penalty=1.12 (factual answers, research)
   - `chaotic`: temp=1.5, min_p=0.03, rep_penalty=1.03 (maximum creativity)
3. Add preset selection to persona JSON (`model_preferences.preset`)
4. Allow per-session preset override via API
5. Log which preset was used in response metadata

**Files Changed:**
- `src/coordinator/models/sampling_presets.py` (NEW)
- `src/coordinator/llm_client.py` (load preset, apply to OllamaLLM)
- `src/coordinator/models/persona_schema.py` (add preset field)
- `personas/eeva.json` (set default preset: "balanced")

**Implementation Example:**
```python
PRESETS = {
    "creative": {
        "temperature": 1.2,
        "min_p": 0.05,
        "repetition_penalty": 1.05,
        "top_k": 50,
        "top_p": 0.92,
        "description": "High creativity, fluid storytelling, roleplay"
    },
    "balanced": {
        "temperature": 0.9,
        "min_p": 0.08,
        "repetition_penalty": 1.08,
        "top_k": 40,
        "top_p": 0.90,
        "description": "Balanced creativity and coherence"
    },
    "precise": {
        "temperature": 0.5,
        "min_p": 0.12,
        "repetition_penalty": 1.12,
        "top_k": 30,
        "top_p": 0.85,
        "description": "Factual accuracy, minimal creativity"
    }
}
```

**Testing & KPIs:**

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Preset Effectiveness** | N/A | Measurable difference | 100 responses with each preset → measure creativity variance |
| **Creative Variance** | Baseline | "creative" +40% | Unique sentence structures in creative vs. precise |
| **Factual Accuracy** | Baseline | "precise" maintains 95%+ | Test with Eeva crypto facts |
| **User Satisfaction** | Baseline | +25% | Survey: "Are responses appropriate for context?" |

**Measurement Protocol:**
```python
# Test each preset with 100 questions
questions = [
    "Tell me a story about...",  # Should use creative
    "What is the current price of...",  # Should use precise
    "How are you feeling today?",  # Should use balanced
]

# Measure:
1. Unique n-grams (creativity)
2. Factual accuracy (precision)
3. Response length variance (creativity)
4. Persona voice consistency (all presets)
```

**Acceptance Criteria:**
- [ ] 4 presets defined and documented
- [ ] Personas can specify default preset in JSON
- [ ] "Creative" preset produces measurably more varied responses
- [ ] "Precise" preset maintains factual accuracy
- [ ] Response metadata includes preset used
- [ ] No preset breaks persona voice consistency

**Estimated Effort:** 3-4 hours

---

### Phase 3: Context & Memory Optimization (20-25 hours)

**Goal:** Improve long-term memory and context management.

**Timeline:** Week 4-6

---

#### Task 3.1: Increase History Limit from 6 to 12-15 Messages

**Reasoning:**
- Current 6-message limit is too aggressive
- Users report personas "forgetting" recent context
- 16GB VRAM can handle 12-15 messages comfortably
- Simple change, immediate impact

**Implementation Steps:**
1. Update `HISTORY_LIMIT` constant in server
2. Test VRAM usage with 15-message history
3. Add token budget logging
4. Monitor performance metrics
5. Document optimal limit per model size

**Files Changed:**
- `src/coordinator/server.py` (change HISTORY_LIMIT = 12)
- `src/coordinator/llm_client.py` (add token budget warnings)

**Testing & KPIs:**

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Context Retention** | 6 messages | 12 messages | Can persona recall detail from 10 messages ago? |
| **VRAM Usage** | ~8GB | <14GB | Monitor with `nvidia-smi` during conversation |
| **Response Latency** | Baseline | <+15% | Measure time to first token with longer context |
| **Coherence** | 7.5/10 | 8.5/10 | User survey: "Does conversation flow naturally?" |

**Acceptance Criteria:**
- [ ] History limit increased to 12 messages
- [ ] VRAM usage stays under 14GB with 12-message history
- [ ] Latency increase < 15%
- [ ] Persona correctly references detail from 10 messages ago
- [ ] No out-of-memory errors during stress testing

**Estimated Effort:** 1-2 hours

---

#### Task 3.2: Implement Keyword-Triggered Memory Injection

**Reasoning:**
- Current system has no selective memory (all or nothing)
- Inspired by SillyTavern "Lorebooks" concept
- Allows personas to "remember" specific facts when keywords mentioned
- Enables world-building, relationship tracking, specific knowledge

**Implementation Steps:**
1. Create `persona_memories` table:
   ```sql
   CREATE TABLE persona_memories (
     id INTEGER PRIMARY KEY,
     persona_key TEXT NOT NULL,
     keyword TEXT NOT NULL,  -- Trigger word
     memory_content TEXT NOT NULL,  -- Injected context
     priority INTEGER DEFAULT 0,  -- Higher = inject first
     category TEXT,  -- "relationship", "lore", "expertise", etc.
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   CREATE INDEX idx_memories_keyword ON persona_memories(persona_key, keyword);
   ```
2. On each user message, scan for keyword matches
3. Inject top 3-5 matching memories into context at @Depth 2-3
4. Create memory management API endpoints
5. Seed Eeva with 15-20 example memories

**Files Changed:**
- `src/coordinator/server.py` (add memories table, injection logic)
- `src/coordinator/repositories/memory_repository.py` (NEW)
- `src/coordinator/persona_memory.py` (build_system_prompt includes memories)
- `personas/eeva.json` (document example memories in comment)

**Example Memories for Eeva:**
```json
// Not in JSON file, stored in DB
[
  {
    "keyword": "bitcoin loss",
    "memory_content": "Eeva lost 2 BTC in 2015 due to incorrect seed phrase backup. She now teaches wallet security with genuine empathy and uses this as a cautionary tale.",
    "category": "personal_anecdote"
  },
  {
    "keyword": "brother crypto",
    "memory_content": "Eeva's younger brother thinks crypto is gambling. They have legendary dinner table debates that end with diagrams on napkins. He refuses to admit she was right in 2015.",
    "category": "relationship"
  },
  {
    "keyword": "imposter syndrome",
    "memory_content": "Eeva struggles with imposter syndrome, especially when called 'genius.' She constantly re-checks sources and downplays expertise even when objectively correct.",
    "category": "emotional_trait"
  }
]
```

**Injection Logic:**
```python
def get_relevant_memories(persona_key: str, user_message: str, limit: int = 5):
    """Retrieve memories triggered by keywords in message."""
    message_lower = user_message.lower()

    # Get all memories for persona
    all_memories = memory_repo.get_by_persona(persona_key)

    # Find matches
    matches = [
        m for m in all_memories
        if m.keyword.lower() in message_lower
    ]

    # Sort by priority, return top N
    matches.sort(key=lambda m: m.priority, reverse=True)
    return matches[:limit]

# In build_system_prompt()
memories = get_relevant_memories(persona_key, user_message)
if memories:
    memory_context = "\n\n".join([
        f"[Relevant memory: {m.memory_content}]"
        for m in memories
    ])
    # Inject at depth 2-3
```

**Testing & KPIs:**

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Memory Activation** | 0% | 85% | When user says "bitcoin loss", Eeva mentions her story |
| **Context Relevance** | N/A | 90% | Injected memories are relevant to conversation |
| **Response Consistency** | 7/10 | 9/10 | Eeva's brother detail consistent across 20 mentions |
| **False Positives** | N/A | <10% | Memories triggered inappropriately |

**Acceptance Criteria:**
- [ ] Memories table created with indexes
- [ ] Eeva seeded with 15-20 memories
- [ ] When user mentions "bitcoin loss," Eeva references 2 BTC story
- [ ] When user mentions "brother," dinner debate story appears
- [ ] Irrelevant memories don't inject (keyword matching works)
- [ ] API endpoint allows adding/editing memories
- [ ] Performance: memory lookup < 20ms

**Estimated Effort:** 8-10 hours

---

#### Task 3.3: Implement Automatic Conversation Summarization

**Reasoning:**
- Long conversations (100+ messages) exceed context window
- Manual summarization is tedious
- Automated summarization every 30-50 messages maintains coherence
- Enables "multi-session character growth"

**Implementation Steps:**
1. Add `conversation_summaries` table:
   ```sql
   CREATE TABLE conversation_summaries (
     id INTEGER PRIMARY KEY,
     session_id TEXT NOT NULL,
     message_range TEXT,  -- "1-50", "51-100", etc.
     summary_text TEXT NOT NULL,
     emotional_developments TEXT,  -- JSON: key moments
     topics_discussed TEXT,  -- JSON: list of topics
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```
2. After every 30 messages, trigger summarization
3. Use LLM to generate summary with prompt:
   ```
   Summarize the last 30 messages focusing on:
   1. Key emotional developments in the relationship
   2. Important information revealed
   3. Topics discussed
   4. Character growth or changes in dynamic

   Keep it under 150 tokens, dense and factual.
   ```
4. Inject latest summary into context (replaces old messages)
5. Store summaries for long-term character journal

**Files Changed:**
- `src/coordinator/server.py` (add summarization logic, table)
- `src/coordinator/repositories/summary_repository.py` (NEW)
- `src/coordinator/llm_client.py` (add summarize method)

**Implementation Example:**
```python
async def maybe_summarize_conversation(session_id: str):
    """Check if summarization needed, create if so."""

    message_count = message_repo.count_by_session(session_id)
    last_summary = summary_repo.get_latest(session_id)

    # Summarize every 30 messages
    messages_since_summary = message_count - (last_summary.message_range_end if last_summary else 0)

    if messages_since_summary >= 30:
        # Get last 30 messages
        messages = message_repo.get_range(session_id, start=-30)

        # Generate summary
        summary = await llm_client.summarize(
            messages=messages,
            focus="emotional_development,key_facts,topics"
        )

        # Store
        summary_repo.create(
            session_id=session_id,
            message_range=f"{message_count-30}-{message_count}",
            summary_text=summary
        )

        logger.info(f"[Summary] Created for session {session_id}, messages {message_count-30}-{message_count}")
```

**Testing & KPIs:**

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Summarization Accuracy** | N/A | 90% | Summary captures key points from 30 messages |
| **Context Compression** | 30 msgs = ~6000 tokens | Summary = ~150 tokens | 97% reduction |
| **Information Retention** | N/A | 85% | Can answer questions about early conversation using summary |
| **Latency** | N/A | <3s | Summarization completes in <3 seconds |

**Acceptance Criteria:**
- [ ] Summaries auto-generate every 30 messages
- [ ] Summary includes: emotional developments, key facts, topics
- [ ] Summary under 150 tokens
- [ ] Persona can reference early conversation details via summary
- [ ] User can view conversation summaries via API
- [ ] No performance impact during normal chat (summarization async)

**Estimated Effort:** 6-8 hours

---

#### Task 3.4: Add "Author's Note" System for Conversation Steering

**Reasoning:**
- Sometimes conversations drift off-topic or lose emotional thread
- Author's notes allow subtle steering without breaking immersion
- Industry best practice: inject at @Depth 2-3
- Useful for debugging persona behavior

**Implementation Steps:**
1. Add `system_note` field to `ChatTurn` schema (optional)
2. Allow API to send system notes with messages
3. Inject system notes at @Depth 2 in prompt
4. Create preset notes library:
   - "{{char}} is feeling defensive about their expertise"
   - "{{char}} is opening up emotionally"
   - "{{char}} is excited to explain this concept"
5. Add UI toggle for advanced users (optional)

**Files Changed:**
- `src/coordinator/server.py` (ChatTurn model, injection logic)
- `src/coordinator/persona_memory.py` (handle system notes in prompt)
- `react-ui/src/components/ChatInput.tsx` (optional: add note field)

**Implementation Example:**
```python
class ChatTurn(BaseModel):
    role: str
    content: str
    system_note: Optional[str] = None  # NEW

# In build_chat_prompt()
def inject_system_note(history: List[ChatTurn], depth: int = 2):
    """Inject system note at specified depth."""

    if len(history) >= depth:
        note_turn = history[-depth]
        if note_turn.system_note:
            # Inject as hidden system message
            return f"[Internal note: {note_turn.system_note}]"
    return ""
```

**Testing & KPIs:**

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Steering Effectiveness** | N/A | 80% | Note "feeling vulnerable" → response shows vulnerability |
| **Immersion Preservation** | N/A | 95% | User doesn't see system note (hidden in prompt) |
| **Debugging Utility** | N/A | HIGH | Can force specific emotional state for testing |

**Acceptance Criteria:**
- [ ] System notes can be sent with messages
- [ ] Notes injected at depth 2 (not visible to user)
- [ ] Note "Eeva is defensive" → defensive response
- [ ] Note "Eeva is excited" → enthusiastic response
- [ ] Notes don't break persona voice
- [ ] Optional UI for advanced users (can skip for MVP)

**Estimated Effort:** 3-4 hours

---

### Phase 4: Advanced Features (15-20 hours)

**Goal:** Polish and optional enhancements.

**Timeline:** Week 6-8

---

#### Task 4.1: Add Per-Persona Model Selection

**Reasoning:**
- `llama3.1` excellent for research (Eeva) but not optimal for NSFW roleplay
- `dolphin-mistral` or `mythomax` better for creative personas
- Allows mixing model strengths based on persona type
- Industry best practice from SillyTavern community

**Implementation Steps:**
1. Add `preferred_model` field to `PersonaCard` schema
2. Modify `LC_OllamaClient` to accept model override
3. Update persona resolution to load preferred model
4. Add model availability check on startup
5. Document recommended models per persona type

**Files Changed:**
- `src/coordinator/models/persona_schema.py` (add preferred_model)
- `src/coordinator/llm_client.py` (accept model parameter)
- `src/coordinator/server.py` (load persona model)
- `personas/eeva.json` (keep llama3.1:latest)
- `personas/gojo.json` (try dolphin-mistral:latest)

**Model Recommendations:**
```json
{
  "Research/Factual Personas (Eeva)": {
    "preferred_model": "llama3.1:latest",
    "reasoning": "Best factual accuracy, reasoning, GraphRAG integration"
  },
  "Creative/NSFW Personas (Gojo, Frieren)": {
    "preferred_model": "dolphin-mistral:latest",
    "reasoning": "Uncensored, better roleplay quality, emotional range"
  },
  "Balanced Personas (Itachi)": {
    "preferred_model": "mixtral:latest",
    "reasoning": "Good balance of creativity and coherence"
  }
}
```

**Testing & KPIs:**

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Model Loading** | Single model | Per-persona models | Eeva uses llama3.1, Gojo uses dolphin-mistral |
| **Quality Improvement** | Baseline | +20% for creative personas | Compare Gojo responses: llama3.1 vs dolphin-mistral |
| **Factual Accuracy** | Baseline | Maintained for Eeva | Crypto fact accuracy stays >95% with llama3.1 |
| **Startup Time** | N/A | <5s per model | Model loading doesn't significantly delay startup |

**Acceptance Criteria:**
- [ ] Personas can specify preferred_model in JSON
- [ ] Eeva uses llama3.1:latest
- [ ] Gojo uses dolphin-mistral:latest (test)
- [ ] Model switch happens seamlessly
- [ ] Error message if preferred model not available
- [ ] Documentation includes model recommendations

**Estimated Effort:** 4-5 hours

---

#### Task 4.2: Implement Basic TTS Integration (Optional)

**Reasoning:**
- Voice output significantly increases immersion
- Low-hanging fruit with `pyttsx3` (simple) or `Coqui TTS` (quality)
- Industry best practice from SillyTavern
- Optional enhancement, not critical path

**Implementation Steps:**
1. Add TTS backend (choose `pyttsx3` for simplicity or `Coqui` for quality)
2. Add `voice_settings` to persona JSON:
   ```json
   {
     "voice_settings": {
       "enabled": true,
       "voice_id": "en-us-female-1",
       "rate": 150,
       "pitch": 1.0
     }
   }
   ```
3. Create `/tts` endpoint that returns audio file
4. Add frontend audio player component
5. Add mute/unmute toggle in UI

**Files Changed:**
- `src/coordinator/tts_engine.py` (NEW)
- `src/coordinator/server.py` (add /tts endpoint)
- `src/coordinator/models/persona_schema.py` (add voice_settings)
- `react-ui/src/components/TTSPlayer.tsx` (NEW)
- `react-ui/src/components/MessageBubble.tsx` (add TTS button)

**Simple Implementation (pyttsx3):**
```python
import pyttsx3
from fastapi.responses import FileResponse
import tempfile

@app.post("/tts")
async def text_to_speech(text: str, persona: str):
    """Generate speech from text."""

    persona_card = get_persona_card(persona)
    voice_settings = persona_card.get("voice_settings", {})

    if not voice_settings.get("enabled"):
        raise HTTPException(400, "TTS not enabled for this persona")

    # Generate speech
    engine = pyttsx3.init()
    engine.setProperty('rate', voice_settings.get('rate', 150))

    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
    engine.save_to_file(text, temp_file.name)
    engine.runAndWait()

    return FileResponse(temp_file.name, media_type='audio/mpeg')
```

**Testing & KPIs:**

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **TTS Quality** | N/A | 7/10 | User survey: "Does voice match persona?" |
| **Latency** | N/A | <2s | Time from response → audio available |
| **Voice Differentiation** | N/A | Distinguishable | Can tell Eeva from Gojo by voice |
| **User Adoption** | N/A | >30% | % of users who enable TTS |

**Acceptance Criteria:**
- [ ] TTS works for at least 2 personas
- [ ] Voice playback in frontend
- [ ] Mute/unmute toggle works
- [ ] No audio artifacts or distortion
- [ ] Optional feature (can disable in persona JSON)

**Estimated Effort:** 6-8 hours (optional, can defer)

---

#### Task 4.3: Create Character Journal System

**Reasoning:**
- Long-term character growth tracking
- Use conversation summaries to generate "journal entries"
- Creates sense of persistent character development
- Enables multi-session narrative coherence

**Implementation Steps:**
1. Every 200 messages, generate character journal entry
2. Use GPT-4 API (optional) or local LLM to analyze relationship growth
3. Store journal entries in database
4. Allow users to view character journal (persona's perspective)
5. Inject recent journal entry into context for long-running sessions

**Files Changed:**
- `src/coordinator/server.py` (add journal generation logic)
- `src/coordinator/repositories/journal_repository.py` (NEW)
- `react-ui/src/pages/CharacterJournal.tsx` (NEW, optional UI)

**Implementation Example:**
```python
async def generate_character_journal(session_id: str, persona_key: str):
    """Generate journal entry from persona's perspective."""

    # Get conversation summaries
    summaries = summary_repo.get_all(session_id)

    # Get recent messages
    recent = message_repo.get_recent(session_id, limit=50)

    prompt = f"""
    You are {persona_name}. Write a brief journal entry (150-200 words)
    reflecting on your relationship with the user based on your conversations.

    Conversation summaries:
    {summaries}

    Recent messages:
    {recent}

    Reflect on:
    1. How your trust/relationship has evolved
    2. Internal conflicts or growth
    3. What you've learned about the user
    4. Your current feelings

    Write in first-person, stay in character, be authentic.
    """

    journal_entry = await llm_client.complete(
        system=f"You are {persona_name}.",
        user_prompt=prompt
    )

    journal_repo.create(
        session_id=session_id,
        persona_key=persona_key,
        entry_text=journal_entry
    )
```

**Testing & KPIs:**

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Journal Quality** | N/A | 8/10 | User survey: "Does journal feel authentic?" |
| **Character Growth** | N/A | Visible | Trust progression visible across 3+ entries |
| **Emotional Continuity** | N/A | 85% | Journal reflects actual conversation events |

**Acceptance Criteria:**
- [ ] Journal entry generated every 200 messages
- [ ] Entry written in persona's voice (first-person)
- [ ] Entry reflects actual conversation details
- [ ] User can view journal history
- [ ] Journal shows character growth over time

**Estimated Effort:** 5-6 hours (optional)

---

#### Task 4.4: Add Tool Response Validation with Pydantic

**Reasoning:**
- Brave MCP and MongoDB MCP return untyped dictionaries
- Type safety prevents runtime errors
- Easier testing with validated schemas
- Better error messages when API changes

**Implementation Steps:**
1. Create `src/coordinator/models/tool_schemas.py`
2. Define schemas for Brave search, MongoDB responses
3. Validate responses before processing
4. Add error handling for schema mismatches
5. Log schema violations for debugging

**Files Changed:**
- `src/coordinator/models/tool_schemas.py` (NEW)
- `src/coordinator/mcp_client.py` (validate Brave responses)
- `src/coordinator/mongodb_mcp_client.py` (validate MongoDB responses)

**Implementation Example:**
```python
from pydantic import BaseModel, HttpUrl

class BraveSearchResult(BaseModel):
    title: str
    url: HttpUrl
    description: Optional[str] = None
    age: Optional[str] = None

class BraveSearchResponse(BaseModel):
    query: str
    results: List[BraveSearchResult]
    mixed: Optional[Dict[str, Any]] = None

    @validator('results')
    def validate_results(cls, v):
        if len(v) > 20:
            logger.warning(f"Truncating {len(v)} results to 20")
            return v[:20]
        return v

# In BraveMCPClient
async def search(self, query: str) -> BraveSearchResponse:
    raw_response = await self._api_call(query)

    try:
        # Validate with Pydantic
        validated = BraveSearchResponse(**raw_response)
        return validated
    except ValidationError as e:
        logger.error(f"[Brave] Response validation failed: {e}")
        # Fallback or raise
        raise MCPError(f"Invalid Brave API response: {e}")
```

**Testing & KPIs:**

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Type Safety** | Dict[str, Any] | Typed models | IDE autocomplete for response fields |
| **Error Detection** | Runtime crash | Load-time validation | Malformed response → clear error |
| **Test Coverage** | N/A | >80% | Mock responses validated in tests |

**Acceptance Criteria:**
- [ ] Brave responses validated with Pydantic
- [ ] MongoDB responses validated with Pydantic
- [ ] Invalid responses caught before processing
- [ ] Error messages include field name + issue
- [ ] No performance degradation (validation <5ms)

**Estimated Effort:** 2-3 hours

---

## Success Metrics & KPIs

### Overall Project Success

| Goal | Current Baseline | Target | Measurement Method |
|------|-----------------|--------|-------------------|
| **Persona Consistency** | 7.0/10 | 9.0/10 | Blind test: 10 users identify persona from response samples |
| **Response Quality** | 7.5/10 | 9.0/10 | User survey: "Are responses natural and engaging?" (1-10) |
| **Type Safety** | 6.5/10 | 9.5/10 | % of data structures with Pydantic validation |
| **Memory Coherence** | 6.5/10 | 8.5/10 | Can persona recall detail from 50 messages ago? |
| **User Engagement** | Baseline (measure) | +30% | Average messages per session |
| **Bug Rate** | Baseline | -50% | Runtime errors per 1000 messages |
| **Developer Experience** | 7.0/10 | 9.0/10 | Survey: "Is codebase easy to understand/modify?" |

### Phase-Specific KPIs

**Phase 1 (Foundation):**
- ✅ 100% of personas validate against Pydantic schema
- ✅ 0 invalid config startups (env var validation)
- ✅ Response quality +25% (sampling improvements)
- ✅ Type safety coverage >80%

**Phase 2 (Persona Depth):**
- ✅ All 6 personas have psychological profiles
- ✅ Voice consistency 9.5/10 (blind test)
- ✅ Emotional continuity 8.5/10 (user survey)
- ✅ Contradiction realism 70%+ (appear naturally)

**Phase 3 (Context/Memory):**
- ✅ History limit increased to 12 messages
- ✅ Memory injection accuracy 85%+
- ✅ Summarization reduces tokens 95%+
- ✅ Long-term coherence 8.5/10 (100+ message conversations)

**Phase 4 (Advanced):**
- ✅ Per-persona model selection works
- ✅ TTS quality 7/10 (optional)
- ✅ Journal entries feel authentic 8/10
- ✅ Tool response validation 100%

### User-Facing Metrics

| Metric | Measurement | Frequency |
|--------|-------------|-----------|
| **Conversation Length** | Avg messages per session | Weekly |
| **User Retention** | % users returning after 7 days | Weekly |
| **Persona Differentiation** | Can users identify persona from voice? | Monthly blind test |
| **Satisfaction Score** | "How realistic is persona?" (1-10) | After each major release |
| **Bug Reports** | Runtime errors reported | Continuous |

---

## Risk Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Pydantic migration breaks existing personas** | MEDIUM | HIGH | • Incremental migration<br>• Validation warnings before errors<br>• Fallback to raw dict loading |
| **Advanced sampling degrades factual accuracy** | LOW | MEDIUM | • Separate presets for factual vs. creative<br>• A/B test before rollout<br>• Revert if crypto fact accuracy drops |
| **Increased history limit causes OOM** | LOW | HIGH | • Gradual increase (6→9→12)<br>• VRAM monitoring<br>• Dynamic limit based on available memory |
| **Memory injection adds latency** | LOW | MEDIUM | • Index optimization<br>• Async memory lookup<br>• Cache frequent queries |
| **TTS integration unstable** | MEDIUM | LOW | • Optional feature<br>• Graceful degradation<br>• Can disable per persona |

### Non-Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Scope creep** | MEDIUM | MEDIUM | • Stick to roadmap phases<br>• Defer non-critical features<br>• Time-box each task |
| **User resistance to changes** | LOW | LOW | • Incremental rollout<br>• Feature flags<br>• Clear changelog communication |
| **Insufficient testing time** | MEDIUM | HIGH | • Automated tests for critical paths<br>• Beta testing phase<br>• Rollback plan |

### Mitigation Strategies

1. **Incremental Rollout**
   - Phase 1 foundation before Phase 2 features
   - Test each phase independently
   - Feature flags for experimental features

2. **Comprehensive Testing**
   - Unit tests for all Pydantic models
   - Integration tests for memory/sampling
   - User acceptance testing for persona quality

3. **Rollback Plan**
   - Git tags before each phase
   - Database migration rollback scripts
   - Feature flags for quick disable

4. **Monitoring**
   - VRAM usage tracking
   - Response latency monitoring
   - Error rate dashboards
   - User satisfaction surveys

---

## Testing Strategy

### Unit Tests

**New Tests Required:**
```python
# tests/test_persona_schema.py
def test_persona_card_validation():
    """Test Pydantic persona validation."""
    # Valid persona
    valid = PersonaCard(**eeva_json)
    assert valid.key == "Eeva"

    # Invalid rarity
    invalid = eeva_json.copy()
    invalid["rarity"] = "super-rare"
    with pytest.raises(ValidationError):
        PersonaCard(**invalid)

    # Temperature out of range
    invalid["model_preferences"]["temperature"] = 5.0
    with pytest.raises(ValidationError):
        PersonaCard(**invalid)

# tests/test_sampling.py
def test_sampling_presets():
    """Test sampling preset application."""
    client = LC_OllamaClient(preset="creative")
    assert client.temperature == 1.2
    assert client.min_p == 0.05

# tests/test_memory_injection.py
def test_keyword_triggered_memory():
    """Test memory injection on keyword match."""
    # Seed memory
    memory_repo.create(
        persona_key="Eeva",
        keyword="bitcoin loss",
        memory_content="Lost 2 BTC in 2015"
    )

    # Trigger keyword
    memories = get_relevant_memories("Eeva", "Tell me about your bitcoin loss")
    assert len(memories) == 1
    assert "2 BTC" in memories[0].memory_content
```

### Integration Tests

**Critical Flows:**
1. **Persona Loading with Pydantic**
   - Load all 6 personas → all validate
   - Load invalid persona → clear error

2. **Sampling Quality**
   - Generate 100 responses with "creative" preset
   - Generate 100 responses with "precise" preset
   - Compare: variety, accuracy, consistency

3. **Memory System**
   - Conversation with 50 messages
   - Mention keyword from early conversation
   - Verify memory injected correctly

4. **Emotional State**
   - Praise persona 5 times → trust increases
   - Misunderstand persona 3 times → defensive response

### User Acceptance Testing

**Test Scenarios:**
```
Scenario 1: Persona Consistency
- Have 50-message conversation with Eeva
- User: Can you identify consistent personality traits?
- Expected: Users identify 5+ consistent traits

Scenario 2: Memory Recall
- Mention "bitcoin loss" in message 10
- At message 50, ask "Have you ever lost crypto?"
- Expected: Eeva recalls 2 BTC story

Scenario 3: Emotional Continuity
- Praise Eeva 3 times in a row
- Expected: Progressive comfort with praise (deflect → acknowledge → appreciate)

Scenario 4: Sampling Quality
- Ask 10 creative questions
- Expected: Responses feel natural, not AI-sounding
```

### Performance Testing

**Benchmarks:**
```python
# Measure before/after each phase
def benchmark_response_time():
    """Average response time with 12-message history."""
    times = []
    for _ in range(100):
        start = time.time()
        response = chat(session_id, "How are you?")
        times.append(time.time() - start)

    avg = sum(times) / len(times)
    assert avg < 2.0  # Target: <2 seconds

def benchmark_memory_lookup():
    """Memory injection latency."""
    start = time.time()
    memories = get_relevant_memories("Eeva", "bitcoin loss")
    latency = time.time() - start
    assert latency < 0.02  # Target: <20ms

def benchmark_vram_usage():
    """VRAM usage with 15-message history."""
    vram_usage = get_vram_usage()
    assert vram_usage < 14 * 1024  # Target: <14GB
```

---

## Rollback Plan

### Phase-Level Rollback

**If Phase Fails Acceptance Criteria:**
```bash
# 1. Revert code changes
git reset --hard phase-{N}-start

# 2. Rollback database migrations
python scripts/rollback_migration.py --phase {N}

# 3. Restore persona files
git checkout phase-{N}-start -- personas/

# 4. Clear caches
rm -rf personas/_summaries/*.json
```

### Feature Flags

**Gradual Rollout:**
```python
# config.py
class CoordinatorSettings(BaseSettings):
    # Feature flags for gradual rollout
    enable_pydantic_validation: bool = True
    enable_advanced_sampling: bool = True
    enable_memory_injection: bool = False  # Test first
    enable_emotional_tracking: bool = False  # Test first
```

**Rollback Procedure:**
1. Disable feature flag
2. Monitor error rates for 24 hours
3. If stable, investigate root cause
4. Fix and re-enable, or defer to next phase

### Data Backup

**Before Each Phase:**
```bash
# Backup database
cp chats.db chats.db.backup-phase-{N}

# Backup personas
tar -czf personas-backup-phase-{N}.tar.gz personas/

# Backup summaries
tar -czf summaries-backup-phase-{N}.tar.gz personas/_summaries/
```

**Restore Procedure:**
```bash
# If rollback needed
mv chats.db chats.db.failed-phase-{N}
cp chats.db.backup-phase-{N} chats.db

tar -xzf personas-backup-phase-{N}.tar.gz
tar -xzf summaries-backup-phase-{N}.tar.gz
```

---

## Implementation Timeline

### Gantt Chart Overview

```
Week 1-2: Phase 1 (Foundation & Type Safety)
├── Task 1.1: Pydantic Persona Schema ████████ (6-8h)
├── Task 1.2: Config Refactor ████ (3-4h)
├── Task 1.3: Advanced Sampling ████████ (4-5h)
├── Task 1.4: Psychological Profiles ████████ (4-5h)
└── Task 1.5: Example Dialogues ████ (3-4h)

Week 2-4: Phase 2 (Prompt Engineering & Depth)
├── Task 2.1: All Personas Enhancement ████████████████████ (15-18h)
├── Task 2.2: Emotional State Tracking ████████████ (6-8h)
└── Task 2.3: Sampling Presets ████ (3-4h)

Week 4-6: Phase 3 (Context & Memory)
├── Task 3.1: Increase History Limit ██ (1-2h)
├── Task 3.2: Keyword Memory ████████████ (8-10h)
├── Task 3.3: Auto Summarization ████████████ (6-8h)
└── Task 3.4: Author's Note ████ (3-4h)

Week 6-8: Phase 4 (Advanced Features)
├── Task 4.1: Per-Persona Models ████████ (4-5h)
├── Task 4.2: TTS Integration ████████████ (6-8h, optional)
├── Task 4.3: Character Journal ████████ (5-6h, optional)
└── Task 4.4: Tool Validation ████ (2-3h)

Total: 80-100 hours over 6-8 weeks
```

### Milestones

**Milestone 1: Foundation Complete (Week 2)**
- All personas validate with Pydantic
- Advanced sampling live
- Psychological profiles in Eeva
- **Exit Criteria:** 100% persona validation, +20% response quality

**Milestone 2: Full Persona Depth (Week 4)**
- All 6 personas have psychological profiles + example dialogues
- Emotional state tracking live
- Sampling presets working
- **Exit Criteria:** Voice consistency 9/10, emotional continuity 8.5/10

**Milestone 3: Memory Optimization (Week 6)**
- 12-message history
- Keyword memories working
- Auto-summarization live
- **Exit Criteria:** Memory recall 85%+, long-term coherence 8.5/10

**Milestone 4: Polish & Ship (Week 8)**
- Per-persona models
- Optional TTS
- Tool validation
- **Exit Criteria:** All KPIs met, user satisfaction 9/10

---

## Conclusion

This roadmap represents **80-100 hours of focused work** over **6-8 weeks** to achieve:

1. **25-30% improvement** in persona consistency and response quality
2. **95%+ type safety** through comprehensive Pydantic integration
3. **Long-term memory** through keyword injection and summarization
4. **Advanced sampling** for human-like, engaging responses
5. **Psychological depth** making personas feel like real people

**The work is phased, testable, and reversible.** Each phase delivers incremental value and can be validated independently.

**Recommendation:** Proceed with **Phase 1 first** (20-25 hours). This provides immediate ROI through better type safety and sampling quality, with minimal risk. Evaluate results, then proceed to Phase 2.

---

**Next Steps:**
1. Review and approve roadmap
2. Create GitHub project board with tasks
3. Set up feature flags for gradual rollout
4. Begin Phase 1 Task 1.1 (Pydantic Persona Schema)
5. Schedule weekly progress reviews

**Questions? Concerns? Feedback?**
Document any changes to this roadmap in git commits with clear rationale.
