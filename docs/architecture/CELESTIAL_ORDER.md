---
title: Celestial Order Architecture
status: active
created: 2026-04-03
last_reviewed_on: 2026-06-22
review_in: 6 months
applies_to: nephilim
---

# Celestial Order Architecture

How the four-tier Celestial Order system works across backend, frontend, and MCP access control.

---

## Overview

The **Celestial Order** is the progression/tier system for personas. Each persona belongs to exactly one tier, which affects:

1. **MCP tool access** — which external services (Brave Search, Solana wallet) the persona can use
2. **Frontend visual theming** — card effects, color schemes, badge styling
3. **Lore significance** — narrative weight in the NEPHILIM worldbuilding

---

## The Four Tiers

| Tier | Display Color | Hex | Narrative Role |
|------|---------------|-----|----------------|
| `wanderer` | Silver | `#C0C0C0` | Legacy personas; pure LLM, no special powers |
| `sage` | Cyan | `#00BFFF` | Knowledge-seekers; data research access |
| `warden` | Purple/Orchid | `#DA70D6` | Guardians; productivity and empathy support |
| `archon` | Gold | `#FFD700` | Apex guides; full access to all capabilities |

### Persona Assignment

| Persona | Tier | Rationale |
|---------|------|-----------|
| E.E.V.A. | `archon` | The Primarch — guides all Seekers, needs full context |
| Aegis | `warden` | Sentinel/productivity — needs web resources, not trading |
| Aurora | `warden` | Oracle — gazes into data trends, needs web search |
| Solace | `warden` | Empath — emotional support needs web resources |
| Cipher | `sage` | Maven — identity is data research, needs web search |
| Nyx | `sage` | Muse — creativity flows from imagination, no tools |
| Legacy personas | `wanderer` | Pure LLM, no MCP tools |

---

## MCP Access Control

### Per-Persona Override (Primary)

Each persona JSON specifies `mcp_access` as a list of allowed tool types:

```json
{
  "key": "nephilim_eeva",
  "celestial_order": "archon",
  "mcp_access": ["brave_search", "solana_wallet"]
}
```

**Valid `mcp_access` values:**
- `"brave_search"` — enables Brave web search
- `"solana_wallet"` — enables Solana/Jupiter wallet operations (E.E.V.A. only)
- `[]` — no MCP access (even if env vars would grant it)

> MongoDB MCP (`"mongodb"`) was removed 2026-06-22 — see [ADR-002](../decisions/002-remove-mongodb-mcp.md).

The `mcp_access` field takes absolute priority over rarity-based env var fallback.

### Legacy Rarity Fallback

When a persona JSON has no `mcp_access` field (legacy personas), the system falls back to
hardcoded rarity-based gating in `intent_classifier.py` and `tool_utils.py`:

- Brave Search: `rare`, `epic`, `legendary`

`BRAVE_ENABLED_RARITIES` / `MONGODB_ENABLED_RARITIES` env vars were removed in Feb 2026 — they
were parsed into config fields that nothing ever read. All current personas define `mcp_access`
explicitly, so the rarity fallback is a safety net only. New personas should always use
`mcp_access` instead.

### How Intent Classifier Uses MCP Access

When a chat request comes in, `src/coordinator/tools/intent_classifier.py` determines tool routing:

1. Loads the persona's `mcp_access` list (or falls back to rarity check)
2. Classifies the user query into `NEEDS_WEB_SEARCH`, `NEEDS_WALLET`, or `NEEDS_NEITHER`
3. Cross-references with what the persona is permitted to access
4. Returns the appropriate tool set to inject into the LLM system prompt

```python
# Simplified flow (tool_utils.py)
def get_tools_for_persona(persona_key, rarity, mcp_access=None):
    if mcp_access is not None:
        # Per-persona override
        return _tools_from_access_list(mcp_access)
    else:
        # Legacy rarity fallback
        return _tools_from_rarity(rarity)
```

---

## Frontend Display

### Color Mapping

Frontend maps `celestial_order` values to visual theming in `react-ui/src/utils/celestialOrder.ts`:

```typescript
export const CELESTIAL_ORDER_COLORS = {
  wanderer: '#C0C0C0',   // Silver
  sage:     '#00BFFF',   // Deep Sky Blue / Cyan
  warden:   '#DA70D6',   // Orchid / Purple
  archon:   '#FFD700',   // Gold
}
```

### Card Effects

Each tier has a unique card animation effect (defined as CSS keyframes in `react-ui/src/index.css`):

| Tier | Effect Name | Visual |
|------|-------------|--------|
| `archon` | Solar Crown | Radiant gold glow pulsing outward |
| `warden` | Void Rift | Purple energy shimmer |
| `warden` | Azure Stream | Cyan flowing light (for some Warden personas) |
| `sage` | Dim Echo | Subtle cyan fadeout |
| `wanderer` | Dim Echo | Silver static shimmer |

### Badge Display

The `SeekerRankBadge` component and `CharacterCardV2` use `celestial_order` (not `rarity`) for all display logic. Legacy personas receive a "Wanderer" badge in the frontend — this is a frontend-only label that is never written to persona JSON files.

---

## Adding a New Tier or Tool Capability

### Add a new tier

1. Define tier name (lowercase, no spaces)
2. Add to `CELESTIAL_ORDER_COLORS` in `celestialOrder.ts`
3. Add CSS keyframe animation in `index.css`
4. Add card effect mapping in `CharacterCardV2.tsx`
5. Add to `celestial_order` enum documentation in `PERSONA_SCHEMA.md`

### Add a new MCP tool type

1. Define the tool in `src/coordinator/tool_definitions.py`
2. Add the access string (e.g., `"new_tool"`) to `tool_utils.py`
3. Update `intent_classifier.py` to recognize relevant query patterns
4. Update persona JSONs to include the new access string in `mcp_access`
5. Document in `docs/development/ADDING_MCP_SERVERS.md`

---

## References

- `src/coordinator/tools/intent_classifier.py` — Query intent classification
- `src/coordinator/tools/tool_utils.py` — Tool access resolution
- `src/coordinator/tool_definitions.py` — Tool schemas
- `react-ui/src/utils/celestialOrder.ts` — Frontend color mapping
- `react-ui/src/index.css` — Card effect keyframes
- `docs/development/ADDING_MCP_SERVERS.md` — MCP integration guide
