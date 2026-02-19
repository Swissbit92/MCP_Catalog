# src/coordinator/services/wallet_proposal_service.py
"""Builds ProposalCard and StrategyApprovalCard chat message payloads.

These are structured messages returned in the chat response that the frontend
renders as interactive confirmation cards (not plain text).
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

PROPOSAL_TTL_SECONDS = 300  # 5 minutes


def build_trade_proposal(
    user_id: str,
    from_token: str,
    to_token: str,
    amount: float,
    quote: Optional[dict] = None,
    reason: Optional[str] = None,
) -> dict:
    """Build a ProposalCard payload for ad-hoc swap confirmation.

    Returns a chat message dict with type='trade_proposal' in metadata.
    The frontend renders this as a confirm/cancel card.

    Args:
        user_id: User identifier
        from_token: Token being sold (e.g. "USDC")
        to_token: Token being bought (e.g. "SOL")
        amount: Amount to sell
        quote: Optional pre-fetched Jupiter quote dict
        reason: Optional explanation from E.E.V.A.

    Returns:
        Chat message dict with proposal metadata
    """
    proposal_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=PROPOSAL_TTL_SECONDS)

    proposal_data = {
        "proposal_id": proposal_id,
        "proposal_type": "swap",
        "user_id": user_id,
        "from_token": from_token,
        "to_token": to_token,
        "amount": amount,
        "quote": quote,
        "reason": reason or f"Swap {amount} {from_token} for {to_token}",
        "status": "pending",
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
    }

    # Generate E.E.V.A.'s narrative text
    out_amount_str = ""
    if quote:
        out = quote.get("out_amount_human", "?")
        impact = quote.get("price_impact_pct", 0)
        out_amount_str = (
            f" You'd receive approximately **{out} {to_token}**"
            f" (price impact: {impact:.2f}%)"
        )

    narrative = (
        f"I've prepared a swap proposal.{out_amount_str} "
        f"Review the details below and confirm if you'd like to proceed. "
        f"This proposal expires in 5 minutes."
    )

    return {
        "content": narrative,
        "metadata": {
            "source_type": "wallet_proposal",
            "proposal_type": "trade_proposal",
            "proposal": proposal_data,
        },
    }


def build_strategy_proposal(
    user_id: str,
    strategy_type: str,
    name: str,
    from_token: str,
    to_token: str,
    parameters: dict,
    max_trade_size_usdc: float,
    daily_limit_usdc: float,
    stop_loss_pct: Optional[float] = None,
    take_profit_pct: Optional[float] = None,
) -> dict:
    """Build a StrategyApprovalCard payload for one-time strategy approval.

    Returns a chat message dict with type='strategy_proposal' in metadata.

    Args:
        user_id: User identifier
        strategy_type: 'RSIStrategy' or 'DCAStrategy'
        name: Human-readable name
        from_token: Token to sell (usually USDC)
        to_token: Token to buy
        parameters: Strategy-specific parameters dict
        max_trade_size_usdc: Max per-trade USDC amount
        daily_limit_usdc: Daily USDC spending limit
        stop_loss_pct: Optional stop-loss percentage
        take_profit_pct: Optional take-profit percentage

    Returns:
        Chat message dict with strategy proposal metadata
    """
    from datetime import date

    proposal_id = str(uuid.uuid4())
    today = date.today().isoformat()

    # Build the full strategy JSON that will be saved on approval
    strategy_config = {
        "strategy_id": (
            f"{to_token.lower()}_{strategy_type.lower().replace('strategy', '')}_{proposal_id[:8]}"
        ),
        "strategy_type": strategy_type,
        "name": name,
        "status": "pending_approval",
        "user_id": user_id,
        "approved_at": None,
        "token_pair": {
            "from_token": from_token,
            "from_mint": _get_known_mint(from_token),
            "to_token": to_token,
            "to_mint": _get_known_mint(to_token),
        },
        "parameters": parameters,
        "risk_management": {
            "stop_loss_pct": stop_loss_pct,
            "take_profit_pct": take_profit_pct,
        },
        "guardrails": {
            "max_trade_size_usdc": max_trade_size_usdc,
            "daily_limit_usdc": daily_limit_usdc,
            "spent_today_usdc": 0.0,
            "daily_reset_date": today,
        },
    }

    proposal_data = {
        "proposal_id": proposal_id,
        "proposal_type": "strategy",
        "user_id": user_id,
        "strategy_config": strategy_config,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Build guardrail summary for E.E.V.A.'s narrative
    sl_text = f"Stop-loss: {stop_loss_pct}%" if stop_loss_pct else "No stop-loss"
    tp_text = f"Take-profit: {take_profit_pct}%" if take_profit_pct else "No take-profit"

    narrative = (
        f"I've designed a **{name}** strategy for you. "
        f"Guardrails: max {max_trade_size_usdc} USDC per trade, {daily_limit_usdc} USDC/day. "
        f"{sl_text}. {tp_text}. "
        f"Once you approve, I'll execute autonomously and notify you after each trade. "
        f"You can pause or cancel anytime by telling me."
    )

    return {
        "content": narrative,
        "metadata": {
            "source_type": "wallet_proposal",
            "proposal_type": "strategy_proposal",
            "proposal": proposal_data,
        },
    }


def build_wallet_deletion_proposal(
    user_id: str,
    wallet_name: str,
    public_address: str,
) -> dict:
    """Build a WalletDeletionCard payload for chat-based wallet deletion.

    Returns a chat message dict with proposal_type='wallet_deletion' in metadata.
    The frontend renders this as a confirm/cancel card with countdown timer.

    Args:
        user_id: User identifier
        wallet_name: Human-readable wallet label
        public_address: Solana public key (base58)

    Returns:
        Chat message dict with wallet deletion proposal metadata
    """
    proposal_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=PROPOSAL_TTL_SECONDS)

    short_addr = f"{public_address[:8]}...{public_address[-4:]}" if len(public_address) > 12 else public_address

    proposal_data = {
        "proposal_id": proposal_id,
        "proposal_type": "wallet_deletion",
        "user_id": user_id,
        "wallet_name": wallet_name,
        "public_address": public_address,
        "status": "pending",
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
    }

    narrative = (
        f"You're about to delete **{wallet_name}** (`{short_addr}`). "
        "This is irreversible. Any remaining funds should be transferred first. "
        "Confirm below to proceed."
    )

    return {
        "content": narrative,
        "metadata": {
            "source_type": "wallet_proposal",
            "proposal_type": "wallet_deletion",
            "proposal": proposal_data,
        },
    }


def build_wallet_creation_step(step: int, total_steps: int = 3, **kwargs) -> dict:
    """Build a wallet creation guided flow message.

    Steps:
        1: Explain what we're creating, ask for wallet name
        2: Confirm — generate keypair, ask for password
        3: Success — show public address, remind about backup
    """
    steps = {
        1: {
            "content": (
                "I'll guide you through creating your Solana wallet. "
                "This wallet will be stored encrypted on this device — only you control the keys. "
                "**Step 1 of 3**: What would you like to name your wallet? (e.g. 'My Trading Wallet')"
            ),
            "metadata": {
                "source_type": "wallet_flow",
                "wallet_step": 1,
                "total_steps": total_steps,
            },
        },
        2: {
            "content": (
                "**Step 2 of 3**: Choose a strong password to encrypt your private key. "
                "This password is never stored — you'll need it to unlock your wallet for trading. "
                "Please type your password in the next message."
            ),
            "metadata": {
                "source_type": "wallet_flow",
                "wallet_step": 2,
                "total_steps": total_steps,
                "wallet_name": kwargs.get("wallet_name", "My Wallet"),
            },
        },
        3: {
            "content": (
                f"**Wallet Created!** Your Solana wallet is ready.\n\n"
                f"**Address**: `{kwargs.get('public_address', 'N/A')}`\n\n"
                "Your private key is encrypted and stored safely. "
                "To start trading, send some SOL or USDC to this address. "
                "Say 'what's my balance' anytime to check your holdings."
            ),
            "metadata": {
                "source_type": "wallet_flow",
                "wallet_step": 3,
                "total_steps": total_steps,
                "public_address": kwargs.get("public_address"),
                "wallet_created": True,
            },
        },
    }
    return steps.get(step, steps[1])


def _get_known_mint(symbol: str) -> str:
    """Get the Solana mainnet mint address for known tokens."""
    KNOWN_MINTS = {
        "SOL": "So11111111111111111111111111111111111111112",
        "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
        "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
        "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    }
    return KNOWN_MINTS.get(symbol.upper(), "")
