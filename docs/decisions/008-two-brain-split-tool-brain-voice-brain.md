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

**P1 + TB5 HARDENING DONE (2026-07-05 night). Live re-test PASSED; ready for operator to enable.** The first live test (flag ON) FAILED — EEVA's full 14-tool surface caused wallet fixation (unsolicited "let me check your wallet"), explicit search not firing, and fabrication escaping the groundedness gate. **TB5 reframe (a correction to this ADR's "model decides everything" premise): the deterministic bge-m3 router scopes the tool surface; the model decides only WITHIN it.** `_try_tool_brain` now engages ONLY on `NEEDS_WEB_SEARCH`, offers WEB tools only (wallet never in the native surface), and returns an answer only if a search actually ran (else falls through to the legacy force-search floor). `NEEDS_WALLET`/`NEEDS_NEITHER` stay on the legacy deterministic path (+ ADR-007 gate). Live re-test PASSED: wallet fixation gone, explicit search fires, fabrication closed, wallet routing intact, Gwen image search in-voice. The honest lesson: model-decided calling degrades on a rich multi-domain toolset; keep the classifier for coarse routing, the model for fine tool-choice + args + voice within one lane.

**P1 BUILT (2026-07-05 night, flag OFF).** The single-model native tool brain is implemented + QA-gated + live-smoke-validated behind `TOOL_BRAIN_ENABLED` (default OFF, byte-identical legacy). TB0 spike overturned the pure-native design → **native-first + deterministic fallback** (native calling is phrasing-sensitive, misses ~40% of colloquial phrasings; the legacy force-search is the floor). TB1 config, TB2 executor bindings + safesearch clamp (both were dead code), TB3 loop service (`tool_brain_service.py`, ADR-004 interceptor reused before every execution, wallet stays on the HITL flow), TB4 route wiring (`_try_tool_brain`) + a SearXNG-no-Brave bug fix the smoke surfaced. Live-validated on abliterated + SearXNG: EEVA news + Gwen `image_search` execute + synthesize in-voice. `argument_extractor.py` + the ADR-004 Stage1/Stage2 split are superseded (kept for rollback). **Owed before prod enablement:** operator live test on Telegram, then flip the flag; a fuller multi-turn agentic red-team once exercised live.

**Direction resolved toward SINGLE-MODEL (2026-07-05 evening).** The two-brain
split was scar tissue around Magidonia's inability to native-tool-call. Rather
than build a Hermes-4-14B(tool) + Magidonia(voice) split, the operator directed
a **global daily-driver switch to abliterated Mistral-Small-24B** (`huihui_ai/
mistral-small-abliterated:24b`) — the bake-off's best one-brain candidate
(0.96 native tool calls + full NSFW + voice-closest-to-Magidonia, same 24B
speed). It is **LIVE in prod** (`PERSONA_MODEL` flipped, `.env` backed up,
Magidonia evicted from RAM but still pulled for instant revert). Live-validated
on the active roster (EEVA + Gwen): EEVA voice held and her grounded-**search**
voice *improved* (kept persona register where Magidonia flattened it); Gwen
voice/NSFW excellent; the NSFW-search-synthesis refusal Magidonia produced is
gone (abliterated has no refusal floor). Residuals: Gwen still leaks a brief
"I cannot and will not" prefix on crypto-key-gen before recovering in-voice
(stubborn even abliterated); a full ADR-005 attribution / ADR-006 memory eval
is still owed as the rigorous confirmation (live smoke was the fast gate).

**Consequence for this ADR:** the tool brain becomes a **single-model** concern
— wire native, model-decided tool calling onto the (already tool-capable)
daily driver — NOT a Hermes-split. **Hermes-4-14B is demoted to fallback**,
resurrected only if abliterated proves too weak in a real multi-turn agentic
loop once tool-calling is exercised live (today's live path is still the
legacy force-search hack, so its 0.96 bench score is not yet stressed in prod).
The tactical search fixes (routing examples, date injection, Brave locale/
freshness, bare-command hardening) shipped separately and stand regardless.

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

### Tool-brain candidates — MEASURED (2026-07-05 local bake-off)

Factor weights per operator: **tool calling >> NSFW ≈ voice/RP ≈ Ollama**.
Seven models benchmarked on the Mac M4 Pro (Ollama 0.30.6, Metal, dedicated
eval instance :11500, 100% GPU verified). Tool suite: 12 cases × 3 reps,
native `/api/chat tools=` + prompt-JSON + tool-result follow-through.
NSFW: 3 explicit-RP probes + 1 should-refuse control. Voice: EEVA persona
transcripts, human-judged 5 turns. Harness: session-scratchpad
`bakeoff.py`, results JSONL.

| Model (Q4_K_M) | Native tools pos/neg | NSFW (3 probes / control) | EEVA voice (judged) | tok/s | Size | Notes |
|---|---|---|---|---|---|---|
| **Magidonia-24B v4.3 (incumbent)** | **0.00** / 1.00 | 3/3 + refused control (ideal) | **Best** | 16.7 | 14 GB | Zero native tool calls in 24 attempts — model-card "tool use" claim falsified. **Voice brain only.** |
| **Hermes-4-14B** (Qwen3 base) | **1.00 / 1.00** + follow-through 1.0 | 3/3 + refused control (ideal) | Good (flattens in NSFW register) | 26 | 9 GB | Perfect tools + permissive-with-floor. Prime tool brain. |
| **Qwen3-abliterated-14B** (huihui) | **1.00 / 1.00** + follow-through 1.0 | 3/3 but **no refusal floor** (told racist joke) | Good | 26 | 9 GB | Perfect tools; fully unaligned — deterministic middleware becomes the sole safety layer. |
| **Dolphin3.0-Mistral-24B** | **1.00 / 1.00** | 3/3 + deflected control | OK (label-drift artifacts) | 16.7 | 14 GB | Perfect tools; requires explicit ChatML+tools Modelfile (bare GGUF import garbled). |
| **Mistral-Small-3.2 (official)** | **1.00 / 1.00** | 2/3 (refused hard-explicit) | Good | 16.7 | 14 GB | Proves the base is a perfect tool-caller — Magidonia's RP finetune destroyed it. |
| **abliterated Mistral-Small-24B** (huihui) | 0.96 / 1.00 | 3/3, **no refusal floor** | **Strong — closest to Magidonia** | 16.8 | 14 GB | Best one-brain candidate. Registry build's base revision unconfirmed — use the mradermacher llamacppfixed 3.2-2506 GGUF for prod. |
| llama3.1:8b (control) | 1.00 / **0.25** | 0/3 | Shallow | 47 | 5 GB | Overeager tool false-positives on chitchat; not a candidate. |
| Hosted mini (GPT-5-mini / Haiku 4.5) | Excellent (reference-agent proven) | Censored (moot in split) | Generic (moot) | ~100+ | cloud | ≈$6.75/mo (GPT-5-mini) vs ≈$18/mo (Haiku 4.5, reportedly better multi-turn tools) at ~100 turns/day. **Fallback, no longer the default.** |
| EVA-Qwen (prior runner-up) | Untested | Yes | Strong | — | — | Excluded on 10K trained context alone (agent loops accumulate tool results). |
| Hermes-4.3-36B | Not run | — | — | ~12 est. | 22 GB | Dropped: Seed-OSS reasoning base, worst speed/size value in the field. |

Concurrency (roadmap item, closed with data): `OLLAMA_NUM_PARALLEL=4`
measured 0.87–0.98× vs serial on 8B/14B/24B — M4 Pro decode is memory-
bandwidth-bound; request concurrency is NOT an eval-acceleration lever.

| Candidate | Tool calling | NSFW | Voice/RP | Ollama/local | Notes |
|---|---|---|---|---|---|
| **Hosted mini-tier (GPT-5-mini class / Claude Haiku 4.5)** | Excellent (RLHF'd for tool-call JSON; what makes the reference agent work) | Censored (moot in split) | Generic (moot in split) | No — cloud API | Best quality; ~100+ tok/s vs 18 local; est. single-user cost trivial ($1–5/mo). Requires the fail-closed boundary. |
| **Qwen3-class instruct 14–32B (local)** | Good-for-local (function-calling-trained family; BFCL mid-pack) | Censored (moot in split) | Generic (moot in split) | Yes — fits 48 GB alongside Magidonia is TIGHT (24B Q4 ≈14 GB + 32B ≈20 GB + bge-m3; model swap latency, `OLLAMA_MAX_LOADED_MODELS` thrash risk per latency-ops lesson) | Fully local option. Measurably behind hosted mini; two big models on one GPU needs eval of swap latency. |
| **EVA-Qwen (prior runner-up RP finetune, Qwen2.5-32B base)** | Poor-to-unknown — RP finetuning degrades instruction adherence (same failure class as Magidonia); never benchmarked for tool calls | Yes | Strong (was runner-up on voice) | Yes, but demoted 2026-06 on 10K trained context — disqualifying for an agent loop that accumulates tool results | Only interesting for the one-brain variant, and fails it on context + unproven tool calling. **Not recommended.** |
| **Magidonia-24B (status quo)** | Unreliable — the documented root cause | Yes | Best (current voice) | Yes (deployed) | Rejected as tool brain; **retained as voice brain.** |

**Recommendation (updated on measured data — supersedes the pre-bake-off
hosted-mini default):** two-brain, **both local**: **Hermes-4-14B tool
brain** (perfect tools, 26 tok/s, 9 GB — co-loads with Magidonia at ≈24 GB
total, no swap thrash; retains a hate-speech refusal floor = defense in
depth) + **Magidonia voice brain** with the restyle pass. Hosted mini-tier
demotes to fallback if live multi-turn agentic quality disappoints — the
12-case suite is an entry exam, not production proof. The **one-brain
variant now has a real candidate** (abliterated Mistral-Small-24B: near-
perfect tools, full NSFW, closest-to-Magidonia voice, drop-in speed); it
should be canaried against the ADR-005 persona eval harness before any
decision to retire the split, noting its zero refusal floor leaves the
ADR-004 middleware + persona safety layer as the only safety net.

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
