---
title: "Two-brain split: tool brain + voice brain"
status: Proposed
created: 2026-07-05
last_reviewed_on: 2026-07-05
review_in: 12 months
applies_to: nephilim
---

# ADR-008: Two-brain split — tool brain + voice brain

## Status

Proposed — **open decision: which model drives the tool brain** (candidate
matrix below). The 2026-07-05 tactical search fixes (routing examples, date
injection, Brave locale/freshness, bare-command hardening) shipped separately
as a stopgap; they do not change the architecture this ADR addresses.

## Context

**Incident.** 2026-07-05 Telegram comparison against a reference agent
(Nous Research `hermes-agent` on a Hostinger VPS, GPT-5.4-mini): E.E.V.A.
refused weather and general-news questions ("I cannot and will not provide
real-time data"), free-associated a wallet query from "search the web to
answer my question", reported °F for a Swiss location, and presented a
5-day-old article as "today". The reference agent answered all of these
correctly and effortlessly. Code-level diagnosis traced every failure to two
structural facts, not to the guard stack (all SearchSettings guards and the
ADR-007 groundedness gate were ON and behaved correctly):

1. **Tool use is classifier-gated, not model-decided.** The bge-m3 semantic
   router decides whether search is even offered; its example set is
   crypto/sports-centric by construction and has been patched reactively per
   incident (sports 2026-07-04, weather/news 2026-07-05). Every uncovered
   topic falls to `NEEDS_NEITHER` → bare completion → the model's own trained
   refusal. This is whack-a-mole by construction.
2. **The model cannot be trusted with agency.** The entire guard stack
   (force-search, grammar-constrained extraction in ADR-004, groundedness
   gate in ADR-007) is scar tissue around Magidonia-24B's unreliability at
   structured tool calls — ADR-004 already rejected embedding the Nous
   Hermes loop for exactly this reason. External evidence corroborates:
   the Magidonia family breaks simple structural instructions in its own
   native RP domain (documented HF discussion on v4.2.0), and BFCL v4 shows
   even function-calling-*specialized* 24–32B local models are mid-pack.

**Industry direction (researched 2026-07-05).** Every well-regarded
2025-2026 personal-agent project surveyed (hermes-agent, OpenClaw, Letta,
goose, OpenHands) uses native model-decided tool calling; none gates tools
behind an intent classifier. The Agent Skills standard (SKILL.md progressive
disclosure) is now cross-vendor. The persona/grounding tension is evidenced
in the literature, with a published two-pass fix: draft/ground first,
restyle in persona voice last ("Post Persona Alignment", arXiv 2506.11857) —
consistent with ADR-004's own measurement that grounded synthesis is
inherently low-voice for this model on every path.

**Constraint that stays.** The local-first privacy rationale (rejected cloud
LLMs because injected financial/wallet context would leak) remains valid.
2025-2026 research shows redaction is a leaky mitigation (LLM-based
re-identification partially reverses masking), so "redact then send to
cloud" is NOT an acceptable pattern for financial data. The correct boundary
is architectural: sensitive context never enters a cloud-bound call at all.

**Forces, weighted per the operator (2026-07-05):** tool calling is the
dominant factor; NSFW capability and voice/roleplay quality matter to the
companion product; Ollama compatibility matters for the local path.
**Honest framing:** in a two-brain split, NSFW and voice/RP are *voice-brain*
factors and the voice brain does not change — so they should NOT drive the
tool-brain choice. They become decisive only in the alternative
"collapse-to-one-brain" architecture (one model does everything), which is
scored honestly below and rejected.

## Decision

Split the companion into two roles, divided by **capability and
sensitivity**, not all-or-nothing:

1. **Tool brain** — a model competent at native tool calling runs an agent
   loop for turns needing external action (web search, weather, news,
   later: skills). It receives tool schemas and decides tool use itself;
   the semantic-router gate is retired for this path (the router remains
   for wallet-intent detection, where a deterministic gate is a safety
   feature, not a limitation). The tool brain's output is *content*, never
   user-facing prose.
2. **Voice brain** — Magidonia-24B stays the persona/voice/NSFW engine. It
   renders every user-facing reply, including a final in-character restyle
   pass over tool-brain output (the PPA two-pass pattern). All ADR-005/006
   persona and memory work is unchanged.
3. **Hard privacy boundary, fail-closed** — wallet, trading, and financial
   context is architecturally excluded from any cloud-bound call. Wallet
   turns route entirely local as today. If the tool brain is hosted and a
   turn's context would include sensitive data, the turn stays local
   (degraded capability over leaked data — fail closed, never redact-and-send).

### Tool-brain candidates (open decision)

Factor weights per operator: **tool calling >> NSFW ≈ voice/RP ≈ Ollama**.
NSFW/voice scores are listed for the one-brain variant's sake; under the
recommended two-brain split they are moot (Magidonia keeps that role).

| Candidate | Tool calling | NSFW | Voice/RP | Ollama/local | Notes |
|---|---|---|---|---|---|
| **Hosted mini-tier (GPT-5-mini class / Claude Haiku 4.5)** | Excellent (RLHF'd for tool-call JSON; what makes the reference agent work) | Censored (moot in split) | Generic (moot in split) | No — cloud API | Best quality; ~100+ tok/s vs 18 local; est. single-user cost trivial ($1–5/mo). Requires the fail-closed boundary. |
| **Qwen3-class instruct 14–32B (local)** | Good-for-local (function-calling-trained family; BFCL mid-pack) | Censored (moot in split) | Generic (moot in split) | Yes — fits 48 GB alongside Magidonia is TIGHT (24B Q4 ≈14 GB + 32B ≈20 GB + bge-m3; model swap latency, `OLLAMA_MAX_LOADED_MODELS` thrash risk per latency-ops lesson) | Fully local option. Measurably behind hosted mini; two big models on one GPU needs eval of swap latency. |
| **EVA-Qwen (prior runner-up RP finetune, Qwen2.5-32B base)** | Poor-to-unknown — RP finetuning degrades instruction adherence (same failure class as Magidonia); never benchmarked for tool calls | Yes | Strong (was runner-up on voice) | Yes, but demoted 2026-06 on 10K trained context — disqualifying for an agent loop that accumulates tool results | Only interesting for the one-brain variant, and fails it on context + unproven tool calling. **Not recommended.** |
| **Magidonia-24B (status quo)** | Unreliable — the documented root cause | Yes | Best (current voice) | Yes (deployed) | Rejected as tool brain; **retained as voice brain.** |

**Recommendation:** hosted mini-tier as tool brain with the fail-closed
boundary (decisive on the dominant factor), Qwen3-local as the fallback if
any cloud use is rejected on principle — accepting visibly lower agentic
quality and a memory-pressure eval. The one-brain alternative (a single
model scoring well on all four factors) has no viable candidate: nothing
local combines frontier-class tool calling with uncensored RP voice, which
is precisely why the split exists.

### Phasing

- **P0 (done, separate commit):** tactical fixes — router examples, synthesis
  date injection, `BRAVE_COUNTRY`/freshness, bare-command hardening.
- **P1:** tool-brain MVP behind a flag (`TOOL_BRAIN_ENABLED`, default OFF):
  model-decided search for non-wallet turns; voice-brain restyle pass;
  eval-first gate (persona attribution match-or-beat + grounding accuracy on
  the incident query classes + latency budget), same discipline as
  ADR-005/006/007.
- **P2:** sensitivity classifier + fail-closed routing hardening; red-team
  the boundary (no financial context in any cloud-bound payload — logged,
  testable, `[inspected]` verifiable).
- **P3:** Agent Skills (SKILL.md progressive disclosure) on the tool brain;
  retire the per-incident router-example patching loop.

## Consequences

- **Easier:** open-set assistant queries (weather, news, anything uncovered
  by router examples) stop failing structurally; the reactive
  patch-per-incident loop ends; grounded answers regain persona voice via
  the restyle pass instead of fighting instruction saturation; skills give
  capability growth without prompt bloat.
- **Harder / costs:** a second model dependency (API key, billing, or local
  memory pressure); the restyle pass adds one voice-brain round-trip
  (~2–6 s at 18 tok/s for short answers) on tool turns; the privacy boundary
  becomes safety-critical code that must be red-teamed, not assumed.
- **Risks:** hosted-model outage degrades tool turns (mitigation: fall back
  to the legacy force-search path, which stays intact behind the flag);
  restyle pass could distort grounded facts (mitigation: citation service
  already system-generates citations; add a groundedness spot-check to the
  P1 gate); 48 GB memory pressure in the local variant (mitigation: eval
  before commit, or choose the hosted variant).
- **Supersedes/relates:** extends the VISION.md "HERMES-Agents framework"
  track with the missing premise (a tool-capable model, not just new routing
  around Magidonia). ADR-004's agentic pipeline stays parked for write
  actions; its safety middleware (interceptor, injection guard) wraps the
  tool brain's execution path unchanged. ADR-007's groundedness gate remains
  for the local bare-completion branches.
