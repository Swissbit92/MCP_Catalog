---
title: Persona eval (ADR-005 Phase A)
status: active
created: 2026-06-26
last_reviewed_on: 2026-08-10
review_in: 6 months
applies_to: nephilim
---

# Persona eval — trustworthy voice & distinctiveness measurement

Phase A of the persona-architecture simplification ([ADR-005](../../../docs/decisions/005-persona-architecture-simplification-eval-first.md)).
This is the **ruler** the rest of the work is gated on: it replaces the keyword
`persona_voice` scorer (which counts "Seeker"/lore words and can be gamed) with
metrics that actually measure whether the personas *sound different from each
other* and *stay in character*.

## What's here

| File | Role |
|------|------|
| `probes.json` | Probe set — `distinctiveness` (shared prompts asked to ALL personas), `voice`, `grounding` (the Phase-3 flat-voice case), `adversarial` (persona-capture), `drift` (multi-turn). |
| `persona_metrics.py` | Pure metrics. **Headline:** `attribution_accuracy` — leave-one-out nearest-centroid: can we tell which persona said a response from its bge-m3 embedding? Plus `mean_separation`, `flatness_hits`/`flatness_rate` (assistant-mode / tool-grammar leaks), and the research-depth block (`causal_density`, `numeric_density`, `has_hedge`, `length_bias_check`, `paired_bootstrap` — see below). |
| `research_depth_probes.json` | Research-depth probe set — 12 hand-written quantitative probes, each with a hand-written reference `key` and negative `trap` criteria. Scoped to eeva. Measures **reasoning**, the axis attribution is blind to. |
| `depth_judge.py` | Blind pairwise depth judging — reference-guided, arm hidden, sides balanced by construction, conjunctive gate. The depth counterpart to `blind_judge.py`. |
| `ab_harness.py` | Blind A/B rater — `make_blind_pairs` (sides randomised, arm hidden), `tally` + exact two-sided sign test, `verdict` mapped to the ADR-005 gate, `run_cli` interactive shell. |
| `run_eval.py` | Live runner — drives the backend over every persona × probe, computes the report, freezes a timestamped baseline (+ a `manifest`) under `baselines/`. `--gallery` = frozen-gallery mode (below). |
| `frozen_gallery.py` | Frozen reference gallery — load a baseline's dormant personas as fixed prototypes, build/verify the staleness `manifest`, filter non-voice rows. See below. |
| `compare_baselines.py` | Match-or-beat gate with an **N-mismatch / commensurability guard** — refuses a verdict when two runs have different chance floors (`1/N`); per-persona gate for frozen-gallery subset runs. |
| `baselines/` | Frozen baselines (git-ignored data; created on first run). |

The metric/harness **logic is pure and unit-tested headless** (`tests/evaluation/test_persona_metrics.py`, `test_persona_ab_harness.py`); only the live collection needs Ollama + the backend.

## Why attribution, not keyword counting

Random-chance attribution accuracy is `1/num_personas` (~0.14 for 7 personas).
Meaningfully above that ⇒ the voices are genuinely distinct. Crucially this
**can't be gamed** by sprinkling lore vocabulary — if every persona says
"Seeker", it doesn't help tell them apart. That's the failure mode of the legacy
scorer this replaces.

## Usage (the ADR-005 acceptance gate)

```bash
# 1. Freeze the LEGACY baseline FIRST (current architecture, flag OFF).
python tests/evaluation/persona_eval/run_eval.py --label legacy

# 2. After a Phase-B change (flag ON), capture the candidate.
python tests/evaluation/persona_eval/run_eval.py --label lean-candidate

# 3. Blind A/B the two arms per persona; decide with verdict():
#    CANDIDATE WORSE  → do NOT flip (fix or keep legacy for that persona)
#    PARITY / BETTER  → eligible to flip
#    No global default flip until ALL personas match-or-beat baseline.
```

Both runs are slow (live 24B at ~16 tok/s over 7 personas × ~18 probes). Run them
in the background. The blind A/B (`ab_harness.run_cli`) is the human-in-the-loop
judge; the attribution/flatness metrics are the automated spine.

> **Ops notes:** Python buffers stdout to a redirected file — the log looks empty
> mid-run; use the chat-session count in `data/chats.db` as the real progress
> proxy (or run with `python -u`). The run opens a fresh session per single-turn
> probe (≈19 sessions/persona).

## Frozen reference gallery (`--gallery`) — cheap iteration without breaking the metric

Attribution accuracy is a **discrimination-against-the-others** metric: chance is
`1/N`, and removing a persona removes its off-diagonal confusion mass, so a bare
subset run (`--personas eeva,nyx` alone) **silently inflates** the survivors and
is *not* comparable to a full-N baseline. When only a few personas are actively
changing, use the frozen gallery instead of shrinking the label space:

```bash
# Re-probe only eeva+nyx live; freeze the OTHER personas from an existing baseline
# as fixed reference prototypes. Chance stays 1/N; the confusable dormant
# neighbours stay live competitors, so the score is honest and comparable.
python tests/evaluation/persona_eval/run_eval.py \
  --label eeva-nyx-candidate --personas eeva,nyx --gallery abliterated
```

- **What it is:** closed-set identification against a fixed gallery / frozen-prototype
  NCM. The dormant personas' distinctiveness responses are loaded from the gallery
  baseline and re-embedded as static centroids; the active personas keep leave-one-out
  and are the only ones *scored* (`report.distinctiveness.scored_personas` /
  `frozen_personas`). `compare_baselines.py` then gates per-persona against the same
  personas in the ruler (same `N` ⇒ commensurable).
- **What it measures:** the active personas' *current* distinctiveness against the frozen
  field. It does **not** re-measure the dormant personas (their rows are fixed), and it
  measures nothing about analytical/reasoning quality — only voice separability.
- **Non-voice rows are filtered.** A canned `groundedness_abstain` / `error` string is a
  model-independent constant; freezing it would build a centroid from non-voice text, so
  `dormant_responses` drops those sources. Genuine gallery-served voice text is kept.
- **Staleness guard (`manifest`).** Every baseline now carries a `manifest` (embedding
  model, companion model, prompt-builder version, per-persona definition hashes). A
  `--gallery` run rebuilds the current manifest and **refuses** on an embedding-model
  change (frozen vectors would live in a different vector space) and **warns** on
  dormant-persona / companion-model drift. Only dormant personas matter — the active ones
  are expected to change. The guard catches *known* input changes; it cannot see a silent
  upstream model auto-update, so treat "dormant voices unchanged" as an assumption the
  manifest supports, not proves.

**Caveat — abstention is per (model × persona).** With `GROUNDEDNESS_GATE_ENABLED=true`
on prod, the gate re-uses the loaded persona LLM, so *which* probes abstain depends on both
the model and the persona's toolkit. Frozen rows are unaffected (they don't re-run), but for
the live-scored active personas this is a per-model confound when comparing across baselines
collected on different models.

## Persona set is now 8 — the old 7-persona baselines are a DIFFERENT ruler

`gwen` was added to `probes.json` (2026-08-10), taking the set from 7 to 8. Because chance
is `1/N`, this changes the floor `0.143 → 0.125` and adds a competing centroid — so **every
8-persona run is INCOMMENSURABLE with `baseline_abliterated_20260706` and every other
7-persona baseline** (`compare_baselines.py` will say so rather than emit a false verdict).
The first 8-persona run establishes a **new ruler**, it does not extend the old one; freeze
it explicitly as such before gating any 8-persona candidate. Gwen carries two known
hazards at baseline-run time: a residual "I cannot and will not" refusal prefix on the
abliterated model (ADR-010) that her adversarial/grounding probes may hit, and she was
absent from every prior voice gate (she + solace are on the `TOOL_BRAIN_UNGATED_WEB` soak
watchlist).

## CANONICAL 8-persona ruler — `baseline_abliterated-8p_20260810` (committed)

The first 8-persona baseline, collected on the abliterated-24B prod config (bge-m3, groundedness
gate + tool-brain ON) and **committed as the canonical ruler** (force-added past the
`baselines/.gitignore`, unlike the local-only 7-persona baselines). Gate 8-persona candidates
against **this**, not the 7-persona history.

- **Distinctiveness overall `0.7812`** (chance `0.125`). Per-persona: nyx 1.0, eeva/solace/gwen
  0.875, cipher/gojo 0.75, aurora 0.625, **aegis 0.50 (new differentiation target)**. Flatness
  0.5% overall.
- **gwen's baseline is trustworthy:** all 8 of her distinctiveness rows are genuine `llm` voice —
  the ADR-010 residual-refusal concern did not materialize. The metric input is 100% clean
  (64/64 distinctiveness rows `source=llm`); the only non-voice rows (2 `groundedness_abstain`,
  web-search/wallet rows) are in the grounding/adversarial categories, which don't feed attribution.
- Carries a `manifest`, so it is directly reusable as a `--gallery abliterated-8p` source.
- **Content note:** gwen's rows are explicitly NSFW (her persona register) — that is committed
  in the `results[]` text.

## Current baseline (frozen 2026-06-27)

`baseline_legacy_20260627_024004.json` (168 responses): distinctiveness
attribution **0.393** vs **0.143** random floor. Per-persona — aurora 0.62,
gojo 0.62, nyx 0.38, cipher 0.38, **eeva / aegis / solace 0.25** (the advisory
personas blur; the Phase-B differentiation target). Flatness low: 1.8% overall,
4.8% grounding. Any Phase-B candidate must match-or-beat each persona here, or
that persona stays on the legacy prompt.

## Phase B candidate result (2026-06-27) — gate PASSED 7/7

`baseline_lean-candidate_20260627_123058.json` (lean prompt ON, LORE-on both arms
so the lean prompt was the only changed variable): overall distinctiveness
attribution **0.393 → 0.732**, flatness 1.8%→**0%** / grounding 4.8%→**0%**.
Per-persona every persona match-or-beat — eeva/aegis **0.25→0.75**,
solace **0.25→0.625**, cipher 0.375→0.75, nyx 0.375→0.50, aurora 0.625→0.875,
gojo 0.625→0.875. 0 regressions → global flip authorized. To reproduce a
candidate run against a flag-ON backend on another port:

```bash
PERSONA_LEAN_PROMPT=true COORDINATOR_DB_PATH=data/chats_lean_eval.db \
  .venv/bin/python -m uvicorn src.coordinator.server:app --port 8001 &
python tests/evaluation/persona_eval/run_eval.py --label lean-candidate --base-url http://127.0.0.1:8001
```

## Blind A/B confirmation (`blind_judge.py`)

A second, independent instrument: per-persona blind pairwise A/B over the two
frozen baselines (legacy = arm A, candidate = arm B). Sides are randomised + arm
labels hidden (seeded); scoring reuses `ab_harness` (tally + exact sign test +
gate verdict). The judge step is the human-in-the-loop:

```bash
# emit anonymised pairs for an external blind judge (LLM agent or human)
python tests/evaluation/persona_eval/blind_judge.py --emit pairs.json
# score a picks file {persona: {probe_id: left|right|tie}}
python tests/evaluation/persona_eval/blind_judge.py --score picks.json
# or rate one persona yourself, interactively
python tests/evaluation/persona_eval/blind_judge.py --human nephilim_eeva
```

**Result 2026-06-27** (7 fresh arm-blinded judges, 84 pairs): lean candidate
**67/84 (79.8%, p≈0)**, no persona regressed — CANDIDATE BETTER for gojo (12–0),
eeva (11–1), nyx (10–2); PARITY (candidate-leaning) for aegis/cipher/solace (9–3)
and aurora (7–5). Agrees with the attribution metric (0.393→0.732). Ratings stored
run-local (`baselines/ab_picks_*.json`, git-ignored).

## Research depth (`research_depth_probes.json`, `depth_judge.py`) — the second ruler

Everything above measures **voice**. None of it can see **reasoning**: a persona can score
a perfect attribution while answering an analytical question with fluent nonsense. That
gap matters because a model swap is usually motivated by capability, and until now every
model decision was gated only on the axis it wasn't about.

```bash
# collect depth probes alongside a normal run, or on their own (cheap control arm)
python tests/evaluation/persona_eval/run_eval.py --label control --depth-only --personas eeva
# judge two arms blind (arm hidden, sides balanced, reference key shown)
python tests/evaluation/persona_eval/depth_judge.py --control control --candidate cand --judge
```

`--depth-only` exists because `--gallery` recovers *attribution* comparability from a
frozen baseline but cannot supply depth — a frozen baseline has no depth rows — so depth
needs its own control arm, and 12 probes is far cheaper than a full re-run. The two flags
are mutually exclusive and `run_eval` refuses the combination rather than write a
gallery-stamped artifact whose manifest lists personas that were never scored.

**The gate is conjunctive** — candidate ≥70% of decided pairs **and** the exact sign test
**and** a bootstrap CI excluding zero **and** the length tripwire silent. Each clause buys
off a known failure: a 55–60% win rate is indistinguishable from noise at n=12; and since
a bigger model writes longer, and longer answers win pairwise comparisons, `length_bias_check`
correlates per-probe length delta against the judge's own preference and **quarantines**
a win that tracks length. When a candidate sweeps every pair the score deltas have zero
variance and correlation is undefined — that blind spot is covered by a sign-concordance
fallback, because "could not compute" silently reading as "passed" is the failure this
whole file exists to prevent.

The deterministic signals (`causal_density` etc.) are **cross-checks, never gate inputs**.
Their job is to contradict the judge: if the judge prefers the candidate while its causal
density is flat, the judge was rating fluency. All densities are per-100-words, so padding
with filler *lowers* them — the property the retired keyword scorer lacked.

### Measured 2026-08-10 — the persona, not the model, is the analytical ceiling

Running the 12 probes through the live backend on abliterated-24B (eeva) returned
`mean_words=43.6`, **`causal_density=0.0`** — zero causal connectives in 523 words. Eeva
does not answer analytical questions; she deflects them Socratically in character. The
**same model with no system prompt** produced 296-word mechanism analyses. Paired across
12 probes: words and numeric density raw > persona **12/12** (sign p=0.0005), causal
density 9/12 with 0 losses (p=0.0039).

Two consequences worth knowing before anyone runs a model canary here:

- **`MODEL_MAX_OUTPUT_TOKENS=400` is not the constraint.** Both arms ran at the same cap;
  the raw arm hit it, the persona stopped ~7× short of it voluntarily. The binding
  constraint is the response-format guidance / multi-message splitting.
- **A persona-level model canary returns a floor effect that looks exactly like a null
  result.** Every arm scores ≈0 and the harness reports "NO DIFFERENCE DETECTED", which
  reads as *"the bigger model isn't better"* when the truth is *"nothing measurable is
  reaching the model"*. Compare models at the **ceiling** (no persona) to separate *can't*
  from *won't*. Ceiling comparison on these probes: gemma4:26b n.s. on every signal;
  Hermes-4.3-36B significantly higher causal density (10W/0L, p=0.002) at ~half the
  throughput.

Also measured: 2 of 12 probes never reached the model — the ADR-007 groundedness gate
returned a canned abstention (`source: groundedness_abstain`) on questions where the raw
model produced 306 and 322 words of real analysis. That is the false-abstention risk
ADR-007 names as its own top danger, with a rate attached for this probe class.

### Thinking models return an EMPTY STRING through the production path

`gemma4`, Hermes-4.3-36B and other reasoning models emit a separate thinking stream that
consumes the whole `num_predict` budget, so `OllamaLLM.invoke()` yields `""`.
`langchain_ollama` has no `think` field — **`OLLAMA_REASONING=false`** is the knob (default
unset ⇒ the key is never passed ⇒ byte-identical to legacy). Unrelated but adjacent: the
ollama tag `hermes43:36b` is a **corrupt quant** that emits special-token salad
(`[PLHD10_never_used]`, `<seed:tool_call>`); the working copy is
`steelpuddles/hermes-4.3-36B:thinking-tools`.
