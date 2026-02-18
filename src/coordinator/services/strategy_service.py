# src/coordinator/services/strategy_service.py
"""Strategy management service — CRUD for strategies + guardrail enforcement."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Any

logger = logging.getLogger(__name__)


class StrategyService:
    """Manages strategy lifecycle and enforces guardrails.

    Acts as the safety layer between the scheduler and execution.
    Guardrails enforced here CANNOT be bypassed by the LLM.
    """

    def __init__(
        self,
        strategies_dir: str = "strategies",
        mongo_write: Any = None,
    ):
        self.strategies_dir = strategies_dir
        self.mongo_write = mongo_write

    def list_strategies(self, user_id: Optional[str] = None) -> list[dict]:
        """Load all strategies, optionally filtered by user_id."""
        from ..jupiter.strategy_loader import load_strategies

        strategies = load_strategies(self.strategies_dir)
        if user_id:
            strategies = [s for s in strategies if s.get("user_id") == user_id]
        return strategies

    def get_strategy(self, strategy_id: str) -> Optional[dict]:
        """Get a single strategy by ID."""
        from ..jupiter.strategy_loader import load_strategy

        return load_strategy(strategy_id, self.strategies_dir)

    def activate_strategy(self, strategy_config: dict, user_id: str) -> str:
        """Save and activate a strategy after user approval.

        Args:
            strategy_config: Full strategy dict (from proposal)
            user_id: Approving user ID

        Returns:
            strategy_id of the saved strategy
        """
        from ..jupiter.strategy_loader import save_strategy
        from datetime import date

        strategy_config["status"] = "active"
        strategy_config["user_id"] = user_id
        strategy_config["approved_at"] = datetime.now(timezone.utc).isoformat()
        strategy_config["guardrails"]["daily_reset_date"] = date.today().isoformat()
        strategy_config["guardrails"]["spent_today_usdc"] = 0.0

        save_strategy(strategy_config, self.strategies_dir)
        strategy_id = strategy_config["strategy_id"]

        logger.info(f"Strategy activated: {strategy_id} (user={user_id})")

        # Log to MongoDB
        self._log_approval_decision(
            decision_type="strategy_approved",
            strategy_id=strategy_id,
            user_id=user_id,
        )

        return strategy_id

    def pause_strategy(self, strategy_id: str, user_id: str) -> bool:
        """Pause an active strategy."""
        from ..jupiter.strategy_loader import update_strategy

        try:
            update_strategy(strategy_id, {"status": "paused"}, self.strategies_dir)
            logger.info(f"Strategy paused: {strategy_id}")
            self._log_approval_decision("strategy_paused", strategy_id, user_id)
            return True
        except FileNotFoundError:
            return False

    def resume_strategy(self, strategy_id: str, user_id: str) -> bool:
        """Resume a paused strategy."""
        from ..jupiter.strategy_loader import update_strategy

        try:
            update_strategy(strategy_id, {"status": "active"}, self.strategies_dir)
            logger.info(f"Strategy resumed: {strategy_id}")
            return True
        except FileNotFoundError:
            return False

    def cancel_strategy(self, strategy_id: str, user_id: str) -> bool:
        """Permanently cancel a strategy (sets status=cancelled)."""
        from ..jupiter.strategy_loader import update_strategy

        try:
            update_strategy(strategy_id, {"status": "cancelled"}, self.strategies_dir)
            logger.info(f"Strategy cancelled: {strategy_id}")
            self._log_approval_decision("strategy_cancelled", strategy_id, user_id)
            return True
        except FileNotFoundError:
            return False

    def check_guardrails(self, strategy: dict, amount_usdc: float) -> tuple[bool, str]:
        """Check all guardrails before executing a trade.

        Args:
            strategy: Full strategy dict
            amount_usdc: Trade size in USDC

        Returns:
            (passed: bool, reason: str)
        """
        guardrails = strategy.get("guardrails", {})

        # Check daily limit
        spent = guardrails.get("spent_today_usdc", 0.0)
        daily_limit = guardrails.get("daily_limit_usdc", 0.0)
        if spent + amount_usdc > daily_limit:
            return (
                False,
                f"Daily limit exceeded: {spent:.2f} + {amount_usdc:.2f} > {daily_limit:.2f} USDC",
            )

        # Check per-trade size
        max_trade = guardrails.get("max_trade_size_usdc", 0.0)
        if amount_usdc > max_trade:
            return (
                False,
                f"Trade size {amount_usdc:.2f} USDC exceeds max {max_trade:.2f} USDC",
            )

        return True, "passed"

    def has_open_position(self, strategy_id: str) -> bool:
        """Check if strategy has an open position in MongoDB.

        Fails CLOSED on any error — if we cannot verify, we assume a position exists
        to prevent double-entry. The scheduler will skip this cycle and retry next tick.

        Returns:
            True if an open position exists OR if the check cannot be completed.
            False only when MongoDB confirms no open position.

        Raises:
            Nothing — returns True on any database error (conservative/safe default).
        """
        if self.mongo_write is None:
            logger.warning(
                f"[StrategyService] MongoDB write client unavailable — "
                f"assuming open position for {strategy_id} (fail-closed)"
            )
            return True  # Fail closed — cannot verify, block entry
        try:
            doc = self.mongo_write["open_positions"].find_one(
                {"strategy_id": strategy_id, "status": "open"}
            )
            return doc is not None
        except Exception as e:
            logger.warning(
                f"[StrategyService] Failed to check open position for {strategy_id}: {e} "
                f"— assuming open position (fail-closed)"
            )
            return True  # Fail closed — cannot verify, block entry

    def _log_approval_decision(
        self,
        decision_type: str,
        strategy_id: str,
        user_id: str,
        extra: Optional[dict] = None,
    ) -> None:
        """Log a HITL decision to MongoDB approval_decisions collection."""
        if self.mongo_write is None:
            return
        try:
            self.mongo_write["approval_decisions"].insert_one(
                {
                    "decision_type": decision_type,
                    "strategy_id": strategy_id,
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **(extra or {}),
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log decision: {e}")
