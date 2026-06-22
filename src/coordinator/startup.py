# src/coordinator/startup.py
"""Application startup and initialization logic."""

from __future__ import annotations

import os
import logging
from typing import Optional

from .config import get_settings
from .ollama_utils import assert_model_available
from .mcp_client_stdio import BraveMCPClientStdio
from .persona_memory import _load_all_cards_cached, ensure_all_summaries_serialized
from .repositories.session_repository import SessionRepository
from .repositories.message_repository import MessageRepository
from .repositories.summary_repository import SummaryRepository
from .repositories.emotional_state_repository import EmotionalStateRepository
from .repositories.user_profile_repository import UserProfileRepository
from .repositories.seeker_progression_repository import SeekerProgressionRepository
from .repositories.user_repository import UserRepository
from .repositories.wallet_registry_repository import WalletRegistryRepository
from .repositories.wallet_summary_repository import WalletSummaryRepository
from .repositories.trade_history_repository import TradeHistoryRepository
from .memory_manager import MemoryManager, ConversationSummarizer
from .memory_rag import EpisodicMemoryRAG
from .fact_extractor import FactExtractor

logger = logging.getLogger(__name__)

# ----------------- Global State -----------------
_DB_PATH = os.environ.get("COORDINATOR_DB_PATH", "data/chats.db")
os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True) if os.path.dirname(_DB_PATH) else None

# MCP Clients
_brave_client: Optional[BraveMCPClientStdio] = None

# Jupiter MCP + Strategy Scheduler
_jupiter_client = None
_jupiter_ops = None
_wallet_execution_service = None
_strategy_service = None
_wallet_repo = None
_trade_proposal_repo = None
_strategy_scheduler = None

# Repositories
_session_repo: Optional[SessionRepository] = None
_message_repo: Optional[MessageRepository] = None
_summary_repo: Optional[SummaryRepository] = None
_emotional_state_repo: Optional[EmotionalStateRepository] = None
_user_profile_repo: Optional[UserProfileRepository] = None
_seeker_progression_repo: Optional[SeekerProgressionRepository] = None
_user_repo: Optional[UserRepository] = None

# Wallet Metadata Layer
_wallet_registry_repo: Optional[WalletRegistryRepository] = None
_wallet_summary_repo: Optional[WalletSummaryRepository] = None
_trade_history_repo: Optional[TradeHistoryRepository] = None

# Memory Management (Phase 2)
_memory_manager: Optional[MemoryManager] = None
_conversation_summarizer: Optional[ConversationSummarizer] = None

# Phase 3: Advanced AI Memory
_episodic_memory_rag: Optional[EpisodicMemoryRAG] = None
_fact_extractor: Optional[FactExtractor] = None


# ----------------- Getters -----------------

def get_brave_client() -> Optional[BraveMCPClientStdio]:
    """Get the global Brave MCP client instance (STDIO ephemeral containers)."""
    return _brave_client


def get_session_repo() -> SessionRepository:
    """Get the session repository."""
    if _session_repo is None:
        raise RuntimeError("SessionRepository not initialized — server startup incomplete")
    return _session_repo


def get_message_repo() -> MessageRepository:
    """Get the message repository."""
    if _message_repo is None:
        raise RuntimeError("MessageRepository not initialized — server startup incomplete")
    return _message_repo


def get_summary_repo() -> SummaryRepository:
    """Get the summary repository."""
    if _summary_repo is None:
        raise RuntimeError("SummaryRepository not initialized — server startup incomplete")
    return _summary_repo


def get_emotional_state_repo() -> EmotionalStateRepository:
    """Get the emotional state repository."""
    if _emotional_state_repo is None:
        raise RuntimeError("EmotionalStateRepository not initialized — server startup incomplete")
    return _emotional_state_repo


def get_memory_manager() -> MemoryManager:
    """Get the memory manager."""
    if _memory_manager is None:
        raise RuntimeError("MemoryManager not initialized — server startup incomplete")
    return _memory_manager


def get_conversation_summarizer() -> ConversationSummarizer:
    """Get the conversation summarizer."""
    if _conversation_summarizer is None:
        raise RuntimeError("ConversationSummarizer not initialized — server startup incomplete")
    return _conversation_summarizer


def get_user_profile_repo() -> UserProfileRepository:
    """Get the user profile repository."""
    if _user_profile_repo is None:
        raise RuntimeError("UserProfileRepository not initialized — server startup incomplete")
    return _user_profile_repo


def get_user_repo() -> UserRepository:
    """Get the OAuth user repository."""
    if _user_repo is None:
        raise RuntimeError("UserRepository not initialized — server startup incomplete")
    return _user_repo


def get_seeker_progression_repo() -> SeekerProgressionRepository:
    """Get the NEPHILIM seeker progression repository."""
    if _seeker_progression_repo is None:
        raise RuntimeError("SeekerProgressionRepository not initialized — server startup incomplete")
    return _seeker_progression_repo


def get_wallet_registry_repo() -> Optional[WalletRegistryRepository]:
    """Get the wallet registry repository."""
    return _wallet_registry_repo


def get_wallet_summary_repo() -> Optional[WalletSummaryRepository]:
    """Get the wallet summary repository."""
    return _wallet_summary_repo


def get_trade_history_repo() -> Optional[TradeHistoryRepository]:
    """Get the trade history repository."""
    return _trade_history_repo


def get_episodic_memory_rag() -> Optional[EpisodicMemoryRAG]:
    """Get the episodic memory RAG system."""
    return _episodic_memory_rag


def get_fact_extractor() -> Optional[FactExtractor]:
    """Get the fact extractor."""
    return _fact_extractor


# Jupiter MCP getters

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

def init_brave_client():
    """Initialize Brave MCP client if enabled."""
    global _brave_client

    brave_cfg = get_settings().brave
    if not brave_cfg.enabled:
        logger.info("Brave MCP is disabled (no API key)")
        return

    try:
        api_key = brave_cfg.api_key
        max_results = brave_cfg.max_results
        safesearch = brave_cfg.safesearch
        timeout = brave_cfg.timeout

        _brave_client = BraveMCPClientStdio(
            image=os.getenv("BRAVE_MCP_IMAGE", "docker.io/mcp/brave-search"),
            api_key=api_key,
            max_results=max_results,
            safesearch=safesearch,
            timeout=timeout
        )

        # Verify Docker daemon is reachable (Brave MCP requires Docker)
        if not _brave_client.health_check():
            logger.error(
                "Brave MCP client created but Docker is NOT running. "
                "Web search will fail until Docker Desktop is started."
            )
            _brave_client = None
        else:
            logger.info(f"Brave MCP STDIO client initialized (image={_brave_client.image}, max_results={max_results}, timeout={timeout}s)")
    except Exception as e:
        logger.error(f"Failed to initialize Brave MCP client: {e}")
        _brave_client = None


def init_repositories():
    """Initialize database repositories."""
    global _session_repo, _message_repo, _summary_repo, _emotional_state_repo
    global _user_profile_repo, _seeker_progression_repo, _user_repo
    global _wallet_registry_repo, _wallet_summary_repo, _trade_history_repo

    _session_repo = SessionRepository(_DB_PATH)
    _message_repo = MessageRepository(_DB_PATH)
    _summary_repo = SummaryRepository(_DB_PATH)
    _emotional_state_repo = EmotionalStateRepository(_DB_PATH)
    _user_profile_repo = UserProfileRepository(_DB_PATH)
    _seeker_progression_repo = SeekerProgressionRepository(_DB_PATH)
    _user_repo = UserRepository(_DB_PATH)
    _user_repo._ensure_tables()

    # Wallet Metadata Layer
    _wallet_registry_repo = WalletRegistryRepository(_DB_PATH)
    _wallet_summary_repo = WalletSummaryRepository(_DB_PATH)
    _trade_history_repo = TradeHistoryRepository(_DB_PATH)

    # Reset all wallet unlock states on startup (wallets are locked until user provides password)
    _wallet_summary_repo.reset_all_unlock_states()

    logger.info("Repositories initialized (Phase 1-3 + NEPHILIM Progression + OAuth + Wallet Metadata)")


def init_memory_manager():
    """Initialize memory management components."""
    global _memory_manager, _conversation_summarizer

    _memory_manager = MemoryManager(max_tokens=get_settings().ollama.context_window)
    _conversation_summarizer = ConversationSummarizer()
    logger.info("Memory manager initialized (Phase 2)")


def init_phase3_memory():
    """Initialize Phase 3 advanced memory systems (RAG + Fact Extraction)."""
    global _episodic_memory_rag, _fact_extractor

    try:
        # Initialize RAG memory with embeddings (uses config default)
        _episodic_memory_rag = EpisodicMemoryRAG()
        logger.info("Episodic Memory RAG initialized (Phase 3)")

        # Initialize fact extractor
        # Note: Will need LLM client, initialized later in chat flow
        # For now, mark as ready for lazy init
        _fact_extractor = None  # Will be initialized with LLM client on first use
        logger.info("Fact Extractor ready for initialization (Phase 3)")

    except Exception as e:
        logger.error(f"Failed to initialize Phase 3 memory systems: {e}")
        logger.warning("Phase 3 features (RAG, cross-session memory) will be disabled")
        _episodic_memory_rag = None
        _fact_extractor = None


def init_db():
    """Initialize database using Alembic migrations (if available), otherwise repositories auto-initialize schema."""
    try:
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{_DB_PATH}")

        # Run migrations to latest version
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied successfully")

    except ImportError:
        # Alembic not installed - repositories will auto-initialize schema when first used
        logger.info("Alembic not available, repositories will auto-initialize database schema")

    except Exception as e:
        # Alembic config or migration files not found (e.g., Docker without alembic dir)
        # Repositories with _ensure_tables() will self-initialize schema
        logger.warning(f"Alembic migration skipped ({e}), repositories will auto-initialize schema")

    # Users table creation is handled by UserRepository._ensure_tables() in init_repositories()


def init_jupiter():
    """Initialize Jupiter MCP client, execution service, and strategy service."""
    global _jupiter_client, _jupiter_ops, _wallet_execution_service, _strategy_service
    global _wallet_repo, _trade_proposal_repo

    from .config import get_settings
    jupiter_cfg = get_settings().jupiter

    if not jupiter_cfg.enabled:
        logger.info("Jupiter MCP is disabled (JUPITER_ENABLED=false)")
        return

    try:
        from .jupiter.jupiter_mcp_client import JupiterDockerClient
        from .jupiter.jupiter_operations import JupiterOperations
        from .services.wallet_execution_service import WalletExecutionService
        from .services.strategy_service import StrategyService
        from .repositories.wallet_repository import WalletRepository
        from .repositories.trade_proposal_repository import TradeProposalRepository

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
            trade_history_repo=_trade_history_repo,
            wallet_summary_repo=_wallet_summary_repo,
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
        from .jupiter.strategy_scheduler import init_scheduler
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


def cleanup_orphaned_sessions():
    """Remove chat sessions for personas that no longer exist."""
    if _session_repo is None:
        logger.debug("cleanup_orphaned_sessions skipped: repo not yet initialized")
        return
    try:
        cards = _load_all_cards_cached()
        current_persona_keys = {card.get("key") for card in cards if card.get("key")}

        all_sessions = _session_repo.get_all_sessions()

        orphaned_persona_keys = []
        for session in all_sessions:
            persona_key = session["persona_key"]
            if persona_key not in current_persona_keys:
                orphaned_persona_keys.append(persona_key)

        if orphaned_persona_keys:
            orphaned_personas = list(set(orphaned_persona_keys))
            deleted_count = _session_repo.delete_sessions_by_persona(orphaned_personas)
            logger.info(f"Cleaned up {deleted_count} orphaned sessions for removed personas: {orphaned_personas}")

    except Exception as e:
        logger.warning(f"Failed to cleanup orphaned sessions: {e}")


def initialize_all():
    """Run all initialization routines."""
    logger.info("Initializing FastAPI server...")

    # Check Ollama
    try:
        assert_model_available(get_settings().ollama.base, get_settings().ollama.model)
        logger.info("Model check passed.")
    except Exception as e:
        logger.error(f"Model check failed: {e}")
        raise

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized.")
    except Exception as e:
        logger.error(f"Database init failed: {e}")
        raise

    # Initialize repositories
    init_repositories()

    # Initialize memory manager
    init_memory_manager()

    # Initialize Phase 3 advanced memory (RAG + fact extraction)
    try:
        init_phase3_memory()
        if _episodic_memory_rag:
            logger.info("Phase 3: RAG memory enabled (semantic search)")
        else:
            logger.info("Phase 3: RAG memory disabled")
    except Exception as e:
        logger.warning(f"Phase 3 initialization warning: {e}")

    # Initialize Brave MCP
    try:
        init_brave_client()
        if _brave_client:
            logger.info("Brave MCP enabled (web search available)")
        else:
            logger.info("Brave MCP disabled (web search not available)")
    except Exception as e:
        logger.warning(f"Brave MCP initialization warning: {e}")

    # Initialize Jupiter MCP
    try:
        init_jupiter()
    except Exception as e:
        logger.warning(f"Jupiter MCP initialization warning: {e}")

    # Initialize Strategy Scheduler (must be after Jupiter)
    try:
        init_strategy_scheduler()
    except Exception as e:
        logger.warning(f"Strategy scheduler initialization warning: {e}")

    # Remove sessions for personas that no longer exist
    cleanup_orphaned_sessions()

    # Refresh persona summaries
    try:
        result = ensure_all_summaries_serialized(timeout_sec=0.01, poll_sec=0.01)
        logger.info(f"Summaries check completed: {result}")
    except Exception as e:
        logger.warning(f"Summary check failed: {e}")

    # R4: Pre-warm semantic router centroids in background (reuses the RAG embedding model already pulled)
    try:
        import threading as _threading
        def _prewarm_semantic():
            try:
                from .tools.semantic_router import warm_centroids
                ok = warm_centroids()
                logger.info(f"[SemanticRouter] Centroid pre-warm {'succeeded' if ok else 'skipped (no embedding model)'}")
            except Exception as exc:
                logger.debug(f"[SemanticRouter] Centroid pre-warm failed (non-fatal): {exc}")
        _threading.Thread(target=_prewarm_semantic, daemon=True, name="prewarm-semantic").start()
    except Exception as e:
        logger.debug(f"[SemanticRouter] Pre-warm thread start failed (non-fatal): {e}")

    # R6: Pre-warm system prompt LRU cache for all personas in a background thread.
    # Eliminates blocking CV-summary LLM call on the first user request per persona.
    try:
        import threading
        from .persona_memory import build_system_prompt as _build_sp

        def _prewarm_prompts():
            cards = _load_all_cards_cached()
            for card in cards:
                key = card.get("key")
                if not key:
                    continue
                try:
                    _build_sp(key)
                    logger.debug(f"[Prewarm] System prompt cached for '{key}'")
                except Exception as exc:
                    logger.debug(f"[Prewarm] Skipped '{key}': {exc}")
            logger.info(f"[Prewarm] System prompt cache warmed for {len(cards)} persona(s)")

        threading.Thread(target=_prewarm_prompts, daemon=True, name="prewarm-prompts").start()
        logger.info("[Prewarm] System prompt pre-warming started in background")
    except Exception as e:
        logger.warning(f"[Prewarm] Pre-warm thread failed to start: {e}")

    logger.info("FastAPI server initialization complete.")
