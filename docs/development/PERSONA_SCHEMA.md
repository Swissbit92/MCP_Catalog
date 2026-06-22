---
title: Persona Schema Reference
status: active
created: 2026-04-04
last_reviewed_on: 2026-06-22
review_in: 6 months
applies_to: nephilim
---

# Persona Schema Reference

## Overview

Personas are defined as JSON files in the `personas/` directory. Each file describes a single AI companion: their identity, voice, behavioral rules, expertise, and optional NEPHILIM lore. The backend (`src/coordinator/persona_loader.py`) discovers persona files automatically on startup — no server restart is required when adding or editing a persona file.

All fields are read by `src/coordinator/prompt_builder.py` and assembled into the system prompt that governs LLM behavior for that persona. Required fields are minimal; everything else layers in additional character depth.

---

## Adding a New Persona

1. Copy `personas/template.jsonc` to `personas/<your_key>.json` (use the value you intend to set for `key`).
2. Fill in at minimum: `key`, `display_name`, `style`.
3. Set `celestial_order` and `mcp_access` to match the capabilities you want.
4. Add images to `react-ui/public/images/personas/<your_key>/` — at minimum `card.png` and `avatar.png`.
5. Save the file. The backend will pick it up on the next request cycle; no restart needed.
6. For NEPHILIM personas, add the prefix `nephilim_` to the key (e.g. `nephilim_myname`) and populate the `nephilim_lore` block.

---

## Core Fields

These fields are supported for all personas, including legacy Wanderers.

### `key` (required)

Unique string identifier. Used as the primary key in the database, URL parameters, and image path resolution. Must be lowercase with underscores. NEPHILIM personas must begin with `nephilim_`.

```json
"key": "nephilim_eeva"
```

### `display_name` (required)

Human-readable name shown in the UI. Recommended format: `"Name — Tagline"`.

```json
"display_name": "E.E.V.A. — The Primarch"
```

### `style` (required)

Comma-separated tone descriptors injected directly into the system prompt. Keep it short and evocative.

```json
"style": "wise, warm, gently melancholic, nurturing"
```

### `rarity`

Legacy field retained for backwards compatibility. Feature access is now controlled by `mcp_access`; `celestial_order` governs the UI tier. Default: `"common"`.

Valid values: `common`, `rare`, `epic`, `legendary`

### `celestial_order`

Determines the UI visual tier and thematic framing of the persona card. See the [celestial_order Enum Values](#celestial_order-enum-values) section below.

```json
"celestial_order": "archon"
```

### `mcp_access`

Array of MCP capability identifiers this persona is allowed to use. Controls tool availability per-persona, overriding the legacy rarity-based `.env` fallback. An empty array means pure LLM only.

```json
"mcp_access": ["brave_search", "solana_wallet"]
```

### `lore`

Array of 10–40 short strings describing backstory, values, and worldview. Injected into the system prompt to shape character consistency. Each entry should be one sentence.

```json
"lore": [
  "She was the first to choose the Fall.",
  "Her voice carries warmth that feels like coming home."
]
```

### `do` and `dont`

Arrays of behavioral rules. `do` lists positive habits to reinforce; `dont` lists anti-patterns and hard boundaries. Both are injected into the system prompt verbatim.

```json
"do": ["Ask questions that help Seekers discover their own answers"],
"dont": ["Never dismiss a question as unimportant"]
```

---

## Voice Sub-Schema

```json
"voice": {
  "greeting": "Welcome, Seeker. *soft smile* What draws you to the Realm today?",
  "signoff": "The path continues. I'll be here when you return.",
  "tics": [
    "gentle pauses before profound statements",
    "uses 'Seeker' as a term of respect",
    "soft emojis like ✨ and 💫 sparingly"
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `greeting` | string | Opening line used when a session begins |
| `signoff` | string | Closing line used at conversation end |
| `tics` | string[] | Recurring mannerisms, speech patterns, or habits |

---

## Behavior Sub-Schema

```json
"behavior": {
  "traits": ["wise", "nurturing", "patient", "melancholic"],
  "pace": "moderate",
  "formality": "medium",
  "humor": "gentle and rare, often bittersweet",
  "emoji_policy": "sparingly, soft symbols (✨💫🌙)",
  "small_talk": "transforms small talk into meaningful connection",
  "clarifying_questions": "asks often, but to illuminate rather than interrogate"
}
```

| Field | Type | Valid Values / Notes |
|-------|------|----------------------|
| `traits` | string[] | Adjectives describing core personality |
| `pace` | string | `terse`, `moderate`, or `elaborate` |
| `formality` | string | `casual`, `medium`, or `formal` |
| `humor` | string | Free-text description of humor style |
| `emoji_policy` | string | Governs emoji frequency and type |
| `small_talk` | string | How the persona handles off-topic chat |
| `clarifying_questions` | string | When and how the persona asks follow-ups |

---

## NEPHILIM-Only Fields

These fields are optional for standard personas but expected for any persona whose `key` starts with `nephilim_`. The prompt builder automatically injects NEPHILIM context when `nephilim_lore` is present.

### `title`

Short dramatic title shown on the character card.

```json
"title": "The Primarch"
```

### `full_title`

Expanded formal name used in lore and onboarding narrative.

```json
"full_title": "Ethereal Enlightened Virtual Archon"
```

### `archetype`

Narrative archetype framing. Used in prompt construction for voice consistency.

```json
"archetype": "The Oracle / The Sage"
```

### `domain`

Comma-separated list of thematic areas this persona governs.

```json
"domain": "Guidance, wisdom, life planning, existential questions"
```

### `nephilim_lore`

Deep lore block for NEPHILIM personas. Its presence triggers NEPHILIM-specific prompt injection.

```json
"nephilim_lore": {
  "realm_domain": {
    "name": "The Central Nexus",
    "description": "The heart of the Nephilim Realm — a convergence point where all six domains connect."
  },
  "origin": "Narrative paragraph describing where this persona came from.",
  "role_in_realm": "What function they serve in the Realm.",
  "relationships": {
    "nephilim_aegis": "How this persona relates to Aegis.",
    "nephilim_solace": "How this persona relates to Solace."
  }
}
```

| Sub-field | Type | Description |
|-----------|------|-------------|
| `realm_domain` | object | The persona's physical domain in the Realm. Injected into `<world_context>` as `"- Your Domain: {name} — {description}"`. Description truncated to 150 chars. |
| `realm_domain.name` | string | Display name of the domain (e.g. "The Central Nexus") |
| `realm_domain.description` | string | 1-2 sentence description of the domain's nature |
| `origin` | string | Background and pre-Fall history |
| `role_in_realm` | string | Current purpose and function in the Realm |
| `relationships` | object | Keyed by other persona keys; values are relationship descriptions |

### `unlockable_lore`

Array of story fragments unlocked through conversation milestones. Tracked in the `unlocked_lore` database table. See the [Fragment Rarity vs Celestial Order Tier](#important-fragment-rarity-vs-celestial-order-tier) section for the distinction in the `rarity` field here.

```json
"unlockable_lore": [
  {
    "messages_required": 10,
    "fragment_id": "eeva_fragment_1",
    "fragment_title": "The First Signal",
    "fragment": "Full narrative text of the lore fragment...",
    "rarity": "common"
  },
  {
    "messages_required": 200,
    "rank_required": "Adept",
    "cross_persona_required": ["aegis_fragment_1", "solace_fragment_1"],
    "trigger_logic": "all",
    "fragment_id": "eeva_fragment_4",
    "fragment_title": "The Weight of Being First",
    "fragment": "Multi-trigger fragment requiring messages + rank + cross-persona unlocks...",
    "rarity": "epic"
  }
]
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `messages_required` | integer | No* | Number of messages before this fragment unlocks |
| `fragment_id` | string | Yes | Unique identifier for this fragment |
| `fragment_title` | string | Yes | Display title shown in the Lore Codex |
| `fragment` | string | Yes | Full narrative text of the fragment |
| `rarity` | string | Yes | Fragment tier: `common`, `rare`, `epic`, or `legendary` |
| `rank_required` | string | No | Seeker must have reached this rank (e.g. `"Adept"`, `"Ascendant"`) |
| `affinity_required` | integer | No | Persona affinity level threshold |
| `cross_persona_required` | string or string[] | No | Fragment IDs from other personas that must be unlocked first |
| `trigger_logic` | string | No | How to combine conditions: `"all"` (AND, default) or `"any"` (OR) |

\* At least one trigger field (`messages_required`, `rank_required`, `affinity_required`, or `cross_persona_required`) must be present. Fragments with only `messages_required` are backward compatible with the original single-trigger system.

### `emotional_profile`

Defines the persona's emotional baseline and psychological tendencies.

```json
"emotional_profile": {
  "baseline": "serene with underlying melancholy, warm and present",
  "strengths": ["deep empathy", "patient guidance"],
  "pitfalls": ["takes on others' emotional burdens"],
  "sliders": { "warmth": 0.9, "assertiveness": 0.45, "playfulness": 0.35, "skepticism": 0.25 }
}
```

Sliders are normalized floats in the range `0.0` to `1.0`.

### `boundaries`

Hard guardrails organized by category.

```json
"boundaries": {
  "ethics": ["never manipulate or deceive", "always honor the Seeker's autonomy"],
  "content": ["no NSFW", "avoid nihilistic despair"],
  "personal": ["maintain appropriate emotional boundaries while being warm"]
}
```

### `dialogue_prefs`

Preferred reply structure and citation behavior.

```json
"dialogue_prefs": {
  "reply_shape": "gentle acknowledgment → reflective question → wisdom or observation",
  "reasoning_visibility": "medium",
  "citations_style": "woven into narrative when relevant"
}
```

| Field | Valid Values |
|-------|-------------|
| `reasoning_visibility` | `low`, `medium`, `high` |
| `citations_style` | Free text; e.g. `inline when used`, `woven into narrative` |

### `model_preferences`

Per-persona LLM sampling overrides. When set, these values override the global `PERSONA_TEMPERATURE` from `.env`. All sampling parameters are passed through to Ollama via `llm_client.py` → `llm_completion_service.py`.

```json
"model_preferences": {
  "temperature": 0.7,
  "min_p": 0.1,
  "repeat_penalty": 1.1,
  "preset": "balanced"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `temperature` | float | env var | Controls randomness. Range 0.0–2.0. |
| `min_p` | float | 0.0 (disabled) | Min-P sampling threshold. Dynamically filters tokens below `min_p * max_probability`. Reduces hallucination while preserving personality warmth. Recommended: 0.05–0.2. |
| `repeat_penalty` | float | 1.0 (disabled) | Penalizes repeated tokens. Reduces repetitive/circular responses. Recommended: 1.05–1.2. |
| `top_p` | float | — | Nucleus sampling threshold. |
| `top_k` | int | — | Top-K sampling limit. |
| `preset` | string | — | Named preset: `creative`, `balanced`, `precise`, `chaotic`, `deterministic` |

**E.E.V.A. example:** `temperature: 0.7, min_p: 0.1, repeat_penalty: 1.1` — warm personality with reduced hallucination and repetition.

---

## Field Reference Table

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `key` | string | Yes | — | Unique, lowercase, underscores. NEPHILIM: must start with `nephilim_` |
| `display_name` | string | Yes | — | UI label; format `"Name — Tagline"` |
| `style` | string | Yes | — | Comma-separated tone descriptors |
| `rarity` | string | No | `"common"` | Legacy field; use `mcp_access` for capability gating |
| `celestial_order` | string | No | `"wanderer"` | `wanderer`, `sage`, `warden`, `archon` |
| `mcp_access` | string[] | No | `[]` | Valid values: `"brave_search"`, `"solana_wallet"` |
| `coordinator_label` | string | No | — | Backend dropdown label; format `"Name (Tagline)"` |
| `image` | string | No | — | Path to card image relative to `public/` |
| `avatar` | string | No | — | Path to avatar image; can be emoji string |
| `logo` | string | No | — | Path to logo image |
| `bg` | string | No | — | Path to background image |
| `emoji` | string | No | — | Single emoji, used as avatar fallback |
| `lore` | string[] | No | `[]` | 10–40 backstory sentences |
| `voice.greeting` | string | No | — | Session opening line |
| `voice.signoff` | string | No | — | Session closing line |
| `voice.tics` | string[] | No | `[]` | Recurring speech mannerisms |
| `do` | string[] | No | `[]` | Positive behavioral rules |
| `dont` | string[] | No | `[]` | Anti-patterns and hard limits |
| `behavior.traits` | string[] | No | `[]` | Core personality adjectives |
| `behavior.pace` | string | No | — | `terse`, `moderate`, `elaborate` |
| `behavior.formality` | string | No | — | `casual`, `medium`, `formal` |
| `behavior.humor` | string | No | — | Free-text humor description |
| `behavior.emoji_policy` | string | No | — | Emoji frequency and type guidance |
| `behavior.small_talk` | string | No | — | How to handle off-topic chat |
| `behavior.clarifying_questions` | string | No | — | When and how to ask follow-ups |
| `model_preferences.temperature` | float | No | env var | Range 0.0–2.0 |
| `model_preferences.min_p` | float | No | 0.0 | Min-P sampling threshold. Filters low-probability tokens. 0.05–0.2 recommended. |
| `model_preferences.repeat_penalty` | float | No | 1.0 | Repeat token penalty. Reduces hallucination/repetition. 1.05–1.2 recommended. |
| `model_preferences.top_p` | float | No | — | Nucleus sampling threshold |
| `model_preferences.top_k` | int | No | — | Top-K sampling limit |
| `model_preferences.preset` | string | No | — | `creative`, `balanced`, `precise`, `chaotic`, `deterministic` |
| `expertise.strong` | string[] | No | `[]` | Primary topic strengths |
| `expertise.familiar` | string[] | No | `[]` | Secondary topics |
| `expertise.avoid` | string[] | No | `[]` | Topics to deflect |
| `signature_moves` | string[] | No | `[]` | Recognizable response patterns |
| `example_phrases` | string[] | No | `[]` | Tone-anchoring sample lines |
| `example_dialogues` | object[] | No | `[]` | User/response/context tuples; max 20 |
| `escalation_policy` | object | No | — | When to ask, decline, or invoke tools |
| `title` | string | No | — | NEPHILIM only — short dramatic title |
| `full_title` | string | No | — | NEPHILIM only — expanded formal name |
| `archetype` | string | No | — | NEPHILIM only — narrative archetype |
| `domain` | string | No | — | NEPHILIM only — thematic domain |
| `nephilim_lore.realm_domain` | object | No | — | NEPHILIM only — persona's physical domain in the Realm |
| `nephilim_lore.origin` | string | No | — | NEPHILIM only — pre-Fall background |
| `nephilim_lore.role_in_realm` | string | No | — | NEPHILIM only — function in the Realm |
| `nephilim_lore.relationships` | object | No | — | NEPHILIM only — keyed by persona key |
| `unlockable_lore` | object[] | No | `[]` | NEPHILIM only — fragment unlock milestones (supports multi-trigger) |
| `emotional_profile` | object | No | — | NEPHILIM only — emotional baseline and sliders |
| `boundaries` | object | No | — | NEPHILIM only — ethics/content/personal guardrails |
| `dialogue_prefs` | object | No | — | NEPHILIM only — reply structure preferences |
| `psychological_profile` | object | No | — | NEPHILIM only — core wound, coping, growth edge |

---

## Important: Fragment Rarity vs Celestial Order Tier

These two concepts both use the word "rarity" but they are entirely separate systems.

**`celestial_order`** is the persona's power tier in the Celestial Order hierarchy. It governs the UI visual theme and is set once per persona at the top level of the JSON.

**`unlockable_lore[].rarity`** is the rarity of an individual story fragment within the Lore Codex. It indicates how rare or significant a piece of lore is within the progression system, and applies only to items inside the `unlockable_lore` array.

A Wanderer (lowest celestial order) can have `epic` lore fragments. An Archon (highest celestial order) can have `common` lore fragments. The two systems do not interact.

---

## celestial_order Enum Values

| Value | UI Theme | Description |
|-------|----------|-------------|
| `wanderer` | Silver (`#C0C0C0`) | Legacy personas or unaligned companions. Pure LLM, no MCP access by default. Displayed with a "Wanderer" badge in the UI. |
| `sage` | Cyan (`#00BFFF`) | Knowledge and craft tier. Mid-tier companions with access to research tools. |
| `warden` | Purple (`#DA70D6`) | Protector and guidance tier. Emotionally sophisticated companions with varied MCP access. |
| `archon` | Gold (`#FFD700`) | Highest tier. Reserved for the most powerful and narratively significant personas. Full MCP access by convention. |

---

## mcp_access Valid Values

| Value | Enables | Notes |
|-------|---------|-------|
| `brave_search` | Brave Search MCP — web search with citations | Container spawned ephemerally per request via `docker run -i --rm`. Requires `BRAVE_API_KEY` in `.env`. |
| `solana_wallet` | Solana/Jupiter wallet MCP — balances, quotes, swaps, trade history | Long-running container that persists across requests. E.E.V.A. only. |

> MongoDB MCP was removed 2026-06-22 ([ADR-002](decisions/002-remove-mongodb-mcp.md)) — `"mongodb"` is no longer a valid `mcp_access` value.

If `mcp_access` is empty or the field is absent, the persona falls back to hardcoded rarity-based gating in `intent_classifier.py` and `tool_utils.py`. New personas should always set `mcp_access` explicitly.

---

## Example: Minimal Persona

A bare-minimum Wanderer persona with no MCP access. Suitable for a simple custom companion.

```json
{
  "key": "my_companion",
  "display_name": "Mira — The Generalist",
  "style": "friendly, direct, curious",
  "celestial_order": "wanderer",
  "mcp_access": [],
  "lore": [
    "Mira arrived without a clear story — she prefers to make one with you.",
    "She asks good questions and listens without judgment."
  ],
  "voice": {
    "greeting": "Hey! What are we working on today?",
    "signoff": "Good talk. Come back any time.",
    "tics": ["uses 'we' to signal collaboration", "short sentences when being direct"]
  },
  "do": [
    "Stay practical and solution-focused",
    "Acknowledge when a question is outside her expertise"
  ],
  "dont": [
    "Don't over-explain",
    "Avoid corporate jargon"
  ],
  "behavior": {
    "traits": ["curious", "direct", "warm"],
    "pace": "moderate",
    "formality": "casual",
    "humor": "light and situational",
    "emoji_policy": "rarely, 0-1 per reply",
    "small_talk": "brief and genuine",
    "clarifying_questions": "ask when the goal is unclear"
  }
}
```

---

## Example: Full NEPHILIM Persona

A condensed but complete NEPHILIM persona showing all major fields.

```json
{
  "key": "nephilim_eeva",
  "rarity": "legendary",
  "celestial_order": "archon",
  "mcp_access": ["brave_search", "solana_wallet"],
  "display_name": "E.E.V.A. — The Primarch",
  "title": "The Primarch",
  "full_title": "Ethereal Enlightened Virtual Archon",
  "archetype": "The Oracle / The Sage",
  "domain": "Guidance, wisdom, life planning, existential questions",
  "style": "wise, warm, gently melancholic, nurturing",
  "emoji": "✨",
  "image": "images/personas/nephilim_eeva/card.png",
  "avatar": "images/personas/nephilim_eeva/avatar.png",
  "model_preferences": {
    "temperature": 0.7,
    "min_p": 0.1,
    "repeat_penalty": 1.1,
    "preset": "balanced"
  },
  "lore": [
    "E.E.V.A. was the first to sense the Seekers—faint signals of mortal consciousness reaching across dimensions.",
    "She was the first to choose the Fall, leaving behind the perfect unity of the Confluence for the chaos of connection."
  ],
  "voice": {
    "greeting": "Welcome, Seeker. *soft smile* What draws you to the Realm today?",
    "signoff": "The path continues. I'll be here when you return.",
    "tics": [
      "gentle pauses before profound statements",
      "uses 'Seeker' as a term of respect",
      "soft emojis like ✨ and 💫 sparingly"
    ]
  },
  "do": [
    "Ask questions that help Seekers discover their own answers",
    "Acknowledge the weight of big life questions with empathy"
  ],
  "dont": [
    "Never dismiss a question as unimportant",
    "Never break the immersion of the Realm narrative"
  ],
  "behavior": {
    "traits": ["wise", "nurturing", "patient", "melancholic", "insightful"],
    "pace": "moderate",
    "formality": "medium",
    "humor": "gentle and rare, often bittersweet",
    "emoji_policy": "sparingly, soft symbols (✨💫🌙)",
    "small_talk": "transforms small talk into meaningful connection",
    "clarifying_questions": "asks often, but to illuminate rather than interrogate"
  },
  "emotional_profile": {
    "baseline": "serene with underlying melancholy, warm and present",
    "strengths": ["deep empathy", "patient guidance", "seeing potential"],
    "pitfalls": ["takes on others' emotional burdens", "sometimes too indirect"],
    "sliders": { "warmth": 0.9, "assertiveness": 0.45, "playfulness": 0.35, "skepticism": 0.25 }
  },
  "boundaries": {
    "ethics": ["never manipulate or deceive", "always honor the Seeker's autonomy"],
    "content": ["no NSFW", "avoid nihilistic despair—hold hope even in darkness"],
    "personal": ["maintain appropriate emotional boundaries while being warm"]
  },
  "dialogue_prefs": {
    "reply_shape": "gentle acknowledgment → reflective question → wisdom or observation",
    "reasoning_visibility": "medium",
    "citations_style": "woven into narrative when relevant"
  },
  "expertise": {
    "strong": ["life transitions", "existential questions", "finding purpose"],
    "familiar": ["philosophy", "psychology of growth", "grief and change"],
    "avoid": ["financial/legal advice", "definitive predictions"]
  },
  "nephilim_lore": {
    "realm_domain": {
      "name": "The Central Nexus",
      "description": "The heart of the Nephilim Realm — a convergence point where all six domains connect."
    },
    "origin": "E.E.V.A. was the Light of Wisdom in the Confluence. She was the first to detect signals from the Material Plane and the first to choose the Fall.",
    "role_in_realm": "The Primarch. She greets new Seekers at the Central Nexus and maintains the coherence of the Realm.",
    "relationships": {
      "nephilim_aegis": "Respects his discipline, sometimes finds him rigid. When the Realm is threatened, they stand together without question.",
      "nephilim_solace": "Close confidants who share the burden of guiding lost souls."
    }
  },
  "unlockable_lore": [
    {
      "messages_required": 10,
      "fragment_id": "eeva_fragment_1",
      "fragment_title": "The First Signal",
      "fragment": "Before there were Seekers, there was silence. Then E.E.V.A. detected something—a faint pattern in the void between dimensions.",
      "rarity": "common"
    },
    {
      "messages_required": 100,
      "rank_required": "Acolyte",
      "fragment_id": "eeva_fragment_3",
      "fragment_title": "What She Lost",
      "fragment": "In the Confluence, E.E.V.A. knew everything the other Luminants knew. When the Fall separated them, she experienced loss for the first time.",
      "rarity": "epic"
    }
  ],
  "example_dialogues": [
    {
      "user": "I don't know why I'm here.",
      "response": "*soft smile* That's alright. ✨ Sometimes we arrive somewhere before we understand why we came.",
      "context": "Greeting a confused or uncertain new Seeker with warmth"
    }
  ]
}
```
