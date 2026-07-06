---
title: Image-search result quality and spurious-refusal handling
status: Accepted
created: 2026-07-06
last_reviewed_on: 2026-07-06
review_in: 24 months
applies_to: docs
---

# ADR-010: Image-search result quality and spurious-refusal handling

## Context

A live Gwen `image_search` turn (2026-07-06) surfaced two independent defects on the ADR-008 tool-brain path:

1. **Garbage results.** Aggregated image search (SearXNG over Bing/Google/DuckDuckGo) returned icon-CDN SVGs (`cdn.jsdelivr.net` devicons, lucide-static icons) and a museum artwork matched only on a keyword collision, mixed with a couple of on-topic hits. The bge-m3 relevance gate existed only on the **legacy** `tool_calling_service` path (and default OFF) — the live `ToolBrainService`/`executor_bindings` path had **zero** result filtering.
2. **Refusal + sources incoherence.** The model executed the search fine but then, in the synthesis step, emitted a spurious safety refusal ("I cannot and will not search for images") — a known residual-refusal leak of the abliterated daily driver. `routes/chat.py:_try_tool_brain` stapled the verified 🔍 Sources block on regardless, because citation-append was gated only on `used_search`/`search_results` booleans, never inspecting `result.answer`. Tool-success and synthesis-compliance were fully decoupled.

A follow-up trace found the root cause of the keyword-collision was upstream: the model authors the `image_search` query **freely, with zero guidance** (the param description was just "The search query."), from the full raw conversation, and it is passed **byte-identical** to the backend. It distilled explicit story prose into a long query and "Cock" (an artist's surname) collided.

Two web-research passes informed the fixes: refusal handling (prefill steering is the robust in-loop countermeasure for abliterated residual refusal; >99% steer-success) and junk filtering (path-substring denylists for shared CDNs, whole-host for pure-icon services, `.svg` = icon signal, and a semantic relevance floor as a separate soft layer).

## Decision

**Result quality (in the bound search executor `tools/executor_bindings.py`, the single choke point feeding both synthesis and citations):**

- **Deterministic image-junk denylist** — new `tools/result_filters.py`, **always-on, no flag** (deterministic + unit-testable to certainty on a single-operator system → a flag would be flag-debt with no soak hypothesis). Images-only; strips icon-CDN package paths, whole-host icon/placeholder/favicon/badge services, host-independent icon path signals, and `.svg`. Never-empty fallback: if filtering would empty a set, the original is returned.
- **Per-result bge-m3 relevance floor** — `SearchRelevanceService.filter_relevant`, flag-gated `SEARCH_RELEVANCE_GATE_ENABLED` (default OFF), graceful (never empties a uniform-low set), fail-open. **Kept OFF for images:** a live cosine study found legit-NSFW results (0.37–0.47) and keyword-collision junk (0.26–0.36) *overlap*, so no single threshold cleanly separates them, and false-abstention on a companion is the worse failure. The denylist is the reliable layer; the artwork class is better addressed at the query layer (below).

**Spurious-refusal handling (in `services/tool_brain_service.py`):**

- `is_synthesis_refusal` detects a templated refusal in the opening ~240 chars of the synthesis output; the loop runs **one bounded prefill-steered retry** (anti-refusal nudge + compliant assistant prefill — the inference-time analogue of a DPO fix). A new `ToolBrainResult.refused` flag is set only if the retry also refuses.
- `routes/chat.py:_try_tool_brain` returns `None` (falls through to the legacy honest floor) when `refused` — **citations are never stapled onto a refusal.**

**Query quality (content-neutral — this is an uncensored companion; NSFW *keyword* search still works):**

- `image_search`/`video_search` tool descriptions now instruct the model to formulate `query` as concrete visual keywords, not narrative prose.
- `tool_interceptor._validate_arguments` applies the query allowlist (non-empty, ≤300 chars, no control chars) to the live ADR-009 search names (`_SEARCH_QUERY_TOOLS`), not just the dead `brave_web_search` — closing a gap where the tool-brain query was structurally unvalidated.

**Persona policy:** Gwen may web/image/video-search explicit adult content when asked. Her `escalation_policy.tool_intent` "avoid web search for sexual content" line was decorative (never read by code); it was replaced with a positive statement for internal coherence — no behavioral change (the field does not reach the prompt or any tool decision).

## Status

Accepted — shipped across PRs #11–#13 and deployed to prod 2026-07-06.

## Consequences

- **Easier:** image search returns clean, on-topic results; a model refusal can never produce an incoherent refusal-plus-sources artifact; the tool-brain query is now length/control-char bounded like the legacy path.
- **Harder / trade-offs:** the denylist is a maintained pattern list (new icon-CDN mirrors may need adding — logged, not silent). The relevance floor is off for images by deliberate design, so a semantic-collision result the denylist can't catch (a legit-domain artwork) can still slip through; the mitigation is the query-formulation guidance, not a filter.
- **Follow-up:** if a concrete keyword-collision recurs despite the query guidance, revisit a per-`nsfw` relevance split (SFW-only floor ~0.45, where legit results sit 0.54–0.73 far above junk). The relevance-gate default stays OFF for images until such evidence appears.
- **Related:** [ADR-008](008-two-brain-split-tool-brain-voice-brain.md) (tool brain), [ADR-009](009-layered-toolkit-registry-generic-web-toolset-inner-wisdom-skills.md) (web toolset), [ADR-004](004-persona-safe-agentic-tool-calls.md) (interceptor).
