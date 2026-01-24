"""Tests for connection pooling performance improvements."""

import time
import uuid
import os
from concurrent.futures import ThreadPoolExecutor
from alembic.config import Config
from alembic import command
from src.coordinator.repositories.session_repository import SessionRepository
from src.coordinator.repositories.db_adapter import SQLiteAdapter


def _init_test_db(db_path: str):
    """Initialize test database with Alembic migrations."""
    # Set environment variable for database path
    os.environ["COORDINATOR_DB_PATH"] = db_path

    # Run Alembic migrations
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(alembic_cfg, "head")


def test_concurrent_session_creation():
    """
    Test concurrent session creation performance with connection pooling.

    With connection pooling (QueuePool):
    - Expected: <2s for 50 concurrent sessions
    - Pool reuses connections efficiently

    Without pooling (would be):
    - Expected: ~10s for 50 concurrent sessions
    - Each operation creates new connection
    """
    db_path = "test_pooling.db"

    # Clean up before test
    if os.path.exists(db_path):
        os.remove(db_path)

    # Initialize database schema
    _init_test_db(db_path)

    repo = SessionRepository(db_path)

    def create_session(idx):
        """Create a test session with unique ID."""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}_{idx}"
        persona_key = f"test_persona_{idx % 5}"  # Rotate through 5 personas
        title = f"Test Session {idx}"

        # create_session(persona_key, title, session_id=...)
        repo.create_session(persona_key, title, session_id=session_id)
        return session_id

    # Warm up the pool
    create_session(0)

    # Test concurrent creation
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_session, i) for i in range(50)]
        results = [f.result() for f in futures]

    elapsed = time.time() - start_time

    # Verify all sessions created
    assert len(results) == 50
    assert len(set(results)) == 50  # All unique

    # Performance assertion
    assert elapsed < 2.0, f"Concurrent operations took {elapsed:.2f}s (expected <2s with pooling)"

    print(f"[PASS] Created 50 sessions concurrently in {elapsed:.3f}s (with connection pooling)")

    # Cleanup
    if os.path.exists(db_path):
        # Dispose engine to release locks
        adapter = repo._adapter
        if hasattr(adapter, '_get_engine'):
            engine = adapter._get_engine(db_path)
            engine.dispose()
        os.remove(db_path)


def test_concurrent_read_operations():
    """Test concurrent read operations benefit from connection pooling."""
    db_path = "test_pooling_read.db"

    # Clean up before test
    if os.path.exists(db_path):
        os.remove(db_path)

    # Initialize database schema
    _init_test_db(db_path)

    repo = SessionRepository(db_path)

    # Create test data
    session_ids = []
    for i in range(10):
        session_id = f"session_{i}"
        # create_session(persona_key, title, session_id=...)
        repo.create_session("test_persona", f"Session {i}", session_id=session_id)
        session_ids.append(session_id)

    def read_session(session_id):
        """Read a session."""
        return repo.get_persona_key(session_id)

    # Test concurrent reads
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=10) as executor:
        # Read each session 10 times concurrently (100 total reads)
        futures = []
        for _ in range(10):
            for session_id in session_ids:
                futures.append(executor.submit(read_session, session_id))

        results = [f.result() for f in futures]

    elapsed = time.time() - start_time

    # Verify all reads successful
    assert len(results) == 100
    assert all(r == "test_persona" for r in results), f"Expected all 'test_persona', got: {set(results)}"

    # Performance assertion
    assert elapsed < 1.0, f"100 concurrent reads took {elapsed:.2f}s (expected <1s with pooling)"

    print(f"[PASS] Performed 100 concurrent reads in {elapsed:.3f}s (with connection pooling)")

    # Cleanup
    if os.path.exists(db_path):
        adapter = repo._adapter
        if hasattr(adapter, '_get_engine'):
            engine = adapter._get_engine(db_path)
            engine.dispose()
        os.remove(db_path)


def test_pool_reuses_connections():
    """Verify that connection pool actually reuses connections."""
    db_path = "test_pool_reuse.db"

    # Clean up before test
    if os.path.exists(db_path):
        os.remove(db_path)

    # Initialize database schema
    _init_test_db(db_path)

    repo1 = SessionRepository(db_path)
    repo2 = SessionRepository(db_path)

    # Both repos should use SQLiteAdapter
    assert isinstance(repo1._adapter, SQLiteAdapter)
    assert isinstance(repo2._adapter, SQLiteAdapter)

    # Both adapters should share the same engine (class-level)
    engine1 = SQLiteAdapter._get_engine(repo1._db_path)
    engine2 = SQLiteAdapter._get_engine(repo2._db_path)

    assert engine1 is engine2, "Repositories should share the same engine instance"

    # Verify pool configuration
    pool_obj = engine1.pool
    assert pool_obj.__class__.__name__ == "QueuePool", "Should use QueuePool"
    assert pool_obj.size() == 5, "Pool size should be 5"

    print(f"[PASS] Connection pool properly configured: QueuePool(size=5, max_overflow=10)")

    # Cleanup
    if os.path.exists(db_path):
        engine1.dispose()
        os.remove(db_path)


if __name__ == "__main__":
    print("\n=== Connection Pooling Performance Tests ===\n")

    print("Test 1: Concurrent session creation")
    test_concurrent_session_creation()

    print("\nTest 2: Concurrent read operations")
    test_concurrent_read_operations()

    print("\nTest 3: Pool connection reuse")
    test_pool_reuses_connections()

    print("\n=== All connection pooling tests passed ===\n")
