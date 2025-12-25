# Phase 1 Implementation Plan: Docker-First Migration

**Duration**: 2-3 weeks
**Goal**: Containerize application and fix database persistence
**Status**: Planning

---

## Overview

Phase 1 transforms the MCP Coordinator from a local development setup to a containerized, production-ready application with persistent database storage. This phase focuses on **infrastructure foundations** without requiring architectural changes.

**What Changes**:
- ✅ SQLite → PostgreSQL migration
- ✅ Hardcoded localhost → Environment variables
- ✅ Manual startup → Docker Compose orchestration
- ✅ Basic health check → Comprehensive liveness/readiness probes
- ✅ File-based summaries → Database storage

**What Stays the Same**:
- ✅ Application code (minimal changes)
- ✅ API contracts
- ✅ Frontend React app
- ✅ Persona system
- ✅ MCP integrations (refactored in Phase 2)

---

## Prerequisites

Before starting Phase 1, ensure you have:

- [ ] Docker Desktop installed (v24.0+)
- [ ] Docker Compose v2.0+
- [ ] PostgreSQL client tools (`psql`, `pg_dump`)
- [ ] Python 3.11+ with `pip`
- [ ] Node.js 20+ with `npm`
- [ ] Git for version control
- [ ] 20GB free disk space (for Docker images + volumes)

**Optional but Recommended**:
- [ ] DBeaver or pgAdmin (PostgreSQL GUI)
- [ ] Portainer (Docker GUI)
- [ ] Backup of current `chats.db` file

---

## Week 1: Database Migration

### Day 1-2: PostgreSQL Setup & Schema Design

#### Task 1.1: Install Dependencies
```bash
# Add to requirements.txt
sqlalchemy==2.0.25
asyncpg==0.29.0
alembic==1.13.1
psycopg2-binary==2.9.9  # For migration script
```

**Action Items**:
- [ ] Update `requirements.txt`
- [ ] Run `pip install -r requirements.txt`
- [ ] Verify installation: `python -c "import sqlalchemy; print(sqlalchemy.__version__)"`

---

#### Task 1.2: Create SQLAlchemy Models

**File**: `src/coordinator/models/database_models.py` (NEW)

```python
"""SQLAlchemy ORM models for PostgreSQL database."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, Float, ForeignKey, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class ChatSession(Base):
    """Chat session model."""
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    persona_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)

    # Relationships
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan"
    )
    summaries: Mapped[list["ConversationSummary"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan"
    )
    emotional_state: Mapped[Optional["EmotionalState"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False
    )
    user_sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan"
    )


class Message(Base):
    """Chat message model."""
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), default="llm", nullable=False)

    # Relationships
    session: Mapped["ChatSession"] = relationship(back_populates="messages")


class ConversationSummary(Base):
    """Conversation summary model."""
    __tablename__ = "conversation_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    message_range: Mapped[str] = mapped_column(String(100), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    emotional_developments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    topics_discussed: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    # Relationships
    session: Mapped["ChatSession"] = relationship(back_populates="summaries")


class EmotionalState(Base):
    """Emotional state tracking model (Phase 2.2)."""
    __tablename__ = "emotional_states"

    session_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        primary_key=True
    )
    trust_level: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    rapport: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    current_mood: Mapped[str] = mapped_column(String(100), default="neutral", nullable=False)
    mood_intensity: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    last_emotional_event: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emotional_history: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relationships
    session: Mapped["ChatSession"] = relationship(back_populates="emotional_state")


class UserProfile(Base):
    """User profile model (Phase 3: Cross-session memory)."""
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)
    profile_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON

    # Relationships
    user_sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user_profile",
        cascade="all, delete-orphan"
    )


class UserSession(Base):
    """Links users to their chat sessions."""
    __tablename__ = "user_sessions"

    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("user_profiles.user_id", ondelete="CASCADE"),
        primary_key=True
    )
    session_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    # Relationships
    user_profile: Mapped["UserProfile"] = relationship(back_populates="user_sessions")
    session: Mapped["ChatSession"] = relationship(back_populates="user_sessions")

    # Indexes
    __table_args__ = (
        Index("idx_user_sessions_user_id", "user_id"),
        Index("idx_user_sessions_session_id", "session_id"),
    )
```

**Action Items**:
- [ ] Create file `src/coordinator/models/database_models.py`
- [ ] Copy SQLAlchemy models above
- [ ] Verify imports: `python -c "from src.coordinator.models.database_models import Base"`

---

#### Task 1.3: Create Database Engine & Session Factory

**File**: `src/coordinator/database.py` (NEW)

```python
"""Database connection and session management."""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.pool import NullPool

from .config import settings
from .models.database_models import Base

logger = logging.getLogger(__name__)

# Global engine instance
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the async database engine."""
    global _engine
    if _engine is None:
        logger.info(f"Creating database engine: {settings.database_url.split('@')[-1]}")  # Log without password

        # Check if using PostgreSQL or SQLite
        if settings.is_postgres:
            _engine = create_async_engine(
                settings.database_url,
                echo=False,
                pool_size=20,              # Max connections in pool
                max_overflow=10,           # Extra connections beyond pool_size
                pool_pre_ping=True,        # Verify connections before using
                pool_recycle=3600,         # Recycle connections after 1 hour
                connect_args={
                    "server_settings": {"application_name": "mcp_coordinator"}
                }
            )
        else:
            # SQLite (for backward compatibility during migration)
            _engine = create_async_engine(
                settings.database_url,
                echo=False,
                poolclass=NullPool,  # SQLite doesn't support connection pooling
                connect_args={"check_same_thread": False}
            )

        logger.info("Database engine created successfully")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )
        logger.info("Session factory created successfully")
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI routes to get database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database():
    """Initialize database tables (create all tables)."""
    engine = get_engine()
    async with engine.begin() as conn:
        logger.info("Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def close_database():
    """Close database connections."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database connections closed")
```

**Action Items**:
- [ ] Create file `src/coordinator/database.py`
- [ ] Copy code above
- [ ] Test import: `python -c "from src.coordinator.database import get_engine"`

---

#### Task 1.4: Update Configuration for DATABASE_URL

**File**: `src/coordinator/config.py` (UPDATE)

Add to `CoordinatorSettings` class:

```python
# Add this field to CoordinatorSettings class
database_url: str = Field(
    default="sqlite+aiosqlite:///./chats.db",
    description="Database connection URL (SQLAlchemy async format)",
    alias="DATABASE_URL"
)

@property
def is_postgres(self) -> bool:
    """Check if using PostgreSQL."""
    return self.database_url.startswith("postgresql")

@property
def is_sqlite(self) -> bool:
    """Check if using SQLite."""
    return self.database_url.startswith("sqlite")
```

Add getter function at bottom of file:

```python
def get_database_url() -> str:
    """Get database connection URL."""
    return settings.database_url
```

**Action Items**:
- [ ] Open `src/coordinator/config.py`
- [ ] Add `database_url` field to `CoordinatorSettings`
- [ ] Add `is_postgres` and `is_sqlite` properties
- [ ] Add `get_database_url()` function
- [ ] Test: `python -c "from src.coordinator.config import settings; print(settings.database_url)"`

---

#### Task 1.5: Create Migration Script

**File**: `scripts/migrate_sqlite_to_postgres.py` (NEW)

```python
"""Migrate data from SQLite to PostgreSQL.

Usage:
    python scripts/migrate_sqlite_to_postgres.py

Environment variables:
    SQLITE_PATH: Path to SQLite database (default: chats.db)
    DATABASE_URL: PostgreSQL connection URL
"""

import os
import sys
import sqlite3
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.coordinator.models.database_models import (
    Base, ChatSession, Message, ConversationSummary, EmotionalState, UserProfile, UserSession
)


async def migrate():
    """Migrate data from SQLite to PostgreSQL."""
    # Get paths from environment
    sqlite_path = os.getenv("SQLITE_PATH", "chats.db")
    postgres_url = os.getenv("DATABASE_URL")

    if not postgres_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    if not os.path.exists(sqlite_path):
        print(f"ERROR: SQLite database not found: {sqlite_path}")
        sys.exit(1)

    print(f"Starting migration from {sqlite_path} to PostgreSQL...")

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    # Connect to PostgreSQL
    pg_engine = create_async_engine(postgres_url, echo=False)

    # Create tables
    async with pg_engine.begin() as conn:
        print("Creating PostgreSQL tables...")
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session = sessionmaker(pg_engine, class_=AsyncSession, expire_on_commit=False)

    # Migrate chat_sessions
    print("Migrating chat_sessions...")
    sqlite_cur.execute("SELECT * FROM chat_sessions")
    sessions = sqlite_cur.fetchall()

    async with async_session() as session:
        for row in sessions:
            chat_session = ChatSession(
                id=row["id"],
                persona_key=row["persona_key"],
                title=row["title"],
                created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
            )
            session.add(chat_session)
        await session.commit()
    print(f"Migrated {len(sessions)} chat sessions")

    # Migrate messages
    print("Migrating messages...")
    sqlite_cur.execute("SELECT * FROM messages")
    messages = sqlite_cur.fetchall()

    async with async_session() as session:
        for row in messages:
            message = Message(
                id=row["id"],
                session_id=row["session_id"],
                role=row["role"],
                content=row["content"],
                timestamp=datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")),
                latency_ms=row.get("latency_ms"),
                source_type=row.get("source_type", "llm")
            )
            session.add(message)
        await session.commit()
    print(f"Migrated {len(messages)} messages")

    # Migrate conversation_summaries
    print("Migrating conversation_summaries...")
    sqlite_cur.execute("SELECT * FROM conversation_summaries")
    summaries = sqlite_cur.fetchall()

    async with async_session() as session:
        for row in summaries:
            summary = ConversationSummary(
                id=row["id"],
                session_id=row["session_id"],
                message_range=row["message_range"],
                summary_text=row["summary_text"],
                emotional_developments=row.get("emotional_developments"),
                topics_discussed=row.get("topics_discussed"),
                created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            )
            session.add(summary)
        await session.commit()
    print(f"Migrated {len(summaries)} conversation summaries")

    # Migrate emotional_states
    print("Migrating emotional_states...")
    sqlite_cur.execute("SELECT * FROM emotional_states")
    states = sqlite_cur.fetchall()

    async with async_session() as session:
        for row in states:
            state = EmotionalState(
                session_id=row["session_id"],
                trust_level=row.get("trust_level", 0.5),
                rapport=row.get("rapport", 0.5),
                current_mood=row.get("current_mood", "neutral"),
                mood_intensity=row.get("mood_intensity", 0.5),
                last_emotional_event=row.get("last_emotional_event"),
                emotional_history=row.get("emotional_history", "[]"),
                updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")) if row.get("updated_at") else None
            )
            session.add(state)
        await session.commit()
    print(f"Migrated {len(states)} emotional states")

    # Migrate user_profiles (if table exists)
    try:
        print("Migrating user_profiles...")
        sqlite_cur.execute("SELECT * FROM user_profiles")
        profiles = sqlite_cur.fetchall()

        async with async_session() as session:
            for row in profiles:
                profile = UserProfile(
                    user_id=row["user_id"],
                    created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")),
                    profile_data=row["profile_data"]
                )
                session.add(profile)
            await session.commit()
        print(f"Migrated {len(profiles)} user profiles")
    except sqlite3.OperationalError:
        print("user_profiles table not found (Phase 3 not implemented yet), skipping...")

    # Migrate user_sessions (if table exists)
    try:
        print("Migrating user_sessions...")
        sqlite_cur.execute("SELECT * FROM user_sessions")
        user_sessions = sqlite_cur.fetchall()

        async with async_session() as session:
            for row in user_sessions:
                user_session = UserSession(
                    user_id=row["user_id"],
                    session_id=row["session_id"],
                    created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                )
                session.add(user_session)
            await session.commit()
        print(f"Migrated {len(user_sessions)} user-session links")
    except sqlite3.OperationalError:
        print("user_sessions table not found (Phase 3 not implemented yet), skipping...")

    # Close connections
    sqlite_conn.close()
    await pg_engine.dispose()

    print("\n✅ Migration completed successfully!")
    print(f"Total sessions: {len(sessions)}")
    print(f"Total messages: {len(messages)}")
    print(f"Total summaries: {len(summaries)}")
    print(f"Total emotional states: {len(states)}")


if __name__ == "__main__":
    asyncio.run(migrate())
```

**Action Items**:
- [ ] Create directory `scripts/`
- [ ] Create file `scripts/migrate_sqlite_to_postgres.py`
- [ ] Copy migration script above
- [ ] Make executable: `chmod +x scripts/migrate_sqlite_to_postgres.py` (Linux/Mac)

---

### Day 3-4: Repository Refactoring

#### Task 1.6: Update Repositories to Use SQLAlchemy

**Strategy**: Create new async repository methods alongside existing sync methods for backward compatibility.

**File**: `src/coordinator/repositories/session_repository.py` (UPDATE)

```python
"""Session repository with SQLAlchemy async support."""

from __future__ import annotations

import logging
from typing import Optional
from datetime import datetime

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.database_models import ChatSession
from ..database import get_session_factory

logger = logging.getLogger(__name__)


class SessionRepository:
    """Repository for chat session operations."""

    def __init__(self, db_path: str = None):
        """Initialize repository.

        Args:
            db_path: Legacy parameter for backward compatibility (ignored)
        """
        self.session_factory = get_session_factory()

    async def get_all_sessions(self) -> list[dict]:
        """Get all chat sessions, ordered by creation date (newest first)."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(ChatSession).order_by(ChatSession.created_at.desc())
            )
            sessions = result.scalars().all()

            return [
                {
                    "id": s.id,
                    "persona_key": s.persona_key,
                    "title": s.title,
                    "created_at": s.created_at.isoformat() + "Z",
                    "updated_at": s.updated_at.isoformat() + "Z"
                }
                for s in sessions
            ]

    async def get_session_by_id(self, session_id: str) -> Optional[dict]:
        """Get a session by ID."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            chat_session = result.scalar_one_or_none()

            if not chat_session:
                return None

            return {
                "id": chat_session.id,
                "persona_key": chat_session.persona_key,
                "title": chat_session.title,
                "created_at": chat_session.created_at.isoformat() + "Z",
                "updated_at": chat_session.updated_at.isoformat() + "Z"
            }

    async def create_session(self, session_id: str, persona_key: str, title: str) -> dict:
        """Create a new chat session."""
        now = datetime.utcnow()

        async with self.session_factory() as session:
            chat_session = ChatSession(
                id=session_id,
                persona_key=persona_key,
                title=title,
                created_at=now,
                updated_at=now
            )
            session.add(chat_session)
            await session.commit()
            await session.refresh(chat_session)

            return {
                "id": chat_session.id,
                "persona_key": chat_session.persona_key,
                "title": chat_session.title,
                "created_at": chat_session.created_at.isoformat() + "Z",
                "updated_at": chat_session.updated_at.isoformat() + "Z"
            }

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session (cascade deletes messages, summaries, emotional state)."""
        async with self.session_factory() as session:
            result = await session.execute(
                delete(ChatSession).where(ChatSession.id == session_id)
            )
            await session.commit()
            return result.rowcount > 0

    async def get_persona_key(self, session_id: str) -> Optional[str]:
        """Get the persona key for a session."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(ChatSession.persona_key).where(ChatSession.id == session_id)
            )
            return result.scalar_one_or_none()

    async def update_session_timestamp(self, session_id: str):
        """Update the updated_at timestamp for a session."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            chat_session = result.scalar_one_or_none()

            if chat_session:
                chat_session.updated_at = datetime.utcnow()
                await session.commit()

    async def delete_sessions_by_persona(self, persona_keys: list[str]) -> int:
        """Delete all sessions for given persona keys."""
        async with self.session_factory() as session:
            result = await session.execute(
                delete(ChatSession).where(ChatSession.persona_key.in_(persona_keys))
            )
            await session.commit()
            return result.rowcount
```

**CRITICAL**: Update all repository methods to be `async`. Repeat similar refactoring for:
- `message_repository.py`
- `summary_repository.py`
- `emotional_state_repository.py`
- `user_profile_repository.py` (if exists)

**Action Items**:
- [ ] Update `session_repository.py` with async methods
- [ ] Update `message_repository.py` with async methods
- [ ] Update `summary_repository.py` with async methods
- [ ] Update `emotional_state_repository.py` with async methods
- [ ] Test each repository: `python -c "import asyncio; from src.coordinator.repositories.session_repository import SessionRepository; asyncio.run(SessionRepository().get_all_sessions())"`

---

### Day 5: Testing & Validation

#### Task 1.7: Update FastAPI Routes to Async

**File**: `src/coordinator/routes/sessions.py` (UPDATE)

Convert all route handlers to async:

```python
@router.get("/sessions")
async def get_sessions():  # ← Add async
    """Get all chat sessions."""
    session_repo = get_session_repo()
    sessions = await session_repo.get_all_sessions()  # ← Add await
    return {"sessions": sessions}

@router.post("/sessions")
async def create_session(body: CreateSessionBody):  # ← Add async
    """Create a new chat session."""
    session_repo = get_session_repo()
    session = await session_repo.create_session(  # ← Add await
        session_id=body.session_id,
        persona_key=body.persona,
        title=body.title
    )
    return session

# ... etc for all routes
```

**CRITICAL**: Update ALL route handlers in:
- `routes/sessions.py`
- `routes/chat.py`
- `routes/personas.py`

**Action Items**:
- [ ] Add `async` to all route handlers
- [ ] Add `await` to all repository calls
- [ ] Add `await` to all database operations
- [ ] Test each endpoint manually or with Postman

---

#### Task 1.8: Update Startup Initialization

**File**: `src/coordinator/startup.py` (UPDATE)

```python
# Update init_repositories() to be async
async def init_repositories():
    """Initialize database repositories."""
    global _session_repo, _message_repo, _summary_repo, _emotional_state_repo, _user_profile_repo

    # Initialize database tables
    from .database import init_database
    await init_database()

    _session_repo = SessionRepository()
    _message_repo = MessageRepository()
    _summary_repo = SummaryRepository()
    _emotional_state_repo = EmotionalStateRepository()
    _user_profile_repo = UserProfileRepository()
    logger.info("Repositories initialized (PostgreSQL async)")

# Update initialize_all() to be async
async def initialize_all():
    """Run all initialization routines."""
    logger.info("Initializing FastAPI server...")

    # Check Ollama
    try:
        assert_model_available(get_ollama_base(), get_persona_model())
        logger.info("Model check passed.")
    except Exception as e:
        logger.error(f"Model check failed: {e}")
        raise

    # Initialize repositories (creates tables)
    await init_repositories()

    # ... rest of initialization ...
```

**Update server.py to call async initialization**:

```python
# src/coordinator/server.py
import asyncio

# At bottom of file (after app definition)
@app.on_event("startup")
async def startup_event():
    """Run initialization on app startup."""
    from .startup import initialize_all
    await initialize_all()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on app shutdown."""
    from .database import close_database
    await close_database()
```

**Action Items**:
- [ ] Make `init_repositories()` async
- [ ] Make `initialize_all()` async
- [ ] Add startup/shutdown event handlers to `server.py`
- [ ] Remove synchronous `initialize_all()` call from module level

---

#### Task 1.9: Test Migration Locally

**Setup Test PostgreSQL**:
```bash
# Using Docker
docker run --name test-postgres -e POSTGRES_PASSWORD=testpass -e POSTGRES_DB=mcp_test -p 5432:5432 -d postgres:16-alpine

# Wait for startup
sleep 5

# Set environment
export DATABASE_URL="postgresql+asyncpg://postgres:testpass@localhost:5432/mcp_test"
export SQLITE_PATH="chats.db"

# Run migration
python scripts/migrate_sqlite_to_postgres.py
```

**Validation Queries**:
```bash
# Check record counts
psql postgresql://postgres:testpass@localhost:5432/mcp_test -c "SELECT COUNT(*) FROM chat_sessions;"
psql postgresql://postgres:testpass@localhost:5432/mcp_test -c "SELECT COUNT(*) FROM messages;"

# Compare with SQLite
sqlite3 chats.db "SELECT COUNT(*) FROM chat_sessions;"
sqlite3 chats.db "SELECT COUNT(*) FROM messages;"
```

**Action Items**:
- [ ] Start test PostgreSQL container
- [ ] Backup production SQLite: `cp chats.db chats.db.backup`
- [ ] Run migration script
- [ ] Verify record counts match
- [ ] Test application with PostgreSQL
- [ ] Check all features work (create session, send message, view history)

---

## Week 2: Docker Containerization

### Day 1-2: Create Dockerfiles

#### Task 2.1: Backend Dockerfile

**File**: `Dockerfile` (NEW - in project root)

```dockerfile
# Multi-stage build for smaller image size
FROM python:3.11-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY personas/ ./personas/

# Create non-root user for security
RUN useradd -m -u 1000 coordinator && \
    chown -R coordinator:coordinator /app
USER coordinator

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Start server
CMD ["uvicorn", "src.coordinator.server:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
```

**Build & Test**:
```bash
# Build image
docker build -t mcp-backend:test .

# Run container
docker run -p 8000:8000 -e DATABASE_URL="postgresql+asyncpg://..." mcp-backend:test

# Test health
curl http://localhost:8000/health
```

**Action Items**:
- [ ] Create `Dockerfile` in project root
- [ ] Build Docker image
- [ ] Test image runs successfully
- [ ] Verify health check works
- [ ] Check logs: `docker logs <container_id>`

---

#### Task 2.2: Frontend Dockerfile

**File**: `react-ui/Dockerfile` (NEW)

```dockerfile
# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy source and build
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=build /app/build /usr/share/nginx/html

# Custom nginx config for React Router
RUN echo 'server {\n\
    listen 80;\n\
    server_name localhost;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
    \n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
    \n\
    location /api {\n\
        proxy_pass http://backend:8000;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
    }\n\
    \n\
    gzip on;\n\
    gzip_types text/css application/json application/javascript;\n\
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**Build & Test**:
```bash
cd react-ui

# Build image
docker build -t mcp-frontend:test .

# Run container
docker run -p 3000:80 mcp-frontend:test

# Test
curl http://localhost:3000
```

**Action Items**:
- [ ] Create `react-ui/Dockerfile`
- [ ] Build Docker image
- [ ] Test image serves static files
- [ ] Verify React Router works (try navigating to `/chat`)
- [ ] Check gzip compression: `curl -H "Accept-Encoding: gzip" -I http://localhost:3000`

---

### Day 3-5: Docker Compose Setup

#### Task 2.3: Create Docker Compose Configuration

**File**: `docker-compose.yml` (NEW - see PRODUCTION_READINESS_PLAN.md for full content)

**Key Services**:
1. PostgreSQL (database)
2. Redis (cache)
3. Ollama (LLM)
4. Backend (FastAPI)
5. Frontend (React/Nginx)
6. Qdrant (optional - for Phase 3 RAG)

**Action Items**:
- [ ] Create `docker-compose.yml`
- [ ] Copy configuration from PRODUCTION_READINESS_PLAN.md Phase 1.3
- [ ] Create `.env.docker` file
- [ ] Test: `docker-compose config` (validates YAML)

---

#### Task 2.4: Environment Configuration

**File**: `.env.docker` (NEW)

```bash
# Database
DB_PASSWORD=your_secure_password_here_change_this

# Ollama
PERSONA_MODEL=llama3.1:latest
PERSONA_TEMPERATURE=0.1

# Brave Search (optional)
BRAVE_API_KEY=

# MongoDB (optional)
MONGODB_URI=
MONGODB_ENABLED=false

# Memory
MEMORY_EMBEDDING_MODEL=nomic-embed-text:latest
```

**Action Items**:
- [ ] Create `.env.docker`
- [ ] Generate secure password: `openssl rand -base64 32`
- [ ] Update `DB_PASSWORD` in `.env.docker`
- [ ] Add `.env.docker` to `.gitignore`

---

#### Task 2.5: Launch Full Stack

```bash
# Pull Ollama model before starting
docker pull ollama/ollama:latest
docker run -d -v ollama_models:/root/.ollama -p 11434:11434 --name ollama ollama/ollama:latest
docker exec -it ollama ollama pull llama3.1:latest

# Start all services
docker-compose --env-file .env.docker up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Test health
curl http://localhost:8000/health
curl http://localhost:3000
```

**Action Items**:
- [ ] Start Docker Compose stack
- [ ] Wait for all services to be healthy: `docker-compose ps`
- [ ] Test backend health check
- [ ] Test frontend loads
- [ ] Create test chat session
- [ ] Send test message
- [ ] Verify data persists after restart: `docker-compose restart backend`

---

## Week 3: Configuration & Polish

### Day 1-2: Configuration Updates

#### Task 3.1: CORS Origins Environment Variable

**Already covered in PRODUCTION_READINESS_PLAN.md Phase 1.4**

**Action Items**:
- [ ] Add `cors_origins` field to `config.py`
- [ ] Update `server.py` CORS middleware
- [ ] Test with production domain
- [ ] Verify `localhost` still works for development

---

#### Task 3.2: Health Check Improvements

**Create new health router** (see PRODUCTION_READINESS_PLAN.md Phase 1.5)

**Endpoints**:
- `GET /health` - Basic liveness probe
- `GET /health/ready` - Readiness probe (checks DB, Ollama, MCP clients)
- `GET /health/startup` - Startup probe (checks initialization)

**Action Items**:
- [ ] Create `src/coordinator/routes/health.py`
- [ ] Implement all three health endpoints
- [ ] Register health router in `server.py`
- [ ] Test each endpoint
- [ ] Update Dockerfile `HEALTHCHECK` to use `/health/ready`

---

### Day 3-4: Documentation

#### Task 3.3: Update README

**Add Docker instructions** to `README.md`:

```markdown
## Docker Deployment (Recommended)

### Quick Start with Docker Compose

```bash
# 1. Copy environment file
cp .env.example .env.docker

# 2. Update .env.docker with your settings
# - Set DB_PASSWORD to a secure password
# - Add BRAVE_API_KEY (optional)
# - Configure other settings

# 3. Start all services
docker-compose --env-file .env.docker up -d

# 4. Pull Ollama model
docker exec ollama ollama pull llama3.1:latest

# 5. Access the application
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | React UI |
| Backend | 8000 | FastAPI server |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache |
| Ollama | 11434 | LLM inference |

### Useful Commands

```bash
# View logs
docker-compose logs -f backend

# Restart a service
docker-compose restart backend

# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v

# Update to latest images
docker-compose pull
docker-compose up -d
```
```

**Action Items**:
- [ ] Update `README.md` with Docker instructions
- [ ] Add troubleshooting section
- [ ] Document environment variables
- [ ] Add architecture diagram (optional)

---

#### Task 3.4: Create Migration Guide

**File**: `docs/MIGRATION_GUIDE.md` (NEW)

```markdown
# Migration Guide: SQLite to PostgreSQL

This guide walks through migrating your existing MCP Coordinator data from SQLite to PostgreSQL.

## Prerequisites

- [ ] Docker installed
- [ ] Backup of `chats.db` file
- [ ] Python 3.11+ (for migration script)

## Step 1: Backup Current Data

```bash
# Backup SQLite database
cp chats.db chats.db.backup.$(date +%Y%m%d)

# Verify backup
sqlite3 chats.db.backup.* "SELECT COUNT(*) FROM chat_sessions;"
```

## Step 2: Start PostgreSQL

```bash
# Start only PostgreSQL service
docker-compose --env-file .env.docker up -d postgres

# Wait for PostgreSQL to be ready
docker-compose logs -f postgres
# Look for: "database system is ready to accept connections"
```

## Step 3: Run Migration

```bash
# Set environment variables
export DATABASE_URL="postgresql+asyncpg://coordinator:your_password@localhost:5432/mcp_coordinator"
export SQLITE_PATH="chats.db"

# Install dependencies
pip install -r requirements.txt

# Run migration script
python scripts/migrate_sqlite_to_postgres.py
```

## Step 4: Verify Migration

```bash
# Count records in PostgreSQL
docker exec -it mcp_postgres psql -U coordinator -d mcp_coordinator -c "SELECT COUNT(*) FROM chat_sessions;"
docker exec -it mcp_postgres psql -U coordinator -d mcp_coordinator -c "SELECT COUNT(*) FROM messages;"

# Compare with SQLite
sqlite3 chats.db "SELECT COUNT(*) FROM chat_sessions;"
sqlite3 chats.db "SELECT COUNT(*) FROM messages;"
```

## Step 5: Update Configuration

```bash
# Update .env.docker
DATABASE_URL=postgresql+asyncpg://coordinator:your_password@postgres:5432/mcp_coordinator
```

## Step 6: Start Full Stack

```bash
# Start all services
docker-compose --env-file .env.docker up -d

# Check logs
docker-compose logs -f backend

# Test application
curl http://localhost:8000/health
```

## Rollback Plan

If migration fails:

```bash
# Stop all services
docker-compose down

# Restore SQLite backup
cp chats.db.backup.YYYYMMDD chats.db

# Use SQLite configuration
export DATABASE_URL="sqlite+aiosqlite:///./chats.db"

# Restart application
python run_react.py
```

## Troubleshooting

### Migration script fails with connection error

**Symptom**: `asyncpg.exceptions.InvalidCatalogNameError: database "mcp_coordinator" does not exist`

**Solution**:
```bash
# Create database manually
docker exec -it mcp_postgres psql -U coordinator -c "CREATE DATABASE mcp_coordinator;"
```

### Record count mismatch

**Symptom**: PostgreSQL has fewer records than SQLite

**Solution**:
```bash
# Check migration logs for errors
python scripts/migrate_sqlite_to_postgres.py 2>&1 | tee migration.log

# Look for "ERROR" or "FAILED" messages
```

### Application won't start after migration

**Symptom**: Backend returns 500 errors

**Solution**:
```bash
# Check database connection
docker-compose logs backend | grep -i "database"

# Verify DATABASE_URL format
echo $DATABASE_URL
# Should be: postgresql+asyncpg://user:pass@host:port/database
```
```

**Action Items**:
- [ ] Create `docs/` directory
- [ ] Create `docs/MIGRATION_GUIDE.md`
- [ ] Test migration guide with fresh database
- [ ] Document common errors

---

### Day 5: Testing & Validation

#### Task 3.5: End-to-End Testing

**Test Checklist**:

**Basic Functionality**:
- [ ] Start Docker Compose stack
- [ ] All services healthy: `docker-compose ps`
- [ ] Frontend loads at http://localhost:3000
- [ ] Backend health check passes
- [ ] Can create new chat session
- [ ] Can send message to persona
- [ ] Can view chat history
- [ ] Can delete chat session
- [ ] Can switch personas

**Data Persistence**:
- [ ] Restart backend: `docker-compose restart backend`
- [ ] Chat history still visible
- [ ] Restart PostgreSQL: `docker-compose restart postgres`
- [ ] All data intact
- [ ] Stop and start full stack: `docker-compose down && docker-compose up -d`
- [ ] All data persists

**Web Search (if enabled)**:
- [ ] Set `BRAVE_API_KEY` in `.env.docker`
- [ ] Restart backend
- [ ] Ask rare/epic/legendary persona current event question
- [ ] Verify web search executes
- [ ] Verify citations included

**Performance**:
- [ ] Send 10 messages rapidly
- [ ] No errors or timeouts
- [ ] Check response latency < 5s
- [ ] Monitor container resources: `docker stats`

**Error Handling**:
- [ ] Stop Ollama: `docker-compose stop ollama`
- [ ] Try to send message → should get error
- [ ] Restart Ollama: `docker-compose start ollama`
- [ ] Messages work again

---

## Phase 1 Deliverables Checklist

### Code Changes
- [ ] SQLAlchemy models created (`models/database_models.py`)
- [ ] Database engine & session factory (`database.py`)
- [ ] Repositories refactored to async
- [ ] Routes updated to async/await
- [ ] Startup initialization updated
- [ ] Configuration supports `DATABASE_URL`
- [ ] CORS supports `CORS_ORIGINS` env var
- [ ] Health checks implemented (liveness, readiness, startup)

### Docker Artifacts
- [ ] Backend `Dockerfile` created
- [ ] Frontend `Dockerfile` created
- [ ] `docker-compose.yml` created
- [ ] `.env.docker` template created
- [ ] `.dockerignore` file created

### Scripts & Tools
- [ ] Migration script (`scripts/migrate_sqlite_to_postgres.py`)
- [ ] Verification script (optional)

### Documentation
- [ ] `README.md` updated with Docker instructions
- [ ] `docs/MIGRATION_GUIDE.md` created
- [ ] Environment variables documented
- [ ] Troubleshooting guide added

### Testing
- [ ] All existing tests pass
- [ ] Migration tested with production data copy
- [ ] Docker Compose stack tested
- [ ] End-to-end user flows verified
- [ ] Data persistence validated

---

## Success Criteria

Phase 1 is complete when:

1. ✅ Application runs fully in Docker Compose
2. ✅ PostgreSQL replaces SQLite
3. ✅ All data migrated successfully (verified counts match)
4. ✅ All features work (chat, search, summaries, emotional state)
5. ✅ Data persists across container restarts
6. ✅ Health checks functional
7. ✅ Documentation updated
8. ✅ Can deploy to single VM or cloud platform

**NOT Required for Phase 1**:
- ❌ Horizontal scaling (Phase 2)
- ❌ Distributed cache (Phase 2)
- ❌ HTTP-based MCP (Phase 2)
- ❌ Kubernetes manifests (Phase 3)
- ❌ Observability stack (Phase 2-3)

---

## Troubleshooting

### Common Issues

#### 1. Migration fails with "table already exists"

**Cause**: PostgreSQL tables created but migration interrupted

**Solution**:
```bash
# Drop all tables
docker exec -it mcp_postgres psql -U coordinator -d mcp_coordinator -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Re-run migration
python scripts/migrate_sqlite_to_postgres.py
```

---

#### 2. Backend won't start - "database connection failed"

**Cause**: PostgreSQL not ready yet

**Solution**:
```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Wait for "database system is ready to accept connections"
# Then restart backend
docker-compose restart backend
```

---

#### 3. Persona summaries not loading

**Cause**: Summaries stored in filesystem, not database

**Solution**: Phase 1 keeps file-based summaries (moved to DB in Phase 2)
```bash
# Ensure personas/_summaries/ mounted in container
docker-compose exec backend ls /app/personas/_summaries/
```

---

#### 4. Docker build fails - "no space left on device"

**Cause**: Docker running out of disk space

**Solution**:
```bash
# Clean up unused images
docker system prune -a

# Check disk usage
docker system df
```

---

## Next Steps

After completing Phase 1:

1. **Deploy to Production** (Single VM):
   - DigitalOcean Droplet ($12/month)
   - AWS EC2 t3.medium
   - Google Cloud Compute Engine

2. **Begin Phase 2** (Cloud-Native Refactoring):
   - Distributed caching with Redis
   - Externalize RAG vector store (Qdrant)
   - HTTP-based MCP servers
   - Observability stack

3. **Monitoring** (Optional but recommended):
   - Add Prometheus metrics
   - Setup Grafana dashboards
   - Configure alerts

---

## Support

**Questions? Issues?**
- Check [PRODUCTION_READINESS_PLAN.md](PRODUCTION_READINESS_PLAN.md) for context
- Review [CLAUDE.md](CLAUDE.md) for project documentation
- Create GitHub issue for bugs
