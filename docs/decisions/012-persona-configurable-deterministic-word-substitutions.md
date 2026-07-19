---
title: Persona-configurable deterministic word substitutions
status: Accepted
created: 2026-07-19
last_reviewed_on: 2026-07-19
review_in: 24 months
applies_to: nephilim
---

# ADR-012: Persona-configurable deterministic word substitutions

## Context

A persona (Gwen) needed to never use a specific word ("shaft") and always use an
approved form ("cock"). Prompting could not enforce it, for two compounding reasons
found by live testing:

1. **The lean prompt builder (ADR-005) does not include the `do`/`dont` arrays.**
   Verified against the actual built prompt: a `dont` line like "always say cock not
   shaft" never reaches the model. Those arrays are largely vestigial under the
   exemplar-first builder.
2. **Even if it reached the model, negative instruction is a weak lever.** The word
   is ordinary anatomy vocabulary the local model reaches for on its own; naming the
   forbidden token in the prompt can even prime it. Measured: "shaft" appeared in
   **6/12** turns at temperature **0.9** (not the high temp first assumed) with the
   `dont` line present-but-unreached.

So no prompt-level change can reliably control this. The only remaining lever is the
generated text itself.

## Decision

Add a **data-driven, deterministic output substitution** applied in the shared
finalize path. Each persona card may declare a `word_substitutions` map
(e.g. `{"shaft": "cock"}`); the finalize path replaces whole-word occurrences with
the approved form, case-preserving.

- Helper: `services/message_processing_service.py::apply_word_substitutions(answer, subs)`
  — whole-word (`\b`), case-insensitive match with case-preserving output, keys
  regex-escaped, rule count capped (25). **No-op** when the map is empty.
- Applied in **both** finalize paths so it is persona-agnostic:
  `routes/chat.py::_build_llm_response` (pure-LLM + tool-brain + greet) and
  `services/query_handler_service.py::_finalize_response` (wallet/agentic/legacy).
- Schema: `PersonaCard.word_substitutions: Dict[str, str]` (documented/validated;
  `extra="allow"` already carried it through).
- Config lives in the persona JSON as **data**, matching how `lore`/`voice`/
  `model_preferences` are already handled — any persona self-serves without a code
  change.

## Status

Accepted

## Consequences

**Easier:** guaranteed word choice at any temperature, for any persona, by editing
JSON only. Zero runtime cost — one `re.sub` per rule on the finished string
(microseconds; it does **not** touch the token-generation loop, unlike a second LLM
pass such as the ADR-007 groundedness gate). Other personas declare nothing and pay
nothing (early no-op).

**Harder / caveats:**
- It is a **blunt** instrument: whole-word case-preserving substitution with no
  semantic awareness. Word-boundary anchoring means substrings survive
  (`driveshaft` untouched), but a persona that legitimately needed the banned word in
  some context could not (acceptable for the NSFW-companion use case, where there is
  no such context).
- It runs on the finished text, so it cannot fix *structure* (that is what
  `strip_role_prefix_leaks` / the `<msg>` handling do) — only vocabulary.
- The `do`/`dont` arrays remain vestigial under the lean builder; this ADR routes
  around them rather than reviving them. Anything that must truly steer *generation*
  (not post-hoc) still needs a `voice_signature`/exemplar change, not a `dont` line.
