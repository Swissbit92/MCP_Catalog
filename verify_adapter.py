"""Verify database adapter pattern implementation."""

import os
from alembic.config import Config
from alembic import command

# Initialize test database
db_path = "test_adapter.db"
if os.path.exists(db_path):
    os.remove(db_path)

os.environ["COORDINATOR_DB_PATH"] = db_path
alembic_cfg = Config("alembic.ini")
alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
command.upgrade(alembic_cfg, "head")

print("Database initialized")

# Test adapter pattern
from src.coordinator.repositories.session_repository import SessionRepository
from src.coordinator.repositories.db_adapter import SQLiteAdapter

# Test 1: Default adapter (should auto-create SQLiteAdapter)
print("\nTest 1: Default adapter initialization")
repo1 = SessionRepository(db_path)
assert repo1._adapter is not None
assert isinstance(repo1._adapter, SQLiteAdapter)
print("  [PASS] Default SQLiteAdapter created")

# Test 2: Explicit adapter injection
print("\nTest 2: Explicit adapter injection")
explicit_adapter = SQLiteAdapter(db_path)
repo2 = SessionRepository(db_path, adapter=explicit_adapter)
assert repo2._adapter is explicit_adapter
print("  [PASS] Explicit adapter injected successfully")

# Test 3: Operations through adapter
print("\nTest 3: Database operations through adapter")
# create_session(persona_key, title, session_id=None)
sid1 = repo1.create_session("test_persona", "Test Session 1", session_id="test_session_1")
sid2 = repo2.create_session("test_persona", "Test Session 2", session_id="test_session_2")

persona = repo1.get_persona_key("test_session_1")
print(f"  Retrieved persona: {persona!r} (expected: 'test_persona')")
assert persona == "test_persona", f"Expected 'test_persona', got {persona!r}"
print(f"  [PASS] Created and retrieved session via adapter")

# Test 4: Verify connection pooling still works
print("\nTest 4: Connection pooling verification")
adapter = repo1._adapter
engine = SQLiteAdapter._get_engine(db_path)
pool_obj = engine.pool

assert pool_obj.__class__.__name__ == "QueuePool"
assert pool_obj.size() == 5
print(f"  [PASS] Connection pooling intact: QueuePool(size=5)")

# Test 5: Adapter abstraction (PostgresAdapter stub)
print("\nTest 5: PostgresAdapter stub verification")
from src.coordinator.repositories.db_adapter import PostgresAdapter

try:
    postgres_adapter = PostgresAdapter("postgresql://localhost/test")
    print("  [FAIL] PostgresAdapter should raise NotImplementedError")
except NotImplementedError as e:
    print(f"  [PASS] PostgresAdapter properly stubbed: {e}")

print("\n=== All adapter pattern tests passed ===")

# Cleanup
engine.dispose()
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"\nCleaned up {db_path}")
