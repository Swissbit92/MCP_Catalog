# src/coordinator/di/__init__.py
"""Composition-root submodules, split out of the former monolithic ``startup.py``.

Each module here owns one cluster of long-lived singletons (module-level
globals + their ``get_*``/``init_*`` functions):

- ``repositories`` — the 12 SQLite repositories + DB/Alembic init + orphaned-
  session cleanup.
- ``services`` — Brave MCP client, memory manager, Phase 3 RAG/fact-extraction
  subsystem, and the tool-call interceptor.
- ``jupiter`` — Jupiter MCP client/ops, wallet execution + strategy services,
  and the autonomous strategy scheduler.

``startup.py`` re-exports every ``get_*``/``init_*`` name from these modules
so ``src.coordinator.startup.get_X`` keeps working exactly as before — that
attribute is the seam tests patch and other modules resolve through
(``from . import startup; startup.get_X()``). See ``startup.py``'s module
docstring for why the re-export (not a direct import elsewhere) is the
contract to preserve.
"""
