# src/coordinator/services/wallet_creation_flow_service.py
"""Guided multi-turn wallet-creation flow (extracted from QueryHandlerService).

Audit follow-up (matrix #4): the wallet-onboarding state machine used to live as
two ~186-line methods on the `QueryHandlerService` god-class, dispatching on a
bare ``step: int`` pulled from a dict. Here it is its own collaborator with a
typed ``WalletFlowStep`` (IntEnum — keeps the SQLite integer column byte-compatible)
and a ``WalletFlowState`` dataclass, dispatched via ``match``.

Persistence goes through the existing ``WalletFlowRepository`` (durable, session-
keyed). **The BIP39 mnemonic is never persisted**: it is generated at the password
step, rendered once in that turn's reply, and only ever wiped — it is not a field
on ``WalletFlowState`` and is never written to the repository.

The response contract is produced by the ``finalize`` callable injected at
construction (``QueryHandlerService._finalize_response``), so Brave/agentic paths
are untouched and every branch keeps the exact same response shape.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum

from .. import startup  # module ref (not `from ..startup import get_X`): resolves
                        # getters at call time so tests patching startup.get_X still
                        # intercept. Cycle-free — startup imports no service at load.
from ..schemas import ResponseMetadata, SourceType

logger = logging.getLogger(__name__)

_CONFIRM_PHRASES = [
    "i saved it", "saved it", "i've saved it", "confirm", "confirmed",
    "yes", "done", "i wrote it down", "saved", "got it", "ok", "okay",
]


class WalletFlowStep(IntEnum):
    """Guided wallet-creation steps (persisted as the integer step column)."""

    NAME = 1      # awaiting the wallet name
    PASSWORD = 2  # awaiting the password → generate keypair, encrypt, save
    CONFIRM = 3   # awaiting "I saved it" confirmation of the recovery phrase
    DONE = 4      # terminal render only — never persisted


@dataclass(slots=True)
class WalletFlowState:
    """Typed, non-secret wallet-creation flow state.

    Mirrors the ``WalletFlowRepository`` row. There is deliberately NO mnemonic
    field — the seed phrase must never be persisted.
    """

    session_id: str
    step: WalletFlowStep
    user_id: str = "default_user"
    wallet_name: str = "My Wallet"
    public_address: str | None = None
    slots_used: int | None = None
    slots_max: int | None = None

    @classmethod
    def from_row(cls, session_id: str, row: dict, step: WalletFlowStep) -> WalletFlowState:
        return cls(
            session_id=session_id,
            step=step,
            user_id=row.get("user_id", "default_user"),
            wallet_name=row.get("wallet_name", "My Wallet"),
            public_address=row.get("public_address"),
            slots_used=row.get("slots_used"),
            slots_max=row.get("slots_max"),
        )

    def to_repo_dict(self) -> dict:
        """Repository payload — step as int, mnemonic structurally absent."""
        return {
            "step": int(self.step),
            "user_id": self.user_id,
            "wallet_name": self.wallet_name,
            "public_address": self.public_address,
            "slots_used": self.slots_used,
            "slots_max": self.slots_max,
        }


class WalletCreationFlowService:
    """Runs the guided wallet-creation flow, decoupled from query routing."""

    def __init__(self, finalize: Callable[..., dict]):
        # Injected QueryHandlerService._finalize_response (bound) — the shared
        # response-contract builder used by every query path.
        self._finalize = finalize

    # ---- slot cap pre-flight ----

    def preflight(self, user_id, persona_name, metadata, *, log_context):
        """Pre-flight the 3-wallet active cap before starting a creation flow.

        Returns ``(slots_used, slots_max, blocked_response)``: if the user is at
        the active-wallet limit, ``blocked_response`` is a finalized "reached the
        maximum" reply (and the caller should return it immediately); otherwise
        it is None. Any registry error is non-fatal — returns defaults + None so
        creation proceeds without the cap check.
        """
        slots_used, slots_max = 0, 3
        try:
            from ..repositories.wallet_registry_repository import MAX_ACTIVE_WALLETS
            registry_repo = startup.get_wallet_registry_repo()
            if registry_repo:
                allowed, count, _ = registry_repo.can_create_wallet(user_id or "default_user")
                slots_used, slots_max = count, MAX_ACTIVE_WALLETS
                if not allowed:
                    metadata.source_type = SourceType.WALLET_MCP
                    metadata.tools_used = []
                    logger.info(
                        f"{log_context} creation blocked — user={user_id} "
                        f"at limit ({count}/{MAX_ACTIVE_WALLETS})"
                    )
                    blocked = self._finalize(
                        answer=(
                            f"You've reached the maximum of {MAX_ACTIVE_WALLETS} active wallets. "
                            "To create a new one, please delete an existing wallet first."
                        ),
                        persona_name=persona_name,
                        metadata=metadata,
                        used_search=False,
                    )
                    return slots_used, slots_max, blocked
        except Exception as e:
            logger.warning(f"{log_context} wallet slot pre-flight check failed (non-fatal): {e}")
        return slots_used, slots_max, None

    # ---- start (dedup of the two former start blocks) ----

    def start(self, *, session_id, user_id, wallet_name, persona_name, metadata,
              source_type, log_context) -> dict:
        """Begin a guided creation flow (step 1): pre-flight, persist, prompt for name."""
        slots_used, slots_max, blocked = self.preflight(
            user_id, persona_name, metadata, log_context=log_context
        )
        if blocked is not None:
            return blocked

        from ..services.wallet_proposal_service import build_wallet_creation_step

        state = WalletFlowState(
            session_id=session_id or "",
            step=WalletFlowStep.NAME,
            user_id=user_id or "default_user",
            wallet_name=wallet_name,
            slots_used=slots_used,
            slots_max=slots_max,
        )
        flow_repo = startup.get_wallet_flow_repo()
        if flow_repo:
            flow_repo.upsert(state.session_id, state.to_repo_dict())

        step_msg = build_wallet_creation_step(step=1, slots_used=slots_used, slots_max=slots_max)
        metadata.source_type = source_type
        metadata.tools_used = ["wallet_create_guided"]
        logger.info(
            f"{log_context} Wallet creation flow started for user={user_id} "
            f"(slot {slots_used + 1}/{slots_max})"
        )
        return self._finalize(
            answer=step_msg["content"],
            persona_name=persona_name,
            metadata=metadata,
            used_search=True,
        )

    # ---- advance (the step machine) ----

    def advance(self, *, message: str, flow_state: dict, session_id: str, user_id: str,
                persona_name: str, metadata: ResponseMetadata) -> dict:
        """Handle one turn of the guided flow, dispatching on the persisted step.

        Step 1: user provides wallet name.
        Step 2: user provides password — generate keypair from BIP39 mnemonic, encrypt, save.
        Step 3: display the 12-word mnemonic — user must confirm they saved it.
        Step 4: user confirms — the (never-persisted) mnemonic is out of scope; show success.
        """
        flow_repo = startup.get_wallet_flow_repo()
        try:
            step = WalletFlowStep(flow_state.get("step", 1))
        except ValueError:
            return self._reset(session_id, persona_name, metadata, flow_repo)

        state = WalletFlowState.from_row(session_id, flow_state, step)

        match step:
            case WalletFlowStep.NAME:
                return self._step_name(message, state, persona_name, metadata, flow_repo)
            case WalletFlowStep.PASSWORD:
                return self._step_password(message, state, user_id, persona_name, metadata, flow_repo)
            case WalletFlowStep.CONFIRM:
                return self._step_confirm(message, state, user_id, persona_name, metadata, flow_repo)
            case _:
                # DONE is a render-only value and should never be persisted.
                return self._reset(session_id, persona_name, metadata, flow_repo)

    def _step_name(self, message, state, persona_name, metadata, flow_repo) -> dict:
        from ..services.wallet_proposal_service import build_wallet_creation_step

        state.wallet_name = message.strip() or "My Wallet"
        state.step = WalletFlowStep.PASSWORD
        if flow_repo:
            flow_repo.upsert(state.session_id, state.to_repo_dict())
        step_msg = build_wallet_creation_step(step=2, wallet_name=state.wallet_name)
        metadata.source_type = SourceType.WALLET_MCP
        return self._finalize(
            answer=step_msg["content"],
            persona_name=persona_name,
            metadata=metadata,
            used_search=True,
        )

    def _step_password(self, message, state, user_id, persona_name, metadata, flow_repo) -> dict:
        from ..jupiter.wallet_manager import (
            cache_session_key,
            encrypt_private_key,
            generate_keypair_from_mnemonic,
            generate_mnemonic,
        )
        from ..services.wallet_proposal_service import build_wallet_creation_step

        password = message.strip()
        if len(password) < 8:
            metadata.source_type = SourceType.WALLET_MCP
            return self._finalize(
                answer="That password is too short — please choose at least 8 characters.",
                persona_name=persona_name,
                metadata=metadata,
                used_search=False,
            )

        # Generate BIP39 mnemonic and derive keypair
        mnemonic_phrase = generate_mnemonic()
        keypair = generate_keypair_from_mnemonic(mnemonic_phrase)
        public_address = keypair["public_address"]
        private_key = keypair["private_key_b58"]

        enc = encrypt_private_key(private_key, password)

        # Save encrypted wallet to SQLite
        try:
            wallet_repo = startup.get_wallet_repo()
            wallet_repo.create_wallet(
                user_id=user_id,
                wallet_name=state.wallet_name,
                public_address=public_address,
                encrypted_private_key=enc.encrypted,
                key_salt=enc.salt,
                key_nonce=enc.nonce,
            )
            # Cache in session (wallet is unlocked immediately after creation)
            cache_session_key(user_id, private_key)
        except Exception as e:
            logger.error(f"[WalletCreation] Failed to save wallet: {e}")
            # Zero out sensitive data before clearing
            mnemonic_phrase = "\x00" * len(mnemonic_phrase)
            del mnemonic_phrase
            if flow_repo:
                flow_repo.delete(state.session_id)
            metadata.source_type = SourceType.WALLET_MCP
            return self._finalize(
                answer="I encountered an error saving your wallet. Please try again.",
                persona_name=persona_name,
                metadata=metadata,
                used_search=False,
            )

        # Register in wallet registry (multi-wallet tracking)
        try:
            registry_repo = startup.get_wallet_registry_repo()
            if registry_repo:
                registry_repo.register_wallet(
                    user_id=user_id,
                    wallet_name=state.wallet_name,
                    public_address=public_address,
                )
        except Exception as e:
            logger.warning(f"[WalletCreation] Registry write failed (non-fatal): {e}")

        # Update activity summary
        try:
            summary_repo = startup.get_wallet_summary_repo()
            if summary_repo:
                reg = startup.get_wallet_registry_repo()
                active_count = reg.get_active_count(user_id) if reg else 1
                summary_repo.upsert_summary(
                    user_id=user_id,
                    active_wallet_count=active_count,
                    total_wallets_ever=(summary_repo.get_summary(user_id) or {}).get("total_wallets_ever", 0) + 1,
                )
        except Exception as e:
            logger.warning(f"[WalletCreation] Summary update failed (non-fatal): {e}")

        # Advance to step 3. The mnemonic is displayed in THIS response only and
        # is never persisted (it is only ever wiped at step 3, never re-read), so
        # it stays a local variable and no seed phrase touches disk.
        state.step = WalletFlowStep.CONFIRM
        state.public_address = public_address
        if flow_repo:
            flow_repo.upsert(state.session_id, state.to_repo_dict())

        step_msg = build_wallet_creation_step(
            step=3,
            mnemonic=mnemonic_phrase,
            public_address=public_address,
        )
        metadata.source_type = SourceType.WALLET_MCP
        metadata.tools_used = ["wallet_create_guided"]
        return self._finalize(
            answer=step_msg["content"],
            persona_name=persona_name,
            metadata=metadata,
            used_search=True,
        )

    def _step_confirm(self, message, state, user_id, persona_name, metadata, flow_repo) -> dict:
        from ..services.wallet_proposal_service import build_wallet_creation_step

        msg_lower = message.strip().lower()
        if not any(p in msg_lower for p in _CONFIRM_PHRASES):
            metadata.source_type = SourceType.WALLET_MCP
            return self._finalize(
                answer=(
                    "Please confirm you've saved your 12-word recovery phrase before continuing. "
                    "Type **'I saved it'** or **'confirm'** to proceed. "
                    "This phrase will be permanently deleted and cannot be shown again."
                ),
                persona_name=persona_name,
                metadata=metadata,
                used_search=False,
            )

        # User confirmed — complete the flow. The mnemonic was never persisted
        # (shown once at step 2, request-local), so there is nothing to wipe here.
        public_address = state.public_address or "N/A"
        if flow_repo:
            flow_repo.delete(state.session_id)

        logger.info(f"[WalletCreation] Flow complete for user={user_id}, wallet creation done")

        step_msg = build_wallet_creation_step(step=4, public_address=public_address)
        metadata.source_type = SourceType.WALLET_MCP
        metadata.tools_used = ["wallet_create_guided"]
        return self._finalize(
            answer=step_msg["content"],
            persona_name=persona_name,
            metadata=metadata,
            used_search=True,
        )

    def _reset(self, session_id, persona_name, metadata, flow_repo) -> dict:
        # Unknown step — clear and restart (no persisted secrets to wipe).
        if flow_repo:
            flow_repo.delete(session_id)
        return self._finalize(
            answer="Something went wrong with the wallet setup. Let's start over — say 'create wallet' when ready.",
            persona_name=persona_name,
            metadata=metadata,
            used_search=False,
        )
