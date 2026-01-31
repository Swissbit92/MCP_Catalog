# src/coordinator/startup.py
"""Application startup and initialization logic."""

from __future__ import annotations

import os
import sqlite3
import logging
from typing import Optional

from .config import (
    get_ollama_base,
    get_persona_model,
    is_brave_enabled,
    get_brave_api_key,
    get_brave_max_results,
    get_brave_safesearch,
    get_brave_search_timeout,
    get_brave_enabled_rarities,
    is_mongodb_enabled,
    get_mongodb_uri,
    get_mongodb_timeout,
    get_mongodb_max_response_bytes,
    get_mongodb_enabled_rarities,
    get_model_context_window,
)
from .ollama_utils import assert_model_available
from .mcp_client_stdio import BraveMCPClientStdio
from .mongodb_mcp_client import MongoDBMCPClient
from .cache import get_cache, MongoDBCache
from .persona_memory import _load_all_cards_cached, ensure_all_summaries_serialized
from .repositories.session_repository import SessionRepository
from .repositories.message_repository import MessageRepository
from .repositories.summary_repository import SummaryRepository
from .repositories.emotional_state_repository import EmotionalStateRepository
from .repositories.user_profile_repository import UserProfileRepository
from .repositories.seeker_progression_repository import SeekerProgressionRepository
from .memory_manager import MemoryManager, ConversationSummarizer
from .services.mongodb_handlers import MongoDBService
from .memory_rag import EpisodicMemoryRAG
from .fact_extractor import FactExtractor

logger = logging.getLogger(__name__)

# ----------------- Global State -----------------
_DB_PATH = os.environ.get("COORDINATOR_DB_PATH", "chats.db")

# MCP Clients
_brave_client: Optional[BraveMCPClientStdio] = None
_mongodb_client: Optional[MongoDBMCPClient] = None
_mongodb_cache: Optional[MongoDBCache] = None
_mongodb_service: Optional[MongoDBService] = None

# Repositories
_session_repo: Optional[SessionRepository] = None
_message_repo: Optional[MessageRepository] = None
_summary_repo: Optional[SummaryRepository] = None
_emotional_state_repo: Optional[EmotionalStateRepository] = None
_user_profile_repo: Optional[UserProfileRepository] = None
_seeker_progression_repo: Optional[SeekerProgressionRepository] = None

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


def get_mongodb_client() -> Optional[MongoDBMCPClient]:
    """Get the global MongoDB MCP client instance."""
    return _mongodb_client


def get_mongodb_cache() -> Optional[MongoDBCache]:
    """Get the global MongoDB cache instance."""
    return _mongodb_cache


def get_mongodb_service() -> Optional[MongoDBService]:
    """Get the global MongoDB service instance."""
    return _mongodb_service


def get_session_repo() -> SessionRepository:
    """Get the session repository."""
    return _session_repo


def get_message_repo() -> MessageRepository:
    """Get the message repository."""
    return _message_repo


def get_summary_repo() -> SummaryRepository:
    """Get the summary repository."""
    return _summary_repo


def get_emotional_state_repo() -> EmotionalStateRepository:
    """Get the emotional state repository."""
    return _emotional_state_repo


def get_memory_manager() -> MemoryManager:
    """Get the memory manager."""
    return _memory_manager


def get_conversation_summarizer() -> ConversationSummarizer:
    """Get the conversation summarizer."""
    return _conversation_summarizer


def get_user_profile_repo() -> UserProfileRepository:
    """Get the user profile repository."""
    return _user_profile_repo


def get_seeker_progression_repo() -> SeekerProgressionRepository:
    """Get the NEPHILIM seeker progression repository."""
    return _seeker_progression_repo


def get_episodic_memory_rag() -> Optional[EpisodicMemoryRAG]:
    """Get the episodic memory RAG system."""
    return _episodic_memory_rag


def get_fact_extractor() -> Optional[FactExtractor]:
    """Get the fact extractor."""
    return _fact_extractor


# ----------------- Initialization Functions -----------------

def init_brave_client():
    """Initialize Brave MCP client if enabled."""
    global _brave_client

    if not is_brave_enabled():
        logger.info("Brave MCP is disabled (no API key)")
        return

    try:
        api_key = get_brave_api_key()
        max_results = get_brave_max_results()
        safesearch = get_brave_safesearch()
        timeout = get_brave_search_timeout()

        _brave_client = BraveMCPClientStdio(
            image=os.getenv("BRAVE_MCP_IMAGE", "docker.io/mcp/brave-search"),
            api_key=api_key,
            max_results=max_results,
            safesearch=safesearch,
            timeout=timeout
        )
        logger.info(f"Brave MCP STDIO client initialized (image={_brave_client.image}, max_results={max_results}, timeout={timeout}s)")
    except Exception as e:
        logger.error(f"Failed to initialize Brave MCP client: {e}")
        _brave_client = None


def init_mongodb_client():
    """Initialize MongoDB MCP client if enabled."""
    global _mongodb_client, _mongodb_cache, _mongodb_service

    if not is_mongodb_enabled():
        logger.info("MongoDB MCP is disabled (no URI or feature flag off)")
        return

    try:
        mongodb_uri = get_mongodb_uri()
        timeout = get_mongodb_timeout()
        max_response_bytes = get_mongodb_max_response_bytes()

        _mongodb_client = MongoDBMCPClient(
            connection_uri=mongodb_uri,
            timeout=timeout,
            max_response_bytes=max_response_bytes
        )

        # Initialize cache
        _mongodb_cache = get_cache()

        # Initialize service
        _mongodb_service = MongoDBService(_mongodb_client, _mongodb_cache)

        logger.info(f"MongoDB MCP client initialized (timeout={timeout}s, max_response={max_response_bytes} bytes)")
        logger.info("MongoDB cache initialized")
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB MCP client: {e}")
        _mongodb_client = None
        _mongodb_cache = None
        _mongodb_service = None


def init_repositories():
    """Initialize database repositories."""
    global _session_repo, _message_repo, _summary_repo, _emotional_state_repo, _user_profile_repo, _seeker_progression_repo

    _session_repo = SessionRepository(_DB_PATH)
    _message_repo = MessageRepository(_DB_PATH)
    _summary_repo = SummaryRepository(_DB_PATH)
    _emotional_state_repo = EmotionalStateRepository(_DB_PATH)
    _user_profile_repo = UserProfileRepository(_DB_PATH)
    _seeker_progression_repo = SeekerProgressionRepository(_DB_PATH)
    logger.info("Repositories initialized (Phase 1-3 + NEPHILIM Progression)")


def init_memory_manager():
    """Initialize memory management components."""
    global _memory_manager, _conversation_summarizer

    _memory_manager = MemoryManager(max_tokens=get_model_context_window())
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
        logger.error(f"Database migration failed: {e}")
        raise


def cleanup_orphaned_sessions():
    """Remove chat sessions for personas that no longer exist."""
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
        assert_model_available(get_ollama_base(), get_persona_model())
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
            enabled_rarities = get_brave_enabled_rarities()
            logger.info(f"Brave MCP enabled for rarities: {', '.join(enabled_rarities)}")
        else:
            logger.info("Brave MCP disabled (web search not available)")
    except Exception as e:
        logger.warning(f"Brave MCP initialization warning: {e}")

    # Initialize MongoDB MCP
    try:
        init_mongodb_client()
        if _mongodb_client:
            enabled_rarities = get_mongodb_enabled_rarities()
            logger.info(f"MongoDB MCP enabled for rarities: {', '.join(enabled_rarities)}")
        else:
            logger.info("MongoDB MCP disabled (no URI or feature flag off)")
    except Exception as e:
        logger.warning(f"MongoDB MCP initialization warning: {e}")

    # Refresh persona summaries
    try:
        result = ensure_all_summaries_serialized(timeout_sec=0.01, poll_sec=0.01)
        logger.info(f"Summaries check completed: {result}")
    except Exception as e:
        logger.warning(f"Summary check failed: {e}")

    logger.info("FastAPI server initialization complete.")
