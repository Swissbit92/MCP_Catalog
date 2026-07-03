# src/coordinator/jupiter/email_service.py
"""Async trade notification email service using aiosmtplib.

Sends per-trade and daily-summary email notifications after Jupiter swaps execute.
Email is optional — disabled by default and enabled via EMAIL_ENABLED=true in .env.

All functions are fire-and-forget: they log errors but never raise, ensuring
a failed email cannot interrupt trade execution or strategy scheduling.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def _get_email_settings():
    """Lazy import to avoid circular imports at module load time."""
    from ..config import get_settings
    return get_settings().email


# ---------------------------------------------------------------------------
# Per-trade notification
# ---------------------------------------------------------------------------

async def send_trade_notification(trade_doc: dict) -> bool:
    """Send an email notification after a trade executes.

    Called by wallet_execution_service.py after every confirmed swap.
    Silently returns False if email is disabled or aiosmtplib is not installed.

    Args:
        trade_doc: The wallet_trades MongoDB document containing trade details.
                   Expected keys: action, pair, amount_in, amount_in_token,
                   amount_out, amount_out_token, tx_signature, strategy_id,
                   execution_mode, timestamp.

    Returns:
        True if email was sent successfully, False otherwise.
    """
    email_cfg = _get_email_settings()

    if not email_cfg.is_enabled:
        logger.debug("Email notifications disabled — skipping trade notification")
        return False

    try:
        import aiosmtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
    except ImportError:
        logger.warning("aiosmtplib not installed — email notification skipped")
        return False

    try:
        subject, body = _build_trade_email(trade_doc)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = email_cfg.from_addr or email_cfg.username
        msg["To"] = email_cfg.to_addr
        msg.attach(MIMEText(body, "plain"))

        await aiosmtplib.send(
            msg,
            hostname=email_cfg.smtp_host,
            port=email_cfg.smtp_port,
            username=email_cfg.username,
            password=email_cfg.password,
            start_tls=True,
        )

        logger.info(
            f"Trade notification sent: tx={trade_doc.get('tx_signature', 'unknown')}"
        )
        return True

    except Exception as exc:
        logger.error(f"Failed to send trade notification: {exc}")
        return False


# ---------------------------------------------------------------------------
# Daily strategy summary
# ---------------------------------------------------------------------------

async def send_strategy_summary(
    strategy_id: str,
    trades_today: list[dict],
    pnl_usdc: Optional[float] = None,
) -> bool:
    """Send a daily strategy performance summary email.

    Intended to be triggered by the strategy scheduler at end-of-day
    (or on-demand via the /wallet/strategies/{id}/summary endpoint).

    Args:
        strategy_id: Identifier for the strategy (e.g. 'sol_rsi_001')
        trades_today: List of wallet_trades documents executed today
        pnl_usdc: Optional pre-computed P&L in USDC. If None, not shown.

    Returns:
        True if email was sent successfully, False otherwise.
    """
    email_cfg = _get_email_settings()

    if not email_cfg.is_enabled:
        logger.debug("Email notifications disabled — skipping strategy summary")
        return False

    try:
        import aiosmtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
    except ImportError:
        logger.warning("aiosmtplib not installed — strategy summary email skipped")
        return False

    try:
        trade_count = len(trades_today)
        subject = f"[E.E.V.A.] Daily Summary — {strategy_id} ({trade_count} trades)"

        lines = [
            "E.E.V.A. Strategy Daily Summary",
            "=" * 40,
            f"Strategy: {strategy_id}",
            f"Trades today: {trade_count}",
        ]

        if pnl_usdc is not None:
            pnl_sign = "+" if pnl_usdc >= 0 else ""
            lines.append(f"Estimated P&L: {pnl_sign}{pnl_usdc:.2f} USDC")

        if trades_today:
            lines.append("")
            lines.append("Trade log:")
            for t in trades_today:
                action = t.get("action", "?").upper()
                amount_in = t.get("amount_in", 0)
                token_in = t.get("amount_in_token", "?")
                amount_out = t.get("amount_out", 0)
                token_out = t.get("amount_out_token", "?")
                sig = t.get("tx_signature", "N/A")
                lines.append(
                    f"  {action}: {amount_in} {token_in} -> {amount_out} {token_out}"
                    f"  (tx: {sig[:16]}...)"
                )

        lines += [
            "",
            "=" * 40,
            "This summary was sent automatically by E.E.V.A.",
            "To pause this strategy, say 'pause strategy' in chat.",
        ]

        body = "\n".join(lines)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = email_cfg.from_addr or email_cfg.username
        msg["To"] = email_cfg.to_addr
        msg.attach(MIMEText(body, "plain"))

        await aiosmtplib.send(
            msg,
            hostname=email_cfg.smtp_host,
            port=email_cfg.smtp_port,
            username=email_cfg.username,
            password=email_cfg.password,
            start_tls=True,
        )

        logger.info(f"Strategy summary sent for {strategy_id} ({trade_count} trades)")
        return True

    except Exception as exc:
        logger.error(f"Failed to send strategy summary for {strategy_id}: {exc}")
        return False


# ---------------------------------------------------------------------------
# Email content builders
# ---------------------------------------------------------------------------

def _build_trade_email(trade_doc: dict) -> tuple[str, str]:
    """Build email subject and plain-text body from a trade document.

    Args:
        trade_doc: wallet_trades document dict

    Returns:
        Tuple of (subject, body) strings
    """
    action = trade_doc.get("action", "trade").upper()
    pair = trade_doc.get("pair", "UNKNOWN/UNKNOWN")
    amount_in = trade_doc.get("amount_in", 0)
    token_in = trade_doc.get("amount_in_token", "")
    amount_out = trade_doc.get("amount_out", 0)
    token_out = trade_doc.get("amount_out_token", "")
    tx_sig = trade_doc.get("tx_signature", "N/A")
    strategy_id = trade_doc.get("strategy_id")
    mode = trade_doc.get("execution_mode", "unknown")
    timestamp = trade_doc.get(
        "timestamp",
        datetime.now(timezone.utc).isoformat(),
    )

    subject = f"[E.E.V.A.] {action} {pair} — Trade Executed"
    source = f"Strategy: {strategy_id}" if strategy_id else "Ad-hoc (confirmed by you)"

    body = (
        f"E.E.V.A. Trade Notification\n"
        f"{'=' * 40}\n"
        f"Action:     {action}\n"
        f"Pair:       {pair}\n"
        f"Spent:      {amount_in} {token_in}\n"
        f"Received:   {amount_out} {token_out}\n"
        f"Source:     {source}\n"
        f"Mode:       {mode}\n"
        f"Tx Sig:     {tx_sig}\n"
        f"Timestamp:  {timestamp}\n"
        f"\n"
        f"View on Solscan: https://solscan.io/tx/{tx_sig}\n"
        f"{'=' * 40}\n"
        f"This notification was sent automatically by E.E.V.A.\n"
        f"To stop autonomous trading, say 'pause all strategies' in chat.\n"
    )

    return subject, body
