# src/coordinator/jupiter/strategies/strategy_base.py
"""Abstract base class for all trading strategies."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class StrategyBase(ABC):
    """Abstract base for trading strategy implementations.

    Subclasses implement check_signal() to return 'buy', 'sell', or 'hold'.
    Guardrail checks live in strategy_service.py, not here.
    """

    def __init__(self, strategy_config: Dict):
        self.config = strategy_config
        self.strategy_id: str = strategy_config["strategy_id"]
        self.strategy_type: str = strategy_config["strategy_type"]
        self.token_pair: Dict = strategy_config["token_pair"]
        self.params: Dict = strategy_config.get("parameters", {})
        self.risk: Dict = strategy_config.get("risk_management", {})
        self.guardrails: Dict = strategy_config.get("guardrails", {})

    @abstractmethod
    async def check_signal(self) -> str:
        """Check strategy conditions and return trading signal.

        Returns:
            'buy'  — entry condition met
            'sell' — exit condition met (take-profit/target hit, not SL — SL is in scheduler)
            'hold' — no action needed
        """
        ...

    def daily_limit_exceeded(self) -> bool:
        """Check if daily USDC spending limit is exhausted."""
        spent = self.guardrails.get("spent_today_usdc", 0.0)
        limit = self.guardrails.get("daily_limit_usdc", 0.0)
        return spent >= limit

    def max_trade_size(self) -> float:
        """Return max single trade size in USDC."""
        return self.guardrails.get("max_trade_size_usdc", 0.0)

    def stop_loss_pct(self) -> Optional[float]:
        return self.risk.get("stop_loss_pct")

    def take_profit_pct(self) -> Optional[float]:
        return self.risk.get("take_profit_pct")

    def __repr__(self) -> str:
        return f"{self.strategy_type}(id={self.strategy_id})"
