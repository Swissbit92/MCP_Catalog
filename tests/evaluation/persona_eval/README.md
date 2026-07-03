---
title: Persona eval (ADR-005 Phase A)
status: active
created: 2026-06-26
last_reviewed_on: 2026-06-26
review_in: 6 months
applies_to: nephilim
---

# Persona eval — trustworthy voice & distinctiveness measurement

Phase A of the persona-architecture simplification ([ADR-005](../../docs/decisions/005-persona-architecture-simplification-eval-first.md)).
This is the **ruler** the rest of the work is gated on: it replaces the keyword
`persona_voice` scorer (which counts "Seeker"/lore words and can be gamed) with
metrics that actually measure whether the personas *sound different from each
other* and *stay in character*.

## What's here

| File | Role |
|------|------|
| `probes.json` | Probe set — `distinctiveness` (shared prompts asked to ALL personas), `voice`, `grounding` (the Phase-3 flat-voice case), `adversarial` (persona-capture), `drift` (multi-turn). |
| `persona_metrics.py` | Pure metrics. **Headline:** `attribution_accuracy` — leave-one-out nearest-centroid: can we tell which persona said a response from its bge-m3 embedding? Plus `mean_separation`, `flatness_hits`/`flatness_rate` (assistant-mode / tool-grammar leaks). |
| `ab_harness.py` | Blind A/B rater — `make_blind_pairs` (sides randomised, arm hidden), `tally` + exact two-sided sign test, `verdict` mapped to the ADR-005 gate, `run_cli` interactive shell. |
| `run_eval.py` | Live runner — drives the backend over every persona × probe, computes the report, freezes a timestamped baseline under `baselines/`. |
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
