# src/coordinator/jupiter/strategy_scheduler.py
"""APScheduler-based autonomous strategy execution scheduler.

Two-phase execution:
  Phase 1 (every tick): Check open positions for SL/TP exits
  Phase 2 (every tick): Check entry signals for active strategies (respects check_interval_minutes)

Daily reset: Reset spent_today_usdc for all strategies at midnight UTC.

IMPORTANT: The scheduler only runs if wallet_unlocked(user_id) is True.
If the wallet is locked, cycles are silently skipped. E.E.V.A. notifies
the user when they open a new chat session.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler = None


def get_scheduler():
    """Get the global APScheduler instance."""
    return _scheduler


def init_scheduler(
    jupiter_ops: Any,
    execution_service: Any,
    strategy_service: Any,
    check_interval_minutes: int = 15,
) -> Any:
    """Initialize and return the APScheduler instance.

    Called from startup.py on server start.
    """
    global _scheduler

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
    except ImportError:
        logger.error("APScheduler not installed — autonomous strategies disabled")
        return None

    _scheduler = AsyncIOScheduler()

    # Phase 1 + 2: Run every check_interval_minutes
    _scheduler.add_job(
        _run_strategy_checks,
        "interval",
        minutes=check_interval_minutes,
        args=[jupiter_ops, execution_service, strategy_service],
        id="strategy_checks",
        replace_existing=True,
        max_instances=1,  # Never overlap — one run at a time
    )

    # Daily reset: midnight UTC
    _scheduler.add_job(
        _reset_daily_spend,
        "cron",
        hour=0, minute=0,
        id="daily_spend_reset",
        replace_existing=True,
    )

    logger.info(f"Strategy scheduler initialized (interval={check_interval_minutes}min)")
    return _scheduler


async def _run_strategy_checks(jupiter_ops, execution_service, strategy_service):
    """Main scheduler job: Phase 1 SL/TP exits + Phase 2 entry signals."""
    from ..jupiter.wallet_manager import wallet_unlocked
    from ..jupiter.strategy_loader import load_strategies, update_strategy
    from ..jupiter.strategies import STRATEGY_REGISTRY
    from ..jupiter.email_service import send_trade_notification

    logger.debug("[Scheduler] Strategy check cycle started")

    strategies = load_strategies()
    if not strategies:
        logger.debug("[Scheduler] No strategies loaded — skipping")
        return

    # -----------------------------------------------------------------------
    # PHASE 2: Check entry signals for active strategies
    # (Phase 1 SL/TP exit via open_positions was MongoDB-dependent — removed)
    # -----------------------------------------------------------------------
    for strategy in strategies:
        if strategy.get("status") != "active":
            continue

        strategy_id = strategy["strategy_id"]
        user_id = strategy.get("user_id", "")
        strategy_type = strategy.get("strategy_type")

        # Wallet must be unlocked
        if not user_id or not wallet_unlocked(user_id):
            logger.debug(f"[Scheduler] Skipping {strategy_id} — wallet not unlocked")
            continue

        # Check if it's time to run this strategy
        if not _needs_check(strategy):
            continue

        # Check daily limit
        if strategy_service.check_guardrails(strategy, 0.0)[0] is False:
            logger.info(f"[Scheduler] Daily limit reached for {strategy_id}")
            continue

        # Check open position (fail-closed if MongoDB unavailable)
        if strategy_service.has_open_position(strategy_id):
            logger.debug(f"[Scheduler] Open position exists for {strategy_id} — skipping entry")
            continue

        # Get strategy implementation
        impl_class = STRATEGY_REGISTRY.get(strategy_type)
        if not impl_class:
            logger.warning(f"[Scheduler] Unknown strategy type: {strategy_type}")
            continue

        impl = impl_class(strategy)

        try:
            signal = await impl.check_signal()
        except Exception as e:
            logger.error(f"[Scheduler] Signal check failed for {strategy_id}: {e}")
            continue

        logger.info(f"[Scheduler] {strategy_id} signal: {signal}")

        if signal != "buy":
            # Update last_checked timestamp
            update_strategy(strategy_id, {"last_checked": datetime.now(timezone.utc).isoformat()})
            continue

        # Check balance pre-flight
        max_trade = strategy["guardrails"]["max_trade_size_usdc"]
        try:
            # Verify guardrails pass for this trade amount
            passed, reason = strategy_service.check_guardrails(strategy, max_trade)
            if not passed:
                logger.info(f"[Scheduler] Guardrail blocked {strategy_id}: {reason}")
                continue
        except Exception as e:
            logger.error(f"[Scheduler] Pre-flight check failed: {e}")
            continue

        # Execute entry trade
        from_mint = strategy["token_pair"]["from_mint"]
        to_mint = strategy["token_pair"]["to_mint"]
        from_token = strategy["token_pair"]["from_token"]
        to_token = strategy["token_pair"]["to_token"]
        amount_lamports = int(max_trade * 1_000_000)  # USDC has 6 decimals

        try:
            # Get quote for price info
            quote = await jupiter_ops.get_swap_quote(from_mint, to_mint, amount_lamports)
            entry_price = quote.get("price", 0.0)

            sl_pct = strategy["risk_management"].get("stop_loss_pct")
            tp_pct = strategy["risk_management"].get("take_profit_pct")
            sl_price = entry_price * (1 - sl_pct / 100) if sl_pct else None
            tp_price = entry_price * (1 + tp_pct / 100) if tp_pct else None

            trade_doc = await execution_service.execute_swap(
                user_id=user_id,
                from_mint=from_mint,
                to_mint=to_mint,
                from_token=from_token,
                to_token=to_token,
                amount_lamports=amount_lamports,
                execution_mode="strategy_autonomous",
                strategy_id=strategy_id,
                entry_price=entry_price,
                stop_loss_price=sl_price,
                take_profit_price=tp_price,
            )

            # Record open position
            await execution_service.open_position(
                strategy_id=strategy_id,
                entry_price=entry_price,
                position_size=quote.get("out_amount_human", 0.0),
                position_token=to_token,
                position_value_usdc=max_trade,
                tx_signature=trade_doc.get("tx_signature", ""),
                stop_loss_price=sl_price,
                take_profit_price=tp_price,
            )

            # Update daily spend
            from ..jupiter.strategy_loader import update_strategy_spend
            update_strategy_spend(strategy_id, max_trade)

            # Update last_executed for DCA strategies
            update_strategy(strategy_id, {
                "last_executed": datetime.now(timezone.utc).isoformat(),
                "last_checked": datetime.now(timezone.utc).isoformat(),
            })

            # Send email notification
            await send_trade_notification(trade_doc)

            logger.info(f"[Scheduler] Entry trade complete: {strategy_id}, tx={trade_doc.get('tx_signature')}")

        except Exception as e:
            logger.error(f"[Scheduler] Entry trade failed for {strategy_id}: {e}")


def _needs_check(strategy: dict) -> bool:
    """Check if enough time has elapsed to run this strategy's signal check."""
    check_interval = strategy.get("parameters", {}).get("check_interval_minutes", 240)
    last_checked_str = strategy.get("last_checked")

    if not last_checked_str:
        return True  # Never checked

    try:
        last_checked = datetime.fromisoformat(last_checked_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return True

    now = datetime.now(timezone.utc)
    elapsed_minutes = (now - last_checked).total_seconds() / 60
    return elapsed_minutes >= check_interval


async def _reset_daily_spend():
    """Reset daily spend counters for all strategies (midnight UTC job)."""
    from ..jupiter.strategy_loader import reset_daily_spend
    count = reset_daily_spend()
    logger.info(f"[Scheduler] Daily spend reset: {count} strategies reset")
