---
title: Conversation-control commands as shared session-API endpoints
status: Proposed
created: 2026-07-16
last_reviewed_on: 2026-07-16
review_in: 24 months
applies_to: docs
---

# ADR-011: Conversation-control commands as shared session-API endpoints

## Context

The Telegram gateway ships three commands today (`/start`, `/reset`, `/tools`), each a
thin HTTP call to the existing coordinator session API. We want a richer set of
**conversation-control** commands driven by companion/RP best practice (SillyTavern
swipe/regenerate/continue, author's-note/system nudges) and Telegram command-menu UX
research (5–8 command sweet spot, lead with the "money" verb, register via
`setMyCommands`):

- **Tier 1 (client chrome):** `/help`, `/whoami`, native command-menu registration.
- **Tier 2 (recovery verbs):** `/regen` (reroll last reply), `/continue` (extend last
  reply), `/undo` (drop last exchange).
- **Tier 3 (director verbs):** `/sys` (one-shot narrator beat), `/note` (persistent
  author's note: set/show/clear), `/impersonate` (draft the user's next line).

The hard requirement: **every command must work identically in BOTH the Telegram
gateway and the React Nephilim UI chat.** That rules out implementing the logic in
either client. It also presses on the gateway's founding invariant, *"thin gateway,
zero coordinator changes"* — several of these verbs are inherently stateful
(regenerate/undo mutate history; note persists per session) and cannot be faked
client-side without drift between the two clients.

Forces:
- Two clients must not diverge — a `/regen` in Telegram and a "regenerate" button in
  React must produce the same server behavior.
- The prompt/history/model machinery already lives in the coordinator
  (`prompt_builder`, `chat_session_service`, the SQLite `messages` table). Duplicating
  any of it in a client is wrong.
- `/reset_persona` was considered and **dropped** — applying a persona-JSON edit is a
  terminal-side `launchctl kickstart` you do at the machine where you edit; a remote
  command adds surface for no real workflow gain.

## Decision

Implement the stateful verbs as **new coordinator session-API endpoints**, and treat
both the Telegram gateway and the React UI as **thin, equal clients** of that shared
contract. Client chrome (`/help`, `/whoami`, menu registration) stays client-local.

This reframes — not abandons — the gateway invariant: the *gateway* still adds zero
business logic (HTTP calls only); it is the *session API itself* that gains
conversation-control endpoints, as a coordinator feature consumed by **both** UIs. A
compromised chat still reaches nothing it couldn't already (no tool/exec/file/trading
surface is added).

New/changed session-API surface (all under the existing `/sessions/{id}` resource):

| Verb | Endpoint | Behavior | State change |
|------|----------|----------|--------------|
| `/regen` | `POST /sessions/{id}/regenerate` | Delete the last assistant turn, re-run the model on the prior user turn, return the new reply. | Replaces last assistant message |
| `/continue` | `POST /sessions/{id}/continue` | Prompt the model to extend its last assistant message; append the continuation as a new assistant message. | Appends assistant message |
| `/undo` | `POST /sessions/{id}/undo` | Delete the last exchange (last user + trailing assistant messages). | Deletes last turn |
| `/sys` | `POST /sessions/{id}/narrate` `{text}` | Store `text` as a `narrator`-role message framed as bracketed scene direction (not user dialogue); model reacts in-world; return the reply. | Appends narrator + assistant messages |
| `/note` | `PUT/GET/DELETE /sessions/{id}/note` `{note}` | Set/show/clear a per-session author's note, injected into every subsequent turn **after** the `lru_cache`d system prompt (same seam as on-demand lore, never inside the cache). | New `session_notes` table (additive) |
| `/impersonate` | `POST /sessions/{id}/impersonate` `{hint?}` | Generate a first-person **user** draft from history (+ optional hint); return it **without** storing — the client decides whether to send it. | None |

Client chrome:
- `/help` — fixed help text (Telegram: `MSG_*` string; React: a help panel). No backend.
- `/whoami` — persona + NSFW mode + session id. Backed by a read-only
  `GET /sessions/{id}` metadata endpoint so both clients read identical truth.
- Menu registration — Telegram `setMyCommands` (native slash menu, 6 surfaced:
  `/start /help /regen /continue /undo /tools`); React surfaces per-message action
  buttons (regenerate/continue/undo) + a composer slash-palette for `/sys /note
  /impersonate`.

Shared model rules preserved for every new endpoint: `OLLAMA_NUM_PARALLEL=1`
serialization, first-person post-processing, tool-name strip, the ADR-007 groundedness
gate, and the forwarded-message injection guard on the gateway side.

## Status

Proposed

## Consequences

**Easier:** one server-side source of truth for every verb → the two clients cannot
drift; new future clients inherit the full command set for free; each endpoint is
independently unit-testable at the service layer (mock the LLM boundary).

**Harder / follow-up:**
- A schema change (`session_notes` table, additive, via alembic) — blast-radius item;
  premortem: *this could fail if the note injection lands inside the `lru_cache`d
  prompt builder and poisons every persona's cache* → mitigated by injecting the note
  through the post-cache `extra_system_context` seam (ADR-006 M0), never inside
  `_build_system_prompt_lean`.
- The gateway CLAUDE.md invariant text must be updated from "zero coordinator changes"
  to "thin HTTP client of the session API (which the coordinator may extend for all
  clients)" — the spirit (no logic/secrets/tool-surface in the gateway) is unchanged.
- `narrator`-role messages are a new `messages.role` value — history rendering,
  summarization, and any role-switch logic must tolerate it.
- Security: `/sys` and `/note` let the (single, allowlisted) owner inject
  elevated-framing text. Framed as in-world narration / author guidance, **not** as a
  system prompt that can override safety — and the gateway already refuses forwarded
  (third-party) content, so there is no external injection path.
- Delivered as QA-gated phases under one branch (Tier 1 → Tier 2 → Tier 3), not a
  big-bang; each phase ships with tests green in both the coordinator suite and the
  gateway suite before the next begins.
