"""Quick verification that connection pooling is working."""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from alembic.config import Config
from alembic import command

# Initialize test database
db_path = "test_verify_pooling.db"
if os.path.exists(db_path):
    os.remove(db_path)

os.environ["COORDINATOR_DB_PATH"] = db_path
alembic_cfg = Config("alembic.ini")
alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
command.upgrade(alembic_cfg, "head")

print("Database initialized with Alembic migrations")

# Now test connection pooling
from src.coordinator.repositories.session_repository import SessionRepository
from src.coordinator.repositories.base_repository import BaseRepository

repo = SessionRepository(db_path)

def create_session(idx):
    """Create a test session."""
    session_id = f"session_{idx}"
    repo.create_session(session_id, "test_persona", f"Session {idx}")
    return session_id

# Test concurrent operations
print("\nTesting concurrent session creation...")
start_time = time.time()

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(create_session, i) for i in range(20)]
    results = [f.result() for f in futures]

elapsed = time.time() - start_time

print(f"Created {len(results)} sessions in {elapsed:.3f}s")
assert len(results) == 20, "Should create 20 sessions"
assert elapsed < 2.0, f"Should complete in <2s, took {elapsed:.2f}s"

# Verify pool configuration
engine = BaseRepository._get_engine(db_path)
pool_obj = engine.pool

print(f"\nPool configuration:")
print(f"  Type: {pool_obj.__class__.__name__}")
print(f"  Size: {pool_obj.size()}")
print(f"  Checked out connections: {pool_obj.checkedout()}")

assert pool_obj.__class__.__name__ == "QueuePool", "Should use QueuePool"
assert pool_obj.size() == 5, "Pool size should be 5"

print("\n[PASS] Connection pooling verified successfully!")

# Cleanup - dispose engine first to release file locks
engine.dispose()
print("\nEngine disposed, connections closed")

# Now safe to remove database file
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Cleaned up {db_path}")
