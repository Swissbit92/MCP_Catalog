---
title: Roadmap
status: active
created: 2026-04-19
last_reviewed_on: 2026-06-22
review_in: 3 months
applies_to: nephilim
---

# Roadmap

Near-term dated items only. Strategic direction lives in the ecosystem [VISION.md](../../VISION.md).

## Next (this month)

- [x] Fixed 3 latent bugs surfaced by the coverage push (2026-06-22): `seeker_progression_repository.get_resonance_history` tie ordering (added `, id DESC`); `wallet_registry_repository.soft_delete_wallet` + `soft_delete_by_address` double-delete (now use `cursor.rowcount`); `message_processing_service` 3-message split (regex made greedy). All previously `xfail`-documented tests now pass normally.

## Soon (next quarter)

- [ ] Raise coverage of the live-LLM orchestration services (`query_handler_service`, `chat_session_service`, `tool_calling_service`) — either by mocking the LLM/tool boundary or by counting the `requires_ollama` suite. Main remaining dark area (overall 63%, gate 60%).

## Later (exploratory)

- [ ] TBD

## Shipped

See [CHANGELOG.md](../CHANGELOG.md).
