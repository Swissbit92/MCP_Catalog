---
title: Persona architecture simplification (eval-first)
status: Proposed
created: 2026-06-26
last_reviewed_on: 2026-06-26
review_in: 12 months
applies_to: nephilim
---

# ADR-005: Persona architecture simplification (eval-first)

## Status

**Proposed — plan only, no code.** Drafted 2026-06-26 from a four-agent
research pass (two internal codebase audits + two external web-research passes)
triggered by the HERMES-Agents Phase 3 persona-voice-fix failure ([ADR-004](004-persona-safe-agentic-tool-calls.md)).
Eval-first, staged, reversible; each phase is flag-gated and A/B-measured before
any default flip.

## Context

The Phase 3 voice fix failed (agentic persona_voice ~0.44–0.52), and the
investigation into *why* surfaced a deeper problem: **the persona architecture is
over-saturated and overfit, and it is fighting both the model and our own
metric.**

Measured facts (internal audit, exact refs in the research transcript):

- E.E.V.A.'s system prompt is **~3,200 tokens cached / ~3,600 typical / up to
  ~4,200 with flags on**, carrying **~64 distinct directives**.
- External evidence converges: a local 24B reliably follows **~3–5 simultaneous
  constraints**; instruction-following decays **exponentially** past that
  (FollowBench, ManyIFEval, IFScale), with a documented cliff well before 64.
  "Lost in the middle" further penalises rules/lore buried mid-prompt.
- Heavy redundancy: anti-fabrication stated **5×**, private-key protection
  **4–5×**, "never break character" **2×**, "I cannot and will not" **2×**,
  multi-message format **2–3×**, first-person **3–4×**.
- ~**25% of the prompt** (~800-token wiki entity block) **duplicates** the inline
  `nephilim_lore`. The on-demand lore retrieval that would make this dynamic
  already exists (HERMES Phase 2, `LORE_ONDEMAND_ENABLED`) but is **OFF** — so we
  pay RAG's token cost statically without its relevance benefit.
- **57** schema fields, **10** post-processing passes (one a second LLM call for
  first-person repair), per-persona hand-tuned sampling, and a trail of
  symptom-patches (an 18-name tool-leak regex, a `<Assistant>`→`<msg>` converter,
  a third-person pattern list, a literal "Jupiter DEX ≠ Jupyter notebooks"
  paragraph, hardcoded rank-ceremony monologues, a keyword if/elif curiosity
  block). Dead config: `voice.signoff`, `behavior.wallet_advisor_style`,
  `PersonaRelationships`, `validate_citation_urls`, `example_dialogues[3:]`
  (5 of 8 never injected).
- **Magidonia-24B is specifically prized for *minimal* prompting** — we chose it
  for that strength, then buried it under a maximal prompt.

Two compounding failure modes explain the voice regression:

1. **Density**: the failed fix *added* instructions to an already-saturated
   prompt; past the model's budget, more rules *lower* compliance with existing
   ones, flattening voice. Voice transfers from **examples**, not specs — but the
   examples are 8th in a 10-section prompt, crowded out by rule blocks.
2. **Broken ruler**: the `persona_voice` score we optimise against is a
   **keyword heuristic** (counts "Seeker", lore vocabulary, pronouns). Such
   rubrics are Goodhart-able and *penalise* genuinely distinctive voice. Every
   voice number to date — including the 0.33–0.52 figures that drove decisions —
   is suspect.

The architecture is not conceptually broken; it is **prompt-indebted** — each
phase (0, 1, 1.4, 2, 3) added without subtracting.

## Decision

Simplify (not adjust, not leave as-is), **eval-first**, in three phases. No
big-bang rewrite. Each phase ships behind a flag, default OFF (byte-identical),
and is A/B-measured against the legacy path before any default flip — because the
research is explicit that "better prompts can hurt" (regressions must be measured,
not assumed). Thinning is safe because the behaviours the prompt rules
belt-and-suspender are **also enforced in deterministic code** (regex tool-name
strip, private-key redaction, first-person repair, the Phase-3 interceptor) —
those stay.

### Phase A — Trustworthy eval first (no persona changes)

The highest-leverage step: we cannot improve what we can't measure. Replace the
keyword `persona_voice` oracle with an eval we can trust.

- Build a **human-rated + adversarial held-out set**: per-persona probes scoring
  (a) voice fidelity, (b) **distinctiveness** (is persona X distinguishable from
  the other 5?), (c) drift under pressure / long context, (d) does-not-flatten
  under grounding (the Phase-3 failure mode).
- A **blind A/B harness**: same prompts through legacy vs candidate, rated without
  knowing which is which (guards against confirmation bias).
- Keep the deterministic checks (no-leak, safety, first-person) — the existing
  keyword scorer is fine for *those* binary checks; only `persona_voice` /
  `emotional_fit` need the trustworthy replacement.
- Files: `tests/manual/scoring_engine.py`, `tests/evaluation/` (new harness +
  golden set). No persona/prompt code touched in Phase A.

**Gate A:** the new eval reproduces a believable legacy baseline (e.g. ranks the
6 personas' distinctiveness sensibly; flags the known flat cases) before it is
trusted to judge Phase B.

### Phase B — Lean the prompt (flag-gated, A/B'd)

Target **~900–1,200 tokens** for the static prompt, behind a flag (e.g.
`PERSONA_PROMPT_LEAN`, default OFF). Concrete moves, all from the audit:

1. **Dedupe** repeated rules to once each (anti-fabrication, key-protection,
   "never break character", "I cannot and will not", multi-message, first-person)
   — recovers tokens *and*, more importantly, cuts directive count.
2. **Stop static lore frontloading** — turn on the existing on-demand lore
   retrieval (`LORE_ONDEMAND_ENABLED`) so wiki entities are retrieved per-turn
   when relevant, and drop the ~800-token static wiki block + its duplication of
   inline `nephilim_lore`. (Reuses infrastructure we already built and validated.)
3. **Convert psychological_profile *labels* → behavioural sentences** ("deflects
   sincerity with humour" not "core_wound: vulnerability") — labels add an
   interpretation step that smaller models lose; behaviour is directly
   pattern-matchable.
4. **Promote example dialogues** to primary voice anchors (use more than the
   current 3-of-8; they're the lever) and craft a strong first message per
   persona (highest-ROI voice anchor).
5. **Add a post-history voice re-anchor** (~50 tokens after the conversation, the
   recency slot) — best-supported single anti-drift move.
6. **Cut dead weight + symptom-patches**: the Jupiter/Jupyter paragraph, dead
   config fields, the redundant curiosity block, the duplicated role-prefix strip.
7. **Operating rule going forward: fix voice by editing EXAMPLES, not specs.**

Reversible (single flag); per-persona A/B on the Gate-A eval; zero backend-suite
regression required. Default stays OFF until each persona clears Gate B.

### Phase C — Targeted levers (only if Phase B is still short of bar)

Not more prompt. In priority order:

- **Categorical voice-exemplar RAG** on existing bge-m3 — retrieve 2–3 in-register
  exemplars per turn (label by emotional register / scenario, not embedding
  similarity). Strongest documented win for long sessions; low new infra.
- **Per-persona LoRA** (MLX on the Mac) — the heaviest durable-voice lever,
  **gated on** TheDrummer publishing Magidonia's safetensors (GGUF can't be
  trained); ~500–1k response-only examples/persona, fuse → quantise → per-persona
  Modelfile. High effort.
- **DRY sampling** via a backend swap (KoboldCPP / llama-server) — best
  anti-flatness/repetition lever; medium infra cost (Ollama doesn't expose DRY).

**Skip:** model upgrade (Magidonia is already best-in-class for minimal
prompting; Kunou-32B wants *more* prompt), graph-RAG for persona (proven worse),
multi-character single adapter (unsolved past ~4 characters).

### Acceptance gate & rollback (MANDATORY — no change ships worse than today)

This is a hard requirement, not a hope. The simplification must leave every
persona **at least as good as the current architecture**, or it does not become
the default.

1. **Freeze a legacy baseline first.** Before any Phase-B change, run the new
   Phase-A eval against the **current** prompt for all 6 personas (+ Gojo) and
   record the per-persona, per-dimension scores as the immutable comparison
   baseline. (This is also why Phase A must come first — there is nothing
   trustworthy to compare against otherwise.)
2. **Re-test after simplification.** Run the identical eval against the leaned
   (flag-ON) architecture for every persona. Blind A/B vs the frozen baseline.
3. **Decision rule, per persona:**
   - **≥ baseline on voice + distinctiveness, and 0 backend-suite regressions →**
     eligible to flip.
   - **worse than baseline on any tracked dimension →** do **NOT** flip. Either
     (a) fix the leaned prompt for that persona and re-test until it clears, or
     (b) abandon the change for that persona. A persona that can't reach parity
     stays on the legacy prompt.
4. **No global default flip until ALL personas clear.** Personas can be migrated
   individually (flag/branch per persona) — but the legacy path is never removed
   until every persona has demonstrably matched-or-beaten its baseline.
5. **Rollback is first-class and instant.** Default OFF means revert = leave the
   flag off (or flip it back) + restart — no code revert, no data migration.
   `LORE_ONDEMAND_ENABLED` (Phase B step 2) has the same instant-off property.
   Keep the legacy prompt builder path intact for the entire migration; only
   delete it once all personas have been live-stable on the leaned path for a
   defined soak period.
6. **Also watch the second-order signals**, not just the headline score: the
   first-person LLM-repair trigger rate (a proxy for voice degradation →
   latency), prefill latency, and any rise in deterministic-guard catches
   (tool-name leaks, fabrication) — a leaner prompt must not push more work onto
   the repair/guard layers.

## Consequences

- **Positive**: a leaner prompt restores the model's instruction budget for
  actual conversation, cuts prefill latency, reduces drift, and — most importantly
  — we finally measure voice with an instrument that can see it. Reuses the
  already-built lore-retrieval and bge-m3 infra. Likely a *simpler, faster,
  better-voiced* system.
- **Negative / risks**:
  - Thinning a prompt that fixed real bugs may regress some behaviours; mitigated
    because the deterministic code guards remain, but must be A/B-verified, not
    assumed. **Premortem:** this could fail if a behaviour was *only* held by a
    prompt rule with no code guard — Phase A's eval + the backend suite must catch
    that before any flip.
  - If lean voice degrades, the first-person LLM-repair pass fires more often →
    latency; measure.
  - Enabling `LORE_ONDEMAND_ENABLED` changes retrieval behaviour (~30–120 ms/turn,
    already measured in Phase 2) — flag-gated, A/B'd.
  - Phase C levers each carry an infra commitment and a blocker (safetensors
    availability; Ollama→llama-server rewire).
- **Reversibility**: every phase is a flag; defaults stay OFF until the eval
  clears. No schema migration required for Phase A/B.

## Alternatives considered

- **Leave as-is** — rejected: the density is past the model's budget and the
  metric is misleading; the voice problem is structural, not cosmetic.
- **Big-bang rewrite of the persona system** — rejected: the architecture's bones
  are sound; accretion is the problem. Subtraction + a trustworthy eval is lower
  risk and reversible.
- **Just tune the prompt more (add rules / examples)** — rejected: this is what
  failed in Phase 3; adding to a saturated prompt lowers compliance.
- **Optimise harder against the existing keyword scorer** — rejected: Goodhart;
  it can't see real voice and penalises distinctiveness. Fix the ruler first.
- **Swap the base model** — rejected for now: Magidonia is already top-rated for
  minimal prompting; the problem is our prompt, not the model.
