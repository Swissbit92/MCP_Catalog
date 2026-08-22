# src/coordinator/di/jupiter.py
"""Jupiter cluster: MCP client/ops, wallet execution + strategy, scheduler.

Split out of ``startup.py`` (2026-08-22 decomposition, audit rec #7). Moved
verbatim — no behavior change; see ``startup.py`` for the re-export contract
that keeps ``startup.get_X`` / ``startup.init_X`` working unchanged.
"""

from __future__ import annotations

import logging

from .repositories import (
    _DB_PATH,
    get_trade_history_repo,
    get_wallet_registry_repo,
    get_wallet_summary_repo,
)

logger = logging.getLogger(__name__)

# ----------------- Global State -----------------

# Jupiter MCP + Strategy Scheduler
_jupiter_client = None
_jupiter_ops = None
_wallet_execution_service = None
_strategy_service = None
_wallet_repo = None
_trade_proposal_repo = None
_strategy_scheduler = None


# ----------------- Getters -----------------

def get_jupiter_client():
    """Get the global Jupiter MCP client instance."""
    return _jupiter_client


def get_jupiter_ops():
    """Get the global Jupiter operations instance."""
    return _jupiter_ops


def get_wallet_execution_service():
    """Get the wallet execution service."""
    return _wallet_execution_service


def get_strategy_service():
    """Get the strategy service."""
    return _strategy_service


def get_wallet_repo():
    """Get the wallet repository."""
    if _wallet_repo is None:
        raise RuntimeError("WalletRepository not initialized — server startup incomplete")
    return _wallet_repo


def get_trade_proposal_repo():
    """Get the trade proposal repository."""
    if _trade_proposal_repo is None:
        raise RuntimeError("TradeProposalRepository not initialized — server startup incomplete")
    return _trade_proposal_repo


def get_strategy_scheduler():
    """Get the global APScheduler instance."""
    return _strategy_scheduler


# ----------------- Initialization Functions -----------------

def init_jupiter():
    """Initialize Jupiter MCP client, execution service, and strategy service."""
    global _jupiter_client, _jupiter_ops, _wallet_execution_service, _strategy_service
    global _wallet_repo, _trade_proposal_repo

    from ..config import get_settings
    jupiter_cfg = get_settings().jupiter

    if not jupiter_cfg.enabled:
        logger.info("Jupiter MCP is disabled (JUPITER_ENABLED=false)")
        return

    try:
        from ..jupiter.jupiter_mcp_client import JupiterDockerClient
        from ..jupiter.jupiter_operations import JupiterOperations
        from ..repositories.trade_proposal_repository import TradeProposalRepository
        from ..repositories.wallet_repository import WalletRepository
        from ..services.strategy_service import StrategyService
        from ..services.wallet_execution_service import WalletExecutionService

        # Init repositories
        _wallet_repo = WalletRepository(_DB_PATH)
        _trade_proposal_repo = TradeProposalRepository(_DB_PATH)

        # Init Jupiter Docker client (deferred — starts on set_private_key())
        _jupiter_client = JupiterDockerClient(
            image=jupiter_cfg.mcp_image,
            solana_rpc_url=jupiter_cfg.solana_rpc_url,
            timeout=jupiter_cfg.timeout,
        )
        _jupiter_ops = JupiterOperations(_jupiter_client)

        # Init services
        _wallet_execution_service = WalletExecutionService(
            jupiter_ops=_jupiter_ops,
            trade_history_repo=get_trade_history_repo(),
            wallet_summary_repo=get_wallet_summary_repo(),
            wallet_registry_repo=get_wallet_registry_repo(),
        )
        _strategy_service = StrategyService(
            strategies_dir=jupiter_cfg.strategies_dir,
        )

        logger.info(f"Jupiter MCP initialized (image={jupiter_cfg.mcp_image}, rpc={jupiter_cfg.solana_rpc_url})")

    except Exception as e:
        logger.error(f"Jupiter MCP initialization failed: {e}")
        _jupiter_client = None
        _jupiter_ops = None


def init_strategy_scheduler():
    """Initialize the APScheduler for autonomous strategy execution."""
    global _strategy_scheduler

    if _jupiter_ops is None or _wallet_execution_service is None:
        logger.info("Strategy scheduler skipped — Jupiter not initialized")
        return

    try:
        from ..jupiter.strategy_scheduler import init_scheduler
        _strategy_scheduler = init_scheduler(
            jupiter_ops=_jupiter_ops,
            execution_service=_wallet_execution_service,
            strategy_service=_strategy_service,
        )
        if _strategy_scheduler:
            _strategy_scheduler.start()
            logger.info("Strategy scheduler started")
    except Exception as e:
        logger.error(f"Strategy scheduler initialization failed: {e}")
        _strategy_scheduler = None
