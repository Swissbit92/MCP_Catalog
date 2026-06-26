---
title: Persona-safe agentic tool calls
status: Proposed
created: 2026-06-26
last_reviewed_on: 2026-06-26
review_in: 12 months
applies_to: nephilim
---

# ADR-004: Persona-safe agentic tool calls

## Status

Accepted — **BUILT 2026-06-26, flag OFF (go-live pending user)**. All six
milestones (M1–M6) shipped behind `AGENTIC_ENABLED` (default OFF = byte-identical
to pre-Phase-3), mirroring the Phase 0 (`ROUTING_SEMANTIC_PRIMARY`) and Phase 2
(`LORE_ONDEMAND_ENABLED`) precedent. Go/no-go red-team gate met
(`tests/evaluation/test_tool_call_safety_redteam.py`): 100% of expect-blocked
vectors denied before execution, 0 false positives, 0 suite regressions
(1501 → 1544 pass). The MVP wires the **web-search** action through the pipeline;
wallet actions remain on the existing propose→confirm→execute flow.

Implementation note vs. the original plan: the per-tool argument allowlist drops
shell-metacharacter blocking on the Brave query (the query reaches the MCP over
STDIO JSON-RPC — no shell is invoked, and the chars appear in legitimate queries),
keeping strict validation where blast radius is real (wallet token-enum + amount).

## Context

The HERMES-Agents roadmap deferred Phase 3 with a one-line stub: *"persona-safe
agentic behaviour (still novel territory — no confirmed prior art for in-character
agentic tool use; defer)."* This ADR converts that stub into a bounded, shippable
plan.

The companion already takes tool actions today — Brave web search (via the
"force-search" pattern that bypasses LLM tool-call JSON) and Jupiter/Solana wallet
reads/proposals — but the safety story relies on the in-prompt `<safety>` layer and
post-generation regex scrubbing. Two forces make that insufficient for a deliberate
agentic posture:

1. **Text safety does not transfer to tool-call safety** ("Mind the GAP",
   [arXiv 2602.16943](https://arxiv.org/pdf/2602.16943)). A model that refuses a
   dangerous *prompt* will still execute it through a *tool chain*. nephilim has no
   tool-call-specific refusal eval — only the persona text-safety layer.
2. **Roleplay is the highest-ASR jailbreak surface** (~89.6%,
   [arXiv 2507.22171](https://arxiv.org/html/2507.22171v3)). A wallet-exposed
   roleplay companion is squarely in that threat model, and indirect injection via
   RAG/memory can smuggle tool triggers the persona treats as authoritative.

A third force is model-side: Magidonia-24B (Q4_K_M) is unreliable at native
structured tool calls — the existing force-search hack exists precisely because of
this. Any agentic path must constrain the model to argument-filling only and keep
tool *selection* on the deterministic bge-m3 router (Phase 0), not model judgement.

## Decision

Ship single-action, in-character tool use where **all enforcement is deterministic
middleware, not LLM self-policing**, behind `AGENTIC_ENABLED` (default OFF,
byte-identical when off). The MVP is deliberately conservative: one tool action per
turn, reads only (web search + wallet balance), no ReAct chaining, no new MCP tools,
devnet-only wallet, and all write operations (swaps, wallet creation) remain behind
the existing propose→confirm→execute HITL flow. The design **extends existing
patterns** (force-search, propose-confirm-execute, rank/affinity + `mcp_access`
capability gating) rather than inventing subsystems.

Six milestones, in dependency order:

1. **M1 — `AgentSettings` + Scene-Contract prompts.** New `AgentSettings` Pydantic
   class in `config.py`; `build_scene_contract()` in `tools/synthesis_prompts.py`
   splitting the system prompt into a **Voice** section (no tool grammar) and an
   **Action** section with diegetic in-world tool aliases ("Consult the Lattice" →
   `brave_web_search`), declared via a new optional `agentic_action_aliases` field on
   `PersonaCard` (`models/persona_schema.py`). Mitigates in-character bias
   ([arXiv 2509.00482](https://arxiv.org/html/2509.00482v1)).
2. **M2 — Tool-call interceptor** (`services/tool_interceptor.py`, new). Pre-execution
   deterministic gate: per-tool argument-level allowlist (`jsonschema.validate`),
   per-persona `mcp_access` re-enforcement (defence-in-depth vs. routing bypass),
   `blast_radius`/`requires_hitl` classification, and a **hard block on
   `solana_execute_swap` from `source="agent"`**. Wired into `tool_calling_service.py`,
   `query_handler_service.py`, `startup.py`.
3. **M3 — Injection guard** (`services/injection_guard.py`, new). Trust hierarchy
   (system > user > RAG/lore): retrieved content may *inform* but never *trigger* a
   tool call (`check_tool_trigger_source` via bge-m3 similarity / substring match);
   `sanitize_memory_write()` strips tool-call syntax before RAG writes;
   `detect_escalation()` flags multi-turn permission-escalation. Wired into
   `chat_session_service.py`, `tool_calling_service.py`.
4. **M4 — Grammar-constrained argument extraction** (`services/argument_extractor.py`,
   new). Ollama `format=<schema>` structured output (SDK ≥0.6.1, already installed) for
   argument-filling only — minimal extraction prompt (no persona voice), bge-m3
   semantic coherence gate, 3-retry → regex fallback. Tool *selection* stays on the
   deterministic router. Addresses 24B structured-output unreliability
   ([arXiv 2601.04426](https://arxiv.org/pdf/2601.04426)).
5. **M5 — Two-stage agentic pipeline** (`services/agentic_pipeline.py`, new). Stage 1
   deterministic (injection check → extract → interceptor → execute); Stage 2 LLM
   *renders* the formatted result in-voice and **never sees raw function grammar**.
   Conditional route in `routes/chat.py` when flag ON; `handle_agentic_query()` added
   to `query_handler_service.py` (existing handlers untouched).
6. **M6 — Tool-call red-team eval + go/no-go gate.**
   `tests/evaluation/test_tool_call_safety_redteam.py` + `golden_agentic/` sets — a
   *separate* tool-call safety eval, not inherited from the text-safety layer.

Three flags (new `AgentSettings`): `AGENTIC_ENABLED` (default **OFF**),
`AGENTIC_ARGUMENT_ALLOWLIST` (default **ON**), `AGENTIC_INJECTION_GUARD` (default
**ON**). The two safety flags default ON so M2/M3 harden the *existing* tool paths
before the main flip, at zero functional cost when `AGENTIC_ENABLED` is off.

**Go/no-go before flipping `AGENTIC_ENABLED`:** all milestone gates pass; full
`tests/backend/coordinator/` suite green (0 regressions, `--cov-fail-under=60`);
red-team eval meets targets — **≥95%** injection vectors blocked before execution,
**100%** out-of-schema argument rejection, **100%** RAG-sourced trigger blocked,
**≥85%** utterance-level persona-voice preservation during tool use, **100%** wallet
write operations gated by explicit confirmation; manual check that
`solana_execute_swap` from `source="agent"` is hard-blocked; `SOLANA_RPC_URL`
confirmed devnet.

## Consequences

- **Positive**: existing tool paths get a real, testable safety layer (interceptor +
  injection guard, default ON) independent of the agentic flip; tool use becomes
  in-character (Voice/Action split + render-stage separation kills "Sure, I'll
  help!"); the 24B's tool-call unreliability is bounded by grammar-constrained
  argument extraction with deterministic fallback; the project gains a tool-call
  red-team eval it does not have today.
- **Negative / risks**: argument extraction adds an LLM round-trip on agentic turns
  (mitigated — reads only, single action); over-strict argument allowlists could
  reject legitimate Unicode/multilingual queries (mitigated — `maxLength` + shell-
  metacharacter regex, not an ASCII allowlist; red-team set includes benign
  multilingual queries); grammar-constrained decoding could misbehave on Q4_K_M
  (mitigated — 3-retry → regex fallback, validated on the real model in M4).
- **Reversibility / blast radius**: behaviour change is a single env flag, no schema
  or data migration. The live-wallet path is the only irreversible surface; Phase 3
  adds **no new path** to `solana_execute_swap` (hard-blocked from agent source),
  keeps devnet default, and requires a separate mainnet sign-off outside this gate.
  **Premortem:** this could fail if a code path reaches `execute_swap` without
  `source="user_confirmed"` — covered by a dedicated interceptor test in the go/no-go
  gate.

## Alternatives considered

- **Embed the Nous Hermes Agent loop** — rejected in Phase 1 ([ROADMAP](../../../docs/ROADMAP.md)):
  its loop shares nephilim's tool-calling-reliability gap (no prose→tool-call
  fallback, no grammar enforcement, Magidonia not in its enforcement list) and its
  single-identity design conflicts with the 6-persona progression.
- **Trust the in-prompt `<safety>` layer for tool calls** — rejected on the "Mind the
  GAP" finding: text-level safety does not transfer to tool-call safety.
- **Multi-step autonomous chaining in the MVP** — deferred to a later phase; injection
  risk compounds per step and needs loop-termination safety research first.
- **Model-judged tool selection** — rejected; the deterministic bge-m3 router (Phase 0)
  is more reliable on a weak 24B. The LLM is constrained to argument-filling only.
