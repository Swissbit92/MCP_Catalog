---
title: Lore as typed-markdown-wiki not a graph DB
status: Accepted
created: 2026-05-29
last_reviewed_on: 2026-05-29
review_in: 12 months
applies_to: nephilim
---

# ADR-001: Lore as typed-markdown-wiki not a graph DB

## Status

Accepted

## Context

NEPHILIM's worldbuilding lived in six monolithic markdown files under `docs/lore/` (BUSINESS_PLAN, THE_CHRONICLE, LORE_BIBLE_DRAFT, NEPHILIM_LORE, NEPHILIM_FACTIONS, NEPHILIM_RANKS) with no schema, no cross-links, and no validation. This produced real drift: two incompatible house-naming systems, three names for the antagonist, eight Chronicle-only entities, and a corrupted README. The lore is hand-authored creative canon and — verified — is not consumed at runtime (personas draw lore from `personas/*.json`, assembled in `prompt_builder.py`).

Typed relationships between entities were needed (patrons, oppositions, locations). The obvious question: use a graph database (Neo4j)?

## Decision

Adopt a **typed-markdown-wiki** (OmegaWiki / Karpathy "LLM-Wiki" pattern). Each entity is one markdown file under `docs/lore/wiki/` with YAML frontmatter declaring `entity_type`, `entity_id`, `canon`, `aliases`, and typed `relationships`. Markdown is the single source of truth. A small Python engine (`scripts/utils/lore_wiki.py`) validates the graph (`check`) and regenerates the index (`index`); a graph is derived on demand (`graph`, networkx), never stored separately.

**Do NOT introduce Neo4j (or any graph DB) for this.**

## Consequences

Easier: git-diffable / PR-reviewable / editable canon; entities load individually (cheap for a local Ollama context); CI-gateable integrity (dangling links, missing inverses, alias collisions, persona↔JSON consistency, prose name-drift); zero new runtime infrastructure.

Harder: multi-hop traversal must be derived in code rather than queried in Cypher; authoring is manual file creation. Both are acceptable at current scale (~30 entities).

## Alternatives Considered

- **Neo4j / graph DB** — rejected: opaque binary store breaks git-native authoring; another always-on service violates "simplicity at solo scale"; overkill for ~30 nodes; MongoDB `$graphLookup` is available if querying is ever needed; the LLM consumes lore as text, so files avoid a serialisation round-trip.
- **Leave monolithic docs as-is** — rejected: the drift that motivated this work would recur with no mechanism to catch it.

If multi-hop traversal becomes the primary access pattern or the graph grows to thousands of densely-linked nodes, escalation path is: networkx in-memory → MongoDB `$graphLookup` → Neo4j read-only projection — keeping markdown canonical throughout.

## References

- `scripts/utils/lore_wiki.py` — the wiki engine
- [`docs/lore/wiki/`](../lore/wiki/) — the entity graph
- [`docs/lore/README.md`](../lore/README.md) — lore directory map
