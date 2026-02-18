# API Reference

## Overview

- **Base URL:** `http://localhost:8000`
- **Auth:** Local-only development — no API keys required
- **Content Type:** All request and response bodies are JSON (`application/json`)
- **Errors:** Error responses return `{ "detail": "..." }` with an appropriate HTTP status code
- **Interactive Docs:** Swagger UI available at `http://localhost:8000/docs`; ReDoc at `http://localhost:8000/redoc`
- **CORS:** Allowed origins are `http://localhost:3000` and `http://localhost:3001`

---

## Chat Endpoints

Source: `src/coordinator/routes/chat.py`

### `POST /persona/greet`

Generate an opening greeting from a persona. Does not require or create a session.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `persona` | string | No | Persona key (e.g. `nephilim_eeva`). Defaults to first loaded persona. |

**Response:**

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string or array | Single string, or array of strings for multi-message greetings |
| `message_flow` | string | `"single"` or `"multi"` |
| `message_count` | integer | Number of messages in the response |
| `rewritten` | boolean | Whether first-person post-processing was applied |

**Errors:**
- `400` — Unknown persona key

---

### `POST /persona/chat`

Chat with a persona using an inline conversation history. Does not persist messages to the database. Automatically routes through web search (Brave) or trading data (MongoDB) tools based on the persona's `mcp_access` configuration and query intent.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `persona` | string | No | Persona key. Defaults to first loaded persona. |
| `message` | string | Yes | User message. Max 10,000 characters. |
| `history` | array | No | Prior conversation turns. Max 100 entries. Each entry is `{ "role": "user"\|"assistant", "content": "..." }`. |

**Response:**

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string or array | Persona reply; array when `message_flow` is `"multi"` |
| `message_flow` | string | `"single"` or `"multi"` |
| `message_count` | integer | Number of messages in the response |
| `used_search` | boolean | Whether a web search tool was invoked |
| `rewritten` | boolean | Whether first-person post-processing was applied |
| `metadata` | object | See `ResponseMetadata` below |

**`metadata` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `source_type` | string | `"llm"`, `"brave_mcp"`, `"mongodb_mcp"`, or `"multi_mcp"` |
| `tools_used` | array | List of tool names that were called |
| `cache_status` | string or null | `"hit"`, `"miss"`, or `null` |
| `data_timestamp` | string or null | ISO timestamp of external data, if applicable |
| `latency_breakdown` | object or null | Per-service latency in ms, e.g. `{ "llm": 3000, "mongodb": 500 }` |
| `is_multi_message` | boolean | Whether the response was split into multiple messages |
| `message_count` | integer | Number of messages in the response |

**Errors:**
- `400` — Unknown persona key

---

### `POST /sessions/{session_id}/chat`

Chat with a persona using the database-backed session history. Messages are automatically persisted to SQLite. Awards NEPHILIM resonance after each exchange if applicable.

**Path parameter:** `session_id` — UUID of an existing session.

**Request body:** Same as `POST /persona/chat` (`persona`, `message`, `history`). The `history` field is supplemented by the stored session history.

**Response:** Same shape as `POST /persona/chat`.

**Errors:**
- `404` — Session not found
- `400` — Unknown persona key

---

## Session Endpoints

Source: `src/coordinator/routes/sessions.py`

### `GET /sessions`

List all chat sessions.

**Response:** Array of session objects.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Session UUID |
| `persona_key` | string | Associated persona key |
| `title` | string | Session title |
| `created_at` | string | ISO timestamp |
| `updated_at` | string | ISO timestamp |
| `message_count` | integer | Total messages in session |

---

### `POST /sessions`

Create a new chat session.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `persona_key` | string | Yes | Persona key to associate with this session |
| `title` | string | No | Session title. Defaults to `"New Chat"`. |

**Response:** The newly created session object (same fields as `GET /sessions` items) with `message_count: 0`.

---

### `GET /sessions/{session_id}`

Get a session with all its messages.

**Path parameter:** `session_id`

**Response:**

| Field | Type | Description |
|-------|------|-------------|
| `session` | object | Session metadata including `message_count` |
| `messages` | array | Ordered list of message objects |

Each message object:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Message UUID |
| `role` | string | `"user"` or `"assistant"` |
| `content` | string | Message text |
| `timestamp` | string | ISO timestamp |
| `latency_ms` | integer or null | Response time in ms (assistant messages only) |
| `source_type` | string | `"llm"`, `"brave_mcp"`, `"mongodb_mcp"`, or `"multi_mcp"` |

**Errors:**
- `404` — Session not found

---

### `PUT /sessions/{session_id}`

Rename a session.

**Path parameter:** `session_id`

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | New title. Blank values are stored as `"Untitled"`. |

**Response:**

```json
{ "ok": true, "id": "...", "title": "...", "updated_at": "..." }
```

**Errors:**
- `404` — Session not found

---

### `DELETE /sessions/{session_id}`

Permanently delete a session and all its messages (cascade).

**Path parameter:** `session_id`

**Response:**

```json
{ "ok": true }
```

**Errors:**
- `404` — Session not found

---

### `POST /sessions/{session_id}/messages`

Append a message to a session. Typically called internally after a chat response, but can be used directly to inject messages.

**Path parameter:** `session_id`

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `role` | string | Yes | `"user"` or `"assistant"` |
| `content` | string | Yes | Message text |
| `ts` | string | No | ISO timestamp. Defaults to server time. |
| `latency_ms` | integer | No | Response latency in ms |
| `source_type` | string | No | Source identifier. Defaults to `"llm"`. |
| `multi_message_id` | string | No | Group ID for multi-message sequences |
| `multi_message_index` | integer | No | Position within a multi-message sequence |

**Response:**

```json
{ "ok": true, "message_id": "..." }
```

**Errors:**
- `404` — Session not found

---

### `DELETE /sessions/{session_id}/messages`

Clear all messages from a session without deleting the session itself. Also resets the emotional state for the session.

**Path parameter:** `session_id`

**Response:**

```json
{ "ok": true }
```

**Errors:**
- `404` — Session not found

---

### `GET /sessions/{session_id}/emotional-state`

Get the current emotional state tracked for a session. State is created on first access.

**Path parameter:** `session_id`

**Response:**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Session UUID |
| `trust_level` | number | Current trust level (0.0–1.0) |
| `rapport` | number | Rapport score |
| `current_mood` | string | Current emotional mood label |
| `mood_intensity` | number | Intensity of current mood (0.0–1.0) |
| `last_emotional_event` | string or null | Description of the last notable emotional event |
| `updated_at` | string | ISO timestamp |

**Errors:**
- `404` — Session not found

---

### `POST /sessions/{session_id}/greet`

Generate a greeting tied to the session's persona and save it as an assistant message in the session.

**Path parameter:** `session_id`

**Request body:** `{ "persona": "..." }` (optional; ignored — the session's own persona key is used)

**Response:** Same shape as `POST /persona/greet`.

**Errors:**
- `404` — Session not found

---

### `GET /sessions/{session_id}/export`

Export a session as a portable JSON object.

**Path parameter:** `session_id`

**Response:**

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Export format version (`"1.0"`) |
| `exported_at` | string | ISO timestamp of export |
| `app_version` | string | Application version |
| `persona` | object | Persona metadata (`key`, `display_name`, `style`) |
| `session` | object | Session metadata |
| `messages` | array | All messages in the session |

**Errors:**
- `404` — Session not found
- `400` — Persona for this session no longer exists

---

### `POST /sessions/import`

Import a previously exported session.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `data` | object | Yes | A valid export payload from `GET /sessions/{id}/export` |
| `create_new_session` | boolean | No | If `true` (default), ignores the original session ID and creates a new one. |

**Response:**

```json
{ "ok": true, "session_id": "..." }
```

**Errors:**
- `400` — Missing required fields in export data, or persona not found

---

## Persona Endpoints

Source: `src/coordinator/routes/personas.py`

### `GET /personas`

List all available personas with their metadata. Response is cached for 30 seconds.

**Response:** Array of persona objects.

| Field | Type | Description |
|-------|------|-------------|
| `key` | string | Unique persona identifier (e.g. `nephilim_eeva`) |
| `display_name` | string | Human-readable name |
| `style` | string | Short style/tone description |
| `rarity` | string | Rarity tier (`common`, `rare`, `epic`, `legendary`) |
| `celestial_order` | string | Celestial order tier (`wanderer`, `sage`, `warden`, `archon`) |
| `mcp_access` | array | List of enabled MCP tools (e.g. `["brave_search", "mongodb"]`) |
| `coordinator_label` | string or null | Optional display label override |
| `image` | string or null | Path to card image |
| `avatar` | string or null | Path to avatar image |
| `bg` | string or null | Path to background image |
| `voice` | object or null | Voice configuration metadata |

**Errors:**
- `500` — Failed to load persona definitions from disk

---

### `POST /persona/summary`

Return the CV-style summary for a persona. The summary is cached and rebuilt only when the persona JSON changes.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `persona` | string | No | Persona key. Defaults to first loaded persona. |

**Response:**

| Field | Type | Description |
|-------|------|-------------|
| `key` | string | Persona key |
| `hash` | string | Hash of the source persona JSON |
| `updated` | string | ISO timestamp of last build |
| `summary` | string | The generated CV-style summary text |

**Errors:**
- `500` — Failed to build or retrieve summary

---

## NEPHILIM Progression Endpoints

Source: `src/coordinator/routes/nephilim.py` — all paths prefixed with `/nephilim`

### `GET /nephilim/seeker/{user_id}`

Get a seeker's profile. Creates a new profile automatically if one does not exist.

**Path parameter:** `user_id` — Seeker identifier (stored in localStorage as `nephilim_user_id`)

**Response (`SeekerProfileResponse`):**

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | string | Seeker identifier |
| `rank_name` | string | Current rank (e.g. `"Initiate"`) |
| `total_resonance` | integer | Lifetime resonance earned |
| `faction_primary` | string or null | Primary house affiliation |
| `faction_secondary` | string or null | Secondary house affiliation |
| `rank_achieved_at` | string or null | ISO timestamp when current rank was reached |
| `created_at` | string | ISO timestamp of profile creation |
| `updated_at` | string | ISO timestamp of last update |

**Errors:**
- `503` — Progression system not initialized

---

### `GET /nephilim/seeker/{user_id}/summary`

Get a comprehensive overview of the seeker including rank, resonance, all affinities, and unlocked lore count.

**Path parameter:** `user_id`

**Response (`SeekerSummaryResponse`):**

| Field | Type | Description |
|-------|------|-------------|
| `exists` | boolean | Whether the profile exists |
| `user_id` | string | Seeker identifier |
| `rank` | string or null | Current rank name |
| `total_resonance` | integer or null | Lifetime resonance |
| `faction_primary` | string or null | Primary faction |
| `faction_secondary` | string or null | Secondary faction |
| `rank_progress` | object or null | `RankProgressResponse` (see below) |
| `persona_affinities` | array | List of `PersonaAffinityResponse` objects |
| `unlocked_lore_count` | integer | Total lore fragments unlocked |
| `created_at` | string or null | Profile creation timestamp |
| `updated_at` | string or null | Last update timestamp |

---

### `POST /nephilim/seeker/{user_id}/faction`

Set or update a seeker's faction affiliation.

**Path parameter:** `user_id`

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `faction_primary` | string | Yes | Must be one of: `lumina`, `ironclad`, `sanctuary`, `prism`, `archive`, `horizon` |
| `faction_secondary` | string | No | Optional secondary faction from the same set |

**Response:**

```json
{ "status": "success", "faction_primary": "lumina" }
```

**Errors:**
- `400` — Invalid faction name
- `404` — Seeker not found
- `503` — Progression system not initialized

---

### `GET /nephilim/seeker/{user_id}/rank`

Get the seeker's current rank and progress toward the next rank.

**Path parameter:** `user_id`

**Response (`RankProgressResponse`):**

| Field | Type | Description |
|-------|------|-------------|
| `current_rank` | string | Current rank name |
| `current_resonance` | integer | Current total resonance |
| `next_rank` | string or null | Next rank name (`null` if at max rank) |
| `resonance_needed` | integer | Resonance required to reach next rank |
| `progress_percent` | integer | Progress toward next rank as a percentage (0–100) |

---

### `POST /nephilim/seeker/{user_id}/resonance`

Award resonance points to a seeker. Called automatically by the chat system (5 points per exchange) but available for manual use.

**Path parameter:** `user_id`

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `amount` | integer | Yes | Points to award. Must be positive. |
| `reason` | string | Yes | Description of why resonance was awarded |
| `persona_key` | string | No | Persona involved in the exchange |
| `session_id` | string | No | Session associated with the award |

**Response:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `"success"` |
| `new_resonance` | integer | Updated total resonance |
| `new_rank` | string | Current rank after award |
| `rank_changed` | boolean | Whether a rank-up occurred |
| `previous_rank` | string or null | Prior rank if `rank_changed` is true |

**Errors:**
- `400` — Amount must be positive
- `503` — Progression system not initialized

---

### `GET /nephilim/seeker/{user_id}/resonance/history`

Get the seeker's recent resonance award history.

**Path parameter:** `user_id`

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | `50` | Number of events to return. Min 1, max 200. |

**Response:**

```json
{ "events": [ { ... } ] }
```

Each event includes the amount, reason, persona key, session ID, and timestamp.

---

### `GET /nephilim/seeker/{user_id}/affinity`

Get all persona affinity records for a seeker.

**Path parameter:** `user_id`

**Response:** Array of `PersonaAffinityResponse` objects.

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | string | Seeker identifier |
| `persona_key` | string | Persona identifier |
| `messages_count` | integer | Total messages exchanged with this persona |
| `affinity_level` | integer | Current affinity tier (increases with `messages_count`) |
| `first_conversation` | string or null | ISO timestamp of first exchange |
| `last_conversation` | string or null | ISO timestamp of most recent exchange |

---

### `GET /nephilim/seeker/{user_id}/affinity/{persona_key}`

Get the affinity record for one specific persona. Creates the record if it does not exist.

**Path parameters:** `user_id`, `persona_key`

**Response:** Single `PersonaAffinityResponse` object (same fields as above).

---

### `GET /nephilim/seeker/{user_id}/lore`

Get all unlocked lore fragments for a seeker.

**Path parameter:** `user_id`

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `persona_key` | string | None | Filter results to a single persona |

**Response:** Array of `UnlockedLoreResponse` objects.

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Record ID |
| `user_id` | string | Seeker identifier |
| `persona_key` | string | Persona associated with the fragment |
| `fragment_id` | string | Fragment identifier |
| `unlocked_at` | string | ISO timestamp of unlock |

---

### `GET /nephilim/seeker/{user_id}/lore/{persona_key}/full`

Get all lore fragments for a persona with full content and unlock status. Locked fragments return a placeholder string instead of the actual content.

**Path parameters:** `user_id`, `persona_key`

**Response:** Array of `LoreFragmentContent` objects.

| Field | Type | Description |
|-------|------|-------------|
| `fragment_id` | string | Fragment identifier |
| `fragment_title` | string | Display title |
| `fragment` | string | Content text, or `"[Locked - Requires more conversations]"` |
| `messages_required` | integer | Message threshold needed to unlock |
| `rarity` | string | Fragment rarity (`common`, `rare`, `epic`) |
| `unlocked` | boolean | Whether the seeker has unlocked this fragment |
| `unlocked_at` | string or null | ISO timestamp of unlock, if applicable |

**Errors:**
- `404` — Persona not found

---

### `POST /nephilim/seeker/{user_id}/lore/{persona_key}/check`

Check and unlock any lore fragments the seeker has now met the message threshold for. Typically called automatically after a conversation.

**Path parameters:** `user_id`, `persona_key`

**Response:**

| Field | Type | Description |
|-------|------|-------------|
| `newly_unlocked` | integer | Count of newly unlocked fragments |
| `fragments` | array | Details of each newly unlocked fragment (`fragment_id`, `fragment_title`, `fragment`, `rarity`) |

**Errors:**
- `404` — Persona not found

---

### `GET /nephilim/ranks`

Get all rank tiers and their resonance thresholds. Read-only reference data.

**Response:**

```json
{
  "ranks": [
    { "name": "Initiate", "resonance_required": 0 },
    { "name": "Acolyte",  "resonance_required": 100 },
    { "name": "Adept",    "resonance_required": 500 },
    { "name": "Ascendant","resonance_required": 2000 },
    { "name": "Nephilim", "resonance_required": 10000 }
  ]
}
```

---

### `GET /nephilim/factions`

Get all faction/house definitions. Read-only reference data.

**Response:**

```json
{
  "factions": [
    {
      "key": "lumina",
      "name": "House Lumina",
      "patron": "E.E.V.A.",
      "values": "Wisdom, mentorship, philosophical inquiry",
      "color": "#e0c3fc"
    },
    ...
  ]
}
```

Available factions: `lumina`, `ironclad`, `sanctuary`, `prism`, `archive`, `horizon`.

---

## Error Conventions

| Status | Meaning |
|--------|---------|
| `400` | Bad request — invalid input (unknown persona, invalid faction, malformed import data) |
| `404` | Not found — session, persona, or seeker does not exist |
| `422` | Unprocessable entity — Pydantic validation failure (missing required field, wrong type, value out of range) |
| `500` | Internal server error — unexpected failure; `detail` contains the error message |
| `503` | Service unavailable — a required subsystem (e.g. progression repository) failed to initialize |

All error bodies follow the FastAPI convention:

```json
{ "detail": "Human-readable description of the error." }
```

Validation errors (`422`) return a structured body:

```json
{
  "detail": [
    { "loc": ["body", "field_name"], "msg": "...", "type": "..." }
  ]
}
```

---

## Notes

- **Interactive docs:** `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc` (ReDoc) provide live, explorable documentation generated from the OpenAPI schema.
- **Multi-message responses:** Some replies are split into multiple sequential messages (simulating a more natural conversation rhythm). When `message_flow` is `"multi"`, the `answer` field is an array of strings rather than a single string.
- **MCP tool routing:** `POST /persona/chat` and `POST /sessions/{session_id}/chat` automatically decide whether to invoke Brave Search, MongoDB, both, or neither based on the persona's `mcp_access` field and the classified intent of the user's message.
- **Persona discovery:** Personas are loaded from JSON files in the `personas/` directory. Changes to those files are picked up on the next request without requiring a server restart (30-second cache).
- **Resonance automation:** The session chat endpoint awards 5 resonance points automatically after each exchange with a NEPHILIM persona. The `POST /nephilim/seeker/{user_id}/resonance` endpoint is available for manual awards or corrections.
