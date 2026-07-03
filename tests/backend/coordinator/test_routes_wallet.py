"""
Unit tests for src/coordinator/routes/wallet.py

Mocks (all via patch on the symbols imported into the route module):
  - src.coordinator.routes.wallet — startup getters via patch on the module's lazy imports
  - src.coordinator.startup.get_trade_proposal_repo
  - src.coordinator.startup.get_wallet_execution_service
  - src.coordinator.startup.get_strategy_service
  - src.coordinator.startup.get_wallet_repo
  - src.coordinator.startup.get_jupiter_ops
  - src.coordinator.jupiter.email_service.send_trade_notification
  - src.coordinator.jupiter.wallet_manager.*
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from fastapi.testclient import TestClient
from src.coordinator.server import app

# Create client WITHOUT context manager to skip lifespan (no live Ollama/DB)
client = TestClient(app)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _mock_proposal_repo(proposal=None, status="pending"):
    repo = MagicMock()
    if proposal is None and status:
        proposal = {
            "id": "prop-1",
            "status": status,
            "proposal_json": json.dumps({
                "from_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "to_mint": "So11111111111111111111111111111111111111112",
                "amount": 10.0,
                "from_token": "USDC",
                "to_token": "SOL",
                "user_id": "default_user",
            }),
        }
    repo.get_proposal.return_value = proposal
    return repo


def _mock_execution_service(tx_sig="abc123"):
    svc = MagicMock()
    trade_doc = {"tx_signature": tx_sig, "status": "confirmed"}
    svc.execute_swap = AsyncMock(return_value=trade_doc)
    return svc


def _mock_strategy_service(activate_return="strat-1", pause_ok=True, resume_ok=True, cancel_ok=True):
    svc = MagicMock()
    svc.activate_strategy.return_value = activate_return
    svc.pause_strategy.return_value = pause_ok
    svc.resume_strategy.return_value = resume_ok
    svc.cancel_strategy.return_value = cancel_ok
    svc.list_strategies.return_value = [{"id": "strat-1", "status": "active"}]
    return svc


def _mock_wallet_repo(wallet=None):
    repo = MagicMock()
    if wallet is None:
        wallet = {
            "id": 1,
            "public_address": "SoLANAaddr1111111111111111111111111111111111",
            "wallet_name": "My Wallet",
            "created_at": "2026-01-01T00:00:00",
            "is_active": 1,
        }
    repo.get_active_wallet.return_value = wallet
    return repo


# ── /wallet/confirm/{proposal_id} ────────────────────────────────────────────

class TestConfirmTrade:
    def test_confirm_happy_path(self):
        proposal_repo = _mock_proposal_repo()
        exec_svc = _mock_execution_service("tx-sig-ok")

        with (
            patch("src.coordinator.startup.get_trade_proposal_repo", return_value=proposal_repo),
            patch("src.coordinator.startup.get_wallet_execution_service", return_value=exec_svc),
            patch("src.coordinator.jupiter.email_service.send_trade_notification", new=AsyncMock()),
        ):
            resp = client.post("/wallet/confirm/prop-1")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "confirmed"
        assert data["proposal_id"] == "prop-1"
        assert data["tx_signature"] == "tx-sig-ok"

    def test_confirm_proposal_not_found(self):
        proposal_repo = MagicMock()
        proposal_repo.get_proposal.return_value = None

        with patch("src.coordinator.startup.get_trade_proposal_repo", return_value=proposal_repo):
            resp = client.post("/wallet/confirm/missing-prop")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_confirm_proposal_already_confirmed(self):
        proposal_repo = _mock_proposal_repo(status="confirmed")

        with patch("src.coordinator.startup.get_trade_proposal_repo", return_value=proposal_repo):
            resp = client.post("/wallet/confirm/prop-1")

        assert resp.status_code == 409
        assert "confirmed" in resp.json()["detail"]

    def test_confirm_proposal_cancelled_status(self):
        proposal_repo = _mock_proposal_repo(status="cancelled")

        with patch("src.coordinator.startup.get_trade_proposal_repo", return_value=proposal_repo):
            resp = client.post("/wallet/confirm/prop-1")

        assert resp.status_code == 409

    def test_confirm_jupiter_not_initialized(self):
        proposal_repo = _mock_proposal_repo()

        with (
            patch("src.coordinator.startup.get_trade_proposal_repo", return_value=proposal_repo),
            patch("src.coordinator.startup.get_wallet_execution_service", return_value=None),
        ):
            resp = client.post("/wallet/confirm/prop-1")

        assert resp.status_code == 503
        assert "Jupiter MCP not initialized" in resp.json()["detail"]

    def test_confirm_execution_raises_exception(self):
        proposal_repo = _mock_proposal_repo()
        exec_svc = MagicMock()
        exec_svc.execute_swap = AsyncMock(side_effect=RuntimeError("swap exploded"))

        with (
            patch("src.coordinator.startup.get_trade_proposal_repo", return_value=proposal_repo),
            patch("src.coordinator.startup.get_wallet_execution_service", return_value=exec_svc),
        ):
            resp = client.post("/wallet/confirm/prop-1")

        assert resp.status_code == 500
        assert "Trade execution failed" in resp.json()["detail"]

    def test_confirm_sol_token_lamport_conversion(self):
        """SOL uses 9 decimals (not 6)."""
        proposal_json = json.dumps({
            "from_mint": "So11111111111111111111111111111111111111112",
            "to_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "amount": 1.0,
            "from_token": "SOL",
            "to_token": "USDC",
            "user_id": "default_user",
        })
        proposal_repo = MagicMock()
        proposal_repo.get_proposal.return_value = {"id": "p2", "status": "pending", "proposal_json": proposal_json}
        exec_svc = _mock_execution_service("tx-sol")

        with (
            patch("src.coordinator.startup.get_trade_proposal_repo", return_value=proposal_repo),
            patch("src.coordinator.startup.get_wallet_execution_service", return_value=exec_svc),
            patch("src.coordinator.jupiter.email_service.send_trade_notification", new=AsyncMock()),
        ):
            resp = client.post("/wallet/confirm/p2")

        assert resp.status_code == 200
        # Verify lamports passed to execute_swap is 1_000_000_000 (9 decimals for SOL)
        call_kwargs = exec_svc.execute_swap.call_args
        assert call_kwargs.kwargs.get("amount_lamports") == 1_000_000_000


# ── /wallet/cancel/{proposal_id} ─────────────────────────────────────────────

class TestCancelTrade:
    def test_cancel_happy_path(self):
        proposal_repo = _mock_proposal_repo()

        with patch("src.coordinator.startup.get_trade_proposal_repo", return_value=proposal_repo):
            resp = client.post("/wallet/cancel/prop-1")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cancelled"
        assert data["proposal_id"] == "prop-1"
        proposal_repo.cancel_proposal.assert_called_once_with("prop-1")

    def test_cancel_proposal_not_found(self):
        proposal_repo = MagicMock()
        proposal_repo.get_proposal.return_value = None

        with patch("src.coordinator.startup.get_trade_proposal_repo", return_value=proposal_repo):
            resp = client.post("/wallet/cancel/no-such-id")

        assert resp.status_code == 404

    def test_cancel_does_not_call_confirm(self):
        proposal_repo = _mock_proposal_repo()

        with patch("src.coordinator.startup.get_trade_proposal_repo", return_value=proposal_repo):
            client.post("/wallet/cancel/prop-1")

        proposal_repo.cancel_proposal.assert_called_once()
        proposal_repo.confirm_proposal.assert_not_called()


# ── /wallet/strategy/approve ─────────────────────────────────────────────────

class TestApproveStrategy:
    def test_approve_happy_path(self):
        svc = _mock_strategy_service(activate_return="strat-xyz")

        with patch("src.coordinator.startup.get_strategy_service", return_value=svc):
            resp = client.post("/wallet/strategy/approve", json={
                "proposal_id": "pp-1",
                "strategy_config": {"name": "MyStrategy", "risk": 0.1},
                "user_id": "user-1",
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["strategy_id"] == "strat-xyz"
        assert data["status"] == "active"
        assert "MyStrategy" in data["message"]

    def test_approve_service_not_initialized(self):
        with patch("src.coordinator.startup.get_strategy_service", return_value=None):
            resp = client.post("/wallet/strategy/approve", json={
                "proposal_id": "pp-1",
                "strategy_config": {},
            })

        assert resp.status_code == 503

    def test_approve_default_user_id(self):
        svc = _mock_strategy_service()

        with patch("src.coordinator.startup.get_strategy_service", return_value=svc):
            resp = client.post("/wallet/strategy/approve", json={
                "proposal_id": "pp-1",
                "strategy_config": {"name": "X"},
            })

        assert resp.status_code == 200
        svc.activate_strategy.assert_called_once()
        call_kwargs = svc.activate_strategy.call_args
        assert call_kwargs.kwargs.get("user_id") == "default_user"

    def test_approve_strategy_name_in_message(self):
        svc = _mock_strategy_service()

        with patch("src.coordinator.startup.get_strategy_service", return_value=svc):
            resp = client.post("/wallet/strategy/approve", json={
                "proposal_id": "pp-1",
                "strategy_config": {"name": "AlphaBot"},
            })

        assert "AlphaBot" in resp.json()["message"]

    def test_approve_strategy_config_without_name(self):
        svc = _mock_strategy_service(activate_return="strat-no-name")

        with patch("src.coordinator.startup.get_strategy_service", return_value=svc):
            resp = client.post("/wallet/strategy/approve", json={
                "proposal_id": "pp-1",
                "strategy_config": {},
            })

        assert resp.status_code == 200
        # Falls back to strategy_id in message
        data = resp.json()
        assert "strat-no-name" in data["message"]


# ── /wallet/strategy/reject/{proposal_id} ────────────────────────────────────

class TestRejectStrategy:
    def test_reject_happy_path(self):
        resp = client.post("/wallet/strategy/reject/prop-99")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["proposal_id"] == "prop-99"

    def test_reject_any_proposal_id(self):
        resp = client.post("/wallet/strategy/reject/some-random-uuid")
        assert resp.status_code == 200
        assert resp.json()["proposal_id"] == "some-random-uuid"


# ── /wallet/strategy/{strategy_id}/pause ─────────────────────────────────────

class TestPauseStrategy:
    def test_pause_happy_path(self):
        svc = _mock_strategy_service(pause_ok=True)

        with patch("src.coordinator.startup.get_strategy_service", return_value=svc):
            resp = client.post("/wallet/strategy/strat-1/pause")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "paused"
        assert data["strategy_id"] == "strat-1"

    def test_pause_not_found(self):
        svc = _mock_strategy_service(pause_ok=False)

        with patch("src.coordinator.startup.get_strategy_service", return_value=svc):
            resp = client.post("/wallet/strategy/ghost/pause")

        assert resp.status_code == 404
        assert "ghost" in resp.json()["detail"]

    def test_pause_service_none(self):
        with patch("src.coordinator.startup.get_strategy_service", return_value=None):
            resp = client.post("/wallet/strategy/strat-1/pause")

        assert resp.status_code == 404

    def test_pause_with_user_id_body(self):
        svc = _mock_strategy_service(pause_ok=True)

        with patch("src.coordinator.startup.get_strategy_service", return_value=svc):
            resp = client.post("/wallet/strategy/strat-1/pause", json={"user_id": "alice"})

        assert resp.status_code == 200
        svc.pause_strategy.assert_called_once_with("strat-1", "alice")


# ── /wallet/strategy/{strategy_id}/resume ────────────────────────────────────

class TestResumeStrategy:
    def test_resume_happy_path(self):
        svc = _mock_strategy_service(resume_ok=True)

        with patch("src.coordinator.startup.get_strategy_service", return_value=svc):
            resp = client.post("/wallet/strategy/strat-2/resume")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "active"
        assert data["strategy_id"] == "strat-2"

    def test_resume_not_found(self):
        svc = _mock_strategy_service(resume_ok=False)

        with patch("src.coordinator.startup.get_strategy_service", return_value=svc):
            resp = client.post("/wallet/strategy/ghost/resume")

        assert resp.status_code == 404

    def test_resume_service_none(self):
        with patch("src.coordinator.startup.get_strategy_service", return_value=None):
            resp = client.post("/wallet/strategy/strat-1/resume")

        assert resp.status_code == 404

    def test_resume_with_user_id(self):
        svc = _mock_strategy_service(resume_ok=True)

        with patch("src.coordinator.startup.get_strategy_service", return_value=svc):
            resp = client.post("/wallet/strategy/strat-1/resume", json={"user_id": "bob"})

        svc.resume_strategy.assert_called_once_with("strat-1", "bob")


# ── /wallet/strategy/{strategy_id}/cancel ────────────────────────────────────

class TestCancelStrategy:
    def test_cancel_happy_path(self):
        svc = _mock_strategy_service(cancel_ok=True)

        with patch("src.coordinator.startup.get_strategy_service", return_value=svc):
            resp = client.post("/wallet/strategy/strat-3/cancel")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cancelled"
        assert data["strategy_id"] == "strat-3"

    def test_cancel_not_found(self):
        svc = _mock_strategy_service(cancel_ok=False)

        with patch("src.coordinator.startup.get_strategy_service", return_value=svc):
            resp = client.post("/wallet/strategy/unknown/cancel")

        assert resp.status_code == 404

    def test_cancel_service_none(self):
        with patch("src.coordinator.startup.get_strategy_service", return_value=None):
            resp = client.post("/wallet/strategy/strat-1/cancel")

        assert resp.status_code == 404

    def test_cancel_with_user_id(self):
        svc = _mock_strategy_service(cancel_ok=True)

        with patch("src.coordinator.startup.get_strategy_service", return_value=svc):
            resp = client.post("/wallet/strategy/strat-1/cancel", json={"user_id": "carol"})

        svc.cancel_strategy.assert_called_once_with("strat-1", "carol")


# ── /wallet/strategies ────────────────────────────────────────────────────────

class TestListStrategies:
    def test_list_happy_path(self):
        svc = _mock_strategy_service()

        with patch("src.coordinator.startup.get_strategy_service", return_value=svc):
            resp = client.get("/wallet/strategies")

        assert resp.status_code == 200
        data = resp.json()
        assert "strategies" in data
        assert isinstance(data["strategies"], list)
        assert len(data["strategies"]) == 1

    def test_list_service_none_returns_empty(self):
        with patch("src.coordinator.startup.get_strategy_service", return_value=None):
            resp = client.get("/wallet/strategies")

        assert resp.status_code == 200
        assert resp.json() == {"strategies": []}

    def test_list_passes_user_id_query_param(self):
        svc = _mock_strategy_service()

        with patch("src.coordinator.startup.get_strategy_service", return_value=svc):
            resp = client.get("/wallet/strategies?user_id=alice")

        assert resp.status_code == 200
        svc.list_strategies.assert_called_once_with(user_id="alice")

    def test_list_default_user_id(self):
        svc = _mock_strategy_service()

        with patch("src.coordinator.startup.get_strategy_service", return_value=svc):
            client.get("/wallet/strategies")

        svc.list_strategies.assert_called_once_with(user_id="default_user")


# ── /wallet/balance/{user_id} ────────────────────────────────────────────────

class TestWalletBalance:
    def test_balance_happy_path_with_jupiter(self):
        wallet_repo = _mock_wallet_repo()
        jupiter_ops = MagicMock()
        jupiter_ops.get_wallet_balance = AsyncMock(return_value={"sol": 5.0, "tokens": [{"mint": "USDC", "amount": 100}]})

        with (
            patch("src.coordinator.startup.get_wallet_repo", return_value=wallet_repo),
            patch("src.coordinator.startup.get_jupiter_ops", return_value=jupiter_ops),
        ):
            resp = client.get("/wallet/balance/default_user")

        assert resp.status_code == 200
        data = resp.json()
        assert data["public_address"] == "SoLANAaddr1111111111111111111111111111111111"
        assert data["sol"] == 5.0
        assert "tokens" in data

    def test_balance_no_wallet(self):
        wallet_repo = MagicMock()
        wallet_repo.get_active_wallet.return_value = None

        with patch("src.coordinator.startup.get_wallet_repo", return_value=wallet_repo):
            resp = client.get("/wallet/balance/no-user")

        assert resp.status_code == 404
        assert "No wallet found" in resp.json()["detail"]

    def test_balance_jupiter_none_returns_stub(self):
        wallet_repo = _mock_wallet_repo()

        with (
            patch("src.coordinator.startup.get_wallet_repo", return_value=wallet_repo),
            patch("src.coordinator.startup.get_jupiter_ops", return_value=None),
        ):
            resp = client.get("/wallet/balance/default_user")

        assert resp.status_code == 200
        data = resp.json()
        assert data["sol"] == 0.0
        assert data["tokens"] == []
        assert "note" in data
        assert "Jupiter MCP" in data["note"]

    def test_balance_jupiter_raises_exception(self):
        wallet_repo = _mock_wallet_repo()
        jupiter_ops = MagicMock()
        jupiter_ops.get_wallet_balance = AsyncMock(side_effect=RuntimeError("network error"))

        with (
            patch("src.coordinator.startup.get_wallet_repo", return_value=wallet_repo),
            patch("src.coordinator.startup.get_jupiter_ops", return_value=jupiter_ops),
        ):
            resp = client.get("/wallet/balance/default_user")

        assert resp.status_code == 503
        assert "Balance check failed" in resp.json()["detail"]


# ── /wallet/create ────────────────────────────────────────────────────────────

class TestCreateWallet:
    def _patch_create(self, wallet_repo=None, existing_wallet=None):
        if wallet_repo is None:
            wallet_repo = MagicMock()
            wallet_repo.get_active_wallet.return_value = existing_wallet

        keypair = {
            "public_address": "NewSoLAddr111111111111111111111111111111111",
            "private_key_b58": "deadbeefdeadbeef",
        }
        enc = MagicMock()
        enc.encrypted = "enc-data"
        enc.salt = "salt"
        enc.nonce = "nonce"

        return (
            patch("src.coordinator.startup.get_wallet_repo", return_value=wallet_repo),
            patch("src.coordinator.jupiter.wallet_manager.generate_new_keypair", return_value=keypair),
            patch("src.coordinator.jupiter.wallet_manager.encrypt_private_key", return_value=enc),
            patch("src.coordinator.jupiter.wallet_manager.cache_session_key"),
        )

    def test_create_happy_path(self):
        wallet_repo = MagicMock()
        wallet_repo.get_active_wallet.return_value = None

        keypair = {
            "public_address": "NewSoLAddr111111111111111111111111111111111",
            "private_key_b58": "deadbeefdeadbeef",
        }
        enc = MagicMock()
        enc.encrypted = "enc-data"
        enc.salt = "salt"
        enc.nonce = "nonce"

        with (
            patch("src.coordinator.startup.get_wallet_repo", return_value=wallet_repo),
            patch("src.coordinator.jupiter.wallet_manager.generate_new_keypair", return_value=keypair),
            patch("src.coordinator.jupiter.wallet_manager.encrypt_private_key", return_value=enc),
            patch("src.coordinator.jupiter.wallet_manager.cache_session_key"),
        ):
            resp = client.post("/wallet/create", json={
                "user_id": "user-1",
                "wallet_name": "Test Wallet",
                "password": "securepw123",
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"
        assert data["public_address"] == "NewSoLAddr111111111111111111111111111111111"
        assert data["network"] == "devnet"

    def test_create_password_too_short(self):
        resp = client.post("/wallet/create", json={
            "user_id": "u1",
            "wallet_name": "W",
            "password": "short",
        })
        assert resp.status_code == 422
        assert "Password must be at least 8 characters" in resp.json()["detail"]

    def test_create_existing_wallet_conflict(self):
        wallet_repo = MagicMock()
        wallet_repo.get_active_wallet.return_value = {
            "public_address": "ExistingAddr111111111111111111111111111111",
        }

        with patch("src.coordinator.startup.get_wallet_repo", return_value=wallet_repo):
            resp = client.post("/wallet/create", json={
                "user_id": "u1",
                "wallet_name": "W",
                "password": "validpassword",
            })

        assert resp.status_code == 409
        assert "already has an active wallet" in resp.json()["detail"]

    def test_create_stores_wallet_in_repo(self):
        wallet_repo = MagicMock()
        wallet_repo.get_active_wallet.return_value = None

        keypair = {
            "public_address": "Addr9999",
            "private_key_b58": "key9999",
        }
        enc = MagicMock()
        enc.encrypted = "enc"
        enc.salt = "s"
        enc.nonce = "n"

        with (
            patch("src.coordinator.startup.get_wallet_repo", return_value=wallet_repo),
            patch("src.coordinator.jupiter.wallet_manager.generate_new_keypair", return_value=keypair),
            patch("src.coordinator.jupiter.wallet_manager.encrypt_private_key", return_value=enc),
            patch("src.coordinator.jupiter.wallet_manager.cache_session_key"),
        ):
            client.post("/wallet/create", json={
                "user_id": "u2",
                "wallet_name": "Vault",
                "password": "password123",
            })

        wallet_repo.create_wallet.assert_called_once()
        call_kwargs = wallet_repo.create_wallet.call_args.kwargs
        assert call_kwargs["user_id"] == "u2"
        assert call_kwargs["wallet_name"] == "Vault"

    def test_create_default_user_id(self):
        wallet_repo = MagicMock()
        wallet_repo.get_active_wallet.return_value = None
        enc = MagicMock()
        enc.encrypted, enc.salt, enc.nonce = "e", "s", "n"

        with (
            patch("src.coordinator.startup.get_wallet_repo", return_value=wallet_repo),
            patch("src.coordinator.jupiter.wallet_manager.generate_new_keypair", return_value={"public_address": "A", "private_key_b58": "k"}),
            patch("src.coordinator.jupiter.wallet_manager.encrypt_private_key", return_value=enc),
            patch("src.coordinator.jupiter.wallet_manager.cache_session_key"),
        ):
            resp = client.post("/wallet/create", json={"password": "password123"})

        assert resp.status_code == 200
        assert resp.json()["user_id"] == "default_user"


# ── /wallet/info/{user_id} ───────────────────────────────────────────────────

class TestWalletInfo:
    def test_info_happy_path(self):
        wallet_repo = _mock_wallet_repo()

        with patch("src.coordinator.startup.get_wallet_repo", return_value=wallet_repo):
            resp = client.get("/wallet/info/default_user")

        assert resp.status_code == 200
        data = resp.json()
        assert data["public_address"] == "SoLANAaddr1111111111111111111111111111111111"
        assert data["wallet_name"] == "My Wallet"
        assert data["network"] == "devnet"
        assert isinstance(data["is_active"], bool)

    def test_info_no_wallet(self):
        wallet_repo = MagicMock()
        wallet_repo.get_active_wallet.return_value = None

        with patch("src.coordinator.startup.get_wallet_repo", return_value=wallet_repo):
            resp = client.get("/wallet/info/ghost-user")

        assert resp.status_code == 404
        assert "No wallet found" in resp.json()["detail"]

    def test_info_is_active_flag(self):
        wallet_repo = MagicMock()
        wallet_repo.get_active_wallet.return_value = {
            "id": 1,
            "public_address": "Addr1",
            "wallet_name": "W",
            "created_at": "2026-01-01",
            "is_active": 0,
        }

        with patch("src.coordinator.startup.get_wallet_repo", return_value=wallet_repo):
            resp = client.get("/wallet/info/u1")

        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_info_missing_optional_fields(self):
        wallet_repo = MagicMock()
        wallet_repo.get_active_wallet.return_value = {
            "id": 2,
            "public_address": "Addr2",
        }

        with patch("src.coordinator.startup.get_wallet_repo", return_value=wallet_repo):
            resp = client.get("/wallet/info/u2")

        assert resp.status_code == 200
        data = resp.json()
        assert data["wallet_name"] == "My Wallet"
        assert data["created_at"] == ""


# ── /wallet/delete/{user_id} ─────────────────────────────────────────────────

class TestDeleteWallet:
    def test_delete_happy_path(self):
        wallet_repo = _mock_wallet_repo()

        with (
            patch("src.coordinator.startup.get_wallet_repo", return_value=wallet_repo),
            patch("src.coordinator.jupiter.wallet_manager.clear_session_key"),
        ):
            resp = client.delete("/wallet/delete/default_user")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "deleted"
        assert data["user_id"] == "default_user"
        assert data["public_address"] == "SoLANAaddr1111111111111111111111111111111111"
        wallet_repo.deactivate_wallet.assert_called_once_with(1)

    def test_delete_no_wallet(self):
        wallet_repo = MagicMock()
        wallet_repo.get_active_wallet.return_value = None

        with patch("src.coordinator.startup.get_wallet_repo", return_value=wallet_repo):
            resp = client.delete("/wallet/delete/ghost-user")

        assert resp.status_code == 404
        assert "No active wallet found" in resp.json()["detail"]

    def test_delete_clears_session_key(self):
        wallet_repo = _mock_wallet_repo()
        mock_clear = MagicMock()

        with (
            patch("src.coordinator.startup.get_wallet_repo", return_value=wallet_repo),
            patch("src.coordinator.jupiter.wallet_manager.clear_session_key", mock_clear),
        ):
            client.delete("/wallet/delete/u1")

        mock_clear.assert_called_once_with("u1")
