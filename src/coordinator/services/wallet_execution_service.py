# src/coordinator/services/wallet_execution_service.py
"""Executes confirmed trades via Jupiter MCP and persists results to MongoDB."""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Any

logger = logging.getLogger(__name__)


class WalletExecutionService:
    """Executes confirmed ad-hoc and strategy trades.

    Called ONLY after:
    - User clicks Confirm on a ProposalCard (ad-hoc)
    - Scheduler detects a strategy signal (autonomous)

    Never called directly from chat handler.
    """

    def __init__(
        self,
        jupiter_ops: Any,  # JupiterOperations
        mongo_write_client: Any = None,  # pymongo client, optional
    ):
        self.jupiter_ops = jupiter_ops
        self.mongo_write = mongo_write_client

    async def execute_swap(
        self,
        user_id: str,
        from_mint: str,
        to_mint: str,
        from_token: str,
        to_token: str,
        amount_lamports: int,
        slippage_bps: int = 50,
        execution_mode: str = "adhoc_confirmed",
        strategy_id: Optional[str] = None,
        rsi_at_execution: Optional[float] = None,
        entry_price: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
    ) -> dict:
        """Execute a token swap and record to MongoDB.

        Args:
            user_id: User identifier
            from_mint: Source token mint address
            to_mint: Destination token mint address
            from_token: Source token symbol
            to_token: Destination token symbol
            amount_lamports: Amount in lamports/raw units
            slippage_bps: Slippage tolerance in basis points
            execution_mode: 'adhoc_confirmed' or 'strategy_autonomous'
            strategy_id: If strategy-driven, the strategy ID
            rsi_at_execution: RSI value at time of execution (for logs)
            entry_price: Entry price in USDC (for SL/TP calculation)
            stop_loss_price: Pre-computed stop-loss price
            take_profit_price: Pre-computed take-profit price

        Returns:
            Trade document with tx_signature and status
        """
        idempotency_key = str(uuid.uuid4())

        logger.info(
            f"[WalletExecution] Executing {execution_mode} swap: "
            f"{from_token} -> {to_token}, amount={amount_lamports} lamports, "
            f"slippage={slippage_bps}bps, user={user_id}"
        )

        try:
            result = await self.jupiter_ops.execute_swap(
                from_mint=from_mint,
                to_mint=to_mint,
                amount_lamports=amount_lamports,
                slippage_bps=slippage_bps,
                idempotency_key=idempotency_key,
            )
        except Exception as e:
            logger.error(f"[WalletExecution] Swap failed: {e}")
            raise

        tx_signature = result.get("tx_signature", "")

        # Build trade document (mirrors KuCoin bot's trade_events collection)
        amount_in_human = (
            amount_lamports / 1_000_000
            if "USDC" in from_token
            else amount_lamports / 1_000_000_000
        )
        # JupiterOperations.execute_swap() returns "out_amount" (not "out_amount_human")
        amount_out_human = result.get("out_amount", result.get("out_amount_human", 0.0))

        trade_doc = {
            "tx_signature": tx_signature,
            "idempotency_key": idempotency_key,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "pair": f"{from_token}/{to_token}",
            "action": "buy" if from_token.upper() in ("USDC", "USDT") else "sell",
            "from_mint": from_mint,
            "to_mint": to_mint,
            "amount_in": amount_in_human,
            "amount_in_token": from_token,
            "amount_out": amount_out_human,
            "amount_out_token": to_token,
            "slippage_bps": slippage_bps,
            "slippage_realized_bps": result.get("slippage_realized_bps"),
            "priority_fee_sol": result.get("priority_fee_sol", 0.0),
            "execution_mode": execution_mode,
            "strategy_id": strategy_id,
            "rsi_at_execution": rsi_at_execution,
            "entry_price": entry_price,
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "status": "confirmed",
            "email_sent": False,
        }

        # Write to MongoDB
        await self._persist_trade(trade_doc)

        logger.info(f"[WalletExecution] Trade complete: tx={tx_signature}")
        return trade_doc

    async def _persist_trade(self, trade_doc: dict) -> None:
        """Write trade to MongoDB wallet_trades collection."""
        if self.mongo_write is None:
            logger.debug("[WalletExecution] No MongoDB write client — skipping persistence")
            return
        try:
            self.mongo_write["wallet_trades"].insert_one(trade_doc)
            logger.info(
                f"[WalletExecution] Trade persisted to MongoDB: {trade_doc.get('tx_signature')}"
            )
        except Exception as e:
            logger.error(f"[WalletExecution] MongoDB write failed: {e}")
            # Non-fatal: trade executed, just not recorded

    async def open_position(
        self,
        strategy_id: str,
        entry_price: float,
        position_size: float,
        position_token: str,
        position_value_usdc: float,
        tx_signature: str,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
    ) -> None:
        """Record an open position to MongoDB open_positions collection."""
        if self.mongo_write is None:
            return

        position_doc = {
            "strategy_id": strategy_id,
            "entry_price": entry_price,
            "position_size": position_size,
            "position_token": position_token,
            "position_value_usdc": position_value_usdc,
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "entry_tx_signature": tx_signature,
            "entry_timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "open",
        }

        try:
            self.mongo_write["open_positions"].insert_one(position_doc)
            logger.info(f"[WalletExecution] Position opened: strategy={strategy_id}")
        except Exception as e:
            logger.error(f"[WalletExecution] Failed to record open position: {e}")

    async def close_position(
        self,
        strategy_id: str,
        tx_signature: str,
        trigger: str,  # 'stop_loss', 'take_profit', 'manual'
    ) -> None:
        """Mark a position as closed in MongoDB."""
        if self.mongo_write is None:
            return
        try:
            self.mongo_write["open_positions"].update_one(
                {"strategy_id": strategy_id, "status": "open"},
                {
                    "$set": {
                        "status": "closed",
                        "exit_trigger": trigger,
                        "exit_tx_signature": tx_signature,
                        "exit_timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                },
            )
            logger.info(
                f"[WalletExecution] Position closed: strategy={strategy_id}, trigger={trigger}"
            )
        except Exception as e:
            logger.error(f"[WalletExecution] Failed to close position: {e}")
