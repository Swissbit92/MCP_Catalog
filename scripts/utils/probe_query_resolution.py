#!/usr/bin/env python
"""Live probe: does the real persona LLM resolve deictic follow-ups well?

Exercises QueryResolutionService end-to-end against live Ollama (no mocks), so
we can eyeball the actual rewrites the 24B produces before flipping the flag on.

Run from the worktree venv:
  SEARCH_QUERY_RESOLUTION_ENABLED=true .venv/bin/python scripts/utils/probe_query_resolution.py
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("SEARCH_QUERY_RESOLUTION_ENABLED", "true")

from src.coordinator.config import get_settings  # noqa: E402
from src.coordinator.services.llm_completion_service import LLMCompletionService  # noqa: E402
from src.coordinator.services.query_resolution_service import QueryResolutionService  # noqa: E402

get_settings.cache_clear()
settings = get_settings()

llm = LLMCompletionService(
    base=settings.ollama.base,
    model=settings.ollama.model,
    temperature=0.1,
)
svc = QueryResolutionService(llm_service=llm)

# (compiled conversation, latest turn) cases — the [ ] marks the resolution target.
CASES = [
    # The actual incident.
    (
        "User: how is the football world cup 2026 in the US going? is switzerland still in it and performing?\n\n"
        "Assistant: Ah, the beautiful game. I do not follow current events as they unfold, Seeker.\n\n"
        "User: search the web for it",
        "search the web for it",
    ),
    # Topic-switch follow-up.
    (
        "User: what's the weather forecast for Zurich this week\n\n"
        "Assistant: I cannot see the skies from here.\n\n"
        "User: and Geneva?",
        "and Geneva?",
    ),
    # Deictic mid-conversation.
    (
        "User: tell me about the new James Webb telescope exoplanet discovery\n\n"
        "Assistant: The void holds many secrets.\n\n"
        "User: look it up online",
        "look it up online",
    ),
    # Self-contained query that should NOT be over-rewritten (passthrough).
    (
        "User: hello\n\nAssistant: Greetings, Seeker.\n\n"
        "User: what is the current bitcoin price in usd",
        "what is the current bitcoin price in usd",
    ),
]


def main() -> int:
    print(f"Model: {settings.ollama.model}")
    print(f"query_resolution_enabled: {settings.search.query_resolution_enabled}\n")
    for i, (prompt, latest) in enumerate(CASES, 1):
        resolved = svc.resolve(prompt)
        changed = "REWRITE" if resolved.strip() != latest.strip() else "passthrough"
        print(f"[{i}] latest : {latest!r}")
        print(f"    result: {resolved!r}   ({changed})\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
