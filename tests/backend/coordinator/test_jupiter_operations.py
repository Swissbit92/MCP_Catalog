"""
Unit tests for src/coordinator/jupiter/jupiter_operations.py

Pure-logic coverage:
  - _require_ready: raises JupiterConnectionError when client not ready
  - get_wallet_balance: response normalisation (sol/SOL variants, token list)
  - get_swap_quote: field normalisation (camelCase/snake_case variants), slippage passthrough
  - get_token_price_usdc: price derivation math, zero-output guard (ValueError)
  - execute_swap: tx_signature field normalisation (txSignature/tx_signature/signature),
                  idempotency_key wiring
  - create_limit_order: field normalisation, expiry_seconds wiring
  - create_dca_order: field normalisation
  - verify_transaction: confirmed field (bool cast, status=="finalized" fallback)

Mocked:
  - JupiterDockerClient (is_ready, call_tool, _parse_tool_response) via unittest.mock.MagicMock

NOT tested (impossible without live Docker/Solana RPC and no clean seam to mock):
  - JupiterDockerClient.__init__ subprocess management
  - Low-level JSON-RPC 2.0 wire protocol
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.coordinator.jupiter.jupiter_operations import (
    JupiterOperations,
    USDC_MINT,
    _PRICE_PROBE_AMOUNT,
)
from src.coordinator.jupiter.jupiter_mcp_client import JupiterConnectionError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(ready: bool = True, parsed_response: dict | None = None) -> MagicMock:
    """Build a mock JupiterDockerClient."""
    client = MagicMock()
    client.is_ready.return_value = ready
    client._parse_tool_response.return_value = parsed_response or {}
    return client


def _ops(ready: bool = True, parsed_response: dict | None = None) -> JupiterOperations:
    return JupiterOperations(_make_client(ready, parsed_response))


# ---------------------------------------------------------------------------
# _require_ready
# ---------------------------------------------------------------------------

class TestRequireReady:
    @pytest.mark.asyncio
    async def test_raises_when_not_ready(self):
        ops = _ops(ready=False)
        with pytest.raises(JupiterConnectionError):
            await ops.get_wallet_balance("some-address")

    @pytest.mark.asyncio
    async def test_does_not_raise_when_ready(self):
        ops = _ops(ready=True, parsed_response={"sol": 1.0, "tokens": []})
        # No exception — just needs to reach the normalisation step
        result = await ops.get_wallet_balance("some-address")
        assert result is not None


# ---------------------------------------------------------------------------
# get_wallet_balance
# ---------------------------------------------------------------------------

class TestGetWalletBalance:
    @pytest.mark.asyncio
    async def test_returns_sol_and_tokens(self):
        ops = _ops(parsed_response={"sol": 2.5, "tokens": [{"mint": "abc", "symbol": "USDC", "amount": 100.0}]})
        result = await ops.get_wallet_balance("addr")
        assert result["sol"] == pytest.approx(2.5)
        assert len(result["tokens"]) == 1

    @pytest.mark.asyncio
    async def test_sol_key_fallback(self):
        """Handles uppercase 'SOL' variant from Jupiter MCP."""
        ops = _ops(parsed_response={"SOL": 3.14})
        result = await ops.get_wallet_balance("addr")
        assert result["sol"] == pytest.approx(3.14)

    @pytest.mark.asyncio
    async def test_missing_sol_defaults_to_zero(self):
        ops = _ops(parsed_response={})
        result = await ops.get_wallet_balance("addr")
        assert result["sol"] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_missing_tokens_defaults_to_empty_list(self):
        ops = _ops(parsed_response={"sol": 1.0})
        result = await ops.get_wallet_balance("addr")
        assert result["tokens"] == []

    @pytest.mark.asyncio
    async def test_calls_correct_tool(self):
        client = _make_client(parsed_response={"sol": 0.0})
        ops = JupiterOperations(client)
        await ops.get_wallet_balance("my-address")
        client.call_tool.assert_called_once_with(
            "wallet_get_balance", {"address": "my-address"}
        )


# ---------------------------------------------------------------------------
# get_swap_quote
# ---------------------------------------------------------------------------

class TestGetSwapQuote:
    @pytest.mark.asyncio
    async def test_normalises_camel_case_response(self):
        ops = _ops(parsed_response={
            "inAmount": 1_000_000,
            "outAmount": 5_000_000_000,
            "priceImpactPct": 0.01,
            "routePlan": [{"swap": "Orca"}],
        })
        result = await ops.get_swap_quote("USDC_MINT", "SOL_MINT", 1_000_000, slippage_bps=50)
        assert result["in_amount"] == 1_000_000
        assert result["out_amount"] == 5_000_000_000
        assert result["price_impact_pct"] == pytest.approx(0.01)
        assert result["route_plan"] == [{"swap": "Orca"}]
        assert result["slippage_bps"] == 50

    @pytest.mark.asyncio
    async def test_normalises_snake_case_response(self):
        """Also accepts snake_case field names from MCP."""
        ops = _ops(parsed_response={
            "in_amount": 500_000,
            "out_amount": 100_000_000,
            "price_impact_pct": 0.5,
            "route_plan": [],
        })
        result = await ops.get_swap_quote("A", "B", 500_000)
        assert result["in_amount"] == 500_000
        assert result["out_amount"] == 100_000_000

    @pytest.mark.asyncio
    async def test_missing_fields_default_to_zero(self):
        ops = _ops(parsed_response={})
        result = await ops.get_swap_quote("A", "B", 1_000)
        assert result["in_amount"] == 0
        assert result["out_amount"] == 0
        assert result["price_impact_pct"] == pytest.approx(0.0)
        assert result["route_plan"] == []

    @pytest.mark.asyncio
    async def test_slippage_passthrough(self):
        ops = _ops(parsed_response={})
        result = await ops.get_swap_quote("A", "B", 1_000, slippage_bps=200)
        assert result["slippage_bps"] == 200

    @pytest.mark.asyncio
    async def test_calls_correct_tool_with_args(self):
        client = _make_client(parsed_response={})
        ops = JupiterOperations(client)
        await ops.get_swap_quote("FROM", "TO", 9999, slippage_bps=75)
        client.call_tool.assert_called_once_with(
            "wallet_get_quote",
            {"inputMint": "FROM", "outputMint": "TO", "amount": 9999, "slippageBps": 75},
        )

    @pytest.mark.asyncio
    async def test_not_ready_raises(self):
        ops = _ops(ready=False)
        with pytest.raises(JupiterConnectionError):
            await ops.get_swap_quote("A", "B", 1_000)


# ---------------------------------------------------------------------------
# get_token_price_usdc
# ---------------------------------------------------------------------------

class TestGetTokenPriceUsdc:
    @pytest.mark.asyncio
    async def test_price_derivation_math(self):
        """price = _PRICE_PROBE_AMOUNT / out_amount."""
        # Probe: 1 USDC (1_000_000 micro) → 5_000_000_000 lamports (SOL 9 decimals)
        # raw ratio = 1_000_000 / 5_000_000_000 = 0.0002
        ops = JupiterOperations(_make_client(parsed_response={
            "inAmount": _PRICE_PROBE_AMOUNT,
            "outAmount": 5_000_000_000,
        }))
        price = await ops.get_token_price_usdc("SOL_MINT")
        assert price == pytest.approx(_PRICE_PROBE_AMOUNT / 5_000_000_000)

    @pytest.mark.asyncio
    async def test_zero_out_amount_raises_value_error(self):
        ops = JupiterOperations(_make_client(parsed_response={"inAmount": _PRICE_PROBE_AMOUNT, "outAmount": 0}))
        with pytest.raises(ValueError, match="zero output"):
            await ops.get_token_price_usdc("SOME_MINT")

    @pytest.mark.asyncio
    async def test_uses_usdc_mint_as_from(self):
        """Probe quote must use USDC_MINT as the input token."""
        client = _make_client(parsed_response={"inAmount": _PRICE_PROBE_AMOUNT, "outAmount": 1_000})
        ops = JupiterOperations(client)
        await ops.get_token_price_usdc("TARGET_MINT")
        call_args = client.call_tool.call_args
        assert call_args[0][1]["inputMint"] == USDC_MINT
        assert call_args[0][1]["outputMint"] == "TARGET_MINT"
        assert call_args[0][1]["amount"] == _PRICE_PROBE_AMOUNT

    @pytest.mark.asyncio
    async def test_not_ready_raises(self):
        ops = _ops(ready=False)
        with pytest.raises(JupiterConnectionError):
            await ops.get_token_price_usdc("MINT")


# ---------------------------------------------------------------------------
# execute_swap
# ---------------------------------------------------------------------------

class TestExecuteSwap:
    @pytest.mark.asyncio
    async def test_normalises_tx_signature_camel_case(self):
        ops = _ops(parsed_response={"txSignature": "sig-abc", "status": "confirmed"})
        result = await ops.execute_swap("FROM", "TO", 1_000)
        assert result["tx_signature"] == "sig-abc"
        assert result["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_normalises_tx_signature_snake_case(self):
        ops = _ops(parsed_response={"tx_signature": "sig-xyz", "status": "pending"})
        result = await ops.execute_swap("FROM", "TO", 1_000)
        assert result["tx_signature"] == "sig-xyz"

    @pytest.mark.asyncio
    async def test_normalises_signature_key(self):
        ops = _ops(parsed_response={"signature": "sig-123", "status": "confirmed"})
        result = await ops.execute_swap("FROM", "TO", 1_000)
        assert result["tx_signature"] == "sig-123"

    @pytest.mark.asyncio
    async def test_missing_tx_signature_defaults_empty(self):
        ops = _ops(parsed_response={"status": "failed"})
        result = await ops.execute_swap("FROM", "TO", 1_000)
        assert result["tx_signature"] == ""

    @pytest.mark.asyncio
    async def test_timestamp_defaults_to_now_when_missing(self):
        ops = _ops(parsed_response={"txSignature": "x", "status": "confirmed"})
        result = await ops.execute_swap("FROM", "TO", 1_000)
        assert "timestamp" in result
        assert result["timestamp"]  # non-empty

    @pytest.mark.asyncio
    async def test_timestamp_from_response_used(self):
        ops = _ops(parsed_response={"txSignature": "x", "status": "confirmed", "timestamp": "2026-01-01T00:00:00Z"})
        result = await ops.execute_swap("FROM", "TO", 1_000)
        assert result["timestamp"] == "2026-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_idempotency_key_included_when_provided(self):
        client = _make_client(parsed_response={"txSignature": "x", "status": "confirmed"})
        ops = JupiterOperations(client)
        await ops.execute_swap("FROM", "TO", 1_000, idempotency_key="idem-001")
        call_args = client.call_tool.call_args[0][1]
        assert call_args["idempotencyKey"] == "idem-001"

    @pytest.mark.asyncio
    async def test_idempotency_key_omitted_when_none(self):
        client = _make_client(parsed_response={"txSignature": "x", "status": "confirmed"})
        ops = JupiterOperations(client)
        await ops.execute_swap("FROM", "TO", 1_000, idempotency_key=None)
        call_args = client.call_tool.call_args[0][1]
        assert "idempotencyKey" not in call_args

    @pytest.mark.asyncio
    async def test_not_ready_raises(self):
        ops = _ops(ready=False)
        with pytest.raises(JupiterConnectionError):
            await ops.execute_swap("FROM", "TO", 1_000)


# ---------------------------------------------------------------------------
# create_limit_order
# ---------------------------------------------------------------------------

class TestCreateLimitOrder:
    @pytest.mark.asyncio
    async def test_normalises_response(self):
        ops = _ops(parsed_response={"orderId": "ord-1", "txSignature": "sig-1", "status": "open"})
        result = await ops.create_limit_order("A", "B", 1_000, 2_000)
        assert result["order_id"] == "ord-1"
        assert result["tx_signature"] == "sig-1"
        assert result["status"] == "open"

    @pytest.mark.asyncio
    async def test_snake_case_fallback(self):
        ops = _ops(parsed_response={"order_id": "ord-2", "tx_signature": "sig-2", "status": "open"})
        result = await ops.create_limit_order("A", "B", 1_000, 2_000)
        assert result["order_id"] == "ord-2"
        assert result["tx_signature"] == "sig-2"

    @pytest.mark.asyncio
    async def test_missing_fields_default_to_empty(self):
        ops = _ops(parsed_response={})
        result = await ops.create_limit_order("A", "B", 1_000, 2_000)
        assert result["order_id"] == ""
        assert result["tx_signature"] == ""
        assert result["status"] == "unknown"

    @pytest.mark.asyncio
    async def test_expiry_seconds_included(self):
        client = _make_client(parsed_response={})
        ops = JupiterOperations(client)
        await ops.create_limit_order("A", "B", 1_000, 2_000, expiry_seconds=3600)
        args = client.call_tool.call_args[0][1]
        assert args["expiredAt"] == 3600

    @pytest.mark.asyncio
    async def test_expiry_seconds_omitted_when_none(self):
        client = _make_client(parsed_response={})
        ops = JupiterOperations(client)
        await ops.create_limit_order("A", "B", 1_000, 2_000, expiry_seconds=None)
        args = client.call_tool.call_args[0][1]
        assert "expiredAt" not in args

    @pytest.mark.asyncio
    async def test_not_ready_raises(self):
        ops = _ops(ready=False)
        with pytest.raises(JupiterConnectionError):
            await ops.create_limit_order("A", "B", 1_000, 2_000)


# ---------------------------------------------------------------------------
# create_dca_order
# ---------------------------------------------------------------------------

class TestCreateDcaOrder:
    @pytest.mark.asyncio
    async def test_normalises_response(self):
        ops = _ops(parsed_response={"dcaId": "dca-1", "txSignature": "sig-dca", "status": "active"})
        result = await ops.create_dca_order("FROM", "TO", 10_000_000, 1_000_000, 3600)
        assert result["dca_id"] == "dca-1"
        assert result["tx_signature"] == "sig-dca"
        assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_snake_case_fallback(self):
        ops = _ops(parsed_response={"dca_id": "dca-2", "tx_signature": "sig-2", "status": "active"})
        result = await ops.create_dca_order("FROM", "TO", 10_000_000, 1_000_000, 3600)
        assert result["dca_id"] == "dca-2"

    @pytest.mark.asyncio
    async def test_missing_fields_default_to_empty(self):
        ops = _ops(parsed_response={})
        result = await ops.create_dca_order("FROM", "TO", 1_000, 500, 86400)
        assert result["dca_id"] == ""
        assert result["tx_signature"] == ""
        assert result["status"] == "unknown"

    @pytest.mark.asyncio
    async def test_calls_correct_tool_with_args(self):
        client = _make_client(parsed_response={})
        ops = JupiterOperations(client)
        await ops.create_dca_order("FROM_MINT", "TO_MINT", 9_000_000, 3_000_000, 7200)
        client.call_tool.assert_called_once_with(
            "wallet_create_dca_order",
            {
                "inputMint": "FROM_MINT",
                "outputMint": "TO_MINT",
                "totalInAmount": 9_000_000,
                "inAmountPerCycle": 3_000_000,
                "cycleFrequency": 7200,
            },
        )

    @pytest.mark.asyncio
    async def test_not_ready_raises(self):
        ops = _ops(ready=False)
        with pytest.raises(JupiterConnectionError):
            await ops.create_dca_order("A", "B", 1, 1, 1)


# ---------------------------------------------------------------------------
# verify_transaction
# ---------------------------------------------------------------------------

class TestVerifyTransaction:
    @pytest.mark.asyncio
    async def test_confirmed_true(self):
        ops = _ops(parsed_response={"confirmed": True, "slot": 100, "err": None})
        result = await ops.verify_transaction("sig-abc")
        assert result["confirmed"] is True
        assert result["slot"] == 100
        assert result["err"] is None

    @pytest.mark.asyncio
    async def test_confirmed_via_status_finalized(self):
        """confirmed key absent but status=='finalized' → confirmed True."""
        ops = _ops(parsed_response={"status": "finalized", "slot": 50})
        result = await ops.verify_transaction("sig-xyz")
        assert result["confirmed"] is True

    @pytest.mark.asyncio
    async def test_confirmed_false_when_not_finalized(self):
        ops = _ops(parsed_response={"status": "pending"})
        result = await ops.verify_transaction("sig-pend")
        assert result["confirmed"] is False

    @pytest.mark.asyncio
    async def test_slot_defaults_to_zero(self):
        ops = _ops(parsed_response={"confirmed": True})
        result = await ops.verify_transaction("sig-x")
        assert result["slot"] == 0

    @pytest.mark.asyncio
    async def test_err_passthrough(self):
        ops = _ops(parsed_response={"confirmed": False, "slot": 0, "err": "InstructionError"})
        result = await ops.verify_transaction("sig-fail")
        assert result["err"] == "InstructionError"

    @pytest.mark.asyncio
    async def test_not_ready_raises(self):
        ops = _ops(ready=False)
        with pytest.raises(JupiterConnectionError):
            await ops.verify_transaction("sig-x")
