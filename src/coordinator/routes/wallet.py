# src/coordinator/routes/wallet.py
"""Wallet API endpoints — confirm/cancel trades, approve/manage strategies, balance."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..dependencies import (
    optional_jupiter_ops,
    optional_strategy_service,
    optional_wallet_execution_service,
    require_trade_proposal_repo,
    require_wallet_repo,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/wallet", tags=["wallet"])


class StrategyApprovalBody(BaseModel):
    proposal_id: str
    strategy_config: dict
    user_id: Optional[str] = "default_user"


class StrategyActionBody(BaseModel):
    user_id: Optional[str] = "default_user"


# ============================================================
# TRADE PROPOSALS (ad-hoc swaps)
# ============================================================

@router.post("/confirm/{proposal_id}")
async def confirm_trade(
    proposal_id: str,
    proposal_repo=Depends(require_trade_proposal_repo),
    execution_service=Depends(optional_wallet_execution_service),
):
    """Confirm an ad-hoc trade proposal. Executes the swap via Jupiter MCP."""
    proposal_record = proposal_repo.get_proposal(proposal_id)

    if not proposal_record:
        raise HTTPException(status_code=404, detail="Proposal not found or expired")

    if proposal_record["status"] != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Proposal is {proposal_record['status']}, cannot confirm"
        )

    # Confirm in DB first
    proposal_repo.confirm_proposal(proposal_id)

    # Execute trade
    try:
        import json
        proposal_data = json.loads(proposal_record["proposal_json"])

        if execution_service is None:
            raise HTTPException(status_code=503, detail="Jupiter MCP not initialized — wallet not unlocked")

        from_mint = proposal_data.get("from_mint", "")
        to_mint = proposal_data.get("to_mint", "")
        amount = proposal_data.get("amount", 0)
        # Convert to lamports (USDC=6 decimals, SOL=9)
        from_token = proposal_data.get("from_token", "USDC")
        amount_lamports = int(amount * 1_000_000) if "USDC" in from_token else int(amount * 1_000_000_000)

        trade_doc = await execution_service.execute_swap(
            user_id=proposal_data.get("user_id", "default_user"),
            from_mint=from_mint,
            to_mint=to_mint,
            from_token=from_token,
            to_token=proposal_data.get("to_token", "SOL"),
            amount_lamports=amount_lamports,
            execution_mode="adhoc_confirmed",
        )

        # Send email notification
        from ..jupiter.email_service import send_trade_notification
        await send_trade_notification(trade_doc)

        return {
            "status": "confirmed",
            "proposal_id": proposal_id,
            "tx_signature": trade_doc.get("tx_signature"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WalletRoute] Confirm trade failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trade execution failed: {type(e).__name__}")


@router.post("/cancel/{proposal_id}")
def cancel_trade(proposal_id: str, proposal_repo=Depends(require_trade_proposal_repo)):
    """Cancel a pending trade proposal."""
    if not proposal_repo.get_proposal(proposal_id):
        raise HTTPException(status_code=404, detail="Proposal not found or expired")

    proposal_repo.cancel_proposal(proposal_id)
    return {"status": "cancelled", "proposal_id": proposal_id}


# ============================================================
# STRATEGY MANAGEMENT
# ============================================================

@router.post("/strategy/approve")
def approve_strategy(body: StrategyApprovalBody, service=Depends(optional_strategy_service)):
    """Approve a strategy proposal. Activates autonomous execution."""
    if service is None:
        raise HTTPException(status_code=503, detail="Strategy service not initialized")

    strategy_id = service.activate_strategy(
        strategy_config=body.strategy_config,
        user_id=body.user_id or "default_user",
    )

    logger.info(f"[WalletRoute] Strategy approved: {strategy_id}")
    return {
        "strategy_id": strategy_id,
        "status": "active",
        "message": f"Strategy '{body.strategy_config.get('name', strategy_id)}' is now active.",
    }


@router.post("/strategy/reject/{proposal_id}")
def reject_strategy(proposal_id: str):
    """Reject a strategy proposal."""
    logger.info(f"[WalletRoute] Strategy proposal rejected: {proposal_id}")
    return {"status": "rejected", "proposal_id": proposal_id}


@router.post("/strategy/{strategy_id}/pause")
def pause_strategy(
    strategy_id: str,
    body: StrategyActionBody = StrategyActionBody(),
    service=Depends(optional_strategy_service),
):
    """Pause an active strategy."""
    if not service or not service.pause_strategy(strategy_id, body.user_id or "default_user"):
        raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
    return {"strategy_id": strategy_id, "status": "paused", "message": "Strategy paused."}


@router.post("/strategy/{strategy_id}/resume")
def resume_strategy(
    strategy_id: str,
    body: StrategyActionBody = StrategyActionBody(),
    service=Depends(optional_strategy_service),
):
    """Resume a paused strategy."""
    if not service or not service.resume_strategy(strategy_id, body.user_id or "default_user"):
        raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
    return {"strategy_id": strategy_id, "status": "active", "message": "Strategy resumed."}


@router.post("/strategy/{strategy_id}/cancel")
def cancel_strategy_endpoint(
    strategy_id: str,
    body: StrategyActionBody = StrategyActionBody(),
    service=Depends(optional_strategy_service),
):
    """Permanently cancel a strategy."""
    if not service or not service.cancel_strategy(strategy_id, body.user_id or "default_user"):
        raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
    return {"strategy_id": strategy_id, "status": "cancelled", "message": "Strategy cancelled."}


@router.get("/strategies")
def list_strategies(user_id: str = "default_user", service=Depends(optional_strategy_service)):
    """List all strategies for a user."""
    if service is None:
        return {"strategies": []}
    return {"strategies": service.list_strategies(user_id=user_id)}


# ============================================================
# WALLET BALANCE
# ============================================================

@router.get("/balance/{user_id}")
async def get_wallet_balance(
    user_id: str,
    wallet_repo=Depends(require_wallet_repo),
    jupiter_ops=Depends(optional_jupiter_ops),
):
    """Get SOL + token balances for the user's wallet."""
    wallet = wallet_repo.get_active_wallet(user_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="No wallet found for user")

    if jupiter_ops is None:
        # Return stored address without live balance
        return {
            "public_address": wallet["public_address"],
            "sol": 0.0,
            "tokens": [],
            "note": "Jupiter MCP not connected — wallet not unlocked",
        }

    try:
        balance = await jupiter_ops.get_wallet_balance(wallet["public_address"])
        return {"public_address": wallet["public_address"], **balance}
    except Exception as e:
        logger.error(f"[WalletRoute] Balance check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Balance check failed: {type(e).__name__}")


class WalletCreateBody(BaseModel):
    user_id: str = "default_user"
    wallet_name: str = "My Wallet"
    password: str


@router.post("/create")
def create_wallet(body: WalletCreateBody):
    """Directly create a new Solana wallet (bypasses conversational flow).

    Used for testing and direct API integrations. In production, wallet creation
    should go through E.E.V.A.'s guided conversational flow for the full ritual.
    """
    from ..jupiter.wallet_manager import generate_new_keypair, encrypt_private_key, cache_session_key

    # Validate password before touching the wallet subsystem — a short password
    # must 422 regardless of whether the repo is initialized. (Resolved here, not
    # via Depends, so this cheap check precedes the require_wallet_repo() 503.)
    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    wallet_repo = require_wallet_repo()

    # Check if user already has an active wallet
    existing = wallet_repo.get_active_wallet(body.user_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"User already has an active wallet: {existing['public_address']}")

    keypair = generate_new_keypair()
    public_address = keypair["public_address"]
    private_key = keypair["private_key_b58"]

    enc = encrypt_private_key(private_key, body.password)
    wallet_repo.create_wallet(
        user_id=body.user_id,
        wallet_name=body.wallet_name,
        public_address=public_address,
        encrypted_private_key=enc.encrypted,
        key_salt=enc.salt,
        key_nonce=enc.nonce,
    )
    cache_session_key(body.user_id, private_key)

    logger.info(f"[WalletRoute] Wallet created for user={body.user_id}, address={public_address}")
    return {
        "status": "created",
        "user_id": body.user_id,
        "wallet_name": body.wallet_name,
        "public_address": public_address,
        "network": "devnet",
        "message": "Wallet created and session key cached. Send SOL/USDC to the address to fund it.",
    }


@router.get("/info/{user_id}")
def get_wallet_info(user_id: str, wallet_repo=Depends(require_wallet_repo)):
    """Get wallet metadata (address, name, creation date) without needing MCP."""
    wallet = wallet_repo.get_active_wallet(user_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="No wallet found for user")

    return {
        "wallet_name": wallet.get("wallet_name", "My Wallet"),
        "public_address": wallet["public_address"],
        "created_at": wallet.get("created_at", ""),
        "is_active": bool(wallet.get("is_active", 1)),
        "network": "devnet",
    }


@router.delete("/delete/{user_id}")
def delete_wallet(user_id: str, wallet_repo=Depends(require_wallet_repo)):
    """Deactivate (soft-delete) the user's active wallet.

    Marks the wallet as inactive in SQLite. The encrypted keypair is retained
    for audit purposes but the wallet is no longer returned by get_active_wallet().
    Also clears any cached session key for this user.
    """
    from ..jupiter.wallet_manager import clear_session_key

    wallet = wallet_repo.get_active_wallet(user_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="No active wallet found for user")

    wallet_repo.deactivate_wallet(wallet["id"])
    clear_session_key(user_id)

    logger.info(f"[WalletRoute] Wallet deactivated for user={user_id}, address={wallet['public_address']}")
    return {
        "status": "deleted",
        "user_id": user_id,
        "public_address": wallet["public_address"],
        "message": "Wallet deactivated and session key cleared.",
    }
