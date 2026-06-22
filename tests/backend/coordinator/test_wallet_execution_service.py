# tests/backend/coordinator/test_wallet_execution_service.py
"""Unit tests for WalletExecutionService — mocks all external deps."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.coordinator.services.wallet_execution_service import WalletExecutionService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_svc(
    jupiter_result: dict | None = None,
    jupiter_raises: Exception | None = None,
    trade_history_repo=None,
    wallet_summary_repo=None,
) -> WalletExecutionService:
    jupiter_ops = AsyncMock()
    if jupiter_raises:
        jupiter_ops.execute_swap.side_effect = jupiter_raises
    else:
        jupiter_ops.execute_swap.return_value = jupiter_result or {
            "tx_signature": "TX123",
            "out_amount": 1.23,
            "slippage_realized_bps": 10,
            "priority_fee_sol": 0.001,
        }
    return WalletExecutionService(
        jupiter_ops=jupiter_ops,
        trade_history_repo=trade_history_repo,
        wallet_summary_repo=wallet_summary_repo,
    )


_DEFAULT_SWAP_KWARGS = dict(
    user_id="user1",
    from_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    to_mint="So11111111111111111111111111111111111111112",
    from_token="USDC",
    to_token="SOL",
    amount_lamports=1_000_000,
    slippage_bps=50,
)


def run(coro):
    # asyncio.run() creates and closes a fresh loop each call. Do NOT use
    # asyncio.get_event_loop(): on Python 3.12 it raises "no current event loop"
    # once an earlier test in the suite has closed the thread's loop (passes alone,
    # fails in-suite).
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# execute_swap — success paths
# ---------------------------------------------------------------------------

class TestExecuteSwapSuccess:
    def test_returns_trade_doc(self):
        svc = _make_svc()
        doc = run(svc.execute_swap(**_DEFAULT_SWAP_KWARGS))
        assert doc["tx_signature"] == "TX123"
        assert doc["status"] == "confirmed"

    def test_trade_doc_has_expected_fields(self):
        svc = _make_svc()
        doc = run(svc.execute_swap(**_DEFAULT_SWAP_KWARGS))
        for field in [
            "tx_signature", "idempotency_key", "timestamp", "user_id",
            "pair", "action", "from_mint", "to_mint",
            "amount_in", "amount_in_token", "amount_out", "amount_out_token",
            "slippage_bps", "execution_mode", "status",
        ]:
            assert field in doc, f"missing field: {field}"

    def test_pair_format(self):
        svc = _make_svc()
        doc = run(svc.execute_swap(**_DEFAULT_SWAP_KWARGS))
        assert doc["pair"] == "USDC/SOL"

    def test_action_buy_when_from_usdc(self):
        svc = _make_svc()
        doc = run(svc.execute_swap(**_DEFAULT_SWAP_KWARGS))
        assert doc["action"] == "buy"

    def test_action_buy_when_from_usdt(self):
        svc = _make_svc()
        kwargs = dict(_DEFAULT_SWAP_KWARGS, from_token="USDT", to_token="SOL")
        doc = run(svc.execute_swap(**kwargs))
        assert doc["action"] == "buy"

    def test_action_sell_when_from_sol(self):
        svc = _make_svc()
        kwargs = dict(_DEFAULT_SWAP_KWARGS, from_token="SOL", to_token="USDC")
        doc = run(svc.execute_swap(**kwargs))
        assert doc["action"] == "sell"

    def test_amount_in_usdc_divided_by_1m(self):
        svc = _make_svc()
        doc = run(svc.execute_swap(**_DEFAULT_SWAP_KWARGS))
        # USDC lamports: 1_000_000 / 1_000_000 = 1.0
        assert doc["amount_in"] == pytest.approx(1.0)

    def test_amount_in_sol_divided_by_1b(self):
        svc = _make_svc()
        kwargs = dict(_DEFAULT_SWAP_KWARGS, from_token="SOL", to_token="USDC", amount_lamports=2_000_000_000)
        doc = run(svc.execute_swap(**kwargs))
        assert doc["amount_in"] == pytest.approx(2.0)

    def test_out_amount_from_result(self):
        svc = _make_svc(jupiter_result={
            "tx_signature": "TX999",
            "out_amount": 42.0,
        })
        doc = run(svc.execute_swap(**_DEFAULT_SWAP_KWARGS))
        assert doc["amount_out"] == pytest.approx(42.0)

    def test_out_amount_fallback_to_out_amount_human(self):
        svc = _make_svc(jupiter_result={
            "tx_signature": "TXABC",
            "out_amount_human": 7.77,
        })
        doc = run(svc.execute_swap(**_DEFAULT_SWAP_KWARGS))
        assert doc["amount_out"] == pytest.approx(7.77)

    def test_optional_fields_stored(self):
        svc = _make_svc()
        kwargs = dict(
            _DEFAULT_SWAP_KWARGS,
            execution_mode="strategy_autonomous",
            strategy_id="rsi_001",
            rsi_at_execution=28.5,
            entry_price=180.0,
            stop_loss_price=165.0,
            take_profit_price=220.0,
        )
        doc = run(svc.execute_swap(**kwargs))
        assert doc["execution_mode"] == "strategy_autonomous"
        assert doc["strategy_id"] == "rsi_001"
        assert doc["rsi_at_execution"] == pytest.approx(28.5)
        assert doc["entry_price"] == pytest.approx(180.0)
        assert doc["stop_loss_price"] == pytest.approx(165.0)
        assert doc["take_profit_price"] == pytest.approx(220.0)

    def test_email_sent_false_by_default(self):
        svc = _make_svc()
        doc = run(svc.execute_swap(**_DEFAULT_SWAP_KWARGS))
        assert doc["email_sent"] is False

    def test_idempotency_key_is_uuid_string(self):
        import uuid
        svc = _make_svc()
        doc = run(svc.execute_swap(**_DEFAULT_SWAP_KWARGS))
        uuid.UUID(doc["idempotency_key"])  # raises if not valid UUID

    def test_timestamp_is_iso_utc(self):
        svc = _make_svc()
        doc = run(svc.execute_swap(**_DEFAULT_SWAP_KWARGS))
        dt = datetime.fromisoformat(doc["timestamp"])
        assert dt.tzinfo is not None


# ---------------------------------------------------------------------------
# execute_swap — failure path
# ---------------------------------------------------------------------------

class TestExecuteSwapFailure:
    def test_raises_on_jupiter_exception(self):
        svc = _make_svc(jupiter_raises=RuntimeError("swap failed"))
        with pytest.raises(RuntimeError, match="swap failed"):
            run(svc.execute_swap(**_DEFAULT_SWAP_KWARGS))


# ---------------------------------------------------------------------------
# _persist_trade_local
# ---------------------------------------------------------------------------

class TestPersistTradeLocal:
    def test_skips_when_no_repo(self):
        svc = _make_svc(trade_history_repo=None)
        trade_doc = {
            "user_id": "u1", "pair": "USDC/SOL", "action": "buy",
            "amount_in": 100.0, "amount_in_token": "USDC",
            "amount_out_token": "SOL", "timestamp": "2026-01-01T00:00:00+00:00",
            "tx_signature": "TX1", "amount_out": 0.5,
            "slippage_bps": 50, "execution_mode": "adhoc_confirmed",
            "strategy_id": None,
        }
        run(svc._persist_trade_local(trade_doc))  # should not raise

    def test_calls_repo_record_trade(self):
        repo = MagicMock()
        svc = _make_svc(trade_history_repo=repo)
        trade_doc = {
            "user_id": "u1", "pair": "USDC/SOL", "action": "buy",
            "amount_in": 100.0, "amount_in_token": "USDC",
            "amount_out_token": "SOL", "timestamp": "2026-01-01T00:00:00+00:00",
            "tx_signature": "TX1", "amount_out": 0.5,
            "slippage_bps": 50, "execution_mode": "adhoc_confirmed",
            "strategy_id": None,
        }
        # Patch out the wallet registry import so it doesn't blow up
        with patch(
            "src.coordinator.services.wallet_execution_service.WalletExecutionService._persist_trade_local",
            wraps=svc._persist_trade_local,
        ):
            # call directly without startup import — it will try to import get_wallet_registry_repo
            # Patch startup at module level
            with patch.dict("sys.modules", {"src.coordinator.startup": MagicMock(
                get_wallet_registry_repo=MagicMock(return_value=None)
            )}):
                run(svc._persist_trade_local(trade_doc))
        repo.record_trade.assert_called_once()

    def test_repo_exception_does_not_propagate(self):
        repo = MagicMock()
        repo.record_trade.side_effect = Exception("db error")
        svc = _make_svc(trade_history_repo=repo)
        trade_doc = {
            "user_id": "u1", "pair": "USDC/SOL", "action": "buy",
            "amount_in": 1.0, "amount_in_token": "USDC",
            "amount_out_token": "SOL", "timestamp": "t",
            "tx_signature": None, "amount_out": None,
            "slippage_bps": None, "execution_mode": "adhoc_confirmed",
            "strategy_id": None,
        }
        with patch.dict("sys.modules", {"src.coordinator.startup": MagicMock(
            get_wallet_registry_repo=MagicMock(return_value=None)
        )}):
            run(svc._persist_trade_local(trade_doc))  # must not raise


# ---------------------------------------------------------------------------
# _update_summary
# ---------------------------------------------------------------------------

class TestUpdateSummary:
    def _trade(self, amount_in_token="USDC", amount_out_token="SOL", amount_in=100.0, amount_out=0.5):
        return {
            "user_id": "u1",
            "pair": f"{amount_in_token}/{amount_out_token}",
            "action": "buy" if amount_in_token in ("USDC", "USDT") else "sell",
            "amount_in": amount_in,
            "amount_in_token": amount_in_token,
            "amount_out": amount_out,
            "amount_out_token": amount_out_token,
            "timestamp": "2026-01-01T00:00:00+00:00",
        }

    def test_skips_when_no_repo(self):
        svc = _make_svc(wallet_summary_repo=None)
        run(svc._update_summary(self._trade()))  # should not raise

    def test_calls_increment_trade_usdc_in(self):
        repo = MagicMock()
        svc = _make_svc(wallet_summary_repo=repo)
        run(svc._update_summary(self._trade(amount_in_token="USDC", amount_in=200.0)))
        repo.increment_trade.assert_called_once()
        call_kwargs = repo.increment_trade.call_args.kwargs
        assert call_kwargs["volume_usdc"] == pytest.approx(200.0)

    def test_calls_increment_trade_usdt_in(self):
        repo = MagicMock()
        svc = _make_svc(wallet_summary_repo=repo)
        run(svc._update_summary(self._trade(amount_in_token="USDT", amount_in=300.0)))
        call_kwargs = repo.increment_trade.call_args.kwargs
        assert call_kwargs["volume_usdc"] == pytest.approx(300.0)

    def test_volume_from_out_when_usdc_is_out(self):
        repo = MagicMock()
        svc = _make_svc(wallet_summary_repo=repo)
        trade = self._trade(amount_in_token="SOL", amount_out_token="USDC", amount_out=55.0)
        run(svc._update_summary(trade))
        call_kwargs = repo.increment_trade.call_args.kwargs
        assert call_kwargs["volume_usdc"] == pytest.approx(55.0)

    def test_volume_zero_when_no_stable(self):
        repo = MagicMock()
        svc = _make_svc(wallet_summary_repo=repo)
        trade = self._trade(amount_in_token="SOL", amount_out_token="JUP")
        run(svc._update_summary(trade))
        call_kwargs = repo.increment_trade.call_args.kwargs
        assert call_kwargs["volume_usdc"] == pytest.approx(0.0)

    def test_repo_exception_does_not_propagate(self):
        repo = MagicMock()
        repo.increment_trade.side_effect = Exception("summary db error")
        svc = _make_svc(wallet_summary_repo=repo)
        run(svc._update_summary(self._trade()))  # must not raise


# ---------------------------------------------------------------------------
# open_position / close_position — no-ops, just log
# ---------------------------------------------------------------------------

class TestPositionMethods:
    def test_open_position_does_not_raise(self):
        svc = _make_svc()
        run(svc.open_position(
            strategy_id="s1", entry_price=100.0, position_size=1.0,
            position_token="SOL", position_value_usdc=100.0, tx_signature="TX1",
        ))

    def test_close_position_does_not_raise(self):
        svc = _make_svc()
        run(svc.close_position(strategy_id="s1", tx_signature="TX2", trigger="stop_loss"))

    def test_open_position_with_sl_tp(self):
        svc = _make_svc()
        run(svc.open_position(
            strategy_id="s1", entry_price=180.0, position_size=1.5,
            position_token="SOL", position_value_usdc=270.0, tx_signature="TX3",
            stop_loss_price=165.0, take_profit_price=210.0,
        ))

    def test_close_position_all_triggers(self):
        svc = _make_svc()
        for trigger in ("stop_loss", "take_profit", "manual"):
            run(svc.close_position(strategy_id="s1", tx_signature="TX", trigger=trigger))
