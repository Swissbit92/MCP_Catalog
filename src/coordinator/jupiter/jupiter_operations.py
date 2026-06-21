# src/coordinator/jupiter/jupiter_operations.py
# High-level Jupiter DEX operations API
# Provides semantic methods built on top of the JupiterDockerClient
#
# Mirrors src/coordinator/mongodb/operations.py pattern exactly.

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .jupiter_mcp_client import JupiterConnectionError, JupiterDockerClient

logger = logging.getLogger(__name__)

# USDC mint address on Solana mainnet (used for price derivation)
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# Small amount for price-check quotes (0.001 USDC = 1000 micro-USDC)
# Avoids price impact on tiny probe swaps
_PRICE_PROBE_AMOUNT = 1_000_000  # 1 USDC in lamports (USDC has 6 decimals)


class JupiterOperations:
    """High-level Jupiter DEX operations.

    Wraps JupiterDockerClient with semantic methods.
    Handles response parsing, error handling, and logging.

    Mirrors MongoDBOperations pattern: the client is injected so that
    JupiterMCPClient can inherit from both via multiple inheritance.
    """

    def __init__(self, client: JupiterDockerClient):
        """Initialize Jupiter operations.

        Args:
            client: Initialized JupiterDockerClient instance
        """
        self.client = client

    # ------------------------------------------------------------------
    # Read-only operations (no wallet confirmation needed in coordinator)
    # ------------------------------------------------------------------

    async def get_wallet_balance(self, public_address: str) -> Dict[str, Any]:
        """Get SOL and SPL token balances for a wallet address.

        Args:
            public_address: Base58-encoded Solana wallet public address

        Returns:
            dict: {
                'sol': float,          # SOL balance
                'tokens': [
                    {
                        'mint': str,       # SPL token mint address
                        'symbol': str,     # Token symbol (e.g. 'USDC')
                        'amount': float,   # Human-readable balance
                    },
                    ...
                ]
            }

        Raises:
            JupiterConnectionError: If wallet is not unlocked
            JupiterResponseError: If MCP server returns an error
        """
        self._require_ready()
        logger.info(f"Jupiter get_wallet_balance: address={public_address}")

        result = self.client.call_tool(
            "wallet_get_balance",
            {"address": public_address},
        )
        parsed = self.client._parse_tool_response(result)

        # Normalise — Jupiter MCP may return various shapes; provide safe defaults
        return {
            "sol": float(parsed.get("sol", parsed.get("SOL", 0.0))),
            "tokens": parsed.get("tokens", []),
        }

    async def get_swap_quote(
        self,
        from_mint: str,
        to_mint: str,
        amount_lamports: int,
        slippage_bps: int = 50,
    ) -> Dict[str, Any]:
        """Get a swap quote from Jupiter aggregator.

        Args:
            from_mint: Input token mint address
            to_mint: Output token mint address
            amount_lamports: Input amount in lamports (smallest token unit)
            slippage_bps: Slippage tolerance in basis points (default: 50 = 0.5%)

        Returns:
            dict: {
                'in_amount': int,           # Input amount in lamports
                'out_amount': int,          # Expected output amount in lamports
                'price_impact_pct': float,  # Price impact percentage
                'route_plan': list,         # Route hops
                'slippage_bps': int,        # Applied slippage
            }

        Raises:
            JupiterConnectionError: If wallet is not unlocked
            JupiterResponseError: If MCP server returns an error
        """
        self._require_ready()
        logger.info(
            f"Jupiter get_swap_quote: {from_mint} -> {to_mint}, "
            f"amount={amount_lamports}, slippage={slippage_bps}bps"
        )

        result = self.client.call_tool(
            "wallet_get_quote",
            {
                "inputMint": from_mint,
                "outputMint": to_mint,
                "amount": amount_lamports,
                "slippageBps": slippage_bps,
            },
        )
        parsed = self.client._parse_tool_response(result)

        return {
            "in_amount": int(parsed.get("inAmount", parsed.get("in_amount", 0))),
            "out_amount": int(parsed.get("outAmount", parsed.get("out_amount", 0))),
            "price_impact_pct": float(parsed.get("priceImpactPct", parsed.get("price_impact_pct", 0.0))),
            "route_plan": parsed.get("routePlan", parsed.get("route_plan", [])),
            "slippage_bps": slippage_bps,
        }

    async def get_token_price_usdc(self, token_mint: str) -> float:
        """Get the current token price in USDC.

        Derives price by fetching a small quote (1 USDC -> token) and computing
        the inverse, avoiding meaningful price impact on the probe.

        Used by the strategy scheduler for stop-loss and take-profit checks.

        Args:
            token_mint: SPL token mint address to price

        Returns:
            float: Token price in USDC (e.g. 180.5 for SOL at $180.50)

        Raises:
            JupiterConnectionError: If wallet is not unlocked
            JupiterResponseError: If quote fails
            ValueError: If price cannot be derived from the quote
        """
        self._require_ready()
        logger.info(f"Jupiter get_token_price_usdc: mint={token_mint}")

        # Probe: 1 USDC -> token_mint
        quote = await self.get_swap_quote(
            from_mint=USDC_MINT,
            to_mint=token_mint,
            amount_lamports=_PRICE_PROBE_AMOUNT,
            slippage_bps=100,  # Generous slippage for probe only
        )

        out_amount = quote.get("out_amount", 0)
        if out_amount <= 0:
            raise ValueError(
                f"Could not derive price for {token_mint}: quote returned zero output"
            )

        # Price = USDC_in / token_out (both in lamports for their respective mints)
        # USDC has 6 decimals; SOL has 9. The caller must supply the correct denominator.
        # For simplicity we return the raw ratio — callers adjust for decimals as needed.
        # price_usdc = usdc_in_micro / token_out_base_units
        price = _PRICE_PROBE_AMOUNT / out_amount
        logger.debug(f"Derived price for {token_mint}: {price} USDC (raw ratio)")
        return price

    async def verify_transaction(self, tx_signature: str) -> Dict[str, Any]:
        """Verify a transaction's on-chain status for idempotency after timeout.

        Useful when a swap execute call times out but the transaction may have
        already been broadcast and confirmed on-chain.

        Args:
            tx_signature: Base58-encoded Solana transaction signature

        Returns:
            dict: {
                'confirmed': bool,      # Whether tx is confirmed on-chain
                'slot': int,            # Slot number (0 if not found)
                'err': Optional[str],   # Error string if tx failed on-chain
            }

        Raises:
            JupiterConnectionError: If wallet is not unlocked
            JupiterResponseError: If MCP server returns an error
        """
        self._require_ready()
        logger.info(f"Jupiter verify_transaction: sig={tx_signature}")

        # Use a dedicated tx-status check approach: call wallet_get_quote with
        # a dummy no-op to verify MCP server liveness, then check via RPC.
        # TODO: replace with a proper wallet_get_transaction tool once Jupiter MCP
        # exposes one. For now we call execute-result status check pattern.
        result = self.client.call_tool(
            "wallet_verify_transaction",
            {"transaction_signature": tx_signature},
        )
        parsed = self.client._parse_tool_response(result)

        return {
            "confirmed": bool(parsed.get("confirmed", parsed.get("status") == "finalized")),
            "slot": int(parsed.get("slot", 0)),
            "err": parsed.get("err"),
        }

    # ------------------------------------------------------------------
    # Write operations (coordinator enforces HITL before calling these)
    # ------------------------------------------------------------------

    async def execute_swap(
        self,
        from_mint: str,
        to_mint: str,
        amount_lamports: int,
        slippage_bps: int = 50,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a token swap via Jupiter.

        IMPORTANT: Only call this method after:
        1. The user has confirmed via ProposalCard (ad-hoc trades), OR
        2. An approved strategy signal has fired and all guardrails pass.

        The coordinator layer (wallet_execution_service.py) enforces this.
        This method calls the MCP execute tool directly — no secondary check here.

        Args:
            from_mint: Input token mint address
            to_mint: Output token mint address
            amount_lamports: Input amount in lamports (smallest token unit)
            slippage_bps: Slippage tolerance in basis points
            idempotency_key: Optional key to deduplicate retried executions

        Returns:
            dict: {
                'tx_signature': str,   # Base58 transaction signature
                'status': str,         # 'confirmed' | 'pending' | 'failed'
                'timestamp': str,      # ISO-8601 UTC timestamp
            }

        Raises:
            JupiterConnectionError: If wallet is not unlocked
            JupiterResponseError: If MCP server returns an error
        """
        self._require_ready()
        logger.info(
            f"Jupiter execute_swap: {from_mint} -> {to_mint}, "
            f"amount={amount_lamports}, slippage={slippage_bps}bps, "
            f"idempotency_key={idempotency_key}"
        )

        arguments: Dict[str, Any] = {
            "inputMint": from_mint,
            "outputMint": to_mint,
            "amount": amount_lamports,
            "slippageBps": slippage_bps,
        }
        if idempotency_key:
            arguments["idempotencyKey"] = idempotency_key

        result = self.client.call_tool("wallet_execute_swap", arguments)
        parsed = self.client._parse_tool_response(result)

        tx_sig = parsed.get("txSignature", parsed.get("tx_signature", parsed.get("signature", "")))
        status = parsed.get("status", "unknown")
        timestamp = parsed.get(
            "timestamp",
            datetime.now(timezone.utc).isoformat(),
        )

        logger.info(f"Jupiter swap executed: sig={tx_sig}, status={status}")
        return {
            "tx_signature": tx_sig,
            "status": status,
            "timestamp": timestamp,
        }

    async def create_limit_order(
        self,
        from_mint: str,
        to_mint: str,
        in_amount_lamports: int,
        out_amount_lamports: int,
        expiry_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a Jupiter limit order.

        Args:
            from_mint: Input token mint address
            to_mint: Output token mint address
            in_amount_lamports: Input amount in lamports
            out_amount_lamports: Minimum output amount (limit price)
            expiry_seconds: Order expiry in seconds from now (None = no expiry)

        Returns:
            dict: {
                'order_id': str,       # Jupiter order identifier
                'tx_signature': str,   # Creation transaction signature
                'status': str,         # 'open' | 'failed'
            }

        Raises:
            JupiterConnectionError: If wallet is not unlocked
            JupiterResponseError: If MCP server returns an error
        """
        self._require_ready()
        logger.info(
            f"Jupiter create_limit_order: {from_mint} -> {to_mint}, "
            f"in={in_amount_lamports}, out_min={out_amount_lamports}"
        )

        arguments: Dict[str, Any] = {
            "inputMint": from_mint,
            "outputMint": to_mint,
            "inAmount": in_amount_lamports,
            "outAmount": out_amount_lamports,
        }
        if expiry_seconds is not None:
            arguments["expiredAt"] = expiry_seconds

        result = self.client.call_tool("wallet_create_limit_order", arguments)
        parsed = self.client._parse_tool_response(result)

        return {
            "order_id": parsed.get("orderId", parsed.get("order_id", "")),
            "tx_signature": parsed.get("txSignature", parsed.get("tx_signature", "")),
            "status": parsed.get("status", "unknown"),
        }

    async def create_dca_order(
        self,
        from_mint: str,
        to_mint: str,
        total_in_amount_lamports: int,
        in_amount_per_cycle_lamports: int,
        cycle_frequency_seconds: int,
    ) -> Dict[str, Any]:
        """Create a Jupiter DCA (Dollar-Cost Averaging) order.

        Args:
            from_mint: Input token mint address
            to_mint: Output token mint address
            total_in_amount_lamports: Total input amount across all cycles
            in_amount_per_cycle_lamports: Input amount per DCA cycle
            cycle_frequency_seconds: Seconds between each DCA purchase

        Returns:
            dict: {
                'dca_id': str,         # Jupiter DCA position identifier
                'tx_signature': str,   # Creation transaction signature
                'status': str,         # 'active' | 'failed'
            }

        Raises:
            JupiterConnectionError: If wallet is not unlocked
            JupiterResponseError: If MCP server returns an error
        """
        self._require_ready()
        logger.info(
            f"Jupiter create_dca_order: {from_mint} -> {to_mint}, "
            f"total={total_in_amount_lamports}, per_cycle={in_amount_per_cycle_lamports}, "
            f"freq={cycle_frequency_seconds}s"
        )

        result = self.client.call_tool(
            "wallet_create_dca_order",
            {
                "inputMint": from_mint,
                "outputMint": to_mint,
                "totalInAmount": total_in_amount_lamports,
                "inAmountPerCycle": in_amount_per_cycle_lamports,
                "cycleFrequency": cycle_frequency_seconds,
            },
        )
        parsed = self.client._parse_tool_response(result)

        return {
            "dca_id": parsed.get("dcaId", parsed.get("dca_id", "")),
            "tx_signature": parsed.get("txSignature", parsed.get("tx_signature", "")),
            "status": parsed.get("status", "unknown"),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_ready(self) -> None:
        """Raise JupiterConnectionError if the client is not ready.

        Used as a guard at the top of every public method to give a clear
        error message when the wallet has not been unlocked.
        """
        if not self.client.is_ready():
            raise JupiterConnectionError(
                "Wallet not unlocked. Call set_private_key() before performing operations."
            )
