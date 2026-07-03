# tests/backend/coordinator/test_wallet_proposal_service.py
"""Unit tests for wallet_proposal_service — all public functions."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from src.coordinator.services.wallet_proposal_service import (
    PROPOSAL_TTL_SECONDS,
    build_trade_proposal,
    build_strategy_proposal,
    build_wallet_deletion_proposal,
    build_wallet_creation_step,
    _get_known_mint,
)


# ---------------------------------------------------------------------------
# _get_known_mint
# ---------------------------------------------------------------------------

class TestGetKnownMint:
    def test_sol(self):
        assert _get_known_mint("SOL") == "So11111111111111111111111111111111111111112"

    def test_usdc(self):
        assert _get_known_mint("USDC") == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    def test_usdt(self):
        assert _get_known_mint("USDT") == "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"

    def test_bonk(self):
        assert _get_known_mint("BONK") == "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"

    def test_jup(self):
        assert _get_known_mint("JUP") == "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"

    def test_unknown_symbol_returns_empty(self):
        assert _get_known_mint("DOGE") == ""

    def test_lowercase_input_normalised(self):
        assert _get_known_mint("sol") == "So11111111111111111111111111111111111111112"


# ---------------------------------------------------------------------------
# build_trade_proposal
# ---------------------------------------------------------------------------

class TestBuildTradeProposal:
    def _build(self, **kw):
        defaults = dict(
            user_id="user123",
            from_token="USDC",
            to_token="SOL",
            amount=100.0,
        )
        defaults.update(kw)
        return build_trade_proposal(**defaults)

    def test_returns_dict_with_required_keys(self):
        result = self._build()
        assert "content" in result
        assert "metadata" in result

    def test_metadata_source_type(self):
        result = self._build()
        assert result["metadata"]["source_type"] == "wallet_proposal"
        assert result["metadata"]["proposal_type"] == "trade_proposal"

    def test_proposal_data_fields(self):
        result = self._build(user_id="u1", from_token="USDC", to_token="SOL", amount=50.0)
        p = result["metadata"]["proposal"]
        assert p["user_id"] == "u1"
        assert p["from_token"] == "USDC"
        assert p["to_token"] == "SOL"
        assert p["amount"] == 50.0
        assert p["proposal_type"] == "swap"
        assert p["status"] == "pending"

    def test_proposal_id_is_uuid(self):
        result = self._build()
        proposal_id = result["metadata"]["proposal"]["proposal_id"]
        # Should parse as UUID without error
        uuid.UUID(proposal_id)

    def test_expires_at_after_created_at(self):
        result = self._build()
        p = result["metadata"]["proposal"]
        created = datetime.fromisoformat(p["created_at"])
        expires = datetime.fromisoformat(p["expires_at"])
        delta = (expires - created).total_seconds()
        assert abs(delta - PROPOSAL_TTL_SECONDS) < 2  # within 2s

    def test_default_reason_generated(self):
        result = self._build(from_token="USDC", to_token="SOL", amount=25.0)
        p = result["metadata"]["proposal"]
        assert "USDC" in p["reason"] or "SOL" in p["reason"]

    def test_custom_reason_used(self):
        result = self._build(reason="DCA buy signal")
        p = result["metadata"]["proposal"]
        assert p["reason"] == "DCA buy signal"

    def test_narrative_without_quote(self):
        result = self._build(quote=None)
        assert "proposal" in result["content"].lower() or "swap" in result["content"].lower()
        # No amount string injected
        assert "receive approximately" not in result["content"]

    def test_narrative_with_quote_includes_amount(self):
        quote = {"out_amount_human": "0.42", "price_impact_pct": 0.5}
        result = self._build(quote=quote)
        assert "0.42 SOL" in result["content"]
        assert "0.50%" in result["content"]

    def test_quote_with_zero_price_impact(self):
        quote = {"out_amount_human": "1.0", "price_impact_pct": 0.0}
        result = self._build(quote=quote)
        assert "0.00%" in result["content"]


# ---------------------------------------------------------------------------
# build_strategy_proposal
# ---------------------------------------------------------------------------

class TestBuildStrategyProposal:
    def _build(self, **kw):
        defaults = dict(
            user_id="user42",
            strategy_type="RSIStrategy",
            name="My RSI Strategy",
            from_token="USDC",
            to_token="SOL",
            parameters={"rsi_period": 14},
            max_trade_size_usdc=200.0,
            daily_limit_usdc=500.0,
        )
        defaults.update(kw)
        return build_strategy_proposal(**defaults)

    def test_returns_dict_with_content_metadata(self):
        result = self._build()
        assert "content" in result
        assert "metadata" in result

    def test_metadata_proposal_type(self):
        result = self._build()
        assert result["metadata"]["proposal_type"] == "strategy_proposal"
        assert result["metadata"]["source_type"] == "wallet_proposal"

    def test_strategy_config_status(self):
        result = self._build()
        sc = result["metadata"]["proposal"]["strategy_config"]
        assert sc["status"] == "pending_approval"
        assert sc["approved_at"] is None

    def test_strategy_id_includes_token_and_type(self):
        result = self._build(to_token="SOL", strategy_type="RSIStrategy")
        sc = result["metadata"]["proposal"]["strategy_config"]
        sid = sc["strategy_id"]
        assert "sol" in sid
        assert "rsi" in sid

    def test_guardrails_stored(self):
        result = self._build(max_trade_size_usdc=150.0, daily_limit_usdc=400.0)
        g = result["metadata"]["proposal"]["strategy_config"]["guardrails"]
        assert g["max_trade_size_usdc"] == 150.0
        assert g["daily_limit_usdc"] == 400.0
        assert g["spent_today_usdc"] == 0.0

    def test_risk_management_with_sl_tp(self):
        result = self._build(stop_loss_pct=5.0, take_profit_pct=10.0)
        rm = result["metadata"]["proposal"]["strategy_config"]["risk_management"]
        assert rm["stop_loss_pct"] == 5.0
        assert rm["take_profit_pct"] == 10.0

    def test_risk_management_without_sl_tp(self):
        result = self._build(stop_loss_pct=None, take_profit_pct=None)
        rm = result["metadata"]["proposal"]["strategy_config"]["risk_management"]
        assert rm["stop_loss_pct"] is None
        assert rm["take_profit_pct"] is None

    def test_narrative_includes_guardrails(self):
        result = self._build(max_trade_size_usdc=200.0, daily_limit_usdc=500.0)
        assert "200" in result["content"]
        assert "500" in result["content"]

    def test_narrative_no_stop_loss_text(self):
        result = self._build(stop_loss_pct=None)
        assert "No stop-loss" in result["content"]

    def test_narrative_with_stop_loss_text(self):
        result = self._build(stop_loss_pct=7.5)
        assert "Stop-loss: 7.5%" in result["content"]

    def test_narrative_no_take_profit_text(self):
        result = self._build(take_profit_pct=None)
        assert "No take-profit" in result["content"]

    def test_narrative_with_take_profit_text(self):
        result = self._build(take_profit_pct=15.0)
        assert "Take-profit: 15.0%" in result["content"]

    def test_known_mint_injected(self):
        result = self._build(from_token="USDC", to_token="SOL")
        tp = result["metadata"]["proposal"]["strategy_config"]["token_pair"]
        assert tp["from_mint"] == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        assert tp["to_mint"] == "So11111111111111111111111111111111111111112"

    def test_unknown_token_mint_empty(self):
        result = self._build(to_token="PEPE")
        tp = result["metadata"]["proposal"]["strategy_config"]["token_pair"]
        assert tp["to_mint"] == ""


# ---------------------------------------------------------------------------
# build_wallet_deletion_proposal
# ---------------------------------------------------------------------------

class TestBuildWalletDeletionProposal:
    def _build(self, **kw):
        defaults = dict(
            user_id="user1",
            wallet_name="Trading Wallet",
            public_address="ABC123DEF456GHI789JKL012",
        )
        defaults.update(kw)
        return build_wallet_deletion_proposal(**defaults)

    def test_returns_dict_with_keys(self):
        result = self._build()
        assert "content" in result
        assert "metadata" in result

    def test_proposal_type_wallet_deletion(self):
        result = self._build()
        assert result["metadata"]["proposal_type"] == "wallet_deletion"

    def test_short_address_in_narrative(self):
        addr = "ABC123DEF456GHI789JKL012"
        result = self._build(public_address=addr)
        short = f"{addr[:8]}...{addr[-4:]}"
        assert short in result["content"]

    def test_very_short_address_not_truncated(self):
        addr = "SHORT"
        result = self._build(public_address=addr)
        assert "SHORT" in result["content"]

    def test_wallet_name_in_narrative(self):
        result = self._build(wallet_name="My Hot Wallet")
        assert "My Hot Wallet" in result["content"]

    def test_irreversible_warning_present(self):
        result = self._build()
        assert "irreversible" in result["content"].lower()

    def test_expires_at_after_created_at(self):
        result = self._build()
        p = result["metadata"]["proposal"]
        created = datetime.fromisoformat(p["created_at"])
        expires = datetime.fromisoformat(p["expires_at"])
        delta = (expires - created).total_seconds()
        assert abs(delta - PROPOSAL_TTL_SECONDS) < 2


# ---------------------------------------------------------------------------
# build_wallet_creation_step
# ---------------------------------------------------------------------------

class TestBuildWalletCreationStep:
    def test_step_1_default(self):
        result = build_wallet_creation_step(1)
        assert result["metadata"]["wallet_step"] == 1
        assert "wallet_step" in result["metadata"]
        assert "Step 1" in result["content"]

    def test_step_2_wallet_name_default(self):
        result = build_wallet_creation_step(2)
        assert "Step 2" in result["content"]
        assert result["metadata"]["wallet_name"] == "My Wallet"

    def test_step_2_custom_wallet_name(self):
        result = build_wallet_creation_step(2, wallet_name="Trading Wallet")
        assert result["metadata"]["wallet_name"] == "Trading Wallet"

    def test_step_3_mnemonic_displayed(self):
        mnemonic = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12"
        result = build_wallet_creation_step(3, mnemonic=mnemonic, public_address="PUBKEY")
        assert mnemonic in result["content"]
        assert result["metadata"]["ephemeral"] is True
        assert result["metadata"]["secret_displayed"] is True

    def test_step_4_wallet_created_flag(self):
        result = build_wallet_creation_step(4, public_address="MYADDR")
        assert result["metadata"]["wallet_created"] is True
        assert "MYADDR" in result["content"]

    def test_slot_info_injected(self):
        result = build_wallet_creation_step(1, slots_used=1, slots_max=3)
        # slot_info format: " (wallet slot 2 of 3)"
        assert "slot 2 of 3" in result["content"]

    def test_invalid_step_falls_back_to_step1(self):
        result = build_wallet_creation_step(99)
        assert result["metadata"]["wallet_step"] == 1

    def test_total_steps_reflected(self):
        result = build_wallet_creation_step(1, total_steps=5)
        assert "5" in result["content"]
        assert result["metadata"]["total_steps"] == 5
