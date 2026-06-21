# src/coordinator/jupiter/strategies/dca_strategy.py
"""DCA (Dollar Cost Averaging) strategy — buys on a fixed schedule."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from .strategy_base import StrategyBase

logger = logging.getLogger(__name__)


class DCAStrategy(StrategyBase):
    """Fixed-schedule DCA strategy.

    Buys `amount_per_cycle_usdc` every `cycle_frequency_hours`.
    Tracks last_executed in strategy JSON.
    """

    async def check_signal(self) -> str:
        """Return 'buy' if cycle_frequency_hours have elapsed since last execution."""
        cycle_hours = self.params.get("cycle_frequency_hours", 168)  # default: weekly
        last_executed_str = self.config.get("last_executed")

        if not last_executed_str:
            # Never executed — buy immediately
            logger.info(f"[DCAStrategy:{self.strategy_id}] First execution — signaling buy")
            return "buy"

        try:
            last_executed = datetime.fromisoformat(last_executed_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            logger.warning(f"[DCAStrategy:{self.strategy_id}] Invalid last_executed: {e}. Signaling buy.")
            return "buy"

        now = datetime.now(timezone.utc)
        elapsed_hours = (now - last_executed).total_seconds() / 3600

        if elapsed_hours >= cycle_hours:
            logger.info(
                f"[DCAStrategy:{self.strategy_id}] Cycle due "
                f"(elapsed={elapsed_hours:.1f}h >= {cycle_hours}h) — buy"
            )
            return "buy"

        remaining = cycle_hours - elapsed_hours
        logger.debug(
            f"[DCAStrategy:{self.strategy_id}] Next buy in {remaining:.1f}h — hold"
        )
        return "hold"
