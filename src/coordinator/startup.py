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
from .mcp_client import BraveMCPClient
from .mongodb_mcp_client import MongoDBMCPClient
from .cache import get_cache, MongoDBCache
from .persona_memory import _load_all_cards_cached, ensure_all_summaries_serialized
from .repositories.session_repository import SessionRepository
from .repositories.message_repository import MessageRepository
from .repositories.summary_repository import SummaryRepository
from .repositories.emotional_state_repository import EmotionalStateRepository
from .repositories.user_profile_repository import UserProfileRepository
from .memory_manager import MemoryManager, ConversationSummarizer
from .services.mongodb_handlers import MongoDBService
from .memory_rag import EpisodicMemoryRAG
from .fact_extractor import FactExtractor

logger = logging.getLogger(__name__)

# ----------------- Global State -----------------
_DB_PATH = os.environ.get("COORDINATOR_DB_PATH", "chats.db")

# MCP Clients
_brave_client: Optional[BraveMCPClient] = None
_mongodb_client: Optional[MongoDBMCPClient] = None
_mongodb_cache: Optional[MongoDBCache] = None
_mongodb_service: Optional[MongoDBService] = None

# Repositories
_session_repo: Optional[SessionRepository] = None
_message_repo: Optional[MessageRepository] = None
_summary_repo: Optional[SummaryRepository] = None
_emotional_state_repo: Optional[EmotionalStateRepository] = None
_user_profile_repo: Optional[UserProfileRepository] = None

# Memory Management (Phase 2)
_memory_manager: Optional[MemoryManager] = None
_conversation_summarizer: Optional[ConversationSummarizer] = None

# Phase 3: Advanced AI Memory
_episodic_memory_rag: Optional[EpisodicMemoryRAG] = None
_fact_extractor: Optional[FactExtractor] = None


# ----------------- Getters -----------------

def get_brave_client() -> Optional[BraveMCPClient]:
    """Get the global Brave MCP client instance."""
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

        _brave_client = BraveMCPClient(
            api_key=api_key,
            max_results=max_results,
            safesearch=safesearch,
            timeout=timeout
        )
        logger.info(f"Brave MCP client initialized (max_results={max_results}, timeout={timeout}s)")
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
    global _session_repo, _message_repo, _summary_repo, _emotional_state_repo, _user_profile_repo

    _session_repo = SessionRepository(_DB_PATH)
    _message_repo = MessageRepository(_DB_PATH)
    _summary_repo = SummaryRepository(_DB_PATH)
    _emotional_state_repo = EmotionalStateRepository(_DB_PATH)
    _user_profile_repo = UserProfileRepository(_DB_PATH)
    logger.info("Repositories initialized (Phase 1-3)")


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
        # Initialize RAG memory with embeddings
        _episodic_memory_rag = EpisodicMemoryRAG(embedding_model="nomic-embed-text:latest")
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
    """Initialize database tables and perform migrations."""
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # Create chat_sessions table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id TEXT PRIMARY KEY,
        persona_key TEXT NOT NULL,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")

    # Create messages table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        latency_ms INTEGER,
        FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
    )""")

    # Create conversation_summaries table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS conversation_summaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        message_range TEXT NOT NULL,
        summary_text TEXT NOT NULL,
        emotional_developments TEXT,
        topics_discussed TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
    )""")

    # Migration: If old tables exist, migrate data
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chats'")
    if cur.fetchone():
        print("Migrating old chat data to new schema...")
        cur.execute("""
        INSERT OR IGNORE INTO chat_sessions (id, persona_key, title, created_at, updated_at)
        SELECT printf('session_%06d', id), persona, title, created_at, updated_at FROM chats
        """)
        cur.execute("""
        INSERT OR IGNORE INTO messages (id, session_id, role, content, timestamp, latency_ms)
        SELECT printf('msg_%06d', id), printf('session_%06d', chat_id), role, content, ts, latency_ms FROM messages
        """)
        print("Migration completed.")

    # Create emotional_states table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS emotional_states (
        session_id TEXT PRIMARY KEY,
        trust_level REAL DEFAULT 0.5,
        rapport REAL DEFAULT 0.5,
        current_mood TEXT DEFAULT 'neutral',
        mood_intensity REAL DEFAULT 0.5,
        last_emotional_event TEXT,
        emotional_history TEXT DEFAULT '[]',
        updated_at TEXT,
        FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
    )""")

    # Create user_profiles table (Phase 3: Cross-session memory)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        profile_data TEXT NOT NULL
    )""")

    # Create user_sessions table (links users to their chat sessions)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_sessions (
        user_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE,
        FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
        PRIMARY KEY(user_id, session_id)
    )""")

    # Create indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_persona ON chat_sessions(persona_key)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON chat_sessions(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_summaries_session_id ON conversation_summaries(session_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_emotional_states_session ON emotional_states(session_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id)")

    conn.commit()
    conn.close()


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
            print(f"Cleaned up {deleted_count} orphaned sessions for removed personas: {orphaned_personas}")

    except Exception as e:
        print(f"Warning: Failed to cleanup orphaned sessions: {e}")


def initialize_all():
    """Run all initialization routines."""
    print("Initializing FastAPI server...")

    # Check Ollama
    try:
        assert_model_available(get_ollama_base(), get_persona_model())
        print("Model check passed.")
    except Exception as e:
        print(f"Model check failed: {e}")
        raise

    # Initialize database
    try:
        init_db()
        print("Database initialized.")
    except Exception as e:
        print(f"Database init failed: {e}")
        raise

    # Initialize repositories
    init_repositories()

    # Initialize memory manager
    init_memory_manager()

    # Initialize Phase 3 advanced memory (RAG + fact extraction)
    try:
        init_phase3_memory()
        if _episodic_memory_rag:
            print("Phase 3: RAG memory enabled (semantic search)")
        else:
            print("Phase 3: RAG memory disabled")
    except Exception as e:
        print(f"Phase 3 initialization warning: {e}")

    # Initialize Brave MCP
    try:
        init_brave_client()
        if _brave_client:
            enabled_rarities = get_brave_enabled_rarities()
            print(f"Brave MCP enabled for rarities: {', '.join(enabled_rarities)}")
        else:
            print("Brave MCP disabled (web search not available)")
    except Exception as e:
        print(f"Brave MCP initialization warning: {e}")

    # Initialize MongoDB MCP
    try:
        init_mongodb_client()
        if _mongodb_client:
            enabled_rarities = get_mongodb_enabled_rarities()
            print(f"MongoDB MCP enabled for rarities: {', '.join(enabled_rarities)}")
        else:
            print("MongoDB MCP disabled (no URI or feature flag off)")
    except Exception as e:
        print(f"MongoDB MCP initialization warning: {e}")

    # Refresh persona summaries
    try:
        result = ensure_all_summaries_serialized(timeout_sec=0.01, poll_sec=0.01)
        print(f"Summaries check completed: {result}")
    except Exception as e:
        print(f"Summary check failed: {e}")

    print("FastAPI server initialization complete.")
