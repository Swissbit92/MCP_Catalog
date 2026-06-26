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
