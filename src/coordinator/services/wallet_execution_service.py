# src/coordinator/services/wallet_execution_service.py
"""Executes confirmed trades via Jupiter MCP and persists results to SQLite."""
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

    Trades are written to SQLite wallet_trades_local (always).
    Activity summary is updated on every trade.
    """

    def __init__(
        self,
        jupiter_ops: Any,  # JupiterOperations
        trade_history_repo: Any = None,  # TradeHistoryRepository, optional
        wallet_summary_repo: Any = None,  # WalletSummaryRepository, optional
        wallet_registry_repo: Any = None,  # WalletRegistryRepository, optional
    ):
        self.jupiter_ops = jupiter_ops
        self.trade_history_repo = trade_history_repo
        self.wallet_summary_repo = wallet_summary_repo
        self.wallet_registry_repo = wallet_registry_repo

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
        """Execute a token swap and record to SQLite.

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
        # Phase 3 defence-in-depth: the on-chain spend chokepoint accepts only the
        # two legitimate, confirmed execution modes. An agentic/chat path can never
        # reach here with an unrecognised mode — this is the last guard before a
        # real Solana transaction, independent of the tool-call interceptor.
        _ALLOWED_EXECUTION_MODES = {"adhoc_confirmed", "strategy_autonomous"}
        if execution_mode not in _ALLOWED_EXECUTION_MODES:
            raise ValueError(
                f"[WalletExecution] refusing swap: execution_mode "
                f"'{execution_mode}' is not a confirmed mode "
                f"{sorted(_ALLOWED_EXECUTION_MODES)}"
            )

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

        # Write to SQLite
        await self._persist_trade_local(trade_doc)

        # Update activity summary
        await self._update_summary(trade_doc)

        logger.info(f"[WalletExecution] Trade complete: tx={tx_signature}")
        return trade_doc

    async def _persist_trade_local(self, trade_doc: dict) -> None:
        """Write trade to SQLite wallet_trades_local table (dual-write fallback)."""
        if self.trade_history_repo is None:
            logger.debug("[WalletExecution] No trade history repo — skipping local persistence")
            return
        try:
            # Resolve wallet_id from registry by looking up the user's active wallet address
            wallet_id = ""
            try:
                # Prefer the injected registry; fall back to the startup seam so
                # this remains resolvable when constructed without one.
                registry_repo = self.wallet_registry_repo
                if registry_repo is None:
                    from .. import startup
                    registry_repo = startup.get_wallet_registry_repo()
                if registry_repo:
                    wallets = registry_repo.get_active_wallets(trade_doc.get("user_id", ""))
                    if wallets:
                        wallet_id = wallets[0].get("wallet_id", "")
            except Exception:
                pass

            self.trade_history_repo.record_trade(
                user_id=trade_doc.get("user_id", ""),
                wallet_id=wallet_id,
                pair=trade_doc.get("pair", ""),
                action=trade_doc.get("action", ""),
                amount_in=trade_doc.get("amount_in", 0.0),
                amount_in_token=trade_doc.get("amount_in_token", ""),
                amount_out_token=trade_doc.get("amount_out_token", ""),
                timestamp=trade_doc.get("timestamp", ""),
                tx_signature=trade_doc.get("tx_signature"),
                amount_out=trade_doc.get("amount_out"),
                slippage_bps=trade_doc.get("slippage_bps"),
                execution_mode=trade_doc.get("execution_mode"),
                strategy_id=trade_doc.get("strategy_id"),
            )
        except Exception as e:
            logger.error(f"[WalletExecution] SQLite trade write failed: {e}")

    async def _update_summary(self, trade_doc: dict) -> None:
        """Update wallet activity summary after a trade."""
        if self.wallet_summary_repo is None:
            return
        try:
            # Estimate USDC volume
            volume = 0.0
            if trade_doc.get("amount_in_token", "").upper() in ("USDC", "USDT"):
                volume = trade_doc.get("amount_in", 0.0)
            elif trade_doc.get("amount_out_token", "").upper() in ("USDC", "USDT"):
                volume = trade_doc.get("amount_out", 0.0) or 0.0

            self.wallet_summary_repo.increment_trade(
                user_id=trade_doc.get("user_id", ""),
                volume_usdc=volume,
                pair=trade_doc.get("pair", ""),
                action=trade_doc.get("action", ""),
                timestamp=trade_doc.get("timestamp", ""),
            )
        except Exception as e:
            logger.error(f"[WalletExecution] Summary update failed: {e}")

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
        """Record that a position was opened (no-op: MongoDB write path removed)."""
        logger.info(f"[WalletExecution] Position opened: strategy={strategy_id}")

    async def close_position(
        self,
        strategy_id: str,
        tx_signature: str,
        trigger: str,  # 'stop_loss', 'take_profit', 'manual'
    ) -> None:
        """Record that a position was closed (no-op: MongoDB write path removed)."""
        logger.info(
            f"[WalletExecution] Position closed: strategy={strategy_id}, trigger={trigger}"
        )
