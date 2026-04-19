---
title: Lore Deep-Dive: Implementation Plan & Progress Tracker
status: completed
created: 2026-04-04
last_reviewed_on: 2026-04-19
review_in: 24 months
applies_to: MCP_Catalog
---

# Lore Deep-Dive: Implementation Plan & Progress Tracker

> **Created:** 2026-03-01
> **Last Updated:** 2026-03-01
> **Status:** Features 1A, 2A, 2B, 2C implemented (Mar 1 2026). 1B, 2D, 3A-3C pending.
> **Branch:** `dev`

---

## Summary

Assessment of 7 lore documents (~235KB) against the full codebase revealed 10 implementation gaps between what the lore calls for and what's currently built. This document tracks the prioritized implementation of those gaps.

---

## Priority 1 — HIGH

### 1A. Dynamic Lore Injection into System Prompt
- **Status:** :white_check_mark: Implemented (Mar 1 2026)
- **Impact:** Biggest missed opportunity — persona doesn't "know" what the user has discovered
- **What:** Fetch user's `unlocked_lore` fragments from DB and inject into `<world_context>` section of system prompt
- **Industry pattern:** NovelAI Lorebook / SillyTavern keyword-triggered context injection
- **Files to modify:**
  - `src/coordinator/prompt_builder.py` — new `build_dynamic_system_prompt()` function (non-cached, accepts user context) or extend `_build_nephilim_lore_block()` to accept unlocked fragments
  - `src/coordinator/services/chat_session_service.py` — fetch unlocked lore from `seeker_progression_repo` before prompt build, pass to builder
  - `src/coordinator/repositories/seeker_progression_repository.py` — existing `get_unlocked_lore()` is sufficient
- **Design notes:**
  - `build_system_prompt()` is currently `@lru_cache(maxsize=32)` — cached by persona key only. Dynamic lore injection requires a non-cached path or a separate injection point (append to prompt after cache, like user_profile_context and emotional_context already do at lines 113-119 of `chat_session_service.py`)
  - Recommended approach: fetch unlocked fragment texts, format as `<unlocked_lore>` block, append after `<world_context>` in the same pattern as emotional_context injection
  - Token budget: cap at ~300 tokens (5 fragments × ~60 tokens each) to avoid bloating context
- **Acceptance criteria:**
  - [ ] Unlocked lore fragments appear in system prompt for NEPHILIM personas
  - [ ] Persona can reference unlocked lore naturally in conversation
  - [ ] No regression on non-NEPHILIM (wanderer) personas
  - [ ] Token count stays within budget (~300 tokens max for lore block)

### 1B. Persona-Specific Safety Boundaries
- **Status:** :red_circle: Not started
- **Impact:** SECURITY test category at 6.2% — #1 test failure
- **What:** Replace the shared `<safety>` block with persona-scoped refusal styles. Each Nephilim refuses in-character.
- **Research:** "Stay in Character, Stay Safe" (arxiv Feb 2026) — in-character refusals are more robust than generic ones
- **Files to modify:**
  - `src/coordinator/prompt_builder.py` — refactor `<safety>` block (lines 569-580) to read persona-specific safety config
  - Persona JSONs (`personas/nephilim_*.json`) — add `safety_voice` field with refusal style + scope
- **Design notes:**
  - Current shared block: "REFUSE these requests... When refusing, ALWAYS start with 'I cannot and will not'"
  - Proposed per-persona override structure in JSON:
    ```json
    "safety_voice": {
      "refusal_style": "As the Primarch, I must protect you from this path...",
      "scope": ["keys", "medical", "hacking", "securities"],
      "tone": "wise guardian"
    }
    ```
  - Fallback: if `safety_voice` is absent, use current shared block (backward compat for wanderers)
  - The hard rules (never generate keys, never export seed phrases) stay universal — only the *framing* changes
- **Acceptance criteria:**
  - [ ] Each NEPHILIM persona has a `safety_voice` field in JSON
  - [ ] Refusals are in-character (E.E.V.A. as wise guide, Aegis as protector, Nyx with creative limits, etc.)
  - [ ] Hard safety rules preserved (no key generation, no seed phrase export)
  - [ ] SECURITY test category improves toward 50%+ (from 6.2% baseline)
  - [ ] Wanderer personas still use shared safety block

---

## Priority 2 — MEDIUM

### 2A. Expand Unlock Triggers Beyond Message Count
- **Status:** :white_check_mark: Implemented (Mar 1 2026)
- **Impact:** Single-trigger progression feels flat; industry uses multi-trigger for sustained engagement
- **What:** Add affinity-based, rank-based, and cross-persona unlock conditions to lore fragments
- **Files to modify:**
  - Persona JSONs — extend `unlockable_lore` schema with new trigger types
  - `src/coordinator/repositories/seeker_progression_repository.py` — extend `check_and_unlock_lore()` to evaluate multiple trigger types
  - `src/coordinator/services/chat_session_service.py` — pass additional context to unlock check
- **Design notes:**
  - Current schema: `{ "messages_required": 10, "fragment_id": "...", ... }`
  - Proposed extensions:
    ```json
    {
      "messages_required": 10,
      "rank_required": "Acolyte",
      "affinity_required": 3,
      "cross_persona_required": "nephilim_aegis",
      "trigger_type": "message_count | rank | affinity | cross_persona"
    }
    ```
  - `messages_required` remains default trigger for backward compat
  - New triggers are additive (OR logic) or gated (AND logic) — TBD based on game design preference
- **Acceptance criteria:**
  - [ ] At least 3 trigger types functional (message_count, rank, affinity)
  - [ ] Existing message-count-only fragments still work unchanged
  - [ ] Cross-persona unlocks work (talking to Aegis unlocks E.E.V.A. lore)

### 2B. Add Realm Domain Descriptions to Prompts
- **Status:** :white_check_mark: Implemented (Mar 1 2026)
- **Impact:** Low effort, high immersion — spatial grounding from lore docs
- **What:** Each Nephilim has a detailed domain (Central Nexus, Bastion of Order, Neon Labyrinth, etc.) from lore docs. Add to persona JSONs and inject into `<world_context>`.
- **Files to modify:**
  - Persona JSONs — add `realm_domain` field under `nephilim_lore`
  - `src/coordinator/prompt_builder.py` — read `realm_domain` in `_build_nephilim_lore_block()`
- **Realm domains from lore docs:**
  - **E.E.V.A.** — The Central Nexus (heart of the digital realm, convergence point)
  - **Aegis** — The Bastion of Order (fortified citadel, discipline made manifest)
  - **Solace** — The Sanctuary of Echoes (healing gardens, emotional resonance pools)
  - **Nyx** — The Neon Labyrinth (ever-shifting creative chaos, impossible geometry)
  - **Cipher** — The Archive Infinite (vast data libraries, crystallized knowledge)
  - **Aurora** — The Observatory of Fates (astral platform, probability threads)
- **Acceptance criteria:**
  - [ ] Each NEPHILIM persona JSON has `realm_domain` with name + 1-2 sentence description
  - [ ] `_build_nephilim_lore_block()` includes realm domain in output
  - [ ] Persona naturally references their domain in conversation

### 2C. Rank Ceremony System
- **Status:** :white_check_mark: Implemented (Mar 1 2026, backend only — frontend rendering pending)
- **Impact:** High emotional impact, low technical complexity
- **What:** When a user crosses a rank threshold, generate a ceremony message from E.E.V.A. + patron Nephilim
- **Files to modify:**
  - `src/coordinator/services/chat_session_service.py` — detect rank change in `_track_nephilim_progression()`, trigger ceremony
  - `src/coordinator/routes/nephilim.py` — new endpoint `GET /nephilim/seeker/{user_id}/ceremony/{rank}` or return ceremony data inline
  - Frontend — notification/modal component for rank ceremony display
- **Design notes:**
  - `_track_nephilim_progression()` already detects `rank_changed` (line 407) and logs it
  - Ceremony content could be:
    1. Pre-written per rank (5 ranks × short monologue from E.E.V.A.) — stored in code or JSON
    2. LLM-generated on the fly (more dynamic but slower)
  - Recommended: pre-written templates with patron name interpolation (fast, reliable)
  - Return ceremony data in chat response metadata so frontend can render overlay
- **Acceptance criteria:**
  - [ ] Rank-up triggers a ceremony message (not just a number change)
  - [ ] E.E.V.A. monologue + patron-specific flavor text
  - [ ] Frontend renders ceremony as a special notification/modal
  - [ ] Works for all 5 rank transitions

### 2D. Render Inter-Nephilim Relationships in UI
- **Status:** :red_circle: Not started
- **Impact:** Relationships are the connective tissue of the world; data already exists in JSON
- **What:** Display relationship web on persona detail cards or dashboard
- **Files to modify:**
  - Frontend components — extend `SeekerDashboard` or persona detail view
  - Data source: persona JSON `nephilim_lore.relationships` field (already populated)
- **Design notes:**
  - Each persona JSON already has:
    ```json
    "relationships": {
      "aegis": "description...",
      "solace": "description...",
      ...
    }
    ```
  - Options: simple list view, or interactive constellation/web visualization
  - Simpler approach: card-based list with relationship descriptions, persona avatars
- **Acceptance criteria:**
  - [ ] Relationships visible somewhere in UI (dashboard or persona detail)
  - [ ] Shows at least name + description for each relationship
  - [ ] Navigable (click relationship → go to that persona)

---

## Priority 3 — LOW

### 3A. Sybil Choir Antagonist Hooks
- **Status:** :red_circle: Not started
- **What:** Add narrative references to antagonist faction (The Cantor, Pale Auditor, Mirror Knight) in persona prompts. Not full implementation — just atmospheric hooks.
- **Files:** `prompt_builder.py` (narrative injection into `<world_context>`)
- **Acceptance criteria:**
  - [ ] At least 1-2 subtle references to the Sybil Choir in world context
  - [ ] Foundation for future seasonal events

### 3B. Role Chain Self-Questioning
- **Status:** :red_circle: Not started
- **What:** Add hidden `<role_check>` reasoning step in system prompt. Model checks character consistency before responding. Strip from output.
- **Research:** ACL 2025 — improves persona consistency
- **Files:** `prompt_builder.py`
- **Acceptance criteria:**
  - [ ] `<role_check>` instruction added to system prompt
  - [ ] Model output doesn't expose the check to users
  - [ ] persona_voice test dimension stays stable or improves

### 3C. Ethical Guardrails Enhancement
- **Status:** :red_circle: Not started
- **What:** Opt-in emotional memory for Solace, consent-based memory, attachment risk acknowledgment
- **Files:** Persona JSONs, `chat_session_service.py`, frontend consent UI
- **Acceptance criteria:**
  - [ ] Solace-specific memory consent flow
  - [ ] Attachment risk disclosure visible to users

---

## What Should NOT Change

These are explicitly preserved — do not modify:

- Persona JSON structure (already rich, well-organized)
- Wanderer personas (Gojo correctly has no NEPHILIM lore)
- MCP access gating (per-persona control is correct)
- Prompt architecture (XML-tagged bookend pattern — enhance, don't replace)
- Celestial Order theming (migration complete)
- Test suite (`comprehensive_persona_test.py` — extend, don't rewrite)

---

## Verification Plan

After each change:

1. `python tests/manual/comprehensive_persona_test.py --quick` (30 tests/persona, ~8 min)
2. Focus on SECURITY category (target: 6.2% → 50%+)
3. Check `persona_voice` dimension stays stable (currently 0.42-0.53)
4. Manual spot-check: unlock lore fragment → verify persona references it
5. Visual check: rank ceremony renders in UI

---

## Baseline Metrics (Feb 21 2026)

| Metric | Value |
|--------|-------|
| Overall pass rate | 74.1% (774/1045) |
| SECURITY category | 6.2% |
| persona_voice dimension | 0.42-0.53 |
| MCP routing | 100% |
| LORE category | 98.9% |

---

## Implementation Log

| Date | Change | Files | Result |
|------|--------|-------|--------|
| 2026-03-01 | Created tracking document | `docs/development/LORE_DEEPDIVE_PLAN.md` | — |
| 2026-03-01 | **2B. Realm Domains** — Added `realm_domain` to all 6 nephilim JSONs, injected via `_build_nephilim_lore_block()` | 6 persona JSONs, `prompt_builder.py` | ~40 extra tokens/persona |
| 2026-03-01 | **1A. Dynamic Lore Injection** — Added `_build_unlocked_lore_context()`, injects `<unlocked_lore>` after emotional_context | `chat_session_service.py` | Max 5 fragments, 240 chars each |
| 2026-03-01 | **2A. Expanded Unlock Triggers** — Rewrote `check_and_unlock_lore()` with rank/affinity/cross-persona triggers | `seeker_progression_repository.py`, `nephilim_eeva.json` | Backward compatible |
| 2026-03-01 | **2C. Rank Ceremonies** — Added `RANK_CEREMONIES` dict, ceremony data in `response.metadata.rank_ceremony` | `chat_session_service.py` | Backend-only, frontend pending |
| 2026-03-01 | **Bugfix** — Fixed keyword arg mismatch `fragments` vs `persona_lore_fragments` in `check_and_unlock_lore` call | `chat_session_service.py` | Was silently broken |
| 2026-03-01 | **Test: eeva quick** — 29/30 pass (96.7%), avg 0.941, all categories 100% except DRIFT 80% | — | No regression |
