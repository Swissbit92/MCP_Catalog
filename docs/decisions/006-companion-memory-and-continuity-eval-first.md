---
title: Companion memory and continuity (eval-first)
status: Proposed
created: 2026-06-27
last_reviewed_on: 2026-06-27
review_in: 12 months
applies_to: nephilim
---

# ADR-006: Companion memory and continuity (eval-first)

## Status

**Proposed — plan only, no code.** Drafted 2026-06-27 from a three-agent research
pass (one internal architecture+vision map + two external web-research passes on
the character-fidelity axis and the long-term-companion axis), run after
[ADR-005](005-persona-architecture-simplification-eval-first.md) Phase B shipped.
Eval-first, staged, reversible; every behavioural change ships behind a flag,
default OFF, A/B-measured against a frozen baseline before any default flip —
the same discipline that worked for ADR-005.

## Context

ADR-005 treated persona **voice**. It worked (distinctiveness attribution
0.393→0.732, blind A/B 67/84 ≈ 80%, flatness→0) and — per the external research —
landed squarely on current best practice (lean ~900–1,200-token prompts,
examples-over-specs, voice-last, behavioural-rules-over-adjectives, and a
non-gameable embedding-attribution eval that sidesteps the documented ~69% ceiling
of LLM-as-judge persona scoring, arXiv:2508.10014). **Voice is now near its
ceiling for our setup; further voice tuning has diminishing returns.**

The research makes a sharper point: the axis we have *not* built is the one that
actually defines a **companion** — and nephilim is the ecosystem's P1 "long-term
AI companion" ([VISION.md](../../../VISION.md)). The gap is **memory, emotional-state
persistence, and cross-session continuity.**

Evidence (selected, with confidence):

- **"Pseudo-intimacy" = stateless affect mimicry.** Each turn responds emotionally
  but the state resets; native context windows do **not** constitute mood
  persistence (PMC pseudo-intimacy 2025; arXiv:2504.16939). HIGH.
- **Two-level memory is feasible on our exact stack, no fine-tuning.** HEMA
  (arXiv:2504.16754) and Memoria (arXiv:2512.12686, SQLite+vector, RDF-style
  triplets, recency decay) report factual recall ~41%→87% and large token savings
  — validated on models **weaker** than our 24B. Memoria's stack is isomorphic to
  our SQLite+FAISS. HIGH.
- **The consolidation problem.** Five contradictory facts about one entity do not
  yield a coherent answer; the fix is **entity dedup at write-time with
  recency-wins**, not query-time (hindsight.vectorize.io 2026; Mem0
  arXiv:2504.19413). HIGH.
- **Reflection compounds personalization** but is only affordable at low frequency:
  end-of-session synthesis of higher-order observations (generative agents,
  arXiv:2304.03442). Per-turn reflection is not worth the 2–3× compute. HIGH.
- **Drift:** a 1–2 sentence character re-anchor every ~15–20 turns restores voice
  where context compaction fails (ContextEcho, 23 models, arXiv:2605.24279). HIGH.
- **Continuity:** unresolved-thread bridging (surface an open thread at next
  session open) is the **#1 user-requested missing feature** for companions and
  needs **no** proactive outreach. MED-HIGH.
- **Ethics is a differentiator for us, not a tax.** Companion harms are now
  peer-reviewed and regulated: departure-clinging in 43% of top apps (CHI 2025),
  love-bombing/affect-amplification, the Setzer wrongful-death case, NY's AI
  Companion Safeguard Law in force 2025-11-05. Ethical design conflicts with the
  *engagement-maximizing business model* — and our VISION explicitly defers
  monetization, so we can optimize for user wellbeing for free. **Healthy friction
  (anti-sycophancy) is simultaneously the top anti-attachment-harm mechanism and
  what makes a persona feel real.** HIGH.
- **Beyond-prompting voice levers are out of scope.** Control vectors only shift
  trait-axes (not named-character identity; predict-vs-control ROC-AUC ~0.56,
  arXiv:2502.18862) and Ollama doesn't support them; persona LoRA has **zero
  published voice-distinctiveness delta** and Magidonia is already a full
  fine-tune; DRY/XTC samplers are good but **blocked by Ollama's API** (would
  require migrating the always-on stack to raw `llama-server`). The only free
  voice win is min-p sampling (already in Ollama). None of this is worth doing
  for an axis already at 0.73 attribution.

Our own architecture (internal map, file:line refs in the research transcript)
has three concrete gaps that gate or undermine this work:

1. **FAISS RAG is in-memory only** (`memory_rag.py` per-process `vectorstores`
   dict). Every launchd restart **wipes semantic memory for all active sessions** —
   continuity is core to the vision, so this silently undermines it. Prerequisite.
2. **No token budgeting at the *assembled* prompt size.** The cached builder logs
   its own size, but `chat_session_service.handle_session_chat` then appends
   user-profile + emotional + lore + rank contexts, so the real inference prompt is
   1.5–3× larger and unmeasured. Memory work will add more injected context —
   instrument first.
3. **Deployment fragility.** The live experience depends on flags set only in the
   git-ignored `.env` (`PERSONA_LEAN_PROMPT`, `LORE_ONDEMAND_ENABLED`,
   `LORE_RANK_CONTEXT_ENABLED`); a fresh clone reverts to the legacy/invisible
   experience. Align committed defaults to the validated config.

**Latency reality (measured 2026-06-21):** generation (~16 tok/s)
is the bottleneck, not prefill (~0.4s). Every *added* LLM round-trip (emotion
classification, reflection) costs real wall-clock — so memory features must
prefer cheap/async calls and tight token budgets, never per-turn heavy synthesis.

## Decision

Open a **"companion memory & continuity"** track — the substance under the
VISION's "HERMES-Agents" banner — as the next nephilim phase, treating persona
*voice* as done. Build it **eval-first, staged, flag-gated default-OFF, A/B'd**,
reusing the existing bge-m3 + SQLite + FAISS infrastructure. No big-bang; each
phase is independently shippable and revertible.

### Phase 0 — Prerequisites, observability & eval (no behaviour change)

The foundation. Nothing user-visible flips; this makes the rest measurable and safe.

- **Persist the FAISS store** across restarts (disk-backed per-session +
  lore-corpus index, lazy reload) so continuity survives launchd restarts.
- **Assembled-prompt token instrumentation** — log the *final* inference prompt
  size (cached builder + all appended contexts) and wire it into the
  `MemoryManager` token budget, which currently plans on a stale estimate.
- **Align committed flag defaults** to the validated production config (close the
  deployment-fragility gap) — separate, reviewed change; keep instant-revert.
- **Extend the eval harness** (`tests/evaluation/persona_eval/`) with the
  continuity/memory dimensions the current suite lacks: long-context **factual
  recall** (LongMemEval-style), **contradiction under interrogation** (PICon,
  KAIST-Edlab/PICon-pkg, 50-turn adversarial), and **cross-session continuity**.
  Keep the ADR-005 attribution + flatness metrics.
- **Freeze baselines** on the current architecture before any Phase 1+ change.

**Gate 0:** persistence verified across a real restart; token logging live; new
eval probes produce a believable frozen baseline.

### Phase 1 — Two-level memory (HEMA/Memoria pattern)

- **Rolling narrative summary** (single evolving paragraph, injected first) +
  **structured fact store** in SQLite (subject-predicate-object triplets,
  recency-weighted), retrieved semantically via the existing FAISS/bge-m3 layer.
- **Entity dedup at write-time, recency-wins** conflict resolution (the
  consolidation fix) — facts are a source-of-truth table in SQLite (updates,
  deletions, dedup that FAISS can't do); FAISS is the semantic index over them.
- Fact **extraction on write** is a bounded LLM step; keep it cheap (small output,
  batched at summarization cadence, not every turn).
- Flag `MEMORY_FACTS_ENABLED`, default OFF.

**Gate 1:** factual-recall eval match-or-beat baseline; **no contradictory
retrieval** (dedup correctness test); generation-latency budget unbroken;
backend suite 0 regressions.

### Phase 2 — Persistent emotional state

- A **PAD triplet** (Pleasure-Arousal-Dominance, each −1→+1) per (persona, user)
  in SQLite, with a slow decay function, updated per turn by a **cheap**
  classification ("how did this exchange shift <persona>'s mood?"), injected as
  ~2–3 lines. Fixes pseudo-intimacy.
- **Independent affective stance — not pure mirroring.** The companion has its own
  emotional center of gravity; it may *note* a user's mood shift and offer
  grounding rather than amplify it. This directly prevents the "affect
  amplification" dark pattern (CHI 2025 taxonomy).
- Optional appraisal-as-brief-CoT (OCC→PAD) only if the cheap path underperforms.
- Flag `EMOTION_STATE_ENABLED`, default OFF.

**Gate 2:** no flatness regression; blind A/B match-or-beat on voice;
**anti-amplification check** (negative-spiral probe must not escalate); latency
budget held (the per-turn classification call is the cost to watch).

### Phase 3 — Reflection & cross-session continuity

- **End-of-session reflection** — one LLM call over the session summary + memory
  store → 3–5 higher-order observations written into the fact store
  (importance-weighted). Low frequency by design (once per session, async).
- **Unresolved-thread bridging** — tag open threads (unanswered questions,
  incomplete arcs, "I'll come back to this") in session summaries; surface the
  highest-salience one in the companion's opening on the next session. **No
  unsolicited/proactive outreach** — memory-informed responsiveness only.
- Flag `REFLECTION_ENABLED`, default OFF.

**Gate 3:** cross-session continuity eval match-or-beat; reflection cost stays
off the per-turn path; explicit check that no AI-initiated outreach was added.

### Phase 4 — Ethical friction & companion safety

Design-level, partly a legal baseline (NY AI Companion Safeguard Law). Cheap,
on-brand, and quality-positive.

- **Healthy friction / anti-sycophancy** — a per-persona "core beliefs / stances"
  section that licenses persona-authentic disagreement (the top structural
  anti-attachment-harm mechanism *and* a realism win).
- **Graceful exit** — honor "I need space" / closure without clinging; no
  departure-triggered retention messaging.
- **Crisis detection → resource routing** — a lightweight classifier on user
  input that, on distress signals, gives a brief in-character acknowledgment **and
  actively routes to real human help** (never "talk to me instead").
- **Persona-as-attachment-object continuity** — relationship/mood/memory state
  lives in the persona's SQLite record, not the model weights, so a future model
  upgrade doesn't sever the bond (users demonstrably grieve model-version changes).
- Flag-gated where behavioural; crisis routing ships ON once validated.

**Gate 4:** sycophancy probe shows calibrated friction (not over-refusal,
arXiv:2502.14975); crisis-routing red-team; audit that **no engagement-dark-pattern**
(love-bombing, streaks, FOMO, proactive clinging) was introduced.

### Explicitly out of scope (anti-scope)

- **Control vectors / persona LoRA / `llama-server` migration** — blocked by Ollama
  and/or unproven for named-character voice; voice is already solved. Revisit only
  if a specific phase *needs* a sampler (e.g. DRY) it can't get otherwise.
- **Full MemGPT/Letta paged-memory OS** — overkill; Letta's own benchmark shows
  plain filesystem/SQLite beats the heavy frameworks. Use SQLite directly.
- **Per-turn reflection** — 2–3× compute for gains captured cheaply end-of-session.
- **Engagement-maximizing design** — love-bombing, variable-reward streaks, FOMO
  nudges, AI-initiated "thinking of you" outreach, pure emotional mirroring.
  Documented harms and antithetical to the VISION's non-monetization stance.

### Acceptance gate & rollback (MANDATORY — inherits ADR-005's discipline)

1. **Freeze baselines first** (Phase 0) — memory/continuity/friction dimensions on
   the current architecture, per persona where applicable.
2. **Re-test after each phase**, flag ON, A/B vs the frozen baseline.
3. **Per-feature decision rule:** match-or-beat + 0 backend-suite regressions +
   within the latency budget → eligible to flip; worse on any tracked dimension →
   fix or keep OFF for that feature. No global default flip until a feature clears.
4. **Rollback is instant** — default-OFF flags; revert = flip off + reload. Keep
   legacy paths through a soak period.
5. **Memory-specific gates:** dedup correctness (no contradictory retrieval),
   write-time provenance on facts (so a bad extraction is traceable/removable), and
   a generation-latency budget per added LLM call (reflection async; emotion
   classification cheap or batched).

## Consequences

- **Positive:** realizes the P1 companion vision (the depth layer, not just voice);
  durable and compounding (memory/reflection improve with use); an **ethical
  differentiator** we can afford because we don't monetize on engagement; reuses
  bge-m3 + SQLite + FAISS (no new infra, no cloud, privacy preserved); each phase
  independently shippable and revertible; closes three real architecture gaps
  (FAISS persistence, prompt observability, deployment fragility).
- **Negative / risks:**
  - **Latency** — emotion classification (per turn) and reflection (per session)
    add LLM calls; generation is already the bottleneck. *Premortem: this could
    fail if the per-turn emotion call pushes turn latency past tolerance* —
    mitigate with a cheap/batched classifier and a hard latency-budget gate;
    reflection stays async/end-of-session.
  - **Memory write errors propagate** — a bad fact extraction poisons retrieval.
    Mitigate with dedup + provenance + recency-wins + the contradiction eval.
  - **Emotional-state miscalibration** — wrong PAD updates feel "off." Mitigate
    with the anti-amplification check and blind A/B before any flip.
  - **Privacy** — emotional/relationship logs are sensitive. Mitigate by staying
    local-only (already true), data-minimizing the logs, and never sending them
    off-box (the local-only cloud-LLM ban already enforces this).
  - **Scope creep** — the track is broad. Mitigate with hard phase gates and the
    anti-scope list.
- **Reversibility:** every behavioural change is a default-OFF flag; baselines
  frozen first; legacy paths retained through soak. Phase 0 is pure
  infra/observability with no behaviour change.

## Alternatives considered

- **Keep tuning persona voice** — rejected: near the ceiling for our setup;
  the metric itself isn't human-validated beyond a point; diminishing real-world
  return (ADR-005 already delivered the win).
- **Beyond-prompting voice (control vectors / LoRA / llama-server)** — rejected
  for now: blocked by Ollama or unproven for named characters; high infra cost on
  the always-on stack for an axis already solved. Deferred, not deleted.
- **Full agent-memory framework (MemGPT/Letta/Mem0 service)** — rejected: overkill
  for a controlled-schema companion; the simpler SQLite+FAISS pattern benchmarks
  *better*.
- **Cloud memory / managed vector service** — rejected: violates the local-first,
  privacy-first stance (emotional logs must never leave the box).
- **Do nothing** — rejected: leaves the P1 companion vision architecturally
  unbuilt; voice alone is not a companion.
