# tests/backend/coordinator/test_wallet_creation_flow.py
"""Characterization tests for the guided wallet-creation state machine.

Locks the behavior of the step 1→2→3→4 flow BEFORE it is refactored into a
typed WalletCreationFlowService (audit follow-up matrix #4). No network, no
Ollama — the external collaborators (wallet_manager, repositories, the
message builder) are mocked; the real _finalize_response contract is exercised.

Critical invariant asserted: the BIP39 mnemonic is never written to the flow
repository (it is displayed once at step 2 and only wiped, never persisted).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.coordinator.schemas import ResponseMetadata
from src.coordinator.services.query_handler_service import QueryHandlerService
from src.coordinator.services.wallet_creation_flow_service import (
    WalletFlowState,
    WalletFlowStep,
)

WM = "src.coordinator.jupiter.wallet_manager"
SU = "src.coordinator.startup"
WP = "src.coordinator.services.wallet_proposal_service.build_wallet_creation_step"


@pytest.fixture()
def svc():
    return QueryHandlerService()


@pytest.fixture()
def repos():
    """Patch the lazily-imported startup getters + wallet_manager + message builder."""
    flow = MagicMock(name="flow_repo")
    wallet = MagicMock(name="wallet_repo")
    registry = MagicMock(name="registry_repo")
    registry.get_active_count.return_value = 1
    summary = MagicMock(name="summary_repo")
    summary.get_summary.return_value = None
    with patch(f"{SU}.get_wallet_flow_repo", return_value=flow), \
         patch(f"{SU}.get_wallet_repo", return_value=wallet), \
         patch(f"{SU}.get_wallet_registry_repo", return_value=registry), \
         patch(f"{SU}.get_wallet_summary_repo", return_value=summary), \
         patch(f"{WP}", side_effect=lambda step, **kw: {"content": f"STEP{step}", "kw": kw}), \
         patch(f"{WM}.generate_mnemonic", return_value="w1 w2 w3 w4 w5 w6 w7 w8 w9 w10 w11 w12"), \
         patch(f"{WM}.generate_keypair_from_mnemonic",
               return_value={"public_address": "PUBADDR", "private_key_b58": "PRIVKEY"}), \
         patch(f"{WM}.encrypt_private_key",
               return_value=MagicMock(encrypted="ENC", salt="SALT", nonce="NONCE")), \
         patch(f"{WM}.cache_session_key"):
        yield {"flow": flow, "wallet": wallet, "registry": registry, "summary": summary}


def _run(svc, message, flow_state):
    # Drives the extracted WalletCreationFlowService (same behavior the
    # QueryHandlerService method had before the refactor).
    return svc._wallet_flow.advance(
        message=message,
        flow_state=dict(flow_state),
        session_id="s1",
        user_id="u1",
        persona_name="E.E.V.A.",
        metadata=ResponseMetadata(),
    )


def _assert_response_contract(resp):
    assert {"answer", "message_flow", "message_count", "used_search",
            "metadata", "rewritten"}.issubset(resp.keys())


# ---- Step 1: name → advance to step 2 ----

def test_step1_sets_name_and_advances(svc, repos):
    resp = _run(svc, "My Vault", {"step": 1, "user_id": "u1"})
    _assert_response_contract(resp)
    repos["flow"].upsert.assert_called_once()
    _, state = repos["flow"].upsert.call_args[0]
    assert state["wallet_name"] == "My Vault"
    assert state["step"] == 2


def test_step1_blank_name_defaults(svc, repos):
    _run(svc, "   ", {"step": 1, "user_id": "u1"})
    _, state = repos["flow"].upsert.call_args[0]
    assert state["wallet_name"] == "My Wallet"


# ---- Step 2: password → create wallet, advance to step 3 ----

def test_step2_short_password_rejected_no_writes(svc, repos):
    resp = _run(svc, "short", {"step": 2, "user_id": "u1", "wallet_name": "W"})
    _assert_response_contract(resp)
    repos["wallet"].create_wallet.assert_not_called()
    repos["flow"].upsert.assert_not_called()
    repos["flow"].delete.assert_not_called()


def test_step2_creates_wallet_and_advances(svc, repos):
    resp = _run(svc, "password123", {"step": 2, "user_id": "u1", "wallet_name": "W"})
    _assert_response_contract(resp)
    repos["wallet"].create_wallet.assert_called_once()
    # advanced to step 3 with the public address
    _, state = repos["flow"].upsert.call_args[0]
    assert state["step"] == 3
    assert state["public_address"] == "PUBADDR"


def test_step2_mnemonic_shown_but_never_persisted(svc, repos):
    """The seed is rendered once (step-3 message) but never written to the repo."""
    with patch(f"{WP}", side_effect=lambda step, **kw: {"content": "X", "kw": kw}) as mk:
        _run(svc, "password123", {"step": 2, "user_id": "u1", "wallet_name": "W"})
    # displayed to the user in the step-3 render...
    step3_call = [c for c in mk.call_args_list if c.kwargs.get("step") == 3][0]
    assert step3_call.kwargs["mnemonic"].startswith("w1 ")
    # ...but NO upsert payload ever carried a mnemonic
    for call in repos["flow"].upsert.call_args_list:
        _, state = call[0]
        assert "mnemonic" not in state


def test_step2_save_failure_deletes_flow(svc, repos):
    repos["wallet"].create_wallet.side_effect = RuntimeError("db down")
    resp = _run(svc, "password123", {"step": 2, "user_id": "u1", "wallet_name": "W"})
    _assert_response_contract(resp)
    repos["flow"].delete.assert_called_once_with("s1")


# ---- Step 3: confirm → complete, delete flow ----

def test_step3_confirm_completes_and_deletes(svc, repos):
    resp = _run(svc, "I saved it",
                {"step": 3, "user_id": "u1", "wallet_name": "W", "public_address": "PUBADDR"})
    _assert_response_contract(resp)
    repos["flow"].delete.assert_called_once_with("s1")


def test_step3_unconfirmed_does_not_delete(svc, repos):
    _run(svc, "hang on a sec",
         {"step": 3, "user_id": "u1", "wallet_name": "W", "public_address": "PUBADDR"})
    repos["flow"].delete.assert_not_called()


# ---- Unknown step: reset ----

def test_unknown_step_resets(svc, repos):
    _run(svc, "whatever", {"step": 9, "user_id": "u1"})
    repos["flow"].delete.assert_called_once_with("s1")


# ---- Typed layer: WalletFlowStep / WalletFlowState ----

def test_step_enum_is_int_compatible_with_stored_values():
    # The SQLite column stores plain ints — the enum must round-trip through them.
    assert int(WalletFlowStep.NAME) == 1
    assert int(WalletFlowStep.PASSWORD) == 2
    assert int(WalletFlowStep.CONFIRM) == 3
    assert WalletFlowStep(2) is WalletFlowStep.PASSWORD


def test_state_to_repo_dict_has_no_mnemonic_field():
    state = WalletFlowState(
        session_id="s", step=WalletFlowStep.CONFIRM, user_id="u",
        wallet_name="W", public_address="ADDR", slots_used=0, slots_max=3,
    )
    row = state.to_repo_dict()
    assert "mnemonic" not in row
    assert row["step"] == 3 and isinstance(row["step"], int)
    assert row["public_address"] == "ADDR"
    # dataclass has no mnemonic attribute at all (structurally impossible to persist)
    assert not hasattr(state, "mnemonic")


def test_state_from_row_roundtrip():
    row = {"step": 2, "user_id": "u", "wallet_name": "W",
           "public_address": None, "slots_used": 1, "slots_max": 3}
    state = WalletFlowState.from_row("s", row, WalletFlowStep.PASSWORD)
    assert state.session_id == "s" and state.wallet_name == "W" and state.slots_used == 1
    assert state.to_repo_dict()["step"] == 2
