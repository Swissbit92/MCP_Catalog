---
title: On-demand hybrid lore retrieval + internal capabilities
status: Accepted
created: 2026-06-26
last_reviewed_on: 2026-06-26
review_in: 12 months
applies_to: nephilim
---

# ADR-003: On-demand hybrid lore retrieval + internal capabilities

## Status

Accepted (HERMES-Agents Phase 2). Shipped behind `LORE_ONDEMAND_ENABLED` (default OFF).

## Context

Lore reached the model only via a hardcoded 3-entity-per-persona prefill
(`lore_loader._PERSONA_ENTITIES`: persona + house + location, ~800–900 tokens),
statically injected into `<world_context>` and cached per-persona. Of the 34 typed
wiki entities, **16 (8 NPCs, 5 ranks, 2 concepts, 1 faction) had no injection path
at all** — authored lore the persona could never reference. There was also no notion
of "skills"/capabilities beyond `mcp_access` tool gating, and two latent progression
bugs: `affinity_level` was never incremented (so `affinity_required` lore triggers
could never fire), and seeker rank was never surfaced to the model.

The HERMES-Agents track (see [VISION.md](../../../VISION.md)) called for on-demand
lore/skill loading. Research (SillyTavern World Info, Character Card V2, Anthropic
Skills, RoleRAG/AMADEUS/DualMem) favoured a hybrid keyword+embedding approach, and
both community and game-design evidence favoured **internal/diegetic** capabilities
over user-invokable command menus for a companion.

## Decision

1. **Hybrid per-turn lore retrieval**, appended to the system prompt *after* the
   `lru_cache`d `build_system_prompt` (mirroring the existing `unlocked_lore`
   injection — never inside the cached function). Tier-1 deterministic alias/keyword
   match; Tier-2 bge-m3 semantic search (`memory_rag.search_lore`, reusing the RAG
   embedder, `canon_only=True`). Deduped vs the static core; trimmed to a token budget.
2. **Keep the static 3-entity core**; retrieval adds on top (safer rollback, no
   immersion regression).
3. **Capabilities are internal** `entity_type: capability` wiki entries gated by
   persona + rank + affinity (`lore_retrieval.py`). Never user-invokable. A brief
   **diegetic** unlock toast (persona voice, outside chat) fires via
   `response.metadata.capability_unlocks` — the gamification beat without a skill menu.
4. **Progression fixes**: `increment_affinity` (deepens after a drive-by gate; awards
   milestone resonance once) and an optional seeker-rank prompt block
   (`LORE_RANK_CONTEXT_ENABLED`).
5. **Flag-gated**: `LORE_ONDEMAND_ENABLED=false` keeps prompt construction
   byte-identical to pre-Phase-2.

## Consequences

- **Positive**: the 16 dormant entities are reachable (validated: a "resonance/
  ascension" query surfaces the concept/rank entities; golden-set recall 0.94 at the
  0.50 floor); richer, query-appropriate lore without permanent prompt bloat;
  capabilities give personas rank/affinity-aware depth; the affinity bug is fixed.
- **Negative / risks**: per-turn embed adds ~30–120 ms (mitigated by the keyword
  fast-path, the budget cap, and flag-default-off); non-canon draft NPCs only surface
  via keyword if aliases are populated (content follow-up); capability narrative
  content must be authored per persona (2 examples shipped).
- **Reversibility**: a single env flag; no schema/data migration.

## Alternatives considered

- **Replace the static core with retrieval** — rejected for Phase 2 (riskier rollback,
  immersion regression potential); revisit after live data.
- **Mean-centroid lore matching** — rejected; the Phase-0 routing work showed centroid
  smear. Per-entity vectors (one per wiki entity) sidestep it here.
- **User-facing/invokable skills** — rejected on immersion grounds (companion would
  feel like a game menu); internal + diegetic chosen instead.
