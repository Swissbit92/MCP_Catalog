"""Comprehensive unit tests for TradeHistoryRepository.

Coverage targets:
- record_trade (required fields, optional fields, return shape, autoincrement id)
- get_user_trades (empty, one, multiple, default limit, custom limit, ordering newest-first)
- get_wallet_trades (empty, one, multiple, limit, isolates by wallet)
- get_trade_count (zero, one, multiple, user isolation)
- get_total_volume (no trades, USDC, USDT, mixed tokens, user isolation)
"""
from __future__ import annotations

import pytest

from src.coordinator.repositories.trade_history_repository import TradeHistoryRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repo(tmp_path):
    """Fresh TradeHistoryRepository backed by a temp SQLite file."""
    db_path = str(tmp_path / "test_history.db")
    return TradeHistoryRepository(db_path)


def _record(
    repo: TradeHistoryRepository,
    user_id: str = "user1",
    wallet_id: str = "wallet_abc",
    pair: str = "SOL/USDC",
    action: str = "buy",
    amount_in: float = 100.0,
    amount_in_token: str = "USDC",
    amount_out_token: str = "SOL",
    timestamp: str = "2026-06-22T10:00:00Z",
    **kwargs,
) -> dict:
    return repo.record_trade(
        user_id=user_id,
        wallet_id=wallet_id,
        pair=pair,
        action=action,
        amount_in=amount_in,
        amount_in_token=amount_in_token,
        amount_out_token=amount_out_token,
        timestamp=timestamp,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Tests — record_trade
# ---------------------------------------------------------------------------

class TestRecordTrade:
    def test_returns_dict(self, repo):
        result = _record(repo)
        assert isinstance(result, dict)

    def test_required_fields_in_result(self, repo):
        result = _record(repo)
        for key in ("id", "user_id", "wallet_id", "pair", "action",
                    "amount_in", "amount_in_token", "amount_out_token", "timestamp"):
            assert key in result

    def test_user_id_stored(self, repo):
        result = _record(repo, user_id="alice")
        assert result["user_id"] == "alice"

    def test_wallet_id_stored(self, repo):
        result = _record(repo, wallet_id="wlt-999")
        assert result["wallet_id"] == "wlt-999"

    def test_pair_stored(self, repo):
        result = _record(repo, pair="BTC/USDT")
        assert result["pair"] == "BTC/USDT"

    def test_action_stored(self, repo):
        result = _record(repo, action="sell")
        assert result["action"] == "sell"

    def test_amount_in_stored(self, repo):
        result = _record(repo, amount_in=42.5)
        assert result["amount_in"] == pytest.approx(42.5)

    def test_timestamp_stored(self, repo):
        ts = "2026-01-01T00:00:00Z"
        result = _record(repo, timestamp=ts)
        assert result["timestamp"] == ts

    def test_optional_tx_signature_stored(self, repo):
        result = _record(repo, tx_signature="sig123")
        assert result["tx_signature"] == "sig123"

    def test_optional_tx_signature_default_none(self, repo):
        result = _record(repo)
        assert result["tx_signature"] is None

    def test_optional_amount_out_stored(self, repo):
        result = _record(repo, amount_out=2.5)
        assert result["amount_out"] == pytest.approx(2.5)

    def test_optional_slippage_bps_stored(self, repo):
        result = _record(repo, slippage_bps=50)
        assert result["slippage_bps"] == 50

    def test_optional_execution_mode_stored(self, repo):
        result = _record(repo, execution_mode="market")
        assert result["execution_mode"] == "market"

    def test_optional_strategy_id_stored(self, repo):
        result = _record(repo, strategy_id="strat-xyz")
        assert result["strategy_id"] == "strat-xyz"

    def test_id_is_integer_autoincrement(self, repo):
        r1 = _record(repo)
        r2 = _record(repo)
        assert isinstance(r1["id"], int)
        assert r2["id"] == r1["id"] + 1

    def test_multiple_records_persist(self, repo):
        for i in range(5):
            _record(repo, amount_in=float(i))
        count = repo.get_trade_count("user1")
        assert count == 5


# ---------------------------------------------------------------------------
# Tests — get_user_trades
# ---------------------------------------------------------------------------

class TestGetUserTrades:
    def test_empty_for_unknown_user(self, repo):
        assert repo.get_user_trades("ghost") == []

    def test_returns_one_trade(self, repo):
        _record(repo, user_id="alice")
        results = repo.get_user_trades("alice")
        assert len(results) == 1

    def test_returns_all_fields(self, repo):
        _record(repo, user_id="alice")
        row = repo.get_user_trades("alice")[0]
        for key in ("id", "user_id", "wallet_id", "pair", "action",
                    "amount_in", "amount_in_token", "amount_out_token", "timestamp"):
            assert key in row

    def test_newest_first_ordering(self, repo):
        _record(repo, user_id="alice", amount_in=1.0)
        _record(repo, user_id="alice", amount_in=2.0)
        _record(repo, user_id="alice", amount_in=3.0)
        results = repo.get_user_trades("alice")
        # Ordered by id DESC → highest id (last inserted) comes first
        assert results[0]["amount_in"] == pytest.approx(3.0)
        assert results[-1]["amount_in"] == pytest.approx(1.0)

    def test_default_limit_50(self, repo):
        for i in range(60):
            _record(repo, user_id="alice", amount_in=float(i))
        results = repo.get_user_trades("alice")
        assert len(results) == 50

    def test_custom_limit(self, repo):
        for i in range(10):
            _record(repo, user_id="alice", amount_in=float(i))
        results = repo.get_user_trades("alice", limit=5)
        assert len(results) == 5

    def test_isolates_by_user(self, repo):
        _record(repo, user_id="alice")
        _record(repo, user_id="bob")
        _record(repo, user_id="bob")
        assert len(repo.get_user_trades("alice")) == 1
        assert len(repo.get_user_trades("bob")) == 2

    def test_limit_one_returns_single(self, repo):
        for _ in range(3):
            _record(repo, user_id="alice")
        results = repo.get_user_trades("alice", limit=1)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Tests — get_wallet_trades
# ---------------------------------------------------------------------------

class TestGetWalletTrades:
    def test_empty_for_unknown_wallet(self, repo):
        assert repo.get_wallet_trades("wallet_unknown") == []

    def test_returns_trade_for_wallet(self, repo):
        _record(repo, wallet_id="wallet_A")
        results = repo.get_wallet_trades("wallet_A")
        assert len(results) == 1
        assert results[0]["wallet_id"] == "wallet_A"

    def test_isolates_by_wallet(self, repo):
        _record(repo, wallet_id="wallet_A")
        _record(repo, wallet_id="wallet_B")
        _record(repo, wallet_id="wallet_B")
        assert len(repo.get_wallet_trades("wallet_A")) == 1
        assert len(repo.get_wallet_trades("wallet_B")) == 2

    def test_default_limit_50(self, repo):
        for i in range(60):
            _record(repo, wallet_id="wallet_A", amount_in=float(i))
        assert len(repo.get_wallet_trades("wallet_A")) == 50

    def test_custom_limit(self, repo):
        for i in range(10):
            _record(repo, wallet_id="wallet_A", amount_in=float(i))
        assert len(repo.get_wallet_trades("wallet_A", limit=3)) == 3

    def test_newest_first_ordering(self, repo):
        _record(repo, wallet_id="wallet_A", amount_in=1.0)
        _record(repo, wallet_id="wallet_A", amount_in=2.0)
        results = repo.get_wallet_trades("wallet_A")
        assert results[0]["amount_in"] == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Tests — get_trade_count
# ---------------------------------------------------------------------------

class TestGetTradeCount:
    def test_zero_for_unknown_user(self, repo):
        assert repo.get_trade_count("ghost") == 0

    def test_one_trade(self, repo):
        _record(repo, user_id="alice")
        assert repo.get_trade_count("alice") == 1

    def test_multiple_trades(self, repo):
        for _ in range(7):
            _record(repo, user_id="alice")
        assert repo.get_trade_count("alice") == 7

    def test_isolates_by_user(self, repo):
        _record(repo, user_id="alice")
        _record(repo, user_id="alice")
        _record(repo, user_id="bob")
        assert repo.get_trade_count("alice") == 2
        assert repo.get_trade_count("bob") == 1


# ---------------------------------------------------------------------------
# Tests — get_total_volume
# ---------------------------------------------------------------------------

class TestGetTotalVolume:
    def test_zero_for_unknown_user(self, repo):
        assert repo.get_total_volume("ghost") == pytest.approx(0.0)

    def test_usdc_trades_counted(self, repo):
        _record(repo, user_id="alice", amount_in=100.0, amount_in_token="USDC")
        _record(repo, user_id="alice", amount_in=50.0, amount_in_token="USDC")
        assert repo.get_total_volume("alice") == pytest.approx(150.0)

    def test_usdt_trades_counted(self, repo):
        _record(repo, user_id="alice", amount_in=200.0, amount_in_token="USDT")
        assert repo.get_total_volume("alice") == pytest.approx(200.0)

    def test_mixed_usdc_usdt(self, repo):
        _record(repo, user_id="alice", amount_in=100.0, amount_in_token="USDC")
        _record(repo, user_id="alice", amount_in=75.0, amount_in_token="USDT")
        assert repo.get_total_volume("alice") == pytest.approx(175.0)

    def test_non_stable_tokens_excluded(self, repo):
        _record(repo, user_id="alice", amount_in=10.0, amount_in_token="SOL")
        _record(repo, user_id="alice", amount_in=1.0, amount_in_token="BTC")
        assert repo.get_total_volume("alice") == pytest.approx(0.0)

    def test_mixed_stable_and_other(self, repo):
        _record(repo, user_id="alice", amount_in=100.0, amount_in_token="USDC")
        _record(repo, user_id="alice", amount_in=10.0, amount_in_token="SOL")
        assert repo.get_total_volume("alice") == pytest.approx(100.0)

    def test_isolates_by_user(self, repo):
        _record(repo, user_id="alice", amount_in=100.0, amount_in_token="USDC")
        _record(repo, user_id="bob", amount_in=500.0, amount_in_token="USDC")
        assert repo.get_total_volume("alice") == pytest.approx(100.0)
        assert repo.get_total_volume("bob") == pytest.approx(500.0)

    def test_returns_float(self, repo):
        result = repo.get_total_volume("alice")
        assert isinstance(result, float)
