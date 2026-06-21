---
title: Architecture
status: active
created: 2026-04-19
last_reviewed_on: 2026-04-19
review_in: 6 months
applies_to: nephilim
---

# Architecture

Reference-style: tables and diagrams, not prose narratives.

## System context

```
[External input] → nephilim → [Output / downstream consumer]
```

## Components

| Component | Responsibility | Module |
|-----------|----------------|--------|
| TBD       | TBD            | TBD    |

## Data

| Source | Format | Writer | Readers |
|--------|--------|--------|---------|
| TBD    | TBD    | TBD    | TBD     |

## Key invariants

- TBD

## Cross-repo contracts

See ecosystem-level contracts (nephilim is read-only; these apply to CRA / btc_price_tracker):
- [../../docs/shared/indicator_api.md](../../docs/shared/indicator_api.md)
- [../../docs/shared/launchd_schedule.md](../../docs/shared/launchd_schedule.md)

## Decisions

Architectural decisions affecting this repo live in [decisions/](decisions/).
