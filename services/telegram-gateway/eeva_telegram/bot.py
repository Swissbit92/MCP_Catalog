"""Application factory: wires config -> handlers -> nephilim client/session store."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from . import handlers
from .config import TelegramConfig
from .handlers import Gateway
from .nephilim_client import NephilimClient
from .session_store import SessionStore

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB_PATH = _PROJECT_ROOT / "data" / "sessions.sqlite3"


async def _post_shutdown(application: Application) -> None:
    """Release the nephilim HTTP client and close the session store on shutdown."""
    gateway: Gateway = application.bot_data.get("gateway")
    if gateway is not None:
        await gateway.client.aclose()
        gateway.store.close()


def build_application(config: TelegramConfig, db_path: Path | None = None) -> Application:
    """Build a fully-wired PTB Application ready for run_polling()."""
    application = ApplicationBuilder().token(config.bot_token).post_shutdown(_post_shutdown).build()

    gateway = Gateway(
        config=config,
        client=NephilimClient(config.nephilim_base_url, config.request_timeout_seconds),
        store=SessionStore(db_path or _DEFAULT_DB_PATH),
        llm_lock=asyncio.Lock(),
    )
    application.bot_data["gateway"] = gateway

    application.add_handler(CommandHandler("start", handlers.start_command))
    application.add_handler(CommandHandler("reset", handlers.reset_command))
    application.add_handler(CommandHandler("tools", handlers.tools_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.text_message))
    # Any non-text, non-command content (media, voice, stickers, docs).
    application.add_handler(MessageHandler((filters.ALL & ~filters.TEXT) & ~filters.COMMAND, handlers.non_text_message))
    application.add_error_handler(_typed_error_handler)

    return application


async def _typed_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handlers.on_error(update, context)
