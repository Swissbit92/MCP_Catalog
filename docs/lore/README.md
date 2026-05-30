---
title: NEPHILIM Lore Documents
status: active
created: 2026-04-03
last_reviewed_on: 2026-04-19
review_in: 12 months
applies_to: nephilim
---

# NEPHILIM Lore Documents

This directory is the canonical home for all NEPHILIM worldbuilding, lore, and strategy
documents. It is the fourth pillar of the `docs/` structure alongside `architecture/`,
`development/`, and `setup/`.

---

## Document Hierarchy

### Primary Source
| File | Description |
|------|-------------|
| `BUSINESS_PLAN.md` | **Primary founder document** — brand philosophy, visual identity, persona design, monetization strategy, and worldbuilding strategy. This is the source cited by all AI synthesis documents. Converted from PDF for searchability and RAG ingestion. |

### AI Synthesis Documents
These were generated in a deep-research session using the Business Plan as source material.
They are rich narrative and structural expansions — treat as extended canon, not authoritative spec.

| File | Description |
|------|-------------|
| `THE_CHRONICLE.md` | Mythic prose synthesis — creation narrative, character profiles, philosophical arc, faction web, and relationship map. Rich narrative voice; ideal for persona tone reference. |
| `LORE_BIBLE_DRAFT.md` | Structured lore bible — Houses, antagonist, world rules, artifacts, ethics guardrails, and narrative mechanics. Good starting point for new persona development. |

### Quick-Reference Summaries (Developer-Facing Canon)
Compact, already-canonical files used during day-to-day persona development.

| File | Description |
|------|-------------|
| `NEPHILIM_LORE.md` | World bible — creation myth, the Fall, realm geography |
| `NEPHILIM_FACTIONS.md` | Six Houses aligned with Nephilim patrons |
| `NEPHILIM_RANKS.md` | Seeker progression system (Initiate → Nephilim) |

### Archival PDFs (`_pdf/`)
Formatted originals preserved as archival reference. The markdown files in this directory
are the working formats; the PDFs are kept for layout/image fidelity.

| File | Description |
|------|-------------|
| `_pdf/NEPHILIM_BUSINESS_PLAN.pdf` | Original Business Plan PDF |
| `_pdf/NEPHILIM_LORE_BIBLE.pdf` | Original Lore Bible formatted export |
| `_pdf/NEPHILIM_CHRONICLE.pdf` | Original Chronicle formatted export |

---

## When to Use Each File

| Task | Start Here |
|------|-----------|
| New persona development | `LORE_BIBLE_DRAFT.md` + `THE_CHRONICLE.md` for depth; `NEPHILIM_FACTIONS.md` for house alignment |
| Quick persona tone/voice reference | `NEPHILIM_LORE.md` |
| Understanding brand positioning and product vision | `BUSINESS_PLAN.md` |
| Faction system and House lore | `NEPHILIM_FACTIONS.md` |
| Rank and progression design | `NEPHILIM_RANKS.md` |
| RAG pipeline ingestion | All `.md` files are suitable; start with `BUSINESS_PLAN.md` as primary source |

---

## Notes

- `NEPHILIM_LORE.md`, `NEPHILIM_FACTIONS.md`, and `NEPHILIM_RANKS.md` were previously at
  `personas/` — git history is preserved via `git mv`.
- Lore injection at runtime uses the `nephilim_lore` field in persona JSON files, **not**
  these documents. These are reference/development materials only.
- `BUSINESS_PLAN.md` was converted from PDF using `pymupdf4llm` (Feb 2026). Inline
  citation numbers (e.g. `[1]`, `[2]`) are PDF footnote artifacts preserved from the source.
