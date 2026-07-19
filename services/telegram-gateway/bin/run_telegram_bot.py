#!/usr/bin/env python3
"""Entrypoint: run the eeva-telegram long-polling bot.

Single-instance guard via an flock'd lock file: Telegram allows only ONE poller
per bot token (a second getUpdates poller gets HTTP 409 Conflict). If launchd
restarts overlap, the second process exits cleanly rather than flapping.

Multi-instance (one process per persona/bot-token): set ``EEVA_TG_INSTANCE`` to
a short name (e.g. ``gwen``). That selects the env file ``.env.<instance>`` and
a PER-INSTANCE lock ``data/bot.<instance>.lock`` — so two bots (each its own
token) run side by side without colliding on the singleton lock. Unset (the
default) = the original single-bot behavior, byte-identical: ``.env`` +
``data/bot.lock``. Each instance still enforces ONE poller for ITS token.
"""

from __future__ import annotations

import fcntl
import logging
import os
import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from eeva_telegram.bot import build_application  # noqa: E402
from eeva_telegram.config import load_config  # noqa: E402
from eeva_telegram.logging_setup import configure_logging  # noqa: E402

logger = logging.getLogger("eeva_telegram")


def _instance_name() -> str:
    """Sanitized EEVA_TG_INSTANCE ('' = default single-bot). Restricted to
    [a-z0-9_-] so it can't traverse paths or collide via odd characters."""
    raw = (os.getenv("EEVA_TG_INSTANCE") or "").strip().lower()
    return re.sub(r"[^a-z0-9_-]", "", raw)


def _paths_for_instance(instance: str) -> tuple[Path, Path]:
    """Return (env_file, lock_file) for this instance. Default instance keeps
    the historical paths exactly (.env, data/bot.lock)."""
    if not instance:
        return _PROJECT_ROOT / ".env", _PROJECT_ROOT / "data" / "bot.lock"
    return (
        _PROJECT_ROOT / f".env.{instance}",
        _PROJECT_ROOT / "data" / f"bot.{instance}.lock",
    )


def _acquire_singleton_lock(lock_path: Path):
    """Return the held lock file handle, or exit(0) if another instance holds it."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    # Intentionally NOT a context manager: the fd must stay open for the whole
    # process lifetime so the advisory lock is held until the bot exits.
    handle = open(lock_path, "w")  # noqa: SIM115
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        logger.warning(
            "Another eeva-telegram instance holds %s — exiting.", lock_path.name
        )
        sys.exit(0)
    return handle


def main() -> None:
    configure_logging()
    instance = _instance_name()
    env_file, lock_path = _paths_for_instance(instance)
    _lock = _acquire_singleton_lock(lock_path)  # held for process lifetime  # noqa: F841
    if instance:
        logger.info("Instance '%s' — env=%s lock=%s", instance, env_file.name, lock_path.name)
    config = load_config(env_path=env_file)
    logger.info(
        "Starting eeva-telegram: %d allowed chat(s), backend=%s, default persona=%s",
        len(config.allowed_chat_ids),
        config.nephilim_base_url,
        config.default_persona_key,
    )
    application = build_application(config)
    # run_polling owns the event loop and blocks until SIGINT/SIGTERM.
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
