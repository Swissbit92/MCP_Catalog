# src/coordinator/jupiter/strategies/rsi_strategy.py
"""RSI-based trading strategy."""
from __future__ import annotations

import logging
from .strategy_base import StrategyBase

logger = logging.getLogger(__name__)


class RSIStrategy(StrategyBase):
    """Buy when RSI < oversold_threshold, sell signal when RSI > overbought_threshold.

    RSI data fetched from jupiter_operations (wired at runtime).
    Placeholder returns 50.0 until wired to live data.
    """

    async def check_signal(self) -> str:
        """Return buy/sell/hold based on RSI thresholds."""
        try:
            rsi = await self._get_current_rsi()
        except Exception as e:
            logger.warning(f"[RSIStrategy:{self.strategy_id}] Failed to get RSI: {e}. Returning hold.")
            return "hold"

        oversold = self.params.get("oversold_threshold", 30.0)
        overbought = self.params.get("overbought_threshold", 70.0)

        logger.info(
            f"[RSIStrategy:{self.strategy_id}] RSI={rsi:.2f} "
            f"(oversold<{oversold}, overbought>{overbought})"
        )

        if rsi <= oversold:
            return "buy"
        elif rsi >= overbought:
            return "sell"
        return "hold"

    async def _get_current_rsi(self) -> float:
        """Fetch current RSI for the token pair.

        TODO: Wire to jupiter_operations.get_token_rsi() once available.
        Currently returns placeholder 50.0 (neutral — no signal).
        """
        # Placeholder until jupiter_operations is wired in
        logger.debug(f"[RSIStrategy:{self.strategy_id}] RSI placeholder — returning 50.0")
        return 50.0
